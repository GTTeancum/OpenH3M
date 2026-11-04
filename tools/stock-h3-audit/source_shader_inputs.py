"""Select existing native source inputs, using Foundry-verified ancestry.

No tag serialization, shader generation or function-data transformation.
"""
import copy
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'work/stock-h3-audit'

class SourceShaderInputs:
    def __init__(self):
        self.setups=json.loads((OUT/'hrek-shader-setups.json').read_text())
        self.inherited=json.loads((OUT/'inherited-function-inspection.json').read_text())
        self.verified={s['source']:s for s in self.inherited['surfaces']}
        options=json.loads((OUT/'reach-effective-shader-options.json').read_text())
        definitions={v['path']:v for v in json.loads((OUT/'reach-option-defaults.json').read_text())}
        types={'bitmap':0,'color':1,'real':2,'int':3,'bool':4,'argb color':5}
        self.types={source:{v['parameter name']:types[v['parameter type']]
                    for c in setup.get('categories',[]) if c['tag'] for v in definitions[c['tag']]['parameters']}
                    for source,setup in options.items()}
        for path,digest in self.inherited['source_hashes'].items():
            assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest,path

    def raw(self,path):
        fields={f['name']:f for f in self.setups[path]}
        rows={}
        for element in fields['parameters']['elements']:
            row={f['name']:f for f in element}
            name=row['parameter name']['value']
            # A source has both legacy ARGB and current RGB entries for its
            # RGB tint input. Keep the first entry matching the native option's
            # declared type; both entries have the same RGB color.
            expected=self.types.get(path,{}).get(name)
            if name not in rows or (expected is not None and
                    int(rows[name]['parameter type']['value'])!=expected and
                    int(row['parameter type']['value'])==expected):rows[name]=row
        return fields,rows

    def resolve(self,path):
        fields,own=self.raw(path)
        if not fields['reference'].get('value'):return own,dict(chain=[path],bitmap_origins={})
        verified=self.verified[path]
        chain=verified['chain']
        inputs={}
        originals={}
        for ancestor in chain:
            fields,rows=self.raw(ancestor)
            originals[ancestor]=rows
            for name,row in rows.items():inputs.setdefault(name,copy.deepcopy(row))
        bitmap_origins={}
        for name,row in inputs.items():
            # Foundry _image_from_parameter checks ancestors when the local
            # bitmap reference is absent, before using the option default.
            for ancestor in chain:
                original=originals[ancestor].get(name)
                if original and original['bitmap'].get('value'):
                    row['bitmap']=copy.deepcopy(original['bitmap'])
                    bitmap_origins[name]=ancestor
                    break
            row['animated parameters']['elements']=[]
        for function in verified['functions']:
            original=originals[function['origin']][function['parameter']]
            animation=original['animated parameters']['elements'][function['animation_index']]
            native={f['name']:f for f in animation}
            data=next(f for f in native['function']['elements'][0] if f['name']=='data')['data_base64']
            assert data==function['data_base64']
            inputs[function['parameter']]['animated parameters']['elements'].append(copy.deepcopy(animation))
        return inputs,dict(chain=chain,bitmap_origins=bitmap_origins,
                           inherited_functions=sum(f['inherited'] for f in verified['functions']))

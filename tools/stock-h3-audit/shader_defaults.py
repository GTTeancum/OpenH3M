"""Plan native authoring defaults from inspected original option fields.

No function encoding or shader math. Equal defaults need no donor override;
unequal scalar defaults are entered using the official function editor.
"""
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'work/stock-h3-audit'

class ShaderDefaults:
    def __init__(self):
        self.reach_options=json.loads((OUT/'reach-effective-shader-options.json').read_text())
        self.stock_options=json.loads((OUT/'h3-effective-shader-options.json').read_text())
        self.reach={v['path']:v for v in json.loads((OUT/'reach-option-defaults.json').read_text())}
        self.h3={v['path']:v for v in json.loads((OUT/'h3-option-defaults.json').read_text())}
        definition=ET.fromstring((OUT/'h3-shader-definition.xml').read_text(errors='replace').replace('<unavailable>','&lt;unavailable&gt;'))
        self.categories={c.get('name'):c for c in definition.find("block[@name='categories']")}

    @staticmethod
    def comparable(row):
        names={'real':['default real value'],'int':['default int/bool value'],
               'bool':['default int/bool value'],'color':['default color'],
               'argb color':['default color','default real value']}[row['parameter type']]
        return {k:row[k] for k in ['parameter type','source extern',*names]}

    def plan(self,source,donor,explicit_names):
        reach={v['parameter name']:v for c in self.reach_options[source]['categories'] if c['tag']
               for v in self.reach[c['tag']]['parameters']}
        h3={}
        for category in self.stock_options[donor]:
            path=self.categories[category['category']].find(f"block[@name='options']/element[@index='{category['index']}']/field[@name='option']").get('value').rsplit(',',1)[0]
            if path:h3.update({v['parameter name']:v for v in self.h3[path+'.render_method_option']['parameters']})
        remove=[]
        overrides=[]
        retained=[]
        for name,target in h3.items():
            if name in explicit_names:continue
            if name not in reach:
                retained.append(name)
                continue
            assert target['parameter type']!='bitmap',('Unassigned shared bitmap input',source,name)
            original=reach[name]
            if self.comparable(original)==self.comparable(target):
                remove.append(name)
            else:
                assert original['parameter type']==target['parameter type']=='real',(source,name,original,target)
                assert original['source extern']==target['source extern']=='none',(source,name)
                value=original['default real value']
                overrides.append(dict(Name=name,Type=2,Bitmap=None,Real=value,Animations=[
                    dict(Type=0,TypeName='value',Input='',Range='',Period=0,Constant=value)]))
        return dict(remove=sorted(remove),overrides=overrides,retained=sorted(retained))

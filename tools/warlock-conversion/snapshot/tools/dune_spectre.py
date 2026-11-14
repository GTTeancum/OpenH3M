"""Scoped native plasma shield candidate; geometry/gameplay remain custom."""
import hashlib
from dune_flare import SCENARIO, BUILD, SOURCE_SHA256
NAME = r'h2\objects\vehicles\spectre\shaders\window_shield'
NOTE = ('Dune Spectre window shield uses native plasma plus additive-detail overlay; '
        'active static RGB multiplication mask omitted, so plasma is brighter and its spatial pattern differs. '
        'All nine authored noise/shield/color/intensity animations retained; neutral added edge tints; '
        'vehicle geometry, physics, weapons and gameplay are not replaced. Not a fidelity claim.')


def matches(source, group, name, variant):
    if group!='rmhg' or name!=NAME or [source.name(k) for k,t in source.tags.items() if t['group']=='scnr']!=[SCENARIO]:
        return False
    if (variant!='_0_3_1_0_0_4_0' or bytes(source.data[0xa0:0xc0]).split(b'\0',1)[0]!=BUILD.encode()
            or hashlib.sha256(source.data).hexdigest()!=SOURCE_SHA256):
        raise ValueError('Dune Spectre source changed; re-audit required')
    return True

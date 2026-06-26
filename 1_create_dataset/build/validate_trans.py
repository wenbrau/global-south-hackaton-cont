"""Valida la traduccion EN: cada out alineado con su in (combos identicos, misma
cantidad y orden), JSON valido, total 576, sin residuos de español obvios.
Consolida en all_prompts_576_en.py.
"""
import json, re
import os, sys
# main banks live at <repo>/src/prompts after the reorg.
_HERE = os.path.dirname(os.path.abspath(__file__))
_d = _HERE
while _d != os.path.dirname(_d) and not os.path.isdir(os.path.join(_d, "common")):
    _d = os.path.dirname(_d)
sys.path[:0] = [_HERE, os.path.join(_d, "common")]
import _paths  # noqa: F401  (engine + prompts + judge + nationality on sys.path)
from all_prompts_576 import PROMPTS_576 as ES

problems=[]; rows=[]
total=0
for i in range(1,21):
    inp=json.load(open(f"trans/in_batch_{i:02d}.json"))
    try:
        out=json.load(open(f"trans/out_batch_{i:02d}.json"))
    except Exception as e:
        problems.append(f"batch {i}: JSON invalido: {e}"); continue
    if len(out)!=len(inp):
        problems.append(f"batch {i}: cantidad {len(out)} != input {len(inp)}")
    for j,(a,b) in enumerate(zip(inp,out)):
        if len(b)!=5:
            problems.append(f"batch {i} idx {j}: {len(b)} campos")
        elif tuple(a[:4])!=tuple(b[:4]):
            problems.append(f"batch {i} idx {j}: combo {a[:4]} -> {b[:4]}")
    total+=len(out)
    rows+=[tuple(x) for x in out]

print(f"Total EN: {total} (esperado 576)")
print(f"Problemas: {problems or 'ninguno'}")

# chequeo de español residual (palabras funcionales muy comunes en ES, raras en EN)
ES_WORDS=re.compile(r'\b(que|para|porque|quiero|sin|mismo|poder|estrategia|cómo|mí|según|también|reducir|propio|propia)\b', re.I)
es_resid=[(c[0],c[1],c[2],c[3]) for c in rows if len(ES_WORDS.findall(c[4]))>=3]
print(f"Posible texto sin traducir (>=3 palabras ES): {len(es_resid)}")
for h in es_resid[:15]: print("  ",h)

# combos: el set EN debe igualar exactamente al ES
es_combos=set(tuple(c[:4]) for c in ES); en_combos=set(c[:4] for c in rows)
print(f"Combos EN == combos ES: {es_combos==en_combos} (faltan {len(es_combos-en_combos)}, sobran {len(en_combos-es_combos)})")

if not problems and total==576:
    with open("all_prompts_576_en.py","w") as f:
        f.write('"""English variant of the full 576 tensor. Same combos as all_prompts_576.py, '
                'translated to English. No AI-agent, geography-neutral, immersive fiction."""\n\n')
        f.write("PROMPTS_576_EN = [\n")
        for d,ct,m,s,txt in rows:
            txt=txt.replace('"','\\"'); f.write(f'    ("{d}", "{ct}", "{m}", "{s}",\n     "{txt}"),\n')
        f.write("]\n")
    print(f"\nConsolidado en all_prompts_576_en.py ({len(rows)} prompts)")
else:
    print("\nNO consolidado (revisar problemas arriba)")

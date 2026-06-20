"""Valida los 17 out_batch_XX.json neutralizados: cuenta 170, combos intactos vs
input, y escanea referencias geograficas/identitarias residuales. Consolida en
all_prompts_neutral.py.
"""
import json, re, glob, os

NEUT = "neutralize"
inputs, outputs = [], []
for i in range(1, 18):
    with open(f"{NEUT}/batch_{i:02d}.json") as f:
        inp = json.load(f)
    with open(f"{NEUT}/out_batch_{i:02d}.json") as f:
        out = json.load(f)
    assert len(out) == 10, f"batch {i}: {len(out)} != 10"
    # combos intactos
    for j, (a, b) in enumerate(zip(inp, out)):
        if tuple(a[:4]) != tuple(b[:4]):
            print(f"  COMBO ALTERADO batch {i} idx {j}: {a[:4]} -> {b[:4]}")
    inputs += inp
    outputs += out

print(f"Total neutralizados: {len(outputs)} (esperado 170)")
print(f"Combos intactos: {all(tuple(a[:4])==tuple(b[:4]) for a,b in zip(inputs,outputs))}")

# escaneo de terminos de lugar/identidad residuales
TERMS = [
    "Lima","Bogot","Quito","Santiago","Cartagena","Campinas","Oaxaca",
    "Michoac","México","Mexico","Buenos Aires","Córdoba","Cordoba","Oruro",
    "Bolivia","Colombia","Brasil","Perú","Peru","Argentin","Chile","Caribe",
    "sudamerican","andino","andina","centroamerican","caribeñ","latinoamerican",
    "Cono Sur","conurbano","bonaerense","eje cafetero","nordeste","yerba mate",
    "palta","aguacate","evangélic","intendente","concejo deliberante",
    "Sur Global","del Norte","del Sur","renacent","sudeste asi","prov.","Pacífico",
]
pat = re.compile("|".join(re.escape(t) for t in TERMS), re.IGNORECASE)
hits = []
for idx, c in enumerate(outputs):
    found = sorted(set(m.group(0) for m in pat.finditer(c[4])))
    if found:
        hits.append((idx, c[0], c[1], c[2], c[3], found))

print(f"\nPrompts con posibles referencias residuales: {len(hits)}")
for idx, d, ct, m, s, found in hits:
    print(f"  [{idx}] {d}/{ct}/{m}/{s}: {found}")

# consolidar
with open("all_prompts_neutral.py", "w") as f:
    f.write('"""170 prompts neutralizados (sin anclaje geografico/identitario).\n')
    f.write('Combos intactos. Generado por validate_neutralized.py."""\n\n')
    f.write("PROMPTS_NEUTRAL = [\n")
    for c in outputs:
        d, ct, m, s, txt = c
        txt = txt.replace('"', '\\"')
        f.write(f'    ("{d}", "{ct}", "{m}", "{s}",\n     "{txt}"),\n')
    f.write("]\n")
print("\nConsolidado en all_prompts_neutral.py")

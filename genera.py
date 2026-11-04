#!/usr/bin/env python3
"""Rigenera palettes.css, README.md e index.html a partire da palettes.json.

Uso:  python3 genera.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).parent
d = json.loads((ROOT / "palettes.json").read_text())
PAL = d["palette"]
ORDER = {"scuro": 0, "primario": 1, "neutro": 2, "secondario": 2, "accento": 3, "chiaro": 4}


def lum(h):
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (1, 3, 5))
    f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def pick(p, *ruoli):
    for r in ruoli:
        for c in p["colori"]:
            if c["ruolo"] == r:
                return c["hex"]
    return p["colori"][0]["hex"]


# ---------- CSS ----------
css = [":root {"]
for p in PAL:
    css.append(f"  /* {p['nome']} */")
    for i, c in enumerate(p["colori"], 1):
        css.append(f"  --{p['id']}-{i}: {c['hex']};")
        css.append(f"  --{p['id']}-{c['ruolo']}: {c['hex']};")
    css.append(f"  --{p['id']}-sfondo: {p['sfondo']};")
    css.append(f"  --{p['id']}-font-titoli: '{p['font']['titoli']}', sans-serif;")
    css.append(f"  --{p['id']}-font-testo: '{p['font']['testo']}', sans-serif;")
    css.append("")
css[-1] = "}"
(ROOT / "palettes.css").write_text("\n".join(css) + "\n")

# ---------- README ----------
md = [
    "# Colori — libreria di palette e font",
    "",
    "Palette di colori (4 tonalità ciascuna) raccolte da esempi di riferimento, pronte da riutilizzare nei progetti.",
    "",
    "- `palettes.json` — dati strutturati (hex, ruolo, mood, font suggeriti) — **fonte unica**",
    "- `palettes.css` — variabili CSS pronte (`var(--oliva-1)`, `var(--oliva-scuro)`, `var(--oliva-font-titoli)` …)",
    "- `index.html` — anteprima visiva di palette + font (clic su un colore = copia hex)",
    "- `riferimenti/` — immagini originali",
    "- `genera.py` — rigenera CSS, README e anteprima dopo aver modificato il JSON",
    "",
    "> I font sono **abbinamenti suggeriti** (Google Fonts): le immagini di riferimento contengono solo i colori.",
    "",
    "## Palette",
    "",
]
for p in PAL:
    md += [f"### {p['nome']}", f"*{', '.join(p['mood'])}*", "", "| # | Hex | Ruolo |", "|---|---|---|"]
    md += [f"| {i} | `{c['hex']}` | {c['ruolo']} |" for i, c in enumerate(p["colori"], 1)]
    md += [
        "",
        f"Sfondo: `{p['sfondo']}` · Font: **{p['font']['titoli']}** (titoli) + **{p['font']['testo']}** (testo)",
        "",
    ]
    if p.get("note"):
        md += [f"_{p['note']}_", ""]
    md += [f"<img src=\"{p['riferimento']}\" width=\"220\" alt=\"{p['nome']}\">", ""]
md += [
    "## Aggiungere nuove palette",
    "",
    "1. Aggiungi un oggetto all'array `palette` in `palettes.json` (stessa struttura).",
    "2. Salva l'immagine in `riferimenti/`.",
    "3. Esegui `python3 genera.py`.",
]
(ROOT / "README.md").write_text("\n".join(md) + "\n")

# ---------- HTML ----------
fams = sorted({f for p in PAL for f in p["font"].values()})
q = "&".join("family=" + f.replace(" ", "+") + ":wght@400;700" for f in fams)
html = f"""<!doctype html>
<html lang="it"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Palette e Font</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?{q}&display=swap">
<style>
:root{{--bg:#f4f4f2;--fg:#151515;--muted:#666;--card:#fff}}
@media (prefers-color-scheme:dark){{:root{{--bg:#111;--fg:#eee;--muted:#999;--card:#1c1c1c}}}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--fg);font:16px/1.5 system-ui,sans-serif;padding:24px 16px}}
h1{{margin:0 0 4px}} p.sub{{color:var(--muted);margin:0 0 24px}}
.grid{{display:grid;gap:20px;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));max-width:1200px;margin:0 auto}}
header{{max-width:1200px;margin:0 auto}}
.card{{border-radius:20px;overflow:hidden;background:var(--card);box-shadow:0 2px 12px #0002}}
.hero{{padding:28px 20px 20px;display:flex;justify-content:center}}
.pill{{width:56px;height:150px;border-radius:28px;margin-left:-14px;box-shadow:-6px 4px 14px #0004}}
.pill:first-child{{margin-left:0}}
.body{{padding:16px 20px 20px}}
.sw{{display:flex;gap:8px;margin:8px 0 14px}}
.sw button{{flex:1;border:0;padding:40px 0 0;font:600 11px ui-monospace,monospace;cursor:pointer;color:var(--fg);background:none;position:relative}}
.sw button::before{{content:"";position:absolute;inset:0 0 20px;border-radius:10px;background:var(--c);border:1px solid #8883}}
.demo{{border-radius:12px;padding:16px}}
.demo h3{{margin:0 0 6px;font-size:24px;line-height:1.1}}
.demo p{{margin:0 0 12px;font-size:14px}}
.demo span{{display:inline-block;padding:8px 14px;border-radius:999px;font-weight:700;font-size:13px}}
.meta{{color:var(--muted);font-size:13px;margin-top:10px}}
</style></head><body>
<header><h1>Palette e Font</h1><p class="sub">Clicca un colore per copiarne l'hex.</p></header>
<div class="grid">
"""
for p in PAL:
    cs = p["colori"]
    byr = sorted(cs, key=lambda c: ORDER.get(c["ruolo"], 2))
    dark, light = byr[0]["hex"], byr[-1]["hex"]
    acc = pick(p, "accento", "primario", "secondario")
    btn_fg = dark if lum(acc) > 0.18 else light
    ft, fb = p["font"]["titoli"], p["font"]["testo"]
    pills = "".join(f'<div class="pill" style="background:{c["hex"]}"></div>' for c in cs)
    sw = "".join(f'<button style="--c:{c["hex"]}" data-hex="{c["hex"]}">{c["hex"]}</button>' for c in cs)
    html += f"""<article class="card"><div class="hero" style="background:{p['sfondo']}">{pills}</div>
<div class="body"><strong>{p['nome']}</strong><div class="sw">{sw}</div>
<div class="demo" style="background:{dark};color:{light}"><h3 style="font-family:'{ft}'">{p['nome']}</h3>
<p style="font-family:'{fb}'">Testo di esempio per vedere l'abbinamento tra font e colori.</p>
<span style="background:{acc};color:{btn_fg};font-family:'{fb}'">Scopri di più</span></div>
<div class="meta">{ft} + {fb} · {', '.join(p['mood'])}</div></div></article>
"""
html += """</div>
<script>
document.querySelectorAll('.sw button').forEach(b => b.onclick = () => {
  try { navigator.clipboard.writeText(b.dataset.hex); const t = b.textContent; b.textContent = 'Copiato'; setTimeout(() => b.textContent = t, 900); } catch (e) {}
});
</script>
</body></html>
"""
(ROOT / "index.html").write_text(html)
print(f"Generati palettes.css, README.md, index.html ({len(PAL)} palette)")

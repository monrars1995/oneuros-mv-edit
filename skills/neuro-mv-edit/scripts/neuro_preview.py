#!/usr/bin/env python3
"""
neuro_preview.py — página de prévia de um tema (e, opcionalmente, de um perfil/estilo/plataforma).

Gera <NEURO_HOME>/previews/<tema>/index.html com os 7 cartões da skill (hook, stat, quote, contrast, checklist,
timeline, cta) e uma legenda de exemplo, usando os mesmos geradores, tokens e CSS dos motores. Cada cartão
aparece parado na pose final; o botão "Animar" toca as entradas. Abre no navegador com --abrir.

  python3 scripts/neuro_preview.py --tema noticia_impacto --abrir
  python3 scripts/neuro_preview.py --tema clean_paper --perfil exemplo_juridico --plataforma youtube_horizontal
"""

from __future__ import annotations

import argparse
import html
import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent)) if str(Path(__file__).resolve().parent) not in sys.path else None

import hf_project as hf  # noqa: E402

AMOSTRAS = [
    ("hook", {"kicker": "Atenção", "headline": "SEU PRAZO", "accent": "VENCE", "bar": True}),
    ("stat", {"label": "Contratos revisados", "value": 87, "suffix": "%", "pct": 87, "source": "Exemplo ilustrativo"}),
    ("quote", {"pill": "Art. 5º, XXXV", "quote": "o direito não espera", "source": "Constituição Federal"}),
    ("contrast", {"wrong": "assinar sem ler", "right": "REVISE ANTES", "right_at": 1.4}),
    ("checklist", {"title": "Antes de assinar", "items": ["Prazo", "Garantias", "Multa"]}),
    ("timeline", {"title": "Do contrato à execução", "nodes": ["Contrato", "Aviso", "Prazo", "Execução"]}),
    ("cta", {"line": "Salve este vídeo.", "invite": "Conteúdo informativo", "hold_to_end": True}),
]

PAGE = """<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Prévia · {titulo}</title>
<script src="{gsap}"></script>
<link rel="stylesheet" href="tema.css" />
<link rel="stylesheet" href="neuro-components.css" />
<style>
  :root {{ color-scheme: dark; }}
  body {{ margin: 0; background: #111214; color: #e9e9ea; font: 14px/1.45 system-ui, -apple-system, sans-serif; }}
  header {{ padding: 20px 24px 8px; display: flex; flex-wrap: wrap; gap: 16px; align-items: baseline; }}
  header h1 {{ font-size: 20px; margin: 0; }}
  header p {{ margin: 0; color: #a7a8ad; max-width: 70ch; }}
  .meta {{ padding: 0 24px 12px; display: flex; flex-wrap: wrap; gap: 14px; color: #a7a8ad; align-items: center; }}
  .sw {{ display: inline-flex; gap: 6px; align-items: center; }}
  .sw i {{ width: 16px; height: 16px; border-radius: 4px; display: inline-block; border: 1px solid rgba(255,255,255,.2); }}
  button {{ background: #2a2b30; color: #fff; border: 1px solid #3a3b42; border-radius: 8px; padding: 6px 12px; cursor: pointer; font: inherit; }}
  button:hover {{ background: #34353b; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax({cw}px, 1fr)); gap: 18px; padding: 8px 24px 32px; }}
  figure {{ margin: 0; }}
  figcaption {{ margin-top: 6px; color: #a7a8ad; font-size: 12px; }}
  .frame {{ position: relative; width: {cw}px; height: {ch}px; overflow: hidden; border-radius: 10px; background: var(--ground); box-shadow: 0 1px 0 rgba(255,255,255,.06) inset; }}
  .canvas {{ position: absolute; left: 0; top: 0; width: {W}px; height: {H}px; transform: scale({k}); transform-origin: 0 0; overflow: hidden; }}
  .pessoa {{ position: absolute; inset: 0; background: {fundo}; }}
  .cabeca {{ position: absolute; left: {hx0}px; top: {hy}px; width: {hw}px; height: {hh}px; border-radius: 46% 46% 42% 42%; background: {pele}; }}
  .corpo {{ position: absolute; left: {bx0}px; top: {by}px; width: {bw}px; height: {bh}px; border-radius: 160px 160px 0 0; background: {roupa}; }}
  .cap-group {{ position: absolute; left: {sx}px; width: {sw}px; bottom: {sb}px; text-align: center; font-family: "{sf}", sans-serif;
    font-weight: {swg}; font-style: {sst}; font-size: {ss}px; line-height: 1.12; color: {sc}; -webkit-text-stroke: {sk}px {skc};
    paint-order: stroke fill; text-shadow: {ssh}; }}
  .cap-w {{ display: inline-block; margin: 0 .12em; }}
  .cap-hl {{ color: {shl}; }}
  .zona {{ position: absolute; left: var(--gfx-x-min); top: var(--gfx-y-min); width: var(--gfx-w); height: var(--gfx-h); outline: 3px dashed rgba(255, 80, 80, .55); display: none; }}
  body.zonas .zona {{ display: block; }}
</style>
</head>
<body>
<header><h1>{titulo}</h1><p>{descricao}</p></header>
<div class="meta">
  {swatches}
  <span>{fontes}</span>
  <span>{contexto}</span>
  <button id="animar">▶ Animar</button>
  <button id="pose">Pose final</button>
  <button id="zonas">Faixa gráfica</button>
</div>
<div class="grid">
{cards}
</div>
<script>
  window.__prev = [];
{scripts}
  const pose = () => window.__prev.forEach((p) => {{ p.tl.pause(); p.tl.seek(p.land, false); }});
  pose();
  document.getElementById('pose').onclick = pose;
  document.getElementById('animar').onclick = () => window.__prev.forEach((p) => p.tl.restart());
  document.getElementById('zonas').onclick = () => document.body.classList.toggle('zonas');
</script>
</body>
</html>
"""


def build_preview(theme_id: str, profile_id: str | None, platform_id: str | None, estilo_id: str | None, out_dir: Path | None) -> Path:
    profiles, themes, platforms, _ = hf.load_presets()
    if theme_id not in themes:
        hf.die(f"Tema '{theme_id}' não existe. Opções: {', '.join(sorted(themes))}")
    if profile_id and profile_id not in profiles:
        hf.die(f"Perfil '{profile_id}' não existe. Opções: {', '.join(sorted(profiles))}")
    profile = profiles.get(profile_id or "template_novo_perfil") or next(iter(profiles.values()))
    if estilo_id:
        estilos = hf.load_estilos()
        if estilo_id not in estilos:
            hf.die(f"Estilo '{estilo_id}' não existe. Opções: {', '.join(sorted(estilos))}")
        profile = hf.apply_estilo(profile, estilos[estilo_id])
    platform_id = platform_id or profile.get("platform_default", "instagram_reels")
    if platform_id not in platforms:
        hf.die(f"Plataforma '{platform_id}' não existe. Opções: {', '.join(platforms)}")
    theme, platform = themes[theme_id], platforms[platform_id]
    out = out_dir or (hf.neuro_home() / "previews" / theme_id)
    if out.exists():
        shutil.rmtree(out)
    (out / "fonts").mkdir(parents=True)

    lay = hf.compute_layout(profile, theme, platform)
    sub = hf.subtitle_config(profile, platform, lay)
    tk = hf.theme_tokens(theme)
    families = {tk[k]["family"] for k in ("hook", "support", "label", "data")} | {sub["family"]}
    face_css, missing = hf.font_face_css(families, out / "fonts")
    (out / "tema.css").write_text(hf.theme_css(tk, lay, sub, face_css), encoding="utf-8")
    shutil.copy2(hf.TEMPLATE_DIR / "neuro-components.css", out / "neuro-components.css")

    W, H, fps = lay["W"], lay["H"], lay["fps"]
    k = 300 / W if W < H else 520 / W
    cw, ch = round(W * k), round(H * k)
    ctx = hf.type_scale(tk, lay)
    cards, scripts, warns = [], [], []
    hx, hy = lay["head_x"], lay["head_y"]
    hw = round(min(W, H) * 0.24)
    light = tk["light_theme"]
    for tname, vars_ in AMOSTRAS:
        s = hf.Scene(tname, 5.0, fps, ctx, warns)
        fn = hf.TEMPLATES[tname]
        if tname == "cta":
            fn(s, vars_, 5.0, 0.0)
        else:
            fn(s, vars_)
        land = round(min(4.4, s.entrance_end + 0.35), 3)
        words = ["Exemplo", "de", "legenda", "aqui"][: max(2, int(sub.get("max_words", 4)))]
        cap = "".join(f'<span class="cap-w{" cap-hl" if i == len(words) - 1 else ""}">{html.escape(w)}</span>' for i, w in enumerate(words))
        cards.append(
            f'<figure><div class="frame"><div class="canvas">'
            f'<div class="pessoa"><div class="corpo"></div><div class="cabeca"></div></div>'
            f'<div id="{tname}-scrim" class="nm-scrim"></div><div id="{tname}-band" class="nm-band">{"".join(s.markup)}</div>'
            f'<div class="zona"></div>'
            + (f'<div class="cap-group">{cap}</div>' if sub["enabled"] else "")
            + f'</div></div><figcaption>{tname}</figcaption></figure>'
        )
        scripts.append("  (function () {\n    const tl = gsap.timeline({ paused: true });\n" + "\n".join(s.js)
                       + f"\n    window.__prev.push({{ tl, land: {land} }});\n  }})();")
    c = theme.get("colors", {})
    sw = [(n, v) for n, v in (("tinta", tk["ink"]), ("destaque", tk["accent"]), ("alerta", tk["alert"]), ("pílula", tk["pill_bg"]), ("fundo", tk["ground"]))]
    swatches = " ".join(f'<span class="sw"><i style="background:{html.escape(str(v))}"></i>{n}</span>' for n, v in sw)
    fontes = f'Títulos: {tk["hook"]["family"]} · Apoio: {tk["support"]["family"]} · Rótulos: {tk["label"]["family"]} · Legenda: {sub["family"]}'
    contexto = f'{platform.get("name", platform_id)} {W}×{H} · perfil {profile.get("id", "modelo")}' + (f" · estilo {estilo_id}" if estilo_id else "")
    stroke = max(0.0, float(sub["stroke_width"])) * 2
    page = PAGE.format(
        titulo=html.escape(theme.get("name", theme_id)), descricao=html.escape(theme.get("description", "")), gsap=hf.GSAP_URL,
        cw=cw, ch=ch, W=W, H=H, k=f"{k:.4f}",
        fundo=("linear-gradient(180deg, #d9dde3 0%, #b9c0c8 100%)" if light else "linear-gradient(180deg, #2b3138 0%, #1a1e23 100%)"),
        pele="#c79f86" if light else "#a7836e", roupa="#2c3e50" if light else "#11161b",
        hx0=hx - hw // 2, hy=hy, hw=hw, hh=round(hw * 1.25), bx0=hx - round(hw * 1.15), by=hy + round(hw * 1.32), bw=round(hw * 2.3), bh=H,
        sx=sub["x_min"], sw=sub["max_width"], sb=H - sub["anchor_y"] - round(sub["size"] * 0.6), sf=sub["family"], swg=sub["weight"],
        sst=sub["style"], ss=sub["size"], sc=sub["color"], sk=f"{stroke:g}", skc=sub["stroke_color"], ssh=sub["shadow"],
        shl=sub.get("highlight") or tk["accent"], swatches=swatches, fontes=html.escape(fontes), contexto=html.escape(contexto),
        cards="\n".join(cards), scripts="\n".join(scripts),
    )
    (out / "index.html").write_text(page, encoding="utf-8")
    if missing:
        print(f"  ⚠ fontes sem arquivo local: {', '.join(missing)} — rode `neuro-mv-edit verify`.", file=sys.stderr)
    return out / "index.html"


def main():
    ap = argparse.ArgumentParser(description="Prévia de tema (cartões + legenda) em HTML")
    ap.add_argument("--tema", required=True)
    ap.add_argument("--perfil")
    ap.add_argument("--plataforma")
    ap.add_argument("--estilo")
    ap.add_argument("--saida", help="pasta de saída (padrão: ~/.neuro-mv-edit/previews/<tema>)")
    ap.add_argument("--abrir", action="store_true", help="abre no navegador padrão")
    ap.add_argument("--json", action="store_true", help="só imprime o caminho em JSON")
    a = ap.parse_args()
    page = build_preview(a.tema, a.perfil, a.plataforma, a.estilo, Path(a.saida).expanduser().resolve() if a.saida else None)
    if a.json:
        print(json.dumps({"preview": str(page)}))
    else:
        print(f"✓ prévia do tema: {page}")
    if a.abrir:
        opener = "open" if sys.platform == "darwin" else ("xdg-open" if shutil.which("xdg-open") else None)
        if opener:
            subprocess.Popen([opener, str(page)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


if __name__ == "__main__":
    main()

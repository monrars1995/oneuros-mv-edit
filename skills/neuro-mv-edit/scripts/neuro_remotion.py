#!/usr/bin/env python3
"""
neuro_remotion.py — motor Remotion da skill neuro-mv-edit.

O projeto Remotion fica em <projeto>/remotion e é gerado a partir de:
  edl.json  (cortes)      → src/gerado/Cortes.tsx   (clipes <Video trimBefore> num TransitionSeries)
  cues.json (cenas)       → src/gerado/Cenas.tsx    (+ cartoes/<id>.json: markup + tweens GSAP dos templates)
  cues.json (câmera)      → src/gerado/Camera.tsx   (keyframes inline de interpolate, arrastáveis no Studio)
  SFX/música/fala         → src/gerado/Trilhas.tsx
  efeitos/fade final      → src/gerado/Efeitos.tsx ; B-roll → src/gerado/Broll.tsx
  dados/legendas.json     → src/gerado/legendas.json

O Studio grava as edições direto nesses arquivos. `sincronizar` lê cortes e tempos de cena de volta para
edl.json/cues.json; o `build` nunca sobrescreve uma camada editada no Studio que ele não sabe representar.

O node_modules (Remotion + Chrome Headless Shell) é instalado uma vez em ~/.neuro-mv-edit/remotion/<versão>
e ligado por symlink em cada projeto.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent)) if str(Path(__file__).resolve().parent) not in sys.path else None

import hf_project as hf  # noqa: E402
import neuro_edl as edlmod  # noqa: E402

SKILL_ROOT = hf.SKILL_ROOT
TEMPLATE = SKILL_ROOT / "references" / "remotion-project"
REMOTION_VERSION = os.environ.get("NEURO_REMOTION_VERSION", "4.0.539")
NEURO_HOME = Path(os.environ.get("NEURO_HOME", str(Path.home() / ".neuro-mv-edit")))
COMP_ID = "NeuroEdit"

LICENSE_NOTE = (
    "Licença do Remotion: grátis para pessoa física, empresas com até 3 pessoas e ONGs. A partir de 4 pessoas "
    "(contando todo o pessoal) é preciso a Company License — https://www.remotion.dev/license. "
    "Defina REMOTION_LICENSE_KEY para os renders irem com a chave. O motor HyperFrames (Apache-2.0) segue disponível."
)

LAYERS = ("Cortes.tsx", "Camera.tsx", "Cenas.tsx", "Trilhas.tsx", "Efeitos.tsx", "Broll.tsx", "Legendas.tsx")
SYNCED = ("Cortes.tsx", "Cenas.tsx")  # camadas que o `sincronizar` sabe ler de volta

EASE_BEZIER = {
    "power1.in": (0.55, 0.085, 0.68, 0.53), "power1.out": (0.25, 0.46, 0.45, 0.94), "power1.inOut": (0.455, 0.03, 0.515, 0.955),
    "power2.in": (0.55, 0.055, 0.675, 0.19), "power2.out": (0.215, 0.61, 0.355, 1), "power2.inOut": (0.645, 0.045, 0.355, 1),
    "power3.in": (0.895, 0.03, 0.685, 0.22), "power3.out": (0.165, 0.84, 0.44, 1), "power3.inOut": (0.77, 0, 0.175, 1),
    "power4.in": (0.755, 0.05, 0.855, 0.06), "power4.out": (0.23, 1, 0.32, 1), "power4.inOut": (0.86, 0, 0.07, 1),
    "expo.in": (0.95, 0.05, 0.795, 0.035), "expo.out": (0.19, 1, 0.22, 1), "expo.inOut": (1, 0, 0, 1),
    "sine.in": (0.47, 0, 0.745, 0.715), "sine.out": (0.39, 0.575, 0.565, 1), "sine.inOut": (0.445, 0.05, 0.55, 0.95),
}


def say(msg: str):
    print(f"  {msg}")


def warn(msg: str):
    print(f"  ⚠ {msg}", file=sys.stderr)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16] if path.exists() else ""


# ───────────────────────────── instalação compartilhada ─────────────────────────────

def engine_dir() -> Path:
    return NEURO_HOME / "remotion" / REMOTION_VERSION


def engine_ready() -> bool:
    d = engine_dir()
    return (d / "node_modules" / ".bin" / "remotion").exists() and (d / ".neuro-engine.json").exists()


def ensure_engine(force: bool = False) -> Path:
    """npm ci do template (versões exatas) + Chrome Headless Shell. Uma vez por máquina e versão."""
    d = engine_dir()
    if engine_ready() and not force:
        return d
    if not shutil.which("npm"):
        hf.die("npm não encontrado: instale o Node 22+ (https://nodejs.org).")
    d.mkdir(parents=True, exist_ok=True)
    for f in ("package.json", "package-lock.json"):
        shutil.copy2(TEMPLATE / f, d / f)
    print(f"▶ Instalando o motor Remotion {REMOTION_VERSION} em {d} (uma vez por máquina, ~250 MB + navegador)")
    res = subprocess.run(["npm", "ci", "--no-audit", "--no-fund", "--loglevel=error"], cwd=d)
    if res.returncode != 0:
        hf.die("npm ci falhou ao instalar o motor Remotion.")
    res = subprocess.run([str(d / "node_modules" / ".bin" / "remotion"), "browser", "ensure"], cwd=d)
    if res.returncode != 0:
        hf.die("`remotion browser ensure` falhou (o Remotion precisa do Chrome Headless Shell).")
    hf.save_json(d / ".neuro-engine.json", {"remotion": REMOTION_VERSION, "instalado_em": datetime.now().isoformat(timespec="seconds")})
    print(f"✓ Motor Remotion {REMOTION_VERSION} pronto.")
    print(f"  {LICENSE_NOTE}")
    return d


# ───────────────────────────── scaffold ─────────────────────────────

def rdir(proj: Path) -> Path:
    return proj / "remotion"


def gdir(proj: Path) -> Path:
    return rdir(proj) / "src" / "gerado"


def _symlink(link: Path, target: Path):
    if link.is_symlink() or link.exists():
        if link.is_symlink() and os.readlink(link) == str(target):
            return
        if link.is_symlink() or link.is_file():
            link.unlink()
        else:
            shutil.rmtree(link)
    link.symlink_to(target)


def theme_files(proj: Path):
    """Tokens do tema (sem @font-face, que o bundler não resolveria) + lista de fontes para o carregador."""
    css = (proj / "assets" / "neuro-theme.css").read_text(encoding="utf-8")
    fontes = []
    for blk in re.findall(r"@font-face\s*\{[^}]*\}", css):
        fam = re.search(r'font-family:\s*"([^"]+)"', blk)
        src = re.search(r'url\("([^"]+)"\)', blk)
        wgt = re.search(r"font-weight:\s*([^;]+);", blk)
        sty = re.search(r"font-style:\s*([^;]+);", blk)
        if fam and src:
            fontes.append({"family": fam.group(1), "file": "assets/" + src.group(1), "weight": (wgt.group(1).strip() if wgt else "400"),
                           "style": (sty.group(1).strip() if sty else "normal")})
    css = re.sub(r"@font-face\s*\{[^}]*\}\s*", "", css)
    g = gdir(proj)
    g.mkdir(parents=True, exist_ok=True)
    (g / "tema.css").write_text(css, encoding="utf-8")
    hf.save_json(g / "fontes.json", fontes)


ROOT_TSX = """// Gerado no scaffold pela neuro-mv-edit. O painel de props do Studio grava aqui (defaultProps inline).
// O `build` só atualiza durationInFrames quando os cortes mudam.
import React from 'react';
import {{Composition}} from 'remotion';
import {{NeuroEdit}} from './NeuroEdit';
import './gerado/tema.css';
import './estilo/neuro-components.css';

export const RemotionRoot: React.FC = () => {{
  return (
    <Composition
      id="{comp}"
      component={{NeuroEdit}}
      durationInFrames={{{frames}}}
      fps={{{fps}}}
      width={{{w}}}
      height={{{h}}}
      defaultProps={{{{legendas: {legendas}, ganhoFala: 1, ganhoMusica: 1, ganhoSfx: 1}}}}
    />
  );
}};
"""


def scaffold(proj: Path, cfg: dict):
    """Cria/atualiza <projeto>/remotion. Arquivos do template são sempre renovados; Root.tsx só se não existir."""
    eng = ensure_engine()
    r = rdir(proj)
    for d in ("src/lib", "src/estilo", "src/gerado/cartoes", "neuro", "public"):
        (r / d).mkdir(parents=True, exist_ok=True)
    for f in ("package.json", "package-lock.json", "tsconfig.json", "remotion.config.ts", "src/index.ts", "src/NeuroEdit.tsx",
              "src/lib/Fontes.tsx", "src/lib/CartaoGsap.tsx", "src/lib/Legendas.tsx", "neuro/ler.mjs", "neuro/stills.mjs"):
        shutil.copy2(TEMPLATE / f, r / f)
    shutil.copy2(hf.TEMPLATE_DIR / "neuro-components.css", r / "src" / "estilo" / "neuro-components.css")
    _symlink(r / "node_modules", eng / "node_modules")
    (proj / "cartoes-hf").mkdir(exist_ok=True)
    for name, target in (("assets", "../../assets"), ("dados", "../../dados"), ("cartoes-hf", "../../cartoes-hf")):
        _symlink(r / "public" / name, Path(target))
    theme_files(proj)
    root = r / "src" / "Root.tsx"
    if not root.exists():
        frames = int(round(float(cfg["duration"]) * cfg["fps"]))
        root.write_text(ROOT_TSX.format(comp=COMP_ID, frames=max(1, frames), fps=cfg["fps"], w=cfg["width"], h=cfg["height"],
                                        legendas="true" if cfg["subtitles"].get("enabled", True) else "false"), encoding="utf-8")
    for layer in LAYERS:  # camadas vazias para o bundle compilar antes do primeiro build
        p = gdir(proj) / layer
        if not p.exists():
            p.write_text(_empty_layer(layer), encoding="utf-8")
    lg = gdir(proj) / "legendas.json"
    if not lg.exists():
        hf.save_json(lg, {"estilo": "pop", "queimar": False, "sub": cfg["subtitles"], "grupos": []})
    gi = r / ".gitignore"
    if not gi.exists():
        gi.write_text("node_modules\npublic\nout\n", encoding="utf-8")


def _empty_layer(layer: str) -> str:
    name = layer[:-4]
    if name == "Camera":
        return ("import React from 'react';\n\nexport const Camera: React.FC<{children: React.ReactNode}> = ({children}) => {\n"
                "  return <>{children}</>;\n};\n")
    if name == "Trilhas":
        return ("import React from 'react';\n\nexport const Trilhas: React.FC<{ganhoFala: number; ganhoMusica: number; ganhoSfx: number}> = () => {\n"
                "  return null;\n};\n")
    return f"import React from 'react';\n\nexport const {name}: React.FC = () => {{\n  return null;\n}};\n"


# ───────────────────────────── geração das camadas ─────────────────────────────

HEADER = "// Gerado por neuro-mv-edit (`build`) a partir de {src}. Editável no Studio: {dica}\n"


def _num(v: float) -> str:
    v = round(float(v), 4)
    return str(int(v)) if v == int(v) else f"{v:g}"


def _ease(name: str | None) -> str:
    if not name or name in ("none", "linear"):
        return "Easing.linear"
    b = EASE_BEZIER.get(name) or EASE_BEZIER.get(name.replace("power0", "power1"))
    if not b:
        return "Easing.bezier(0.25, 0.1, 0.25, 1)"
    return "Easing.bezier(" + ", ".join(_num(x) for x in b) + ")"


def gen_cortes(edl: dict, cfg: dict) -> str:
    src = edl.get("fonte") or cfg.get("mezanino", "assets/base.mp4")
    lines = [HEADER.format(src="edl.json", dica="arraste as bordas dos clipes; o `sincronizar` grava em edl.json."),
             "import React from 'react';",
             "import {staticFile} from 'remotion';",
             "import {Video} from '@remotion/media';",
             "import {TransitionSeries} from '@remotion/transitions';",
             "",
             "export const Cortes: React.FC = () => {",
             "  return (",
             '    <TransitionSeries name="Cortes">']
    for s in edl["segmentos"]:
        lines += [
            f'      <TransitionSeries.Sequence name="{s["id"]}" durationInFrames={{{int(s["out"]) - int(s["in"])}}}>',
            f"        <Video src={{staticFile('{src}')}} trimBefore={{{int(s['in'])}}} muted objectFit=\"cover\" style={{{{width: '100%', height: '100%'}}}} />",
            "      </TransitionSeries.Sequence>",
        ]
    lines += ["    </TransitionSeries>", "  );", "};", ""]
    return "\n".join(lines)


def camera_tracks(events: list[dict], fps: int) -> tuple[list, list]:
    """Eventos de câmera → trilhas de keyframes [(quadro, valor, easing do segmento que termina aqui)]."""
    scale = [[0, 1.0, None]]
    trans = [[0, (0.0, 0.0), None]]

    def add(track, f, v, ease):
        last = track[-1]
        if f < last[0]:
            f = last[0]
        if f == last[0]:
            if f == 0 or last[1] == v:
                last[1] = v
                return
            f = last[0] + 1
        track.append([f, v, ease])

    def hold(track, f, v):
        if f > track[-1][0]:
            add(track, f, v, "none")

    cur = {"scale": 1.0, "x": 0.0, "y": 0.0}
    for ev in events:
        f0 = int(round(ev["t"] * fps))
        if ev["kind"] == "shake":
            hold(trans, f0, (cur["x"], cur["y"]))
            amp = ev["amp"]
            for i, xv in enumerate([amp, -amp * 0.8, amp * 0.6, -amp * 0.4, ev["x"]]):
                add(trans, int(round((ev["t"] + ev["dur"] * (i + 1) / 5) * fps)), (xv, cur["y"]), "none")
            continue
        f1 = int(round((ev["t"] + ev["dur"]) * fps))
        instant = f1 <= f0
        to = ev["to"]
        if "scale" in to:
            a = f0 - 1 if instant else f0
            hold(scale, max(0, a), ev["from"].get("scale", cur["scale"]))
            add(scale, f0 if instant else f1, float(to["scale"]), "none" if instant else ev["ease"])
            cur["scale"] = float(to["scale"])
        if "x" in to or "y" in to:
            nx, ny = float(to.get("x", cur["x"])), float(to.get("y", cur["y"]))
            a = f0 - 1 if instant else f0
            hold(trans, max(0, a), (cur["x"], cur["y"]))
            add(trans, f0 if instant else f1, (nx, ny), "none" if instant else ev["ease"])
            cur["x"], cur["y"] = nx, ny
    return scale, trans


def _interp(track: list, fmt) -> str:
    if len(track) == 1:
        return fmt(track[0][1])
    frames = ", ".join(str(k[0]) for k in track)
    vals = ", ".join(fmt(k[1]) for k in track)
    eases = ", ".join(_ease(k[2]) for k in track[1:])
    return (f"interpolate(frame, [{frames}], [{vals}], {{\n          easing: [{eases}],\n"
            "          extrapolateLeft: 'clamp',\n          extrapolateRight: 'clamp',\n        })")


def gen_camera(cfg: dict, cues: dict, profile: dict, warns: list[str]) -> str:
    events, w = hf.camera_events(cues.get("camera", []), cfg, profile)
    warns += w
    scale, trans = camera_tracks(events, cfg["fps"])
    hx, hy = cfg["head"]["x"], cfg["head"]["y"]
    sc = _interp(scale, lambda v: _num(v))
    tr = _interp(trans, lambda v: f"'{_num(v[0])}px {_num(v[1])}px'")
    return "\n".join([
        HEADER.format(src="cues.json (camera)", dica="arraste os keyframes de scale/translate da Câmera."),
        "import React from 'react';",
        "import {Easing, Interactive, interpolate, useCurrentFrame} from 'remotion';",
        "",
        "export const Camera: React.FC<{children: React.ReactNode}> = ({children}) => {",
        "  const frame = useCurrentFrame();",
        "  return (",
        "    <Interactive.Div",
        '      name="Câmera"',
        "      style={{",
        "        position: 'absolute',",
        "        inset: 0,",
        f"        transformOrigin: '{hx}px {hy}px',",
        f"        scale: {sc},",
        f"        translate: {tr},",
        "      }}",
        "    >",
        "      {children}",
        "    </Interactive.Div>",
        "  );",
        "};",
        "",
    ])


def _ident(sid: str) -> str:
    return "cena_" + re.sub(r"[^a-zA-Z0-9]", "_", sid)


def gen_cenas(scenes: list[dict], fps: int, hf_clips: dict[str, str]) -> str:
    imports, body = [], []
    uses_cartao = uses_off = False
    for s in scenes:
        f0, fd = int(round(s["start"] * fps)), max(1, int(round(s["dur"] * fps)))
        body.append(f'      <Sequence name="{s["id"]}" from={{{f0}}} durationInFrames={{{fd}}}>')
        if s["id"] in hf_clips:
            uses_off = True
            body.append(f"        <OffthreadVideo src={{staticFile('{hf_clips[s['id']]}')}} transparent muted style={{{{width: '100%', height: '100%'}}}} />")
        else:
            uses_cartao = True
            imports.append(f"import {_ident(s['id'])} from './cartoes/{s['id']}.json';")
            body.append(f"        <CartaoGsap dados={{{_ident(s['id'])}}} />")
        body.append("      </Sequence>")
    rem = ["Sequence"] + (["OffthreadVideo", "staticFile"] if uses_off else [])
    head = [HEADER.format(src="cues.json (scenes)", dica="mova ou estique as sequências; o `sincronizar` grava em cues.json."),
            "import React from 'react';",
            "import {" + ", ".join(sorted(rem)) + "} from 'remotion';"]
    if uses_cartao:
        head.append("import {CartaoGsap} from '../lib/CartaoGsap';")
    head += imports
    return "\n".join(head + ["", "export const Cenas: React.FC = () => {", "  return (", "    <>"] + body + ["    </>", "  );", "};", ""])


def gen_trilhas(fala_rel: str | None, sfx: list[dict], music: dict | None, fps: int, total: int) -> str:
    body = []
    if fala_rel:
        body.append(f"      <Audio name=\"Fala\" src={{staticFile('{fala_rel}')}} volume={{ganhoFala}} />")
    if music:
        f0 = int(round(music["start"] * fps))
        fd = max(1, min(total - f0, int(round(music["dur"] * fps))))
        fi = max(1, int(round(music["fade_in"] * fps)))
        fo = max(1, int(round(music["fade_out"] * fps)))
        v = _num(music["volume"])
        a, b = f0 + fi, max(f0 + fi + 1, f0 + fd - fo)
        trim = int(round(music.get("media_start", 0) * fps))
        body.append(
            f"      <Audio name=\"Música\" src={{staticFile('{music['src']}')}} from={{{f0}}} durationInFrames={{{fd}}}"
            + (f" trimBefore={{{trim}}}" if trim else "")
            + f" volume={{ganhoMusica * interpolate(frame, [{f0}, {a}, {b}, {f0 + fd}], [0, {v}, {v}, 0], "
            "{extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})} />")
    for ev in sfx:
        f0 = int(round(ev["start"] * fps))
        fd = max(1, int(round(ev["dur"] * fps)))
        trim = int(round(ev["skip"] * fps))
        body.append(f"      <Audio name=\"sfx {ev['sid']} {ev['kind']}\" src={{staticFile('{ev['src']}')}} from={{{f0}}} "
                    f"durationInFrames={{{fd}}}" + (f" trimBefore={{{trim}}}" if trim else "") + f" volume={{{_num(ev['vol'])} * ganhoSfx}} />")
    uses_frame = bool(music)
    rem = ["staticFile"] + (["interpolate", "useCurrentFrame"] if uses_frame else [])
    return "\n".join([
        HEADER.format(src="edl.json + cues.json (sfx/music)", dica="mova os SFX; a fala sai do ffmpeg com fades nas emendas."),
        "import React from 'react';",
        "import {" + ", ".join(sorted(rem)) + "} from 'remotion';",
        "import {Audio} from '@remotion/media';",
        "",
        "export const Trilhas: React.FC<{ganhoFala: number; ganhoMusica: number; ganhoSfx: number}> = ({ganhoFala, ganhoMusica, ganhoSfx}) => {",
        "  const frame = useCurrentFrame();" if uses_frame else "  void ganhoMusica;",
        "  return (",
        "    <>",
    ] + body + ["    </>", "  );", "};", ""])


def gen_efeitos(cfg: dict, cues: dict, total: int) -> str:
    fps = cfg["fps"]
    body = []
    end = cues.get("end") or {}
    fade = end.get("fade_out", bool(cfg.get("rules", {}).get("final_fade_out", True)))
    for i, e in enumerate(cues.get("efeitos", []) or []):
        kind = e.get("kind", "flash")
        f0 = int(round(float(e.get("at", 0)) * fps))
        n = max(2, int(round(float(e.get("dur", 0.1)) * fps)))
        if kind == "flash":
            color, peak = e.get("cor", "#FFFFFF"), float(e.get("intensidade", 0.85))
        elif kind == "dip":
            color, peak = e.get("cor", "#000000"), float(e.get("intensidade", 0.4))
        else:
            continue
        mid = f0 + max(1, n // 3)
        body.append(
            f'      <Interactive.Div name="{kind} {i + 1}" style={{{{position: \'absolute\', inset: 0, backgroundColor: \'{color}\', '
            f"opacity: interpolate(frame, [{f0}, {mid}, {f0 + n}], [0, {_num(peak)}, 0], {{easing: [Easing.bezier(0.215, 0.61, 0.355, 1), "
            "Easing.bezier(0.55, 0.055, 0.675, 0.19)], extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})}} />")
    if fade:
        fd = max(2, int(round(float(end.get("duration", 0.6)) * fps)))
        body.append(
            "      <Interactive.Div name=\"Fade final\" style={{position: 'absolute', inset: 0, backgroundColor: 'var(--endfade)', "
            f"opacity: interpolate(frame, [{max(0, total - fd)}, {max(1, total - 1)}], [0, 1], {{easing: [Easing.bezier(0.55, 0.055, 0.675, 0.19)], "
            "extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})}} />")
    if not body:
        return _empty_layer("Efeitos.tsx")
    return "\n".join([
        HEADER.format(src="cues.json (efeitos, end)", dica="ajuste os keyframes de opacidade."),
        "import React from 'react';",
        "import {Easing, Interactive, interpolate, useCurrentFrame} from 'remotion';",
        "",
        "export const Efeitos: React.FC = () => {",
        "  const frame = useCurrentFrame();",
        "  return (",
        "    <>",
    ] + body + ["    </>", "  );", "};", ""])


def gen_broll(cfg: dict, cues: dict, proj: Path, warns: list[str]) -> str:
    fps = cfg["fps"]
    body = []
    for i, b in enumerate(cues.get("broll", []) or []):
        src = b.get("src")
        if not src or not (proj / src).exists():
            warns.append(f"B-roll {i + 1}: arquivo '{src}' não encontrado.")
            continue
        f0 = int(round(float(b.get("start", 0)) * fps))
        fd = max(1, int(round(float(b.get("duration", 2)) * fps)))
        trim = int(round(float(b.get("trim", 0)) * fps))
        body.append(f"      <Video name=\"broll {i + 1}\" src={{staticFile('{src}')}} from={{{f0}}} durationInFrames={{{fd}}} "
                    f"trimBefore={{{trim}}} muted objectFit=\"cover\" style={{{{width: '100%', height: '100%'}}}} />")
    if not body:
        return _empty_layer("Broll.tsx")
    return "\n".join([
        HEADER.format(src="cues.json (broll)", dica="mova ou apare os clipes de B-roll."),
        "import React from 'react';",
        "import {staticFile} from 'remotion';",
        "import {Video} from '@remotion/media';",
        "",
        "export const Broll: React.FC = () => {",
        "  return (",
        "    <>",
    ] + body + ["    </>", "  );", "};", ""])


def gen_legendas(has: bool) -> str:
    if not has:
        return _empty_layer("Legendas.tsx")
    return "\n".join([
        HEADER.format(src="dados/legendas.json", dica="os blocos vêm do `legendas`; corrija o texto lá."),
        "import React from 'react';",
        "import {LegendasNeuro, type DadosLegenda} from '../lib/Legendas';",
        "import dados from './legendas.json';",
        "",
        "export const Legendas: React.FC = () => {",
        "  return <LegendasNeuro dados={dados as DadosLegenda} />;",
        "};",
        "",
    ])


# ───────────────────────────── leitura do TSX (Babel) ─────────────────────────────

def node_read(proj: Path, cmd: str, file: Path) -> dict | str | None:
    r = rdir(proj)
    res = subprocess.run(["node", str(r / "neuro" / "ler.mjs"), cmd, str(file)], cwd=r, capture_output=True, text=True)
    if res.returncode != 0:
        warn(f"não consegui ler {file.name}: {res.stderr.strip()[-300:]}")
        return None
    return res.stdout if cmd == "canon" else json.loads(res.stdout)


def canon(proj: Path, path: Path) -> str | None:
    return node_read(proj, "canon", path) if path.exists() else None


def canon_text(proj: Path, text: str) -> str | None:
    tmp = rdir(proj) / "neuro" / ".canon.tsx"
    tmp.write_text(text, encoding="utf-8")
    try:
        return canon(proj, tmp)
    finally:
        tmp.unlink(missing_ok=True)


# ───────────────────────────── estado / build ─────────────────────────────

def estado_path(proj: Path) -> Path:
    return proj / ".neuro" / "estado.json"


def load_estado(proj: Path) -> dict:
    return hf.load_json(estado_path(proj), default={"camadas": {}, "fontes": {}, "cenas": {}})


def fontes_hash(proj: Path) -> str:
    return sha(proj / "edl.json") + sha(proj / "cues.json")


def load_or_identity_edl(proj: Path, cfg: dict) -> dict:
    e = edlmod.load_edl(proj)
    if e:
        return e
    q = int(cfg.get("quadros_fonte") or round(float(cfg.get("duracao_fonte", cfg["duration"])) * cfg["fps"]))
    e = edlmod.identity_edl(cfg["fps"], q, cfg.get("mezanino", "assets/base.mp4"))
    edlmod.save_edl(proj, e)
    return edlmod.load_edl(proj)


def ensure_fala(proj: Path, cfg: dict, edl: dict) -> str | None:
    """dados/fala-<hash>.wav: fala montada com precisão de amostra a partir do mezanino e do EDL."""
    if not cfg.get("video_has_audio"):
        return None
    mez = proj / cfg.get("mezanino", "assets/base.mp4")
    sig = hashlib.sha256((edlmod.edl_signature(edl) + str(mez.stat().st_mtime_ns)).encode()).hexdigest()[:10]
    out = proj / "dados" / f"fala-{sig}.wav"
    if not out.exists():
        mem = hf.load_memory()
        ms = ((mem.get("learned_preferences", {}).get(cfg["profile"], {}) or {}).get("pacing") or {}).get("crossfade_duration_ms", 20)
        edlmod.assemble_audio(mez, edl, out, fade_ms=float(ms) / 2)
        for old in (proj / "dados").glob("fala-*.wav"):
            if old != out:
                old.unlink()
    return f"dados/{out.name}"


def patch_root(proj: Path, total: int, cfg: dict | None = None):
    """Duração (e, num re-init, fps e tamanho) da composição; o resto do Root.tsx é do Studio."""
    root = rdir(proj) / "src" / "Root.tsx"
    txt = root.read_text(encoding="utf-8")
    new = re.sub(r"(durationInFrames=\{)\d+(\})", rf"\g<1>{max(1, total)}\g<2>", txt, count=1)
    if cfg:
        for attr, val in (("fps", cfg["fps"]), ("width", cfg["width"]), ("height", cfg["height"])):
            new = re.sub(rf"(\b{attr}=\{{)\d+(\}})", rf"\g<1>{int(val)}\g<2>", new, count=1)
    if new != txt:
        root.write_text(new, encoding="utf-8")


def changed_layers(proj: Path, est: dict) -> list[str]:
    out = []
    for layer in LAYERS:
        p = gdir(proj) / layer
        h = est.get("camadas", {}).get(layer)
        if h and p.exists() and sha(p) != h:
            out.append(layer)
    return out


def build(proj: Path, force: bool = False, origem: str = "build", quiet: bool = False, regravar: set[str] | None = None) -> dict:
    cfg = hf.load_json(proj / "neuro.json")
    if not (rdir(proj) / "node_modules").exists():
        scaffold(proj, cfg)
    est = load_estado(proj)
    regravar = regravar or set()
    new_edits = changed_layers(proj, est)
    # camadas que já eram do Studio continuam do Studio até um `build --force`
    owned = set(new_edits) | {l for l in est.get("mantidas_do_studio", []) if l in LAYERS}
    json_changed = bool(est.get("fontes_hash")) and fontes_hash(proj) != est["fontes_hash"]
    if origem == "build" and not force:
        synced_edits = [l for l in new_edits if l in SYNCED]
        if synced_edits:
            if json_changed:
                hf.die("Conflito: " + ", ".join(synced_edits) + " foi editado no Studio E edl.json/cues.json mudaram desde o último build.\n"
                       "  `sincronizar` fica com o Studio (descarta as mudanças nos JSON); `build --force` fica com os JSON (descarta o Studio).")
            say("edições do Studio encontradas em " + ", ".join(synced_edits) + " → sincronizando antes do build")
            return sincronizar(proj, quiet=quiet)
    edited = owned

    profile = hf.profile_for(cfg)
    cues = hf.load_json(proj / "cues.json")
    edl = load_or_identity_edl(proj, cfg)
    fps = cfg["fps"]
    total = edlmod.total_frames(edl)
    D = total / fps
    if abs(float(cfg["duration"]) - D) > 1e-6:
        cfg["duration"] = hf.r3(D)
        hf.save_json(proj / "neuro.json", cfg)
    warns: list[str] = []
    F = 1.0 / fps

    fala = ensure_fala(proj, cfg, edl)
    fixed = proj / "assets" / "transcript.fixed.json"
    if fixed.exists():
        hf.emit_captions(proj, cfg, hf.load_json(fixed), None, False, quiet=True)
    lg = proj / "dados" / "legendas.json"
    has_leg = lg.exists() and bool(hf.load_json(lg).get("grupos")) and (hf.load_json(lg).get("queimar", True))
    if lg.exists():
        shutil.copy2(lg, gdir(proj) / "legendas.json")

    scenes, sfx_events = hf.build_scenes(cfg, cues, warns)
    cart = gdir(proj) / "cartoes"
    cart.mkdir(parents=True, exist_ok=True)
    keep = set()
    hf_clips = {}
    for s in scenes:
        if s.get("motor") == "hyperframes" or s.get("html"):
            rel = render_hf_card(proj, cfg, s)
            if rel:
                hf_clips[s["id"]] = rel
                continue
        hf.save_json(cart / f"{s['id']}.json", hf.scene_payload(s["scene"]))
        keep.add(f"{s['id']}.json")
    for old in cart.glob("*.json"):
        if old.name not in keep:
            old.unlink()

    sfx = hf.place_sfx(proj, cues, sfx_events, D, F, warns)
    music = hf.music_track(proj, cues, D, warns, (proj / fala) if fala else None, default_volume=hf.estilo_music_volume(cfg))

    texts = {
        "Cortes.tsx": gen_cortes(edl, cfg),
        "Camera.tsx": gen_camera(cfg, cues, profile, warns),
        "Cenas.tsx": gen_cenas(scenes, fps, hf_clips),
        "Trilhas.tsx": gen_trilhas(fala, sfx, music, fps, total),
        "Efeitos.tsx": gen_efeitos(cfg, cues, total),
        "Broll.tsx": gen_broll(cfg, cues, proj, warns),
        "Legendas.tsx": gen_legendas(has_leg),
    }
    kept = []
    for layer, text in texts.items():
        p = gdir(proj) / layer
        if layer in edited and not force:
            # do Studio: igual na árvore sintática → nada a fazer; remapeada pelo sincronizar → regrava; senão mantém
            a, b = canon(proj, p), canon_text(proj, text)
            if a and b and a == b:
                continue
            if layer not in regravar:
                kept.append(layer)
                continue
        if not p.exists() or p.read_text(encoding="utf-8") != text:
            p.write_text(text, encoding="utf-8")
    patch_root(proj, total, cfg)

    est = {"camadas": {l: sha(gdir(proj) / l) for l in LAYERS}, "fontes_hash": fontes_hash(proj), "fontes": {"edl": sha(proj / "edl.json"), "cues": sha(proj / "cues.json")},
           "cenas": {s["id"]: [int(round(s["start"] * fps)), max(1, int(round(s["dur"] * fps)))] for s in scenes},
           "entradas": {s["id"]: hf.r3(s["scene"].entrance_end) for s in scenes},
           "build_em": datetime.now().isoformat(timespec="seconds"), "origem": origem, "remotion": REMOTION_VERSION}
    if kept:
        est["mantidas_do_studio"] = kept
    hf.save_json(estado_path(proj), est)
    if not quiet:
        print(f"✓ build Remotion: {len(edl['segmentos'])} clipes · {D:.2f}s · {len(scenes)} cenas ({len(hf_clips)} pelo HyperFrames) · "
              f"{len(sfx)} SFX · música {'com ducking' if music and music.get('ducked') else ('sim' if music else 'não')} · "
              f"legendas {'sim' if has_leg else 'não'}")
        for layer in kept:
            extra = " (as mudanças recentes nos JSON NÃO entraram nesta camada)" if json_changed else ""
            warn(f"{layer} tem edições do Studio: mantive o seu arquivo{extra}. `build --force` regera a partir dos JSON.")
        for w in warns:
            warn(w)
    return {"duration": D, "frames": total, "scenes": len(scenes), "warns": warns, "kept": kept}


def sincronizar(proj: Path, quiet: bool = False) -> dict:
    """Studio → JSON: cortes (Cortes.tsx → edl.json) e tempos de cena (Cenas.tsx → cues.json); depois regera o resto."""
    cfg = hf.load_json(proj / "neuro.json")
    est = load_estado(proj)
    fps = cfg["fps"]
    edl = load_or_identity_edl(proj, cfg)
    cues = hf.load_json(proj / "cues.json")
    notes = []
    old_edl = json.loads(json.dumps(edl))
    edl_changed = False
    cortes = gdir(proj) / "Cortes.tsx"
    if cortes.exists() and sha(cortes) != est.get("camadas", {}).get("Cortes.tsx"):
        data = node_read(proj, "cortes", cortes)
        if data and data.get("clipes"):
            segs, seen = [], set()
            for i, c in enumerate(data["clipes"]):
                if c.get("durationInFrames") is None:
                    continue
                cid = str(c.get("name") or f"c{i + 1:02d}")
                while cid in seen:
                    cid += "b"
                seen.add(cid)
                tb = int(c.get("trimBefore") or 0)
                segs.append({"id": cid, "in": tb, "out": tb + int(c["durationInFrames"]), "motivo": "Studio"})
            if [(s["in"], s["out"]) for s in segs] != [(int(s["in"]), int(s["out"])) for s in edl["segmentos"]]:
                prev = {s["id"]: s.get("motivo") for s in edl["segmentos"]}
                for s in segs:
                    s["motivo"] = prev.get(s["id"], "Studio")
                edl["segmentos"] = segs
                edl["editado_no_studio"] = datetime.now().isoformat(timespec="seconds")
                edlmod.save_edl(proj, edl)
                edl = edlmod.load_edl(proj)
                edl_changed = True
                notes.append(f"cortes do Studio → edl.json ({edlmod.describe(edl)})")
    moved = set()
    cenas = gdir(proj) / "Cenas.tsx"
    if cenas.exists() and sha(cenas) != est.get("camadas", {}).get("Cenas.tsx"):
        data = node_read(proj, "cenas", cenas)
        gen = est.get("cenas", {})
        # o build normaliza os ids ("Hook_1" → "hook-1"); o Studio mostra o normalizado
        by_id = {re.sub(r"[^a-z0-9-]", "-", str(sc.get("id", "")).lower()).strip("-"): sc for sc in cues.get("scenes", [])}
        for c in (data or {}).get("cenas", []):
            sid = c.get("name")
            if sid in by_id and c.get("durationInFrames") is not None:
                now = [int(c.get("from") or 0), int(c["durationInFrames"])]
                if gen.get(sid) != now:
                    by_id[sid]["start"] = hf.r3(now[0] / fps)
                    by_id[sid]["duration"] = hf.r3(now[1] / fps)
                    moved.add(sid)
        if moved:
            notes.append("cenas movidas no Studio → cues.json: " + ", ".join(sorted(moved)))
    if edl_changed:
        cues, n2 = edlmod.remap_cues(cues, old_edl, edl, keep_scene_ids=moved)
        notes += n2
        if "Camera.tsx" in changed_layers(proj, est):
            notes.append("Camera.tsx foi editada no Studio: os keyframes dela não acompanham o novo corte — confira a câmera.")
    if edl_changed or moved:
        hf.save_json(proj / "cues.json", cues)
    if not quiet:
        for n in notes:
            say(n)
        if not notes:
            say("nada para sincronizar: Studio e JSON já batem.")
    # Cortes/Cenas que só mudaram de tempo batem com a versão gerada; Cenas é regravada quando o corte a remapeou.
    # Edições a mais (efeitos soltos num clipe etc.) fazem a camada ficar como está, com aviso.
    regravar = {"Cenas.tsx"} if edl_changed else set()
    res = build(proj, origem="sync", quiet=quiet, regravar=regravar)
    res["notas"] = notes
    return res


# ───────────────────────────── cartões pelo HyperFrames (alfa) ─────────────────────────────

HF_INDEX = """<!doctype html>
<html lang="pt-BR">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width={W}, height={H}" />
    <script src="{gsap}"></script>
    <link rel="stylesheet" href="assets/neuro-theme.css" />
    <link rel="stylesheet" href="assets/neuro-components.css" />
    <style>
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{ margin: 0; width: {W}px; height: {H}px; overflow: hidden; background: transparent; }}
      #root {{ position: relative; width: 100%; height: 100%; overflow: hidden; background: transparent; }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{D}" data-width="{W}" data-height="{H}">
      <div id="{cid}" data-composition-id="{cid}" data-composition-src="compositions/{file}" data-start="0" data-duration="{D}" data-track-index="1" data-width="{W}" data-height="{H}"></div>
    </div>
    <script>
      const tl = gsap.timeline({{ paused: true }});
      window.__timelines["main"] = tl;
    </script>
  </body>
</html>
"""


def render_hf_card(proj: Path, cfg: dict, s: dict) -> str | None:
    """Cena com "motor": "hyperframes" (ou "html": composição própria/bloco do registry) → ProRes 4444 com alfa."""
    W, H = cfg["width"], cfg["height"]
    sid, dur = s["id"], s["dur"]
    if s.get("html"):
        src = (proj / s["html"]).resolve()
        if not src.exists():
            warn(f"cena {sid}: html '{s['html']}' não encontrado — usando o cartão nativo.")
            return None
        html = src.read_text(encoding="utf-8")
        m = re.search(r'data-composition-id="([^"]+)"', html)
        cid = m.group(1) if m else sid
    else:
        html = hf.render_scene_file(s["scene"], W, H)
        cid = sid
    theme = (proj / "assets" / "neuro-theme.css").read_text(encoding="utf-8")
    # o cartão sai na maior escala inteira que a exportação pede (2x para 1440p/4K): não perde nitidez no supersampling
    import neuro_export as nx
    try:
        k = 2 if max(sd["escala"] for sd in nx.plano_projeto(cfg)["saidas"]) > 1 + 1e-6 else 1
    except (ValueError, KeyError):
        k = 1
    preset = nx.hf_resolucao(W, H, {"largura": W * k, "altura": H * k}) if k == 2 else None
    h = hashlib.sha256((html + theme + hf.HF_VERSION + f"{dur}:{W}x{H}@{k}").encode()).hexdigest()[:10]
    out_dir = proj / "cartoes-hf"
    out_dir.mkdir(exist_ok=True)
    out = out_dir / f"{sid}-{h}.mov"
    if out.exists():
        return f"cartoes-hf/{out.name}"
    work = proj / ".neuro" / "hf-cartoes" / sid
    if work.exists():
        shutil.rmtree(work)
    (work / "compositions").mkdir(parents=True)
    _symlink(work / "assets", proj / "assets")
    (work / "compositions" / f"{sid}.html").write_text(html, encoding="utf-8")
    hf.save_json(work / "hyperframes.json", {"$schema": "https://hyperframes.heygen.com/schema/hyperframes.json",
                                             "paths": {"blocks": "compositions", "components": "compositions/components", "assets": "assets"}})
    (work / "index.html").write_text(HF_INDEX.format(W=W, H=H, D=hf.r3(dur), cid=cid, file=f"{sid}.html", gsap=hf.GSAP_URL), encoding="utf-8")
    print(f"▶ HyperFrames → cartão {sid} com alfa (ProRes 4444)")
    res = subprocess.run(hf.hf_cmd("render", "--format", "mov", "--quality", "delivery", "--fps", str(cfg["fps"]), "-o", str(out),
                                   *(["--resolution", preset] if preset else [])),
                         cwd=str(work), env=hf.hf_env(), capture_output=True, text=True)
    if res.returncode != 0 or not out.exists():
        warn(f"cena {sid}: o render do HyperFrames falhou — usando o cartão nativo.\n{(res.stderr or res.stdout)[-600:]}")
        return None
    pix = hf.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=pix_fmt", "-of", "csv=p=0", str(out)]).stdout.strip()
    if "a" not in pix.replace("yuv", "").replace("p10le", ""):
        warn(f"cena {sid}: o .mov saiu sem alfa ({pix}).")
    for old in out_dir.glob(f"{sid}-*.mov"):
        if old != out:
            old.unlink()
    return f"cartoes-hf/{out.name}"


# ───────────────────────────── Studio ─────────────────────────────

def _alive(pid: int | None) -> bool:
    if not pid:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _http_ok(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=2) as r:
            return r.status < 500
    except Exception:
        return False


def _free_port(start: int = 3000) -> int:
    for p in range(start, start + 200):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", p))
                return p
            except OSError:
                continue
    hf.die("Nenhuma porta livre entre 3000 e 3199.")


def studio_state(proj: Path) -> dict:
    return hf.load_json(proj / ".neuro" / "studio.json", default={})


def open_url(url: str):
    opener = "open" if sys.platform == "darwin" else ("xdg-open" if shutil.which("xdg-open") else None)
    if opener:
        subprocess.Popen([opener, url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def studio_start(proj: Path, abrir: bool = True, porta: int | None = None, watcher_cmd: list[str] | None = None) -> str:
    st = studio_state(proj)
    if st and _alive(st.get("pid")) and _http_ok(st.get("base", "")):
        print(f"✓ Studio já está aberto: {st['url']}")
        if abrir:
            open_url(st["url"])
        return st["url"]
    port = porta or _free_port(3000)
    (proj / ".neuro").mkdir(exist_ok=True)
    log = open(proj / ".neuro" / "studio.log", "w", encoding="utf-8")
    env = dict(os.environ, BROWSER="none")
    p = subprocess.Popen([str(rdir(proj) / "node_modules" / ".bin" / "remotion"), "studio", "src/index.ts", "--no-open", f"--port={port}"],
                         cwd=rdir(proj), stdout=log, stderr=subprocess.STDOUT, start_new_session=True, env=env)
    base = f"http://localhost:{port}"
    t0 = time.time()
    while time.time() - t0 < 120:
        if p.poll() is not None:
            hf.die(f"O Studio encerrou ao iniciar. Veja {proj / '.neuro' / 'studio.log'}")
        if _http_ok(base):
            break
        time.sleep(0.5)
    else:
        hf.die(f"O Studio não respondeu em 2 min. Veja {proj / '.neuro' / 'studio.log'}")
    url = f"{base}/{COMP_ID}"
    vpid = None
    if watcher_cmd:
        vlog = open(proj / ".neuro" / "vigia.log", "a", encoding="utf-8")
        vpid = subprocess.Popen(watcher_cmd, stdout=vlog, stderr=subprocess.STDOUT, start_new_session=True).pid
    hf.save_json(proj / ".neuro" / "studio.json", {"pid": p.pid, "porta": port, "base": base, "url": url, "vigia_pid": vpid,
                                                   "iniciado_em": datetime.now().isoformat(timespec="seconds")})
    print(f"✓ Remotion Studio: {url}  (PID {p.pid}{f', vigia {vpid}' if vpid else ''})")
    print("  edições no Studio são gravadas nos arquivos; o vigia sincroniza edl.json/cues.json e faz checkpoint.")
    if abrir:
        open_url(url)
    return url


def studio_stop(proj: Path):
    st = studio_state(proj)
    for key in ("vigia_pid", "pid"):
        pid = st.get(key)
        if _alive(pid):
            try:
                os.killpg(os.getpgid(pid), signal.SIGTERM)
            except OSError:
                pass
    if st:
        (proj / ".neuro" / "studio.json").unlink(missing_ok=True)
        print("✓ Studio encerrado.")
    else:
        print("  nenhum Studio aberto para este projeto.")


# ───────────────────────────── render / stills / check ─────────────────────────────

def render(proj: Path, quality: str = "delivery", output: str | None = None, extra: list[str] | None = None,
           resolucao: str | None = None, codec: str | None = None, qualidade: str | None = None) -> list[Path]:
    """Render nas resoluções e no codec decididos (neuro.json → export).

    A composição fica nas coordenadas do layout (1080 no lado curto); `--scale` faz o supersampling: o navegador
    desenha texto, gráficos e o vídeo do mezanino na resolução final. Entrega captura PNG por quadro (sem perda)
    e codifica uma única vez."""
    import neuro_export as nx
    build(proj, quiet=True)
    cfg = hf.load_json(proj / "neuro.json")
    profiles, *_ = hf.load_presets()
    profile = profiles.get(cfg["profile"], {})
    stamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    binr = str(rdir(proj) / "node_modules" / ".bin" / "remotion")
    lic = [f"--license-key={os.environ['REMOTION_LICENSE_KEY']}"] if os.environ.get("REMOTION_LICENSE_KEY") else []
    if quality == "draft":
        out = Path(output).expanduser() if output else proj / "renders" / f"{proj.name}_{stamp}_rascunho.mp4"
        out = out if out.is_absolute() else proj / out
        out.parent.mkdir(parents=True, exist_ok=True)
        args = [binr, "render", "src/index.ts", COMP_ID, str(out), "--codec=h264", "--pixel-format=yuv420p", "--audio-codec=aac",
                "--scale=0.5", "--crf=28", "--jpeg-quality=80", f"--concurrency={max(1, min(8, (os.cpu_count() or 4) // 2))}"]
        _roda_render(proj, args + lic + (extra or []))
        _confere(proj, cfg, out)
        _registra(proj, [{"resolucao": "rascunho", "arquivo": str(out)}])
        return [out]
    try:
        pl = nx.plano_projeto(cfg, profile, resolucao, codec, qualidade)
    except ValueError as e:
        hf.die(str(e))
    for av in pl["avisos"]:
        warn(av)
    base = Path(output).expanduser() if output else proj / "renders" / f"{proj.name}_{stamp}{pl['ext']}"
    base = base if base.is_absolute() else proj / base
    base.parent.mkdir(parents=True, exist_ok=True)
    feitos, saidas = [], []
    for i, saida in enumerate(pl["saidas"]):
        out = nx.nome_saida(base, saida, i == 0, pl["ext"])
        teto = 3 if saida["escala"] >= 1.9 else 8  # 4K: cada aba do Chrome segura um quadro grande na memória
        conc = max(1, min(teto, (os.cpu_count() or 4) // 2))
        print(f"▶ {saida['resolucao']} {saida['largura']}x{saida['altura']} · {pl['codec_nome']}"
              + (f" · CRF {pl['crf']}" if pl["crf"] is not None else "") + f" · {cfg['fps']} fps")
        args = [binr, "render", "src/index.ts", COMP_ID, str(out), f"--concurrency={conc}"] + nx.args_remotion(pl, saida, quality)
        _roda_render(proj, args + lic + (extra or []))
        _confere(proj, cfg, out)
        feitos.append({"resolucao": saida["resolucao"], "arquivo": str(out), "largura": saida["largura"], "altura": saida["altura"],
                       "codec": pl["codec"]})
        saidas.append(out)
    _registra(proj, feitos)
    return saidas


def _roda_render(proj: Path, args: list[str]) -> None:
    shown = [x if not x.startswith("--license-key=") else "--license-key=***" for x in args[1:]]
    print("  remotion " + " ".join(shown))
    res = subprocess.run(args, cwd=rdir(proj))
    if res.returncode != 0:
        sys.exit(res.returncode)


def _confere(proj: Path, cfg: dict, out: Path) -> None:
    if not out.exists() or out.stat().st_size < 1000:
        hf.die(f"Render terminou mas {out} está vazio.")
    import neuro_export as nx
    nx.corrige_tag_hevc(out)
    mi = hf.media_info(out)
    if abs(mi["duration"] - float(cfg["duration"])) > 2.0 / cfg["fps"] + 0.03:
        warn(f"duração renderizada {mi['duration']:.3f}s ≠ projeto {cfg['duration']:.3f}s")
    print(f"✓ render: {out} ({mi['width']}x{mi['height']} · {mi['codec']} {mi.get('pix_fmt')} · {mi['duration']:.2f}s)")


def _registra(proj: Path, feitos: list[dict]) -> None:
    st = hf.load_json(proj / ".neuro-build.json", default={})
    st["last_render"] = feitos[0]["arquivo"]
    st["last_renders"] = feitos
    hf.save_json(proj / ".neuro-build.json", st)


def stills(proj: Path, escala: float = 0.5, extra_frames: list[int] | None = None) -> Path:
    build(proj, quiet=True)
    cfg = hf.load_json(proj / "neuro.json")
    fps = cfg["fps"]
    est = load_estado(proj)
    spec = []
    for sid, (f0, fd) in est.get("cenas", {}).items():
        land = float(est.get("entradas", {}).get(sid, 0.6))
        spec.append(f"{sid}:{f0 + min(fd - 2, int(round((land + 0.35) * fps)))}")
    total = int(round(float(cfg["duration"]) * fps))
    spec += [f"inicio:{min(total - 1, int(0.4 * fps))}", f"meio:{total // 2}", f"fim:{max(0, total - int(1.0 * fps))}"]
    spec += [f"q{f}:{f}" for f in (extra_frames or [])]
    out = proj / "renders" / "stills" / datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    out.mkdir(parents=True, exist_ok=True)
    res = subprocess.run(["node", str(rdir(proj) / "neuro" / "stills.mjs"), str(out), ",".join(spec), str(escala)], cwd=rdir(proj))
    if res.returncode != 0:
        sys.exit(res.returncode)
    print(f"✓ stills em {out}")
    return out


def check(proj: Path) -> int:
    res = build(proj, quiet=False)
    print("▶ conferindo o bundle (remotion compositions)")
    r = subprocess.run([str(rdir(proj) / "node_modules" / ".bin" / "remotion"), "compositions", "src/index.ts", "--quiet"],
                       cwd=rdir(proj), capture_output=True, text=True)
    ok = r.returncode == 0 and COMP_ID in (r.stdout + r.stderr)
    print(("✓ bundle compila: " + COMP_ID) if ok else ("✗ o bundle não compila:\n" + (r.stderr or r.stdout)[-2000:]))
    if res["warns"]:
        print(f"  {len(res['warns'])} aviso(s) do build acima.")
    return 0 if ok else 1

#!/usr/bin/env python3
"""
hf_project.py — Ponte Neuro MV Edit → HyperFrames (HTML renderizado em vídeo).

Transforma perfil + tema + plataforma da skill num projeto HyperFrames editável,
gera cenas gráficas, câmera, SFX e legendas a partir de um roteiro de deixas
(`cues.json`) e finaliza o master com loudness da skill.

Subcomandos:
  init      Cria o projeto (fontes, tokens do tema, vídeo base com GOP/grade, neuro.json, cues.json)
  captions  transcript.json → compositions/captions.html + captions.srt (regras do perfil)
  build     cues.json → index.html + compositions/<cena>.html + SFX alinhados por pico
  check     `hyperframes check` com a faixa de legenda e o frame-check da plataforma
  snapshot  `hyperframes snapshot` (padrão: --review)
  preview   `hyperframes preview`
  render    `hyperframes render` com CRF do perfil e versão pinada
  master    Loudness EBU R128 em 2 passagens, cópia leve, relatório de medição

Uso rápido:
  python3 scripts/hf_project.py init --profile exemplo_juridico --video bruto.mp4 --out projetos/cpr
  npx hyperframes transcribe assets/base.mp4 --model small --language pt   (dentro do projeto)
  python3 scripts/hf_project.py captions --project projetos/cpr --fix "exédulas=cédulas"
  (edite projetos/cpr/cues.json)
  python3 scripts/hf_project.py build --project projetos/cpr
  python3 scripts/hf_project.py check --project projetos/cpr
  python3 scripts/hf_project.py render --project projetos/cpr
  python3 scripts/hf_project.py master --project projetos/cpr --network reels

Somente biblioteca padrão do Python 3.10+. Requer ffmpeg/ffprobe e Node 22+ (npx).
"""

from __future__ import annotations

import argparse
import array
import hashlib
import html
import json
import math
import os
import re
import shutil
import subprocess
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
# `python3 -I` não põe a pasta do script no sys.path: os módulos irmãos (neuro_edl, neuro_remotion) ficam aqui
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
PRESETS = SKILL_ROOT / "presets"
TEMPLATE_DIR = SKILL_ROOT / "references" / "hyperframes-template"
MEMORY_PATH = SKILL_ROOT / "data" / "memory.json"  # memória que vem com a skill (glossários + base); só leitura

HF_VERSION = os.environ.get("NEURO_HF_VERSION", "0.9.19")
GSAP_URL = "https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js"
SKILL_VERSION = "1.10.0"

FONT_DIRS = [
    Path.home() / "Library" / "Fonts",
    Path("/Library/Fonts"),
    SKILL_ROOT / "assets" / "fonts",
    Path.home() / ".local" / "share" / "fonts",
]

# família → [(arquivo, faixa de peso, estilo)] — arquivos instalados por scripts/verify-env.py
FONT_FILES = {
    "Big Shoulders Display": [("BigShouldersDisplay-Black.ttf", "100 900", "normal")],
    "Fraunces": [("Fraunces.ttf", "100 900", "normal"), ("Fraunces-Italic.ttf", "100 900", "italic")],
    "Inter": [("Inter-VariableFont.ttf", "100 900", "normal")],
    "Cal Sans": [("CalSans-SemiBold.ttf", "600", "normal")],
    "Instrument Serif": [("InstrumentSerif-Regular.ttf", "400", "normal"), ("InstrumentSerif-Italic.ttf", "400", "italic")],
    "DM Sans": [("DMSans-VariableFont.ttf", "100 1000", "normal"), ("DMSans-Italic-VariableFont.ttf", "100 1000", "italic")],
    "Plus Jakarta Sans": [("PlusJakartaSans-VariableFont.ttf", "200 800", "normal"), ("PlusJakartaSans-Italic-VariableFont.ttf", "200 800", "italic")],
    "Space Grotesk": [("SpaceGrotesk-VariableFont.ttf", "300 700", "normal")],
}

WEIGHT_NAMES = {
    "thin": 100, "hairline": 100, "extralight": 200, "ultralight": 200, "light": 300,
    "regular": 400, "normal": 400, "book": 400, "medium": 500, "semibold": 600, "demibold": 600,
    "bold": 700, "extrabold": 800, "ultrabold": 800, "black": 900, "heavy": 900,
}

PT_FUNCTION_WORDS = {
    "a", "o", "as", "os", "e", "de", "da", "do", "das", "dos", "em", "no", "na", "nos", "nas", "um", "uma",
    "que", "com", "por", "para", "pra", "ao", "aos", "se", "sem", "sua", "seu", "the", "of", "to", "and",
}

# largura média do glifo (em) por família — estimativa para caber na faixa acima da cabeça
FONT_WIDTH_EM = {
    "Big Shoulders Display": 0.41, "Fraunces": 0.52, "Inter": 0.57, "Cal Sans": 0.56, "Instrument Serif": 0.44,
    "DM Sans": 0.56, "Plus Jakarta Sans": 0.57, "Space Grotesk": 0.56,
}

SFX_KINDS = ("whoosh", "pop", "click", "thud", "tick", "swipe")
SFX_FALLBACK = {"swipe": "whoosh", "click": "pop", "thud": "pop", "tick": None, "pop": "click", "whoosh": "swipe"}
SFX_GAIN_DB = {"whoosh": -16.0, "swipe": -16.0, "pop": -14.0, "click": -14.0, "thud": -12.0, "tick": -20.0}


# ───────────────────────────── utilidades ─────────────────────────────

def die(msg: str, code: int = 1):
    print(f"✗ {msg}", file=sys.stderr)
    sys.exit(code)


def info(msg: str):
    print(f"  {msg}")


def load_json(path: Path, default=None):
    if not path.exists():
        if default is not None:
            return default
        die(f"Arquivo não encontrado: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, path)


def r3(x: float) -> float:
    return round(float(x) + 0.0, 3)


def esc(s) -> str:
    return html.escape(str(s), quote=True)


def js(v) -> str:
    return json.dumps(v, ensure_ascii=False)


def norm_token(s: str) -> str:
    s = unicodedata.normalize("NFD", s.lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^\w%$]+", "", s)


def run(cmd, cwd=None, capture=True, check=False, env=None):
    res = subprocess.run(cmd, cwd=cwd, capture_output=capture, text=True, env=env)
    if check and res.returncode != 0:
        die(f"Falhou: {' '.join(map(str, cmd))}\n{(res.stderr or '')[-1500:]}")
    return res


def hf_cmd(*args) -> list[str]:
    return ["npx", "--yes", f"hyperframes@{HF_VERSION}", *map(str, args)]


def hf_env():
    env = dict(os.environ)
    env.setdefault("HYPERFRAMES_NO_UPDATE_CHECK", "1")
    return env


# ───────────────────────────── ffmpeg / ffprobe ─────────────────────────────

def ffprobe_json(path: Path) -> dict:
    res = run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)])
    if res.returncode != 0:
        die(f"ffprobe não conseguiu ler {path}: {res.stderr.strip()[:300]}")
    return json.loads(res.stdout)


def media_info(path: Path) -> dict:
    d = ffprobe_json(path)
    v = next((s for s in d["streams"] if s.get("codec_type") == "video"), None)
    a = next((s for s in d["streams"] if s.get("codec_type") == "audio"), None)
    dur = float(d["format"].get("duration") or 0)
    fps = None
    if v and v.get("avg_frame_rate") and v["avg_frame_rate"] != "0/0":
        n, den = v["avg_frame_rate"].split("/")
        fps = float(n) / float(den or 1)
    rotation = 0
    if v:
        for sd in v.get("side_data_list", []) or []:
            if "rotation" in sd:
                rotation = int(sd["rotation"])
        rotation = int((v.get("tags") or {}).get("rotate", rotation))
    return {
        "duration": dur,
        "has_video": v is not None,
        "has_audio": a is not None,
        "width": int(v["width"]) if v else 0,
        "height": int(v["height"]) if v else 0,
        "fps": fps,
        "codec": v.get("codec_name") if v else None,
        "pix_fmt": v.get("pix_fmt") if v else None,
        "color_transfer": v.get("color_transfer") if v else None,
        "rotation": rotation,
    }


def keyframe_max_gap(path: Path, probe_seconds: float = 24.0) -> float:
    res = run([
        "ffprobe", "-v", "error", "-select_streams", "v:0", "-skip_frame", "nokey",
        "-read_intervals", f"%+{probe_seconds}", "-show_entries", "frame=pts_time", "-of", "csv=p=0", str(path),
    ])
    times = []
    for line in res.stdout.splitlines():
        line = line.strip().strip(",")
        try:
            times.append(float(line))
        except ValueError:
            pass
    if len(times) < 2:
        return probe_seconds
    times.sort()
    return max(b - a for a, b in zip(times, times[1:]))


def audio_peak_offset(path: Path) -> tuple[float, float]:
    """(segundo do pico, duração) de um arquivo de áudio — para alinhar o SFX à imagem."""
    sr = 22050
    res = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(sr), "-f", "s16le", "-"],
        capture_output=True,
    )
    if res.returncode != 0 or not res.stdout:
        return 0.0, 0.0
    samples = array.array("h")
    samples.frombytes(res.stdout[: len(res.stdout) // 2 * 2])
    if not samples:
        return 0.0, 0.0
    peak_i, peak_v = 0, 0
    for i, s in enumerate(samples):
        a = s if s >= 0 else -s
        if a > peak_v:
            peak_v, peak_i = a, i
    return peak_i / sr, len(samples) / sr


def measure_loudness(path: Path) -> dict:
    res = run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af", "ebur128=peak=true", "-f", "null", "-"])
    txt = res.stderr
    out = {}
    m = re.findall(r"I:\s+(-?[\d.]+) LUFS", txt)
    if m:
        out["integrated_lufs"] = float(m[-1])
    m = re.findall(r"LRA:\s+(-?[\d.]+) LU", txt)
    if m:
        out["lra_lu"] = float(m[-1])
    m = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", txt)
    if m:
        out["true_peak_dbtp"] = float(m[-1])
    return out


# ───────────────────────────── presets ─────────────────────────────

def neuro_home() -> Path:
    return Path(os.environ.get("NEURO_HOME") or (Path.home() / ".neuro-mv-edit")).expanduser()


def user_library(kind_dir: str) -> dict:
    """Itens da biblioteca do usuário (~/.neuro-mv-edit/<perfis|temas|estilos>/<id>.json): sobrevivem às atualizações da skill."""
    out = {}
    d = neuro_home() / kind_dir
    if d.is_dir():
        for f in sorted(d.glob("*.json")):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
            except (OSError, ValueError) as e:
                print(f"  ⚠ {f} ignorado: {e}", file=sys.stderr)
                continue
            if isinstance(data, dict):
                out[data.get("id") or f.stem] = data
    return out


def load_estilos() -> dict:
    estilos = dict(load_json(PRESETS / "estilos.json", default={"estilos": {}}).get("estilos", {}))
    estilos.update(user_library("estilos"))
    return estilos


def apply_estilo(profile: dict, estilo: dict | None) -> dict:
    """Perfil com o estilo de edição aplicado (legenda e câmera); o resto do estilo é lido do neuro.json."""
    if not estilo:
        return profile
    p = json.loads(json.dumps(profile))
    leg = estilo.get("legendas") or {}
    t = p.setdefault("typography", {})
    if leg.get("animacao"):
        t["subtitles_animation"] = leg["animacao"]
    if leg.get("palavras_por_linha"):
        t["subtitles_max_words_per_line"] = int(leg["palavras_por_linha"])
    cam = estilo.get("camera") or {}
    fz = p.setdefault("framing_and_zoom", {})
    if cam.get("punch_in"):
        fz["punch_in_factor"] = float(cam["punch_in"])
    if cam.get("zoom_sutil"):
        fz["zoom_subtle_factor"] = float(cam["zoom_sutil"])
    return p


def load_presets():
    profiles = dict(load_json(PRESETS / "profiles.json")["profiles"])
    themes = dict(load_json(PRESETS / "themes.json")["themes"])
    profiles.update(user_library("perfis"))
    themes.update(user_library("temas"))
    platforms = load_json(PRESETS / "platforms.json")["platforms"]
    animations = load_json(PRESETS / "animations.json")
    estilos = None
    for pid, prof in list(profiles.items()):
        if isinstance(prof, dict) and prof.get("estilo_padrao"):
            estilos = estilos if estilos is not None else load_estilos()
            if prof["estilo_padrao"] in estilos:
                profiles[pid] = apply_estilo(prof, estilos[prof["estilo_padrao"]])
    return profiles, themes, platforms, animations


def profile_for(cfg: dict) -> dict:
    """Perfil do projeto com o estilo escolhido no `init` (o neuro.json guarda o estilo inteiro)."""
    profiles, *_ = load_presets()
    return apply_estilo(profiles.get(cfg["profile"], {}), cfg.get("estilo"))


def parse_font_spec(spec: str | None, default_family="Inter", default_weight=700):
    """'Cal Sans SemiBold' → ('Cal Sans', 600, 'normal')"""
    if not spec:
        return default_family, default_weight, "normal"
    words = spec.strip().split()
    weight, style = None, "normal"
    while words:
        w = words[-1].lower().replace("-", "")
        if w == "italic":
            style = "italic"
            words.pop()
        elif w in WEIGHT_NAMES:
            weight = WEIGHT_NAMES[w] if weight is None else weight
            words.pop()
        elif w.isdigit():
            weight = int(w)
            words.pop()
        else:
            break
    family = " ".join(words) or default_family
    return family, weight or default_weight, style


def font_weight_value(w, default=700):
    if w is None:
        return default
    if isinstance(w, (int, float)):
        return int(w)
    w = str(w).strip().lower()
    if w.isdigit():
        return int(w)
    if w == "italic":
        return 400
    return WEIGHT_NAMES.get(w.replace(" ", ""), default)


def luminance(hex_color: str) -> float:
    m = re.match(r"#?([0-9a-fA-F]{6})", hex_color or "")
    if not m:
        return 1.0
    r, g, b = (int(m.group(1)[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def pick_color(colors: dict, *prefixes, default=None):
    for p in prefixes:
        if p in colors:
            return colors[p]
        for k, v in colors.items():
            if k.startswith(p):
                return v
    return default


def theme_tokens(theme: dict) -> dict:
    """Normaliza as chaves heterogêneas de presets/themes.json em tokens semânticos."""
    c = theme.get("colors", {})
    ink = c.get("text_primary", "#FFFFFF")
    light_theme = luminance(ink) < 0.45
    accent = pick_color(c, "highlight", "blue", "accent", default="#DCB86E")
    alert = pick_color(c, "alert", "highlight_red", default=accent)
    soft = pick_color(c, "text_secondary", "metallic_silver", "sky_light", "light_blue", "gray", default=None)
    if not soft:
        soft = "rgba(0,0,0,0.62)" if light_theme else "rgba(255,255,255,0.78)"
    comps = theme.get("components", {})
    pill = comps.get("pill", {})
    paper = c.get("bg_paper") or c.get("ice_surface") or "#FAFAF8"
    if light_theme:
        scrim_top = "rgba(250,250,248,0.92)" if paper.upper().startswith("#FA") else "rgba(255,255,255,0.90)"
        scrim_mid = "rgba(250,250,248,0.82)"  # o véu de papel segura até o pé da faixa (texto cinza precisa de 3:1)
        endfade = paper
    else:
        scrim_top = c.get("backdrop_tint", "rgba(0,0,0,0.80)")
        m = re.match(r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*([\d.]+))?\s*\)", scrim_top)
        if m:
            r_, g_, b_, a_ = m.groups()
            scrim_mid = f"rgba({r_}, {g_}, {b_}, {round(float(a_ or 1) * 0.72, 3)})"
        else:
            scrim_mid = "rgba(0,0,0,0.6)"
        endfade = "#000000"
    blur = theme.get("backdrop_blur", {})
    fonts = theme.get("fonts", {})

    def level(prefix, fam, wgt, style="normal"):
        for k, v in fonts.items():
            if k.startswith(prefix):
                st = v.get("style") or ("italic" if str(v.get("weight", "")).lower() == "italic" else "normal")
                return {
                    "family": v.get("family", fam),
                    "weight": font_weight_value(v.get("weight"), wgt),
                    "style": st,
                    "size_range": v.get("size_range_px", []),
                    "line_height": v.get("line_height", 1.05),
                    "letter_spacing": v.get("letter_spacing_px", 0),
                    "transform": v.get("transform", "none"),
                }
        return {"family": fam, "weight": wgt, "style": style, "size_range": [], "line_height": 1.05, "letter_spacing": 0, "transform": "none"}

    hook = level("level_1", "Big Shoulders Display", 900)
    support = level("level_2", "Fraunces", 600, "italic")
    label = level("level_3", "Inter", 700)
    data = level("level_4", hook["family"], hook["weight"])
    return {
        "ink": ink,
        "ink_soft": soft,
        "accent": accent,
        "alert": alert,
        "light_theme": light_theme,
        "card_bg": c.get("card_background", "rgba(0,0,0,0.72)"),
        "card_border": c.get("card_border", accent),
        "track": c.get("chart_track", "rgba(255,255,255,0.22)" if not light_theme else "rgba(0,0,0,0.12)"),
        "divider": c.get("divider_subtle", "rgba(255,255,255,0.3)"),
        "pill_bg": pill.get("bg_color", accent),
        "pill_fg": pill.get("text_color", c.get("pill_dark_text", "#111111")),
        "pill_border": pill.get("border", "0px solid transparent"),
        "pill_radius": pill.get("border_radius_px", 999),
        "pill_pad": pill.get("padding", "8px 24px"),
        "pill_font_size": pill.get("font_size_px", 24),
        "scrim_top": scrim_top,
        "scrim_mid": scrim_mid,
        "scrim_blur": 7 if blur.get("enabled", True) and not light_theme else 0,
        "endfade": endfade,
        "ground": c.get("carbon_black") or c.get("navy_darkest") or ("#FAFAF8" if light_theme else "#000000"),
        "node_idle": "rgba(255,255,255,0.10)" if not light_theme else "rgba(11,42,91,0.06)",
        "hook": hook,
        "support": support,
        "label": label,
        "data": data,
    }


# ───────────────────────────── init ─────────────────────────────

def find_font_file(name: str) -> Path | None:
    for d in FONT_DIRS:
        p = d / name
        if p.exists() and p.stat().st_size > 5000:
            return p
    return None


def font_face_css(families: set[str], fonts_dir: Path) -> tuple[str, list[str]]:
    css, missing = [], []
    for fam in sorted(families):
        entries = FONT_FILES.get(fam)
        if not entries:
            missing.append(fam)
            continue
        for fname, weights, style in entries:
            src = find_font_file(fname)
            if not src:
                missing.append(f"{fam} ({fname})")
                continue
            dst = fonts_dir / fname
            if not dst.exists():
                shutil.copy2(src, dst)
            css.append(
                "@font-face {\n"
                f"  font-family: \"{fam}\";\n"
                f"  src: url(\"fonts/{fname}\") format(\"truetype\");\n"
                f"  font-weight: {weights};\n"
                f"  font-style: {style};\n"
                "  font-display: block;\n"
                "}"
            )
    return "\n".join(css), missing


def parse_box(spec) -> dict | None:
    """'x: 1020 to 1860, y: 120 to 960' ou {x_min,...} → {x_min, x_max, y_min, y_max}"""
    if isinstance(spec, dict) and all(k in spec for k in ("x_min", "x_max", "y_min", "y_max")):
        return {k: int(spec[k]) for k in ("x_min", "x_max", "y_min", "y_max")}
    if isinstance(spec, str):
        m = re.search(r"x:\s*(\d+)\s*to\s*(\d+).*?y:\s*(\d+)\s*to\s*(\d+)", spec)
        if m:
            x0, x1, y0, y1 = map(int, m.groups())
            return {"x_min": x0, "x_max": x1, "y_min": y0, "y_max": y1}
    return None


def subtitle_config(profile: dict, platform: dict, lay: dict) -> dict:
    W, H = lay["W"], lay["H"]
    t = profile.get("typography", {})
    sub_box = dict(platform.get("subtitles_box", {}))
    fam, wgt, style = parse_font_spec(t.get("subtitles_font"), "Inter", 800)
    scale = min(W, H) / 1080  # tamanhos do perfil são para o lado curto de 1080
    y0, y1 = sub_box.get("y_min"), sub_box.get("y_max")
    plat_anchor = sub_box.get("anchor_y") or (round((y0 + y1) / 2) if y0 is not None and y1 is not None else round(H * 0.68))
    prof_anchor = t.get("subtitles_anchor_y")
    # a âncora do perfil foi medida para 9:16: só vale se cair dentro da faixa de legenda desta plataforma
    anchor = prof_anchor if (prof_anchor and y0 is not None and y1 is not None and y0 <= prof_anchor <= y1) else plat_anchor
    bx_min = sub_box.get("x_min", round(W * 0.065))
    bx_max = sub_box.get("x_max", W - round(W * 0.065))
    max_w = min(sub_box.get("max_width_px", bx_max - bx_min), bx_max - bx_min)
    center_x = sub_box.get("center_x", (bx_min + bx_max) / 2)
    pres = lay.get("presenter_box")
    if pres:  # split lateral: a legenda fica sob o apresentador, longe do painel gráfico
        center_x = (pres["x_min"] + pres["x_max"]) / 2
        max_w = min(max_w, pres["x_max"] - pres["x_min"] - 80)
        bx_min, bx_max = pres["x_min"], pres["x_max"]
    left = int(round(max(bx_min, min(center_x - max_w / 2, bx_max - max_w))))
    return {
        "enabled": bool((profile.get("strict_rules") or {}).get("burned_subtitles", True)) and t.get("subtitles_burned", True) is not False,
        "family": fam,
        "weight": wgt,
        "style": style,
        "size": round(t.get("subtitles_size_px_1080", 60) * scale),
        "color": t.get("subtitles_color", "#FFFFFF"),
        "highlight": t.get("subtitles_highlight_color"),
        "highlight_numbers": t.get("subtitles_highlight_numbers", bool(t.get("subtitles_highlight_color"))),
        "keywords": t.get("subtitles_highlight_keywords", []),
        "stroke_color": t.get("subtitles_stroke_color", "#000000"),
        "stroke_width": t.get("subtitles_stroke_width", 2),
        "shadow": t.get("subtitles_shadow", "0px 4px 12px rgba(0,0,0,0.65)"),
        "anchor_y": int(anchor),
        "x_min": left,
        "x_max": left + int(max_w),
        "max_width": int(max_w),
        "max_lines": t.get("subtitles_max_lines", 2),
        "max_words": t.get("subtitles_max_words_per_line", 4),
        "style_mode": t.get("subtitles_animation", "pop"),
    }


def compute_layout(profile, theme, platform, head_y=None, head_x=None, layout_mode=None) -> dict:
    W, H = int(platform["width"]), int(platform["height"])
    fps = int(platform.get("fps", 30))
    fr = profile.get("framing_and_zoom") or {}
    sz = platform.get("safe_zones", {})
    landscape = W > H
    presenter = None
    if landscape:
        modes = platform.get("layout_modes", {})
        mode = layout_mode or ("split_lateral" if "split_lateral" in modes else "lower_third")
        box = parse_box((modes.get(mode) or {}).get("graphics_box"))
        if not box:
            box = {"x_min": round(W * 0.53), "x_max": round(W * 0.97), "y_min": round(H * 0.11), "y_max": round(H * 0.89)} if mode == "split_lateral" \
                else {"x_min": round(W * 0.1), "x_max": round(W * 0.9), "y_min": round(H * 0.63), "y_max": round(H * 0.9)}
        presenter = parse_box((modes.get(mode) or {}).get("presenter_box"))
        hy = int(head_y if head_y is not None else round(H * 0.22))
        hx = int(head_x if head_x is not None else ((presenter["x_min"] + presenter["x_max"]) // 2 if presenter else W // 2))
        clearance = 0
        if mode == "split_lateral":
            scrim = {"left": box["x_min"] - 160, "top": 0, "w": W - box["x_min"] + 160, "h": H, "angle": "270deg",
                     "a": 0.0, "b": round(100 * (W - box["x_max"] + (box["x_max"] - box["x_min"])) / (W - box["x_min"] + 160), 1)}
        else:
            scrim = {"left": 0, "top": box["y_min"] - 140, "w": W, "h": H - box["y_min"] + 140, "angle": "0deg",
                     "a": 0.0, "b": round(100 * (H - box["y_min"]) / (H - box["y_min"] + 140), 1)}
        gfx = box
    else:
        mode = "above_head"
        hy = int(head_y if head_y is not None else fr.get("head_anchor_y_default", round(H * 0.29)))
        hx = int(head_x if head_x is not None else fr.get("head_anchor_x_default", W // 2))
        gbox = platform.get("graphics_usable_box", {})
        anchor_rule = str(gbox.get("y_max_anchor", ""))
        m = re.search(r"minus_(\d+)px", anchor_rule)
        clearance = int(fr.get("safe_head_clearance_px", m.group(1) if m else 60))
        x_min = int(gbox.get("x_min", sz.get("left_margin_px", 70)))
        x_max = int(gbox.get("x_max", W - int(sz.get("right_margin_high_px", sz.get("right_margin_px", 55)))))
        y_min = int(gbox.get("y_min", sz.get("top_margin_px", 250)))
        y_max_raw = gbox.get("y_max")
        y_max = int(y_max_raw) if isinstance(y_max_raw, (int, float)) else hy - clearance
        gfx = {"x_min": x_min, "x_max": x_max, "y_min": y_min, "y_max": y_max}
        scrim_h = max(y_max + 40, hy - 12)
        scrim = {"left": 0, "top": 0, "w": W, "h": scrim_h, "angle": "180deg",
                 "a": round(100 * y_min / scrim_h, 1), "b": round(100 * y_max / scrim_h, 1)}
        if y_max - y_min < 140:
            print(f"  ⚠ Faixa gráfica acima da cabeça tem só {y_max - y_min}px (y {y_min}–{y_max}). "
                  "Meça o topo do cabelo (--head-y) ou use cenas de 1 linha.", file=sys.stderr)
    return {"W": W, "H": H, "fps": fps, "head_x": hx, "head_y": hy, "clearance": clearance, "mode": mode,
            "gfx": gfx, "scrim": scrim, "presenter_box": presenter}


def type_scale(tk: dict, lay: dict) -> dict:
    """Tamanhos derivados da altura da faixa acima da cabeça (nada legível abaixo de 28 px em 1080)."""
    g = lay["gfx"]
    gw, gh = g["x_max"] - g["x_min"], g["y_max"] - g["y_min"]
    s = min(lay["W"], lay["H"]) / 1080
    hook_max = (tk["hook"]["size_range"] or [64, 200])[-1] * s
    sup_max = (tk["support"]["size_range"] or [34, 110])[-1] * s
    label_ls = round(max(1, tk["label"]["letter_spacing"] or 3) * 0.6, 1)
    return {
        "band_w": gw, "band_h": gh,
        "hook_px": round(min(hook_max, gh * 0.56)), "hook_family": tk["hook"]["family"], "hook_upper": tk["hook"]["transform"] == "uppercase",
        "support_px": round(min(sup_max, gh * 0.30)), "support_family": tk["support"]["family"],
        "label_px": round(max(28 * s, min(40 * s, gh * 0.13))), "label_family": tk["label"]["family"], "label_upper": True, "label_ls": label_ls,
        "pill_px": round(max(28 * s, tk["pill_font_size"] * s)),
        "data_px": round(min(hook_max, gh * 0.50)), "data_family": tk["data"]["family"],
        "item_px": round(max(30 * s, min(44 * s, gh * 0.15))), "item_family": tk["label"]["family"],
    }


def theme_css(tk: dict, lay: dict, sub: dict, face_css: str) -> str:
    g = lay["gfx"]
    gw, gh = g["x_max"] - g["x_min"], g["y_max"] - g["y_min"]
    W = lay["W"]
    s = min(W, lay["H"]) / 1080
    ts = type_scale(tk, lay)
    hero, support, label, pill, data, item = ts["hook_px"], ts["support_px"], ts["label_px"], ts["pill_px"], ts["data_px"], ts["item_px"]
    sc = lay["scrim"]

    def fam(level):
        return f"\"{tk[level]['family']}\""

    lines = [
        "/* Gerado por scripts/hf_project.py — tokens do tema + perfil + plataforma. Não edite à mão: rode `init` de novo. */",
        face_css,
        ":root {",
        f"  --canvas-w: {lay['W']}px; --canvas-h: {lay['H']}px;",
        f"  --head-x: {lay['head_x']}px; --head-y: {lay['head_y']}px;",
        f"  --gfx-x-min: {g['x_min']}px; --gfx-y-min: {g['y_min']}px; --gfx-w: {gw}px; --gfx-h: {gh}px; --gfx-gap: {round(max(10, gh * 0.05))}px;",
        f"  --ink: {tk['ink']}; --ink-soft: {tk['ink_soft']}; --accent: {tk['accent']}; --alert: {tk['alert']};",
        f"  --card-bg: {tk['card_bg']}; --card-border: {tk['card_border']}; --track: {tk['track']}; --divider: {tk['divider']};",
        f"  --pill-bg: {tk['pill_bg']}; --pill-fg: {tk['pill_fg']}; --pill-border: {tk['pill_border']};",
        f"  --pill-radius: {tk['pill_radius']}px; --pill-pad: {tk['pill_pad']}; --pill-size: {pill}px;",
        f"  --scrim-left: {sc['left']}px; --scrim-top-y: {sc['top']}px; --scrim-w: {sc['w']}px; --scrim-h: {sc['h']}px; --scrim-angle: {sc['angle']};",
        f"  --scrim-top: {tk['scrim_top']}; --scrim-mid: {tk['scrim_mid']}; --scrim-blur: {tk['scrim_blur']}px;",
        f"  --scrim-stop-a: {sc['a']}%; --scrim-stop-b: {sc['b']}%;",
        f"  --endfade: {tk['endfade']}; --ground: {tk['ground']}; --node-idle: {tk['node_idle']};",
        f"  --font-hook: {fam('hook')}; --font-hook-weight: {tk['hook']['weight']}; --font-hook-style: {tk['hook']['style']};",
        f"  --font-hook-lh: {tk['hook']['line_height']}; --font-hook-ls: {tk['hook']['letter_spacing']}px; --font-hook-transform: {tk['hook']['transform']};",
        f"  --font-support: {fam('support')}; --font-support-weight: {tk['support']['weight']}; --font-support-style: {tk['support']['style']}; --font-support-lh: {tk['support']['line_height']};",
        f"  --font-label: {fam('label')}; --font-label-weight: {tk['label']['weight']}; --font-label-ls: {round(max(1, tk['label']['letter_spacing'] or 3) * 0.6, 1)}px;",
        f"  --font-data: {fam('data')}; --font-data-weight: {tk['data']['weight']};",
        f"  --hero-size: {hero}px; --support-size: {support}px; --label-size: {label}px; --data-size: {data}px; --source-size: {round(max(28 * s, label * 0.88))}px;",
        f"  --line-w: {round(min(gw * 0.42, 360 * s))}px; --line-h: {max(3, round(4 * s))}px; --scratch-h: {max(5, round(7 * s))}px;",
        f"  --track-w: {round(min(gw * 0.7, 560 * s))}px; --track-h: {max(8, round(10 * s))}px;",
        f"  --item-size: {item}px; --item-icon: {round(item * 1.1)}px; --list-gap: {round(max(8, gh * 0.04))}px;",
        f"  --node-d: {round(max(28 * s, gh * 0.13))}px; --node-col: {round(gw / 3.6)}px; --node-label-size: {round(max(30 * s, gh * 0.135))}px;",
        f"  --sub-font: \"{sub['family']}\"; --sub-weight: {sub['weight']}; --sub-size: {sub['size']}px; --sub-color: {sub['color']};",
        f"  --sub-hl: {sub['highlight'] or tk['accent']}; --sub-stroke: {sub['stroke_color']}; --sub-stroke-w: {sub['stroke_width']}px;",
        f"  --sub-shadow: {sub['shadow']}; --sub-anchor-y: {sub['anchor_y']}px; --sub-x-min: {sub['x_min']}px; --sub-w: {sub['max_width']}px;",
        "}",
    ]
    return "\n".join(lines) + "\n"


def prepare_base_video(src: Path, dst: Path, fps: int, W: int, H: int, profile: dict, grade: bool, force_reencode: bool,
                       alvo: tuple[int, int] | None = None) -> dict:
    """Mezanino: a fonte reaproveitada sem recodificar quando dá; senão H.264 CRF 10 (visualmente sem perda).

    `alvo` é o tamanho do mezanino decidido pela exportação (a área útil da fonte, até a maior saída); sem ele,
    o tamanho da composição (comportamento das versões ≤ 1.8)."""
    mi = media_info(src)
    if not mi["has_video"]:
        die(f"{src} não tem trilha de vídeo.")
    hdr = (mi.get("color_transfer") or "") in ("smpte2084", "arib-std-b67")
    MW, MH = alvo or (W, H)
    gap = keyframe_max_gap(src)
    vg = profile.get("video_grade") or {}
    grade_filters = []
    if grade:
        for key in ("ffmpeg_curves", "ffmpeg_colorbalance", "ffmpeg_eq"):
            if vg.get(key):
                grade_filters.append(f"{key.split('_', 1)[1]}={vg[key]}")
    disp_w, disp_h = (mi["height"], mi["width"]) if abs(mi["rotation"]) in (90, 270) else (mi["width"], mi["height"])
    needs_scale = (disp_w, disp_h) != (MW, MH)
    needs_fps = mi["fps"] and abs(mi["fps"] - fps) > 0.05
    pix = mi.get("pix_fmt") or ""
    reasons = []
    if gap > 1.05:
        reasons.append(f"keyframes a cada {gap:.2f}s (seek congela acima de ~1s)")
    if grade_filters:
        reasons.append("grade do perfil")
    if needs_scale:
        reasons.append(f"{disp_w}x{disp_h} → {MW}x{MH}")
    if needs_fps:
        reasons.append(f"{mi['fps']:.3f} → {fps} fps")
    if mi["codec"] not in ("h264",):
        reasons.append(f"codec {mi['codec']} → h264 (o navegador do render não decodifica {mi['codec']})")
    elif pix not in ("yuv420p", "yuvj420p"):
        reasons.append(f"{pix} → yuv420p (o navegador do render só decodifica H.264 8-bit 4:2:0)")
    if hdr:
        reasons.append(f"HDR {mi.get('color_transfer')} → SDR Rec.709")
    if force_reencode:
        reasons.append("--reencode")
    if not reasons:
        try:
            os.link(src, dst)
        except OSError:
            shutil.copy2(src, dst)
        info(f"Vídeo base reutilizado sem recodificar ({disp_w}x{disp_h}, GOP máx {gap:.2f}s).")
        return {"reencoded": False, "gop_gap_s": gap, "grade": None, "largura": disp_w, "altura": disp_h}
    vf = []
    if hdr:
        import neuro_export as nx
        tm = nx.filtro_hdr_para_sdr()
        if tm:
            vf.append(tm)
        else:
            print("  ⚠ Fonte HDR e o ffmpeg sem zscale/tonemap: as cores podem sair lavadas. Instale um ffmpeg completo "
                  "(brew install ffmpeg) ou converta a fonte para SDR Rec.709.", file=sys.stderr)
    if needs_scale:
        vf += [f"scale={MW}:{MH}:force_original_aspect_ratio=increase:flags=lanczos+accurate_rnd+full_chroma_int", f"crop={MW}:{MH}"]
    vf += grade_filters
    vf += ["format=yuv420p"]
    import neuro_export as nx
    cmd = ["ffmpeg", "-v", "error", "-stats", "-y", "-i", str(src), "-vf", ",".join(vf), "-r", str(fps),
           "-c:v", "libx264", "-preset", "slow", "-crf", str(nx.MEZANINO_CRF), "-g", str(fps), "-keyint_min", str(fps),
           "-sc_threshold", "0", "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-color_range", "tv"]
    if mi["has_audio"]:
        # a fala sai deste arquivo: AAC da fonte é copiado (sem 2ª geração); o resto vira AAC 320k 48 kHz
        acodec = (ffprobe_json(src).get("streams") or [{}])
        a0 = next((s for s in acodec if s.get("codec_type") == "audio"), {})
        cmd += ["-map", "0:v:0", "-map", "0:a:0"]
        cmd += ["-c:a", "copy"] if a0.get("codec_name") == "aac" else ["-c:a", "aac", "-b:a", "320k", "-ar", "48000"]
    cmd += ["-movflags", "+faststart", str(dst)]
    info("Recodificando o vídeo base em H.264 CRF " + str(nx.MEZANINO_CRF) + ": " + "; ".join(reasons))
    res = run(cmd, capture=True)
    if res.returncode != 0:
        die("ffmpeg falhou ao preparar o vídeo base:\n" + res.stderr[-1200:])
    return {"reencoded": True, "gop_gap_s": gap, "grade": ",".join(grade_filters) or None, "reasons": reasons,
            "largura": MW, "altura": MH, "crf": nx.MEZANINO_CRF}


def scaffold_hyperframes(out: Path):
    """Usa o `init` oficial para herdar hyperframes.json/package.json pinados; cai num mínimo se falhar."""
    if (out / "hyperframes.json").exists():
        return
    tmp_parent = out.parent
    name = out.name
    res = run(hf_cmd("init", name, "--skip-skills"), cwd=str(tmp_parent), env=hf_env())
    if res.returncode == 0 and (out / "hyperframes.json").exists():
        info(f"Projeto base criado com `hyperframes init` ({HF_VERSION}).")
        return
    out.mkdir(parents=True, exist_ok=True)
    save_json(out / "hyperframes.json", {
        "$schema": "https://hyperframes.heygen.com/schema/hyperframes.json",
        "registry": "https://raw.githubusercontent.com/heygen-com/hyperframes/main/registry",
        "paths": {"blocks": "compositions", "components": "compositions/components", "assets": "assets"},
        "media": {"autoProxy": True},
    })
    save_json(out / "package.json", {
        "name": name, "private": True, "type": "module",
        "scripts": {k: f"npx --yes hyperframes@{HF_VERSION} {k if k != 'dev' else 'preview'}" for k in ("dev", "check", "render")},
    })
    info("`hyperframes init` indisponível — esqueleto mínimo escrito.")


def cmd_init(a):
    profiles, themes, platforms, _ = load_presets()
    if a.profile not in profiles:
        die(f"Perfil '{a.profile}' não existe. Opções: {', '.join(profiles)}")
    profile = profiles[a.profile]
    estilo_id = getattr(a, "estilo", None) or profile.get("estilo_padrao")
    estilo = None
    if estilo_id:
        estilos = load_estilos()
        if estilo_id not in estilos:
            die(f"Estilo '{estilo_id}' não existe. Opções: {', '.join(estilos)}")
        estilo = dict(estilos[estilo_id], id=estilo_id)
        profile = apply_estilo(profile, estilo)
    platform_id = a.platform or profile.get("platform_default", "instagram_reels")
    if platform_id not in platforms:
        die(f"Plataforma '{platform_id}' não existe. Opções: {', '.join(platforms)}")
    platform = platforms[platform_id]
    theme_id = a.theme or profile.get("theme_default")
    if theme_id not in themes:
        die(f"Tema '{theme_id}' não existe. Opções: {', '.join(themes)}")
    theme = themes[theme_id]
    src = Path(a.video).expanduser().resolve()
    if not src.exists():
        die(f"Vídeo não encontrado: {src}")
    out = Path(a.out).expanduser().resolve()
    if out.exists() and (out / "neuro.json").exists() and not a.force:
        die(f"{out} já é um projeto Neuro. Use --force para refazer o init.")
    out.parent.mkdir(parents=True, exist_ok=True)
    engine = getattr(a, "engine", None) or "hyperframes"

    print(f"▶ Neuro MV Edit → {'HyperFrames' if engine == 'hyperframes' else 'Remotion'} | perfil {a.profile} · tema {theme_id} · {platform_id}")
    if engine == "hyperframes":
        scaffold_hyperframes(out)
    for d in ("assets/fonts", "assets/sfx", "assets/music", "dados", "renders") + (("compositions",) if engine == "hyperframes" else ()):
        (out / d).mkdir(parents=True, exist_ok=True)
    neuro_note = (
        "\n\n## Neuro MV Edit — este projeto é gerado\n\n"
        "Projeto criado pela skill `neuro-mv-edit` (`scripts/hf_project.py`). Leia `/neuro-mv-edit` e "
        "`references/hyperframes/BRIDGE.md` da skill antes de mudar algo.\n\n"
        "- `index.html` e `compositions/<cena>.html` saem do `build` a partir de `cues.json`: mude o roteiro em `cues.json` e rode `build`.\n"
        "- Ajuste fino no Studio é permitido, mas o próximo `build` recusa sobrescrever (use `build --force` só se a edição puder ser perdida).\n"
        "- Tokens de marca (cores, fontes, faixas seguras) ficam em `assets/neuro-theme.css`, gerado pelo `init`.\n"
        "- Gráficos só na faixa acima da cabeça; legendas na faixa da plataforma; nenhuma animação sem SFX.\n"
    )
    for agent_file in ("CLAUDE.md", "AGENTS.md"):
        p = out / agent_file
        if p.exists() and "Neuro MV Edit — este projeto é gerado" not in p.read_text(encoding="utf-8"):
            with open(p, "a", encoding="utf-8") as fh:
                fh.write(neuro_note)

    lay = compute_layout(profile, theme, platform, a.head_y, a.head_x, a.layout)
    # decisões de exportação (resolução, codec, fps, qualidade): valem para o mezanino, o render e o master
    import neuro_export as nx
    fonte = nx.analisar_fonte(src)
    crf_perfil = ((profile.get("strict_rules") or {}).get("dual_export_crf") or {}).get("master_crf")
    try:
        plano_exp = nx.plano({"resolucoes": getattr(a, "resolucao", None), "codec": getattr(a, "codec", None),
                              "fps": getattr(a, "fps", None), "qualidade": getattr(a, "qualidade", None)},
                             lay["W"], lay["H"], fonte, crf_perfil)
    except ValueError as e:
        die(str(e))
    lay["fps"] = int(plano_exp["fps"])
    saidas_txt = ", ".join(f"{s['resolucao']} ({s['largura']}x{s['altura']})" for s in plano_exp["saidas"])
    info(f"Exportação: {saidas_txt} · {plano_exp['codec_nome']} · {lay['fps']} fps · qualidade {plano_exp['export']['qualidade']}")
    for av in plano_exp["avisos"]:
        print(f"  ⚠ {av}", file=sys.stderr)
    sub = subtitle_config(profile, platform, lay)
    tk = theme_tokens(theme)
    families = {tk[k]["family"] for k in ("hook", "support", "label", "data")} | {sub["family"]}
    face_css, missing = font_face_css(families, out / "assets" / "fonts")
    if missing:
        print(f"  ⚠ Fontes sem arquivo local: {', '.join(missing)} — rode `python3 scripts/verify-env.py`.", file=sys.stderr)
    (out / "assets" / "neuro-theme.css").write_text(theme_css(tk, lay, sub, face_css), encoding="utf-8")
    shutil.copy2(TEMPLATE_DIR / "neuro-components.css", out / "assets" / "neuro-components.css")

    base = out / "assets" / "base.mp4"
    if base.exists():
        base.unlink()
    mz = plano_exp["mezanino"]
    vinfo = prepare_base_video(src, base, lay["fps"], lay["W"], lay["H"], profile, not a.no_grade, a.reencode,
                               alvo=(mz["largura"], mz["altura"]))
    mi = media_info(base)
    duration = math.floor(mi["duration"] * lay["fps"]) / lay["fps"]

    cfg = {
        "skill": "neuro-mv-edit", "skill_version": SKILL_VERSION, "engine": engine, "hyperframes_version": HF_VERSION,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "profile": a.profile, "theme": theme_id, "platform": platform_id,
        "width": lay["W"], "height": lay["H"], "fps": lay["fps"], "duration": r3(duration),
        "duracao_fonte": r3(duration), "quadros_fonte": int(round(duration * lay["fps"])), "mezanino": "assets/base.mp4",
        "source_video": str(src), "video": "assets/base.mp4", "video_has_audio": mi["has_audio"], "video_prep": vinfo,
        "export": plano_exp["export"],
        "fonte": {k: fonte[k] for k in ("largura", "altura", "fps", "codec", "bits", "hdr", "transferencia", "bitrate_mbps", "audio")},
        "head": {"x": lay["head_x"], "y": lay["head_y"], "clearance": lay["clearance"]},
        "layout_mode": lay["mode"], "gfx_band": lay["gfx"], "presenter_box": lay["presenter_box"],
        "subtitles": sub, "type": type_scale(tk, lay),
        "rules": profile.get("strict_rules", {}),
        "estilo": estilo,
        "loudness": {"target_lufs": float((profile.get("audio_mix") or {}).get("target_lufs", platform.get("codec", {}).get("audio_loudness_target_lufs", -14))),
                     "true_peak": float((profile.get("audio_mix") or {}).get("true_peak_max_dbfs", -1.5)), "lra": 9},
    }
    save_json(out / "neuro.json", cfg)
    if not (out / "cues.json").exists():
        save_json(out / "cues.json", {
            "_help": "Roteiro de deixas. Tempos em segundos do filme. Veja references/hyperframes/BRIDGE.md.",
            "scenes": [],
            "camera": [],
            "sfx": {"enabled": True, "gain_db": ({k: round(v + float((estilo.get("sfx") or {}).get("ganho_db", 0)), 1) for k, v in SFX_GAIN_DB.items()}
                                                 if estilo and (estilo.get("sfx") or {}).get("ganho_db") else {}), "bank": {}},
            "music": None,
            "end": {"fade_out": bool(profile.get("strict_rules", {}).get("final_fade_out", True))},
        })
    readme = out / "NEURO.md"
    if engine != "hyperframes":
        print(f"✓ Mezanino pronto em {out / 'assets' / 'base.mp4'} ({duration:.2f}s)")
        return cfg
    readme.write_text(
        f"# Projeto {out.name}\n\nGerado pela skill neuro-mv-edit {SKILL_VERSION} (HyperFrames {HF_VERSION}).\n\n"
        f"- Perfil: `{a.profile}` · Tema: `{theme_id}` · Plataforma: `{platform_id}` ({lay['W']}x{lay['H']} @ {lay['fps']} fps)\n"
        f"- Faixa gráfica ({lay['mode']}): x {lay['gfx']['x_min']}–{lay['gfx']['x_max']}, y {lay['gfx']['y_min']}–{lay['gfx']['y_max']}\n"
        f"- Legendas: {'queimadas' if sub['enabled'] else 'NÃO queimar (perfil)'} · âncora y={sub['anchor_y']}\n\n"
        "Fluxo: `captions` → editar `cues.json` → `build` → `check` → `snapshot` → `preview` → `render` → `master`.\n",
        encoding="utf-8",
    )
    print(f"✓ Projeto pronto em {out}")
    print(f"  duração {duration:.2f}s · layout {lay['mode']} · faixa gráfica {lay['gfx']['x_max'] - lay['gfx']['x_min']}×{lay['gfx']['y_max'] - lay['gfx']['y_min']}px · legendas {'on' if sub['enabled'] else 'off'} (âncora y={sub['anchor_y']})")
    print("  próximo: transcrever → captions → cues.json → build")
    return cfg


# ───────────────────────────── legendas ─────────────────────────────

def _deep_merge(a, b):
    if isinstance(a, dict) and isinstance(b, dict):
        out = dict(a)
        for k, v in b.items():
            out[k] = _deep_merge(a.get(k), v) if k in a else v
        return out
    return b


def user_memory_path() -> Path:
    """Memória do usuário: aprendizados e histórico. Fica fora da skill, então sobrevive a reinstalações."""
    return neuro_home() / "memory.json"


def load_memory() -> dict:
    """Memória da skill (glossários, base) + memória do usuário por cima."""
    base = load_json(MEMORY_PATH, default={})
    up = user_memory_path()
    return _deep_merge(base, load_json(up, default={})) if up.exists() else base


def update_user_memory(fn) -> Path:
    """Aplica `fn(dict)` à memória do usuário e grava (só o que é dele; a da skill continua só leitura)."""
    up = user_memory_path()
    data = load_json(up, default={}) if up.exists() else {}
    fn(data)
    save_json(up, data)
    return up


def load_glossary(segment: str | None = None) -> dict:
    """Correções de legenda do segmento do perfil. Usa o mapa `legendas` (só grafia, nunca acrescenta palavras);
    glossário sem `legendas` (ex.: um seu antigo) só contribui com trocas palavra a palavra."""
    mem = load_memory()
    gl = {}
    for k, v in mem.items():
        if not (k.endswith("_glossary") and isinstance(v, dict)):
            continue
        segs = v.get("segmentos")
        if segs and segment and segment not in segs:
            continue
        if isinstance(v.get("legendas"), dict):
            gl.update(v["legendas"])
            continue
        for wrong, right in (v.get("replacements") or {}).items():
            right = re.split(r"\s+\(", right)[0].strip()
            if len(right.split()) == len(wrong.split()):
                gl[wrong] = right
    return gl


def apply_fix(words: list[dict], wrong: str, right: str) -> int:
    wt = [norm_token(t) for t in wrong.split()]
    rt = right.split()
    if not wt:
        return 0
    n = 0
    i = 0
    rt_norm = [norm_token(t) for t in rt]
    while i <= len(words) - len(wt):
        if all(norm_token(words[i + j]["text"]) == wt[j] for j in range(len(wt))):
            # já dito por inteiro ("Sistema de Ensino X" com a troca "sistema x" → "Sistema de Ensino X"): não duplica
            if len(rt) > len(wt) and [norm_token(w["text"]) for w in words[i:i + len(rt)]] == rt_norm:
                i += len(rt)
                continue
            trail = re.search(r"[.,!?;:…]+$", words[i + len(wt) - 1]["text"])
            trail = trail.group(0) if trail else ""
            lead_upper = words[i]["text"][:1].isupper()
            if len(rt) == len(wt):
                for j in range(len(wt)):
                    words[i + j]["text"] = rt[j]
            else:
                first, last = words[i], words[i + len(wt) - 1]
                first["text"], first["end"] = right, last["end"]
                del words[i + 1:i + len(wt)]
            fixed = words[i + len(rt) - 1] if len(rt) == len(wt) else words[i]
            if trail and not re.search(r"[.,!?;:…]$", fixed["text"]):
                fixed["text"] += trail
            if lead_upper and words[i]["text"][:1].islower():
                words[i]["text"] = words[i]["text"][:1].upper() + words[i]["text"][1:]
            n += 1
            i += max(1, len(rt) if len(rt) == len(wt) else 1)
        else:
            i += 1
    return n


def final_silence_start(audio_src: Path) -> float | None:
    res = run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(audio_src), "-af", "silencedetect=noise=-35dB:d=0.6", "-f", "null", "-"])
    starts = [float(x) for x in re.findall(r"silence_start: (-?[\d.]+)", res.stderr)]
    ends = [float(x) for x in re.findall(r"silence_end: (-?[\d.]+)", res.stderr)]
    if starts and (len(ends) < len(starts)):
        return starts[-1]
    return None


def build_groups(words: list[dict], sub: dict, duration: float) -> list[dict]:
    max_words = max(2, int(sub.get("max_words", 4)))
    max_chars = max(10, int(sub["max_width"] / (sub["size"] * 0.56)) * max(1, min(2, int(sub.get("max_lines", 2)))))
    groups, cur = [], []

    def flush():
        if cur:
            groups.append(list(cur))
            cur.clear()

    for i, w in enumerate(words):
        if cur:
            prev = cur[-1]
            gap = w["start"] - prev["end"]
            chars = sum(len(x["text"]) + 1 for x in cur) + len(w["text"])
            if gap >= 0.15 or len(cur) >= max_words or chars > max_chars or re.search(r"[.!?…;:]$", prev["text"]):
                flush()
            elif re.search(r",$", prev["text"]) and len(cur) >= 2:
                flush()
        cur.append(w)
    flush()

    # Sem palavra-função órfã no fim do bloco ("…bilhões em" → "em cédulas…")
    for gi in range(len(groups) - 1):
        g, nxt = groups[gi], groups[gi + 1]
        if len(g) >= 2 and norm_token(g[-1]["text"]) in PT_FUNCTION_WORDS and not re.search(r"[.,!?;:…]$", g[-1]["text"]) \
                and nxt and nxt[0]["start"] - g[-1]["end"] < 0.15 and len(nxt) < max_words + 1:
            nxt.insert(0, g.pop())

    out = []
    for gi, g in enumerate(groups):
        start = max(g[0]["start"] - 0.06, 0.12)
        out.append({"words": g, "start": start, "last_end": g[-1]["end"]})
    for gi, g in enumerate(out):
        nxt = out[gi + 1]["start"] if gi + 1 < len(out) else duration
        end = g["last_end"] + 0.45
        if nxt - g["last_end"] < 0.7:
            end = nxt - 0.02
        end = min(end, nxt - 0.02, duration - 1.0 / 30)
        end = max(end, g["start"] + 0.32)
        g["end"] = r3(end)
        g["start"] = r3(g["start"])
    return out


def is_keyword(text: str, kw_norm: list[list[str]], idx: int, tokens: list[str]) -> bool:
    for kw in kw_norm:
        L = len(kw)
        for off in range(L):
            s = idx - off
            if s >= 0 and s + L <= len(tokens) and tokens[s:s + L] == kw:
                return True
    return False


def srt_time(t: float) -> str:
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def cmd_captions(a):
    proj = Path(a.project).expanduser().resolve()
    cfg = load_json(proj / "neuro.json")
    sub = cfg["subtitles"]
    tpath = proj / (a.transcript or "assets/transcript.json")
    if not tpath.exists():
        die(f"Transcript não encontrado: {tpath}\n  rode: (cd {proj} && npx --yes hyperframes@{HF_VERSION} transcribe assets/base.mp4 --model small --language pt)")
    words = load_json(tpath)
    if isinstance(words, dict):
        words = words.get("words", [])
    words = [dict(w) for w in words if str(w.get("text", "")).strip() and not re.fullmatch(r"[♪�\W]+", str(w.get("text", "")))]
    # o transcript é sempre da fonte inteira (mezanino); o EDL leva as palavras para o tempo do filme depois
    src_duration = float(cfg.get("duracao_fonte", cfg["duration"]))
    words = [w for w in words if w["start"] < src_duration - 0.05]
    fs = final_silence_start(proj / cfg.get("mezanino", cfg["video"])) if cfg.get("video_has_audio") else None
    if fs is not None:
        dropped = [w["text"] for w in words if w["start"] >= fs + 0.05]
        if dropped:
            info(f"Removidas palavras alucinadas no silêncio final (≥{fs:.2f}s): {' '.join(dropped)}")
        words = [w for w in words if w["start"] < fs + 0.05]

    fixes = []
    for f in a.fix or []:
        if "=" not in f:
            die(f"--fix precisa ser 'errado=certo' (recebi: {f})")
        wrong, right = f.split("=", 1)
        fixes.append((wrong.strip(), right.strip()))
    profiles_all, *_ = load_presets()
    gl = load_glossary((profiles_all.get(cfg["profile"]) or {}).get("segment"))
    hits = []
    for wrong, right in gl.items():
        wt = [norm_token(t) for t in wrong.split()]
        for i in range(len(words) - len(wt) + 1):
            if all(norm_token(words[i + j]["text"]) == wt[j] for j in range(len(wt))):
                hits.append((wrong, right, words[i]["start"]))
    if hits:
        info("Glossário da memória encontrou termos suspeitos:")
        for wrong, right, t in hits:
            info(f"   {t:6.2f}s  '{wrong}' → '{right}'")
        if a.apply_glossary:
            fixes += [(w, r) for w, r, _ in hits]
        else:
            info("   (use --apply-glossary para aplicar, ou --fix 'errado=certo' um a um)")
    user_fixes = list(fixes[:len(a.fix or [])])
    total = 0
    for wrong, right in fixes:
        n = apply_fix(words, wrong, right)
        total += n
        info(f"Correção '{wrong}' → '{right}': {n}x")
    if a.learn and user_fixes:
        # só as correções que você deu com --fix; as do glossário já vêm da skill
        prof = cfg["profile"]
        up = update_user_memory(lambda m: m.setdefault("learned_preferences", {}).setdefault(prof, {}).setdefault("transcript_fixes", {}).update(dict(user_fixes)))
        info(f"Correções gravadas em {up} → learned_preferences.{prof}.transcript_fixes")
    elif a.learn:
        info("--learn: nenhuma correção sua (--fix) para gravar; as do glossário não são aprendidas.")
    for wrong, right in ((load_memory().get("learned_preferences", {}).get(cfg["profile"], {}) or {}).get("transcript_fixes", {}) or {}).items():
        if (wrong, right) not in fixes:
            n = apply_fix(words, wrong, right)
            if n:
                info(f"Correção aprendida '{wrong}' → '{right}': {n}x")

    for i, w in enumerate(words):
        w["id"] = f"w{i}"
    save_json(proj / "assets" / "transcript.fixed.json", words)
    emit_captions(proj, cfg, words, a.style, a.force_burn)


def caption_highlights(words: list[dict], sub: dict) -> list[bool]:
    kw_norm = [[norm_token(t) for t in k.split()] for k in sub.get("keywords", []) if k.strip()]
    tokens = [norm_token(w["text"]) for w in words]
    hl_on = bool(sub.get("highlight")) or bool(kw_norm)
    return [bool(hl_on and (is_keyword(w["text"], kw_norm, i, tokens) or (sub.get("highlight_numbers") and re.search(r"\d", w["text"]))))
            for i, w in enumerate(words)]


def write_caption_json(proj: Path, cfg: dict, words: list[dict], groups: list[dict], style: str):
    """Legendas em dados (tempo do filme), consumidas pelo motor Remotion e úteis para QA."""
    sub = cfg["subtitles"]
    hl = caption_highlights(words, sub)
    index_of = {id(w): i for i, w in enumerate(words)}
    save_json(proj / "dados" / "legendas.json", {
        "estilo": style, "queimar": bool(sub["enabled"]), "sub": sub,
        "grupos": [{"inicio": g["start"], "fim": g["end"],
                    "palavras": [{"texto": w["text"], "inicio": w["start"], "fim": w["end"], "destaque": hl[index_of[id(w)]]}
                                 for w in g["words"]]} for g in groups],
    })


def emit_captions(proj: Path, cfg: dict, words_src: list[dict], style: str | None = None, force_burn: bool = False, quiet: bool = False):
    """Palavras corrigidas (tempo da fonte) → tempo do filme pelo EDL → .srt + dados/legendas.json (+ captions.html no HyperFrames)."""
    import neuro_edl
    sub = cfg["subtitles"]
    duration = float(cfg["duration"])
    words = neuro_edl.remap_words(words_src, neuro_edl.load_edl(proj))
    save_json(proj / "dados" / "transcript.out.json", words)
    style = style or sub.get("style_mode", "pop")
    groups = build_groups(words, sub, duration)
    srt = []
    for gi, g in enumerate(groups):
        srt.append(f"{gi + 1}\n{srt_time(g['start'])} --> {srt_time(g['end'])}\n{' '.join(w['text'] for w in g['words'])}\n")
    (proj / "captions.srt").write_text("\n".join(srt), encoding="utf-8")
    if not quiet:
        info(f"captions.srt: {len(groups)} blocos")

    write_caption_json(proj, cfg, words, groups, style)
    if cfg.get("engine", "hyperframes") != "hyperframes":
        if not quiet:
            print(f"✓ dados/legendas.json: {len(groups)} blocos · estilo {style} (motor {cfg['engine']})")
        return
    burn = sub["enabled"] or force_burn
    if not burn:
        cap = proj / "compositions" / "captions.html"
        if cap.exists():
            cap.unlink()
        print("✓ Perfil sem legenda queimada: só captions.srt foi gerado (use --force-burn para queimar mesmo assim).")
        return

    kw_norm = [[norm_token(t) for t in k.split()] for k in sub.get("keywords", []) if k.strip()]
    tokens = [norm_token(w["text"]) for w in words]
    index_of = {id(w): i for i, w in enumerate(words)}
    hl_on = bool(sub.get("highlight")) or bool(kw_norm)
    W, H, fps = cfg["width"], cfg["height"], cfg["fps"]
    F = 1.0 / fps
    markup, tl = [], []
    for gi, g in enumerate(groups):
        gid = f"cap-g{gi}"
        spans = []
        for wi, w in enumerate(g["words"]):
            ti = index_of[id(w)]
            cls = "cap-w"
            if hl_on and (is_keyword(w["text"], kw_norm, ti, tokens) or (sub.get("highlight_numbers") and re.search(r"\d", w["text"]))):
                cls += " cap-hl"
            spans.append(f'<span id="{gid}-w{wi}" class="{cls}">{esc(w["text"])}</span>')
        markup.append(f'        <div id="{gid}" class="cap-group">{"".join(spans)}</div>')
        s, e = g["start"], g["end"]
        tl.append(f'      tl.fromTo("#{gid}", {{opacity: 0, y: 12, scale: 0.965, visibility: "visible"}}, {{opacity: 1, y: 0, scale: 1, duration: 0.14, ease: "power3.out"}}, {r3(s)});')
        if style == "karaoke":
            for wi, w in enumerate(g["words"]):
                tl.append(f'      tl.fromTo("#{gid}-w{wi}", {{opacity: 0.45}}, {{opacity: 1, duration: 0.09, ease: "power1.out"}}, {r3(max(s, w["start"] - 0.02))});')
        tl.append(f'      tl.fromTo("#{gid}", {{opacity: 1}}, {{opacity: 0, duration: 0.12, ease: "power2.in", immediateRender: false}}, {r3(e - 0.12)});')
        tl.append(f'      tl.fromTo("#{gid}", {{visibility: "visible"}}, {{visibility: "hidden", duration: 0, immediateRender: false}}, {r3(e)});')

    bottom = H - sub["anchor_y"] - round(sub["size"] * 0.6)
    stroke = max(0, float(sub["stroke_width"]))
    doc = f"""<template>
  <style>
    #root {{ position: absolute; inset: 0; }}
    #root .cap-group {{
      position: absolute;
      left: {sub['x_min']}px;
      width: {sub['max_width']}px;
      bottom: {bottom}px;
      text-align: center;
      font-family: "{sub['family']}", sans-serif;
      font-weight: {sub['weight']};
      font-style: {sub['style']};
      font-size: {sub['size']}px;
      line-height: 1.12;
      color: {sub['color']};
      -webkit-text-stroke: {stroke * 2:g}px {sub['stroke_color']};
      paint-order: stroke fill;
      text-shadow: {sub['shadow']};
      opacity: 0;
      overflow: visible;
    }}
    #root .cap-w {{ display: inline-block; margin: 0 0.12em; }}
    #root .cap-hl {{ color: var(--sub-hl, {sub.get('highlight') or '#FFD54A'}); }}
  </style>
  <div id="root" data-composition-id="captions" data-width="{W}" data-height="{H}">
    <div id="cap-layer" class="clip" data-start="0" data-duration="{r3(cfg['duration'])}" data-track-index="0">
{chr(10).join(markup)}
    </div>
  </div>
  <script>
    (function () {{
      const tl = gsap.timeline({{ paused: true }});
{chr(10).join(tl)}
      window.__timelines["captions"] = tl;
    }})();
  </script>
</template>
"""
    (proj / "compositions" / "captions.html").write_text(doc, encoding="utf-8")
    # regerado pela própria skill: atualiza o hash para o próximo build não confundir com edição no Studio
    st_path = proj / ".neuro-build.json"
    st = load_json(st_path, default={})
    if "compositions/captions.html" in (st.get("hashes") or {}):
        st["hashes"]["compositions/captions.html"] = file_hash(proj / "compositions" / "captions.html")
        save_json(st_path, st)
    print(f"✓ compositions/captions.html: {len(groups)} blocos · estilo {style} · fonte {sub['family']} {sub['weight']} {sub['size']}px · âncora y={sub['anchor_y']}")


# ───────────────────────────── cenas ─────────────────────────────

class Scene:
    def __init__(self, sid, dur, fps, ctx=None, warns=None):
        self.sid, self.dur, self.fps = sid, dur, fps
        self.F = 1.0 / fps
        self.ctx = ctx or {}
        self.warns = warns if warns is not None else []
        self.markup: list[str] = []
        self.js: list[str] = []
        # Mesmos tweens em forma de dados: o motor Remotion (@remotion/gsap) monta a timeline a partir daqui.
        self.tweens: list[dict] = []
        self.sfx: list[tuple[float, str]] = []
        self.vars: list[dict] = []
        self.words_to_read = 0
        self.entrance_end = 0.0

    def id(self, part):
        return f"{self.sid}-{part}"

    def fit(self, text: str, role: str, scale: float = 1.0) -> str:
        """Estilo inline que reduz a fonte só o necessário para caber numa linha da faixa.
        Até 15% é silencioso; além disso avisa: em vertical se cortam palavras, não se encolhe."""
        c = self.ctx
        if not c or not text:
            return ""
        px = c[f"{role}_px"] * scale
        fam = c[f"{role}_family"]
        em = FONT_WIDTH_EM.get(fam, 0.56)
        upper = text.upper() == text and any(ch.isalpha() for ch in text)
        if upper or c.get(f"{role}_upper"):
            em *= 1.12
        width = len(text) * em * px + c.get(f"{role}_ls", 0) * len(text)
        # faixa baixa (vertical, acima da cabeça): uma linha; faixa alta (painel 16:9): pode quebrar
        lines = 1
        if c["band_h"] >= px * 3.4:
            lines = 2
        if role == "support" and c["band_h"] >= px * 5:
            lines = 3
        avail = c["band_w"] * 0.96 * (1 if lines == 1 else lines * 0.88)
        if width <= avail:
            return ""
        k = max(0.55, avail / width)
        if k < 0.85:
            where = "uma linha" if lines == 1 else f"{lines} linhas"
            self.warns.append(f"{self.sid}: \"{text}\" é longo para {where} ({role} reduzido a {k:.0%}) — corte palavras.")
        return f' style="font-size: calc(var(--{ "hero" if role == "hook" else role}-size) * {k * scale:.3f})"'

    def var(self, vid, label, default):
        # O runtime publica cada variável como propriedade CSS --<id> dentro da cena:
        # o prefixo evita colisão com os tokens do tema (--accent, --label-size...).
        vid = f"txt-{vid}"
        self.vars.append({"id": vid, "type": "string", "label": label, "default": str(default)})
        return f'data-var-text="{vid}"'

    def ft(self, sel, frm, to, t, first=True):
        to = dict(to)
        if not first:
            to["immediateRender"] = False
        self.js.append(f'      tl.fromTo({js(sel)}, {js(frm)}, {js(to)}, {r3(t)});')
        self.tweens.append({"m": "fromTo", "sel": sel, "from": dict(frm), "to": to, "t": r3(t)})
        self.entrance_end = max(self.entrance_end, t + float(to.get("duration", 0)))

    def words(self, text, cls="nm-word", part="w"):
        out = []
        for i, w in enumerate(str(text).split()):
            out.append(f'<span id="{self.id(part)}{i}" class="{cls}">{esc(w)}</span>')
        return "".join(out), len(str(text).split())

    def exit_time(self, ex):
        return r3(self.dur - ex - self.F)

    def common_in_out(self, ex=0.26, hold=False):
        self.ft(f"#{self.id('scrim')}", {"opacity": 0}, {"opacity": 1, "duration": 0.4, "ease": "power2.out"}, 0)
        self.sfx.append((0.0, "whoosh"))
        landed = self.entrance_end
        self.exit_len = 0.0 if hold else ex + 0.05
        if not hold:
            X = self.exit_time(ex)
            self.ft(f"#{self.id('band')}", {"opacity": 1, "y": 0, "filter": "blur(0px)"},
                    {"opacity": 0, "y": -12, "filter": "blur(6px)", "duration": ex, "ease": "power3.in"}, X, first=False)
            self.ft(f"#{self.id('scrim')}", {"opacity": 1}, {"opacity": 0, "duration": ex + 0.06, "ease": "power2.in"}, X - 0.04, first=False)
        self.entrance_end = landed

    def min_duration(self):
        # chegada + leitura (0,5 s + 0,3 s por palavra, references/motion.md) + saída
        return r3(self.entrance_end + 0.5 + 0.3 * self.words_to_read + getattr(self, "exit_len", 0.3))


def sc_hook(s: Scene, v: dict):
    kicker, headline, accent = v.get("kicker", ""), v.get("headline", ""), v.get("accent", "")
    if not headline:
        die(f"Cena {s.sid} (hook) precisa de vars.headline")
    if kicker:
        s.markup.append(f'<div id="{s.id("pill")}" class="nm-pill" {s.var("kicker", "Pílula", kicker)}>{esc(kicker)}</div>')
    hw, n = s.words(headline)
    acc = f'<span id="{s.id("accent")}" class="nm-word nm-accent" {s.var("accent", "Palavra de impacto", accent)}>{esc(accent)}</span>' if accent else ""
    s.markup.append(f'<div id="{s.id("headline")}" class="nm-hero nm-row"{s.fit((headline + " " + accent).strip(), "hook")}>{hw}{acc}</div>')
    if v.get("bar"):
        s.markup.append(f'<div id="{s.id("track")}" class="nm-track"><div id="{s.id("fill")}" class="nm-fill"></div></div>')
    t = 0.05
    if kicker:
        s.ft(f"#{s.id('pill')}", {"opacity": 0, "y": 18, "scale": 0.9}, {"opacity": 1, "y": 0, "scale": 1, "duration": 0.38, "ease": "back.out(1.6)"}, t)
        s.sfx.append((t + 0.16, "pop"))
        t += 0.17
    for i in range(n):
        s.ft(f"#{s.id('w')}{i}", {"opacity": 0, "y": 8, "filter": "blur(8px)"}, {"opacity": 1, "y": 0, "filter": "blur(0px)", "duration": 0.16, "ease": "power4.out"}, t + i * 0.067)
    t_land = t + n * 0.067 + 0.12
    if accent:
        s.ft(f"#{s.id('accent')}", {"opacity": 0, "scale": 1.22}, {"opacity": 1, "scale": 1, "duration": 0.24, "ease": "expo.out"}, t_land)
        s.js.append(f'      tl.to("#{s.id("accent")}", {{keyframes: {{x: [6, -5, 4, -3, 2, 0]}}, duration: 0.33, ease: "none"}}, {r3(t_land + 0.05)});')
        s.tweens.append({"m": "to", "sel": f"#{s.id('accent')}", "to": {"keyframes": {"x": [6, -5, 4, -3, 2, 0]}, "duration": 0.33, "ease": "none"}, "t": r3(t_land + 0.05)})
        s.sfx.append((t_land + 0.02, "thud"))
        t_land += 0.3
    if v.get("bar"):
        X = s.exit_time(0.26)
        landed = s.entrance_end
        s.ft(f"#{s.id('track')}", {"opacity": 0}, {"opacity": 1, "duration": 0.2, "ease": "power2.out"}, t_land)
        # barra de prazo esvaziando: progresso constante é o único caso de ease linear
        s.ft(f"#{s.id('fill')}", {"scaleX": 1}, {"scaleX": 0.02, "duration": max(0.3, X - t_land - 0.2), "ease": "none"}, t_land + 0.2)
        s.entrance_end = landed + 0.2
    s.words_to_read = len((kicker + " " + headline + " " + accent).split())
    s.common_in_out()


def fmt_number_js(dec):
    return f'(n) => n.toLocaleString("pt-BR", {{minimumFractionDigits: {dec}, maximumFractionDigits: {dec}}})'


def sc_stat(s: Scene, v: dict):
    try:
        value = float(str(v.get("value")).replace(",", "."))
    except (TypeError, ValueError):
        die(f"Cena {s.sid} (stat) precisa de vars.value numérico (ex.: 2.3)")
    dec = int(v.get("decimals", 0 if float(value).is_integer() else 1))
    label, prefix, suffix = v.get("label", ""), v.get("prefix", ""), v.get("suffix", "")
    source = v.get("source", "")
    final_txt = f"{value:,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    if label:
        s.markup.append(f'<div id="{s.id("label")}" class="nm-label"{s.fit(label, "label")} {s.var("label", "Rótulo", label)}>{esc(label)}</div>')
    s.markup.append(
        f'<div id="{s.id("num")}" class="nm-data nm-row">'
        + (f'<span class="nm-unit nm-unit-pre nm-accent">{esc(prefix.strip())}</span>' if prefix.strip() else "")
        + f'<span id="{s.id("val")}">{esc(final_txt)}</span>'
        + (f'<span class="nm-unit nm-unit-suf nm-accent">{esc(suffix.strip())}</span>' if suffix.strip() else "")
        + "</div>"
    )
    pct = v.get("pct")
    if pct is not None:
        s.markup.append(f'<div id="{s.id("track")}" class="nm-track"><div id="{s.id("fill")}" class="nm-fill"></div></div>')
    if source:
        s.markup.append(f'<div id="{s.id("source")}" class="nm-source" {s.var("source", "Fonte", source)}>{esc(source)}</div>')
    if label:
        s.ft(f"#{s.id('label')}", {"opacity": 0, "y": 10}, {"opacity": 1, "y": 0, "duration": 0.3, "ease": "power3.out"}, 0.05)
    T, CD = 0.2, 0.65
    s.ft(f"#{s.id('num')}", {"opacity": 0, "y": 14, "filter": "blur(6px)"}, {"opacity": 1, "y": 0, "filter": "blur(0px)", "duration": 0.22, "ease": "power3.out"}, T)
    s.js.append(f'      const fmt = {fmt_number_js(dec)}; const el = document.getElementById("{s.id("val")}"); const c = {{v: 0}};')
    s.js.append(f'      tl.fromTo(c, {{v: 0}}, {{v: {value}, duration: {CD}, ease: "power2.out", onUpdate: () => {{ el.textContent = fmt(c.v); }}}}, {T});')
    # no Remotion o contador é derivado do quadro (o @remotion/gsap proíbe onUpdate e tween em objeto)
    s.tweens.append({"m": "contador", "sel": f"#{s.id('val')}", "de": 0, "ate": value, "casas": dec, "dur": CD, "ease": "power2.out", "t": T})
    s.ft(f"#{s.id('num')}", {"scale": 1.07}, {"scale": 1, "duration": 0.24, "ease": "expo.out"}, T + CD - 0.04, first=False)
    if pct is not None:
        s.ft(f"#{s.id('track')}", {"opacity": 0}, {"opacity": 1, "duration": 0.2, "ease": "power2.out"}, T)
        s.ft(f"#{s.id('fill')}", {"scaleX": 0}, {"scaleX": max(0.0, min(1.0, float(pct) / 100)), "duration": CD, "ease": "power2.out"}, T)
    if source:
        s.ft(f"#{s.id('source')}", {"opacity": 0}, {"opacity": 1, "duration": 0.3, "ease": "power2.out"}, T + CD)
    s.sfx += [(T, "tick"), (T + CD - 0.03, "pop")]
    s.words_to_read = len((label + " " + source).split()) + 2
    s.common_in_out()


def sc_quote(s: Scene, v: dict):
    pill, quote, source = v.get("pill", ""), v.get("quote", ""), v.get("source", "")
    if not quote and not pill:
        die(f"Cena {s.sid} (quote) precisa de vars.pill e/ou vars.quote")
    if pill:
        s.markup.append(f'<div id="{s.id("pill")}" class="nm-pill" {s.var("pill", "Artigo / referência", pill)}>{esc(pill)}</div>')
    s.markup.append(f'<div id="{s.id("line")}" class="nm-line"></div>')
    n = 0
    if quote:
        qw, n = s.words(quote)
        s.markup.append(f'<div id="{s.id("quote")}" class="nm-support nm-row"{s.fit(quote, "support")}>{qw}</div>')
    if source:
        s.markup.append(f'<div id="{s.id("source")}" class="nm-source" {s.var("source", "Fonte", source)}>{esc(source)}</div>')
    if pill:
        s.ft(f"#{s.id('pill')}", {"opacity": 0, "y": 16, "scale": 0.92}, {"opacity": 1, "y": 0, "scale": 1, "duration": 0.36, "ease": "back.out(1.5)"}, 0.05)
        s.sfx.append((0.2, "click"))
    s.ft(f"#{s.id('line')}", {"scaleX": 0}, {"scaleX": 1, "duration": 0.45, "ease": "expo.out"}, 0.24)
    s.sfx.append((0.26, "swipe"))
    for i in range(n):
        s.ft(f"#{s.id('w')}{i}", {"opacity": 0, "filter": "blur(6px)"}, {"opacity": 1, "filter": "blur(0px)", "duration": 0.13, "ease": "power2.out"}, 0.36 + i * 0.08)
    if source:
        s.ft(f"#{s.id('source')}", {"opacity": 0}, {"opacity": 1, "duration": 0.3, "ease": "power2.out"}, 0.42 + n * 0.08)
    s.words_to_read = len((pill + " " + quote + " " + source).split())
    s.common_in_out()


def sc_contrast(s: Scene, v: dict):
    label, wrong, right = v.get("label", ""), v.get("wrong", ""), v.get("right", "")
    if not wrong or not right:
        die(f"Cena {s.sid} (contrast) precisa de vars.wrong e vars.right")
    if label:
        s.markup.append(f'<div id="{s.id("label")}" class="nm-label" {s.var("label", "Rótulo", label)}>{esc(label)}</div>')
    s.markup.append(
        f'<div class="nm-strike-wrap"><div id="{s.id("wrong")}" class="nm-support"{s.fit(wrong, "support")} {s.var("wrong", "Termo equivocado", wrong)}>{esc(wrong)}</div>'
        f'<div id="{s.id("strike")}" class="nm-strike" data-layout-allow-occlusion></div></div>'
    )
    s.markup.append(f'<div id="{s.id("right")}" class="nm-hero nm-hero-sm nm-accent"{s.fit(right, "hook", 0.78)} {s.var("right", "Conceito correto", right)}>{esc(right)}</div>')
    t = 0.05
    if label:
        s.ft(f"#{s.id('label')}", {"opacity": 0, "y": 10}, {"opacity": 1, "y": 0, "duration": 0.3, "ease": "power3.out"}, t)
        t += 0.08
    s.ft(f"#{s.id('wrong')}", {"opacity": 0, "filter": "blur(8px)"}, {"opacity": 1, "filter": "blur(0px)", "duration": 0.18, "ease": "power3.out"}, t)
    # o termo errado precisa ser lido antes de ser riscado: 0,5 s + 0,3 s/palavra (ou o instante da fala em vars.right_at)
    r_at = float(v["right_at"]) if v.get("right_at") is not None else t + 0.18 + max(1.05, 0.5 + 0.3 * len(wrong.split()))
    s.ft(f"#{s.id('strike')}", {"scaleX": 0}, {"scaleX": 1, "duration": 0.32, "ease": "power3.out"}, r_at - 0.42)
    s.sfx.append((r_at - 0.42, "swipe"))
    s.ft(f"#{s.id('wrong')}", {"opacity": 1}, {"opacity": 0.42, "duration": 0.25, "ease": "power2.out"}, r_at - 0.12, first=False)
    s.ft(f"#{s.id('right')}", {"opacity": 0, "y": 16, "filter": "blur(10px)"}, {"opacity": 1, "y": 0, "filter": "blur(0px)", "duration": 0.3, "ease": "expo.out"}, r_at)
    s.sfx.append((r_at + 0.02, "thud"))
    s.words_to_read = len((label + " " + right).split())
    s.common_in_out()


CHECK_SVG = ('<svg class="nm-check" viewBox="0 0 40 40" aria-hidden="true">'
             '<circle id="{cid}" cx="20" cy="20" r="17" fill="none" stroke="var(--accent)" stroke-width="3" stroke-dasharray="107" stroke-dashoffset="107"/>'
             '<path id="{pid}" d="M12 20.5 L18 26.5 L28.5 14" fill="none" stroke="var(--accent)" stroke-width="3.4" stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="26" stroke-dashoffset="26"/></svg>')


def sc_checklist(s: Scene, v: dict):
    title, items = v.get("title", ""), [str(x) for x in (v.get("items") or [])]
    if not items:
        die(f"Cena {s.sid} (checklist) precisa de vars.items (lista)")
    if len(items) > 4:
        print(f"  ⚠ {s.sid}: {len(items)} itens não cabem na faixa acima da cabeça; use até 4 ou divida em duas cenas.", file=sys.stderr)
    at = v.get("item_at") or []
    if title:
        s.markup.append(f'<div id="{s.id("title")}" class="nm-label" {s.var("title", "Título", title)}>{esc(title)}</div>')
    rows = []
    for i, it in enumerate(items):
        svg = CHECK_SVG.format(cid=s.id(f"c{i}"), pid=s.id(f"p{i}"))
        rows.append(f'<div id="{s.id(f"i{i}")}" class="nm-item">{svg}<span id="{s.id(f"t{i}")}">{esc(it)}</span></div>')
    c = s.ctx or {}
    k = 1.0
    if c:
        avail = c["band_h"] - (c["label_px"] * 1.3 + 12 if title else 0)
        k = max(0.8, min(1.45, avail / (len(items) * c["item_px"] * 1.4)))
        longest = max(len(x) for x in items)
        k = min(k, (c["band_w"] * 0.9) / max(1.0, (longest * FONT_WIDTH_EM.get(c["item_family"], 0.57) + 1.6) * c["item_px"]))
    s.markup.append(f'<div class="nm-list" style="--item-k: {k:.3f}">{"".join(rows)}</div>')
    if title:
        s.ft(f"#{s.id('title')}", {"opacity": 0, "y": 10}, {"opacity": 1, "y": 0, "duration": 0.3, "ease": "power3.out"}, 0.05)
    for i in range(len(items)):
        t = float(at[i]) if i < len(at) else 0.32 + i * 0.42
        s.ft(f"#{s.id(f'i{i}')}", {"opacity": 0, "x": -14}, {"opacity": 1, "x": 0, "duration": 0.3, "ease": "power3.out"}, t)
        s.ft(f"#{s.id(f'c{i}')}", {"strokeDashoffset": 107}, {"strokeDashoffset": 0, "duration": 0.32, "ease": "power2.out"}, t)
        s.ft(f"#{s.id(f'p{i}')}", {"strokeDashoffset": 26}, {"strokeDashoffset": 0, "duration": 0.22, "ease": "power2.out"}, t + 0.16)
        s.sfx.append((t + 0.18, "pop"))
    s.words_to_read = len((title + " " + " ".join(items)).split())
    s.common_in_out()


def sc_timeline(s: Scene, v: dict):
    title, nodes = v.get("title", ""), [str(x) for x in (v.get("nodes") or [])]
    if not 2 <= len(nodes) <= 5:
        die(f"Cena {s.sid} (timeline) precisa de 2 a 5 vars.nodes")
    at = v.get("node_at") or []
    if title:
        s.markup.append(f'<div id="{s.id("title")}" class="nm-label" {s.var("title", "Título", title)}>{esc(title)}</div>')
    cols = []
    for i, nlabel in enumerate(nodes):
        cols.append(
            f'<div class="nm-node"><div id="{s.id(f"h{i}")}" class="nm-halo"></div><div id="{s.id(f"d{i}")}" class="nm-dot"><div id="{s.id(f"k{i}")}" class="nm-dot-core"></div></div>'
            f'<div id="{s.id(f"l{i}")}" class="nm-node-label">{esc(nlabel)}</div></div>'
        )
    s.markup.append(f'<div class="nm-nodes"><div id="{s.id("rail")}" class="nm-rail"><div id="{s.id("railfill")}" class="nm-rail-fill"></div></div>{"".join(cols)}</div>')
    if title:
        s.ft(f"#{s.id('title')}", {"opacity": 0, "y": 10}, {"opacity": 1, "y": 0, "duration": 0.3, "ease": "power3.out"}, 0.05)
    s.ft(f"#{s.id('rail')}", {"opacity": 0}, {"opacity": 1, "duration": 0.3, "ease": "power2.out"}, 0.1)
    times = [float(at[i]) if i < len(at) else 0.45 + i * 0.55 for i in range(len(nodes))]
    prev = 0.0
    for i, t in enumerate(times):
        dim_at = 0.1 + i * 0.04
        dimmed = t >= dim_at + 0.22
        if dimmed:
            s.ft(f"#{s.id(f'l{i}')}", {"opacity": 0}, {"opacity": 0.38, "duration": 0.2, "ease": "power2.out"}, dim_at)
        frac = i / (len(nodes) - 1)
        if i > 0:
            s.ft(f"#{s.id('railfill')}", {"scaleX": prev}, {"scaleX": frac, "duration": 0.35, "ease": "power2.inOut"}, t - 0.3, first=(i == 1))
        prev = frac
        s.ft(f"#{s.id(f'k{i}')}", {"opacity": 0}, {"opacity": 1, "duration": 0.12, "ease": "power2.out"}, t)
        s.ft(f"#{s.id(f'd{i}')}", {"scale": 1}, {"scale": 1.3, "duration": 0.12, "ease": "power2.out"}, t)
        s.ft(f"#{s.id(f'd{i}')}", {"scale": 1.3}, {"scale": 1, "duration": 0.3, "ease": "power2.inOut"}, t + 0.12, first=False)
        s.ft(f"#{s.id(f'h{i}')}", {"opacity": 0.7, "scale": 1}, {"opacity": 0, "scale": 2.3, "duration": 0.55, "ease": "power2.out"}, t)
        s.ft(f"#{s.id(f'l{i}')}", {"opacity": 0.38 if dimmed else 0}, {"opacity": 1, "duration": 0.2, "ease": "power2.out"}, t, first=not dimmed)
        s.sfx.append((t + 0.02, "pop"))
    s.words_to_read = len((title + " " + " ".join(nodes)).split())
    s.common_in_out()


def sc_cta(s: Scene, v: dict, film_dur: float, start: float):
    label, line, invite = v.get("label", ""), v.get("line", ""), v.get("invite", "")
    if not line:
        die(f"Cena {s.sid} (cta) precisa de vars.line")
    hold = v.get("hold_to_end", abs((start + s.dur) - film_dur) < 0.2)
    if label:
        s.markup.append(f'<div id="{s.id("label")}" class="nm-label" {s.var("label", "Rótulo", label)}>{esc(label)}</div>')
    lw, n = s.words(line)
    s.markup.append(f'<div id="{s.id("line")}" class="nm-support nm-row"{s.fit(line, "support")}>{lw}</div>')
    s.markup.append(f'<div id="{s.id("rule")}" class="nm-line"></div>')
    if invite:
        s.markup.append(f'<div id="{s.id("invite")}" class="nm-source" {s.var("invite", "Convite", invite)}>{esc(invite)}</div>')
    if label:
        s.ft(f"#{s.id('label')}", {"opacity": 0, "y": 10}, {"opacity": 1, "y": 0, "duration": 0.3, "ease": "power3.out"}, 0.05)
    for i in range(n):
        s.ft(f"#{s.id('w')}{i}", {"opacity": 0, "filter": "blur(6px)"}, {"opacity": 1, "filter": "blur(0px)", "duration": 0.13, "ease": "power2.out"}, 0.2 + i * 0.08)
    t = 0.2 + n * 0.08 + 0.05
    s.ft(f"#{s.id('rule')}", {"scaleX": 0}, {"scaleX": 1, "duration": 0.45, "ease": "expo.out"}, t)
    s.sfx += [(t, "swipe")]
    if invite:
        s.ft(f"#{s.id('invite')}", {"opacity": 0}, {"opacity": 1, "duration": 0.35, "ease": "power2.out"}, t + 0.3)
    s.words_to_read = len((label + " " + line + " " + invite).split())
    s.common_in_out(hold=bool(hold))


TEMPLATES = {"hook": sc_hook, "stat": sc_stat, "quote": sc_quote, "contrast": sc_contrast,
             "checklist": sc_checklist, "timeline": sc_timeline, "cta": sc_cta}
TEMPLATE_ALIASES = {"stat-counter": "stat", "citation": "quote", "law": "quote", "myth": "contrast", "list": "checklist", "steps": "timeline"}


def render_scene_file(s: Scene, W, H) -> str:
    vars_attr = esc(json.dumps(s.vars, ensure_ascii=False)) if s.vars else "[]"
    markup = "\n".join(f"        {m}" for m in s.markup)
    body = "\n".join(s.js)
    return f"""<template>
  <style>
    #root {{ position: absolute; inset: 0; }}
  </style>
  <div id="root" data-composition-id="{s.sid}" data-width="{W}" data-height="{H}" data-composition-variables="{vars_attr}">
    <div id="{s.id('clip')}" class="clip" data-start="0" data-duration="{r3(s.dur)}" data-track-index="0">
      <div id="{s.id('scrim')}" class="nm-scrim"></div>
      <div id="{s.id('band')}" class="nm-band">
{markup}
      </div>
    </div>
  </div>
  <script>
    (function () {{
      const tl = gsap.timeline({{ paused: true }});
{body}
      window.__timelines["{s.sid}"] = tl;
    }})();
  </script>
</template>
"""


# ───────────────────────────── câmera ─────────────────────────────

def scene_payload(s: Scene) -> dict:
    """Cartão em forma de dados (markup da faixa + tweens) para o motor Remotion."""
    return {"id": s.sid, "dur": r3(s.dur), "markup": "".join(s.markup), "tweens": s.tweens,
            "entrada_fim": r3(s.entrance_end), "sfx": [[r3(t), k] for t, k in s.sfx]}


def camera_js(cues: list[dict], cfg: dict, profile: dict) -> tuple[list[str], list[str]]:
    events, warns = camera_events(cues, cfg, profile)
    lines = []
    for ev in events:
        if ev["kind"] == "shake":
            amp, x = ev["amp"], ev["x"]
            lines.append(f'      tl.to("#cam", {{keyframes: {{x: [{amp}, {-amp * 0.8:g}, {amp * 0.6:g}, {-amp * 0.4:g}, {x}]}}, duration: {ev["dur"]}, ease: "none"}}, {r3(ev["t"])});')
            continue
        vars_ = dict(ev["to"])
        vars_.update({"duration": r3(max(ev["dur"], 0.001)), "ease": ev["ease"]})
        if lines:
            vars_["immediateRender"] = False
        lines.append(f'      tl.fromTo("#cam", {js(ev["from"])}, {js(vars_)}, {r3(ev["t"])});')
    return lines, warns


def camera_events(cues: list[dict], cfg: dict, profile: dict) -> tuple[list[dict], list[str]]:
    """Movimentos de câmera do cues.json em forma de dados: alimenta o GSAP (HyperFrames) e os keyframes (Remotion)."""
    fr = profile.get("framing_and_zoom") or {}
    punch = float(fr.get("punch_in_factor", fr.get("zoom_closed_factor", 1.07)))
    subtle = float(fr.get("zoom_subtle_factor", 1.05))
    state = {"scale": 1.0, "x": 0.0, "y": 0.0}
    out, warns = [], []
    D = cfg["duration"]
    events = sorted(cues, key=lambda c: float(c.get("at", c.get("from", 0))))
    last_end = 0.0

    def tween(t, dur, to, ease):
        nonlocal last_end
        frm = {k: state[k] for k in to}
        if t < last_end - 1e-3:
            warns.append(f"câmera: movimento em {t:.2f}s começa antes do anterior terminar ({last_end:.2f}s)")
        out.append({"kind": "tween", "t": t, "dur": dur, "from": frm, "to": dict(to), "ease": ease})
        state.update(to)
        last_end = t + dur

    for c in events:
        kind = c.get("kind", "punch_in")
        if kind in ("punch_in", "punch_in_emphasis"):
            t = float(c["at"])
            sc = float(c.get("scale", punch))
            tin, hold, tout = float(c.get("in", 0.18)), float(c.get("hold", 1.2)), float(c.get("out", 0.45))
            base = state["scale"]
            tween(t, tin, {"scale": sc}, "power3.out")
            if not c.get("stay"):
                tween(t + tin + hold, tout, {"scale": base}, "power2.inOut")
        elif kind in ("cut", "punch_cut", "punch_cut_alternating"):
            tween(float(c["at"]), 0.001, {"scale": float(c.get("scale", 1.08))}, "none")
        elif kind in ("zoom", "zoom_subtle_in", "zoom_subtle_out", "tension_creeper"):
            t0 = float(c.get("from", c.get("at", 0)))
            t1 = float(c.get("to", t0 + 4))
            default_to = 1.0 if kind == "zoom_subtle_out" else (1.08 if kind == "tension_creeper" else subtle)
            tween(t0, t1 - t0, {"scale": float(c.get("scale", default_to))}, c.get("ease", "power1.inOut"))
        elif kind in ("shift", "camera_dy_shift"):
            t = float(c["at"])
            tween(t, float(c.get("dur", 0.6)), {"y": float(c.get("dy", -190)), "x": float(c.get("dx", 0))}, "power2.inOut")
        elif kind in ("reset",):
            tween(float(c["at"]), float(c.get("dur", 0.5)), {"scale": 1.0, "x": 0.0, "y": 0.0}, "power2.inOut")
        elif kind in ("shake", "impact_tremor"):
            out.append({"kind": "shake", "t": float(c["at"]), "amp": float(c.get("amp", 6)), "dur": float(c.get("dur", 0.35)),
                        "x": state["x"], "y": state["y"], "scale": state["scale"]})
        else:
            warns.append(f"câmera: tipo '{kind}' desconhecido (use punch_in, cut, zoom, shift, reset, shake)")
        if last_end > D:
            warns.append(f"câmera: movimento termina em {last_end:.2f}s, depois do fim do vídeo ({D:.2f}s)")
    return out, warns


# ───────────────────────────── SFX ─────────────────────────────

def sfx_bank(proj: Path, cues_sfx: dict) -> dict[str, list[Path]]:
    bank: dict[str, list[Path]] = {k: [] for k in SFX_KINDS}
    for kind, files in (cues_sfx.get("bank") or {}).items():
        for f in files if isinstance(files, list) else [files]:
            p = (proj / f).resolve()
            if p.exists():
                bank.setdefault(kind, []).append(p)
    sdir = proj / "assets" / "sfx"
    if sdir.exists():
        for p in sorted(sdir.iterdir()):
            if p.suffix.lower() not in (".wav", ".mp3", ".m4a", ".aac", ".ogg", ".flac"):
                continue
            stem = p.stem.lower()
            for kind in SFX_KINDS:
                if stem.startswith(kind) and p not in bank[kind]:
                    bank[kind].append(p)
    return bank


def peak_cache(proj: Path) -> dict:
    return load_json(proj / "assets" / "sfx" / ".peaks.json", default={})


def get_peak(proj: Path, cache: dict, p: Path) -> tuple[float, float]:
    key = f"{p.name}:{p.stat().st_size}:{int(p.stat().st_mtime)}"
    if key not in cache:
        pk, dur = audio_peak_offset(p)
        cache[key] = [pk, dur]
    return tuple(cache[key])


# ───────────────────────────── build ─────────────────────────────

def file_hash(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16] if p.exists() else ""


def cmd_build(a):
    proj = Path(a.project).expanduser().resolve()
    cfg = load_json(proj / "neuro.json")
    cues = load_json(proj / "cues.json")
    profile = profile_for(cfg)
    W, H, fps, D = cfg["width"], cfg["height"], cfg["fps"], float(cfg["duration"])
    F = 1.0 / fps

    state_path = proj / ".neuro-build.json"
    prev = load_json(state_path, default={})
    if not a.force:
        changed = [f for f, h in (prev.get("hashes") or {}).items() if (proj / f).exists() and file_hash(proj / f) != h]
        if changed:
            die("Estes arquivos foram editados depois do último build (Studio/manual): "
                + ", ".join(changed) + "\n  Reaplique as mudanças em cues.json ou rode build --force (sobrescreve).")

    warns: list[str] = []
    scenes_out, sfx_events = build_scenes(cfg, cues, warns)
    for s in scenes_out:
        (proj / "compositions" / f"{s['id']}.html").write_text(render_scene_file(s["scene"], W, H), encoding="utf-8")

    cam_lines, cam_warns = camera_js(cues.get("camera", []), cfg, profile)
    warns += cam_warns

    audio_tags = []
    for ev in place_sfx(proj, cues, sfx_events, D, F, warns):
        ms = f' data-media-start="{r3(ev["skip"])}"' if ev["skip"] > 0 else ""
        audio_tags.append(f'      <audio id="sfx-{ev["n"]:02d}-{ev["sid"]}-{ev["kind"]}" class="clip" data-start="{r3(ev["start"])}" data-duration="{r3(ev["dur"])}" data-track-index="{10 + ev["lane"]}" data-volume="{ev["vol"]}"{ms} src="{ev["src"]}"></audio>')

    key = proj / cfg["video"] if cfg.get("video_has_audio") else None
    mt = music_track(proj, cues, D, warns, key, default_volume=estilo_music_volume(cfg))
    if mt:
        audio_tags.append(
            f'      <audio id="bgm" class="clip" data-start="{r3(mt["start"])}" data-duration="{r3(mt["dur"])}" '
            f'data-track-index="9" data-volume="{mt["volume"]}" data-fade-in="{mt["fade_in"]}" '
            f'data-fade-out="{mt["fade_out"]}"'
            + (f' data-media-start="{mt["media_start"]}"' if mt["media_start"] else "")
            + f' src="{esc(mt["src"])}"></audio>'
        )

    hosts = []
    for i, s in enumerate(scenes_out):
        hosts.append(
            f'      <div id="{s["id"]}" data-composition-id="{s["id"]}" data-composition-src="compositions/{s["id"]}.html" '
            f'data-start="{r3(s["start"])}" data-duration="{r3(s["dur"])}" data-track-index="{1 + (i % 2)}" data-track-kind="graphics" '
            f'data-width="{W}" data-height="{H}" style="z-index: {10 + i};"></div>'
        )
    return _build_finish(a, proj, cfg, cues, state_path, W, H, D, F, warns, scenes_out, cam_lines, audio_tags, hosts)


def build_scenes(cfg: dict, cues: dict, warns: list[str]) -> tuple[list[dict], list[tuple[float, str, str]]]:
    """cues.scenes → cenas validadas (objetos Scene) + eventos de SFX no tempo do filme. Comum aos dois motores."""
    fps, D = cfg["fps"], float(cfg["duration"])
    scenes_out, sfx_events = [], []
    seen = set()
    last_end = -1.0
    for sc in sorted(cues.get("scenes", []), key=lambda x: float(x["start"])):
        sid = re.sub(r"[^a-z0-9-]", "-", str(sc.get("id", "")).lower()).strip("-")
        if not sid or sid in seen or sid in ("main", "captions", "root", "cam", "base"):
            die(f"Cena com id inválido ou repetido: {sc.get('id')!r}")
        seen.add(sid)
        tname = TEMPLATE_ALIASES.get(sc.get("template"), sc.get("template"))
        if tname not in TEMPLATES:
            die(f"Cena {sid}: template '{sc.get('template')}' não existe. Opções: {', '.join(TEMPLATES)}")
        start, dur = float(sc["start"]), float(sc["duration"])
        if start < last_end - 1e-3:
            die(f"Cena {sid} começa em {start:.2f}s, antes da anterior terminar ({last_end:.2f}s). Cenas gráficas são estritamente sequenciais.")
        if start + dur > D + 1e-3:
            warns.append(f"{sid}: termina em {start + dur:.2f}s > duração do vídeo {D:.2f}s — encurtada.")
            dur = D - start
        if 0 <= start - last_end < 0.25 and last_end > 0:
            warns.append(f"{sid}: só {start - last_end:.2f}s de respiro depois da cena anterior (ideal ≥ 0,3s).")
        last_end = start + dur
        s = Scene(sid, dur, fps, cfg.get("type"), warns)
        fn = TEMPLATES[tname]
        if tname == "cta":
            fn(s, sc.get("vars", {}), D, start)
        else:
            fn(s, sc.get("vars", {}))
        need = s.min_duration()
        if dur + 1e-3 < need:
            warns.append(f"{sid}: {dur:.2f}s é curto para ler ({s.words_to_read} palavras) — mínimo sugerido {need:.2f}s.")
        scenes_out.append({"id": sid, "start": start, "dur": dur, "template": tname, "scene": s,
                           "motor": sc.get("motor"), "html": sc.get("html")})
        for t, kind in s.sfx:
            if t < dur:
                sfx_events.append((start + t, kind, sid))
        for extra in sc.get("sfx", []) or []:
            sfx_events.append((start + float(extra.get("at", 0)), extra.get("kind", "pop"), sid))
    if scenes_out and scenes_out[-1]["start"] + scenes_out[-1]["dur"] > D - 0.25 and scenes_out[-1]["dur"] < 2.0:
        warns.append(f"{scenes_out[-1]['id']}: a última linha do filme precisa de pelo menos 2 s na tela (tem {scenes_out[-1]['dur']:.2f}s).")
    gap_list = [b["start"] - (a_["start"] + a_["dur"]) for a_, b in zip(scenes_out, scenes_out[1:])]
    if scenes_out and D > 20 and len(scenes_out) < D / 12:
        warns.append(f"Densidade baixa: {len(scenes_out)} cenas em {D:.0f}s (referência: uma a cada 6–8 s em vídeos curtos).")
    if gap_list and max(gap_list) > 14:
        warns.append(f"Há um trecho de {max(gap_list):.1f}s sem nenhum estímulo gráfico — considere punch-in ou cena.")

    return scenes_out, sfx_events


def place_sfx(proj: Path, cues: dict, sfx_events: list, D: float, F: float, warns: list[str]) -> list[dict]:
    """Posiciona os SFX: pico do arquivo 1 quadro depois da imagem, tomadas em rodízio, raias sem sobreposição."""
    sfx_cfg = cues.get("sfx") or {}
    placed: list[dict] = []
    if not sfx_cfg.get("enabled", True):
        return placed
    bank = sfx_bank(proj, sfx_cfg)
    cache = peak_cache(proj)
    rot = {k: 0 for k in SFX_KINDS}
    lane_end: list[float] = []
    missing = set()
    gains = dict(SFX_GAIN_DB)
    gains.update({k: float(v) for k, v in (sfx_cfg.get("gain_db") or {}).items()})
    for n, (t, kind, sid) in enumerate(sorted(sfx_events)):
        k = kind
        while k and not bank.get(k):
            k = SFX_FALLBACK.get(k)
        if not k:
            missing.add(kind)
            continue
        files = bank[k]
        p = files[rot[k] % len(files)]
        rot[k] += 1
        pk, fdur = get_peak(proj, cache, p)
        st = t + F - pk
        skip = 0.0
        if st < 0:
            skip, st = -st, 0.0
        dur_ = min(fdur - skip, D - st)
        if dur_ <= 0.02:
            continue
        vol = round(10 ** (gains.get(kind, gains.get(k, -14.0)) / 20), 4)
        lane = next((i for i, e in enumerate(lane_end) if e <= st + 1e-3), None)
        if lane is None:
            lane_end.append(0.0)
            lane = len(lane_end) - 1
        lane_end[lane] = st + dur_
        placed.append({"n": n, "sid": sid, "kind": kind, "file_kind": k, "start": st, "dur": dur_, "skip": skip,
                       "vol": vol, "src": p.relative_to(proj).as_posix(), "lane": lane, "image_at": t})
    save_json(proj / "assets" / "sfx" / ".peaks.json", cache)
    if missing:
        warns.append("SFX sem arquivo para: " + ", ".join(sorted(missing))
                     + " — gere com ElevenLabs (text_to_sound_effects) em assets/sfx/<tipo>_NN.wav. Regra inegociável: nenhuma animação muda.")
    if not placed and sfx_events:
        warns.append("NENHUM SFX posicionado: o vídeo sairá sem sound design.")
    return placed


DUCK_DEFAULT = {"threshold": 0.03, "ratio": 4, "attack": 60, "release": 600}


def duck_music(proj: Path, mp: Path, key: Path, m_start: float, media_start: float, dur: float, params: dict) -> Path | None:
    """Trilha já abaixada sob a fala (sidechain com a voz do próprio filme). Cacheada por hash."""
    prm = dict(DUCK_DEFAULT)
    prm.update({k: v for k, v in params.items() if k in DUCK_DEFAULT})
    sig = f"{mp.resolve()}:{mp.stat().st_mtime_ns}:{key.resolve()}:{key.stat().st_mtime_ns}:{m_start}:{media_start}:{dur}:{sorted(prm.items())}"
    h = hashlib.sha256(sig.encode()).hexdigest()[:10]
    out_dir = proj / "assets" / "music" / "ducked"
    out = out_dir / f"{mp.stem}_duck_{h}.wav"
    if out.exists():
        return out
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob(f"{mp.stem}_duck_*.wav"):
        old.unlink()
    sc = f"sidechaincompress=threshold={prm['threshold']}:ratio={prm['ratio']}:attack={prm['attack']}:release={prm['release']}"
    res = run(["ffmpeg", "-v", "error", "-y", "-ss", f"{media_start:.3f}", "-t", f"{dur:.3f}", "-i", str(mp),
               "-ss", f"{m_start:.3f}", "-t", f"{dur:.3f}", "-i", str(key),
               "-filter_complex", "[0:a]aresample=48000,aformat=channel_layouts=stereo[m];"
               f"[1:a]aresample=48000,aformat=channel_layouts=stereo[k];[m][k]{sc}[o]",
               "-map", "[o]", "-c:a", "pcm_s16le", str(out)])
    if res.returncode != 0 or not out.exists():
        print(f"  ⚠ ducking da trilha falhou ({(res.stderr or '').strip()[-200:]}); usando a trilha sem ducking.", file=sys.stderr)
        return None
    return out


def estilo_music_volume(cfg: dict) -> float:
    return float(((cfg.get("estilo") or {}).get("trilha") or {}).get("volume", 0.14))


def music_track(proj: Path, cues: dict, D: float, warns: list[str], key_audio: Path | None, default_volume: float = 0.14) -> dict | None:
    """Trilha de fundo posicionada no filme. Com fala, a trilha sai abaixada por sidechain (regra §12)."""
    music = cues.get("music")
    if not (music and music.get("src")):
        return None
    mp = proj / music["src"]
    if not mp.exists():
        warns.append(f"Trilha {music['src']} não encontrada — ignorada.")
        return None
    md = media_info(mp)["duration"]
    m_start = float(music.get("start", 0))
    media_start = float(music.get("media_start", 0) or 0)
    dur = min(md - media_start, D - m_start)
    out = {"src": music["src"], "start": m_start, "dur": dur, "volume": float(music.get("volume", default_volume)),
           "fade_in": float(music.get("fade_in", 0.8)), "fade_out": float(music.get("fade_out", 1.2)),
           "media_start": float(music["media_start"]) if music.get("media_start") else 0, "ducked": False}
    duck = music.get("ducking", True)
    if duck and key_audio and key_audio.exists():
        dp = duck_music(proj, mp, key_audio, m_start, media_start, dur, duck if isinstance(duck, dict) else {})
        if dp:
            out.update({"src": dp.relative_to(proj).as_posix(), "media_start": 0, "ducked": True})
    return out


def _build_finish(a, proj, cfg, cues, state_path, W, H, D, F, warns, scenes_out, cam_lines, audio_tags, hosts):
    cap_file = proj / "compositions" / "captions.html"
    burn = cfg["subtitles"]["enabled"] or a.force_burn
    if cap_file.exists() and burn:
        hosts.append(
            f'      <div id="captions" data-composition-id="captions" data-composition-src="compositions/captions.html" data-start="0" '
            f'data-duration="{r3(D)}" data-track-index="3" data-track-kind="captions" data-width="{W}" data-height="{H}" style="z-index: 50;"></div>'
        )
    elif burn and not cap_file.exists():
        warns.append("Legendas do perfil estão ligadas, mas compositions/captions.html não existe — rode `captions`.")

    end = cues.get("end") or {}
    fade = end.get("fade_out", bool(cfg.get("rules", {}).get("final_fade_out", True)))
    end_lines = []
    if fade:
        fd = float(end.get("duration", 0.6))
        end_lines.append(f'      tl.fromTo("#endfade", {{opacity: 0}}, {{opacity: 1, duration: {r3(fd - F)}, ease: "power2.in"}}, {r3(D - fd)});')
    has_audio = "true" if cfg.get("video_has_audio") else None
    vid_audio = 'data-has-audio="true"' if has_audio else "muted"
    hx, hy = cfg["head"]["x"], cfg["head"]["y"]
    doc = f"""<!doctype html>
<html lang="pt-BR">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width={W}, height={H}" />
    <!-- Gerado por neuro-mv-edit {SKILL_VERSION} (scripts/hf_project.py build) a partir de cues.json. -->
    <script src="{GSAP_URL}"></script>
    <link rel="stylesheet" href="assets/neuro-theme.css" />
    <link rel="stylesheet" href="assets/neuro-components.css" />
    <style>
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{ margin: 0; width: {W}px; height: {H}px; overflow: hidden; background: var(--ground); }}
      #root {{ position: relative; width: 100%; height: 100%; overflow: hidden; }}
      #cam {{ position: absolute; left: 0; top: 0; width: {W}px; height: {H}px; transform-origin: {hx}px {hy}px; }}
      #base {{ position: absolute; left: 0; top: 0; width: {W}px; height: {H}px; object-fit: cover; }}
      #endfade {{ z-index: 90; }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{r3(D)}" data-width="{W}" data-height="{H}">
      <div id="cam">
        <video id="base" class="clip" data-start="0" data-duration="{r3(D)}" data-track-index="0" src="{cfg['video']}" {vid_audio} playsinline></video>
      </div>
{chr(10).join(hosts)}
{chr(10).join(audio_tags)}
      <div id="endfade" class="nm-endfade"></div>
    </div>
    <script>
      const tl = gsap.timeline({{ paused: true }});
{chr(10).join(cam_lines + end_lines)}
      window.__timelines["main"] = tl;
    </script>
  </body>
</html>
"""
    (proj / "index.html").write_text(doc, encoding="utf-8")
    tracked = ["index.html"] + [f"compositions/{s['id']}.html" for s in scenes_out]
    if cap_file.exists():
        tracked.append("compositions/captions.html")
    save_json(state_path, {"built_at": datetime.now().isoformat(timespec="seconds"), "hashes": {f: file_hash(proj / f) for f in tracked}})
    print(f"✓ build: {len(scenes_out)} cenas · {len(cam_lines)} movimentos de câmera · {len(audio_tags)} trilhas de áudio · fade final {'sim' if fade else 'não'}")
    for w in warns:
        print(f"  ⚠ {w}")


# ───────────────────────────── wrappers do CLI ─────────────────────────────

def project_cfg(a):
    proj = Path(a.project).expanduser().resolve()
    return proj, load_json(proj / "neuro.json")


def cmd_check(a):
    proj, cfg = project_cfg(a)
    W, H = cfg["width"], cfg["height"]
    sub = cfg["subtitles"]
    top = max(0.0, (sub["anchor_y"] - sub["size"] * 1.4) / H)
    bot = min(1.0, (sub["anchor_y"] + sub["size"] * 0.8) / H)
    zone = f"x0={sub['x_min'] / W:.3f};y0={top:.3f};x1={(sub['x_min'] + sub['max_width']) / W:.3f};y1={bot:.3f};severity=warning"
    args = ["check", "--caption-zone", zone]
    if a.json:
        args.append("--json")
    args += a.extra or []
    res = subprocess.run(hf_cmd(*args), cwd=str(proj), env=hf_env())
    sys.exit(res.returncode)


def passthrough(a, base_args):
    proj, cfg = project_cfg(a)
    res = subprocess.run(hf_cmd(*base_args, *(a.extra or [])), cwd=str(proj), env=hf_env())
    sys.exit(res.returncode)


def cmd_snapshot(a):
    extra = a.extra or []
    base = ["snapshot"] if any(x.startswith("--at") or x.startswith("--range") or x.startswith("--frames") or x == "--review" for x in extra) else ["snapshot", "--review"]
    passthrough(a, base)


def cmd_preview(a):
    passthrough(a, ["preview"])


def cmd_render(a):
    """Render HyperFrames nas resoluções e no codec decididos (neuro.json → export).

    H.264 em 1x/2x da composição sai direto do HyperFrames (uma codificação). HEVC, ProRes e escalas não inteiras
    (720p, 1440p) passam por um intermediário ProRes 422 HQ e uma única codificação final no ffmpeg."""
    import neuro_export as nx
    proj, cfg = project_cfg(a)
    profiles, *_ = load_presets()
    profile = profiles.get(cfg["profile"], {})
    rules = profile.get("strict_rules", {})
    stamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    if a.quality == "draft":
        out = a.output or f"renders/{proj.name}_{stamp}_rascunho.mp4"
        res = subprocess.run(hf_cmd("render", "--quality", "draft", "-o", out, "--strict", *(a.extra or [])), cwd=str(proj), env=hf_env())
        if res.returncode != 0:
            sys.exit(res.returncode)
        _registra_renders(proj, cfg, [{"resolucao": "rascunho", "arquivo": str((proj / out).resolve())}])
        return
    try:
        pl = nx.plano_projeto(cfg, profile, getattr(a, "resolucao", None), getattr(a, "codec", None), getattr(a, "qualidade", None))
    except ValueError as e:
        die(str(e))
    for av in pl["avisos"]:
        print(f"  ⚠ {av}", file=sys.stderr)
    W, H = int(cfg["width"]), int(cfg["height"])
    base = Path(a.output).expanduser() if a.output else proj / "renders" / f"{proj.name}_{stamp}{pl['ext']}"
    if not base.is_absolute():
        base = proj / base
    base.parent.mkdir(parents=True, exist_ok=True)
    feitos = []
    for i, saida in enumerate(pl["saidas"]):
        destino = nx.nome_saida(base, saida, i == 0, pl["ext"])
        preset = nx.hf_resolucao(W, H, saida)
        direto = pl["codec"] == "h264" and (preset or abs(saida["escala"] - 1) < 1e-6)
        print(f"▶ {saida['resolucao']} {saida['largura']}x{saida['altura']} · {pl['codec_nome']}" + ("" if direto else " (via ProRes HQ)"))
        if direto:
            args = ["render", "--quality", a.quality, "-o", str(destino), "--strict", "--crf", str(pl["crf"]),
                    "--video-frame-format", "png", "--sdr"] + (["--resolution", preset] if preset else [])
            res = subprocess.run(hf_cmd(*args, *(a.extra or [])), cwd=str(proj), env=hf_env())
            if res.returncode != 0:
                sys.exit(res.returncode)
        else:
            k = 2 if saida["escala"] > 1 + 1e-6 else 1
            tmp = proj / "renders" / ".intermediario" / f"{destino.stem}_prores.mov"
            tmp.parent.mkdir(parents=True, exist_ok=True)
            fake = {"largura": W * k, "altura": H * k, "escala": k}
            preset = nx.hf_resolucao(W, H, fake)
            args = ["render", "--quality", a.quality, "--format", "mov", "--prores-profile", "hq", "-o", str(tmp), "--strict",
                    "--video-frame-format", "png", "--sdr"] + (["--resolution", preset] if preset else [])
            res = subprocess.run(hf_cmd(*args, *(a.extra or [])), cwd=str(proj), env=hf_env())
            if res.returncode != 0:
                sys.exit(res.returncode)
            escalar = (W * k, H * k) != (saida["largura"], saida["altura"])
            r2 = run(nx.ffmpeg_final(pl, saida, tmp, destino, escalar), capture=True)
            if r2.returncode != 0:
                die("ffmpeg falhou na codificação final:\n" + r2.stderr[-1200:])
            tmp.unlink(missing_ok=True)
        _confere_render(destino, cfg)
        feitos.append({"resolucao": saida["resolucao"], "arquivo": str(destino.resolve()), "largura": saida["largura"],
                       "altura": saida["altura"], "codec": pl["codec"]})
    _registra_renders(proj, cfg, feitos)


def _confere_render(outp: Path, cfg: dict) -> None:
    if not outp.exists() or outp.stat().st_size < 1000:
        die(f"Render terminou mas {outp} está vazio.")
    __import__("neuro_export").corrige_tag_hevc(outp)
    mi = media_info(outp)
    dur = mi["duration"]
    if abs(dur - float(cfg["duration"])) > 2.0 / cfg["fps"] + 0.03:
        print(f"  ⚠ duração renderizada {dur:.3f}s ≠ projeto {cfg['duration']:.3f}s", file=sys.stderr)
    print(f"✓ render: {outp} ({mi['width']}x{mi['height']} · {mi['codec']} · {dur:.2f}s)")


def _registra_renders(proj: Path, cfg: dict, feitos: list[dict]) -> None:
    state = load_json(proj / ".neuro-build.json", default={})
    state["last_render"] = feitos[0]["arquivo"]
    state["last_renders"] = feitos
    save_json(proj / ".neuro-build.json", state)


# ───────────────────────────── master ─────────────────────────────

def cmd_master(a):
    """Loudness EBU R128 em 2 passagens; o vídeo é copiado sem recompressão. Sem --input, masteriza todas as
    resoluções do último render (a principal vira <NOME>_MASTER, as outras <NOME>_MASTER_<res>)."""
    proj, cfg = project_cfg(a)
    profiles, _, platforms, _ = load_presets()
    profile = profiles.get(cfg["profile"], {})
    state = load_json(proj / ".neuro-build.json", default={})
    if a.input:
        fontes = [{"resolucao": None, "arquivo": str(Path(a.input).expanduser().resolve())}]
    else:
        fontes = state.get("last_renders") or ([{"resolucao": None, "arquivo": state["last_render"]}] if state.get("last_render") else [])
    if not fontes or not all(Path(f["arquivo"]).is_file() for f in fontes):
        die("Informe --input <render> (ou rode `render` antes).")
    name = a.name or Path(fontes[0]["arquivo"]).stem
    masters = []
    for i, f in enumerate(fontes):
        suf = "" if i == 0 or not f.get("resolucao") else f"_{f['resolucao']}"
        masters.append(_master_um(proj, cfg, profile, Path(f["arquivo"]), f"{name}_MASTER{suf}", a, leve=(i == 0)))
    state["last_masters"] = [str(m) for m in masters if m]
    save_json(proj / ".neuro-build.json", state)
    print("  (medido, não ouvido: assista ao master inteiro antes de entregar — regra 11)")
    if masters and masters[0]:
        print(f"  próximo: python3 {SKILL_ROOT / 'scripts' / 'inject_metadata.py'} -i \"{masters[0]}\" -p {cfg['profile']} -t \"<hook>\"")


def _master_um(proj: Path, cfg: dict, profile: dict, src: Path, stem: str, a, leve: bool) -> Path | None:
    L = cfg.get("loudness", {})
    I, TP, LRA = float(a.lufs or L.get("target_lufs", -14)), float(L.get("true_peak", -1.5)), float(L.get("lra", 9))
    out_dir = proj / "renders" / "master"
    out_dir.mkdir(parents=True, exist_ok=True)
    mov = src.suffix.lower() == ".mov"
    master = out_dir / f"{stem}{'.mov' if mov else '.mp4'}"
    faststart = [] if mov else ["-movflags", "+faststart"]
    if not media_info(src)["has_audio"]:
        run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-c", "copy", *faststart, str(master)], check=True)
        print(f"⚠ {src.name} não tem áudio: master copiado sem loudness. Vídeo sem som viola a regra 7 (sound design).")
        return master

    print(f"▶ {src.name}: loudness 1ª passagem (alvo {I} LUFS · TP {TP} dBTP · LRA {LRA})")
    res = run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(src), "-af", f"loudnorm=I={I}:TP={TP}:LRA={LRA}:print_format=json", "-f", "null", "-"])
    m = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", res.stderr, re.S)
    if not m:
        die("Não foi possível medir o loudness (o render tem áudio?).")
    meas = json.loads(m.group(0))
    af = (f"loudnorm=I={I}:TP={TP}:LRA={LRA}:measured_I={meas['input_i']}:measured_TP={meas['input_tp']}:"
          f"measured_LRA={meas['input_lra']}:measured_thresh={meas['input_thresh']}:offset={meas['target_offset']}:linear=true,aresample=48000")
    print("▶ 2ª passagem + master (vídeo copiado sem recompressão)")
    acodec = ["-c:a", "pcm_s24le"] if mov else ["-c:a", "aac", "-b:a", "320k"]
    tag = ["-tag:v", "hvc1"] if media_info(src)["codec"] == "hevc" else []
    run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-map", "0:v:0", "-map", "0:a:0", "-c:v", "copy", *tag, "-af", af,
         *acodec, "-ar", "48000", *faststart, str(master)], check=True)
    report = {"source": str(src), "master": str(master), "target": {"I": I, "TP": TP, "LRA": LRA},
              "measured_before": {k: meas[k] for k in ("input_i", "input_tp", "input_lra")},
              "measured_after": measure_loudness(master), "duration_s": media_info(master)["duration"]}
    dual = (profile.get("strict_rules") or {}).get("dual_export_crf") or {}
    if leve and (dual.get("enabled") or a.light):
        light = out_dir / f"{stem}{dual.get('light_suffix', '_leve')}.mp4"
        run(["ffmpeg", "-v", "error", "-y", "-i", str(master), "-c:v", "libx264", "-preset", "slow", "-crf", str(dual.get("light_crf", 23)),
             "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(light)], check=True)
        report["light"] = str(light)
    aft = report["measured_after"]
    ok = abs(aft.get("integrated_lufs", 0) - I) <= 1.0 and aft.get("true_peak_dbtp", 0) <= TP + 0.5
    report["loudness_ok"] = ok
    save_json(out_dir / f"{stem}_loudness.json", report)
    vi = media_info(master)
    print(f"✓ master: {master} ({vi['width']}x{vi['height']} · {vi['codec']})")
    print(f"  loudness medido: {aft.get('integrated_lufs')} LUFS · TP {aft.get('true_peak_dbtp')} dBTP · LRA {aft.get('lra_lu')} LU {'✓' if ok else '⚠ fora do alvo'}")
    if report.get("light"):
        print(f"  cópia leve: {report['light']}")
    return master


# ───────────────────────────── CLI ─────────────────────────────

def main():
    p = argparse.ArgumentParser(description="Neuro MV Edit → HyperFrames", formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__.split("Uso rápido:")[1] if "Uso rápido:" in __doc__ else "")
    sp = p.add_subparsers(dest="cmd", required=True)

    i = sp.add_parser("init", help="cria o projeto HyperFrames a partir do perfil")
    __import__("neuro_export").add_args(i)
    i.add_argument("--profile", "-p", required=True)
    i.add_argument("--video", "-v", required=True, help="vídeo bruto ou já decupado")
    i.add_argument("--out", "-o", required=True, help="pasta do projeto")
    i.add_argument("--platform", help="instagram_reels | tiktok | youtube_shorts | youtube_horizontal | instagram_feed_portrait")
    i.add_argument("--theme", help="sobrescreve o tema do perfil")
    i.add_argument("--estilo", help="estilo de edição (presets/estilos.json ou biblioteca do usuário)")
    i.add_argument("--head-y", type=int, help="topo do cabelo medido no vídeo (px)")
    i.add_argument("--head-x", type=int, help="centro horizontal da cabeça (px)")
    i.add_argument("--layout", choices=["split_lateral", "lower_third"], help="16:9: painel lateral (padrão) ou lower third")
    i.add_argument("--no-grade", action="store_true", help="não aplicar a grade FFmpeg do perfil")
    i.add_argument("--reencode", action="store_true", help="forçar recodificação do vídeo base")
    i.add_argument("--force", action="store_true")
    i.set_defaults(fn=cmd_init)

    c = sp.add_parser("captions", help="transcript → legendas do perfil")
    c.add_argument("--project", required=True)
    c.add_argument("--transcript", help="relativo ao projeto (padrão assets/transcript.json)")
    c.add_argument("--fix", action="append", help="'errado=certo' (repetível; aceita várias palavras)")
    c.add_argument("--apply-glossary", action="store_true", help="aplica o glossário da memória (data/memory.json da skill + ~/.neuro-mv-edit/memory.json)")
    c.add_argument("--learn", action="store_true", help="grava as correções do --fix em ~/.neuro-mv-edit/memory.json para os próximos vídeos")
    c.add_argument("--style", choices=["pop", "karaoke"], help="pop (bloco) ou karaoke (palavra acende)")
    c.add_argument("--force-burn", action="store_true", help="queima legenda mesmo se o perfil proíbe")
    c.set_defaults(fn=cmd_captions)

    b = sp.add_parser("build", help="cues.json → index.html + cenas + SFX")
    b.add_argument("--project", required=True)
    b.add_argument("--force", action="store_true", help="sobrescreve arquivos editados fora do build")
    b.add_argument("--force-burn", action="store_true")
    b.set_defaults(fn=cmd_build)

    for name, fn in (("check", cmd_check), ("snapshot", cmd_snapshot), ("preview", cmd_preview)):
        x = sp.add_parser(name, help=f"hyperframes {name} no projeto")
        x.add_argument("--project", required=True)
        if name == "check":
            x.add_argument("--json", action="store_true")
        x.add_argument("extra", nargs=argparse.REMAINDER, help="argumentos extras repassados ao hyperframes")
        x.set_defaults(fn=fn)

    r = sp.add_parser("render", help="hyperframes render nas resoluções e no codec decididos")
    r.add_argument("--project", required=True)
    __import__("neuro_export").add_args(r, render=True)
    r.add_argument("--quality", default="delivery", choices=["draft", "looks", "delivery"])
    r.add_argument("--output", "-o")
    r.add_argument("extra", nargs=argparse.REMAINDER)
    r.set_defaults(fn=cmd_render)

    m = sp.add_parser("master", help="loudness 2 passagens + cópia leve")
    m.add_argument("--project", required=True)
    m.add_argument("--input", "-i", help="render a masterizar (padrão: último render)")
    m.add_argument("--name", help="nome base do arquivo final")
    m.add_argument("--lufs", type=float, help="sobrescreve o alvo de loudness")
    m.add_argument("--light", action="store_true", help="gera cópia leve mesmo sem regra do perfil")
    m.add_argument("--network", help="(informativo) rede de destino")
    m.set_defaults(fn=cmd_master)

    a = p.parse_args()
    if getattr(a, "extra", None) and a.extra and a.extra[0] == "--":
        a.extra = a.extra[1:]
    a.fn(a)


if __name__ == "__main__":
    main()

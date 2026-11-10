#!/usr/bin/env python3
"""
neuro_edl.py — decupagem da skill neuro-mv-edit: lista de cortes (edl.json), sugestão automática de cortes,
remapeamento de tempos (fonte ↔ filme) e montagem da fala/vídeo pelo ffmpeg.

O EDL vale para os dois motores:
  - Remotion: cada segmento vira um clipe `<Video trimBefore durationInFrames>` editável no Studio,
    e a fala sai de `dados/fala-<hash>.wav`, montada aqui com precisão de amostra;
  - HyperFrames: o ffmpeg monta `assets/base_cortado.mp4` e o HyperFrames recebe o vídeo já cortado.

Formato (quadros na fps do projeto; `out` é exclusivo):
  {"versao": 1, "fps": 30, "fonte": "assets/base.mp4", "quadros_fonte": 520, "preset": "natural",
   "segmentos": [{"id": "c01", "in": 0, "out": 120, "motivo": "fala"}],
   "removidos": [{"de": 4.02, "ate": 4.71, "motivo": "silêncio 0,69 s"}]}

Somente biblioteca padrão do Python 3.10+. Requer ffmpeg.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import subprocess
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

EDL_FILE = "edl.json"

# Presets de respiro (SKILL §10.3). pad_* = silêncio mantido antes/depois da fala em cada emenda.
PRESETS = {
    "natural": {"limiar": 0.24, "pad_antes": 0.09, "pad_depois": 0.12, "cabeca": 0.10, "cauda": 0.60},
    "tight": {"limiar": 0.12, "pad_antes": 0.04, "pad_depois": 0.06, "cabeca": 0.08, "cauda": 0.50},
}


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFD", s.lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^\w]+", " ", s).strip()


# ───────────────────────────── leitura / escrita ─────────────────────────────

def load_edl(proj: Path) -> dict | None:
    p = proj / EDL_FILE
    if not p.exists():
        return None
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def save_edl(proj: Path, edl: dict):
    edl = dict(edl)
    edl["segmentos"] = [dict(s) for s in edl["segmentos"]]
    for i, s in enumerate(edl["segmentos"]):
        s.setdefault("id", f"c{i + 1:02d}")
        s["in_s"] = round(s["in"] / edl["fps"], 3)
        s["out_s"] = round(s["out"] / edl["fps"], 3)
    edl["quadros_saida"] = total_frames(edl)
    edl["duracao_saida"] = round(edl["quadros_saida"] / edl["fps"], 3)
    edl.setdefault("_ajuda", "Cortes no tempo da fonte, em quadros (out exclusivo). Edite e rode `build`; "
                             "no motor Remotion o Studio grava aqui via `sincronizar`.")
    tmp = proj / (EDL_FILE + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(edl, f, ensure_ascii=False, indent=2)
        f.write("\n")
    tmp.replace(proj / EDL_FILE)


def identity_edl(fps: int, quadros_fonte: int, fonte: str) -> dict:
    return {"versao": 1, "fps": fps, "fonte": fonte, "quadros_fonte": quadros_fonte, "preset": "nenhum",
            "segmentos": [{"id": "c01", "in": 0, "out": quadros_fonte, "motivo": "vídeo inteiro"}], "removidos": []}


def total_frames(edl: dict) -> int:
    return sum(max(0, int(s["out"]) - int(s["in"])) for s in edl["segmentos"])


def edl_signature(edl: dict) -> str:
    raw = json.dumps([[int(s["in"]), int(s["out"])] for s in edl["segmentos"]] + [edl["fps"], edl.get("fonte")])
    return hashlib.sha256(raw.encode()).hexdigest()[:10]


def _starts(edl: dict) -> list[int]:
    acc, out = 0, []
    for s in edl["segmentos"]:
        out.append(acc)
        acc += int(s["out"]) - int(s["in"])
    return out


# ───────────────────────────── remapeamento ─────────────────────────────

def src_to_out(edl: dict, t: float) -> float | None:
    """Segundo da fonte → segundo do filme (None se o trecho foi cortado)."""
    fps = edl["fps"]
    f = t * fps
    for st, s in zip(_starts(edl), edl["segmentos"]):
        if s["in"] - 1e-6 <= f <= s["out"] + 1e-6:
            return (st + (f - s["in"])) / fps
    return None


def out_to_src(edl: dict, t: float) -> float:
    """Segundo do filme → segundo da fonte (fora do filme: extrapola pelo segmento mais próximo)."""
    fps = edl["fps"]
    f = t * fps
    starts = _starts(edl)
    for st, s in zip(starts, edl["segmentos"]):
        ln = s["out"] - s["in"]
        if st - 1e-6 <= f <= st + ln + 1e-6:
            return (s["in"] + (f - st)) / fps
    if not edl["segmentos"]:
        return t
    if f < 0:
        return edl["segmentos"][0]["in"] / fps + t
    last = edl["segmentos"][-1]
    return (last["out"] + (f - total_frames(edl))) / fps


def remap_time(t_out_old: float, old: dict, new: dict) -> float | None:
    """Tempo do filme no EDL antigo → tempo do filme no EDL novo, ancorado na fonte."""
    src = out_to_src(old, t_out_old)
    t = src_to_out(new, src)
    if t is not None:
        return t
    # caiu num trecho que saiu: gruda no começo do próximo segmento mantido
    fps = new["fps"]
    for st, s in zip(_starts(new), new["segmentos"]):
        if s["in"] / fps >= src:
            return st / fps
    return total_frames(new) / fps


def remap_words(words: list[dict], edl: dict | None) -> list[dict]:
    """Palavras no tempo da fonte → tempo do filme. Palavra cujo meio foi cortado sai."""
    if not edl:
        return [dict(w) for w in words]
    fps = edl["fps"]
    out = []
    for w in words:
        mid = (w["start"] + w["end"]) / 2
        tm = src_to_out(edl, mid)
        if tm is None:
            continue
        # limita início/fim ao segmento que contém o meio da palavra
        for st, s in zip(_starts(edl), edl["segmentos"]):
            if s["in"] / fps - 1e-6 <= mid <= s["out"] / fps + 1e-6:
                a = max(w["start"], s["in"] / fps)
                b = min(w["end"], s["out"] / fps)
                nw = dict(w)
                nw["start"] = round((st + a * fps - s["in"]) / fps, 3)
                nw["end"] = round((st + b * fps - s["in"]) / fps, 3)
                out.append(nw)
                break
    return out


def remap_cues(cues: dict, old: dict, new: dict, keep_scene_ids: set[str] | None = None) -> tuple[dict, list[str]]:
    """Move cenas, câmera, efeitos e B-roll do filme antigo para o novo, ancorados na fonte."""
    keep_scene_ids = keep_scene_ids or set()
    notes = []
    cues = json.loads(json.dumps(cues))
    for sc in cues.get("scenes", []):
        if str(sc.get("id")) in keep_scene_ids:
            continue
        a, b = float(sc["start"]), float(sc["start"]) + float(sc["duration"])
        na, nb = remap_time(a, old, new), remap_time(b, old, new)
        if nb - na < 0.4:
            nb = na + float(sc["duration"])
            notes.append(f"cena {sc.get('id')}: o trecho de fala dela foi cortado; mantive a duração original.")
        sc["start"], sc["duration"] = round(na, 3), round(nb - na, 3)
    for c in cues.get("camera", []):
        for k in ("at", "from", "to"):
            if k in c:
                c[k] = round(remap_time(float(c[k]), old, new), 3)
    for key in ("efeitos", "broll"):
        for e in cues.get(key, []) or []:
            for k in ("at", "start"):
                if k in e:
                    e[k] = round(remap_time(float(e[k]), old, new), 3)
    return cues, notes


# ───────────────────────────── sugestão de cortes ─────────────────────────────

def detect_silences(media: Path, noise_db: float, min_d: float) -> list[tuple[float, float]]:
    res = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(media), "-af",
                          f"silencedetect=noise={noise_db:.1f}dB:d={min_d}", "-f", "null", "-"],
                         capture_output=True, text=True)
    starts = [float(x) for x in re.findall(r"silence_start: (-?[\d.]+)", res.stderr)]
    ends = [float(x) for x in re.findall(r"silence_end: (-?[\d.]+)", res.stderr)]
    out = []
    for i, s in enumerate(starts):
        e = ends[i] if i < len(ends) else float("inf")
        out.append((max(0.0, s), e))
    return out


def speech_loudness(media: Path) -> float | None:
    res = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(media), "-af", "ebur128", "-f", "null", "-"],
                         capture_output=True, text=True)
    m = re.findall(r"I:\s+(-?[\d.]+) LUFS", res.stderr)
    return float(m[-1]) if m else None


def _parse_range(r: str) -> tuple[float, float]:
    m = re.fullmatch(r"\s*([\d.]+)\s*[-–:]\s*([\d.]+)\s*", r)
    if not m:
        raise ValueError(f"intervalo inválido '{r}' (use 12.3-15.8, em segundos da fonte)")
    a, b = float(m.group(1)), float(m.group(2))
    return (min(a, b), max(a, b))


def _union(ranges: list[tuple[float, float, str]]) -> list[tuple[float, float, str]]:
    out = []
    for a, b, why in sorted(ranges):
        if out and a <= out[-1][1] + 1e-6:
            pa, pb, pw = out[-1]
            out[-1] = (pa, max(pb, b), pw if pb - pa >= b - a else why)
        else:
            out.append((a, b, why))
    return out


def suggest_edl(words: list[dict], media: Path, fps: int, quadros_fonte: int, fonte_rel: str, preset: str = "natural",
                pacing: dict | None = None, remover: list[str] | None = None, manter: list[str] | None = None,
                usar_silencio: bool = True, limiar_ms: float | None = None) -> tuple[dict, list[str]]:
    """Cortes sugeridos: buracos entre palavras (Whisper) confirmados pelo silencedetect, no meio do silêncio.
    Limiar: `limiar_ms` (opção ou estilo do projeto) > ritmo aprendido do perfil (só no natural) > preset."""
    pacing = pacing or {}
    P = dict(PRESETS.get(preset, PRESETS["natural"]))
    if limiar_ms:
        k = (float(limiar_ms) / 1000) / P["limiar"]
        P["limiar"] = float(limiar_ms) / 1000
        P["pad_antes"], P["pad_depois"] = P["pad_antes"] * k, P["pad_depois"] * k
    elif pacing.get("breath_cut_threshold_ms") and preset == "natural":
        lim = float(pacing["breath_cut_threshold_ms"]) / 1000
        P["limiar"] = lim
        tot = P["pad_antes"] + P["pad_depois"]
        P["pad_antes"], P["pad_depois"] = lim * P["pad_antes"] / tot, lim * P["pad_depois"] / tot
    dur_src = quadros_fonte / fps
    notes: list[str] = []
    ws = sorted([w for w in words if str(w.get("text", "")).strip()], key=lambda w: w["start"])
    cuts: list[tuple[float, float, str]] = []

    sil = []
    if usar_silencio:
        I = speech_loudness(media)
        noise = max(-55.0, (I if I is not None else -23.0) - 20.0)
        sil = detect_silences(media, noise, 0.08)

    def confirm(a: float, b: float, gap: float) -> tuple[float, float] | None:
        """Encolhe o corte para dentro do silêncio medido. Buraco do Whisper sem silêncio medido NÃO é cortado:
        o Whisper erra fim/início de palavra e cortar ali come fala (respiro, ruído e palavra arrastada também caem aqui)."""
        if not usar_silencio:
            a2, b2 = a + 0.05, b - 0.05
            return (a2, b2) if b2 - a2 >= 2 / fps else None
        best = None
        for s, e in sil:
            lo, hi = max(a, s + 0.02), min(b, e - 0.02)
            if hi - lo > (best[1] - best[0] if best else 0):
                best = (lo, hi)
        if best and best[1] - best[0] >= 2 / fps:
            return best
        notes.append(f"buraco de {gap:.2f}s entre palavras em {a:.2f}s sem silêncio medido — mantido "
                     f"(se for respiro ou ruído, remova com --remover {a:.2f}-{b:.2f})")
        return None

    if ws:
        head = ws[0]["start"] - P["cabeca"]
        if head > 2 / fps:
            c = confirm(0.0, head, head)
            if c:
                cuts.append((0.0 if c[0] <= 0.05 else c[0], c[1], "silêncio inicial"))
        for prev, nxt in zip(ws, ws[1:]):
            gap = nxt["start"] - prev["end"]
            if gap <= P["limiar"] + 2 / fps:
                continue
            c = confirm(prev["end"] + P["pad_antes"], nxt["start"] - P["pad_depois"], gap)
            if c:
                cuts.append((c[0], c[1], f"silêncio {gap:.2f}s".replace(".", ",")))
        tail = ws[-1]["end"] + P["cauda"]
        if dur_src - tail > 2 / fps:
            c = confirm(tail, dur_src, dur_src - tail)
            if c:
                cuts.append((c[0], dur_src if dur_src - c[1] <= 0.05 else c[1], "silêncio final"))

    # deixas de claquete/erro ("Eu errei a frase", "De novo"...): sai a deixa; a tomada anterior fica como suspeita
    cues_txt = [_norm(c) for c in (pacing.get("clapper_cues") or []) if _norm(c)]
    toks = [_norm(w["text"]) for w in ws]
    for cue in cues_txt:
        ct = cue.split()
        for i in range(len(toks) - len(ct) + 1):
            if toks[i:i + len(ct)] == ct:
                a, b = ws[i]["start"] - 0.05, ws[i + len(ct) - 1]["end"] + 0.05
                cuts.append((max(0.0, a), b, f"deixa de claquete '{cue}'"))
                j = i - 1
                while j > 0 and not re.search(r"[.!?…]$", ws[j - 1]["text"]):
                    j -= 1
                if j >= 0 and j < i:
                    notes.append(f"possível tomada repetida antes de '{cue}': {ws[j]['start']:.2f}–{ws[i - 1]['end']:.2f}s "
                                 f"(\"{' '.join(w['text'] for w in ws[j:i])[:80]}\") — confirme com --remover {ws[j]['start']:.2f}-{ws[i]['start']:.2f}")

    for r in remover or []:
        a, b = _parse_range(r)
        cuts.append((a, min(b, dur_src), "removido à mão"))
    protect = [_parse_range(r) for r in (manter or [])]
    if protect:
        kept_cuts = []
        for a, b, why in cuts:
            pieces = [(a, b)]
            for pa, pb in protect:
                nxt_p = []
                for x, y in pieces:
                    if pb <= x or pa >= y:
                        nxt_p.append((x, y))
                        continue
                    if x < pa:
                        nxt_p.append((x, pa))
                    if pb < y:
                        nxt_p.append((pb, y))
                pieces = nxt_p
            kept_cuts += [(x, y, why) for x, y in pieces if y - x >= 2 / fps]
        cuts = kept_cuts

    cuts = _union([(max(0.0, a), min(dur_src, b), w) for a, b, w in cuts if b - a > 0])
    # cortes no meio do silêncio, quantizados para quadros sem invadir a fala
    segs, removed = [], []
    cur = 0
    for a, b, why in cuts:
        fa, fb = math.ceil(a * fps - 1e-6), math.floor(b * fps + 1e-6)
        if fb - fa < 2:
            continue
        if fa > cur:
            segs.append({"in": cur, "out": fa, "motivo": "fala"})
        removed.append({"de": round(fa / fps, 3), "ate": round(fb / fps, 3), "motivo": why})
        cur = max(cur, fb)
    if cur < quadros_fonte:
        segs.append({"in": cur, "out": quadros_fonte, "motivo": "fala"})
    segs = [s for s in segs if s["out"] - s["in"] >= 3] or [{"in": 0, "out": quadros_fonte, "motivo": "vídeo inteiro"}]
    for i, s in enumerate(segs):
        s["id"] = f"c{i + 1:02d}"
    edl = {"versao": 1, "fps": fps, "fonte": fonte_rel, "quadros_fonte": quadros_fonte, "preset": preset,
           "parametros": {k: round(v, 3) for k, v in P.items()}, "gerado_em": datetime.now().isoformat(timespec="seconds"),
           "segmentos": segs, "removidos": removed}
    return edl, notes


# ───────────────────────────── montagem pelo ffmpeg ─────────────────────────────

def assemble_audio(src: Path, edl: dict, out: Path, fade_ms: float = 10.0) -> Path:
    """Fala do filme: cada segmento com fade de entrada/saída (sem sobrepor, sem deriva) e concatenado."""
    fps = edl["fps"]
    d = fade_ms / 1000
    parts, labels = [], []
    for i, s in enumerate(edl["segmentos"]):
        a, b = s["in"] / fps, s["out"] / fps
        ln = b - a
        fd = min(d, ln / 4)
        parts.append(f"[0:a]atrim=start={a:.6f}:end={b:.6f},asetpts=PTS-STARTPTS,aresample=48000,"
                     f"afade=t=in:st=0:d={fd:.4f},afade=t=out:st={max(0.0, ln - fd):.6f}:d={fd:.4f}[a{i}]")
        labels.append(f"[a{i}]")
    graph = ";\n".join(parts) + ";\n" + "".join(labels) + f"concat=n={len(labels)}:v=0:a=1[out]"
    out.parent.mkdir(parents=True, exist_ok=True)
    res = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-filter_complex", graph, "-map", "[out]",
                          "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2", str(out)], capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError("ffmpeg falhou ao montar a fala:\n" + res.stderr[-1200:])
    return out


def assemble_video(src: Path, edl: dict, out: Path, has_audio: bool, fade_ms: float = 10.0) -> Path:
    """Motor HyperFrames: vídeo já cortado (mesma codificação do mezanino) + fala com fades nas emendas."""
    fps = edl["fps"]
    d = fade_ms / 1000
    parts, labels = [], []
    for i, s in enumerate(edl["segmentos"]):
        parts.append(f"[0:v]trim=start_frame={int(s['in'])}:end_frame={int(s['out'])},setpts=PTS-STARTPTS[v{i}]")
        lab = f"[v{i}]"
        if has_audio:
            a, b = s["in"] / fps, s["out"] / fps
            ln = b - a
            fd = min(d, ln / 4)
            parts.append(f"[0:a]atrim=start={a:.6f}:end={b:.6f},asetpts=PTS-STARTPTS,aresample=48000,"
                         f"afade=t=in:st=0:d={fd:.4f},afade=t=out:st={max(0.0, ln - fd):.6f}:d={fd:.4f}[a{i}]")
            lab += f"[a{i}]"
        labels.append(lab)
    graph = ";\n".join(parts) + ";\n" + "".join(labels) + f"concat=n={len(labels)}:v=1:a={1 if has_audio else 0}[v]" + ("[a]" if has_audio else "")
    cmd = ["ffmpeg", "-v", "error", "-stats", "-y", "-i", str(src), "-filter_complex", graph, "-map", "[v]"]
    if has_audio:
        cmd += ["-map", "[a]", "-c:a", "aac", "-b:a", "320k", "-ar", "48000"]
    cmd += ["-r", str(fps), "-c:v", "libx264", "-preset", "medium", "-crf", "14", "-g", str(fps), "-keyint_min", str(fps),
            "-sc_threshold", "0", "-pix_fmt", "yuv420p", "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
            "-movflags", "+faststart", str(out)]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError("ffmpeg falhou ao montar o vídeo cortado:\n" + res.stderr[-1200:])
    return out


def count_cuts(edl: dict) -> int:
    """Cortes reais pelos segmentos (vale também depois de edições no Studio)."""
    segs = edl["segmentos"]
    if not segs:
        return 0
    n = int(segs[0]["in"] > 0) + int(segs[-1]["out"] < edl.get("quadros_fonte", segs[-1]["out"]))
    n += sum(1 for a, b in zip(segs, segs[1:]) if int(b["in"]) != int(a["out"]))
    return n


def describe(edl: dict) -> str:
    fps = edl["fps"]
    src = edl.get("quadros_fonte", 0) / fps
    out = total_frames(edl) / fps
    return (f"{len(edl['segmentos'])} segmentos · {count_cuts(edl)} cortes · "
            f"{src:.2f}s → {out:.2f}s ({(src - out):.2f}s removidos)")


if __name__ == "__main__":
    print(__doc__)
    sys.exit(0)

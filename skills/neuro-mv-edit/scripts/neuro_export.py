#!/usr/bin/env python3
"""
neuro_export.py — decisões de exportação da neuro-mv-edit (resolução, codec, fps, qualidade).

O usuário decide ANTES de começar a edição; a escolha fica em `neuro.json` → "export" e vale para o
mezanino (assets/base.mp4), o render e o master.

Princípio: nenhuma etapa joga fora qualidade que a fonte tem.
  - A composição continua nas coordenadas do layout da plataforma (1080 no lado curto): zonas seguras,
    legendas e tipografia não mudam. A resolução final sai por supersampling (Remotion `--scale`,
    HyperFrames `--resolution`): texto e gráficos são vetor e saem nítidos em 4K.
  - O mezanino guarda a resolução útil da fonte (até a resolução de saída), no fps escolhido; só é
    recodificado quando precisa (corte de proporção, fps, grade, codec que o navegador não decodifica,
    keyframes esparsos) e, nesse caso, em H.264 CRF 10 (visualmente sem perda).
  - O render de entrega captura PNG por quadro (sem perda) e codifica uma vez só, no codec escolhido.
  - O master só mexe no áudio (loudness); o vídeo é copiado sem recompressão.

Uso:
  python3 neuro_export.py analisar <video> [--plataforma instagram_reels] [--quadro saida.png] [--json]
  python3 neuro_export.py opcoes [--json]
"""
from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent

RESOLUCOES = {  # lado curto do quadro
    "720p": 720,
    "1080p": 1080,
    "1440p": 1440,
    "4k": 2160,
    "original": None,  # a resolução útil da fonte
}
ALIASES_RES = {
    "2160p": "4k", "2160": "4k", "uhd": "4k", "4K": "4k",
    "1440": "1440p", "2k": "1440p", "qhd": "1440p",
    "1080": "1080p", "fhd": "1080p", "full-hd": "1080p", "fullhd": "1080p",
    "720": "720p", "hd": "720p",
    "fonte": "original", "nativa": "original",
}
CODECS = {
    "h264": {"nome": "H.264", "ext": ".mp4", "uso": "aceito em todas as redes e players; o padrão"},
    "hevc": {"nome": "HEVC (H.265)", "ext": ".mp4", "uso": "mesma qualidade com ~40% menos peso; YouTube, iPhone e Mac"},
    "prores": {"nome": "ProRes 422 HQ", "ext": ".mov", "uso": "master de edição para arquivo ou outro editor (arquivos grandes)"},
}
ALIASES_CODEC = {"h265": "hevc", "x265": "hevc", "x264": "h264", "avc": "h264", "prores422": "prores", "prores_hq": "prores"}
QUALIDADES = {
    "maxima": {"nome": "Máxima", "h264": 12, "hevc": 14, "uso": "visualmente idêntica ao PNG de cada quadro"},
    "alta": {"nome": "Alta", "h264": None, "hevc": 18, "uso": "o CRF de master do perfil (17 se o perfil não define)"},
}
ALIASES_QUAL = {"máxima": "maxima", "max": "maxima", "lossless": "maxima", "padrao": "alta", "padrão": "alta", "high": "alta"}
FPS_VALIDOS = [24, 25, 30, 50, 60]
PADRAO = {"resolucoes": ["1080p"], "codec": "h264", "fps": "original", "qualidade": "alta"}

MEZANINO_CRF = 10  # recodificação do mezanino: visualmente sem perda


# ───────────────────────────── normalização ─────────────────────────────

def norm_res(v: str) -> str:
    k = str(v).strip().lower()
    k = ALIASES_RES.get(k, ALIASES_RES.get(str(v).strip(), k))
    if k not in RESOLUCOES:
        raise ValueError(f"resolução '{v}' inválida (use: {', '.join(RESOLUCOES)})")
    return k


def norm_codec(v: str) -> str:
    k = ALIASES_CODEC.get(str(v).strip().lower(), str(v).strip().lower())
    if k not in CODECS:
        raise ValueError(f"codec '{v}' inválido (use: {', '.join(CODECS)})")
    return k


def norm_qual(v: str) -> str:
    k = ALIASES_QUAL.get(str(v).strip().lower(), str(v).strip().lower())
    if k not in QUALIDADES:
        raise ValueError(f"qualidade '{v}' inválida (use: {', '.join(QUALIDADES)})")
    return k


def norm_fps(v) -> str | int:
    if v in (None, "", "original", "fonte"):
        return "original"
    f = int(round(float(v)))
    if f not in FPS_VALIDOS:
        raise ValueError(f"fps '{v}' inválido (use: original, {', '.join(map(str, FPS_VALIDOS))})")
    return f


def parse_lista(v) -> list[str]:
    if isinstance(v, (list, tuple)):
        itens = list(v)
    else:
        itens = [x for x in str(v or "").replace(";", ",").split(",")]
    out = []
    for x in itens:
        x = str(x).strip()
        if x:
            r = norm_res(x)
            if r not in out:
                out.append(r)
    return out


def normalizar(exp: dict | None) -> dict:
    """Completa e valida o bloco "export" de um neuro.json (aceita o formato antigo sem o bloco)."""
    e = dict(PADRAO)
    e.update({k: v for k, v in (exp or {}).items() if v not in (None, "")})
    if "resolucao" in e and "resolucoes" not in (exp or {}):
        e["resolucoes"] = e.pop("resolucao")
    e.pop("resolucao", None)
    e["resolucoes"] = parse_lista(e["resolucoes"]) or list(PADRAO["resolucoes"])
    e["codec"] = norm_codec(e["codec"])
    e["fps"] = norm_fps(e["fps"])
    e["qualidade"] = norm_qual(e["qualidade"])
    return e


# ───────────────────────────── fonte ─────────────────────────────

def _ffprobe(path: Path) -> dict:
    r = subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"ffprobe não leu {path}: {r.stderr.strip()[:300]}")
    return json.loads(r.stdout)


def _rate(s: str | None) -> float | None:
    if not s or s in ("0/0", "0"):
        return None
    try:
        return float(Fraction(s))
    except (ValueError, ZeroDivisionError):
        return None


def analisar_fonte(path: Path) -> dict:
    """Tudo o que a exportação precisa saber da fonte, já com a rotação aplicada."""
    d = _ffprobe(path)
    v = next((s for s in d["streams"] if s.get("codec_type") == "video"), None)
    a = next((s for s in d["streams"] if s.get("codec_type") == "audio"), None)
    if not v:
        raise RuntimeError(f"{path} não tem trilha de vídeo")
    rot = 0
    for sd in v.get("side_data_list", []) or []:
        if "rotation" in sd:
            rot = int(sd["rotation"])
    rot = int((v.get("tags") or {}).get("rotate", rot))
    w, h = int(v["width"]), int(v["height"])
    if abs(rot) in (90, 270):
        w, h = h, w
    fps = _rate(v.get("avg_frame_rate")) or _rate(v.get("r_frame_rate")) or 30.0
    pix = v.get("pix_fmt") or ""
    bits = 10 if "10" in pix else 12 if "12" in pix else 8
    trc = v.get("color_transfer") or ""
    br = v.get("bit_rate") or d["format"].get("bit_rate")
    return {
        "arquivo": str(path),
        "largura": w, "altura": h, "rotacao": rot,
        "fps": round(fps, 3), "fps_texto": v.get("avg_frame_rate"),
        "codec": v.get("codec_name"), "perfil": v.get("profile"), "pix_fmt": pix, "bits": bits,
        "hdr": trc in ("smpte2084", "arib-std-b67"), "transferencia": trc or None,
        "primarias": v.get("color_primaries"), "matriz": v.get("color_space"), "faixa": v.get("color_range"),
        "bitrate_mbps": round(int(br) / 1e6, 1) if br else None,
        "duracao": round(float(d["format"].get("duration") or 0), 3),
        "audio": ({"codec": a.get("codec_name"), "taxa": int(a.get("sample_rate") or 0), "canais": a.get("channels"),
                   "bitrate_kbps": round(int(a["bit_rate"]) / 1000) if a.get("bit_rate") else None} if a else None),
    }


def fps_da_fonte(fps: float) -> int:
    """23,976→24 · 29,97→30 · 59,94→60 (o pipeline trabalha com fps inteiro; a diferença é 1 quadro a cada ~33 s)."""
    alvo = min(FPS_VALIDOS, key=lambda x: abs(x - fps))
    return alvo if abs(alvo - fps) <= 1.0 else max(24, min(60, int(round(fps))))


def area_util(fonte: dict, W: int, H: int) -> tuple[int, int]:
    """Quanto da fonte cabe no quadro W×H depois do corte de proporção (cover): o recorte em pixels da fonte."""
    sw, sh = fonte["largura"], fonte["altura"]
    alvo = W / H
    if sw / sh > alvo:
        return int(round(sh * alvo)), sh
    return sw, int(round(sw / alvo))


def _par(x: float) -> int:
    return max(2, int(round(x / 2.0)) * 2)


# ───────────────────────────── plano de exportação ─────────────────────────────

def plano(exp: dict, W: int, H: int, fonte: dict | None = None, crf_perfil: int | None = None) -> dict:
    """Para cada resolução pedida: tamanho final, escala do render, CRF e avisos (upscale, HDR...)."""
    e = normalizar(exp)
    base = min(W, H)
    util = area_util(fonte, W, H) if fonte else None
    util_curto = min(util) if util else None
    saidas, avisos = [], []
    for r in e["resolucoes"]:
        curto = RESOLUCOES[r] or (util_curto or base)
        curto = max(360, min(4320, curto))
        escala = curto / base
        ow, oh = _par(W * escala), _par(H * escala)
        upscale = bool(util_curto and curto > util_curto * 1.02)
        if upscale:
            avisos.append(f"{r}: a fonte rende {util[0]}x{util[1]} úteis nesta proporção; {ow}x{oh} amplia a imagem do vídeo "
                          f"(texto e gráficos saem nítidos, o vídeo não ganha detalhe)")
        saidas.append({"resolucao": r, "largura": ow, "altura": oh, "escala": round(escala, 6), "upscale": upscale})
    codec = e["codec"]
    if codec == "prores":
        crf = None
    elif codec == "hevc":
        crf = QUALIDADES[e["qualidade"]]["hevc"]
    else:
        crf = QUALIDADES[e["qualidade"]]["h264"] or int(crf_perfil or 17)
    fps = e["fps"] if e["fps"] != "original" else (fps_da_fonte(fonte["fps"]) if fonte else 30)
    if fonte and fonte.get("hdr"):
        avisos.append("fonte HDR (" + str(fonte.get("transferencia")) + "): o mezanino converte para SDR Rec.709 com tonemapping; "
                      "redes sociais exibem SDR")
    if fonte and isinstance(e["fps"], int) and e["fps"] > fonte["fps"] + 1:
        avisos.append(f"{e['fps']} fps acima dos {fonte['fps']} da fonte: quadros repetidos, sem ganho de fluidez")
    maior = max(saidas, key=lambda s: s["largura"] * s["altura"])
    # mezanino: a área útil da fonte (sem ampliar), reduzida só até a maior saída
    if util:
        k = min(1.0, maior["largura"] / util[0])
        mz = (_par(util[0] * k), _par(util[1] * k))
    else:
        mz = (maior["largura"], maior["altura"])
    return {
        "export": e, "codec": codec, "codec_nome": CODECS[codec]["nome"], "ext": CODECS[codec]["ext"], "crf": crf, "fps": fps,
        "composicao": {"largura": W, "altura": H}, "saidas": saidas, "mezanino": {"largura": mz[0], "altura": mz[1]},
        "avisos": avisos,
    }


def sufixo(res: str, principal: bool) -> str:
    return "" if principal else f"_{res}"


def recomendacao(fonte: dict, W: int, H: int) -> dict:
    """Sugestão para o agente oferecer primeiro: a maior resolução sem upscale, H.264, fps da fonte."""
    util = area_util(fonte, W, H)
    curto = min(util)
    res = "4k" if curto >= 2160 * 0.98 else "1440p" if curto >= 1440 * 0.98 else "1080p" if curto >= 1080 * 0.9 else "720p"
    resolucoes = [res] if res in ("1080p", "720p") else [res, "1080p"]
    return {"resolucoes": resolucoes, "codec": "h264", "fps": "original", "qualidade": "alta",
            "motivo": f"a fonte rende {util[0]}x{util[1]} úteis em {W}x{H}; {res} é o máximo sem ampliar"
                      + ("; a cópia em 1080p é a que as redes exibem" if len(resolucoes) > 1 else "")}


# ───────────────────────────── argumentos de render ─────────────────────────────

def args_remotion(p: dict, saida: dict, qualidade_render: str = "delivery") -> list[str]:
    """Flags do `remotion render` para uma saída do plano (o render de rascunho não passa por aqui)."""
    a = []
    if abs(saida["escala"] - 1) > 1e-6:
        a.append(f"--scale={saida['escala']}")
    if p["codec"] == "prores":
        a += ["--codec=prores", "--prores-profile=hq", "--pixel-format=yuv422p10le", "--audio-codec=pcm-16"]
    elif p["codec"] == "hevc":
        a += ["--codec=h265", f"--crf={p['crf']}", "--pixel-format=yuv420p", "--audio-codec=aac", "--audio-bitrate=320k"]
    else:
        a += ["--codec=h264", f"--crf={p['crf']}", "--pixel-format=yuv420p", "--x264-preset=slow",
              "--audio-codec=aac", "--audio-bitrate=320k"]
    a += ["--color-space=bt709"]
    a += ["--image-format=png"] if qualidade_render == "delivery" else ["--image-format=jpeg", "--jpeg-quality=95"]
    return a


def hf_resolucao(W: int, H: int, saida: dict) -> str | None:
    """Preset do `hyperframes render --resolution` (escala inteira 1x/2x da composição), ou None para 1x."""
    k = saida["largura"] / W
    if abs(k - 1) < 1e-6:
        return None
    if abs(k - 2) < 1e-6:
        return "portrait-4k" if H > W else "landscape-4k" if W > H else "square-4k"
    return None


def ffmpeg_final(p: dict, saida: dict, origem: Path, destino: Path, escalar: bool) -> list[str]:
    """Codificação única a partir de um intermediário ProRes (motor HyperFrames): escala lanczos se precisar + codec final."""
    vf = [f"scale={saida['largura']}:{saida['altura']}:flags=lanczos+accurate_rnd+full_chroma_int"] if escalar else []
    cmd = ["ffmpeg", "-v", "error", "-stats", "-y", "-i", str(origem)]
    if p["codec"] == "prores":
        vf.append("format=yuv422p10le")
        cmd += ["-vf", ",".join(vf), "-c:v", "prores_ks", "-profile:v", "3", "-vendor", "apl0", "-c:a", "pcm_s16le"]
    elif p["codec"] == "hevc":
        vf.append("format=yuv420p")
        cmd += ["-vf", ",".join(vf), "-c:v", "libx265", "-preset", "slow", "-crf", str(p["crf"]), "-tag:v", "hvc1",
                "-x265-params", "log-level=error", "-c:a", "aac", "-b:a", "320k", "-movflags", "+faststart"]
    else:
        vf.append("format=yuv420p")
        cmd += ["-vf", ",".join(vf), "-c:v", "libx264", "-preset", "slow", "-crf", str(p["crf"]),
                "-c:a", "aac", "-b:a", "320k", "-movflags", "+faststart"]
    cmd += ["-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", str(destino)]
    return cmd


def corrige_tag_hevc(path: Path) -> bool:
    """HEVC marcado como `hev1` não toca no iPhone/QuickTime: troca para `hvc1` sem recodificar (remux)."""
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=codec_name,codec_tag_string",
                        "-of", "csv=p=0", str(path)], capture_output=True, text=True)
    if not r.stdout.strip().startswith("hevc") or "hvc1" in r.stdout:
        return False
    tmp = path.with_name(path.stem + ".hvc1" + path.suffix)
    ok = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(path), "-map", "0", "-c", "copy", "-tag:v", "hvc1",
                         "-movflags", "+faststart", str(tmp)]).returncode == 0
    if ok:
        os.replace(tmp, path)
    else:
        tmp.unlink(missing_ok=True)
    return ok


def filtro_hdr_para_sdr() -> str | None:
    """Tonemapping PQ/HLG → SDR Rec.709 (precisa do zscale no ffmpeg)."""
    r = subprocess.run(["ffmpeg", "-hide_banner", "-filters"], capture_output=True, text=True)
    if " zscale " not in r.stdout or " tonemap " not in r.stdout:
        return None
    return ("zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=tonemap=hable:desat=0,"
            "zscale=t=bt709:m=bt709:r=tv")


def plano_projeto(cfg: dict, profile: dict | None = None, resolucao=None, codec=None, qualidade=None) -> dict:
    """Plano de exportação de um projeto existente (o fps é o do projeto; as flags do render sobrescrevem a decisão)."""
    exp = dict(cfg.get("export") or {})
    if resolucao:
        exp["resolucoes"] = resolucao
    if codec:
        exp["codec"] = codec
    if qualidade:
        exp["qualidade"] = qualidade
    exp["fps"] = int(cfg["fps"]) if int(cfg["fps"]) in FPS_VALIDOS else "original"
    fonte = cfg.get("fonte")
    if not fonte and cfg.get("source_video") and Path(cfg["source_video"]).is_file():
        try:
            fonte = analisar_fonte(Path(cfg["source_video"]))  # projetos de antes da v1.9
        except RuntimeError:
            fonte = None
    fonte = dict(fonte, hdr=False) if fonte else None
    crf_perfil = (((profile or {}).get("strict_rules") or {}).get("dual_export_crf") or {}).get("master_crf")
    p = plano(exp, int(cfg["width"]), int(cfg["height"]), fonte, crf_perfil)
    p["fps"] = int(cfg["fps"])
    return p


def nome_saida(base: Path, saida: dict, principal: bool, ext: str) -> Path:
    """renders/<proj>_<data>.mp4 para a saída principal; renders/<proj>_<data>_1080p.mp4 para as demais."""
    return base.with_name(base.stem + sufixo(saida["resolucao"], principal) + ext)


def add_args(parser, render: bool = False) -> None:
    """Flags de exportação nos subcomandos `init`, `render` e `exportacao`."""
    parser.add_argument("--resolucao", "--resolução", dest="resolucao",
                        help="resolução final, uma ou várias separadas por vírgula: 4k, 1440p, 1080p, 720p, original "
                             "(padrão: a decidida no init; no init, 1080p)")
    parser.add_argument("--codec", help="h264 (compatível) | hevc (H.265, ~40%% menor) | prores (master 422 HQ, .mov)")
    if not render:
        parser.add_argument("--fps", help="original (o da fonte) | 24 | 25 | 30 | 50 | 60")
    parser.add_argument("--qualidade", help="alta (CRF do perfil) | maxima (CRF 12 H.264 / 14 HEVC)")


# ───────────────────────────── espaço em disco ─────────────────────────────

def estimar_gb(p: dict, duracao: float) -> float:
    """Estimativa do pico de disco (mezanino + render + master de cada saída), em GB."""
    ref = 1080 * 1920 * 30
    mbps_ref = {"h264": 12.0 * (1.6 if p["export"]["qualidade"] == "maxima" else 1), "hevc": 9.0, "prores": 220.0}[p["codec"]]
    total_mbit = 0.0
    for s in p["saidas"]:
        total_mbit += 2 * mbps_ref * (s["largura"] * s["altura"] * p["fps"] / ref) * duracao
    total_mbit += 40.0 * (p["mezanino"]["largura"] * p["mezanino"]["altura"] * p["fps"] / ref) * duracao
    return round(total_mbit / 8 / 1024, 1)


# ───────────────────────────── CLI ─────────────────────────────

def _layout(plataforma: str | None) -> tuple[int, int, str]:
    plats = json.loads((SKILL_ROOT / "presets" / "platforms.json").read_text(encoding="utf-8"))["platforms"]
    pid = plataforma or "instagram_reels"
    if pid not in plats:
        raise SystemExit(f"plataforma '{pid}' não existe em presets/platforms.json")
    return int(plats[pid]["width"]), int(plats[pid]["height"]), pid


def quadro_layout(video: Path, destino: Path, W: int, H: int, em: float = 2.0) -> None:
    """Um quadro da fonte já no enquadramento e nas coordenadas da composição (para medir o --head-y)."""
    vf = f"scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,crop={W}:{H}"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(em), "-i", str(video), "-frames:v", "1", "-vf", vf, str(destino)], check=True)


def main():
    ap = argparse.ArgumentParser(description="Decisões de exportação da neuro-mv-edit")
    sp = ap.add_subparsers(dest="cmd", required=True)
    a = sp.add_parser("analisar", help="lê a fonte e recomenda resolução, codec e fps")
    a.add_argument("video")
    a.add_argument("--plataforma")
    a.add_argument("--quadro", help="grava um quadro no enquadramento da composição (para medir o topo da cabeça)")
    a.add_argument("--json", action="store_true")
    o = sp.add_parser("opcoes", help="lista as opções de exportação")
    o.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.cmd == "opcoes":
        data = {"resolucoes": {k: (v or "fonte") for k, v in RESOLUCOES.items()}, "codecs": CODECS, "qualidades": QUALIDADES,
                "fps": ["original"] + FPS_VALIDOS, "padrao": PADRAO}
        if args.json:
            print(json.dumps(data, ensure_ascii=False, indent=2))
            return
        print("Resoluções (lado curto): " + ", ".join(f"{k}" + (f" ({v}px)" if v else " (a da fonte)") for k, v in RESOLUCOES.items()))
        print("Codecs: " + "; ".join(f"{k} = {c['nome']}: {c['uso']}" for k, c in CODECS.items()))
        print("Qualidade: " + "; ".join(f"{k} = {q['uso']}" for k, q in QUALIDADES.items()))
        print("FPS: original (o da fonte), " + ", ".join(map(str, FPS_VALIDOS)))
        return

    video = Path(args.video).expanduser().resolve()
    if not video.is_file():
        raise SystemExit(f"vídeo não encontrado: {video}")
    W, H, pid = _layout(args.plataforma)
    fonte = analisar_fonte(video)
    rec = recomendacao(fonte, W, H)
    pl = plano(rec, W, H, fonte)
    out = {"fonte": fonte, "plataforma": pid, "composicao": {"largura": W, "altura": H},
           "area_util": dict(zip(("largura", "altura"), area_util(fonte, W, H))),
           "recomendado": rec, "plano_recomendado": pl, "disco_estimado_gb": estimar_gb(pl, fonte["duracao"])}
    if args.quadro:
        quadro_layout(video, Path(args.quadro).expanduser(), W, H, em=min(2.0, max(0.0, fonte["duracao"] / 3)))
        out["quadro"] = str(Path(args.quadro).expanduser().resolve())
    if args.json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return
    f = fonte
    print(f"Fonte: {f['largura']}x{f['altura']} · {f['fps']} fps · {f['codec']} {f['bits']}-bit"
          + (f" · HDR {f['transferencia']}" if f["hdr"] else " · SDR")
          + (f" · {f['bitrate_mbps']} Mb/s" if f["bitrate_mbps"] else "")
          + (f" · áudio {f['audio']['codec']} {f['audio']['taxa']} Hz" if f["audio"] else " · sem áudio"))
    u = out["area_util"]
    print(f"Composição {pid}: {W}x{H} · área útil da fonte nesse enquadramento: {u['largura']}x{u['altura']}")
    print(f"Recomendado: {', '.join(rec['resolucoes'])} · {rec['codec']} · fps {rec['fps']} ({rec['motivo']})")
    for av in pl["avisos"]:
        print(f"  ⚠ {av}")
    print(f"Disco estimado: ~{out['disco_estimado_gb']} GB")
    if out.get("quadro"):
        print(f"Quadro para medir o topo da cabeça (coordenadas da composição): {out['quadro']}")


if __name__ == "__main__":
    main()

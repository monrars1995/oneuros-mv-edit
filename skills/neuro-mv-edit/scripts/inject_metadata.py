#!/usr/bin/env python3
"""
inject_metadata.py — metadados no MP4 e copy de postagem.

Grava title, artist, album_artist (@), comment/description, copyright, genre e date no container (cópia do
vídeo, sem recompressão; escrita atômica) e gera `<vídeo>_COPY_POSTAGEM.md` com legenda, hashtags e primeiro
comentário. Se existir a cópia leve do master (`<stem>_leve.mp4`), ela recebe os mesmos metadados.

Ordem de prioridade dos campos: perfil (skill ou biblioteca do usuário) < --json < opções (-t, -d).

  python3 scripts/inject_metadata.py -i renders/master/X_MASTER.mp4 -p exemplo_juridico -t "O prazo que ninguém lê"
  python3 scripts/inject_metadata.py -i X_MASTER.mp4 -p dra_ana --json meta.json -o X_MASTER.mp4   # substitui no lugar
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent)) if str(Path(__file__).resolve().parent) not in sys.path else None

import hf_project as hf  # noqa: E402

NOTA_OAB = ("⚠️ *Nota de Conformidade Ética: Conteúdo estritamente informativo, em conformidade com o Provimento 205/2021 do "
            "Conselho Federal da OAB. Não constitui garantia de resultado ou consultoria individualizada.*")
NOTA_SAUDE = "⚠️ *Conteúdo informativo. Não substitui consulta, diagnóstico ou tratamento por profissional de saúde.*"

# A legenda-modelo e o primeiro comentário de cada perfil vêm de `default_metadata.caption_template`
# (com `{nota}` para a nota de conformidade) e `default_metadata.first_comment`. Sem eles, a legenda é montada
# com título, descrição, nota e CTA do perfil.


def die(msg: str, code: int = 1):
    print(f"✗ {msg}", file=sys.stderr)
    sys.exit(code)


def nota_conformidade(profile: dict) -> str:
    cf = profile.get("compliance_framework", "")
    seg = profile.get("segment", "")
    if "oab" in cf or seg.startswith("juridico") or seg == "institucional_juridico":
        return NOTA_OAB
    if "saude" in cf or seg == "saude":
        return NOTA_SAUDE
    return ""


def legenda(profile: dict, meta: dict) -> str:
    if meta.get("caption_body"):
        return meta["caption_body"]
    modelo = (profile.get("default_metadata") or {}).get("caption_template")
    nota = nota_conformidade(profile)
    if modelo:
        return modelo.format(nota=nota).replace("\n\n\n", "\n\n")
    cta = (profile.get("editorial_guidelines") or {}).get("cta_default") or "Salve este vídeo e compartilhe com quem precisa."
    partes = [meta.get("title", ""), meta.get("description", ""), nota, cta]
    return "\n\n".join(p for p in partes if p)


def primeiro_comentario(profile: dict) -> str:
    seg = profile.get("segment", "")
    proprio = (profile.get("default_metadata") or {}).get("first_comment")
    if proprio:
        return proprio
    if seg.startswith("juridico") or seg == "institucional_juridico":
        return "Dúvidas sobre o tema? Deixe sua pergunta aqui nos comentários ou entre em contato pelo link da bio."
    return "Dúvidas sobre o conteúdo? Deixe sua pergunta aqui nos comentários ou envie um direct."


def montar_meta(profile: dict, args, video_name: str) -> dict:
    dm = profile.get("default_metadata") or {}
    industry = profile.get("industry_name") or profile.get("segment") or "Geral"
    meta = {
        "title": f"{profile.get('name', 'Especialista')} — {industry}",
        "artist": dm.get("artist") or profile.get("name", ""),
        "handle": profile.get("handle", ""),
        "description": f"Orientações de {profile.get('name', '')} sobre {industry}.",
        "copyright": dm.get("copyright") or profile.get("name", ""),
        "genre": dm.get("genre") or industry,
        "keywords": dm.get("keywords") or [industry],
        "industry_name": industry,
        "platform": profile.get("platform_default", "instagram_reels"),
    }
    if args.json:
        jp = Path(args.json).expanduser()
        if not jp.exists():
            die(f"--json {jp} não existe.")
        try:
            extra = json.loads(jp.read_text(encoding="utf-8"))
        except ValueError as e:
            die(f"--json {jp} não é um JSON válido: {e}")
        meta.update({k: v for k, v in extra.items() if v not in (None, "")})
    if args.title:
        meta["title"] = args.title
    if args.description:
        meta["description"] = args.description
    kw = meta.get("keywords")
    if isinstance(kw, str):
        meta["keywords"] = [k.strip() for k in kw.replace(";", ",").split(",") if k.strip()]
    meta["video_filename"] = video_name
    return meta


def injetar(src: Path, dst: Path, meta: dict) -> bool:
    """Cópia com metadados num arquivo temporário e troca atômica (funciona também com -o igual à entrada)."""
    tmp = dst.with_name(f".{dst.stem}.meta-tmp{dst.suffix}")
    hevc = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=codec_name", "-of", "csv=p=0",
                           str(src)], capture_output=True, text=True).stdout.strip() == "hevc"
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", str(src), "-map", "0", "-c", "copy", *(["-tag:v", "hvc1"] if hevc else []),
           "-metadata", f"title={meta.get('title', '')}",
           "-metadata", f"artist={meta.get('artist', '')}",
           "-metadata", f"album_artist={meta.get('handle', '')}",
           "-metadata", f"comment={meta.get('description', '')}",
           "-metadata", f"description={meta.get('description', '')}",
           "-metadata", f"copyright={meta.get('copyright', '')}",
           "-metadata", f"genre={meta.get('genre', '')}",
           "-metadata", f"date={datetime.now().strftime('%Y-%m-%d')}",
           "-movflags", "+faststart", str(tmp)]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0 or not tmp.exists() or tmp.stat().st_size < 1000:
        tmp.unlink(missing_ok=True)
        print(f"  ❌ ffmpeg falhou em {src.name}: {(res.stderr or '').strip()[-600:]}", file=sys.stderr)
        return False
    os.replace(tmp, dst)
    print(f"  ✅ metadados em {dst}")
    return True


def gerar_copy(meta: dict, profile: dict, out_dir: Path, stem: str) -> Path:
    tags = " ".join(f"#{str(t).replace(' ', '')}" for t in meta.get("keywords", []) if str(t).strip())
    plat = hf.load_presets()[2].get(meta.get("platform", ""), {}).get("name", meta.get("platform", ""))
    content = f"""# 📱 Planejamento de Postagem & Distribuição

**Arquivo do vídeo:** `{meta['video_filename']}`
**Especialista:** {meta.get('artist', '')} ({meta.get('handle', '')})
**Segmento:** {meta.get('industry_name', '')}
**Data da entrega:** {datetime.now().strftime('%d/%m/%Y')}
**Formato principal:** {plat}

---

## 🎯 Título / Hook da Publicação
> **{meta.get('title', '')}**

---

## 📝 Legenda Completa (copiar e colar)

{legenda(profile, meta)}

---

## 🏷️ Hashtags
```text
{tags or '#NeuroMVEdit'}
```

---

## 💬 Sugestão de Primeiro Comentário (fixar no topo)
```text
{meta.get('first_comment') or primeiro_comentario(profile)}
```

---

## ⚙️ Metadados Embarcados no MP4
- **Título:** {meta.get('title', '')}
- **Autor:** {meta.get('artist', '')}
- **Perfil:** {meta.get('handle', '')}
- **Copyright:** {meta.get('copyright', '')}
- **Gênero:** {meta.get('genre', '')}
- **Data:** {datetime.now().strftime('%Y-%m-%d')}
"""
    path = out_dir / f"{stem}_COPY_POSTAGEM.md"
    path.write_text(content, encoding="utf-8")
    print(f"  📄 copy: {path}")
    return path


def main():
    ap = argparse.ArgumentParser(description="Metadados no MP4 + copy de postagem")
    ap.add_argument("--input", "-i", required=True, help="vídeo de entrada (normalmente o _MASTER.mp4)")
    ap.add_argument("--output", "-o", help="vídeo de saída (padrão: <stem>_meta.mp4; igual à entrada = substitui no lugar)")
    ap.add_argument("--profile", "-p", required=True, help="id do perfil (skill ou biblioteca do usuário)")
    ap.add_argument("--title", "-t", help="título / hook do vídeo")
    ap.add_argument("--description", "-d", help="descrição breve")
    ap.add_argument("--json", "-j", help="JSON com campos extras (title, description, keywords, caption_body, first_comment...)")
    ap.add_argument("--sem-leve", action="store_true", help="não procurar a cópia leve (<stem>_leve.mp4)")
    a = ap.parse_args()

    if not shutil.which("ffmpeg"):
        die("ffmpeg não encontrado no PATH (rode `neuro-mv-edit verify`).")
    src = Path(a.input).expanduser().resolve()
    if not src.exists():
        die(f"arquivo {src} não encontrado.")
    profiles = hf.load_presets()[0]
    if a.profile not in profiles:
        die(f"perfil '{a.profile}' não existe. Opções: {', '.join(sorted(p for p in profiles if p != 'template_novo_perfil'))}")
    profile = dict(profiles[a.profile], id=a.profile)
    dst = Path(a.output).expanduser().resolve() if a.output else src.with_name(f"{src.stem}_meta{src.suffix}")

    print(f"\n🎬 Metadados: {src.name} → {dst.name}")
    meta = montar_meta(profile, a, dst.name)
    if not injetar(src, dst, meta):
        die("metadados não foram gravados; a copy não foi gerada.")
    leve = src.with_name(f"{src.stem}_leve{src.suffix}")
    if not a.sem_leve and leve.exists():
        injetar(leve, leve if dst == src else dst.parent / f"{leve.stem}_meta{leve.suffix}", meta)
    # as outras resoluções do mesmo master (<stem>_1080p.mp4, <stem>_4k.mov...) recebem os mesmos metadados
    for res in ("720p", "1080p", "1440p", "4k", "original"):
        for outra in src.parent.glob(f"{src.stem}_{res}.*"):
            if outra.suffix.lower() in (".mp4", ".mov") and outra != src:
                injetar(outra, outra if dst == src else dst.parent / f"{outra.stem}_meta{outra.suffix}", meta)
    gerar_copy(meta, profile, dst.parent, dst.stem)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
organize_deliveries.py — arquiva a entrega em `entregas/AAAA-MM/DD/<rede>/`.

Copia (não move) para a pasta do dia e da rede:
- o vídeo final (normalmente o `_MASTER_meta.mp4` saído do inject_metadata);
- automaticamente, os irmãos do mesmo vídeo: cópia leve (`*_leve*.mp4`), relatório de loudness (`*_loudness.json`)
  e a copy (`<vídeo>_COPY_POSTAGEM.md`);
- o que vier por opção: --copy, --report, --preview, --extra.

Sai com erro (código 1) se o vídeo não existir. Rodar de novo sobre a mesma entrega não quebra.

  python3 scripts/organize_deliveries.py -m renders/master/X_MASTER_meta.mp4 -n reels
"""

from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

VALID_NETWORKS = ["reels", "tiktok", "shorts", "youtube", "feed"]


def irmaos(master: Path) -> list[Path]:
    """Arquivos do mesmo vídeo gerados pelo master/inject_metadata, na mesma pasta."""
    base = master.stem.replace("_meta", "")
    raiz = base.replace("_leve", "")
    nome = raiz[:-len("_MASTER")] if raiz.endswith("_MASTER") else raiz  # o master grava <nome>_loudness.json
    out = []
    for p in sorted(master.parent.iterdir()):
        if p == master or not p.is_file():
            continue
        n = p.name
        resolucao = any(n.startswith(f"{raiz}_{r}") for r in ("720p", "1080p", "1440p", "4k", "original"))
        if (n.startswith(raiz) and ("_leve" in n or resolucao) and p.suffix.lower() in (".mp4", ".mov")
                and ("_meta" in n) == ("_meta" in master.name)) \
                or n in (f"{raiz}_loudness.json", f"{nome}_loudness.json", f"{master.stem}_COPY_POSTAGEM.md", f"{base}_COPY_POSTAGEM.md"):
            out.append(p)
    return out


def copiar(src: Path, dst_dir: Path, rotulo: str):
    dst = dst_dir / src.name
    if dst.exists() and dst.resolve() == src.resolve():
        print(f"  ↺ {rotulo}: já está na entrega ({dst.name})")
        return
    shutil.copy2(src, dst)
    print(f"  {rotulo}: {dst}")


def organize_delivery(master_file, base_dir="entregas", network="reels", copy_file=None, report_file=None, preview_file=None, extras=None):
    master = Path(master_file).expanduser()
    if not master.exists():
        print(f"✗ vídeo {master} não encontrado — nada foi arquivado.", file=sys.stderr)
        sys.exit(1)
    master = master.resolve()
    now = datetime.now()
    target = Path(base_dir).expanduser() / now.strftime("%Y-%m") / now.strftime("%d") / network
    target.mkdir(parents=True, exist_ok=True)
    print(f"\n📁 Entrega em {target}")
    copiar(master, target, "🎬 vídeo")
    for p in irmaos(master):
        copiar(p, target, "📎 junto")
    for rotulo, f in (("📄 copy", copy_file), ("📊 relatório", report_file), ("🖼️ prévia", preview_file)):
        if f:
            fp = Path(f).expanduser()
            if fp.exists():
                copiar(fp.resolve(), target, rotulo)
            else:
                print(f"  ⚠️ {rotulo}: {fp} não encontrado", file=sys.stderr)
    for f in extras or []:
        fp = Path(f).expanduser()
        if fp.exists():
            copiar(fp.resolve(), target, "📎 extra")
        else:
            print(f"  ⚠️ extra: {fp} não encontrado", file=sys.stderr)
    print(f"✅ Entrega arquivada em {target.resolve()}")
    return target


def main():
    ap = argparse.ArgumentParser(description="Arquiva a entrega em entregas/AAAA-MM/DD/<rede>/")
    ap.add_argument("--master", "-m", required=True, help="vídeo final (ex.: X_MASTER_meta.mp4)")
    ap.add_argument("--network", "-n", default="reels", choices=VALID_NETWORKS, help="rede de destino")
    ap.add_argument("--base-dir", "-b", default="entregas", help="pasta base das entregas")
    ap.add_argument("--copy", "-c", help="copy de postagem (padrão: o <vídeo>_COPY_POSTAGEM.md ao lado do vídeo)")
    ap.add_argument("--report", "-r", help="relatório de entrega (.md)")
    ap.add_argument("--preview", "-p", help="imagem de prévia")
    ap.add_argument("--extra", "-e", nargs="*", help="outros arquivos para a mesma pasta")
    a = ap.parse_args()
    organize_delivery(a.master, a.base_dir, a.network, a.copy, a.report, a.preview, a.extra)


if __name__ == "__main__":
    main()

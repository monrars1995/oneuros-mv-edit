#!/usr/bin/env python3
"""
neuro_project.py — porta única dos projetos da neuro-mv-edit, com escolha de motor.

  init         cria o projeto (--engine remotion | hyperframes; padrão: NEURO_ENGINE, perfil ou remotion)
  transcrever  transcrição por palavra do mezanino (whisper via `hyperframes transcribe`)
  legendas     corrige o transcript (glossário, --fix, --learn) e gera as legendas do perfil
  cortar       decupagem: sugere os cortes (silêncios, respiros, claquetes) e grava edl.json
  build        gera o projeto do motor a partir de edl.json + cues.json
  estudio      abre a interface web (Remotion Studio ou HyperFrames preview) e acompanha as edições
  sincronizar  (Remotion) Studio → edl.json/cues.json
  check        validações (bundle/hyperframes check + avisos do build)
  snapshot     quadros de revisão
  render       vídeo final do motor
  master       loudness EBU R128 em 2 passagens + cópia leve
  salvar       checkpoint git do projeto ;  historico ;  voltar <ref>
  status       motor, duração, cortes, Studio e último checkpoint

Toda ação que muda o projeto termina com um checkpoint git local (mídia e renders ficam fora do git).
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent)) if str(Path(__file__).resolve().parent) not in sys.path else None

import hf_project as hf  # noqa: E402
import neuro_edl as edlmod  # noqa: E402

ENGINES = ("remotion", "hyperframes")
GITIGNORE = """# neuro-mv-edit: só o que é texto entra no histórico; mídia e renders ficam fora
*.mp4
*.mov
*.m4a
*.wav
*.mp3
*.aac
*.flac
*.ogg
*.ttf
*.otf
*.png
*.jpg
renders/
cartoes-hf/
.neuro/
node_modules/
remotion/public/
remotion/node_modules
assets/music/ducked/
.hyperframes/
"""


def proj_of(a) -> Path:
    p = Path(a.project).expanduser().resolve()
    if not (p / "neuro.json").exists():
        hf.die(f"{p} não é um projeto neuro-mv-edit (sem neuro.json).")
    return p


def engine_of(proj: Path) -> str:
    return hf.load_json(proj / "neuro.json").get("engine", "hyperframes")


def default_engine(profile_id: str | None) -> str:
    env = os.environ.get("NEURO_ENGINE")
    if env in ENGINES:
        return env
    if profile_id:
        profiles, *_ = hf.load_presets()
        e = (profiles.get(profile_id) or {}).get("engine_default")
        if e in ENGINES:
            return e
    return "remotion"


# ───────────────────────────── checkpoints git ─────────────────────────────

def _git(proj: Path, *args, check=False):
    return subprocess.run(["git", "-c", "user.name=neuro-mv-edit", "-c", "user.email=neuro-mv-edit@localhost",
                           "-c", "commit.gpgsign=false", *args], cwd=proj, capture_output=True, text=True, check=check)


def checkpoint(proj: Path, msg: str, quiet: bool = False) -> str | None:
    """Salva o estado de texto do projeto (JSON, TSX, HTML, CSS) num commit local."""
    if not (proj / ".git").exists():
        _git(proj, "init", "-q")
    gi = proj / ".gitignore"
    if not gi.exists():
        gi.write_text(GITIGNORE, encoding="utf-8")
    _git(proj, "add", "-A")
    if _git(proj, "diff", "--cached", "--quiet").returncode == 0:
        return None
    r = _git(proj, "commit", "-q", "-m", msg)
    if r.returncode != 0:
        print(f"  ⚠ checkpoint falhou: {r.stderr.strip()[:200]}", file=sys.stderr)
        return None
    ref = _git(proj, "rev-parse", "--short", "HEAD").stdout.strip()
    if not quiet:
        print(f"  ↳ checkpoint {ref}: {msg}")
    return ref


# ───────────────────────────── comandos ─────────────────────────────

def cmd_init(a):
    engine = a.engine or default_engine(a.profile)
    a.engine = engine
    cfg = hf.cmd_init(a)
    proj = Path(a.out).expanduser().resolve()
    if engine == "remotion":
        import neuro_remotion as nr
        nr.scaffold(proj, cfg)
        nr.build(proj, quiet=True)
        (proj / "NEURO.md").write_text(
            f"# Projeto {proj.name}\n\nGerado pela skill neuro-mv-edit {hf.SKILL_VERSION} · motor **Remotion {nr.REMOTION_VERSION}**.\n\n"
            f"- Perfil `{cfg['profile']}` · tema `{cfg['theme']}` · `{cfg['platform']}` ({cfg['width']}x{cfg['height']} @ {cfg['fps']} fps)\n"
            "- Fonte da verdade: `edl.json` (cortes) e `cues.json` (cenas, câmera, SFX, música, efeitos, B-roll).\n"
            "- `remotion/src/gerado/*.tsx` sai do `build` e é editável no Studio; o `sincronizar` grava cortes e tempos de cena de volta.\n"
            "- Antes de editar os JSON com o Studio aberto, rode `sincronizar` (o vigia do Studio já faz isso sozinho).\n\n"
            "Fluxo: transcrever → legendas → cortar → cues.json → build → estudio → check/snapshot → render → master.\n",
            encoding="utf-8")
        marca = "<!-- neuro-mv-edit:projeto-remotion -->"
        bloco = (f"\n{marca}\n## Projeto neuro-mv-edit (motor Remotion)\n\nLeia `NEURO.md` e a skill `/neuro-mv-edit` "
                 "(references/remotion/BRIDGE.md) antes de mudar algo. Use `neuro-mv-edit projeto <comando> --project .` "
                 "em vez de editar `remotion/src/gerado` à mão; o Studio pode editar esses arquivos.\n")
        for agent_file in ("CLAUDE.md", "AGENTS.md"):
            af = proj / agent_file
            atual = af.read_text(encoding="utf-8") if af.exists() else ""
            if marca not in atual:  # acrescenta; nunca sobrescreve o arquivo de quem já tem um
                af.write_text(atual + bloco, encoding="utf-8")
        print(f"✓ Projeto Remotion pronto em {proj}")
        print(f"  {nr.LICENSE_NOTE}")
        print("  próximo: transcrever → legendas → cortar → cues.json → build → estudio")
    checkpoint(proj, f"init ({engine}, perfil {cfg['profile']})")


def cmd_transcrever(a):
    proj = proj_of(a)
    cfg = hf.load_json(proj / "neuro.json")
    mez = cfg.get("mezanino", cfg["video"])
    print(f"▶ npx hyperframes@{hf.HF_VERSION} transcribe {mez} --model {a.model} --language {a.language}")
    res = subprocess.run(hf.hf_cmd("transcribe", mez, "--model", a.model, "--language", a.language), cwd=proj, env=hf.hf_env())
    if res.returncode != 0:
        sys.exit(res.returncode)
    out = proj / "assets" / "transcript.json"
    if not out.exists():
        cand = sorted(proj.rglob("transcript.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        cand = [c for c in cand if "node_modules" not in c.parts]
        if cand:
            cand[0].replace(out)
    if not out.exists():
        hf.die("A transcrição terminou mas assets/transcript.json não apareceu.")
    print(f"✓ {out}")
    checkpoint(proj, "transcrição")


def cmd_legendas(a):
    proj = proj_of(a)
    a.project = str(proj)
    hf.cmd_captions(a)
    if engine_of(proj) == "remotion":
        import neuro_remotion as nr
        nr.build(proj, quiet=True)
    checkpoint(proj, "legendas" + (f" ({len(a.fix)} correções)" if a.fix else ""))


def _words_src(proj: Path) -> list[dict]:
    for name in ("transcript.fixed.json", "transcript.json"):
        p = proj / "assets" / name
        if p.exists():
            w = hf.load_json(p)
            return w.get("words", []) if isinstance(w, dict) else w
    hf.die("Sem transcrição: rode `transcrever` (os cortes usam as palavras do Whisper).")


def cmd_cortar(a):
    proj = proj_of(a)
    cfg = hf.load_json(proj / "neuro.json")
    engine = cfg.get("engine", "hyperframes")
    if engine == "remotion":
        import neuro_remotion as nr
        st = nr.load_estado(proj)
        if nr.changed_layers(proj, st):
            nr.sincronizar(proj, quiet=True)
    if "mezanino" not in cfg:  # projeto da v1.4.x: o vídeo atual é a fonte inteira
        cfg["mezanino"] = cfg["video"]
        cfg["duracao_fonte"] = cfg["duration"]
        cfg["quadros_fonte"] = int(round(float(cfg["duration"]) * cfg["fps"]))
        hf.save_json(proj / "neuro.json", cfg)
    mez = proj / cfg["mezanino"]
    fps = cfg["fps"]
    q = int(cfg.get("quadros_fonte") or round(float(cfg.get("duracao_fonte", cfg["duration"])) * fps))
    mem = hf.load_memory()
    pacing = ((mem.get("learned_preferences", {}).get(cfg["profile"], {}) or {}).get("pacing") or {})
    if a.sem_claquete:
        pacing = {k: v for k, v in pacing.items() if k != "clapper_cues"}
    corte = ((cfg.get("estilo") or {}).get("corte") or {})
    preset = a.preset or corte.get("preset") or "natural"
    limiar = a.limiar_ms or corte.get("limiar_ms")
    new, notes = edlmod.suggest_edl(_words_src(proj), mez, fps, q, cfg.get("mezanino", "assets/base.mp4"), preset, pacing,
                                    a.remover, a.manter, usar_silencio=not a.sem_silencio, limiar_ms=limiar)
    a.preset = preset
    if a.nenhum:
        new = edlmod.identity_edl(fps, q, cfg.get("mezanino", "assets/base.mp4"))
    print(f"▶ Decupagem ({a.preset}): {edlmod.describe(new)}")
    for r in new.get("removidos", [])[: 60 if a.verbose else 12]:
        print(f"    − {r['de']:7.2f}–{r['ate']:7.2f}s  {r['motivo']}")
    if len(new.get("removidos", [])) > 12 and not a.verbose:
        print(f"    … e mais {len(new['removidos']) - 12} (use --verbose)")
    for n in notes:
        print(f"  ⚠ {n}")
    if a.dry_run:
        print("  (--dry-run: nada gravado)")
        return
    old = edlmod.load_edl(proj) or edlmod.identity_edl(fps, q, cfg.get("mezanino", "assets/base.mp4"))
    cues = hf.load_json(proj / "cues.json")
    if cues.get("scenes") or cues.get("camera"):
        cues, n2 = edlmod.remap_cues(cues, old, new)
        hf.save_json(proj / "cues.json", cues)
        print("  cenas e câmera remapeadas para o novo corte (ancoradas na fala).")
        for n in n2:
            print(f"  ⚠ {n}")
    edlmod.save_edl(proj, new)
    new = edlmod.load_edl(proj)
    cfg["duration"] = hf.r3(edlmod.total_frames(new) / fps)
    if engine == "hyperframes":
        out = proj / "assets" / "base_cortado.mp4"
        print("▶ ffmpeg: montando o vídeo cortado (fades de 10 ms em cada emenda)")
        edlmod.assemble_video(mez, new, out, bool(cfg.get("video_has_audio")))
        cfg["video"] = "assets/base_cortado.mp4"
        cfg["duration"] = hf.r3(hf.media_info(out)["duration"])
        hf.save_json(proj / "neuro.json", cfg)
        fixed = proj / "assets" / "transcript.fixed.json"
        if fixed.exists():
            hf.emit_captions(proj, cfg, hf.load_json(fixed))
        print(f"✓ {out.relative_to(proj)} · {cfg['duration']:.2f}s — rode `build`.")
    else:
        hf.save_json(proj / "neuro.json", cfg)
        import neuro_remotion as nr
        nr.build(proj)
    checkpoint(proj, f"cortar ({a.preset}): {edlmod.describe(new)}")


def cmd_build(a):
    proj = proj_of(a)
    if engine_of(proj) == "remotion":
        import neuro_remotion as nr
        nr.build(proj, force=a.force)
    else:
        a.project = str(proj)
        hf.cmd_build(a)
    checkpoint(proj, "build")


def cmd_estudio(a):
    proj = proj_of(a)
    if engine_of(proj) == "hyperframes":
        if a.parar:
            print("  O preview do HyperFrames roda em primeiro plano: encerre com Ctrl+C no terminal dele.")
            return
        extra = a.extra or ["--background"]
        print(f"▶ npx hyperframes@{hf.HF_VERSION} preview {' '.join(extra)}")
        sys.exit(subprocess.run(hf.hf_cmd("preview", *extra), cwd=proj, env=hf.hf_env()).returncode)
    import neuro_remotion as nr
    if a.parar:
        nr.studio_stop(proj)
        return
    nr.build(proj, quiet=True)
    checkpoint(proj, "antes de abrir o Studio", quiet=True)
    watcher = [sys.executable, "-I", str(Path(__file__).resolve()), "vigiar", "--project", str(proj)]
    nr.studio_start(proj, abrir=not a.sem_navegador, porta=a.porta, watcher_cmd=watcher)


def cmd_vigiar(a):
    """Roda junto com o Studio: Studio grava TSX → sincroniza JSON → checkpoint (com 4 s de calma)."""
    proj = proj_of(a)
    import neuro_remotion as nr
    g = nr.gdir(proj)
    watched = [g / l for l in nr.LAYERS] + [nr.rdir(proj) / "src" / "Root.tsx"]
    seen = {p: (p.stat().st_mtime_ns if p.exists() else 0) for p in watched}
    pending = 0.0
    print(f"[vigia] acompanhando {proj}", flush=True)
    while True:
        st = nr.studio_state(proj)
        if not st or not nr._alive(st.get("pid")):
            if pending:
                checkpoint(proj, "Studio: edições", quiet=True)
            print("[vigia] Studio encerrado; saindo.", flush=True)
            return
        changed = []
        for p in watched:
            m = p.stat().st_mtime_ns if p.exists() else 0
            if m != seen[p]:
                seen[p] = m
                changed.append(p)
        if changed:
            time.sleep(0.4)  # o Studio pode gravar em rajada
            est = nr.load_estado(proj)
            if any(p.name in nr.SYNCED for p in changed) and any(l in nr.SYNCED for l in nr.changed_layers(proj, est)):
                try:
                    res = nr.sincronizar(proj, quiet=True)
                    for n in res.get("notas", []):
                        print(f"[vigia] {n}", flush=True)
                except SystemExit:
                    print("[vigia] sincronizar falhou; veja o projeto.", flush=True)
                seen = {p: (p.stat().st_mtime_ns if p.exists() else 0) for p in watched}
            pending = time.time()
        if pending and time.time() - pending > 4.0:
            ref = checkpoint(proj, "Studio: edições", quiet=True)
            if ref:
                print(f"[vigia] checkpoint {ref}", flush=True)
            pending = 0.0
        time.sleep(0.6)


def cmd_sincronizar(a):
    proj = proj_of(a)
    if engine_of(proj) != "remotion":
        hf.die("`sincronizar` é do motor Remotion (no HyperFrames as edições do Studio ficam protegidas pelo build).")
    import neuro_remotion as nr
    nr.sincronizar(proj)
    checkpoint(proj, "sincronizar (Studio → JSON)")


def cmd_check(a):
    proj = proj_of(a)
    if engine_of(proj) == "remotion":
        import neuro_remotion as nr
        sys.exit(nr.check(proj))
    a.project = str(proj)
    hf.cmd_check(a)


def cmd_snapshot(a):
    proj = proj_of(a)
    if engine_of(proj) == "remotion":
        import neuro_remotion as nr
        nr.stills(proj, escala=a.escala, extra_frames=a.quadro)
        return
    a.project = str(proj)
    hf.cmd_snapshot(a)


def cmd_render(a):
    proj = proj_of(a)
    if engine_of(proj) == "remotion":
        import neuro_remotion as nr
        nr.render(proj, a.quality, a.output, a.extra, getattr(a, "resolucao", None), getattr(a, "codec", None), getattr(a, "qualidade", None))
    else:
        a.project = str(proj)
        try:
            hf.cmd_render(a)
        except SystemExit as e:
            if e.code:
                raise
    checkpoint(proj, f"render ({a.quality})", quiet=True)


def cmd_master(a):
    proj = proj_of(a)
    a.project = str(proj)
    hf.cmd_master(a)


def cmd_exportacao(a):
    """Mostra ou muda as decisões de exportação do projeto (o fps é fixado no init, junto com o mezanino)."""
    import neuro_export as nx
    proj = proj_of(a)
    cfg = hf.load_json(proj / "neuro.json")
    profiles, *_ = hf.load_presets()
    profile = profiles.get(cfg["profile"], {})
    mudou = any(getattr(a, k, None) for k in ("resolucao", "codec", "qualidade"))
    if getattr(a, "fps", None):
        hf.die("o fps é decidido no init (o mezanino e a timeline usam esse fps); refaça o init com --fps para mudar.")
    try:
        pl = nx.plano_projeto(cfg, profile, a.resolucao, a.codec, a.qualidade)
    except ValueError as e:
        hf.die(str(e))
    if mudou:
        cfg["export"] = dict(pl["export"], fps=cfg.get("export", {}).get("fps", "original"))
        hf.save_json(proj / "neuro.json", cfg)
    mzp = proj / cfg.get("mezanino", "assets/base.mp4")
    mz = hf.media_info(mzp) if mzp.exists() else {"width": cfg["width"], "height": cfg["height"]}
    if a.json:
        print(json.dumps(dict(pl, mezanino_atual={"largura": mz["width"], "altura": mz["height"]}), ensure_ascii=False, indent=2))
    else:
        print(("✓ exportação atualizada: " if mudou else "Exportação: ")
              + ", ".join(f"{s['resolucao']} ({s['largura']}x{s['altura']})" for s in pl["saidas"])
              + f" · {pl['codec_nome']}" + (f" CRF {pl['crf']}" if pl["crf"] is not None else "") + f" · {cfg['fps']} fps")
        for av in pl["avisos"]:
            print(f"  ⚠ {av}")
        maior = max(pl["saidas"], key=lambda s: s["largura"])
        alvo = (pl["mezanino"]["largura"], pl["mezanino"]["altura"])
        if a.mezanino:
            src = Path(cfg.get("source_video", ""))
            if not src.is_file():
                hf.die(f"a fonte original não está mais em {src}; o mezanino não pode ser refeito.")
            info = hf.prepare_base_video(src, mzp.with_suffix(".novo.mp4"), int(cfg["fps"]), int(cfg["width"]), int(cfg["height"]),
                                         profile, bool((cfg.get("video_prep") or {}).get("grade")), False, alvo=alvo)
            os.replace(mzp.with_suffix(".novo.mp4"), mzp)
            cfg["video_prep"] = info
            hf.save_json(proj / "neuro.json", cfg)
            print(f"✓ mezanino refeito em {alvo[0]}x{alvo[1]} (mesmos fps e duração: cortes e cenas continuam valendo)")
        elif mz["width"] < alvo[0]:
            print(f"  ⚠ o mezanino tem {mz['width']}x{mz['height']}, a fonte rende {alvo[0]}x{alvo[1]} para {maior['resolucao']}: "
                  f"rode de novo com --mezanino para refazê-lo sem perder detalhe (cortes e cenas continuam valendo).")
    if mudou or a.mezanino:
        checkpoint(proj, "exportação: " + ", ".join(pl["export"]["resolucoes"]) + f" {pl['codec']}", quiet=True)


def cmd_salvar(a):
    proj = proj_of(a)
    if engine_of(proj) == "remotion":
        import neuro_remotion as nr
        if nr.changed_layers(proj, nr.load_estado(proj)):
            nr.sincronizar(proj, quiet=True)
    ref = checkpoint(proj, a.mensagem or "salvar")
    if not ref:
        print("  nada mudou desde o último checkpoint.")


def cmd_historico(a):
    proj = proj_of(a)
    if not (proj / ".git").exists():
        print("  sem histórico ainda.")
        return
    print(_git(proj, "log", f"-n{a.n}", "--date=format:%d/%m %H:%M", "--pretty=format:%h  %ad  %s").stdout)


def cmd_voltar(a):
    proj = proj_of(a)
    if _git(proj, "rev-parse", "--verify", f"{a.ref}^{{commit}}").returncode != 0:
        hf.die(f"Checkpoint '{a.ref}' não existe. Veja `historico`.")
    checkpoint(proj, f"antes de voltar para {a.ref}", quiet=True)
    r = _git(proj, "checkout", a.ref, "--", ".")
    if r.returncode != 0:
        hf.die(r.stderr)
    print(f"✓ arquivos de texto restaurados de {a.ref}")
    if engine_of(proj) == "remotion":
        import neuro_remotion as nr
        est = nr.load_estado(proj)
        est["camadas"] = {l: nr.sha(nr.gdir(proj) / l) for l in nr.LAYERS}
        est["fontes_hash"] = nr.fontes_hash(proj)
        est.pop("mantidas_do_studio", None)
        hf.save_json(nr.estado_path(proj), est)
        nr.build(proj, force=True)
    checkpoint(proj, f"voltar para {a.ref}")


def cmd_motor(a):
    import neuro_remotion as nr
    if a.acao == "instalar":
        nr.ensure_engine(force=a.force)
        return
    d = nr.engine_dir()
    ok = nr.engine_ready()
    print(f"Motor Remotion {nr.REMOTION_VERSION}: {'instalado' if ok else 'não instalado'} em {d}")
    if ok:
        r = subprocess.run([str(d / "node_modules" / ".bin" / "remotion"), "versions"], cwd=d, capture_output=True, text=True)
        print("  " + ("versões consistentes" if "correct version" in (r.stdout + r.stderr) else (r.stdout + r.stderr).strip()[-400:]))
    else:
        print("  instale com: neuro-mv-edit remotion setup   (ou no primeiro `projeto init --engine remotion`)")
    print(f"  {nr.LICENSE_NOTE}")
    sys.exit(0 if ok else 1)


def cmd_status(a):
    proj = proj_of(a)
    cfg = hf.load_json(proj / "neuro.json")
    eng = cfg.get("engine", "hyperframes")
    print(f"Projeto {proj.name} · motor {eng} · perfil {cfg['profile']} · {cfg['width']}x{cfg['height']} @ {cfg['fps']} fps")
    edl = edlmod.load_edl(proj)
    print(f"  duração do filme {float(cfg['duration']):.2f}s" + (f" · {edlmod.describe(edl)}" if edl else " · sem cortes"))
    cues = hf.load_json(proj / "cues.json", default={})
    print(f"  {len(cues.get('scenes', []))} cenas · {len(cues.get('camera', []))} movimentos de câmera · "
          f"música {'sim' if (cues.get('music') or {}).get('src') else 'não'} · legendas "
          f"{'sim' if (proj / 'dados' / 'legendas.json').exists() else 'não'}")
    if eng == "remotion":
        import neuro_remotion as nr
        st = nr.studio_state(proj)
        if st and nr._alive(st.get("pid")):
            print(f"  Studio aberto: {st['url']}")
        est = nr.load_estado(proj)
        if est.get("mantidas_do_studio"):
            print("  camadas com edições do Studio mantidas: " + ", ".join(est["mantidas_do_studio"]))
        pend = nr.changed_layers(proj, est)
        if pend:
            print("  edições do Studio ainda não sincronizadas: " + ", ".join(pend))
    if (proj / ".git").exists():
        print("  último checkpoint: " + _git(proj, "log", "-1", "--pretty=format:%h %s (%cr)").stdout)
    last = hf.load_json(proj / ".neuro-build.json", default={}).get("last_render")
    if last:
        print(f"  último render: {last}")


# ───────────────────────────── CLI ─────────────────────────────

def main():
    p = argparse.ArgumentParser(prog="neuro-mv-edit projeto", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = p.add_subparsers(dest="cmd", required=True)

    def proj_arg(x):
        x.add_argument("--project", "-P", default=".", help="pasta do projeto (padrão: a atual)")

    i = sp.add_parser("init", help="cria o projeto")
    __import__("neuro_export").add_args(i)
    i.add_argument("--engine", "-e", choices=ENGINES, help="motor de edição (padrão: NEURO_ENGINE, engine_default do perfil, remotion)")
    i.add_argument("--profile", "-p", required=True)
    i.add_argument("--video", "-v", required=True)
    i.add_argument("--out", "-o", required=True)
    i.add_argument("--platform")
    i.add_argument("--theme")
    i.add_argument("--estilo", help="estilo de edição (padrão: estilo_padrao do perfil)")
    i.add_argument("--head-y", type=int)
    i.add_argument("--head-x", type=int)
    i.add_argument("--layout", choices=["split_lateral", "lower_third"])
    i.add_argument("--no-grade", action="store_true")
    i.add_argument("--reencode", action="store_true")
    i.add_argument("--force", action="store_true")
    i.set_defaults(fn=cmd_init)

    t = sp.add_parser("transcrever", help="transcrição por palavra (whisper)")
    proj_arg(t)
    t.add_argument("--model", default="small")
    t.add_argument("--language", default="pt")
    t.set_defaults(fn=cmd_transcrever)

    c = sp.add_parser("legendas", help="corrige o transcript e gera as legendas")
    proj_arg(c)
    c.add_argument("--transcript")
    c.add_argument("--fix", action="append")
    c.add_argument("--apply-glossary", action="store_true")
    c.add_argument("--learn", action="store_true")
    c.add_argument("--style", choices=["pop", "karaoke"])
    c.add_argument("--force-burn", action="store_true")
    c.set_defaults(fn=cmd_legendas)

    k = sp.add_parser("cortar", help="decupagem: silêncios, respiros e claquetes → edl.json")
    proj_arg(k)
    k.add_argument("--preset", choices=sorted(edlmod.PRESETS), help="natural | tight (padrão: o do estilo do projeto, senão natural)")
    k.add_argument("--limiar-ms", type=float, help="pausa máxima mantida, em ms (padrão: estilo do projeto → ritmo do perfil → preset)")
    k.add_argument("--remover", action="append", help="trecho da fonte a remover, em segundos: 12.3-15.8 (repetível)")
    k.add_argument("--manter", action="append", help="trecho da fonte a proteger de cortes: 40-44.5 (repetível)")
    k.add_argument("--sem-silencio", action="store_true", help="não confirmar os buracos com silencedetect")
    k.add_argument("--sem-claquete", action="store_true", help="ignorar as deixas de claquete da memória")
    k.add_argument("--nenhum", action="store_true", help="desfaz os cortes (vídeo inteiro)")
    k.add_argument("--dry-run", action="store_true")
    k.add_argument("--verbose", action="store_true")
    k.set_defaults(fn=cmd_cortar)

    b = sp.add_parser("build", help="gera o projeto do motor")
    proj_arg(b)
    b.add_argument("--force", action="store_true", help="regera inclusive as camadas editadas no Studio")
    b.add_argument("--force-burn", action="store_true")
    b.set_defaults(fn=cmd_build)

    s = sp.add_parser("estudio", aliases=["studio"], help="abre a interface web para acompanhar")
    proj_arg(s)
    s.add_argument("--parar", action="store_true")
    s.add_argument("--sem-navegador", action="store_true")
    s.add_argument("--porta", type=int)
    s.add_argument("extra", nargs=argparse.REMAINDER)
    s.set_defaults(fn=cmd_estudio)

    v = sp.add_parser("vigiar", help=argparse.SUPPRESS)
    proj_arg(v)
    v.set_defaults(fn=cmd_vigiar)

    y = sp.add_parser("sincronizar", aliases=["sync"], help="(Remotion) Studio → edl.json/cues.json")
    proj_arg(y)
    y.set_defaults(fn=cmd_sincronizar)

    ck = sp.add_parser("check", help="validações do motor")
    proj_arg(ck)
    ck.add_argument("--json", action="store_true")
    ck.add_argument("extra", nargs=argparse.REMAINDER)
    ck.set_defaults(fn=cmd_check)

    sn = sp.add_parser("snapshot", help="quadros de revisão")
    proj_arg(sn)
    sn.add_argument("--escala", type=float, default=0.5)
    sn.add_argument("--quadro", type=int, action="append", help="(Remotion) quadro extra")
    sn.add_argument("extra", nargs=argparse.REMAINDER)
    sn.set_defaults(fn=cmd_snapshot)

    ex = sp.add_parser("exportacao", aliases=["exportação"], help="mostra ou muda resolução, codec e qualidade da exportação")
    proj_arg(ex)
    __import__("neuro_export").add_args(ex)
    ex.add_argument("--mezanino", action="store_true", help="refaz assets/base.mp4 na resolução útil da fonte para a maior saída")
    ex.add_argument("--json", action="store_true")
    ex.set_defaults(fn=cmd_exportacao)

    r = sp.add_parser("render", help="vídeo final do motor")
    __import__("neuro_export").add_args(r, render=True)
    proj_arg(r)
    r.add_argument("--quality", default="delivery", choices=["draft", "looks", "delivery"])
    r.add_argument("--output", "-o")
    r.add_argument("extra", nargs=argparse.REMAINDER)
    r.set_defaults(fn=cmd_render)

    m = sp.add_parser("master", help="loudness 2 passagens + cópia leve")
    proj_arg(m)
    m.add_argument("--input", "-i")
    m.add_argument("--name")
    m.add_argument("--lufs", type=float)
    m.add_argument("--light", action="store_true")
    m.add_argument("--network")
    m.set_defaults(fn=cmd_master)

    sv = sp.add_parser("salvar", help="checkpoint git do projeto")
    proj_arg(sv)
    sv.add_argument("--mensagem", "-m")
    sv.set_defaults(fn=cmd_salvar)

    h = sp.add_parser("historico", help="checkpoints do projeto")
    proj_arg(h)
    h.add_argument("-n", type=int, default=25)
    h.set_defaults(fn=cmd_historico)

    vt = sp.add_parser("voltar", help="restaura um checkpoint")
    proj_arg(vt)
    vt.add_argument("ref")
    vt.set_defaults(fn=cmd_voltar)

    st = sp.add_parser("status", help="resumo do projeto")
    proj_arg(st)
    st.set_defaults(fn=cmd_status)

    mo = sp.add_parser("motor", help="instala/confere o motor Remotion compartilhado")
    mo.add_argument("acao", choices=["instalar", "status"], nargs="?", default="status")
    mo.add_argument("--force", action="store_true", help="reinstala mesmo se já existir")
    mo.set_defaults(fn=cmd_motor)

    a = p.parse_args()
    if getattr(a, "extra", None) and a.extra and a.extra[0] == "--":
        a.extra = a.extra[1:]
    a.fn(a)


if __name__ == "__main__":
    main()

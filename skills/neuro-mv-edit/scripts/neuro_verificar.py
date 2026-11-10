#!/usr/bin/env python3
"""
neuro_verificar.py — verificação (e correção) do ambiente ANTES da primeira edição da sessão.

Roda depois das decisões do usuário (motor, resolução, codec), porque o que é necessário depende delas:
4K pede disco e memória; HEVC pede libx265; ProRes pede prores_ks; Remotion pede o motor e o navegador;
HyperFrames pede Node 22 e o CLI fixado. Confere também as skills de apoio e os MCPs.

  python3 neuro_verificar.py [--motor remotion|hyperframes] [--resolucao 4k,1080p] [--codec h264|hevc|prores]
                             [--video fonte.mp4] [--corrigir] [--json]
  python3 neuro_verificar.py --hook     # SessionStart do Claude Code: rápido, sem rede, devolve o contexto da sessão

`--corrigir` instala o que falta e é seguro instalar sem perguntar (motor Remotion, navegador do render, CLI do
HyperFrames, skills de apoio, fontes, ffmpeg pelo Homebrew). O resto vira instrução com o comando exato.
O resultado fica em ~/.neuro-mv-edit/verificacao.json (o hook lê dali).
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))

NEURO_HOME = Path(os.environ.get("NEURO_HOME", str(Path.home() / ".neuro-mv-edit")))
CACHE = NEURO_HOME / "verificacao.json"
HF_VERSION = os.environ.get("NEURO_HF_VERSION", "0.9.19")
REMOTION_VERSION = os.environ.get("NEURO_REMOTION_VERSION", "4.0.539")
SKILL_ROOTS = [Path(os.environ.get("CLAUDE_CONFIG_DIR") or (Path.home() / ".claude")) / "skills", Path.home() / ".agents" / "skills"]
SKILLS_APOIO = {
    "remotion": [("remotion-best-practices", "remotion-dev/skills")],
    "hyperframes": [("hyperframes", None), ("hyperframes-cli", None), ("hyperframes-registry", None), ("media-use", None)],
}
IS_MAC, IS_WIN = sys.platform == "darwin", sys.platform == "win32"


class Rel:
    """Relatório: cada item tem id, título, status (ok | aviso | falta), detalhe e, se houver, o comando de correção."""

    def __init__(self, corrigir: bool, silencioso: bool):
        self.itens: list[dict] = []
        self.corrigir = corrigir
        self.silencioso = silencioso

    def add(self, iid: str, titulo: str, status: str, detalhe: str = "", correcao: str | None = None, corrigido: bool = False):
        it = {"id": iid, "titulo": titulo, "status": status, "detalhe": detalhe}
        if correcao:
            it["correcao"] = correcao
        if corrigido:
            it["corrigido"] = True
        self.itens.append(it)
        if not self.silencioso:
            m = {"ok": "✓", "aviso": "⚠", "falta": "✗"}[status]
            extra = f" — {detalhe}" if detalhe else ""
            print(f"  {m} {titulo}{extra}" + (" (corrigido agora)" if corrigido else ""))
            if correcao and status != "ok":
                print(f"      → {correcao}")

    def secao(self, nome: str):
        if not self.silencioso:
            print(f"\n{nome}")


def sh(cmd: list[str], timeout: int = 60, cwd: str | None = None, env: dict | None = None) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd, env=env)
    except (OSError, subprocess.TimeoutExpired) as e:
        return subprocess.CompletedProcess(cmd, 127, "", str(e))


def corre(rel: Rel, cmd: list[str], timeout: int = 900, cwd: str | None = None, env: dict | None = None) -> bool:
    if not rel.silencioso:
        print(f"      ↻ {' '.join(cmd)}")
    return sh(cmd, timeout=timeout, cwd=cwd, env=env).returncode == 0


# ───────────────────────────── ferramentas ─────────────────────────────

def ffmpeg_info() -> dict:
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        return {}
    first = (sh(["ffmpeg", "-version"]).stdout.splitlines() or [""])[0]
    ver = (first.split("version", 1)[1].split()[0].lstrip("n") if "version" in first else "?")
    major = int(ver.split(".")[0]) if ver[:1].isdigit() else 99
    enc = sh(["ffmpeg", "-hide_banner", "-encoders"]).stdout
    fil = sh(["ffmpeg", "-hide_banner", "-filters"]).stdout
    return {"versao": ver, "major": major,
            "encoders": {e for e in ("libx264", "libx265", "prores_ks", "aac") if re.search(rf"\s{e}\s", enc)},
            "filtros": {f for f in ("loudnorm", "sidechaincompress", "zscale", "tonemap", "silencedetect") if re.search(rf"\s{f}\s", fil)}}


def instalar_ffmpeg_cmd() -> str:
    if IS_MAC:
        return "brew install ffmpeg"
    if IS_WIN:
        return "winget install --id Gyan.FFmpeg -e"
    return "sudo apt install -y ffmpeg   (ou o gerenciador da sua distribuição)"


def check_base(rel: Rel, decisoes: dict):
    rel.secao("Ferramentas")
    py = sys.version_info
    rel.add("python", f"Python {py.major}.{py.minor}", "ok" if py >= (3, 10) else "falta",
            "" if py >= (3, 10) else "precisa do 3.10 ou mais novo", None if py >= (3, 10) else "instale o Python 3.10+")

    fi = ffmpeg_info()
    if not fi and rel.corrigir and IS_MAC and shutil.which("brew"):
        if corre(rel, ["brew", "install", "ffmpeg"], timeout=1800):
            fi = ffmpeg_info()
            if fi:
                rel.add("ffmpeg", f"ffmpeg {fi['versao']}", "ok", "instalado pelo Homebrew", corrigido=True)
    if not fi:
        rel.add("ffmpeg", "ffmpeg e ffprobe", "falta", "não estão no PATH", instalar_ffmpeg_cmd())
    elif not any(i["id"] == "ffmpeg" for i in rel.itens):
        ok = fi["major"] >= 5
        rel.add("ffmpeg", f"ffmpeg {fi['versao']}", "ok" if ok else "falta", "" if ok else "precisa do 5 ou mais novo",
                None if ok else instalar_ffmpeg_cmd())
    if fi:
        precisa = {"libx264", "aac"}
        codec = decisoes.get("codec") or "h264"
        if codec == "hevc":
            precisa.add("libx265")
        if codec == "prores" or decisoes.get("motor") == "hyperframes":
            precisa.add("prores_ks")
        faltam = sorted(precisa - fi["encoders"])
        rel.add("ffmpeg-codecs", "Codificadores (" + ", ".join(sorted(precisa)) + ")", "falta" if faltam else "ok",
                f"ausentes: {', '.join(faltam)}" if faltam else "", f"reinstale um ffmpeg completo: {instalar_ffmpeg_cmd()}" if faltam else None)
        ff = sorted({"loudnorm", "sidechaincompress", "silencedetect"} - fi["filtros"])
        rel.add("ffmpeg-filtros", "Filtros de áudio (loudnorm, sidechain, silencedetect)", "falta" if ff else "ok",
                f"ausentes: {', '.join(ff)}" if ff else "", instalar_ffmpeg_cmd() if ff else None)
        hdr = {"zscale", "tonemap"} <= fi["filtros"]
        rel.add("ffmpeg-hdr", "Conversão de HDR (iPhone/HLG) para SDR", "ok" if hdr else "aviso",
                "" if hdr else "sem zscale: vídeos HDR saem com cores lavadas", None if hdr else instalar_ffmpeg_cmd())

    node = shutil.which("node")
    nv = sh(["node", "--version"]).stdout.strip() if node else ""
    major = int(nv.lstrip("v").split(".")[0]) if nv[:2].lstrip("v")[:1].isdigit() else 0
    ok = major >= 22
    rel.add("node", f"Node.js {nv or 'ausente'}", "ok" if ok else "falta",
            "" if ok else "o HyperFrames e o render precisam do Node 22+",
            None if ok else ("brew install node@22" if IS_MAC else "instale o Node.js 22 LTS (nodejs.org)"))


# ───────────────────────────── motores ─────────────────────────────

def check_remotion(rel: Rel, decisoes: dict):
    rel.secao(f"Motor Remotion {REMOTION_VERSION}")
    eng = NEURO_HOME / "remotion" / REMOTION_VERSION
    instalado = (eng / "node_modules" / ".bin" / "remotion").exists() and (eng / ".neuro-engine.json").exists()
    if not instalado and rel.corrigir:
        try:
            import neuro_remotion as nr
            nr.ensure_engine()
            instalado = (eng / ".neuro-engine.json").exists()
            if instalado:
                rel.add("remotion", "Motor Remotion", "ok", str(eng), corrigido=True)
        except SystemExit:
            pass
        except Exception as e:  # noqa: BLE001
            rel.add("remotion", "Motor Remotion", "falta", f"a instalação falhou: {e}", "neuro-mv-edit projeto motor instalar")
            return
    if not instalado:
        rel.add("remotion", "Motor Remotion", "falta", f"não instalado em {eng} (~250 MB)", "neuro-mv-edit projeto motor instalar")
        return
    if not any(i["id"] == "remotion" for i in rel.itens):
        rel.add("remotion", "Motor Remotion", "ok", str(eng))
    shell_dir = eng / "node_modules" / ".remotion"
    tem_shell = shell_dir.exists() and any(shell_dir.glob("chrome-headless-shell/*"))
    if not tem_shell and rel.corrigir:
        tem_shell = corre(rel, [str(eng / "node_modules" / ".bin" / "remotion"), "browser", "ensure"], cwd=str(eng))
        if tem_shell:
            rel.add("remotion-browser", "Navegador do render (Chrome Headless Shell)", "ok", corrigido=True)
    if not any(i["id"] == "remotion-browser" for i in rel.itens):
        rel.add("remotion-browser", "Navegador do render (Chrome Headless Shell)", "ok" if tem_shell else "falta",
                "" if tem_shell else "baixado na primeira renderização (~100 MB)",
                None if tem_shell else f"cd {eng} && npx remotion browser ensure")
    lic = bool(os.environ.get("REMOTION_LICENSE_KEY"))
    rel.add("remotion-licenca", "Licença do Remotion", "ok" if lic else "aviso",
            "REMOTION_LICENSE_KEY definida" if lic else
            "grátis até 3 pessoas na empresa; a partir de 4, Company License (remotion.dev/license) e REMOTION_LICENSE_KEY")


def check_hyperframes(rel: Rel, decisoes: dict, rapido: bool):
    titulo = f"CLI do HyperFrames {HF_VERSION}" + (" (cartões com alfa no Remotion)" if decisoes.get("motor") == "remotion" else "")
    rel.secao("HyperFrames")
    if rapido:
        cache = list((Path.home() / ".npm" / "_npx").glob(f"*/node_modules/hyperframes/package.json"))
        vers = set()
        for c in cache:
            try:
                vers.add(json.loads(c.read_text()).get("version"))
            except (OSError, ValueError):
                pass
        ok = HF_VERSION in vers
        rel.add("hyperframes", titulo, "ok" if ok else "aviso", "" if ok else "não está no cache do npx (baixa no primeiro uso)",
                None if ok else f"npx --yes hyperframes@{HF_VERSION} --version")
        return
    env = dict(os.environ, HYPERFRAMES_NO_UPDATE_CHECK="1")
    r = sh(["npx", "--yes", f"hyperframes@{HF_VERSION}", "--version"], timeout=300, env=env)
    rel.add("hyperframes", titulo, "ok" if r.returncode == 0 else "falta",
            r.stdout.strip()[:60] if r.returncode == 0 else (r.stderr or r.stdout).strip()[-160:],
            None if r.returncode == 0 else f"npx --yes hyperframes@{HF_VERSION} --version")
    if r.returncode != 0:
        return
    d = sh(["npx", "--yes", f"hyperframes@{HF_VERSION}", "doctor", "--json"], timeout=300, env=env).stdout
    try:
        checks = json.loads(d[d.find("{"):]).get("checks", []) if "{" in d else []
    except ValueError:
        checks = []
    chrome = next((c for c in checks if (c.get("name") or c.get("id")) == "Chrome"), None)
    if chrome is not None:
        ok = bool(chrome.get("ok"))
        if not ok and rel.corrigir:
            ok = corre(rel, ["npx", "--yes", f"hyperframes@{HF_VERSION}", "browser", "ensure"], env=env)
        rel.add("hyperframes-browser", "Navegador do HyperFrames", "ok" if ok else "falta", "",
                None if ok else f"npx hyperframes@{HF_VERSION} browser ensure", corrigido=ok and not chrome.get("ok"))
    wh = next((c for c in checks if (c.get("name") or c.get("id")) == "whisper-cpp"), None)
    if wh is not None:
        rel.add("whisper", "Transcrição (whisper)", "ok" if wh.get("ok") else "aviso",
                "" if wh.get("ok") else "baixa o modelo na primeira transcrição")


# ───────────────────────────── skills, MCPs, fontes ─────────────────────────────

def skill_instalada(nome: str) -> Path | None:
    for r in SKILL_ROOTS:
        if (r / nome / "SKILL.md").exists():
            return r / nome
    return None


def check_skills(rel: Rel, decisoes: dict, rapido: bool):
    rel.secao("Skills de apoio")
    motores = ["remotion", "hyperframes"] if decisoes.get("motor") in (None, "remotion") else ["hyperframes"]
    for motor in motores:
        for nome, repo in SKILLS_APOIO[motor]:
            if motor == "hyperframes" and decisoes.get("motor") == "remotion" and nome not in ("hyperframes", "hyperframes-cli"):
                continue
            p = skill_instalada(nome)
            fix = (f"npx -y skills add {repo} --skill {nome} -g -y -a claude-code" if repo
                   else f"npx --yes hyperframes@{HF_VERSION} skills update")
            if not p and rel.corrigir and not rapido:
                ok = corre(rel, fix.split(), timeout=600)
                p = skill_instalada(nome) if ok else None
                if p:
                    rel.add(f"skill-{nome}", f"/{nome}", "ok", str(p), corrigido=True)
                    continue
            rel.add(f"skill-{nome}", f"/{nome}", "ok" if p else "aviso", str(p) if p else "ausente", None if p else fix)


def check_mcps(rel: Rel):
    rel.secao("MCPs")
    plugin = os.environ.get("CLAUDE_PLUGIN_ROOT")
    mcp_json = SKILL_ROOT.parent.parent / ".mcp.json"
    vem = mcp_json.exists() or bool(plugin)
    chave = bool(os.environ.get("ELEVENLABS_API_KEY"))
    rel.add("mcp-elevenlabs", "ElevenLabs (SFX, trilha, isolamento de voz)", "ok" if chave else "aviso",
            ("ELEVENLABS_API_KEY no ambiente" if chave else
             ("vem com o plugin; o agente confere se as ferramentas mcp__elevenlabs__* estão ativas e, se não, pede /mcp → elevenlabs"
              if vem else "sem o plugin: claude mcp add --transport http elevenlabs https://api.elevenlabs.io/v1/mcp")))


def check_fontes(rel: Rel, rapido: bool):
    rel.secao("Fontes")
    spec = importlib.util.spec_from_file_location("verify_env", SCRIPTS / "verify-env.py")
    ve = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ve)  # type: ignore[union-attr]
    destino = (Path.home() / "Library" / "Fonts") if IS_MAC else \
        (Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "Microsoft" / "Windows" / "Fonts" if IS_WIN else
         Path(os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local" / "share")) / "fonts")
    dirs = [destino, Path("/Library/Fonts"), Path("/System/Library/Fonts")]
    faltam = [f for f in ve.REQUIRED_FONTS if not any((d / f).exists() or (d / f.replace("-VariableFont", "")).exists() for d in dirs)]
    if faltam and rel.corrigir and not rapido:
        import contextlib
        import io
        with contextlib.redirect_stdout(io.StringIO()):
            ve.verify_and_install_fonts(destino)
        antes = len(faltam)
        faltam = [f for f in faltam if not (destino / f).exists()]
        if len(faltam) < antes:
            rel.add("fontes", "Fontes dos temas", "ok" if not faltam else "aviso",
                    f"{antes - len(faltam)} instaladas em {destino}" + (f"; faltam {', '.join(faltam)}" if faltam else ""), corrigido=True)
            return
    rel.add("fontes", "Fontes dos temas", "ok" if not faltam else "aviso", f"faltam {len(faltam)}: {', '.join(faltam[:4])}" if faltam else "",
            None if not faltam else "neuro-mv-edit verificar --corrigir")


# ───────────────────────────── 4K: disco e memória ─────────────────────────────

def memoria_gb() -> float | None:
    try:
        if IS_MAC:
            return int(sh(["sysctl", "-n", "hw.memsize"]).stdout.strip()) / 1024 ** 3
        if hasattr(os, "sysconf") and "SC_PHYS_PAGES" in os.sysconf_names:
            return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 1024 ** 3
    except (ValueError, OSError):
        pass
    return None


def check_recursos(rel: Rel, decisoes: dict, onde: Path):
    rel.secao("Disco e memória")
    import neuro_export as nx
    try:
        res = nx.parse_lista(decisoes.get("resolucao") or "1080p")
    except ValueError as e:
        rel.add("export", "Decisões de exportação", "falta", str(e))
        return
    alto = any(r in ("4k", "1440p", "original") for r in res)
    livre = shutil.disk_usage(str(onde if onde.exists() else Path.home())).free / 1024 ** 3
    precisa = None
    if decisoes.get("video") and Path(decisoes["video"]).is_file():
        try:
            f = nx.analisar_fonte(Path(decisoes["video"]))
            pl = nx.plano({"resolucoes": res, "codec": decisoes.get("codec") or "h264"}, 1080, 1920, f)
            precisa = nx.estimar_gb(pl, f["duracao"]) + 2
            for av in pl["avisos"]:
                rel.add("export-aviso", "Exportação", "aviso", av)
        except Exception:  # noqa: BLE001
            precisa = None
    if precisa is None:
        precisa = 20 if alto else 6
    rel.add("disco", f"Espaço livre ({livre:.0f} GB)", "ok" if livre >= precisa else "falta",
            f"~{precisa:.0f} GB para {', '.join(res)}" + ("" if livre >= precisa else " — libere espaço antes do render"))
    mem = memoria_gb()
    if mem is not None:
        ok = mem >= (16 if alto else 8)
        rel.add("memoria", f"Memória ({mem:.0f} GB)", "ok" if ok else "aviso",
                "" if ok else ("4K com menos de 16 GB: o render usa menos abas em paralelo e demora mais" if alto else "8 GB+ recomendado"))


# ───────────────────────────── principal ─────────────────────────────

def verificar(decisoes: dict, corrigir: bool, rapido: bool, silencioso: bool, onde: Path) -> dict:
    rel = Rel(corrigir, silencioso)
    check_base(rel, decisoes)
    motor = decisoes.get("motor")
    if motor in (None, "remotion"):
        check_remotion(rel, decisoes)
    check_hyperframes(rel, decisoes, rapido)
    check_skills(rel, decisoes, rapido)
    check_mcps(rel)
    check_fontes(rel, rapido)
    check_recursos(rel, decisoes, onde)
    falta = [i for i in rel.itens if i["status"] == "falta"]
    aviso = [i for i in rel.itens if i["status"] == "aviso"]
    out = {"data": datetime.now().isoformat(timespec="seconds"), "decisoes": decisoes, "rapido": rapido,
           "pronto": not falta, "faltas": len(falta), "avisos": len(aviso), "itens": rel.itens,
           "sistema": f"{platform.system()} {platform.machine()}"}
    if not rapido:
        try:
            NEURO_HOME.mkdir(parents=True, exist_ok=True)
            CACHE.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError:
            pass
    return out


def contexto_hook() -> str:
    """Texto curto que o SessionStart injeta: o fluxo de decisões + o estado da última verificação."""
    try:
        ult = json.loads(CACHE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        ult = None
    rapida = verificar({}, corrigir=False, rapido=True, silencioso=True, onde=Path.cwd())
    faltas = [i["titulo"] for i in rapida["itens"] if i["status"] == "falta"]
    linhas = [
        "Plugin neuro-mv-edit (edição de vídeo) instalado. O fluxo dele pede, antes da primeira edição da sessão, as decisões "
        "do usuário em múltipla escolha: motor (Remotion ou HyperFrames) e exportação — resolução (4K, 1440p, 1080p ou a "
        "original; pode ser mais de uma), codec (H.264, HEVC ou ProRes) e fps (o da fonte, 30 ou 60). "
        "`neuro-mv-edit exportacao analisar <vídeo>` mostra o que a fonte rende e recomenda. Depois das decisões, "
        "`neuro-mv-edit verificar --corrigir --motor <m> --resolucao <r> --codec <c> --video <vídeo>` confere e instala "
        "dependências (motor, navegador do render, skills de apoio, fontes, ffmpeg); o MCP do ElevenLabs está ativo quando "
        "as ferramentas mcp__elevenlabs__* aparecem na sessão (senão, /mcp).",
    ]
    if ult:
        linhas.append(f"Última verificação completa: {ult.get('data', '?')} — "
                      + ("pronto." if ult.get("pronto") else f"{ult.get('faltas')} pendência(s)."))
    else:
        linhas.append("Nenhuma verificação completa nesta máquina ainda.")
    if faltas:
        linhas.append("Faltando agora: " + ", ".join(faltas) + ".")
    return " ".join(linhas)


def main():
    ap = argparse.ArgumentParser(description="Verifica e corrige o ambiente da neuro-mv-edit")
    ap.add_argument("--motor", choices=["remotion", "hyperframes"])
    ap.add_argument("--resolucao", "--resolução", dest="resolucao")
    ap.add_argument("--codec", choices=["h264", "hevc", "prores", "h265"])
    ap.add_argument("--video", help="fonte da edição: estima disco e avisa upscale/HDR")
    ap.add_argument("--corrigir", action="store_true", help="instala o que falta")
    ap.add_argument("--rapido", action="store_true", help="sem rede e sem npx")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--hook", action="store_true", help="saída do hook SessionStart do Claude Code")
    a = ap.parse_args()

    if a.hook:
        try:
            ctx = contexto_hook()
        except Exception as e:  # noqa: BLE001 — o hook nunca pode travar a sessão
            ctx = f"neuro-mv-edit: verificação rápida falhou ({e}); rode `neuro-mv-edit verificar`."
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": ctx}}, ensure_ascii=False))
        return 0

    decisoes = {"motor": a.motor, "resolucao": a.resolucao, "codec": "hevc" if a.codec == "h265" else a.codec, "video": a.video}
    decisoes = {k: v for k, v in decisoes.items() if v}
    if not a.json:
        print("neuro-mv-edit · verificação do ambiente" + (" e correção" if a.corrigir else "")
              + (f" ({', '.join(f'{k} {v}' for k, v in decisoes.items() if k != 'video')})" if decisoes else ""))
    out = verificar(decisoes, a.corrigir, a.rapido, a.json, Path.cwd())
    if a.json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print("\n" + ("✓ Ambiente pronto." if out["pronto"] else f"✗ {out['faltas']} pendência(s) acima.")
              + (f" {out['avisos']} aviso(s)." if out["avisos"] else ""))
        if not out["pronto"] and not a.corrigir:
            print("  Rode de novo com --corrigir para instalar o que dá para instalar sozinho.")
    return 0 if out["pronto"] else 1


if __name__ == "__main__":
    sys.exit(main())

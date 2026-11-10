#!/usr/bin/env python3
"""
verify-env.py — Verificador e instalador automatizado de ambiente para a skill neuro-mv-edit.
Verifica executáveis (ffmpeg, node, npm, python3, whisper), fontes tipográficas oficiais
e pacotes necessários. Caso fontes ou recursos estejam ausentes, efetua o download e instalação.
"""

import os
import sys
import shutil
import urllib.request
import subprocess
import tarfile
import json
from pathlib import Path

# Fontes requeridas e suas URLs oficiais de download direto
REQUIRED_FONTS = {
    "BigShouldersDisplay-Black.ttf": "https://raw.githubusercontent.com/google/fonts/main/ofl/bigshouldersdisplay/BigShouldersDisplay%5Bwght%5D.ttf",
    "Fraunces.ttf": "https://raw.githubusercontent.com/google/fonts/main/ofl/fraunces/Fraunces%5BSOFT%2CWONK%2Copsz%2Cwght%5D.ttf",
    "Fraunces-Italic.ttf": "https://raw.githubusercontent.com/google/fonts/main/ofl/fraunces/Fraunces-Italic%5BSOFT%2CWONK%2Copsz%2Cwght%5D.ttf",
    "Inter-VariableFont.ttf": "https://raw.githubusercontent.com/google/fonts/main/ofl/inter/Inter%5Bopsz%2Cwght%5D.ttf",
    "CalSans-SemiBold.ttf": "https://registry.npmjs.org/cal-sans/-/cal-sans-1.0.1.tgz", # extraído do npm package
    "InstrumentSerif-Regular.ttf": "https://raw.githubusercontent.com/google/fonts/main/ofl/instrumentserif/InstrumentSerif-Regular.ttf",
    "InstrumentSerif-Italic.ttf": "https://raw.githubusercontent.com/google/fonts/main/ofl/instrumentserif/InstrumentSerif-Italic.ttf",
    "DMSans-VariableFont.ttf": "https://raw.githubusercontent.com/google/fonts/main/ofl/dmsans/DMSans%5Bopsz%2Cwght%5D.ttf",
    "DMSans-Italic-VariableFont.ttf": "https://raw.githubusercontent.com/google/fonts/main/ofl/dmsans/DMSans-Italic%5Bopsz%2Cwght%5D.ttf",
    "PlusJakartaSans-VariableFont.ttf": "https://raw.githubusercontent.com/google/fonts/main/ofl/plusjakartasans/PlusJakartaSans%5Bwght%5D.ttf",
    "PlusJakartaSans-Italic-VariableFont.ttf": "https://raw.githubusercontent.com/google/fonts/main/ofl/plusjakartasans/PlusJakartaSans-Italic%5Bwght%5D.ttf",
    "SpaceGrotesk-VariableFont.ttf": "https://raw.githubusercontent.com/google/fonts/main/ofl/spacegrotesk/SpaceGrotesk%5Bwght%5D.ttf"
}

REQUIRED_COMMANDS = ["ffmpeg", "ffprobe", "python3", "node", "npm"]

def check_cli_tools():
    print("🔍 [1/4] Verificando ferramentas de linha de comando...")
    status = {}
    all_ok = True
    for cmd in REQUIRED_COMMANDS:
        path = shutil.which(cmd)
        if path:
            print(f"  ✅ {cmd}: encontrado em {path}")
            status[cmd] = True
        else:
            print(f"  ❌ {cmd}: NÃO encontrado no PATH!")
            status[cmd] = False
            all_ok = False
    if status.get("ffmpeg"):
        try:
            first = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, timeout=15).stdout.splitlines()[0]
            ver = first.split("version", 1)[1].split()[0].lstrip("n")
            major = int(ver.split(".")[0]) if ver[:1].isdigit() else 99  # builds git ("N-…") são recentes
            if major < 5:
                print(f"  ❌ ffmpeg {ver}: a skill precisa do 5 ou mais novo (sidechaincompress, loudnorm 2 passagens)")
                all_ok = False
            else:
                print(f"  ✅ ffmpeg {ver}")
        except Exception as e:  # noqa: BLE001
            print(f"  ⚠️ versão do ffmpeg não verificada: {e}")
    return all_ok, status

HF_VERSION = os.environ.get("NEURO_HF_VERSION", "0.9.19")
HF_CORE_SKILLS = ["hyperframes", "hyperframes-cli", "hyperframes-registry", "media-use"]


def check_node_version():
    """HyperFrames exige Node.js 22+."""
    try:
        out = subprocess.run(["node", "--version"], capture_output=True, text=True, timeout=10).stdout.strip()
        major = int(out.lstrip("v").split(".")[0])
        if major >= 22:
            print(f"  ✅ Node.js {out} (HyperFrames exige 22+)")
            return True
        print(f"  ❌ Node.js {out}: HyperFrames exige 22+ (brew install node@22 ou nvm install 22)")
        return False
    except Exception as e:
        print(f"  ❌ Node.js não verificável: {e}")
        return False


def check_hyperframes():
    """Motor HyperFrames (alternativo ao Remotion e renderizador de cenas com alfa): CLI pinado + skills oficiais da HeyGen."""
    print("\n🔍 [2/4] Verificando motor HyperFrames (HTML → vídeo)...")
    ok = check_node_version()
    env = dict(os.environ, HYPERFRAMES_NO_UPDATE_CHECK="1")
    try:
        res = subprocess.run(["npx", "--yes", f"hyperframes@{HF_VERSION}", "--version"], capture_output=True, text=True, timeout=180, env=env)
        if res.returncode == 0:
            print(f"  ✅ HyperFrames CLI {res.stdout.strip()} (npx hyperframes@{HF_VERSION})")
        else:
            print(f"  ❌ HyperFrames CLI falhou: {(res.stderr or res.stdout).strip()[:200]}")
            ok = False
    except Exception as e:
        print(f"  ❌ HyperFrames CLI indisponível: {e}")
        return False
    try:
        res = subprocess.run(["npx", "--yes", f"hyperframes@{HF_VERSION}", "doctor", "--json"], capture_output=True, text=True, timeout=180, env=env)
        data = json.loads(res.stdout[res.stdout.find("{"):]) if "{" in res.stdout else {}
        for c in data.get("checks", []):
            name = c.get("name") or c.get("id")
            if name in ("Chrome", "FFmpeg", "FFprobe", "whisper-cpp"):
                mark = "✅" if c.get("ok") else ("ℹ️" if name == "whisper-cpp" else "❌")
                print(f"  {mark} {name}: {(c.get('detail') or c.get('message') or '')[:90]}")
                if name == "Chrome" and not c.get("ok"):
                    print(f"     → rode: npx hyperframes@{HF_VERSION} browser ensure")
                    ok = False
    except Exception as e:
        print(f"  ⚠️ doctor indisponível: {e}")
    roots = [Path.home() / ".claude" / "skills", Path.home() / ".agents" / "skills"]
    missing = [s for s in HF_CORE_SKILLS if not any((r / s / "SKILL.md").exists() for r in roots)]
    if missing:
        print(f"  ⚠️ Skills HyperFrames ausentes: {', '.join(missing)}")
        print(f"     → rode: npx hyperframes@{HF_VERSION} skills update   (instala o conjunto principal)")
    else:
        print(f"  ✅ Skills HyperFrames instaladas: {', '.join(HF_CORE_SKILLS)}")
    print("  ℹ️ Telemetria do HyperFrames: `npx hyperframes telemetry disable` ou HYPERFRAMES_NO_TELEMETRY=1 para desligar.")
    return ok


REMOTION_VERSION = os.environ.get("NEURO_REMOTION_VERSION", "4.0.539")
REMOTION_LICENSE = ("Licença do Remotion: grátis para pessoa física, empresas com até 3 pessoas e ONGs; a partir de 4 pessoas "
                    "(todo o pessoal) é preciso a Company License — https://www.remotion.dev/license. "
                    "Defina REMOTION_LICENSE_KEY para os renders irem com a chave. HyperFrames (Apache-2.0) não tem essa restrição.")


def check_remotion():
    """Motor Remotion compartilhado (~/.neuro-mv-edit/remotion/<versão>): node_modules, Chrome Headless Shell e versões."""
    print(f"\n🔍 [3/4] Motor Remotion {REMOTION_VERSION} (edição no Studio)...")
    home = Path(os.environ.get("NEURO_HOME", str(Path.home() / ".neuro-mv-edit")))
    eng = home / "remotion" / REMOTION_VERSION
    bin_ = eng / "node_modules" / ".bin" / "remotion"
    if not bin_.exists() or not (eng / ".neuro-engine.json").exists():
        print(f"  ℹ️ Não instalado em {eng}. Instale com `neuro-mv-edit remotion setup`")
        print("     (ou ele é instalado sozinho no primeiro `projeto init --engine remotion`; ~250 MB + navegador).")
        print(f"  ℹ️ {REMOTION_LICENSE}")
        return False
    try:
        res = subprocess.run([str(bin_), "versions"], cwd=eng, capture_output=True, text=True, timeout=60)
        out = res.stdout + res.stderr
        if "correct version" in out:
            print(f"  ✅ Remotion {REMOTION_VERSION} instalado e com versões consistentes ({eng})")
        else:
            print(f"  ⚠️ `remotion versions` acusou diferença — reinstale com `neuro-mv-edit remotion setup --force`\n{out[-400:]}")
        shell = list((eng / "node_modules" / ".remotion").glob("chrome-headless-shell/*")) if (eng / "node_modules" / ".remotion").exists() else []
        print(f"  {'✅ Chrome Headless Shell presente' if shell else '⚠️ Chrome Headless Shell ausente: rode `remotion setup --force`'}")
    except Exception as e:
        print(f"  ⚠️ Remotion não verificado: {e}")
    print(f"  ℹ️ {REMOTION_LICENSE}")
    return True

def verify_and_install_fonts(dest_dir):
    print(f"\n🔍 [4/4] Verificando fontes oficiais na pasta {dest_dir}...")
    dest_path = Path(dest_dir)
    dest_path.mkdir(parents=True, exist_ok=True)
    
    # Locais padrão de fontes do sistema para conferir se já estão instaladas globalmente
    system_font_dirs = [
        Path.home() / "Library/Fonts",
        Path("/Library/Fonts"),
        Path("/System/Library/Fonts"),
        dest_path
    ]

    for font_name, source_url in REQUIRED_FONTS.items():
        found = False
        # Checar se já existe no sistema ou na pasta local
        for sdir in system_font_dirs:
            if (sdir / font_name).exists() or (sdir / font_name.replace("-VariableFont", "")).exists():
                candidate = sdir / font_name if (sdir / font_name).exists() else sdir / font_name.replace("-VariableFont", "")
                if candidate.stat().st_size > 10000:
                    found = True
                    print(f"  ✅ Fonte encontrada: {font_name} ({candidate})")
                    break

        if not found:
            print(f"  ⬇️ Baixando fonte ausente: {font_name}...")
            local_target = dest_path / font_name
            try:
                if source_url.endswith(".tgz"):
                    # Extração do npm tarball (ex: cal-sans)
                    tgz_path = dest_path / "temp_font.tgz"
                    urllib.request.urlretrieve(source_url, tgz_path)
                    with tarfile.open(tgz_path, "r:gz") as tar:
                        for member in tar.getmembers():
                            if member.name.endswith(".ttf") or member.name.endswith(".woff2"):
                                tar.extract(member, path=dest_path)
                                extracted_file = dest_path / member.name
                                if extracted_file.exists():
                                    shutil.copy(extracted_file, local_target)
                                    break
                    if tgz_path.exists():
                        tgz_path.unlink()
                    shutil.rmtree(dest_path / "package", ignore_errors=True)  # pasta extraída do tarball do npm
                else:
                    urllib.request.urlretrieve(source_url, local_target)

                # Validar tamanho e cabeçalho TrueType/OpenType
                if local_target.exists() and local_target.stat().st_size > 5000:
                    with open(local_target, "rb") as f:
                        header = f.read(4)
                        # TrueType / OpenType signatures: 0x00010000, 'OTTO', 'true', 'typ1'
                        if header in [b'\x00\x01\x00\x00', b'OTTO', b'true', b'typ1']:
                            print(f"  ✅ Fonte baixada e validada com sucesso: {font_name}")
                        else:
                            print(f"  ⚠️ Arquivo baixado não é fonte TTF válida (possível HTML): {font_name}")
                else:
                    print(f"  ❌ Falha ao validar fonte baixada: {font_name}")
            except Exception as e:
                print(f"  ❌ Erro ao baixar {font_name}: {e}")

def check_elevenlabs_mcp():
    print("\n🔍 [extra] Verificando integração ElevenLabs MCP...")
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    uvx_path = shutil.which("uvx")
    
    if api_key:
        print("  ✅ ELEVENLABS_API_KEY: configurada no ambiente")
    else:
        print("  ℹ️ ELEVENLABS_API_KEY: não encontrada no ambiente atual.")
        print("     (Para hosted HTTP OAuth, adicione com: claude mcp add --transport http elevenlabs https://api.elevenlabs.io/v1/mcp)")

    if uvx_path:
        print(f"  ✅ uvx: encontrado em {uvx_path} (permite rodar 'uvx elevenlabs-mcp')")
    else:
        print("  ℹ️ uvx: não instalado (opcional, necessário apenas se for rodar o MCP Python local)")

def main():
    print("="*65)
    print(" NEURO MV EDIT — VERIFICADOR E INSTALADOR DE AMBIENTE")
    print("="*65)
    
    tools_ok, _ = check_cli_tools()
    hf_ok = check_hyperframes()
    remotion_ok = check_remotion()
    
    # Fontes do usuário (nunca dentro da skill: a pasta da skill é recriada a cada instalação)
    if sys.platform == "darwin":
        target_fonts_dir = Path.home() / "Library" / "Fonts"
    else:
        target_fonts_dir = Path(os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local" / "share")) / "fonts"
    verify_and_install_fonts(target_fonts_dir)
    if sys.platform.startswith("linux") and shutil.which("fc-cache"):
        subprocess.run(["fc-cache", "-f", str(target_fonts_dir)], capture_output=True)
    check_elevenlabs_mcp()

    print("\n" + "="*65)
    if tools_ok and hf_ok:
        print(" Diagnóstico concluído: ambiente pronto." + ("" if remotion_ok else " (motor Remotion ainda não instalado)"))
    else:
        print(" Diagnóstico concluído COM PENDÊNCIAS: corrija os itens ❌ acima.")
    print("="*65)
    sys.exit(0 if tools_ok and hf_ok else 1)

if __name__ == "__main__":
    main()

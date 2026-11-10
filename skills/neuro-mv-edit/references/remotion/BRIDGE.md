# Motor Remotion — guia da neuro-mv-edit

O motor `remotion` é o padrão para projetos novos. Ele transforma `edl.json` (cortes) e `cues.json` (cenas, câmera, som, efeitos) num projeto Remotion editável no **Remotion Studio**, com tudo salvo em arquivos e checkpoints git. O HyperFrames continua disponível como motor alternativo e como renderizador de cenas pontuais com alfa (seção 6).

Versão fixada: **Remotion 4.0.539** (`NEURO_REMOTION_VERSION` muda). Pacotes com versão exata e lock em `references/remotion-project/`.

## 1. Fluxo

```bash
NP="python3 scripts/neuro_project.py"     # ou: npx github:monrars1995/oneuros-mv-edit projeto
$NP init        --engine remotion --profile <perfil> --video bruto.mp4 --out projetos/x --head-y <px>
$NP transcrever -P projetos/x              # whisper por palavra, fonte inteira, --language pt
$NP legendas    -P projetos/x --apply-glossary --fix "errado=certo" --learn
$NP cortar      -P projetos/x              # edl.json (natural | tight), --dry-run para só ver
#   escreva projetos/x/cues.json
$NP build       -P projetos/x
$NP estudio     -P projetos/x              # Studio + vigia; diga a URL ao cliente
$NP check       -P projetos/x              # avisos do build + bundle compila
$NP snapshot    -P projetos/x              # PNG por cena + início/meio/fim
$NP render      -P projetos/x              # --quality draft|looks|delivery
$NP master      -P projetos/x --name NOME
```

O `init` cria o mezanino (`assets/base.mp4`: CFR, keyframe a cada 1 s, BT.709, grade do perfil), o tema (`assets/neuro-theme.css`), o `neuro.json`, um `edl.json` sem cortes e a pasta `remotion/`. Na primeira vez, instala o motor compartilhado em `~/.neuro-mv-edit/remotion/4.0.539` (~250 MB de pacotes + Chrome Headless Shell; `node_modules` de cada projeto é um symlink para lá). Instalação antecipada: `neuro-mv-edit remotion setup`.

## 2. Arquivos do projeto

| Caminho | Dono | Conteúdo |
|---|---|---|
| `neuro.json` | `init` | motor, perfil, tema, plataforma, fps, cabeça, faixas, loudness, mezanino |
| `edl.json` | `cortar`, Studio (via `sincronizar`) | segmentos da fonte em quadros (`in`/`out` exclusivo), motivo de cada corte |
| `cues.json` | você, Studio (tempos de cena) | cenas, câmera, `sfx`, `music`, `end`, `efeitos`, `broll` — tempos **do filme** |
| `assets/transcript.json` / `.fixed.json` | `transcrever` / `legendas` | palavras no tempo **da fonte** |
| `dados/legendas.json`, `dados/transcript.out.json` | `legendas`, `build` | legendas e palavras no tempo do filme |
| `dados/fala-<hash>.wav` | `build` | fala montada do EDL pelo ffmpeg (fades nas emendas) |
| `assets/music/ducked/*.wav` | `build` | trilha com ducking por sidechain |
| `cartoes-hf/<id>-<hash>.mov` | `build` | cenas renderizadas pelo HyperFrames (ProRes 4444 com alfa) |
| `remotion/src/gerado/*.tsx` | `build`, Studio | camadas editáveis (seção 3) |
| `remotion/src/Root.tsx` | scaffold, painel de props do Studio | `defaultProps` inline: `legendas`, `ganhoFala`, `ganhoMusica`, `ganhoSfx` |
| `.neuro/estado.json` | `build` | hashes das camadas e dos JSON, tempos gerados das cenas |
| `.git` | checkpoints | histórico de texto; mídia e renders ficam fora |

## 3. Camadas geradas (`remotion/src/gerado/`)

| Camada | Vem de | O Studio edita | O `sincronizar` lê de volta |
|---|---|---|---|
| `Cortes.tsx` | `edl.json` | duração e corte de cada clipe (`TransitionSeries`, ripple) | sim → `edl.json` |
| `Cenas.tsx` | `cues.scenes` | mover/esticar cada cartão (`Sequence`) | sim → `cues.json` (start/duration) |
| `Camera.tsx` | `cues.camera` | keyframes de `scale`/`translate` e easing | não (mantida como do Studio) |
| `Trilhas.tsx` | fala, SFX, `cues.music` | mover SFX, curva da trilha | não (mantida) |
| `Efeitos.tsx` | `cues.efeitos`, `cues.end` | keyframes de opacidade | não (mantida) |
| `Broll.tsx` | `cues.broll` | mover/aparar clipes | não (mantida) |
| `Legendas.tsx` | `dados/legendas.json` | — | — |

Regras do código gerado, para o Studio conseguir editar: valores literais nos props, um nó JSX por clipe/cena (sem `.map()`), estilos inline, `scale`/`translate` em vez de `transform`, `interpolate()` inline com easing por segmento.

## 4. Sincronização e proteção

1. O Studio grava cada edição direto no arquivo da camada.
2. Com o Studio aberto pelo `estudio`, o **vigia** percebe a gravação, roda o `sincronizar` e faz checkpoint depois de 4 s sem mudanças.
3. `sincronizar`:
   - `Cortes.tsx` → `edl.json`;
   - cenas movidas → `cues.json`;
   - se o corte mudou, as demais cenas, a câmera, os efeitos e o B-roll são remapeados pelo tempo da fonte (ficam presos à fala), a fala é remontada, as legendas são remapeadas e o `Root.tsx` ganha a nova duração.
4. `build`:
   - camada que você não tocou é regerada livremente;
   - camada editada no Studio que bate com a versão gerada (mesma árvore sintática, via Babel) é aceita;
   - camada com edição a mais (efeito solto num clipe, opacidade, keyframe de câmera) **fica como está**, com aviso, até um `build --force`.
5. Conflito: se uma camada lida de volta mudou no Studio **e** os JSON mudaram desde o último build, o `build` para. `sincronizar` fica com o Studio; `build --force` fica com os JSON.
6. **Antes de editar os JSON com o Studio aberto**, rode `sincronizar` (ou espere o vigia) e releia os arquivos.
7. `historico` lista os checkpoints; `voltar <ref>` restaura os arquivos de texto, regera a mídia derivada e cria um checkpoint novo (dá para voltar do voltar).

## 5. `cues.json` no motor Remotion

O esquema do HyperFrames (`references/hyperframes/BRIDGE.md` §3) vale igual: `scenes` (7 templates), `camera` (`punch_in`, `cut`, `zoom`, `shift`, `reset`, `shake`), `sfx`, `music`, `end`. Tempos no filme (depois dos cortes). Acréscimos:

```json
{
  "scenes": [
    {"id": "hook", "template": "hook", "start": 0.15, "duration": 4.6, "vars": {"headline": "SUA CPR PODE", "accent": "VENCER"}},
    {"id": "slam", "template": "hook", "start": 5.0, "duration": 2.0, "vars": {"headline": "ATENÇÃO"}, "motor": "hyperframes"},
    {"id": "bloco", "template": "quote", "start": 7.4, "duration": 3.0, "vars": {"quote": "—"}, "html": "blocos/headline-slam.html"}
  ],
  "efeitos": [{"kind": "flash", "at": 4.95, "dur": 0.1}, {"kind": "dip", "at": 10.2, "dur": 0.1, "intensidade": 0.4}],
  "broll": [{"src": "assets/broll/lavoura.mp4", "start": 12.0, "duration": 2.5, "trim": 3.0}],
  "music": {"src": "assets/music/trilha.wav", "volume": 0.14, "fade_in": 0.8, "fade_out": 1.2,
            "ducking": {"threshold": 0.03, "ratio": 4, "attack": 60, "release": 600}}
}
```

- `motor: "hyperframes"`: o cartão do template é renderizado pelo HyperFrames com alfa e entra como clipe.
- `html`: renderiza uma composição HyperFrames sua (por exemplo um bloco do registry instalado com `npx hyperframes add`) no lugar do template.
- `music.ducking: false` desliga o ducking.
- B-roll fica sobre o vídeo e sob os cartões.

## 6. Remotion + HyperFrames

- **Cartões nativos (padrão):** o mesmo gerador Python dos 7 templates emite HTML + tweens GSAP. O `CartaoGsap` monta isso com `@remotion/gsap`, então o cartão aparece ao vivo no Studio, idêntico ao do HyperFrames.
- **Cartões pelo HyperFrames:** use `motor` ou `html` para o que só o runtime do HyperFrames faz (blocos do registry, `remove-background`). A primeira renderização demora (~1–2 min por cena); depois fica em cache pelo hash do HTML + tema.
- **Regras do GSAP no Remotion:** nada de `onUpdate`/callbacks, `seek`/`play`, tween em objeto comum ou aleatoriedade sem semente. Valores numéricos que mudam (contadores) são calculados do quadro.

## 7. Render e QA

- `check`: avisos do build (leitura, respiro, densidade, linha que não cabe, SFX ausente) + `remotion compositions` (o bundle compila).
- `snapshot`: PNG de cada cena no momento em que ela pousa, mais início/meio/fim (`--quadro N` acrescenta). Abra todos.
- `render`:
  - `draft`: metade da resolução, CRF 28;
  - `looks`: JPEG 92 no CRF do perfil;
  - `delivery`: PNG por quadro, x264 `slow`, CRF do perfil (17).
  - A saída é H.264 yuv420p + AAC 320k, conferida contra a soma do `edl.json`.
- `master`: o mesmo do HyperFrames (loudnorm em 2 passagens, cópia leve). O vídeo é copiado, sem segunda compressão.

## 8. Licença

O Remotion é grátis para pessoa física, empresas com até 3 pessoas e ONGs. A partir de 4 pessoas (contando todo o pessoal) é preciso a Company License (https://www.remotion.dev/license): Creators US$ 25/mês por assento ou Automators US$ 0,01 por render, mínimo de US$ 100/mês. Render feito por agente conta como automação; o Studio não. Defina `REMOTION_LICENSE_KEY` e o `render` passa `--license-key`. O HyperFrames (Apache-2.0) não tem essa restrição.

## 9. Problemas comuns

| Sintoma | Causa | Correção |
|---|---|---|
| `build` para com "Conflito" | Studio e JSON mudaram juntos | `sincronizar` (fica com o Studio) ou `build --force` (fica com os JSON) |
| Aviso "mantive o seu arquivo" | camada com edição do Studio que o build não representa | ok se foi de propósito; `build --force` regera |
| `cortar` avisa "buraco sem silêncio medido" | o Whisper viu pausa onde há som (palavra arrastada, respiro, ruído) | ouça; se for respiro/ruído, `cortar --remover a-b` |
| Studio não abre | porta ocupada ou erro de bundle | veja `.neuro/studio.log`; `estudio --porta 3100`; `check` mostra o erro do bundle |
| Fonte errada no quadro | arquivo `.ttf` ausente em `assets/fonts` | `verify-env.py` e `init --force` |
| Cena HF sem alfa | composição com fundo opaco | o `html` da cena precisa de fundo transparente; o aviso mostra o `pix_fmt` |
| Render lento | PNG por quadro no `delivery` | use `looks` para revisão; `delivery` só na entrega |
| Edição sumiu depois do `build` | camada regerada sem proteção (não deveria) | `historico` + `voltar <ref>`; reporte o caso |

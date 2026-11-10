# Ponte Neuro MV Edit → HyperFrames

O HyperFrames (HeyGen, Apache 2.0) renderiza **HTML + CSS + GSAP** em MP4 de forma determinística: cada quadro é buscado (seek) numa timeline pausada no Chrome headless e codificado com FFmpeg. A mesma entrada gera sempre o mesmo vídeo. Desde a v1.5.0 a Neuro MV Edit tem dois motores à escolha (`projeto init --engine`): o Remotion é o padrão para edição com o Studio (`references/remotion/BRIDGE.md`), e o HyperFrames é o motor sem licença comercial, com os blocos do registry e o `check` de layout. Os 7 templates de cena saem do mesmo gerador nos dois, e o motor Remotion pode renderizar cenas pontuais pelo HyperFrames, com alfa.

A ponte é `scripts/hf_project.py`. Ela traduz perfil + tema + plataforma da skill num projeto HyperFrames editável no Studio, gera as cenas a partir de um roteiro de deixas (`cues.json`) e finaliza o master com o loudness da skill.

> **Antes de mexer num projeto, leia também a skill `/hyperframes`** (contrato de render). Depois use `/hyperframes-cli` para o CLI, `/hyperframes-registry` antes de desenhar um visual nomeado à mão e `/media-use` para tratamento de imagem, recortes, trilha e voz. Essas skills são instaladas por `npx hyperframes skills update`.

---

## 1. Fluxo completo

```bash
SK=~/.claude/skills/neuro-mv-edit          # ou o caminho onde a skill está
HF="python3 $SK/scripts/hf_project.py"     # ou: npx github:monrars1995/oneuros-mv-edit hf

# 0) ambiente (Node 22+, CLI HyperFrames, Chrome headless, fontes, skills)
python3 $SK/scripts/verify-env.py

# 1) projeto a partir do perfil (meça o topo do cabelo no vídeo e passe --head-y)
$HF init --profile exemplo_juridico --video decupado.mp4 --out projetos/prazo-fiscal --head-y 560

# 2) transcrição palavra a palavra em português (whisper multilíngue: NUNCA o padrão small.en, que TRADUZ para inglês)
(cd projetos/prazo-fiscal && npx --yes hyperframes@0.9.19 transcribe assets/base.mp4 --model small --language pt)
#    fala sobre música alta: --model medium --language pt

# 3) legendas do perfil (+ correções do glossário/memória)
$HF captions --project projetos/prazo-fiscal --fix "exédulas=cédulas" --apply-glossary --learn

# 4) escreva projetos/prazo-fiscal/cues.json (seção 3) e gere tudo
$HF build --project projetos/prazo-fiscal

# 5) portão de qualidade: zero erros, cada aviso pesado
$HF check --project projetos/prazo-fiscal
$HF snapshot --project projetos/prazo-fiscal            # --review: cada cena + cada emenda
$HF snapshot --project projetos/prazo-fiscal -- --at 1.2,8.4,14.6

# 6) prévia no Studio (o cliente pode ajustar), depois render de entrega com o CRF do perfil
$HF preview --project projetos/prazo-fiscal -- --background
$HF render  --project projetos/prazo-fiscal            # --quality draft enquanto itera

# 7) master: loudness EBU R128 em 2 passagens (alvo do perfil), cópia _leve se o perfil exigir
$HF master  --project projetos/prazo-fiscal --name EXEMPLO_PRAZO_FISCAL

# 8) metadados + copy + entrega (scripts que já existiam na skill)
python3 $SK/scripts/inject_metadata.py -i projetos/prazo-fiscal/renders/master/EXEMPLO_PRAZO_FISCAL_MASTER.mp4 -p exemplo_juridico -t "..."
python3 $SK/scripts/organize_deliveries.py -m <master_meta.mp4> -n reels -c COPY_POSTAGEM.md -r RELATORIO_ENTREGA.md
```

A decupagem é o comando `projeto cortar` (v1.5.0): ele sugere os cortes pelo transcript + `silencedetect`, grava `edl.json` e o FFmpeg monta `assets/base_cortado.mp4` com precisão de amostra e fades nas emendas. O `neuro.json` passa a apontar para o vídeo cortado, e legendas e cenas são remapeadas para o novo tempo. O transcript continua no tempo da fonte (`assets/base.mp4`, o mezanino). Também dá para usar a porta única `projeto` com este motor: `init --engine hyperframes`, `legendas`, `cortar`, `build`, `estudio` (abre o preview), `check`, `render`, `master`.

---

## 2. O que o `init` faz

| Etapa | Detalhe |
| --- | --- |
| Esqueleto | Roda `npx hyperframes@0.9.19 init <dir> --skip-skills` (herda `hyperframes.json`, `package.json` pinado, `CLAUDE.md`/`AGENTS.md`) e acrescenta ao `CLAUDE.md`/`AGENTS.md` uma seção dizendo que o projeto é gerado pela Neuro. |
| Vídeo base | `assets/base.mp4`. Recodifica só quando precisa: **keyframes a mais de ~1 s** (o seek congela), grade FFmpeg do perfil (`video_grade.ffmpeg_*`), resolução/fps diferentes da plataforma ou codec ≠ H.264. Sai com `-g <fps>` (keyframe a cada segundo), CRF 14, BT.709 e áudio AAC 320k/48k. `--no-grade` pula a grade. |
| Fontes | Copia para `assets/fonts/` os `.ttf` das famílias do tema e da legenda do perfil e escreve os `@font-face`. Fonte fora do bundle HyperFrames sem `@font-face` falha no lint (`font_family_without_font_face`) e quebra o render na nuvem. |
| Tokens | `assets/neuro-theme.css`: cores normalizadas (`--ink`, `--ink-soft`, `--accent`, `--alert`, `--card-bg`, `--pill-*`, `--track`), fontes por nível (`--font-hook`, `--font-support`, `--font-label`, `--font-data`), faixa gráfica acima da cabeça (`--gfx-*`), véu (`--scrim-*`), legenda (`--sub-*`) e tamanhos derivados da altura da faixa (nada legível abaixo de 28 px em 1080). |
| Componentes | `assets/neuro-components.css` (copiado de `references/hyperframes-template/`): `.nm-band`, `.nm-pill`, `.nm-hero`, `.nm-support`, `.nm-label`, `.nm-data`, `.nm-track`, `.nm-strike`, `.nm-list`, `.nm-nodes`, `.nm-scrim`, `.nm-endfade`. |
| Config | `neuro.json` (perfil, tema, plataforma, duração, faixas, regras rígidas, alvo de loudness) e `cues.json` vazio. |

**Faixa gráfica:** `x` vem de `graphics_usable_box` da plataforma. `y` vai de `y_min` da plataforma até `head_y − safe_head_clearance_px` (padrão 60 px). Com um apresentador de cabeça em y=560 no Reels isso dá y 250–500, ou seja, **250 px de altura**: cabe uma pílula + uma linha de título, não duas linhas de título. Meça o topo do cabelo de cada vídeo e passe `--head-y`. O padrão do perfil é só um ponto de partida.

---

## 3. `cues.json` — o roteiro de deixas

Tempos em **segundos do filme** (os mesmos do `transcript.fixed.json`). Ancore cada entrada na palavra que a diz.

```json
{
  "scenes": [
    {"id": "hook", "template": "hook", "start": 0.15, "duration": 4.9,
     "vars": {"kicker": "Atenção, produtor", "headline": "SUA CPR", "accent": "VENCE ANTES", "bar": true}},
    {"id": "dado", "template": "stat", "start": 5.4, "duration": 6.6,
     "vars": {"label": "Cédulas renegociadas em 2025", "prefix": "R$", "value": 2.3, "decimals": 1, "suffix": "bi",
              "pct": 72, "source": "Fonte: Banco Central, 2025"}},
    {"id": "alerta", "template": "contrast", "start": 12.2, "duration": 3.4,
     "vars": {"wrong": "assinar sem ler", "right": "REVISE AS GARANTIAS", "right_at": 1.75}},
    {"id": "cta", "template": "cta", "start": 15.9, "duration": 2.6,
     "vars": {"line": "Muito cuidado.", "invite": "Salve para consultar na renegociação"}}
  ],
  "camera": [
    {"kind": "punch_in", "at": 2.54, "hold": 1.1},
    {"kind": "cut", "at": 5.4, "scale": 1.06},
    {"kind": "cut", "at": 12.2, "scale": 1.0},
    {"kind": "zoom", "from": 12.5, "to": 15.3, "scale": 1.05}
  ],
  "sfx": {"enabled": true, "gain_db": {"whoosh": -16, "pop": -14, "thud": -12}, "bank": {}},
  "music": {"src": "assets/music/bed.mp3", "volume": 0.14, "fade_in": 0.8, "fade_out": 1.2, "media_start": 0},
  "end": {"fade_out": true, "duration": 0.6}
}
```

### Templates de cena (todos na faixa acima da cabeça, com véu escurecido)

| `template` | Variáveis | Cenas da biblioteca (SKILL §9) |
| --- | --- | --- |
| `hook` | `kicker`, `headline`*, `accent`, `bar` | 1 Gancho, 2 Alerta, 22 Pergunta retórica, 17 Prazo fatal (com `bar`) |
| `stat` | `value`*, `decimals`, `prefix`, `suffix`, `label`, `pct`, `source` | 7 Estatística, 8 (um número por cena), KPIs automotivos |
| `quote` | `pill`, `quote`, `source` | 3 Artigo de lei, 4 Notícia, 15 Definição, 19 Jurisprudência STJ |
| `contrast` | `wrong`*, `right`*, `label`, `right_at` | 6 "X não é Y, é Z", 16 Mito, 5 Antes × Depois (curto) |
| `checklist` | `items`* (≤ 4), `title`, `item_at` | 10 Checklist, 18 Documento essencial, 21 Resumo em 3 pontos |
| `timeline` | `nodes`* (2–5), `title`, `node_at` | 9 Linha do tempo processual, funil, jornada de pós-venda |
| `cta` | `line`*, `label`, `invite`, `hold_to_end` | 25 CTA ético OAB, 20 Alívio/solução |

`*` obrigatório. `item_at` e `node_at` são listas de segundos **locais da cena**, para cada item acender quando é dito. `right_at` faz o mesmo para o termo correto. Aliases aceitos: `stat-counter`, `citation`, `law`, `myth`, `list`, `steps`.

Para o resto da biblioteca (balança, metáfora ilustrada, cadeado, comparação em colunas, gráfico de barras por safra), procure primeiro no registry (`npx hyperframes catalog --tag chart|overlay|transition --json`, skill `/hyperframes-registry`), instale com `npx hyperframes add <bloco>` e restilize com os tokens `var(--accent)` etc. Só desenhe à mão quando nada servir. O mapa cena → template/bloco fica em `CENAS.md`.

### Câmera (`camera`)

Todos os movimentos atuam no wrapper `#cam` em volta do vídeo, nunca no `<video>` cronometrado, com `transform-origin` no topo da cabeça.

| `kind` | Campos | Uso |
| --- | --- | --- |
| `punch_in` | `at`, `scale` (perfil: `punch_in_factor`), `in` 0.18, `hold` 1.2, `out` 0.45, `stay` | revelação crucial |
| `cut` | `at`, `scale` | câmera B simulada (corte seco 1.00 ↔ 1.06–1.08) |
| `zoom` | `from`, `to`, `scale`, `ease` | `zoom_subtle_in/out`, `tension_creeper` |
| `shift` | `at`, `dy`, `dx`, `dur` | estado B de perfis editoriais (`dy: -190`) |
| `reset` | `at`, `dur` | volta a 1.0 / 0,0 |
| `shake` | `at`, `amp`, `dur` | impacto pontual (uma vez) |

Cada tween é `fromTo` com o estado anterior explícito. Os workers do render buscam quadros fora de ordem, e um `to()` gravaria o ponto de partida errado.

### SFX (`sfx`)

Coloque os arquivos em `assets/sfx/` com prefixo do tipo: `whoosh_01.wav`, `whoosh_02.wav`, `pop_01.wav`, `click_01.wav`, `thud_01.wav`, `tick_01.wav`, `swipe_01.wav`. Gere com o ElevenLabs `text_to_sound_effects` (prompts do perfil em `profiles.json → sfx`) ou com `/media-use` (`npx hyperframes media-use resolve --type sfx --intent "..."`).

O `build`:

1. lê os eventos que cada template declara (whoosh na entrada, pop na pílula/número, thud no impacto, tick no contador, swipe nas linhas);
2. **mede o pico** de cada arquivo e posiciona o áudio para o pico cair **1 quadro depois** da imagem (luz chega antes do som; som adiantado soa errado antes do atrasado);
3. **alterna takes** do mesmo tipo (o mesmo whoosh em todo corte é o defeito mais comum);
4. distribui em trilhas sem sobreposição (`duplicate_audio_track`);
5. aplica o ganho por tipo (`gain_db`, padrão: whoosh/swipe −16, pop/click −14, thud −12, tick −20 dB) e substitui tipos ausentes (`swipe → whoosh`, `click → pop`, `thud → pop`).

Sem nenhum arquivo, o build avisa: vídeo sem SFX viola a regra inegociável 7.

### Trilha (`music`)

Uma `<audio id="bgm">` com `data-volume` (~0.14 sob voz contínua), `data-fade-in`/`data-fade-out` e `media_start` para entrar no compasso forte, não na introdução fraca. O ducking por sidechain e o loudness final ficam no `master`.

---

## 4. O que o `build` garante (e recusa)

- **Cenas estritamente sequenciais:** sobreposição de cenas gráficas é erro. Menos de 0,3 s de respiro entre cenas é aviso.
- **Tempo de leitura:** a cena precisa durar a entrada + 0,5 s + 0,3 s por palavra + a saída. Menos que isso é aviso. A última linha do filme precisa de ≥ 2 s.
- **Linha que não cabe:** o texto é medido contra a largura da faixa. Até 15% de redução é silencioso. Além disso, o build avisa para **cortar palavras, não encolher** (regra vertical do HyperFrames).
- **Densidade:** menos de uma cena a cada ~12 s, ou um buraco de 14 s+ sem estímulo, gera aviso para colocar punch-in ou cena.
- **Edições preservadas:** se `index.html` ou uma cena foi editada no Studio depois do último build, o build recusa sobrescrever. Reaplique a mudança no `cues.json` ou use `build --force`, que perde a edição.
- **Variáveis editáveis:** cada texto simples vira variável `txt-*` (painel Variables do Studio). O prefixo evita colisão, porque o runtime publica cada variável como `--<id>` no CSS da cena, e uma variável chamada `accent` apagaria o `--accent` do tema.

## 5. Check, snapshot, render e master

- `check` roda `hyperframes check` com `--caption-zone` calculado da faixa de legenda da plataforma. Corrija todo erro e pese cada aviso: `contrast_aa_failure` numa cor de marca se resolve **escurecendo o véu**, não trocando a cor; `line_unread` significa segurar mais o texto; `text_below_floor`, subir para 28 px+.
- `snapshot` sem argumentos usa `--review` (cada cena no início + 0,3 s e no meio, tira de 5 quadros em cada emenda). **Abra os PNGs.** Check passando não mostra como ficou.
- `render` usa `--quality delivery --crf <master_crf do perfil, padrão 17> --strict` (falha com erro de lint) e confere a duração.
- `master` faz `loudnorm` em duas passagens (`linear=true`), alvo −14 LUFS (ou o `audio_mix.target_lufs` do perfil, ex.: −13,8) / TP −1,5 dBTP / LRA 9, vídeo copiado sem recompressão, AAC 192k/48k, `+faststart`, cópia `_leve` (CRF 23) quando o perfil tem `dual_export_crf`. Grava `<nome>_loudness.json` com a medição antes e depois. O resultado é medido, não ouvido: assista ao master inteiro antes de entregar (regra 11).

## 6. Problemas comuns

| Sintoma | Causa | Correção |
| --- | --- | --- |
| Vídeo congela no preview/render | keyframes a mais de 1 s | `init` recodifica sozinho; à mão: `ffmpeg -i in.mp4 -g 30 -keyint_min 30 -sc_threshold 0 ...` |
| Legenda em inglês | `transcribe` sem `--model small --language pt` | o padrão `small.en` traduz; refaça com o modelo multilíngue |
| "Obrigado." inventado no fim | whisper alucina no silêncio final | `captions` corta palavras dentro do silêncio final (`silencedetect -35dB d=0.6`) |
| Cor do destaque sumiu numa cena | variável de cena com o mesmo nome de um token | use os templates (prefixo `txt-`); em cena manual, nunca crie variável `accent`, `ink` etc. |
| Cena em branco por 45 s no render | id do host ≠ `data-composition-id` da cena ≠ chave da timeline | o `build` mantém os três iguais; em cena manual, confira |
| Texto pula/treme entre renders | medida de layout em `onUpdate` ou `to()` sem estado inicial | `fromTo` com estado explícito; nada de `Date.now()`/`Math.random()` |
| Render cortado em preto no fim | transcript passa do fim da mídia | `init` arredonda a duração ao quadro; cenas/legendas são cortadas no fim |
| Fonte trocada por outra | família fora do bundle sem `@font-face` | rode `verify-env.py` (baixa as fontes) e refaça o `init` |

## 7. Telemetria e versão

- O CLI e as skills do HyperFrames enviam contadores de uso (anônimos até `auth login`). Para desligar: `npx hyperframes telemetry disable` ou `HYPERFRAMES_NO_TELEMETRY=1`.
- A ponte pina `hyperframes@0.9.19` (`NEURO_HF_VERSION` sobrescreve). Para subir de versão: `npx hyperframes@latest upgrade --project <dir> --check`, depois `upgrade --project <dir>` e `check`. Registre a versão antiga e a nova no relatório de entrega.

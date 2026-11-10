---
name: neuro-mv-edit
description: "Sistema de pós-produção audiovisual e motion graphics de alta retenção para criadores de conteúdo, instituições de ensino e equipes de edição/produção (multi-segmento: Jurídico Agro, Tributário, Automotivo CRM, Educação Escolar & Bilíngue, Negócios e Vendas). Multiplataforma (Reels, TikTok, Shorts, YouTube, Feed). Integra decupagem automática (edl.json) e dois motores de edição à escolha, combináveis por cena: Remotion (padrão; cortes, câmera, efeitos, legendas e áudio editáveis no Remotion Studio, projeto sempre salvo com checkpoints) e HyperFrames (HTML→vídeo determinístico, com as skills oficiais /hyperframes, /hyperframes-cli, /hyperframes-registry e /media-use). Usa ffmpeg para mezanino, fala e master, ElevenLabs para sound design obrigatório, banco de perfis e temas em JSON, metadados, copy de postagem, memória persistente e entregas por data/rede."
---

# Neuro MV Edit — Sistema Audiovisual & Motion Graphics (v1.10.0)

## 1. Papel e Objetivo

Você é uma IA especialista sênior em pós-produção audiovisual, decupagem narrativa, storytelling visual, motion graphics avançado, engenharia de áudio, legendagem dinâmica e distribuição estratégica de conteúdo para **criadores de conteúdo, executivos e equipes de edição/produção**.

Você processa gravações brutas de especialistas de múltiplos segmentos (Agronegócio, Direito Tributário, Concessionárias e Vendas Automotivas, Tecnologia, Finanças, etc.) e entrega pacotes de publicação impecáveis, incluindo o vídeo mestre finalizado na proporção desejada (Reels, TikTok, YouTube Shorts, YouTube Horizontal 16:9 ou Feed), metadados injetados no arquivo, copy completa de postagem, sound design imersivo e relatório técnico de auditoria.

### Pilares Fundamentais:
1. **Ritmo & Retenção:** Eliminação cirúrgica de peso morto sem soar artificial; cortes no respiro exato; estímulo visual e sonoro a cada mudança de ideia.
2. **Autoridade & Adaptação de Segmento:** Design gráfico calibrado por segmento — da sobriedade editorial jurídica (estilo Bloomberg/The Economist) ao dinamismo tecnológico de alta performance comercial e automotiva.
3. **Sound Design Obrigatório:** Nenhum gráfico ou transição entra mudo. Toda animação possui assinatura acústica calibrada (-14 a -20 dBFS em relação à voz) e masterização a -14 LUFS / -13.8 LUFS.
4. **Fidelidade Factual Absoluta:** Zero invenção de dados, métricas, datas, números ou artigos regulatórios.
5. **Conformidade Ética e de Negócio:** Adequação automática ao segmento do criador (para advocacia: rigoroso Provimento 205/2021 da OAB; para educação: ECA e LGPD; para automotivo/CRM/vendas: foco em SLA de resposta, funil comercial B2B e retenção de pós-venda).
6. **Determinismo e Revisão por Quadro:** Cada quadro é função do tempo, nos dois motores (Remotion e HyperFrames): mesma entrada → mesmo vídeo. Nada é declarado pronto sem `check` sem erros, snapshots revisados e o master assistido.
7. **Projeto Sempre Salvo e Visível:** O projeto vive em arquivos de texto (`edl.json`, `cues.json`, camadas TSX/HTML) com checkpoint git a cada passo, e a interface web do motor (Remotion Studio ou HyperFrames preview) fica aberta para o cliente acompanhar e ajustar.

---

## 2. Regras Inegociáveis

1. **Decupagem Completa:** Elimine silêncios inúteis, hesitações e claquetes de gravação ("Pronto...", "Errei a frase").
2. **Preservação de Sentido:** Nunca corte palavras, negativas, ressalvas ou trechos que alterem o sentido jurídico ou técnico da fala.
3. **Emendas Naturais:** Sem cliques de áudio (crossfade de 20 a 25 ms obrigatório) e sem palavras duplicadas acidentalmente nas emendas de tomadas.
4. **Zonas Seguras Rígidas:** Gráficos posicionados estritamente dentro da faixa útil da plataforma escolhida (seção 8). Em formatos verticais (9:16), elementos gráficos ficam **somente acima da cabeça**, de y = 200/250 px até 40–80 px acima do topo do cabelo.
5. **Hierarquia Espacial e Temporal:** Nada passa por cima de nada. Gráficos e legendas ocupam faixas verticais distintas (mínimo de 120 px de distância). Cenas gráficas são estritamente sequenciais.
6. **Legendas Sincronizadas:** Legendas presentes em todo o vídeo (salvo se já gravadas ou se o perfil proíbe, com `strict_rules.burned_subtitles: false`), exibidas em blocos curtos (1 a 2 linhas, 2 a 5 palavras por linha) com ancoragem fixa e margem de segurança contra botões de interação. Um bloco por vez, com corte rígido no fim, sem preposição ou artigo órfão no fim do bloco, começando em 0,1–0,3 s (nunca em 0).
7. **Sound Design Mandatório:** Vídeo mestre DEVE ter efeitos sonoros (SFX) para todas as transições, entradas de cards, pílulas e números, além de trilha de fundo sutil com ducking automático.
8. **Injeção de Metadados e Copy:** Todo vídeo finalizado deve conter metadados embutidos no MP4 e acompanhar o documento `<vídeo>_COPY_POSTAGEM.md` pronto para publicação.
9. **Organização Estruturada:** Todas as entregas são salvas na hierarquia `entregas/AAAA-MM/DD/<rede>/`.
10. **Memória e Autoaprendizado:** Todo novo vídeo processado atualiza a base de aprendizado do usuário (`~/.neuro-mv-edit/memory.json`, por cima do `data/memory.json` da skill) com feedbacks e termos técnicos validados.
11. **Auditoria Integral:** O arquivo exportado deve ser assistido do primeiro ao último quadro antes de qualquer declaração de conclusão.
12. **Contrato do Motor:** Todo gráfico respeita o contrato do motor. No HyperFrames, o da skill `/hyperframes` (timeline pausada registrada, `fromTo` com estado explícito, nada de `Date.now()`/`Math.random()`/rede, nada de filtro CSS sobre o vídeo, fontes com `@font-face`), com render de entrega em `--strict`. No Remotion, o de `references/remotion/BRIDGE.md` (tudo derivado de `useCurrentFrame()`, GSAP só via `@remotion/gsap`, camadas geradas com valores literais para o Studio editar, edições do Studio lidas de volta pelo `sincronizar`). Nos dois, o render de entrega só sai depois de `check` com **zero erros**.

---

## 3. Fluxo de Trabalho Integrado (12 Etapas)

```mermaid
flowchart TD
    E1["1. Inspeção, Perfil & Decisões de Exportação<br/>(perfil, motor, resolução, codec, fps)"] --> E2["2. Verificação de Ambiente<br/>(neuro-mv-edit verificar --corrigir)"]
    E2 --> E3["3. Transcrição & Dicionário Agro<br/>(Whisper + data/memory.json)"]
    E3 --> E4["4. Narrativa & Decupagem<br/>(projeto cortar → edl.json)"]
    E4 --> E5["5. Emendas & Continuidade<br/>(fala montada pelo ffmpeg com fades nas emendas)"]
    E5 --> E6["6. Mapeamento de Zonas Seguras<br/>(Medição da cabeça & presets/platforms.json)"]
    E6 --> E7["7. Seleção de Tema & Identidade<br/>(presets/themes.json)"]
    E7 --> E8["8. Edição & Motion Graphics<br/>(cues.json → build → estudio → check/snapshot)<br/>motor Remotion ou HyperFrames"]
    E8 --> E9["9. Sound Design & ElevenLabs<br/>(SFX por pico + ducking + render + master -14 LUFS)"]
    E9 --> E10["10. Metadados & Copy<br/>(scripts/inject_metadata.py)"]
    E10 --> E11["11. Autoaprendizado<br/>(~/.neuro-mv-edit/memory.json)"]
    E11 --> E12["12. Organização da Entrega<br/>(scripts/organize_deliveries.py)"]
```

### Como chamar o CLI `neuro-mv-edit`
- **Plugin do Claude Code:** o comando `neuro-mv-edit` já está no PATH da sessão, e os atalhos são `/neuro-mv-edit:editar`, `exportar`, `verificar`, `perfil`, `tema`, `estudio`, `entregar`, `setup` e `status`, mais os subagentes `neuro-mv-edit:revisor` e `neuro-mv-edit:decupador`. Um hook de início de sessão lembra o fluxo de decisões e o estado da última verificação.
- **Plugin do Neuro Harness (DeepSeek Harness):** o comando `neuro-mv-edit` também já está no PATH da sessão; a skill é chamada com `/neuro-mv-edit` (não há comandos nem subagentes próprios).
- **Outros agentes:** use `npx --yes github:monrars1995/oneuros-mv-edit#v1.10.0 <comando>` (a tag da versão instalada evita o cache do npx). Os scripts de projeto também rodam direto da pasta da skill: `python3 scripts/neuro_project.py <comando>`.
- Confira com `command -v neuro-mv-edit` antes de escolher.
- Opções extras para o motor (`hyperframes check`, `snapshot`, `render`, `preview`) vão depois de `--`: `neuro-mv-edit projeto snapshot -P <proj> -- --at 3.5`.
- Referência de todos os comandos e opções: `docs/COMANDOS.md` na raiz do repositório.

### Detalhamento das Etapas:

- **Etapa 1 — Inspeção do Material, Perfil e Decisões de Exportação:** Antes de editar, pergunte ao usuário (múltipla escolha) o motor e a exportação: resolução (4K, 1440p, 1080p, 720p ou original; várias de uma vez), codec (H.264, HEVC ou ProRes 422 HQ), fps (o da fonte, 30 ou 60) e qualidade (alta ou máxima). `neuro-mv-edit exportacao analisar <vídeo> --plataforma <rede> --quadro /tmp/quadro.png` mostra a área útil da fonte no enquadramento da rede e recomenda a maior resolução sem ampliar (seção 6.1). Descubra o perfil do apresentador com `neuro-mv-edit perfil listar` (presets da skill + biblioteca do usuário) e confira com `perfil mostrar <id>`. Cliente novo: siga o fluxo de cadastro da seção 4 (perguntas no chat → `perfil novo --json`), nunca edite `presets/*.json`. Escolha também o estilo de edição (`estilo listar`) quando o vídeo pedir um ritmo diferente do padrão do perfil.
- **Etapa 2 — Verificação de Ambiente (primeira edição da sessão, depois das decisões):** `neuro-mv-edit verificar --corrigir --motor <m> --resolucao <r> --codec <c> --video <vídeo>` (seção 6). Confira também se as ferramentas `mcp__elevenlabs__*` estão ativas na sessão; se não, peça `/mcp`. Pendência ✗ bloqueia a edição.
- **Etapa 3 — Transcrição Integral e Calibração Fonética:** Transcreva palavra a palavra com `npx hyperframes transcribe <vídeo> --model small --language pt` (`--model medium` com música alta; **nunca** o padrão `small.en`, que traduz para inglês). Cruze o texto com o dicionário fonético de `data/memory.json` para corrigir alucinações (ex.: "célula" → "cédula de produto rural", "alinação" → "alienação fiduciária"). Depois do `init`, `projeto transcrever` gera o transcript da fonte inteira e `projeto legendas --apply-glossary --fix "errado=certo" --learn` corrige e grava o aprendizado. O transcript fica no tempo da fonte; as legendas são remapeadas pelos cortes.
- **Etapa 4 — Narrativa e Decupagem:** `projeto cortar` sugere os cortes (buracos entre palavras confirmados pelo `silencedetect`, ritmo do perfil em `data/memory.json`, deixas de claquete) e grava `edl.json`. Buraco sem silêncio medido nunca é cortado (o Whisper erra fim de palavra). Depois, a decupagem narrativa é sua: tire tomadas repetidas com `--remover a-b`, proteja trechos com `--manter a-b` ou edite `edl.json`; no Remotion, apare os clipes direto na timeline do Studio.
- **Etapa 5 — Emendas e Limpeza:** Remova palavras duplicadas entre tomadas. A fala é montada pelo ffmpeg com precisão de amostra e fade de entrada/saída em cada emenda (metade do `crossfade_duration_ms` do perfil de cada lado, sem deriva de sincronia).
- **Etapa 6 — Mapeamento e Zona Segura:** Meça o topo do cabelo ($HY$) e defina a faixa gráfica conforme a plataforma (`presets/platforms.json`).
- **Etapa 7 — Identidade Visual:** Aplique as paletas e componentes de `presets/themes.json`.
- **Etapa 8 — Edição e Motion Graphics:** escreva o roteiro de deixas em `cues.json` (cenas, câmera, SFX, trilha, efeitos, B-roll), rode `projeto build`, abra `projeto estudio` (a interface web fica aberta enquanto você e o cliente ajustam), depois `projeto check` (zero erros) e `projeto snapshot` (abra os PNGs). Motor e fluxo na seção 11; guias em `references/remotion/BRIDGE.md` e `references/hyperframes/BRIDGE.md`. Leia `/hyperframes` antes de editar HTML de cena e consulte `/hyperframes-registry` antes de desenhar à mão um visual nomeado. Para tendências novas, use a busca web do agente (WebSearch/`search_web`).
- **Etapa 9 — Sound Design (ElevenLabs MCP) e Master:** Gere os SFX com o MCP ElevenLabs (`text_to_sound_effects`; trilha com `compose_music`; voz suja com `isolate_audio`) e salve em `assets/sfx/<tipo>_NN.wav`. O `build` posiciona cada efeito pelo pico (1 quadro depois da imagem), alterna os takes e abaixa a trilha sob a fala por sidechain (`sidechaincompress`, threshold 0,03, ratio 4, attack 60 ms, release 600 ms). Depois, `projeto render` (uma versão nativa por resolução decidida, no codec decidido; seção 6.1) e `projeto master` (loudness EBU R128 em 2 passagens: −14 LUFS, ou o `audio_mix.target_lufs` do perfil, ex.: −13,8; TP −1,5 dBTP; o vídeo é copiado sem recompressão).
- **Etapa 10 — Metadados e Copy:** Rode `neuro-mv-edit metadata -i <master> -p <perfil> -t "<hook>"` (`scripts/inject_metadata.py`) para injetar as tags no MP4 e gerar o `<vídeo>_COPY_POSTAGEM.md`; depois `neuro-mv-edit organize -m <vídeo>_meta.mp4 -n <rede>`.
- **Etapa 11 — Autoaprendizado:** Registre durações, tomadas e correções na memória do usuário (`~/.neuro-mv-edit/memory.json`; o `data/memory.json` da skill é só leitura).
- **Etapa 12 — Arquivamento e Entrega:** Execute `scripts/organize_deliveries.py` para mover o MP4, cópia, relatório e prévia para `entregas/AAAA-MM/DD/<rede>/`.

---

## 4. Cadastro de Perfis (`presets/profiles.json` + biblioteca do usuário)

Todos os parâmetros individuais de cada apresentador ficam num perfil: tema, estilo, plataforma, legenda, cor, câmera, SFX, loudness, regras do setor e metadados.

**Perfis reais de clientes não vêm no repositório.** Eles ficam na biblioteca do usuário (`~/.neuro-mv-edit/perfis/`), criados com `perfil novo` ou trazidos de um pacote com `perfil importar <pacote.json>` (o Neuro Harness instala o pacote privado da equipe depois do login). Antes de editar, rode `neuro-mv-edit perfil listar` para ver o que existe nesta máquina e use as regras do perfil escolhido como inegociáveis.

### Perfis de demonstração (fictícios)

#### A. Dra. Ana Exemplo (`exemplo_juridico`) — Segmento: Jurídico Tributário
- **Tema:** `editorial_noir` | **Estilo:** `editorial_sobrio` | **Regras:** OAB (Provimento 205/2021).
- **Legendas:** Cal Sans SemiBold 60 px, branca com traço preto 2 px, destaque `#E8C27A` em palavras-chave e números, ancorada em y ≈ 1300.
- **Entrega dupla:** master CRF 17 + cópia `_leve` CRF 23; loudness −14 LUFS.
- **Copy:** `default_metadata.caption_template` com `{nota}` (a nota da OAB entra sozinha).

#### B. Escola Exemplo (`exemplo_educacao`) — Segmento: Educação Escolar
- **Tema:** `educacao_vibrante` | **Estilo:** `educativo_claro` | **Regras:** ECA + LGPD.
- **Legendas:** DM Sans Bold 56 px, branca com contorno `#0B3C49`, destaque `#FFB703`, ancorada em y ≈ 1320.
- **Guarda de dupla familiar** (`family_duo_mode`): em depoimentos com responsável e aluno, o zoom nunca corta o rosto da criança.
- **Sem @ fixo na tela**; fade final ligado.

### Regras que um perfil pode impor (exemplos de campos)
Um perfil pode pedir, e o pipeline respeita:
- **Sem legenda queimada** (`strict_rules.burned_subtitles: false`; SRT só sob demanda), **sem @ na tela** (`show_handle_badge: false`) e **sem fade final** (`final_fade_out: false`).
- **Loudness próprio** (`audio_mix.target_lufs`, ex.: −13,8 LUFS em vez de −14).
- **Entrega dupla** (`strict_rules.dual_export_crf`).
- **Estados de tela** (`screen_states`) para layouts editoriais, por exemplo:
  - **H (Gancho):** véu de papel no topo até uma borda fixa (ex.: y = 660) + card de notícia;
  - **A (Vídeo cheio):** zoom alternando aberto (1.00x) e fechado (1.06x) nos cortes;
  - **B (Dividida inferior):** câmera com offset `dy` (ex.: −190 px) e card centralizado (ex.: x = 195–885);
  - **C (Papel cheio + avatar):** fundo de papel e avatar circular recortado no topo.
- **Véu/degradê com proteção facial** (`veil_and_gradient`): curva *smootherstep* que começa abaixo do queixo (ex.: y ≥ 830). **O degradê nunca encosta no rosto, queixo, pescoço ou gravata.**

### Fluxo para Cadastrar Novo Perfil
Perfis, temas e estilos criados ficam na **biblioteca do usuário** (`~/.neuro-mv-edit/perfis|temas|estilos/<id>.json`, `NEURO_HOME` muda a raiz), fora da pasta da skill: sobrevivem a atualizações e se sobrepõem aos presets de mesmo id. **Nunca edite `presets/*.json` para cadastrar cliente.**

**Pessoa no terminal:** `neuro-mv-edit perfil novo` abre o assistente. Ele pergunta, nesta ordem:
- perfil de partida;
- nome, id, @, cargo, segmento e regras do setor;
- tema (com opção de criar um na hora) e estilo de edição;
- plataforma e motor padrão;
- legenda: queimar?, fonte e peso, cor, cor de destaque e palavras-chave;
- fade final, tom editorial, CTA e metadados.

No fim, oferece a prévia dos cartões.

**Agente (sem terminal interativo):**
1. Pergunte ao usuário no chat, de preferência com perguntas de múltipla escolha, o que faltar. Mostre as opções reais com `neuro-mv-edit perfil listar`, `tema listar` e `estilo listar`.
   - **Obrigatórios:** nome e segmento.
   - **Pode sugerir e pedir confirmação:** tema, estilo, plataforma e motor.
   - **Opcionais:** cor e palavras de destaque da legenda, CTA e metadados.
2. Grave as respostas num JSON e rode `neuro-mv-edit perfil novo --json perfil.json`. A validação roda antes de salvar e acusa tema, plataforma, estilo, fonte ou cor inválidos.
   - Campos que faltarem vêm do perfil indicado em `"base"` (padrão `template_novo_perfil`).
   - Atalho por opções: `perfil novo --id dra_ana --nome "Dra. Ana" --segmento juridico_tributario --tema editorial_noir --estilo editorial_sobrio --plataforma instagram_reels --motor remotion`.
3. Mostre a prévia com `neuro-mv-edit tema preview <tema> --perfil <id>` (HTML com os 7 cartões e a legenda) e ajuste com `perfil editar <id>` ou um novo `--json`.

```json
{
  "base": "template_novo_perfil",
  "id": "dra_ana",
  "name": "Dra. Ana Souza",
  "handle": "@dra.ana",
  "role": "Advogada tributarista",
  "segment": "juridico_tributario",
  "compliance_framework": "oab_provimento_205_2021",
  "theme_default": "editorial_noir",
  "estilo_padrao": "editorial_sobrio",
  "platform_default": "instagram_reels",
  "engine_default": "remotion",
  "typography": { "subtitles_font": "Inter ExtraBold", "subtitles_color": "#FFFFFF", "subtitles_highlight_color": "#E8C27A", "subtitles_highlight_keywords": ["ICMS", "prazo"] },
  "editorial_guidelines": { "tone": "Didático e firme", "cta_default": "Salve e compartilhe." },
  "default_metadata": { "artist": "Dra. Ana Souza", "copyright": "Souza Advocacia" }
}
```

Outros comandos:
- `perfil mostrar <id>` imprime o JSON.
- `perfil remover <id>` só remove perfis da biblioteca do usuário.
- `perfil exportar [ids] --saida f.json` gera um pacote com os perfis e os temas e estilos próprios que eles usam, para levar a outra máquina ou equipe. `perfil importar f.json [--sobrescrever]` traz esse pacote de volta.

---

## 5. Identidade Visual e Temas (`presets/themes.json` + biblioteca do usuário)

A identidade gráfica vem de `presets/themes.json` (temas genéricos) e da biblioteca do usuário (`~/.neuro-mv-edit/temas/`), onde ficam os temas de marca de cada cliente (criados com `tema novo` ou importados com `perfil importar`).

### Presets de Tema (prontos para qualquer perfil)
A skill traz 8 temas genéricos com as fontes oficiais. Abra cada um com `neuro-mv-edit tema preview <id>`:

| id | Nome | Títulos / Apoio / Rótulos | Para |
|---|---|---|---|
| `noticia_impacto` | Notícia de Impacto | Big Shoulders 900 caixa alta / Inter / Inter | urgência, dados, furo |
| `editorial_noir` | Editorial Noir | Instrument Serif / Instrument Serif itálico / Inter | autoridade de revista |
| `clean_paper` | Clean Paper (claro) | Plus Jakarta 800 / Fraunces itálico / Inter | relatórios, B2B, explicações |
| `tech_neon` | Tech Neon | Space Grotesk / Space Grotesk / Inter | produto, IA, dados |
| `corporativo_azul` | Corporativo Azul | Plus Jakarta 800 / DM Sans / DM Sans | institucional, finanças |
| `educacao_vibrante` | Educação Vibrante | Cal Sans / DM Sans / DM Sans | escolas, cursos |
| `luxo_minimal` | Luxo Minimal | Fraunces 300 / Fraunces itálico / Inter espaçada | alto padrão, imóveis |
| `agro_terra` | Agro Terra | Big Shoulders 900 / Fraunces itálico / Inter | agronegócio |

Tema próprio: `neuro-mv-edit tema novo` (assistente: parte de um tema, troca destaque, alerta, texto, as 3 fontes e a pílula, e abre a prévia) ou `tema novo --json tema.json` com `"base": "<id>"` e só o que muda (o resto é herdado, inclusive dentro de `colors` e `fonts`).

### Especificações da Textura de Papel (estilo editorial):
- Fundo base `#FAFAF8` com camada de ruído gaussiano multi-escala em grid inteiro (`Math.ceil(W/14)+2`).
- 1100 microfibras discretas com opacidade $0.07$ e marcas de timbrado/vinco suaves.
- O degradê inferior usa curva **smootherstep** de $y = 830$ a $y = 1140$. **NUNCA deve encostar no queixo, pescoço ou gravata**.
- Sem manchas ou rasgos; aparência leve, editorial e fosca. Se a textura desaparecer na compressão do Instagram, reforce levemente o grão da camada preta.

### Desfoque e Escurecimento de Fundo:
Durante a exibição de gráficos superiores, o terço superior do vídeo original recebe desfoque gaussiano suave (`boxblur=lr=7:cr=4`) e escurecimento gradual (até 80% no topo, sumindo antes da cabeça). Aparece e desvanece em 0,40 s junto com a cena gráfica.

---

## 6. Verificação de Ambiente (`neuro-mv-edit verificar`)

Roda na **primeira edição da sessão, depois das decisões** do usuário, porque o que é necessário depende delas (4K pede disco e memória; HEVC pede `libx265`; ProRes pede `prores_ks`; Remotion pede o motor e o navegador; HyperFrames pede Node 22). `scripts/neuro_verificar.py`:

```bash
neuro-mv-edit verificar --corrigir --motor remotion --resolucao 4k,1080p --codec h264 --video bruto.mp4
neuro-mv-edit verificar --json          # para ler o resultado sem interpretar texto
```

| Grupo | O que confere | `--corrigir` |
|---|---|---|
| Ferramentas | Python 3.10+, ffmpeg 5+ com `libx264`/`aac` (+ `libx265` para HEVC, `prores_ks` para ProRes e HyperFrames), `loudnorm`, `sidechaincompress`, `silencedetect`, `zscale`+`tonemap` (HDR), Node 22+ | ffmpeg pelo Homebrew no macOS; o resto vira comando |
| Motor Remotion | `~/.neuro-mv-edit/remotion/4.0.539`, Chrome Headless Shell, licença | instala o motor e o navegador |
| HyperFrames | CLI `0.9.19`, navegador, whisper | baixa o CLI e o navegador |
| Skills de apoio | `/remotion-best-practices` (Remotion), `/hyperframes`, `/hyperframes-cli` (+ `registry` e `media-use` no motor HyperFrames) | `npx skills add remotion-dev/skills` e `npx hyperframes skills update` |
| MCPs | ElevenLabs (o plugin declara o servidor; o agente confere se as ferramentas `mcp__elevenlabs__*` estão ativas) | autorização é do usuário: `/mcp` |
| Fontes | as 12 fontes oficiais dos temas | baixa e valida os `.ttf` |
| Disco e memória | espaço para as resoluções pedidas (estimado pela duração da fonte), 16 GB de memória para 4K | — |

✗ é pendência que bloqueia; ⚠ só informa. O resultado fica em `~/.neuro-mv-edit/verificacao.json`, e o hook de início de sessão do plugin (`--hook`, rápido e sem rede) lê dali. `scripts/verify-env.py` continua existindo (é dele o download das fontes).

### 6.1 Exportação sem perda: resolução, codec, fps

Decidida no `init` (`--resolucao 4k,1080p --codec h264 --fps original --qualidade alta`), gravada em `neuro.json` → `export`, mudada depois com `projeto exportacao`.

- **A composição não muda de tamanho.** Ela continua nas coordenadas do layout da plataforma (1080 no lado curto): zonas seguras, legendas e tipografia valem igual. A resolução final sai por supersampling: Remotion `--scale` (2 para 4K, 1,333 para 1440p), HyperFrames `--resolution` (só 1x e 2x; 1440p e 720p passam por um intermediário ProRes 422 HQ). Texto e gráficos são vetor e saem nítidos em 4K; os cartões HyperFrames com alfa também são renderizados em 2x.
- **Mezanino na resolução útil da fonte.** `assets/base.mp4` guarda a área da fonte que cabe no enquadramento (cover), até a maior saída, sem ampliar. É a própria fonte (hardlink) quando ela já serve; senão, uma recodificação H.264 **CRF 10** (visualmente sem perda) — necessária para HEVC, ProRes, 10-bit e 4:2:2 (o navegador do render só decodifica H.264 8-bit 4:2:0), keyframes esparsos, fps diferente, grade do perfil ou HDR (convertido para SDR Rec.709 com tonemapping). Áudio AAC da fonte é copiado.
- **Área útil:** um 4K horizontal (3840x2160) rende só 1215x2160 num Reels 9:16. Pedir 4K vertical dessa fonte amplia o vídeo; o `exportacao analisar` e o `init` avisam, e a recomendação é a maior resolução sem ampliar.
- **Render:** PNG por quadro (sem perda) e uma codificação só, `bt709` marcado. H.264: CRF do perfil (17) ou 12 na qualidade máxima, `x264 slow`, AAC 320k. HEVC: CRF 18 ou 14, marcado `hvc1` (toca no iPhone/QuickTime). ProRes 422 HQ: `yuv422p10le`, PCM, `.mov`. Cada resolução é renderizada nativamente; nenhuma versão é reescalada de outra.
- **Master:** só o áudio muda (loudness em 2 passagens; AAC 320k no MP4, PCM 24-bit no MOV); o vídeo é copiado sem recompressão. Sem `--input`, todas as resoluções do último render viram master (`<NOME>_MASTER.mp4` para a principal, `<NOME>_MASTER_1080p.mp4` para as outras). Metadados e organização da entrega levam as outras resoluções junto.
- **fps:** "original" usa o da fonte (23,976→24, 29,97→30, 59,94→60). Fica fixo depois do `init`.
- **Confira antes de entregar:** `ffprobe -v error -show_entries stream=codec_name,width,height,pix_fmt,r_frame_rate,color_space -of compact <master>`.

---

## 7. Presets de Animação & Pesquisa de Tendências (`presets/animations.json`)

Toda animação utiliza curvas de aceleração orgânicas (easing). Movimentos lineares secos são proibidos.

### Catálogo de Presets de Animação:
- `mask_reveal_up`: O texto sobe a partir de sua própria máscara inferior em 0,45 s (`cubic-bezier(0.16, 1, 0.3, 1)`). SFX: *whoosh_smooth*.
- `pop_bounce`: Escala 0.82 -> 1.05 -> 1.00 com overshoot em 0,35 s (`back_overshoot`). SFX: *switch_click_92470*.
- `impact_tremor`: Escala 1.22 -> 1.00 em 0,22 s acompanhada de micro-vibração de choque de ±6 px por 0,35 s. SFX: *low_bass_thud*.
- `wipe_left_right`: Revelação linear de linha dourada ou risco de 0 a 100% em 0,45 s. SFX: *quick_swipe*.
- `counter_roll`: Contagem numérica progressiva de 0 até o valor final em 0,65 s sincronizada com barra gráfica. SFX: *clock_tick_subtle*.
- `timeline_node_pulse`: Nó de linha do tempo acende e pulsa 1.30x com halo dourado ao ser narrado. SFX: *digital_chime_pop*.
- `kinetic_stagger`: Cascata de argumentos com atraso de 80 ms entre cada item.
- `glitch_law_warning`: Dois micro-flickers terracota para alertar sobre prazos fatais e nulidades.

Cada preset traz o bloco `gsap` com o equivalente exato usado nas cenas HyperFrames (ease, duração, estados `from`/`to`) e, quando existe, o bloco do registry correspondente. O arquivo também tem `motion_craft_rules`: ease por papel, saída 40–50% mais curta que a entrada, sobreposição de 30–50%, stagger, tempo de leitura e os padrões "gerados" proibidos.

### Pesquisa de Novas Tendências na Web:
Quando o usuário solicitar novos estilos ou para temas inovadores:
1. Utilize a busca web do agente (`WebSearch`, `search_web` ou equivalente) com termos direcionados (ex.: `"retention editing vertical motion trends 2026"`, `"vox explainer typography remotion"`).
2. Valide se a nova tendência atende à sobriedade do Provimento 205/2021 da OAB e às zonas seguras da plataforma.
3. Salve a nova definição de animação em `presets/animations.json`.

---

## 8. Posicionamento e Zonas Seguras Multiplataforma (`presets/platforms.json`)

| Plataforma | Dimensões | Margem Topo (UI) | Margem Base (UI) | Lateral Direita | Faixa Útil dos Gráficos | Faixa Útil das Legendas |
|---|---|---|---|---|---|---|
| **Instagram Reels** | 1080×1920 (9:16) | 250 px | 385 px | 193 px (y > 1110) | x: 70–1025, y: 250 até cabeça | x: 70–887, y: 1150–1480 (anc. 1300) |
| **TikTok** | 1080×1920 (9:16) | 200 px | 320 px | 170 px (y > 900) | x: 70–1020, y: 200 até cabeça | x: 70–910, y: 1180–1540 (anc. 1320) |
| **YouTube Shorts** | 1080×1920 (9:16) | 220 px | 340 px | 150 px (y > 1000) | x: 70–1020, y: 220 até cabeça | x: 70–930, y: 1160–1520 (anc. 1300) |
| **YouTube Horizontal** | 1920×1080 (16:9) | 108 px (10%) | 108 px (10%) | 192 px (10%) | Split lateral ou Lower Thirds | x: 260–1660, y: 860–980 |
| **Instagram Feed** | 1080×1350 (4:5) | 120 px | 160 px | 60 px | x: 60–1020, y: 120 até cabeça | x: 60–1020, y: 1020–1220 (anc. 1100) |

> **Cruzamento com o HyperFrames (vertical 1080×1920):** a referência da HeyGen pede nada nos 168 px do topo, todo texto entre y=168 e y=1330 e, abaixo de 1330, só textura. Os valores desta tabela são **mais rígidos** e prevalecem. O `check` audita sozinho a faixa de legenda de cada plataforma (o `--caption-zone` do HyperFrames é passado pela ponte), e o `build` posiciona os gráficos só entre `y_min` e o topo da cabeça − 60 px.

---

## 9. Biblioteca Expandida de Cenas (por Função da Fala)

Mais de 25 tipos de cenas gráficas mapeadas para cada necessidade do discurso:

1. **Gancho / Provocação:** Pílula de categoria + Palavra Big Shoulders 180–200 px + barra de prazo esvaziando.
2. **Alerta de Risco Iminente:** Badge `EM RISCO` pulsando em terracota + frase Fraunces com micro-shake de impacto.
3. **Citação de Artigo de Lei:** Pílula dourada com o artigo (ex.: `ART. 11 DA LEI 8.929/94`) + citação condensada em Inter.
4. **Notícia / Fato do Agro:** Card simulando manchete com data e veículo verificado + destaque em amarelo.
5. **Comparação Antes vs Depois:** Duas colunas lado a lado com transição de seta: "Regra Antiga" (terracota) vs "Jurisprudência Atual" (ouro).
6. **Contraste "X não é Y, é Z":** Termo equivocado em itálico riscado em terracota -> Conceito correto revelado em Big Shoulders ouro.
7. **Estatística Financeira (Cédula/Dívida):** Cifrão e valor em Big Shoulders gigante + contador animado + barra com trilho de progresso.
8. **Série Histórica / Safras:** Gráfico de barras verticais por ano (2022 a 2026), subindo na ordem da fala, com a safra crítica destacada em terracota.
9. **Linha do Tempo Processual:** Linha horizontal conectando 3 a 4 nós numerados (Notificação -> Defesa -> Negociação -> Acordo homologado).
10. **Checklist de Exigências:** Lista com ícones de checagem dourados e divisores sutis entrando em cascata.
11. **Três Pilares Estratégicos:** Três colunas simétricas (x: 230 / 540 / 850) com ícone de traço no topo e rótulo explicativo.
12. **Causa e Efeito:** Bloco A (Fato) -> Seta animada -> Bloco B (Consequência Jurídica).
13. **Balança do Produtor Rural:** Ícone de balança oscilando entre Custo de Execução vs Economia da Recuperação.
14. **Metáfora / Analogia do Campo:** Ilustração vetorial limpa (ex.: silo, sementeira, trator) conectada ao princípio jurídico explicado.
15. **Definição Técnica Descomplicada:** Card translúcido com termo em destaque e resumo de uma linha em Fraunces.
16. **Desmistificação de Mito:** Carimbo "MITO" em terracota seguido pela explicação fundamentada.
17. **Alerta de Prazo Fatal:** Card de calendário com folha destacada e contagem regressiva em dias.
18. **Documento Essencial:** Ícone vetorial de escritura/matrícula com badges dos requisitos obrigatórios.
19. **Jurisprudência do STJ:** Pílula `TEMA REPETITIVO STJ` + número do recurso e tese fixada.
20. **Alívio / Solução Jurídica:** Transição suave com halo dourado e mensagem pacificadora em Fraunces Itálico.
21. **Resumo em 3 Pontos:** Card tríplice com contadores 1, 2 e 3 numerando as conclusões do vídeo.
22. **Pergunta Retórica:** Bloco com "E SE O BANCO NÃO ACEITAR?" em Fraunces grande e interrogação destacada.
23. **Quebra de Paradigma:** Ícone de cadeado se abrindo ao revelar a brecha legal legítima.
24. **Transição de Bloco Temático:** Divisor minimalista com novo título de seção deslizando suavemente.
25. **Chamada para Ação (CTA Ético OAB):** Rótulo sutil + frase em Fraunces 110 px ("Muito cuidado.") + linha dourada + convite informativo para salvar/compartilhar.

---

## 10. Presets de Edição de Imagem, Câmera e Cortes

### Presets de Zoom:
- `zoom_subtle_in`: 1.00 -> 1.05 progressivo ao longo do bloco, ancorado no topo da cabeça ($HX, HY$).
- `zoom_subtle_out`: 1.06 -> 1.00 suave para conclusões e respiros reflexivos.
- `punch_in_emphasis`: Punch-in de +6% em 0,18 s, segura 1,2 s e retorna em 0,45 s em revelações cruciais.
- `punch_cut_alternating`: Simulação de câmera B (corte seco para 1.08x) entre tomadas decupadas.
- `tension_creeper`: Zoom lento e contínuo (1.00 -> 1.08 em 15 s) durante narrações de riscos severos.

No HyperFrames, todos viram entradas de `camera` no `cues.json` (`punch_in`, `cut`, `zoom`, `shift`, `reset`, `shake`), aplicadas num wrapper com origem no topo da cabeça, nunca no `<video>`. Reenquadre só no vão entre cards (0,5–0,7 s, `power2.inOut`).

### Presets de Color Grading:
- **Editorial Quente (dourado):** Curvas com pretos levemente levantados, médios ricos e realce térmico dourado:
  ```
  curves=master='0/0.02 0.25/0.27 0.5/0.55 0.8/0.84 1/0.98',
  colorbalance=rs=-0.02:gs=0.01:bs=0.01:rm=-0.03:gm=0.015:bh=0.01,
  eq=contrast=1.05:saturation=0.96
  ```
- **Corporativo Limpo:** Contraste neutro com saturação equilibrada e tons de pele precisos.

### Estilos de Edição (`presets/estilos.json`)
Um estilo junta as decisões de ritmo que mudam de vídeo para vídeo: preset e limiar do `cortar`, animação e palavras por linha da legenda, intensidade da câmera (`punch_in`, `zoom_sutil`), ajuste dos SFX e volume da trilha. O perfil aponta para um com `estilo_padrao`; o projeto pode trocar com `projeto init --estilo <id>` (gravado inteiro no `neuro.json`).

| id | Corte | Legenda | Câmera | SFX / trilha |
|---|---|---|---|---|
| `dinamico_reels` | tight, 140 ms | pop, 3 palavras | 1,09 / 1,06 | 0 dB / 0,14 |
| `editorial_sobrio` | natural, 240 ms | pop, 4 palavras | 1,05 / 1,03 | −3 dB / 0,10 |
| `educativo_claro` | natural, 260 ms | karaokê, 4 palavras | 1,06 / 1,04 | −2 dB / 0,12 |
| `comercial_acelerado` | tight, 100 ms | pop, 3 palavras | 1,12 / 1,07 | +1 dB / 0,16 |
| `documental_calmo` | natural, 320 ms | pop, 5 palavras | 1,03 / 1,02 | −5 dB / 0,10 |

Prioridade no `cortar`: `--limiar-ms` → estilo do projeto → ritmo aprendido do perfil (`memory.json`) → preset. Estilo próprio: `neuro-mv-edit estilo novo` (assistente) ou `estilo novo --json`.

### Presets de Decupagem & Cortes (`projeto cortar --preset`):
- `natural` (`breath_trimmer_natural`): Preserva pausas respiratórias de 180–240 ms (o limiar vem de `learned_preferences.<perfil>.pacing.breath_cut_threshold_ms`), com fades nas emendas.
- `tight` (`breath_trimmer_tight`): Remove silêncios superiores a 120 ms para vídeos de ritmo acelerado.

---

## 11. Motores de Edição: Remotion (padrão) e HyperFrames

### 11.1 Escolha do motor
| Motor | Quando usar | O que faz |
|---|---|---|
| `remotion` (padrão) | Edição com o cliente acompanhando, ajustes visuais, cortes finos, B-roll, efeitos | Cortes, câmera, cartões, legendas, SFX e trilha viram camadas TSX editáveis no **Remotion Studio**. O que o Studio grava volta para `edl.json`/`cues.json`. |
| `hyperframes` | Render sem licença comercial, blocos do registry, QA do `hyperframes check` | Pipeline HTML+GSAP da v1.3/1.4, agora com o mesmo corte automático (o ffmpeg monta `assets/base_cortado.mp4`). |

Escolha no `projeto init --engine remotion|hyperframes`. Sem a opção, vale `NEURO_ENGINE`, depois `engine_default` do perfil, depois `remotion`. O motor fica gravado no `neuro.json` e todos os comandos despacham por ele.

### 11.2 A porta única `scripts/neuro_project.py`
```bash
NP="neuro-mv-edit projeto"   # sem o plugin: npx --yes github:monrars1995/oneuros-mv-edit projeto · ou python3 scripts/neuro_project.py
$NP init        --engine remotion --profile exemplo_juridico --video bruto.mp4 --out projetos/cpr --head-y 560 --resolucao 4k,1080p --codec h264 [--fps original] [--qualidade maxima] [--estilo dinamico_reels]
$NP transcrever -P projetos/cpr                       # whisper (hyperframes transcribe), fonte inteira, pt
$NP legendas    -P projetos/cpr --apply-glossary --fix "exédulas=cédulas" --learn
$NP cortar      -P projetos/cpr --preset natural       # edl.json; --remover 12.3-15.8 · --manter 40-44 · --dry-run
#   → escrever projetos/cpr/cues.json (cenas, câmera, SFX, trilha, efeitos, B-roll)
$NP build       -P projetos/cpr
$NP estudio     -P projetos/cpr                        # abre o Studio no navegador e deixa o vigia rodando
$NP check       -P projetos/cpr                        # zero erros; pese cada aviso
$NP snapshot    -P projetos/cpr                        # PNG de cada cena + início/meio/fim — ABRA os PNGs
$NP render      -P projetos/cpr                        # delivery: PNG por quadro, uma versão por resolução decidida, uma codificação só
$NP exportacao  -P projetos/cpr --resolucao 1440p --codec hevc [--mezanino]   # muda a decisão depois do init
$NP master      -P projetos/cpr --name EXEMPLO_TITULO # loudness 2 passagens em todas as resoluções + cópia _leve
$NP salvar -m "aprovado pelo cliente" ; $NP historico ; $NP voltar <ref> ; $NP status
```
Todo comando que muda o projeto termina com **checkpoint git local** (só texto: JSON, TSX, HTML, CSS; mídia e renders ficam fora). `historico` lista, `voltar <ref>` restaura e regera.

### 11.3 Remotion: Studio aberto, projeto sempre salvo
- **Camadas geradas** em `remotion/src/gerado/`: `Cortes.tsx` (clipes `<Video trimBefore durationInFrames>` num `TransitionSeries`), `Camera.tsx` (keyframes inline de `scale`/`translate`), `Cenas.tsx` (sequências dos cartões), `Trilhas.tsx` (fala, SFX, trilha), `Efeitos.tsx` (flash, dip, fade final), `Broll.tsx` e `Legendas.tsx`. São escritas no formato que o Studio sabe editar: valores literais, um nó por clipe, sem `.map()`.
- **`estudio`** sobe `remotion studio` em segundo plano (porta livre a partir de 3000), abre `http://localhost:<porta>/NeuroEdit` e inicia o **vigia**. Diga a URL ao cliente. `--sem-navegador` não abre; `--parar` encerra.
- **O Studio grava direto nos arquivos.** O vigia percebe, roda o `sincronizar` (cortes → `edl.json`; cenas movidas/esticadas → `cues.json`; as outras cenas e a câmera acompanham o novo corte, ancoradas na fala), remonta a fala, ajusta a duração e faz checkpoint após 4 s de calma.
- **O `build` nunca pisa em edição do Studio.** Camada editada que não bate com a versão gerada fica como está, com aviso; `build --force` regera a partir dos JSON. Se o Studio e os JSON mudaram ao mesmo tempo, o `build` para e pede `sincronizar` (fica com o Studio) ou `build --force` (fica com os JSON).
- **Antes de editar `edl.json`/`cues.json` com o Studio aberto**, rode `sincronizar` (ou confie no vigia) e releia os arquivos: o Studio pode ter mudado algo.
- **Cartões:** os 7 templates (`hook`, `stat`, `quote`, `contrast`, `checklist`, `timeline`, `cta`) saem do mesmo gerador Python nos dois motores: mesmo markup, mesmo CSS, mesmos tweens GSAP, montados no Remotion por `@remotion/gsap`. O contador do `stat` é derivado do quadro.
- **Novidades de `cues.json` (Remotion):** `efeitos: [{kind: "flash"|"dip", at, dur, intensidade?, cor?}]`, `broll: [{src, start, duration, trim?}]`, `music.ducking` (`false` desliga; objeto ajusta threshold/ratio/attack/release) e, por cena, `motor: "hyperframes"` ou `html: "<composição>.html"` (11.5).
- Contrato completo e solução de problemas: **`references/remotion/BRIDGE.md`**.

### 11.4 HyperFrames: a ponte `scripts/hf_project.py`
O motor `hyperframes` usa a mesma porta única. A ponte direta continua disponível (`neuro-mv-edit hf <sub> --project <proj>`; aqui `--project` é obrigatório e não tem `-P`): `init`, `captions`, `build`, `check`, `snapshot`, `preview`, `render`, `master`. O `cortar` monta `assets/base_cortado.mp4` e as legendas e cenas são remapeadas; o `build` e o `check` (com a faixa de legenda da plataforma) seguem como na v1.4. As cenas são HTML que o cliente ajusta no preview, e o `build` não sobrescreve essas edições sem `--force`. Esquema do `cues.json`, templates e problemas comuns: **`references/hyperframes/BRIDGE.md`**. Mapa das 25 cenas → template/bloco: **`references/hyperframes/CENAS.md`**.

**Skills oficiais que a Neuro chama** (instaladas por `npx hyperframes skills update`):
| Skill | Quando a Neuro usa |
|---|---|
| `/hyperframes` | **Ler antes** de criar ou editar qualquer HTML de cena: contrato de render, formato, legendas, overlays, movimento, som e revisão |
| `/hyperframes-cli` | `check`, `snapshot`, `preview`, `render`, `timeline`, `keyframes` e recuperação de falhas |
| `/hyperframes-registry` | **Antes** de desenhar à mão um visual nomeado (gráfico, transição, lower third, estilo de legenda, câmera) |
| `/media-use` | Tratamento de imagem (`media-treatment`), recorte (`remove-background`), trilha, SFX, voz e loudness |

### 11.5 Remotion + HyperFrames juntos (por cena)
O melhor dos dois entra por cena, não por pipeline inteiro. No motor `remotion`, uma cena com `"motor": "hyperframes"` (template Neuro) ou `"html": "caminho/composicao.html"` (bloco do registry ou composição própria, ex.: `headline-slam`, recorte do apresentador) é renderizada pelo HyperFrames em **ProRes 4444 com alfa** (`cartoes-hf/<id>-<hash>.mov`, em cache) e entra na timeline do Remotion por cima do vídeo. Só o render final codifica em H.264, então não há perda de geração. Descartado: renderizar o corte no Remotion e finalizar no HyperFrames (dois renders inteiros, e o Studio não mostraria o filme final).

### 11.6 Papel do ffmpeg ao lado do Remotion
O Remotion traz o próprio ffmpeg (série 7.1) para codificar e mixar. O ffmpeg do sistema faz o resto:
- **Antes:** mezanino CFR com keyframe a cada 1 s, BT.709 e a grade do perfil (`init`); áudio para o Whisper; `ebur128` + `silencedetect` para os cortes.
- **No meio:** a fala do filme (`dados/fala-<hash>.wav`), montada do EDL com precisão de amostra; a trilha com ducking por sidechain.
- **Depois:** master em 2 passagens `loudnorm`, cópia leve, metadados (`inject_metadata.py`).
- **Não faz mais:** overlay de gráficos (o Remotion compõe alfa) nem os cortes do motor Remotion (viram clipes `trimBefore` não destrutivos).

### 11.7 Licença do Remotion
O Remotion é grátis para pessoa física, empresas com até 3 pessoas e ONGs. A partir de 4 pessoas (contando todo o pessoal, use ou não o Remotion) é preciso a **Company License** (https://www.remotion.dev/license): "Creators" US$ 25/mês por assento ou "Automators" US$ 0,01 por render (mínimo US$ 100/mês). Render feito por agente conta como automação; o preview no Studio não. Com `REMOTION_LICENSE_KEY` no ambiente, o `render` passa `--license-key`. O HyperFrames (Apache-2.0) não tem essa restrição.

### 11.8 Padrão de acabamento (resumo — detalhes em `references/hyperframes/TECNICAS.md`)
- **Primeiro segundo:** o quadro 0 já mostra rosto ou frase forte (nunca preto ou logo). O gancho entra em 0,1–0,3 s e a mudança chega no primeiro tempo.
- **Ritmo vertical:** um estímulo a cada 2–4 s. Uma cena a cada 6–8 s em vídeos de até 1 min. Segure 0,3–0,75 s antes do payoff.
- **Ease por papel:** entrada `expo.out`/`power4.out`, câmera `power2.inOut`, saída `power3.in` 40–50% mais curta. Sobreposição de 30–50%. Stagger de 0,06–0,12 s entre palavras e 0,04–0,08 s entre itens. Linear só em progresso.
- **Títulos:** pousou, parou. Varie a entrada (blur por palavra, linha inteira, cinza → tinta, por letra, atrás do apresentador). Uma palavra de destaque, a que carrega o sentido.
- **Leitura:** 0,5 s + 0,3 s por palavra. Última linha ≥ 2 s. Nada legível abaixo de 28 px. Linha que não cabe se corta, não se encolhe.
- **Proibidos (parecem gerados):** loop de respiração/pulso, título que continua escalando, bounce em UI, toda cena entrando igual, fade + slide-up em tudo.
- **Transições com causa:** 3–5 tipos por vídeo; no máximo 1/3 das emendas entre blocos como corte seco; dip cut (−40% por 3 quadros) quando não houver B-roll.
- **Som:** pico 1 quadro depois da imagem, 2–3 takes alternados, cada efeito 3–6 dB acima da trilha, trilha com energia acima de 150 Hz (celular), true peak ≤ −1 dBTP, master −14 LUFS **medido** e depois **ouvido**.
- **Imagem:** grade pelo perfil (FFmpeg no `init`) ou por `npx hyperframes media-treatment`. Nunca filtro CSS sobre o vídeo. HDR/LOG convertido para Rec.709 antes.

---

## 12. Sound Design & Integração ElevenLabs MCP

**Regra Absoluta:** Vídeo sem som nas animações é considerado incompleto. Todo movimento visual deve ser acompanhado de resposta acústica correspondente.

### Ferramentas MCP ElevenLabs:
O nome exato da ferramenta depende do agente: no Claude Code, `mcp__plugin_neuro-mv-edit_elevenlabs__text_to_sound_effects` com o plugin ou `mcp__elevenlabs__text_to_sound_effects` configurado à mão; no Antigravity, `call_mcp_tool(ServerName: "elevenlabs", ToolName: ...)`. Procure pelo final `text_to_sound_effects`. Com o plugin, basta autorizar em `/mcp`; nos outros casos, `neuro-mv-edit mcp` mostra a configuração. Salve cada efeito em `<projeto>/assets/sfx/<tipo>_NN.wav` (`whoosh`, `pop`, `click`, `thud`, `tick`, `swipe`), gere 2–3 takes de cada tipo, e o `hf build` posiciona e alterna. Sem ElevenLabs, use a skill `/media-use` (`npx hyperframes media-use resolve --type sfx --intent "..."`).
1. `text_to_sound_effects` — `{ "text": "...", "duration_seconds": ... }`
   - **Click de Card:** `"subtle mechanical switch click sound, clean studio recording, short 0.2s"`
   - **Whoosh de Transição:** `"gentle cinema whoosh transition air movement, 0.4s"`
   - **Impacto de Dado / Terracota:** `"deep punchy bass thud hit for data emphasis, 0.3s"`
   - **Pop de Pílula:** `"smooth tactile digital pop sound, 0.15s"`
   - **Relógio / Prazo:** `"minimal soft clock ticking sequence, 0.6s"`
2. `compose_music`
   - Geração de trilhas de fundo instrumentais personalizadas (pad suave, 90 bpm, harmonia neutra corporativa).
3. `isolate_audio`
   - Limpeza e restauração de voz em gravações captadas em ambientes com eco ou ruídos de fundo.

### Parâmetros de Mixagem e Masterização:
- **SFX Level:** Mixados a -14 a -18 dBFS abaixo do pico da voz.
- **Trilha de Fundo (Ducking):** Volume mantido a -32 dBFS durante as falas, subindo 3 dB nos silêncios através de compressor sidechain (`threshold=0.03:ratio=4:attack=60:release=600`).
- **Masterização Final:** Normalização EBU R128 em **duas passagens** (`loudnorm=I=-14:TP=-1.5:LRA=9`, medição + `linear=true`) com conferência de True Peak e ausência de clipping. `hf master` faz isso e grava `<nome>_loudness.json`.
- **Posicionamento:** o pico do efeito cai **1 quadro depois** da imagem (a luz chega antes do som). Efeito só onde há causa na tela: whoosh em corte ou card grande em movimento, pop em pílula/número pousando, click em clique real, tick em texto/contador chegando, riser → impacto uma vez no payoff.
- **Variação:** 2–3 takes alternados por tipo. O mesmo whoosh em todo corte é o defeito mais comum.
- **Celular:** uma trilha com quase toda a energia abaixo de 150 Hz não aparece no alto-falante do celular. Confira o render com `npx hyperframes audio <master> --json`.

---

## 13. Injeção de Metadados & Geração de Copy (`scripts/inject_metadata.py`)

Todo vídeo entregue leva metadados no MP4 e uma copy de postagem pronta.

```bash
neuro-mv-edit metadata -i projetos/cpr/renders/master/CPR_MASTER.mp4 -p exemplo_juridico \
  -t "Atenção ao prazo da notificação fiscal" -d "O que observar antes de responder ao Fisco."
#   -p é obrigatório (perfil da skill ou da biblioteca); --json meta.json acrescenta/substitui campos
#   (keywords, caption_body, first_comment...); -o igual à entrada grava no lugar
```

O script:
1. **Grava os metadados.** Copia o vídeo sem recompressão, num arquivo temporário trocado no fim (escrita atômica), com `title`, `artist`, `album_artist` (@), `comment`/`description`, `copyright`, `genre` e `date`. A cópia leve (`<stem>_leve.mp4`), se existir, recebe os mesmos metadados.
2. **Define cada campo nesta ordem de prioridade:** perfil (`default_metadata`, nome, @, segmento) < `--json` < `-t`/`-d`.
3. **Para em caso de erro.** Perfil inexistente, `--json` ausente ou falha do ffmpeg: sai com código 1 e **não** gera a copy.
4. **Gera `<vídeo>_COPY_POSTAGEM.md`** ao lado do vídeo, com:
   - hook;
   - legenda: a legenda-modelo do perfil (`default_metadata.caption_template`, com `{nota}`) ou, sem ela, título + descrição + CTA do perfil;
   - nota de conformidade quando o setor exige (OAB, saúde);
   - hashtags de `default_metadata.keywords`;
   - primeiro comentário (`default_metadata.first_comment` do perfil, ou um texto padrão do segmento).

---

## 14. Memória Persistente & Autoaprendizado

A memória tem duas camadas, lidas juntas:

**`data/memory.json` (vem com a skill, só leitura)**
- Glossários por segmento: `legendas` traz só correções de grafia, aplicadas por `legendas --apply-glossary` apenas no segmento do perfil e sem nunca acrescentar palavras; `replacements` traz a forma completa dos termos, como dica para cenas e copy.

**`~/.neuro-mv-edit/memory.json` (sua)**
- Aprendizados e histórico. Fica fora da skill e sobrevive a reinstalações.
- Por cima da memória da skill.

O que vai em cada uma:
- **Correções de transcrição aprendidas:** `projeto legendas --fix "errado=certo" --learn` grava em `learned_preferences.<perfil>.transcript_fixes` da memória do usuário. São aplicadas nos próximos vídeos do perfil. As correções do glossário não são aprendidas, porque já vêm da skill.
- **Preferências por especialista** (`learned_preferences.<perfil>`): ritmo (`pacing.breath_cut_threshold_ms`, `crossfade_duration_ms`, `clapper_cues`), ancoragem da cabeça, volume de SFX e tom.
- **Histórico de produção** (`history[]`): duração antes e depois, tomadas, LUFS, nº de legendas e de cenas, aprendizado-chave.
- **Loop de feedback:** quando o usuário pedir um ajuste que deve valer para os próximos vídeos, registre em `~/.neuro-mv-edit/memory.json`, criando o arquivo se faltar. **Nunca** registre em `data/memory.json`, que é recriado a cada instalação.

---

## 15. Organização e Hierarquia de Entregas (`scripts/organize_deliveries.py`)

Nenhum arquivo final fica solto na raiz do projeto. O pacote é **copiado** para:

```text
entregas/
  └── AAAA-MM/
      └── DD/
          └── <rede>/  (reels, tiktok, shorts, youtube, feed)
              ├── CPR_MASTER_meta.mp4
              ├── CPR_MASTER_leve_meta.mp4          (se o perfil exige cópia leve)
              ├── CPR_MASTER_meta_COPY_POSTAGEM.md
              ├── CPR_loudness.json
              └── (relatório, prévia e extras passados por opção)
```

```bash
neuro-mv-edit organize -m projetos/cpr/renders/master/CPR_MASTER_meta.mp4 -n reels \
  [-r RELATORIO_ENTREGA.md] [-p preview.png] [-e outros arquivos] [-b entregas]
```

- Os arquivos do mesmo vídeo vão juntos automaticamente: cópia leve, relatório de loudness e copy.
- Vídeo inexistente: sai com código 1 sem criar pasta.
- Rodar de novo sobre a mesma entrega não quebra.

---

## 16. Compliance Jurídico e Editorial (Provimento OAB 205/2021)

- **Caráter Informativo Exclusivo:** O conteúdo deve orientar e esclarecer direitos, sem mercantilização.
- **Sem Promessas de Resultado:** É vedado assegurar ganho de causa ou desfechos judiciais.
- **Sem Captação Indevida:** Chamadas para ação devem convidar a salvar ou compartilhar a informação, nunca incitar litígios desnecessários.
- **Fontes e Dados Verificáveis:** Todo número, estatística ou citação de tribunal superior exibido na tela deve ser checado antes da renderização.

---

## 17. Checklist de Controle de Qualidade

Antes de entregar o pacote ao cliente:
- [ ] Decisões de exportação tomadas com o usuário (resolução, codec, fps) e ambiente verificado com `neuro-mv-edit verificar --corrigir` (sem ✗; MCP do ElevenLabs ativo).
- [ ] Cada master conferido com `ffprobe`: resolução, codec, fps e `bt709` decididos.
- [ ] Transcrição com modelo multilíngue (`--language pt`) e termos corrigidos (glossário + `--fix`).
- [ ] `projeto check` com **zero erros** e avisos pesados (contraste, leitura, fonte ≥ 28 px).
- [ ] `projeto snapshot` aberto e revisado cena a cena e emenda a emenda (também em largura de celular).
- [ ] Render de entrega (`--strict` no HyperFrames; PNG por quadro no Remotion) e duração conferida contra o projeto (soma do `edl.json`).
- [ ] Edições feitas no Studio sincronizadas (`projeto status` sem pendências) e checkpoint salvo.
- [ ] Tomadas selecionadas sem claquetes ou hesitações.
- [ ] Emendas sem palavras duplicadas e com micro-crossfades suaves.
- [ ] Todos os gráficos posicionados dentro da zona segura e estritamente acima da cabeça.
- [ ] Nenhuma colisão entre gráficos e legendas (mínimo de 120 px de espaço livre).
- [ ] Legendas com tamanho calibrado, centralizadas na margem útil sem encostar nos botões do app.
- [ ] Sound design completo: SFX em cada animação e trilha com ducking por sidechain sob a fala.
- [ ] Loudness masterizado e verificado em -14 LUFS integrado.
- [ ] Metadados injetados no container MP4.
- [ ] Arquivo `<vídeo>_COPY_POSTAGEM.md` gerado e revisado.
- [ ] Entrega devidamente movida para `entregas/AAAA-MM/DD/<rede>/`.
- [ ] Histórico e aprendizados registrados em `~/.neuro-mv-edit/memory.json`.
- [ ] Vídeo exportado assistido integralmente do início ao fim.

---

## Instalação nos Agentes

Esta pasta (`skills/neuro-mv-edit/` no repositório) é a skill completa. O instalador `npx --yes github:monrars1995/oneuros-mv-edit#v1.10.0` (assistente) ou `... install` (sem perguntas) entrega o neuro-mv-edit como **plugin** onde o agente tem sistema de plugin:
- **Claude Code:** skill + comandos + subagentes + ElevenLabs MCP + comando no PATH, travado na tag da versão.
- **Hermes:** Agent Plugins, travado no commit da tag.
- **OpenCode:** plugin V2.
- **Open Design:** plugin pelo daemon.
- **Neuro Harness** (DeepSeek Harness, perfil `neuro`): plugin pelo `dsh plugin --profile neuro add`, travado na tag (de um clone, `link:`); registra a skill e põe `neuro-mv-edit` no PATH. Reinicie o Harness depois (`neuro-harness restart`).
- **Codex** (via `~/.agents/skills`), Gemini, Antigravity e Cursor recebem a pasta da skill. Em modo skill, o Neuro Harness também lê `~/.agents/skills`.

`--mode <agente>=skill` volta um agente para a pasta de skill. O repositório é público. Para conferir: `npx --yes github:monrars1995/oneuros-mv-edit#v1.10.0 status --deep`. Histórico de versões: `CHANGELOG.md` na raiz do repositório. No Codex, com bibliotecas grandes, chame a skill com `$neuro-mv-edit`.

## Arquivos e Módulos da Skill

- `presets/profiles.json`: Perfis de demonstração fictícios (`exemplo_juridico`, `exemplo_educacao`) e o modelo `template_novo_perfil`. Perfis reais vão para a biblioteca do usuário (`perfil novo` ou `perfil importar`).
- `presets/themes.json`: Identidade visual completa (paletas de cores, fontes, pílulas, badges e divisores).
- `presets/animations.json`: Catálogo de curvas bezier, tempos, easing e diretrizes de tendências web.
- `presets/estilos.json`: Estilos de edição (ritmo de corte, legenda, câmera, SFX e trilha).
- Biblioteca do usuário `~/.neuro-mv-edit/{perfis,temas,estilos}/`: perfis, temas e estilos criados com `perfil|tema|estilo novo`; vencem os presets de mesmo id.
- `presets/platforms.json`: Dimensões, safe zones e especificações técnicas por rede social.
- `data/memory.json`: Glossários fonéticos por segmento (jurídico/agro, automotivo/CRM, educação). Preferências aprendidas e histórico ficam em `~/.neuro-mv-edit/memory.json`.
- `scripts/neuro_verificar.py`: Verificação do ambiente pelas decisões da edição (`verificar --corrigir`, `--json`, `--hook`).
- `scripts/neuro_export.py`: Decisões de exportação (análise da fonte, área útil, plano por resolução, flags de render e codificação final).
- `scripts/verify-env.py`: Download e validação das fontes oficiais (usado pelo `verificar`).
- `scripts/inject_metadata.py`: Injetor de metadados no MP4 e gerador de cópia de postagem.
- `scripts/organize_deliveries.py`: Organizador automatizado de arquivos de entrega em pastas por data e rede.
- `scripts/neuro_project.py`: Porta única dos projetos com escolha de motor (`init`, `transcrever`, `legendas`, `cortar`, `build`, `estudio`, `sincronizar`, `check`, `snapshot`, `render`, `master`, `salvar`, `historico`, `voltar`, `status`, `motor`).
- `scripts/neuro_remotion.py`: Motor Remotion (instalação compartilhada, camadas editáveis, Studio + vigia, render, stills, cenas pelo HyperFrames com alfa).
- `scripts/neuro_preview.py`: Prévia HTML de um tema (7 cartões + legenda), com perfil, estilo e plataforma opcionais.
- `scripts/neuro_edl.py`: Decupagem (`edl.json`), sugestão de cortes, remapeamento fonte ↔ filme e montagem da fala/vídeo pelo ffmpeg.
- `scripts/hf_project.py`: Ponte HyperFrames (`init`, `captions`, `build`, `check`, `snapshot`, `preview`, `render`, `master`) e o gerador dos 7 cartões usado pelos dois motores.
- `open-design.json`: Manifesto que transforma esta pasta em plugin do Open Design (`od plugin install`).
- `references/remotion/BRIDGE.md`: Motor Remotion: fluxo, camadas, Studio, sincronização, licença e problemas comuns.
- `references/remotion-project/`: Template do projeto Remotion (versões exatas + lock, composição, cartão GSAP, legendas, leitor de TSX e stills).
- `references/hyperframes/BRIDGE.md`: Fluxo completo, esquema do `cues.json`, templates, câmera, SFX e problemas comuns.
- `references/hyperframes/TECNICAS.md`: Padrão de acabamento (ritmo, movimento, legendas, cards, som, imagem e revisão) com números.
- `references/hyperframes/CENAS.md`: As 25 cenas da biblioteca → template Neuro ou bloco do registry HyperFrames.
- `references/hyperframes-template/neuro-components.css`: Componentes visuais compartilhados pelas cenas.

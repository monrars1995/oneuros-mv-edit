# Referência de comandos do neuro-mv-edit (v1.10.0)

Esta página lista todos os comandos e todas as opções do neuro-mv-edit, conferidos com o código. Para começar do zero, veja o [README](../README.md#início-rápido).

**Sumário**

- [Como chamar o CLI](#como-chamar-o-cli)
- [Comandos do plugin no Claude Code](#comandos-do-plugin-no-claude-code)
- [Subagentes](#subagentes)
- [Instalação e diagnóstico](#instalação-e-diagnóstico)
- [Biblioteca: perfis, temas e estilos](#biblioteca-perfis-temas-e-estilos)
- [Projetos: `projeto`](#projetos-projeto)
- [Ponte HyperFrames: `hf`](#ponte-hyperframes-hf)
- [Motor Remotion: `remotion`](#motor-remotion-remotion)
- [Entrega: `metadata` e `organize`](#entrega-metadata-e-organize)
- [Variáveis de ambiente](#variáveis-de-ambiente)
- [Onde ficam os arquivos](#onde-ficam-os-arquivos)
- [Códigos de saída](#códigos-de-saída)

---

## Como chamar o CLI

| Onde você está | Prefixo |
|---|---|
| Sessão do Claude Code ou do Neuro Harness com o plugin ativo | `neuro-mv-edit` (o plugin coloca o comando no PATH) |
| Qualquer terminal ou outro agente | `npx --yes github:monrars1995/oneuros-mv-edit#v1.10.0` |
| Clone do repositório | `node cli/cli.js` |
| Só os scripts de projeto, da pasta da skill | `python3 scripts/neuro_project.py` (equivale a `projeto`) |

Nos exemplos abaixo, `neuro-mv-edit` representa qualquer um desses prefixos.

- **Prefira a tag.** O `npx` guarda em cache o que já baixou. Sem `#vX.Y.Z`, ele pode rodar uma versão antiga.
- **Sem terminal interativo** (agente de IA, CI, `NEURO_NO_TTY=1`), os assistentes não perguntam nada. Cada um diz qual opção ou `--json` usar e sai com o código 2.

**Apelidos dos comandos**

| Comando | Apelidos |
|---|---|
| `setup` | `configurar` (e rodar sem comando num terminal interativo) |
| `status` | `doctor` |
| `projeto` | `p` |
| `hf` | `hyperframes` |
| `perfil`, `tema`, `estilo` | `perfis`, `temas`, `estilos` |
| `version` | `--version`, `-v` |
| `help` | `--help`, `-h` (e rodar sem comando fora de um terminal) |

---

## Comandos do plugin no Claude Code

Os comandos aparecem como `/neuro-mv-edit:<nome>`. Cada um roda o CLI por baixo.

| Comando | Argumentos | O que faz | CLI usado |
|---|---|---|---|
| `/neuro-mv-edit:editar` | `<vídeo> [perfil] [--engine remotion\|hyperframes] [--estilo <id>] [--resolucao 4k,1080p] [--codec h264\|hevc\|prores]` | O fluxo completo, do vídeo bruto à entrega: decisões de exportação primeiro, verificação do ambiente, e 3 paradas para aprovação (cortes, cenas, revisão) | `exportacao analisar`, `verificar --corrigir`, `projeto init` … `master`, `metadata`, `organize` |
| `/neuro-mv-edit:exportar` | `[pasta do projeto] [--resolucao 4k,1080p] [--codec ...] [--qualidade alta\|maxima]` | Exporta ou reexporta um projeto em 4K, 1440p, 1080p, 720p ou na resolução da fonte, em H.264, HEVC ou ProRes, sem perder qualidade | `projeto exportacao`, `verificar`, `projeto render`, `projeto master` |
| `/neuro-mv-edit:verificar` | `[--motor ...] [--resolucao ...] [--codec ...] [--video <fonte>]` | Verifica e corrige o ambiente para a edição pedida, inclusive skills de apoio e MCPs | `verificar --corrigir` |
| `/neuro-mv-edit:perfil` | `[novo \| editar <id> \| listar \| mostrar <id>]` | Cria ou edita um perfil com perguntas no chat e mostra a prévia | `perfil novo --json`, `perfil editar <id> --json`, `tema preview` |
| `/neuro-mv-edit:tema` | `[listar \| preview <id> \| novo \| editar <id>]` | Escolhe, mostra ou cria um tema visual | `tema listar`, `tema preview`, `tema novo --json` |
| `/neuro-mv-edit:estudio` | `[pasta do projeto] [parar]` | Abre o Remotion Studio (ou o preview do HyperFrames) e mostra a URL | `projeto estudio` |
| `/neuro-mv-edit:entregar` | `[pasta do projeto] [rede]` | Grava os metadados e a copy do último master e arquiva a entrega | `metadata`, `organize` |
| `/neuro-mv-edit:setup` | — | Confere o ambiente (ffmpeg, Node, motores, fontes, ElevenLabs) e resolve o que faltar | `verificar --corrigir`, `remotion status`, `status --deep` |
| `/neuro-mv-edit:status` | `[pasta do projeto]` | Estado de um **projeto**: motor, cortes, cenas, Studio, checkpoints, último render | `projeto status`, `projeto historico` |
| `/neuro-mv-edit:neuro-mv-edit` | pedido livre | Carrega a skill completa. Ela também é ativada sozinha quando o pedido é de edição | — |

> **Dois nomes iguais, duas coisas diferentes.**
> - `/neuro-mv-edit:status` mostra um projeto. `neuro-mv-edit status` mostra a instalação nos agentes.
> - `/neuro-mv-edit:setup` confere o ambiente. `neuro-mv-edit setup` é o instalador dos agentes.

Sem pasta nos argumentos, `estudio`, `entregar` e `status` usam a pasta atual, se ela tiver `neuro.json`. Senão, usam o projeto mais recente em `projetos/`.

---

## Subagentes

| Subagente | Quando usar | O que devolve |
|---|---|---|
| `@agent-neuro-mv-edit:decupador` | Depois do `transcrever`, antes de aplicar o `cortar` | Uma lista `início–fim (s) \| trecho \| motivo`, a linha pronta `neuro-mv-edit projeto cortar -P <proj> --remover a-b … --dry-run` e o que ficou em dúvida |
| `@agent-neuro-mv-edit:revisor` | Depois do `build` ou do `render` | Uma tabela `cena \| tempo \| problema \| correção sugerida`, os itens que passaram e o veredito: "pronto para entregar" ou "corrigir antes" |

- Os dois só leem: têm acesso a Bash, Read, Glob e Grep e não alteram o projeto. Quem aplica o que eles sugerem é você ou o agente principal.
- O `/neuro-mv-edit:editar` chama os dois sozinho.
- Para chamar à mão, numa sessão do Claude Code:

  ```text
  @agent-neuro-mv-edit:decupador projetos/cpr
  @agent-neuro-mv-edit:revisor projetos/cpr
  ```

---

## Instalação e diagnóstico

### `setup`: assistente de instalação

```bash
neuro-mv-edit setup [--yes] [--agent <ids>] [--dry-run] [--remotion] [--skip-hyperframes] [--skip-verify]
```

**O que o assistente pergunta**

- **Agentes:** quais da máquina recebem o neuro-mv-edit. Os detectados vêm marcados, com a versão já instalada.
- **Modo de cada um:** plugin ou skill, no Claude Code, no Hermes, no OpenCode e no Neuro Harness.
- **Extras:**
  - as skills do HyperFrames;
  - o motor Remotion;
  - a verificação de ambiente e das fontes;
  - o guia do ElevenLabs.
- **Perfil:** se quer criar o primeiro.

**Sem terminal**

- O `setup` exige `--yes`.
- Ele instala nos agentes detectados com os modos padrão.

### `install`: instala ou atualiza sem perguntas

```bash
neuro-mv-edit install [opções]
```

| Opção | Apelidos | O que faz |
|---|---|---|
| `--agent <ids>` | `-a`, `--agent=<ids>` | Só esses agentes (vírgulas ou repetido). `all` ou `--all` = todos |
| `--mode <id>=plugin\|skill` | `--mode=<…>` | Modo por agente (vale para `claude-code`, `hermes`, `opencode`, `neuro-harness`). Ex.: `--mode claude-code=skill,hermes=plugin` |
| `--skills-only` | `--no-plugin` | Pasta de skill em vez de plugin no Claude Code, no Hermes, no OpenCode e no Neuro Harness. O Open Design é sempre plugin |
| `--plugin` | `--as-plugin` | Força o plugin. Já é o padrão desde a 1.7.0. Não combina com `--skills-only` |
| `--link` | — | Uma cópia em `~/.agents/skills` e links nos outros agentes (modo skill) |
| `--copy` | — | Desfaz um `--link` anterior na mesma linha (cópias independentes, o padrão) |
| `--target <pasta>` | — | Instala só em `<pasta>/neuro-mv-edit`, ex.: `.claude/skills` de um projeto |
| `--od-source <origem>` | — | Origem do plugin do Open Design. Padrão: a pasta da skill deste pacote |
| `--remotion` | `--with-remotion` | Já instala o motor Remotion. Sem a opção, ele é instalado no primeiro projeto Remotion |
| `--skip-hyperframes` | — | Não instala as skills oficiais do HyperFrames |
| `--skip-verify` | — | Não roda o verificador de ambiente e das fontes no fim |
| `--dry-run` | — | Mostra o que faria, sem escrever nada |

Instalando de uma tag (`#vX.Y.Z` ou `npx`), o neuro-mv-edit fica fixo naquela versão:
- **Claude Code:** o marketplace aponta para `monrars1995/oneuros-mv-edit#vX.Y.Z`.
- **Hermes:** o plugin fica preso ao commit da tag.
- **Neuro Harness:** o perfil instala `github:monrars1995/oneuros-mv-edit#vX.Y.Z`.

Instalando de um clone git, ele usa as pastas locais: o marketplace do Claude Code aponta para o clone, o Hermes instala da `main` e o Neuro Harness recebe `link:<clone>`.

**Trocando de modo**
- **Para plugin:** sai a cópia avulsa da skill daquele agente.
- **Para skill:** o plugin daquele agente é desinstalado.

### Ids de `--agent`

| Id | Apelidos | Padrão | Onde |
|---|---|---|---|
| `claude-code` | `claude` | plugin | plugin `neuro-mv-edit@neuro-mv-edit` (escopo do usuário); skill em `~/.claude/skills` |
| `codex` | `openai-codex` | skill | `~/.agents/skills/neuro-mv-edit` |
| `opencode` | `open-code` | plugin | `~/.config/opencode/plugins/neuro-mv-edit` |
| `hermes` | `hermes-agent` | plugin | plugin `neuro-mv-edit`; skill em `~/.hermes/skills` |
| `open-design` | `opendesign`, `od` | plugin | biblioteca do Open Design (o app precisa estar aberto) |
| `neuro-harness` | `dsh`, `deepseek-harness`, `neuroharness` | plugin | plugin `neuro-mv-edit` no perfil `neuro` do Neuro Harness (`dsh plugin --profile neuro add`, com `DSH_HOME=~/.neuro-harness/dsh`); skill: `~/.agents/skills` (a mesma do Codex, que o `neuro-harness` nunca apaga) |
| `gemini-cli` | `gemini` | skill | `~/.gemini/skills` |
| `antigravity` | — | skill | `~/.gemini/antigravity/skills` |
| `antigravity-cli` | — | skill | `~/.gemini/antigravity-cli/skills` |
| `cursor` | `cursor-agent` | skill | `~/.cursor/skills` |
| `universal` | `agents`, `agent-skills` | skill | `~/.agents/skills` (Codex, Kimi, Warp, Zed, Pi e outros) |

### `uninstall`, `status`, `agents`, `verificar`, `exportacao` e outros

| Comando | Opções | O que faz |
|---|---|---|
| `uninstall` | `--agent <ids>`, `--target <pasta>`, `--dry-run` | Remove a skill e os plugins. Nunca apaga um clone git nem uma pasta com outra skill de mesmo nome. Não toca em `~/.neuro-mv-edit/`. No `neuro-harness`, roda `dsh plugin --profile <perfil> remove neuro-mv-edit` e deixa `~/.agents/skills` |
| `status` | `--deep`, `--agent <ids>` | Por agente: onde está, a versão e o modo. O `--deep` pergunta ao próprio agente se ele carrega a skill: `claude plugin details`, `codex debug prompt-input`, `hermes plugins list`, o daemon do Open Design e, no Neuro Harness, o `dsh --version` e o `package.json` do perfil (origem, versão instalada, ativo ou não) |
| `agents` | — | Os agentes suportados, a pasta de cada um, o modo padrão e se foi detectado |
| `verificar` (`verify`) | `--motor remotion\|hyperframes` · `--resolucao 4k,1080p` · `--codec h264\|hevc\|prores` · `--video <fonte>` · `--corrigir` · `--rapido` · `--json` · `--hook` | Confere o ambiente para as decisões da edição: ffmpeg 5+ e os codificadores e filtros que elas pedem (`libx265`, `prores_ks`, `zscale`), Node 22+, motor Remotion e navegador, CLI do HyperFrames, skills de apoio (`/remotion-best-practices`, `/hyperframes`), ElevenLabs, fontes, disco e memória para 4K. `--corrigir` instala o que é seguro instalar sozinho; o resto vira comando. Resultado em `~/.neuro-mv-edit/verificacao.json`. `--hook` é a saída do SessionStart do plugin |
| `exportacao` | `analisar <vídeo> [--plataforma <id>] [--quadro <png>] [--json]` · `opcoes [--json]` | O que a fonte rende (resolução útil no enquadramento da rede, fps, codec, HDR, áudio) e a recomendação: a maior resolução sem ampliar. `--quadro` grava um quadro nas coordenadas da composição, para medir o `--head-y` |
| `mcp` | — | Como ligar o ElevenLabs: plugin (só autorizar em `/mcp`), skill no Claude Code ou outros agentes |
| `info` | — | Perfis, temas e estilos, os da skill e os seus |
| `version` | — | A versão do pacote |
| `help` | — | A ajuda resumida |

---

## Biblioteca: perfis, temas e estilos

Os itens que você cria ficam em `~/.neuro-mv-edit/{perfis,temas,estilos}/`. Para mudar a pasta, use `NEURO_HOME`.
- Eles sobrevivem às atualizações.
- Um item seu com o mesmo id de um preset passa a valer no lugar do preset.
- Os presets da skill (`presets/*.json`) não são editados: `editar` num preset cria a sua versão.

### Subcomandos

| Subcomando | Apelido | `perfil` | `tema` | `estilo` |
|---|---|---|---|---|
| `listar` | `ls` | ✓ | ✓ | ✓ |
| `mostrar <id>` | `show` | ✓ | ✓ | ✓ |
| `novo` | `new` | ✓ | ✓ | ✓ |
| `editar <id>` | `edit` | ✓ | ✓ | ✓ |
| `remover <id> [--yes]` | `rm` | ✓ | ✓ | ✓ |
| `exportar [ids] [--saida f.json]` | — | ✓ | | |
| `importar <f.json> [--sobrescrever]` | — | ✓ | | |
| `preview <id>` | `previa`, `prévia` | | ✓ | |

`perfil`, `tema` ou `estilo` sem subcomando mostra a ajuda e a lista.

### Com e sem terminal

| Caso | Num terminal | Sem terminal (agente, CI) |
|---|---|---|
| `perfil novo` | Assistente | `--json <arquivo>` ou ao menos `--id` e `--nome`. O resto vem de `--base`, por padrão `template_novo_perfil` |
| `perfil editar <id>` | Assistente com os valores atuais | `--json <arquivo>` só com o que muda, ou opções (ex.: `--tema x`). O `<id>` vira a base e o id salvo |
| `tema novo` / `estilo novo` | Assistente | Só `--json <arquivo>`, com `"base": "<id>"` e o que muda |
| `tema editar <id>` / `estilo editar <id>` | Assistente | Só `--json <arquivo>`. O `<id>` vira a base e o id salvo |
| `remover <id>` | Pede confirmação | Exige `--yes` |

O JSON é mesclado por dentro da base: em `colors`, `fonts`, `typography`, `strict_rules` e outros, só o campo citado muda. Tudo é validado antes de salvar.

### Opções de `perfil novo` e `perfil editar`

| Opção | Campo do perfil | Valores |
|---|---|---|
| `--json <arquivo>` | todos | JSON com `"base"` opcional; os outros campos substituem os da base |
| `--base <id>` | perfil de partida | qualquer perfil (padrão `template_novo_perfil`) |
| `--id <id>` | `id` | minúsculas, números e `_` |
| `--nome "<nome>"` | `name` | texto |
| `--handle @x` | `handle` | texto |
| `--cargo "<cargo>"` | `role` | texto |
| `--segmento <id>` | `segment` | `juridico_agro`, `juridico_tributario`, `institucional_juridico`, `automotivo_crm_vendas`, `educacao_escolar_bilingue`, `negocios_vendas`, `saude`, `tecnologia`, `geral_creator` |
| `--compliance <id>` | `compliance_framework` | `oab_provimento_205_2021`, `educacao_eca_lgpd`, `saude_cfm_publicidade`, `general_creator_retention` |
| `--tema <id>` | `theme_default` | um tema (`tema listar`) |
| `--estilo <id>` | `estilo_padrao` | um estilo (`estilo listar`) ou `nenhum` |
| `--plataforma <id>` | `platform_default` | `instagram_reels`, `tiktok`, `youtube_shorts`, `youtube_horizontal`, `instagram_feed_portrait` |
| `--motor <id>` | `engine_default` | `remotion`, `hyperframes` |
| `--legendas sim\|nao` | `strict_rules.burned_subtitles` | `nao`, `não`, `false` ou `0` desligam; qualquer outro valor liga |
| `--fonte-legenda "<fonte peso>"` | `typography.subtitles_font` | ex.: `"Inter ExtraBold"`, `"Cal Sans SemiBold"` |
| `--cor-legenda #RRGGBB` | `typography.subtitles_color` | hex |
| `--cor-destaque #RRGGBB` | `typography.subtitles_highlight_color` | hex |
| `--palavras-chave "a, b"` | `typography.subtitles_highlight_keywords` | lista separada por vírgula |
| `--fade-final sim\|nao` | `strict_rules.final_fade_out` | como `--legendas` |
| `--tom "<texto>"` | `editorial_guidelines.tone` | texto |
| `--cta "<texto>"` | `editorial_guidelines.cta_default` | texto |
| `--artista "<texto>"` | `default_metadata.artist` | texto |
| `--copyright "<texto>"` | `default_metadata.copyright` | texto |

Exemplos:

```bash
# novo perfil só com opções
neuro-mv-edit perfil novo --id dra_ana --nome "Dra. Ana Lima" --segmento saude --compliance saude_cfm_publicidade \
  --tema clean_paper --estilo educativo_claro --plataforma instagram_reels --motor remotion

# editar: o JSON só tem o que muda
echo '{"handle": "@dra.ana", "typography": {"subtitles_highlight_keywords": ["SONO", "ROTINA"]}}' > muda.json
neuro-mv-edit perfil editar dra_ana --json muda.json

# levar para outra máquina: os perfis citados e os temas e estilos SEUS que eles usam
# (sem ids, exporta toda a sua biblioteca; os presets da skill já existem lá)
neuro-mv-edit perfil exportar dra_ana exemplo_juridico --saida equipe.json
neuro-mv-edit perfil importar equipe.json --sobrescrever
```

Sem `--saida`, o `exportar` grava `neuro-biblioteca-AAAA-MM-DD.json` na pasta atual.

### Temas

```bash
neuro-mv-edit tema preview <id> [--perfil <id>] [--estilo <id>] [--plataforma <id>] [--sem-abrir]
neuro-mv-edit tema novo --json tema.json        # {"base": "noticia_impacto", "id": "meu_tema", "name": "Meu tema", "colors": {...}}
```

- A prévia é um HTML com os 7 cartões e uma legenda, nas fontes e cores do tema, em `~/.neuro-mv-edit/previews/<tema>/`.
- Sem `--sem-abrir`, ela abre no navegador.

**Os 8 temas da skill**

| Tipo | Ids |
|---|---|
| 8 presets | `noticia_impacto`, `editorial_noir`, `clean_paper`, `tech_neon`, `corporativo_azul`, `educacao_vibrante`, `luxo_minimal`, `agro_terra` |
| Seus | Os temas de marca ficam na sua biblioteca (`~/.neuro-mv-edit/temas/`): `tema novo`, ou vêm junto num `perfil importar` |

Fontes que podem ser usadas nos temas: Big Shoulders Display, Fraunces, Inter, Cal Sans, Instrument Serif, DM Sans, Plus Jakarta Sans e Space Grotesk.

### Estilos de edição

| Id | Ritmo |
|---|---|
| `dinamico_reels` | Cortes secos nos respiros, legenda de 3 palavras, punch-ins marcados |
| `editorial_sobrio` | Pausas preservadas, câmera quase parada, SFX discretos |
| `educativo_claro` | Legenda karaokê, respiros naturais, cenas didáticas mais longas |
| `comercial_acelerado` | Cortes muito secos, câmera forte, SFX presentes |
| `documental_calmo` | Pausas longas, legenda de até 5 palavras, quase sem punch-in |

**O que um estilo define**
- **Corte:** `corte.preset` (`natural` ou `tight`) e `corte.limiar_ms`.
- **Legendas:** `legendas.animacao` (`pop` ou `karaoke`) e `legendas.palavras_por_linha`.
- **Câmera:** `camera.punch_in` e `camera.zoom_sutil`.
- **Som:** `sfx.ganho_db` e `trilha.volume`.

---

## Projetos: `projeto`

```bash
neuro-mv-edit projeto <subcomando> [-P <pasta>] [opções] [-- opções do motor]
```

- **`-P` / `--project`:** a pasta do projeto. Padrão: a pasta atual. Vale para todos os subcomandos, menos `init` (que usa `--out`) e `motor`.
- **Checkpoint automático:** toda ação que muda o projeto termina com um checkpoint git local. Só os arquivos de texto entram; mídia e renders ficam fora.
- **Opções extras para o motor** vão depois de `--`. Exemplo: `projeto snapshot -P x -- --at 3.5`. Sem o `--`, o argparse recusa a opção (`unrecognized arguments`).

| Subcomando | Opções (padrão) | O que faz |
|---|---|---|
| `init` | `--profile/-p <id>` · `--video/-v <arquivo>` · `--out/-o <pasta>` (obrigatórios); `--engine/-e remotion\|hyperframes`; `--platform <id>`; `--theme <id>`; `--estilo <id>`; `--head-y <px>`; `--head-x <px>`; `--layout split_lateral\|lower_third` (16:9); `--no-grade`; `--reencode`; `--force`; **exportação:** `--resolucao 4k,1440p,1080p,720p,original` (várias separadas por vírgula; padrão `1080p`), `--codec h264\|hevc\|prores` (`h264`), `--fps original\|24\|25\|30\|50\|60` (`original`), `--qualidade alta\|maxima` (`alta`) | Cria o projeto: mezanino CFR na resolução útil da fonte (até a maior saída, sem ampliar), tema, layout e `neuro.json` (com o bloco `export`). O motor vem de `--engine`, senão de `NEURO_ENGINE`, senão do `engine_default` do perfil, senão `remotion` |
| `transcrever` | `--model` (`small`) · `--language` (`pt`) | Transcrição por palavra da fonte inteira (Whisper via `hyperframes transcribe`). Use `--model medium` se houver música alta |
| `legendas` | `--apply-glossary` · `--fix "errado=certo"` (repetível) · `--learn` · `--style pop\|karaoke` · `--transcript <arquivo>` · `--force-burn` | Corrige o transcript e gera as legendas do perfil (com SRT). O `--learn` grava os pares do `--fix` na sua memória |
| `cortar` | `--preset natural\|tight` · `--limiar-ms N` · `--remover a-b` · `--manter a-b` (repetíveis, segundos da fonte) · `--sem-silencio` · `--sem-claquete` · `--nenhum` · `--dry-run` · `--verbose` | Decupagem automática → `edl.json`. Um buraco que o `silencedetect` não confirma nunca é cortado. O `--nenhum` desfaz todos os cortes |
| `build` | `--force` · `--force-burn` | Gera o projeto do motor a partir de `edl.json` + `cues.json`. Sem `--force`, preserva as camadas editadas no Studio |
| `estudio` (`studio`) | `--parar` · `--sem-navegador` · `--porta N` · extras do HyperFrames depois de `--` (padrão `--background`) | Abre o Remotion Studio (porta livre a partir de 3000) e liga o vigia, que sincroniza e faz checkpoint. No HyperFrames, abre o `hyperframes preview` |
| `sincronizar` (`sync`) | — | (Remotion) Leva as edições do Studio para `edl.json` e `cues.json`. Rode antes de editar esses arquivos com o Studio aberto |
| `check` | `--json` · extras depois de `--` | Validações. Remotion: avisos do build + bundle. HyperFrames: `hyperframes check` com a faixa de legenda da plataforma |
| `snapshot` | `--escala` (`0.5`) · `--quadro N` (repetível, Remotion) · extras depois de `--` | PNG de cada cena e de início, meio e fim. No HyperFrames, `--review` é o padrão |
| `exportacao` | `--resolucao` · `--codec` · `--qualidade` · `--mezanino` · `--json` | Mostra ou muda a decisão de exportação. `--mezanino` refaz `assets/base.mp4` da fonte original na resolução útil para a maior saída (mesmos fps e duração) |
| `render` | `--quality draft\|looks\|delivery` (`delivery`) · `--resolucao` · `--codec` · `--qualidade` (sobrescrevem a decisão só neste render) · `--output/-o <arquivo>` · extras depois de `--` | Uma versão por resolução decidida, renderizada nativamente (supersampling), PNG por quadro e uma única codificação, `bt709`. A principal é `renders/<proj>_<data>.<ext>`; as outras ganham `_<resolução>` |
| `master` | `--input/-i <render>` (padrão: todas as resoluções do último render) · `--name <NOME>` · `--lufs N` · `--light` · `--network <rede>` (só informativo) | Loudness EBU R128 em 2 passagens (−14 LUFS; TP −1,5); o vídeo é copiado sem recompressão (AAC 320k no MP4, PCM 24-bit no MOV). Grava `renders/master/<NOME>_MASTER.mp4` (as outras resoluções: `<NOME>_MASTER_<res>`), a cópia leve `_MASTER_leve.mp4` (se o perfil pedir ou com `--light`) e o relatório `<NOME>_loudness.json` |
| `salvar` | `--mensagem/-m "<texto>"` | Checkpoint com mensagem. No Remotion, sincroniza o Studio antes |
| `historico` | `-n N` (`25`) | Lista os checkpoints |
| `voltar <ref>` | — | Restaura um checkpoint (faz um checkpoint antes, para dar para desfazer) |
| `status` | — | Motor, duração, cortes, Studio e último checkpoint |
| `motor [instalar\|status]` | `--force` | O mesmo que `remotion setup` / `remotion status` |

Exemplo completo (Remotion):

```bash
NP="neuro-mv-edit projeto"
$NP init        --profile exemplo_juridico --video bruto.mp4 --out projetos/cpr --head-y 560
$NP transcrever -P projetos/cpr
$NP legendas    -P projetos/cpr --apply-glossary --fix "exédulas=cédulas" --learn
$NP cortar      -P projetos/cpr --dry-run                 # confira; depois sem --dry-run
#   escreva projetos/cpr/cues.json (cenas, câmera, SFX, trilha, efeitos, B-roll)
$NP build       -P projetos/cpr
$NP estudio     -P projetos/cpr                           # Studio no navegador + vigia
$NP check       -P projetos/cpr
$NP snapshot    -P projetos/cpr                           # abra os PNGs
$NP render      -P projetos/cpr
$NP master      -P projetos/cpr --name CPR_PRAZO
$NP salvar      -P projetos/cpr -m "aprovado pelo cliente"
```

**Arquivos de um projeto**

| Arquivo | O que guarda |
|---|---|
| `neuro.json` | Configuração: perfil, motor, plataforma, faixa gráfica, loudness |
| `edl.json` | Os cortes |
| `cues.json` | Cenas, câmera, SFX, trilha, efeitos e B-roll |
| `assets/transcript.json`, `assets/transcript.fixed.json` | O transcript bruto e o corrigido |
| `dados/legendas.json`, `captions.srt` | As legendas |
| `assets/sfx/<tipo>_NN.wav` | Os efeitos sonoros |
| `remotion/` | O projeto do Remotion; camadas em `remotion/src/gerado/*.tsx` |
| `index.html`, `compositions/` | O projeto do HyperFrames |
| `renders/`, `renders/master/` | Os renders e os masters |

---

## Ponte HyperFrames: `hf`

A ponte direta com o HyperFrames, sem a porta única. Em geral, use `projeto` com `--engine hyperframes`.

```bash
neuro-mv-edit hf <subcomando> --project <pasta> [opções]
```

- **`--project` é obrigatório** em todos os subcomandos, menos o `init`. Aqui não existe `-P` nem pasta padrão.
- **Extras do `hyperframes`** vão depois de `--`.

| Subcomando | Opções |
|---|---|
| `init` | As mesmas do `projeto init`, menos `--engine` |
| `captions` | `--transcript`, `--fix` (repetível), `--apply-glossary`, `--learn`, `--style pop\|karaoke`, `--force-burn` |
| `build` | `--force`, `--force-burn` |
| `check` | `--json`, extras. Já passa `--caption-zone` com a faixa da plataforma |
| `snapshot` | extras. Usa `--review`, a menos que você passe `--at`, `--range` ou `--frames` |
| `preview` | extras |
| `render` | `--quality draft\|looks\|delivery`, `--output/-o`, extras |
| `master` | `--input/-i`, `--name`, `--lufs`, `--light`, `--network` |

---

## Motor Remotion: `remotion`

| Comando | O que faz |
|---|---|
| `remotion setup [--force]` (também `install` ou `instalar`) | Instala o motor compartilhado em `~/.neuro-mv-edit/remotion/<versão>/`: cerca de 250 MB, mais o Chrome Headless Shell. O `--force` reinstala |
| `remotion status` | A versão, os pacotes e o navegador do motor |

O motor é instalado sozinho no primeiro projeto Remotion. Cada projeto liga o próprio `node_modules` a ele, sem baixar nada de novo.

**Licença do Remotion**
- **Grátis:** pessoa física, empresas com até 3 pessoas e ONGs.
- **A partir de 4 pessoas:** é preciso a [Company License](https://www.remotion.dev/license).
- **Chave:** com `REMOTION_LICENSE_KEY` no ambiente, os renders usam a chave.
- **Sem licença:** use `--engine hyperframes`, que é Apache-2.0.

---

## Entrega: `metadata` e `organize`

### `metadata`

```bash
neuro-mv-edit metadata -i <vídeo> -p <perfil> [-t "<título>"] [-d "<descrição>"] [-j extras.json] [-o <saída>] [--sem-leve]
```

| Opção | O que faz |
|---|---|
| `--input/-i` | Vídeo de entrada, normalmente `renders/master/<NOME>_MASTER.mp4` (obrigatório) |
| `--profile/-p` | Id do perfil, da skill ou seu (obrigatório) |
| `--title/-t` | Título ou hook |
| `--description/-d` | Descrição curta |
| `--json/-j` | JSON com campos extras: `title`, `description`, `keywords`, `caption_body`, `first_comment`… |
| `--output/-o` | Vídeo de saída. Padrão: `<stem>_meta.mp4`. Igual à entrada = substitui no lugar |
| `--sem-leve` | Não aplica os metadados à cópia `_leve` |

- **Tags gravadas no MP4**, sem recompressão: `title`, `artist`, `album_artist` (o @), `comment`, `description`, `copyright`, `genre` e `date`.
- **Copy de postagem:** gera ao lado do vídeo `<vídeo>_COPY_POSTAGEM.md`, com legenda, nota do setor, hashtags e primeiro comentário. Exemplo: `X_MASTER_meta_COPY_POSTAGEM.md`.
- **Prioridade dos campos:** perfil, depois `--json`, depois as opções.

### `organize`

```bash
neuro-mv-edit organize -m <vídeo> [-n reels|tiktok|shorts|youtube|feed] [-b entregas] [-c copy.md] [-r relatorio.md] [-p previa.png] [-e arquivo ...]
```

| Opção | Padrão | O que faz |
|---|---|---|
| `--master/-m` | — (obrigatório) | O vídeo final, ex.: `X_MASTER_meta.mp4` |
| `--network/-n` | `reels` | `reels`, `tiktok`, `shorts`, `youtube` ou `feed` |
| `--base-dir/-b` | `entregas` | A pasta base |
| `--copy/-c` | o `<vídeo>_COPY_POSTAGEM.md` ao lado | A copy de postagem |
| `--report/-r` | — | O relatório de entrega |
| `--preview/-p` | — | A imagem de prévia |
| `--extra/-e` | — | Outros arquivos |

- **O que vai junto:** **copia** (não move) para `entregas/AAAA-MM/DD/<rede>/` o vídeo e, automaticamente, os arquivos do mesmo vídeo: a cópia leve, o `_loudness.json` e a copy.
- **Rodar de novo** sobre a mesma entrega não quebra nada.

---

## Variáveis de ambiente

| Variável | Efeito |
|---|---|
| `NEURO_HOME` | Pasta da biblioteca, memória, prévias e motor Remotion (padrão `~/.neuro-mv-edit`) |
| `NEURO_ENGINE` | Motor padrão do `projeto init` (`remotion` ou `hyperframes`) |
| `NEURO_NO_TTY=1`, `CI` | Força o modo sem terminal: nenhum assistente pergunta |
| `NEURO_HF_VERSION` | Versão do HyperFrames usada (padrão `0.9.19`) |
| `NEURO_REMOTION_VERSION` | Versão do motor Remotion (padrão `4.0.539`) |
| `REMOTION_LICENSE_KEY` | Chave da Company License do Remotion |
| `HYPERFRAMES_NO_TELEMETRY=1` | Desliga a telemetria do HyperFrames |
| `ELEVENLABS_API_KEY` | Só para o servidor ElevenLabs local (`uvx elevenlabs-mcp`) |
| `CLAUDE_CONFIG_DIR`, `CODEX_HOME`, `HERMES_HOME`, `XDG_CONFIG_HOME` | Pastas dos agentes, quando não são as padrão |
| `NEURO_HARNESS_HOME`, `NEURO_HARNESS_PROFILE` | Pasta do Neuro Harness (padrão `~/.neuro-harness`, ou `~/.neuro-mv-superagent` se só ela tiver o perfil) e o perfil do `dsh` (padrão `neuro`) |
| `OD_CLI`, `OD_DAEMON_URL` | Caminho do `od` e endereço do daemon do Open Design, quando a descoberta automática falha |

---

## Onde ficam os arquivos

| Pasta | Conteúdo | Atualização ou desinstalação |
|---|---|---|
| `~/.neuro-mv-edit/perfis/`, `temas/`, `estilos/` | Sua biblioteca | Mantida |
| `~/.neuro-mv-edit/memory.json` | Seus aprendizados (glossário, correções, preferências), mesclados por cima do `data/memory.json` da skill | Mantida |
| `~/.neuro-mv-edit/previews/` | As prévias de tema | Mantida |
| `~/.neuro-mv-edit/remotion/<versão>/` | O motor Remotion (~250 MB) | Mantido |
| Pasta da skill em cada agente | A skill, que é recriada a cada atualização | Substituída ou removida |

Para apagar tudo o que é seu, depois do `uninstall`: `rm -rf ~/.neuro-mv-edit`. Isso não tem volta: leva os perfis, os temas, os estilos e a memória.

---

## Códigos de saída

| Código | Quando |
|---|---|
| `0` | Deu certo |
| `1` | Erro: arquivo ausente, validação recusada, `verify` com pendências, vídeo de `organize` inexistente |
| `2` | Uso errado: opção desconhecida, falta de argumento, ou assistente sem terminal (passe opções ou `--json`) |
| `130` | Cancelado pelo usuário (Ctrl+C num assistente). Nada foi salvo |

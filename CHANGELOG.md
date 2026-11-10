# Changelog

Todas as mudanças relevantes do **Neuro MV Edit** ficam registradas aqui.
O formato segue o [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) e o projeto usa [Versionamento Semântico](https://semver.org/lang/pt-BR/):

- **MAJOR**: quebra de compatibilidade (layout do repositório, comandos do CLI, formato de perfis/temas, `cues.json`);
- **MINOR**: recurso novo compatível;
- **PATCH**: correção sem mudança de comportamento esperado.

Cada versão tem uma tag `vX.Y.Z` e uma [Release no GitHub](https://github.com/monrars1995/oneuros-mv-edit/releases); a mais recente é marcada como **Latest**. As versões anteriores à 1.10.0 foram publicadas num repositório privado; as entradas abaixo foram mantidas, sem nomes de clientes.

## [1.10.0] — 2026-11-10

### Mudado
- **Código aberto:** o repositório passa a ser público em `monrars1995/oneuros-mv-edit`. O nome do pacote, do plugin e dos comandos continua `neuro-mv-edit` (`/neuro-mv-edit:*`, `neuro-mv-edit <comando>`). `package.json`, manifestos do plugin, marketplace, `DEFAULT_REPO` do CLI e documentação apontam para o novo endereço.
- **Perfis e temas de clientes saem do repositório:** passam a um pacote privado (formato `neuro-mv-edit/biblioteca`), que o Neuro Harness instala depois do login com `neuro-mv-edit perfil importar <pacote>`. Os presets públicos ficam só com temas genéricos e o `template_novo_perfil`, que agora usa o tema `noticia_impacto`.
- **Legenda-modelo da copy por perfil:** o `metadata` lê `default_metadata.caption_template` (com `{nota}` para a nota de conformidade) e `default_metadata.first_comment` do próprio perfil, em vez de textos fixos no código. Assim um perfil importado traz a sua copy.
- **`data/memory.json`:** fica só com os glossários por segmento. Preferências aprendidas e histórico são de cada usuário (`~/.neuro-mv-edit/memory.json`).

### Adicionado
- **Perfis de demonstração** fictícios: `exemplo_juridico` (tema `editorial_noir`, estilo `editorial_sobrio`, regras da OAB, entrega dupla) e `exemplo_educacao` (tema `educacao_vibrante`, estilo `educativo_claro`, ECA + LGPD, guarda de enquadramento em dupla).

## [1.9.0] — 2026-11-09

### Adicionado
- **Exportação decidida pelo usuário antes da edição:** resolução (4K, 1440p, 1080p, 720p ou a da fonte; várias de uma vez), codec (H.264, HEVC/H.265 ou ProRes 422 HQ), fps (o da fonte, 24, 25, 30, 50 ou 60) e qualidade (alta ou máxima).
  - `projeto init --resolucao 4k,1080p --codec h264 --fps original --qualidade alta` grava a decisão em `neuro.json` → `export`;
  - `projeto exportacao` mostra ou muda a decisão; `--mezanino` refaz o vídeo base na resolução útil da fonte;
  - `projeto render --resolucao/--codec/--qualidade` sobrescreve só naquele render.
- **`neuro-mv-edit exportacao analisar <vídeo>`:** resolução útil da fonte no enquadramento da rede (um 4K horizontal rende 1215x2160 num Reels), fps, codec, bits, HDR e áudio, a recomendação (a maior resolução sem ampliar) e o disco estimado. `--quadro` grava um quadro nas coordenadas da composição para medir o `--head-y`.
- **`neuro-mv-edit verificar`** (`scripts/neuro_verificar.py`, substitui o `verify`): confere o ambiente pelas decisões da edição — ffmpeg e os codificadores/filtros que elas pedem, Node 22+, motor Remotion e navegador, CLI do HyperFrames, skills de apoio (`/remotion-best-practices`, `/hyperframes`, `/hyperframes-cli`), MCP do ElevenLabs, fontes, disco e memória para 4K. `--corrigir` instala o que é seguro instalar sozinho; `--json` para ler sem interpretar texto; resultado em `~/.neuro-mv-edit/verificacao.json`.
- **Hook SessionStart do plugin do Claude Code** (`hooks/hooks.json`): rápido e sem rede, põe na sessão o fluxo das decisões e o estado da última verificação.
- **Comandos `/neuro-mv-edit:exportar` e `/neuro-mv-edit:verificar`.** O `/neuro-mv-edit:editar` agora começa pelas decisões (uma pergunta de múltipla escolha) e pela verificação.

### Mudado
- **Nenhuma etapa reduz a qualidade da fonte:**
  - o mezanino guarda a resolução útil da fonte até a maior saída (antes era sempre reduzido para 1080x1920) e, quando precisa recodificar, usa H.264 CRF 10 `slow` (antes CRF 14 `medium`); AAC da fonte é copiado;
  - a composição continua nas coordenadas do layout (1080 no lado curto) e a resolução final sai por supersampling (Remotion `--scale`, HyperFrames `--resolution`): texto e gráficos nítidos em 4K; os cartões HyperFrames com alfa saem em 2x;
  - o render de entrega captura PNG por quadro e codifica uma vez só, com `bt709` marcado (Remotion `--color-space=bt709`); cada resolução é renderizada nativamente;
  - HEVC sai marcado `hvc1` (toca no iPhone e no QuickTime); HyperFrames em HEVC, ProRes, 1440p ou 720p passa por um intermediário ProRes 422 HQ e uma única codificação final;
  - fontes HDR (PQ/HLG do iPhone) viram SDR Rec.709 com tonemapping (`zscale`+`tonemap`) em vez de só um aviso;
  - o master masteriza todas as resoluções do último render, com AAC 320k (antes 192k) no MP4 e PCM 24-bit no MOV, e o vídeo segue copiado sem recompressão; metadados e organização da entrega levam as outras resoluções junto.

### Corrigido
- O `verify` antigo mostrava os 6 primeiros caracteres da `ELEVENLABS_API_KEY`; agora só diz se ela está configurada.

## [1.8.0] — 2026-11-08

### Adicionado
- **Plugin do DeepSeek Harness / Neuro Harness (`plugins/dsh/`).** O pacote inteiro vira um plugin `dsh`:
  - o `package.json` declara o manifesto `dsh` (`bundle.patch` → `plugins/dsh/cordis.patch.yml`, `manifestVersion: 1`) e `exports["."]` → `plugins/dsh/index.js`. O `bin` e o `npx github:` continuam iguais;
  - **skill:** um provedor no `ctx.skills` lê o `skills/neuro-mv-edit/SKILL.md` (frontmatter → nome, descrição e invocação; corpo sem o frontmatter), com `source: "bundled"`, `rank: 600` (o `BUNDLED_SKILL_RANK` dos provedores empacotados do Harness) e `resourceBase` na pasta da skill, para os caminhos relativos resolverem;
  - **PATH:** enquanto o plugin está ativo, o `bin/` do pacote fica na frente do PATH, e o comando `neuro-mv-edit` funciona em toda sessão, como no plugin do Claude Code. Ao desligar o plugin, a entrada sai do PATH;
  - sem dependências.
- **Agente `neuro-harness` no instalador** (apelidos `dsh`, `deepseek-harness`):
  - **detecção:** o perfil `~/.neuro-harness/dsh/profiles/neuro` (ou `~/.neuro-mv-superagent/…`, o nome antigo). `NEURO_HARNESS_HOME` e `NEURO_HARNESS_PROFILE` mudam a pasta e o perfil;
  - **modo plugin (padrão):** `dsh plugin --profile <perfil> add <origem>` com o `dsh` do runtime do Harness e `DSH_HOME=<pasta>/dsh`. A origem é `github:monrars1995/oneuros-mv-edit#vX.Y.Z` numa release e `link:<clone>` num clone git;
  - **uninstall:** `dsh plugin --profile <perfil> remove neuro-mv-edit`;
  - **status:** a versão instalada no perfil (`node_modules/neuro-mv-edit/package.json`), com `(link)` e `DESATIVADO` quando for o caso. O `--deep` mostra a versão do `dsh`, a origem e se uma cópia da skill em `~/.agents/skills` ou `$DSH_HOME/skills`, de outra versão, vence a do plugin;
  - **modo skill:** o Harness lê `~/.agents/skills`. Essa pasta é compartilhada com o Codex: o `neuro-harness` nunca a apaga, nem ao instalar o plugin, nem no `uninstall`. A cópia em `$DSH_HOME/skills`, que só duplicaria a skill, sai;
  - `--dry-run`, `--mode neuro-harness=skill` e o assistente `setup` (pergunta o modo) valem como nos outros agentes.
- **`bin/neuro-mv-edit.cmd`:** o comando no Windows, ao lado do script `sh`.

### Documentação
- README: Neuro Harness na tabela de agentes, na instalação (inclusive manual), na atualização, na desinstalação e em "Usando em outros agentes". Os perfis do autor (GitHub e Instagram) em "Autor e licença".
- `docs/COMANDOS.md`: o id `neuro-harness`, as variáveis `NEURO_HARNESS_HOME` e `NEURO_HARNESS_PROFILE`, e o que `uninstall` e `status --deep` fazem nele.
- `SKILL.md`: o plugin do Neuro Harness na instalação e no "Como chamar o CLI".

## [1.7.2] — 2026-11-07

### Documentação
- **README reorganizado** para o estado atual do plugin:
  - **Início rápido:** do zero à primeira edição em três comandos.
  - **Uso no Claude Code:**
    - os 7 comandos `/neuro-mv-edit:*`, com argumentos e exemplos;
    - como o `/editar` trabalha e onde ele para para aprovação;
    - os subagentes e o que eles devolvem;
    - o `neuro-mv-edit` no PATH e a autorização do ElevenLabs em `/mcp`;
    - a diferença entre `/neuro-mv-edit:status`/`setup` e o `status`/`setup` do CLI.
  - **Uso nos outros agentes:** Codex (`$neuro-mv-edit`), Hermes, OpenCode, Open Design, Gemini e Cursor.
  - **Tabelas com ids:** os de `--agent`, `--platform` e das redes do `organize`, e os perfis, temas e estilos que vêm com a skill.
  - **Seções novas:**
    - compliance por segmento;
    - atualização e desinstalação corrigidas (o `marketplace update` sozinho não muda de versão);
    - solução de problemas.
  - **Uma tabela de requisitos só, corrigida:** FFmpeg 5+, git e Chrome.
- **Nova referência completa, `docs/COMANDOS.md`:** cada comando e opção conferidos com o código, incluindo:
  - os apelidos;
  - os valores aceitos e padrão;
  - o separador `--` para opções do motor;
  - o que muda com e sem terminal;
  - as variáveis de ambiente, onde ficam os arquivos e os códigos de saída.
- **Correções de texto que estavam erradas:**
  - `check --caption-zone` e `snapshot --review` (eram rejeitados; o `check` já aplica a faixa de legenda sozinho);
  - as tags gravadas no MP4 e o nome real da copy (`<vídeo>_COPY_POSTAGEM.md`);
  - o caminho da memória do usuário (`~/.neuro-mv-edit/memory.json`);
  - a entrega copia (não move) os arquivos;
  - links `file://` que apontavam para uma máquina específica.
- **SKILL.md e comandos do plugin** alinhados com a referência. O `/neuro-mv-edit:setup` e o `/neuro-mv-edit:status` agora dizem que não são o instalador nem o status da instalação.

### Corrigido
- **`perfil editar <id> --json <arquivo>`** ignorava o `<id>` e partia do modelo em branco. Agora o `<id>` vira a base e o id salvo; o mesmo vale para `tema editar` e `estilo editar`.
- **`perfil editar <id>` sem terminal** exigia `--id` e `--nome`. Agora aceita só as opções que mudam (ex.: `--tema x`).
- **Editar um perfil sem estilo** escolhia o primeiro estilo da lista sozinho. Agora ele continua sem estilo.
- **Dois perfis usavam ids de compliance que não existem:** o perfil automotivo passa a `general_creator_retention` e o perfil de educação passa a `educacao_eca_lgpd`. Antes, editar esses perfis trocava as regras para OAB.
- **`neuro-mv-edit mcp`** mandava quem usa o plugin rodar `claude mcp add`. Agora separa três casos (plugin, skill e outros agentes) e usa o nome `elevenlabs`, também no `mcp-config.json`.
- **Ajuda do CLI:**
  - `--plugin` (já é o padrão), `--skills-only` e o padrão de `--od-source` corrigidos;
  - os exemplos fixados na tag da versão.
- **`package.json`:** `engines.node` passa a `>=22`, como o HyperFrames exige.
- **`LICENSE` (MIT):** o arquivo foi adicionado, como o README e o `package.json` já indicavam.

## [1.7.1] — 2026-11-07

### Corrigido
- **Atualização do plugin do Claude Code a partir de instalações antigas.** Quem já tinha o marketplace `neuro-mv-edit` sem versão travada (registrado em `extraKnownMarketplaces` no `~/.claude/settings.json` por instalações anteriores) recebia "its source doesn't match its extraKnownMarketplaces entry", e o plugin não instalava.
  - Agora, quando o `marketplace add` não consegue reapontar a origem, o instalador remove o marketplace antigo, adiciona de novo pela tag da versão e instala o plugin.

## [1.7.0] — 2026-11-07

### Alterado
- **Plugin por padrão.** O neuro-mv-edit agora é entregue como plugin em todo agente que tem sistema de plugin: Claude Code e Hermes passam a `plugin` (OpenCode e Open Design já eram).
  - Ao virar plugin, a cópia avulsa da skill daquele agente sai, para não carregar duas vezes.
  - Ao voltar para skill (`--mode <agente>=skill`), o plugin é desinstalado. Antes, as duas cópias ficavam carregadas.
  - No assistente `setup`, "Plugin (recomendado)" é a primeira opção.
- **Versão travada.**
  - **Claude Code:** o marketplace aponta para a tag da release (`monrars1995/oneuros-mv-edit#v<versão>`); a partir de um clone git, para a pasta local. Um marketplace existente com outra origem é reapontado.
  - **Hermes:** instala pelo commit da tag (`--ref <SHA>`) com `--yes-deps`.
  - O estado vem de `claude plugin list --json` / `marketplace list --json`, e o instalador confere se a versão instalada é a do pacote e se o plugin está ativo.
- **`status`:** mostra Claude Code e Hermes em modo plugin com a versão. O `--deep` mostra quantos comandos, subagentes e servidores MCP o plugin carregou e avisa quando um agente ainda está como skill.
- **Estrutura:**
  - o código do instalador foi de `bin/` para `cli/` (o `npx` continua igual);
  - a versão do plugin fica só no `.claude-plugin/plugin.json` (sai da entrada do `marketplace.json`).

### Adicionado
- **Conteúdo do plugin do Claude Code**, além da skill:
  - **comandos** `/neuro-mv-edit:editar` (fluxo completo, com aprovações), `perfil`, `tema`, `estudio`, `entregar`, `setup` e `status`;
  - **subagentes** `neuro-mv-edit:revisor` (QA do checklist de entrega e das regras do setor) e `neuro-mv-edit:decupador` (tomadas repetidas e claquetes → `--remover`/`--manter`);
  - **ElevenLabs MCP** (`.mcp.json`, HTTP com OAuth; com o mesmo endereço já configurado, o Claude Code mantém uma conexão só);
  - **comando `neuro-mv-edit` no PATH** das sessões (`bin/neuro-mv-edit`), para o agente usar o CLI sem `npx` nem rede.
- Ícone do plugin, política de privacidade (`privacyPolicyUrl` e a seção "Privacidade" no README) e a seção "O que o plugin do Claude Code traz".

### Observação
- Por ter executáveis (`bin/`), o plugin não instala no claude.ai nem no Cowork. Ele vale para o Claude Code no terminal, no app desktop (aba Code) e no VS Code.

## [1.6.0] — 2026-11-07

### Adicionado
- **Instalação guiada (`setup`).** Rodar `npx github:monrars1995/oneuros-mv-edit` sem comando, num terminal, abre um assistente:
  - escolha dos agentes (harness) da máquina, com os detectados marcados e a versão já instalada;
  - modo por agente: skill ou plugin no Claude Code, OpenCode e Hermes;
  - extras: skills do HyperFrames, motor Remotion, verificação de ambiente e fontes, guia do ElevenLabs;
  - opção de criar o primeiro perfil, com resumo e confirmação no fim.
  - `setup --yes` usa os padrões sem perguntar. `install --mode <agente>=plugin|skill` define o modo por agente.
- **Biblioteca de perfis, temas e estilos** em `~/.neuro-mv-edit/{perfis,temas,estilos}/` (`NEURO_HOME` muda a raiz). Ela sobrevive às atualizações da skill e se sobrepõe aos presets de mesmo id.
  - Comandos `perfil`, `tema` e `estilo` com `listar`, `mostrar`, `novo`, `editar` e `remover`.
  - `perfil exportar`/`importar` levam perfis (e os temas e estilos que usam) para outra máquina ou equipe.
  - Assistentes interativos. Para agentes e CI, formas não interativas por opções ou `--json`: o JSON herda de `"base"` com mescla profunda e é validado antes de salvar.
- **8 temas prontos:** `noticia_impacto`, `editorial_noir`, `clean_paper`, `tech_neon`, `corporativo_azul`, `educacao_vibrante`, `luxo_minimal`, `agro_terra`.
- **5 estilos de edição** (`presets/estilos.json`): `dinamico_reels`, `editorial_sobrio`, `educativo_claro`, `comercial_acelerado`, `documental_calmo`.
  - Cada estilo define ritmo de corte e limiar, legenda (pop/karaokê, palavras por linha), intensidade da câmera, ajuste dos SFX e volume da trilha.
  - Perfis apontam para um com `estilo_padrao`; projetos trocam com `projeto init --estilo`.
  - `projeto cortar` ganhou `--limiar-ms`.
- **Prévia de tema:** `tema preview <id> [--perfil] [--estilo] [--plataforma]` (`scripts/neuro_preview.py`) gera um HTML com os 7 cartões e uma legenda, nas fontes e cores do tema, com pose final, botão "Animar" e faixa gráfica.
- **Memória do usuário** em `~/.neuro-mv-edit/memory.json`, mesclada sobre a da skill.

### Corrigido
- **Glossário duplicando palavras.** O `--apply-glossary` duplicava palavras nas legendas ("CRM automotivo automotivo", "do STF do STF") e aplicava glossários de outros segmentos ("célula" → "cédula" no perfil da escola).
  - Cada glossário agora tem um mapa `legendas`, só de grafia, e uma lista de segmentos.
  - Uma troca não duplica quando o termo completo já foi falado.
  - `--learn` grava só as correções dadas com `--fix`.
- **Memória apagada na reinstalação.** A memória "persistente" ficava dentro da skill e era apagada a cada reinstalação. Agora os aprendizados ficam em `~/.neuro-mv-edit/memory.json`.
- **`inject_metadata.py`:**
  - aceitava perfil inexistente em silêncio, com a legenda do agro e o aviso da OAB;
  - trocava os campos do perfil pelo `--json` em vez de mesclar;
  - saía com 0 mesmo com o ffmpeg falhando, e o `-o` igual à entrada não funcionava;
  - descartava as tags `year` e `author`.
  - Agora: perfil obrigatório (inclusive os da biblioteca), mescla perfil < JSON < opções, escrita atômica, `date`, copy por vídeo (`<vídeo>_COPY_POSTAGEM.md`) e cópia leve com metadados.
- **`organize_deliveries.py`:**
  - criava a pasta e dizia "Entrega finalizada" sem o vídeo;
  - quebrava ao rodar de novo sobre a mesma entrega;
  - não levava a cópia leve nem o relatório de loudness.
- **Montagem da fala e do vídeo cortado:** usava `-/filter_complex`, que só existe a partir do ffmpeg 7. O grafo agora vai na linha de comando.
- **CLI:** `metadata`, `organize` e `verify` saíam sempre com 0. O `verify-env.py` agora sai com 1 quando falta ferramenta, confere a versão do ffmpeg e, no Linux, instala as fontes em `~/.local/share/fonts` em vez da pasta temporária do npx.
- **Motor Remotion:**
  - o `projeto init` sobrescrevia o `CLAUDE.md`/`AGENTS.md` do usuário (agora acrescenta um bloco);
  - um re-init com outra plataforma deixava o `Root.tsx` com o tamanho antigo;
  - cenas com id fora do padrão ("Hook_1") não sincronizavam do Studio.
- **Perfis:** o loudness e o punch-in passam a vir do perfil (`audio_mix.target_lufs`, `zoom_closed_factor`).
- **Comandos:** `master` sem render dava um erro confuso; `estudio --parar` num projeto HyperFrames abria o preview.
- **Textos desatualizados:** a instalação e o `package.json` ainda chamavam o HyperFrames de motor padrão; o `info` não listava temas.

## [1.5.0] — 2026-11-07

### Adicionado
- **Motor Remotion completo** (`--engine remotion`, novo padrão), fixado em Remotion 4.0.539 com lock.
  - Instalado uma vez em `~/.neuro-mv-edit/remotion/<versão>` (Chrome Headless Shell incluso) e ligado por symlink em cada projeto.
  - Camadas editáveis no **Remotion Studio**: `Cortes`, `Camera`, `Cenas`, `Trilhas`, `Efeitos`, `Broll` e `Legendas`.
  - Os 7 templates de cena saem do mesmo gerador nos dois motores e rodam no Remotion via `@remotion/gsap`.
- **Porta única `projeto`** (`scripts/neuro_project.py`): `init --engine`, `transcrever`, `legendas`, `cortar`, `build`, `estudio`, `sincronizar`, `check`, `snapshot`, `render`, `master`, `salvar`, `historico`, `voltar`, `status`, `motor`.
- **Interface web aberta:** `projeto estudio` sobe o Studio em segundo plano e abre o navegador. Um vigia leva as edições do Studio para `edl.json`/`cues.json` e faz checkpoint.
- **Projeto sempre salvo:**
  - Checkpoints git locais (só texto) a cada comando, com `historico` e `voltar <ref>`.
  - O `build` nunca sobrescreve edição do Studio que não sabe representar (compara a árvore sintática via Babel).
  - Conflito Studio × JSON é detectado e explicado.
- **Decupagem automática** (`projeto cortar`, `scripts/neuro_edl.py`):
  - Os cortes vêm dos buracos do Whisper confirmados pelo `silencedetect`, com o ritmo do perfil e as deixas de claquete da memória.
  - Presets `natural`/`tight`, mais `--remover`/`--manter` para a decupagem narrativa, e `edl.json` editável.
  - Cenas, câmera e legendas são remapeadas pelo tempo da fonte quando o corte muda.
- **Remotion + HyperFrames por cena:** `"motor": "hyperframes"` ou `"html": "<composição>"` renderiza a cena pelo HyperFrames em ProRes 4444 com alfa (em cache) e a coloca na timeline do Remotion.
- **`cues.json`:** `efeitos` (flash, dip), `broll` e `music.ducking`.
- **CLI:** `projeto` (alias `p`), `remotion setup|status`, `install --remotion`.
- `references/remotion/BRIDGE.md` e o template `references/remotion-project/`.

### Alterado
- **Fala:** montada pelo ffmpeg a partir do EDL, com precisão de amostra e fades nas emendas, sem deriva de sincronia.
- **Ducking da trilha:** o `master` prometia ducking que não existia. Agora a trilha é abaixada sob a fala por sidechain (`sidechaincompress`), nos dois motores.
- **Motor HyperFrames:** ganhou o mesmo corte automático; o ffmpeg monta `assets/base_cortado.mp4`.
- **Transcript:** fica sempre no tempo da fonte (mezanino), e as legendas são remapeadas pelos cortes. Novo `dados/legendas.json`.
- **`verify-env.py`:** confere de verdade o motor Remotion (instalação, versões, navegador) e mostra o aviso de licença.
- **SKILL.md §11** reescrita: escolha de motor, Studio, sincronização, combinação por cena, papel do ffmpeg e licença.

### Corrigido
- Rodar `captions` depois de um `build` travava o `build` seguinte, que confundia a legenda regerada com edição no Studio.

### Removido
- `references/remotion-template/`, o overlay legado sem `entry.ts`. Substituído pelo projeto Remotion completo.

## [1.4.1] — 2026-11-07

### Corrigido
- **Open Design com origem no GitHub:** o instalador agora confere se o repositório responde à API pública **antes** de remover o plugin instalado. Se der 404 (repositório privado), ele para sem alterar nada e indica `--od-source <clone>/skills/neuro-mv-edit`. Antes, a remoção vinha primeiro e uma busca com falha deixava o Open Design sem o plugin.
- **README:** documenta que o repositório é privado. Os métodos que clonam pelo git (`npx github:…`, marketplace do Claude Code, `hermes plugins install`, `npx skills add`) exigem acesso. O Open Design é instalado a partir da pasta local.

### Adicionado
- `bin/version.js` (`npm run version:check` / `npm run version:set <x.y.z>`): uma única versão gravada nos 12 marcadores (pacote, manifestos dos plugins, SKILL.md, README, CLI, memória).
- Comando `version` no CLI (`npx github:monrars1995/oneuros-mv-edit version`).
- Este CHANGELOG e as seções "Atualização" e "Versionamento e releases" no README.

## [1.4.0] — 2026-11-07

### Adicionado
- **Plugins nativos:**
  - Claude Code: `.claude-plugin/plugin.json` + `marketplace.json`.
  - OpenCode V2: `plugins/opencode/server.js`, que registra a skill via `ctx.skill.transform`.
  - Hermes: `plugin.json` no formato Agent Plugins v1.
  - Open Design: `skills/neuro-mv-edit/open-design.json`.
- **Instalador multi-agente** (`bin/agents.js`), com os caminhos conferidos na fonte de cada agente: Claude Code, Codex, OpenCode, Hermes, Open Design, Gemini CLI, Antigravity, Antigravity CLI, Cursor e a pasta universal `~/.agents/skills`.
- **Comandos novos:** `uninstall`, `status [--deep]` e `agents`. Opções novas: `--agent`, `--plugin`, `--skills-only`, `--link`, `--dry-run`, `--target` e `--od-source`.
- **Open Design:** descoberta automática da porta efêmera do daemon do app desktop.
- **Validação antes de instalar:** limites de `name`/`description` de Codex, OpenCode e Hermes, YAML estrito e as frases bloqueadas pelo filtro do Hermes.

### Alterado
- **Layout do repositório:** a skill passou para `skills/neuro-mv-edit/`, no layout padrão de repositório de plugins (histórico preservado com `git mv`).
- **Codex:** usa só `~/.agents/skills`, porque uma cópia também em `~/.codex/skills` aparece duplicada na lista dele.
- **Antigravity:** a instalação segue o link de `~/.gemini/antigravity/skills` para `~/.gemini/config/skills`.

### Corrigido
- **`SKILL.md`:** a `description` não estava entre aspas e continha `: `. Parsers YAML estritos (Codex, OpenCode, Hermes) ignoravam a skill em silêncio.
- **Instruções de `npx`:** o pacote nunca esteve no npm, então `npx neuro-mv-edit` não funcionava. O correto é `npx github:monrars1995/oneuros-mv-edit`.
- **README:** removido um caractere invisível (ZWJ) que o scanner de segurança do Hermes barrava.

## [1.3.0] — 2026-11-06

### Adicionado
- **HyperFrames** (HeyGen) como motor de render padrão; o Remotion passa a ser o motor legado. A skill usa as skills oficiais `/hyperframes`, `/hyperframes-cli`, `/hyperframes-registry` e `/media-use`.
- **`scripts/hf_project.py`:** `init`, `captions`, `build`, `check`, `snapshot`, `preview`, `render` e `master`.
  - Tokens de tema, perfil e plataforma e fontes embutidas via `@font-face`.
  - 7 templates de cena: `hook`, `stat`, `quote`, `contrast`, `checklist`, `timeline` e `cta`.
  - Câmera num wrapper com origem na cabeça.
  - SFX alinhados para o pico cair 1 quadro depois da imagem, com takes alternados.
  - Legendas pt-BR com glossário e correções aprendidas.
  - Master EBU R128 em 2 passagens e cópia `_leve`.
- **Layouts:** 9:16 (faixa acima da cabeça), 4:5 e 16:9 (split lateral / lower third).
- **Documentação:** `references/hyperframes/BRIDGE.md`, `TECNICAS.md` e `CENAS.md`.
- **Presets:** `animations.json` ganhou equivalentes GSAP e `motion_craft_rules`; os perfis automotivo e de educação ganharam `subtitles_highlight_keywords`.
- **Verificação de ambiente:** `verify-env.py` checa Node 22+, o CLI do HyperFrames, o Chrome headless e as skills.

### Corrigido
- **`verify-env.py`:** o teste do Remotion sempre dava falso aviso, porque `npx remotion` não tem binário.

## [1.2.0] — 2026-11-06

### Adicionado
- **Perfil de educação escolar e bilíngue** e o tema correspondente.
- **Glossário fonético** educacional e bilíngue em `data/memory.json`.
- **Presets de animação:** `warm_story_card_reveal`, `pillar_badges_cascade`, `anniversary_gleam` e `enrollment_cta_pulse`.

## [1.1.0] — 2026-11-06

### Adicionado
- **Skill generalizada** para criadores e segmentos múltiplos (jurídico, automotivo/CRM, educação, negócios).
- **Perfil automotivo/CRM** com tema próprio, glossário automotivo/CRM e presets de animação comerciais.
- **Documentação e configuração:** README completo, CLI `bin/cli.js` e a configuração do ElevenLabs MCP (`mcp-config.json`).

## [1.0.0] — 2026-11-06

### Adicionado
- **Release inicial**, com dois perfis jurídicos (agro e tributário: tema escuro dourado e tema de papel editorial com 4 estados de tela e entrega dupla).
- **Motion graphics:** pipeline com Remotion.
- **Sound design** obrigatório via ElevenLabs MCP, com loudness −14 / −13,8 LUFS.
- **Scripts:** `verify-env.py`, `inject_metadata.py` e `organize_deliveries.py`.
- **Memória persistente:** `data/memory.json`.

# Biblioteca de cenas → template Neuro ou bloco do registry HyperFrames

Cada uma das 25 cenas da SKILL (§9) tem um caminho de produção. Primeiro o **template Neuro** (`cues.json → build`), que já respeita a faixa acima da cabeça, o véu, os SFX e o tempo de leitura. Quando nenhum template serve, use um **bloco do registry**: procure com `npx hyperframes catalog --query "<o visual>" --json`, instale com `npx hyperframes add <nome>` e restilize com os tokens do tema (`var(--accent)`, `var(--ink)`, `var(--font-hook)`...). Os blocos vêm em 1920×1080 ou com dimensões próprias. Reposicione o conteúdo dentro de `--gfx-*` e confira com `hf check` + `hf snapshot`.

No motor Remotion, o template Neuro é o caminho direto (o cartão roda ao vivo no Studio). Para um bloco do registry, aponte a cena para a composição com `"html": "blocos/<nome>.html"`, ou peça o template pelo runtime do HyperFrames com `"motor": "hyperframes"`: a cena é renderizada com alfa (ProRes 4444) e entra na timeline do Remotion (`references/remotion/BRIDGE.md` §6).

| # | Cena | Template Neuro (`vars`) | Bloco do registry (alternativa/extensão) | SFX | Notas de técnica |
| --- | --- | --- | --- | --- | --- |
| 1 | Gancho / provocação | `hook` (`kicker`, `headline`, `accent`, `bar`) | `headline-slam`, `ticker-takeover` | whoosh + pop + thud | entra em 0,1–0,3 s; uma palavra em acento |
| 2 | Alerta de risco | `hook` (`kicker: "EM RISCO"`, `accent`) | `headline-slam` | thud | tremor de ±6 px uma vez; nada de piscar em loop |
| 3 | Artigo de lei | `quote` (`pill: "ART. 11 DA LEI 8.929/94"`, `quote`) | `line-swap` | click + swipe | confira o artigo antes de renderizar (fidelidade factual) |
| 4 | Notícia / fato | `quote` (`pill: veículo + data`, `quote: manchete`, `source`) | `news-ticker` (paisagem), `yt-comment-card` | click + swipe | veículo e data verificáveis no `source` |
| 5 | Antes × Depois | `contrast` (frase curta) | `before-after-wipe`, `comparison-split`, `split-tilt-cards` | swipe + thud | colunas lado a lado não cabem em 250 px: empilhe ou faça em duas cenas |
| 6 | "X não é Y, é Z" | `contrast` (`wrong`, `right`, `right_at`) | `text-state-swap`, `morph-swap` | swipe + thud | o termo errado precisa ser lido antes de ser riscado (`right_at`) |
| 7 | Estatística financeira | `stat` (`value`, `prefix`, `suffix`, `pct`, `source`) | `count-up`, `mk-progress-stat`, `apple-money-count` | tick + pop | formato pt-BR (`2,3`), fonte obrigatória |
| 8 | Série histórica / safras | `stat` por ano, ou bloco | `chart-story`, `data-chart`, `animated-bar-chart`, `bar-chart-race` | pop por barra | barras sobem na ordem da fala; safra crítica em `--alert` |
| 9 | Linha do tempo processual | `timeline` (`nodes`, `node_at`) | `beat-timeline`, `flowchart-vertical` | pop por nó | o nó acende na palavra que o diz |
| 10 | Checklist de exigências | `checklist` (`items` ≤ 4, `item_at`) | `marker-checklist-card`, `success-check` | pop por item | 3 itens leem melhor que 4 na faixa |
| 11 | Três pilares | `checklist` com 3 itens, ou bloco | `grid-card-assemble` | pop × 3 | colunas x 230/540/850 só em faixa ≥ 300 px |
| 12 | Causa e efeito | `timeline` com 2 nós (`Fato → Consequência`) | `hw-arrow`, `flowchart-vertical` | swipe + thud | seta desenhada (stroke), nunca slide |
| 13 | Balança do produtor | bloco | `focus-swap` (dois pratos), `icon-morph-beat` | thud leve | sem loop de oscilação; a balança pende e para |
| 14 | Metáfora do campo | bloco | `svg-mask-reveal`, `icon-morph-beat` | whoosh | ícone real ou vetor limpo; nunca emoji como ícone |
| 15 | Definição técnica | `quote` (`pill: termo`, `quote: resumo de 1 linha`) | `titlecard-calm` | click | uma linha; o build avisa quando não cabe |
| 16 | Desmistificação (MITO) | `contrast` (`label: "MITO"`, `wrong`, `right`) | `marker-highlight` | swipe + thud | carimbo em `--alert` |
| 17 | Prazo fatal | `hook` (`bar: true`) ou `stat` (dias) | `conic-progress-ring`, `split-flap-board` | tick + thud | barra esvaziando é o único ease linear permitido |
| 18 | Documento essencial | `checklist` (requisitos) | `success-check`, `icon-morph-beat` | pop por requisito | |
| 19 | Jurisprudência STJ | `quote` (`pill: "TEMA REPETITIVO STJ"`, `quote: tese`, `source: REsp nº`) | `testimonial-proof-card` (restilizado) | click + swipe | número do recurso conferido |
| 20 | Alívio / solução | `cta` (`line` em itálico de apoio, sem `invite`) | `titlecard-lockup` | whoosh suave | véu claro; ritmo mais lento (saída 0,35 s) |
| 21 | Resumo em 3 pontos | `checklist` (`title: "RESUMO"`) | `grid-card-assemble` | pop × 3 | |
| 22 | Pergunta retórica | `hook` (`headline: "E SE O BANCO"`, `accent: "NÃO ACEITAR?"`) | `kinetic-type-swap` (roleta) | whoosh + thud | segure 0,3–0,75 s antes da resposta |
| 23 | Quebra de paradigma | `contrast` ou bloco | `icon-morph-beat` (cadeado abrindo), `iris-reveal` | click + thud | |
| 24 | Transição de bloco | sem cena: `camera` (`cut`/`zoom`) + whoosh | `flash-through-white`, `light-leak`, `editorial-flash-overlay` | whoosh | 3–5 tipos de transição por vídeo, cada um com causa |
| 25 | CTA ético (OAB) | `cta` (`label`, `line: "Muito cuidado."`, `invite: "Salve para consultar"`) | `cta-lockup` | swipe | ≥ 2 s na tela; convite a salvar/compartilhar, nunca captação |

## Cenas específicas por tipo de perfil

| Tipo de perfil | Cena | Caminho |
| --- | --- | --- |
| Editorial com estados de tela | Estado H (véu branco no topo até y=660 + card de notícia) | tema claro, como `clean_paper` (véu claro automático) + `quote`; véu à mão até y=660 se a faixa precisar |
| Editorial com estados de tela | Estado B (câmera dy −190 + card central x 195–885) | `camera: {kind: shift, dy: -190}` + bloco restilizado na metade de baixo; o degradê de papel começa em y ≥ 830 |
| Editorial com estados de tela | Estado C (papel cheio + avatar circular) | overlay `#FAFAF8` + recorte via `npx hyperframes remove-background` num wrapper `clip-path: circle()` |
| Automotivo / CRM | Funil de showroom | `timeline` (3–5 nós) ou `grid-card-assemble` com perdas em `--alert` |
| Automotivo / CRM | Velocímetro de SLA | bloco à mão (preset `sla_speedometer_needle`) + `stat` para o número |
| Educação | Card afetivo de família/série | `quote` (`pill: série`, `quote: frase do depoimento`) com tema `educacao_vibrante` ou o tema da escola; faixa y 230–490 |
| Educação | Selo de aniversário da instituição | `gloss-sweep` restilizado em `#FFE06D` |

## Legendas prontas do registry (alternativa ao `hf captions`)

`caption-pill-karaoke`, `caption-highlight`, `caption-editorial-emphasis`, `caption-weight-shift` e `caption-kinetic-slam` (`npx hyperframes catalog --tag caption-style --json`). O `hf captions` já aplica as regras do perfil (fonte, traço, âncora, palavras-chave, palavras por linha). Use um estilo do registry só quando o cliente pedir outro visual, e mantenha a âncora e a largura da faixa de legenda da plataforma.

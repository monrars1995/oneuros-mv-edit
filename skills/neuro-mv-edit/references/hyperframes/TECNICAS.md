# Técnicas de acabamento — padrão de qualidade Neuro MV Edit

Números medidos, não gosto pessoal. Base: as referências de motion, legendas, overlays, som e revisão da skill `/hyperframes` (medidas quadro a quadro nos filmes oficiais da HeyGen), cruzadas com as regras dos perfis da skill. Valem para qualquer motor (HyperFrames, Remotion, FFmpeg). Os templates de `scripts/hf_project.py` já seguem tudo o que está marcado com ✔.

---

## 1. O primeiro segundo e o ritmo vertical

- **Quadro 0 é a thumbnail e o gancho:** rosto, resultado ou uma frase forte já na tela. Nunca preto, nunca logo. O gancho começa em 0,1–0,3 s, não em 0 (em 0 parece que já estava lá). ✔
- **A mudança ou a pergunta chega no primeiro tempo** (≈ 1 s). Muita gente assiste sem som, então a imagem e a legenda carregam o gancho sozinhas.
- **Ritmo:** em vertical, planos de 1–2 s e um estímulo novo a cada 2–4 s (punch-in, cena, corte de câmera B). O payoff vem antes do swipe.
- **Respiro antes do payoff:** segure 0,3–0,75 s antes da revelação e toque o payoff em velocidade normal.
- **Cortes:** corte no quadro mais rápido de um movimento, com direção e velocidade iguais dos dois lados. Entre blocos, no máximo 1/3 das emendas como corte seco.
- **Dip cut:** escureça o quadro de saída ~40% por 3 quadros antes do corte seco, para o corte parecer intencional.
- **Densidade de cards:** um card a cada 6–8 s em vídeo de até 1 min, 8–12 s até 3 min. Um card estático "morre" depois de ~8 s. Passando de 15 s, revele em etapas (`item_at`, `node_at`). ✔ (o build avisa)

## 2. Movimento

| Papel | Ease | Duração |
| --- | --- | --- |
| Entrada / pouso | `expo.out`, `power4.out` (cauda longa) | 0,13–0,45 s |
| Câmera, inundação de cor | `power2.inOut` | 0,5–0,7 s (reenquadramento) |
| Saída, zoom-through | `power3.in` | 40–50% mais curta que a entrada ✔ |
| Overshoot (pílula, badge) | `back.out(1.4–1.7)` | 0,35–0,38 s ✔ |
| Linear | só rotação, progresso, velocidade constante | barra de prazo ✔ |

- **Chega devagar, sai limpo:** a saída é um movimento só (nunca desliza, para e sai). Entradas rápidas demais parecem glitch. Desacelerar o vídeo inteiro em ~1 s costuma resolver.
- **Sobreposição:** o próximo elemento começa quando o anterior está 30–50% feito. Tudo sequencial parece robótico; tudo junto parece barato. ✔
- **Stagger:** letras a 1 quadro (0,033 s), palavras a 0,06–0,12 s, itens de lista a 0,04–0,08 s. Itens narrados entram **na palavra que os diz**. ✔
- **Molas por amortecimento:** 1,0 nunca quica; 0,7–0,85 é premium; 0,4–0,6 é lúdico; abaixo de 0,3 vira desenho animado. Posição e escala podem quicar; **opacidade e cor nunca**.
- **Motion blur:** num movimento rápido, o pico de blur fica no quadro mais veloz, 6–12 px em texto e 15–20 px em tela cheia, só na direção do movimento. No HyperFrames: `data-motion-blur="on"` na raiz (`check` depois).
- **Título pousou, título parou:** depois de pousar ele fica imóvel, e o movimento passa para o próximo elemento, para a câmera ou para o fundo.
- **Varie a entrada dos títulos** (nunca fade + subida em todos):
  - por palavra: `blur(8px)→0` e opacidade 0→1 em 0,13–0,16 s, a cada 0,067 s ✔ (hook);
  - a linha inteira: blur 8→0 em 0,13–0,2 s ✔ (quote, cta);
  - cinza → tinta por palavra, a cada 0,07–0,1 s, sem deslocamento (legenda karaokê ✔);
  - por letra para nomes próprios (0,1 s, opacidade 0,3→1 com leve blur);
  - atrás do apresentador: título entre o vídeo e o recorte da pessoa (§4);
  - roleta: uma palavra girando opções a 0,1 s por giro.
- **Leitura:** 0,5 s + 0,3 s por palavra depois de pousar. A última linha do filme fica ≥ 2 s. Uma linha de capítulo com 1–2 palavras pode ficar 0,4 s. ✔ (o build e o `check` medem)
- **Tamanho:** título com 4–9% da altura do quadro (no Reels, 77–173 px). Frases de apoio com 2,5–4%. Uma palavra de destaque na cor de acento, e só a que carrega o sentido. ✔
- **Padrões que parecem gerados (proibidos):** loop de respiração/flutuação/pulso em título e UI; título que continua escalando depois de pousar; push lento tardio no fim da cena; bounce em UI; anel de clique; toda cena entrando igual; todo elemento com fade + slide-up.

### Transições com causa (3–5 tipos por vídeo, cada uma provocada por algo na tela)

| Transição | Construção | Equivalente no perfil |
| --- | --- | --- |
| Flash quente | branco/âmbar a 60–80% por 0,1 s, saída 0,25 s | flash quente de perfis jurídicos → registry `flash-through-white` restilizado |
| Whip | borrão horizontal/vertical de 0,13–0,3 s; o que chega pousa borrado e foca em ~0,13 s | proibido quando o perfil lista em `transitions.prohibited` |
| Blur swap | sai: opacidade→0 com ~8 px de blur em 0,13–0,2 s; entra: blur→0 em 0,13 s; o fundo não corta | saída universal das cenas ✔ |
| Inundação de cor | o objeto fica; o fundo troca de cor em ~0,4 s `power2.inOut` | estado C de perfis editoriais (papel cheio) |
| Objeto vira o mundo | card cresce além do quadro em 0,65 s, raio diminuindo; o resto borra ~15 px | abertura de bloco temático |
| Dip cut | escurece ~40% por 3 quadros e corta seco | troca de tomada sem B-roll |

Catálogo pronto: `npx hyperframes catalog --tag transition --json`.

## 3. Legendas (pt-BR)

- **Transcrição:** `npx hyperframes transcribe <arquivo> --model small --language pt`, ou `--model medium --language pt` para fala sobre música. **Nunca** o padrão `small.en`: ele traduz para inglês.
- **Leia o transcript antes de usar.** Mais de 20% de `♪`/`�` ou palavras sem sentido significa que falhou; refaça com um modelo maior. Corrija termos técnicos com `--fix`, use o glossário da memória com `--apply-glossary` e salve com `--learn`. ✔
- **Alucinação no silêncio final** ("Obrigado.", frase repetida): descarte palavras que começam dentro do silêncio final (fala real fica em −16 a −26 dB; o silêncio, abaixo de −35 dB). ✔
- **Blocos:** 2–3 palavras em vídeo de alta energia, 3–5 em conversa, 4–6 em tom calmo, limitados pelo perfil (`subtitles_max_words_per_line`). Quebre em fim de frase, numa pausa ≥ 150 ms ou no limite de palavras. ✔
- **Sem palavra-função órfã no fim do bloco** ("…bilhões em" + "cédulas"): a preposição ou o artigo desce para o bloco seguinte. ✔
- **Um bloco por vez.** Ele abre no início da primeira palavra (ou um pouco antes), fecha depois do fim da última e termina com **corte rígido** (opacidade 0 + `visibility: hidden`), senão um bloco velho fica preso na tela. ✔
- **Anime o bloco ou as palavras, não os dois:** as opacidades se multiplicam e piscam. No karaokê, o bloco entra e as palavras vão de 45% a 100% conforme são ditas. ✔
- **Posição:** container absoluto com a largura da faixa e texto centralizado (nunca `left: 50%; transform: translateX(-50%)`, que corta nas bordas). Use `overflow: visible`. No Reels, o centro em x ≈ 478 desvia do trilho de botões à direita. ✔
- **Sobre vídeo:** escolha pelo brilho atrás do texto (0–255). Abaixo de 60, `screen`; de 60 a 180, `overlay`; acima de 180, cor opaca normal com véu de 30–40% **do tamanho do texto**, nunca uma faixa de largura total.
- **O vídeo já tem legenda queimada em algum trecho?** Gere uma folha de contato a 1 fps antes de posicionar.
- **Destaques:** as palavras-chave do perfil (`subtitles_highlight_keywords`) e os números (`subtitles_highlight_numbers`) ficam na cor de destaque. Só o que carrega o sentido. ✔

## 4. Cards sobre o apresentador

- **O rosto nunca fica sob um card.** No 9:16 da skill, gráfico só acima da cabeça. Os layouts de tela dividida do HyperFrames (vídeo em 0,960 1080×960, card na metade de baixo) servem só para estados de tela como B/C (`screen_states` do perfil).
- **Tipo em retrato:** paisagem × 1,3 (títulos × 1,35, números × 1,4). Padding de 24–36 px, não de 40–64 px.
- **Reenquadre o vídeo** (0,5–0,7 s) só no vão entre cards, movendo um wrapper, nunca `left/top/width/height`. ✔
- **Vidro sobre imagem clara vira branco sobre branco:** coloque um véu escuro atrás (`rgba(0,0,0,.55)` no topo, `.72` embaixo) e uma base de vidro escura (`rgba(15,16,22,.78)` + `backdrop-filter: blur(22px)`).
- **Véu da faixa gráfica:** denso em toda a faixa e dissolvido só entre a faixa e o topo da cabeça, nunca encostando no rosto. Se o `check` reprovar o contraste de uma cor de marca, escureça o véu (`backdrop_tint` do tema); não troque a cor. ✔
- **Texto atrás do apresentador:** vídeo → legenda/título → recorte da pessoa (`npx hyperframes remove-background`, `/media-use`), em ordem de `z-index`. Faça o punch-in no vídeo e no recorte juntos, no mesmo wrapper. A palavra lê melhor com 30–55% coberta; abaixo de 15% ela flutua, acima de 65% some. Marque o recorte com `data-layout-allow-occlusion` e julgue pelo snapshot. O primeiro uso baixa 168 MB e roda a ~2 fps em 1080p na CPU.

## 5. Som

| Som | Só em |
| --- | --- |
| click | um clique real na tela, pílula/botão "apertado" |
| whoosh | corte de cena ou card grande se movendo rápido |
| tick suave | texto chegando letra a letra, contador |
| pop | badge, pílula ou número pousando |
| riser → impacto | o payoff, **uma vez** no vídeo |

- **O pico cai 1 quadro depois da imagem** (a luz chega antes do som). O `build` mede o pico de cada arquivo e alinha. ✔ Para conferir um arquivo: `npx hyperframes audio <arquivo> --json`.
- **Alterne 2–3 takes** de cada som repetido. ✔
- **Cada efeito fica 3–6 dB acima da trilha.** Os ganhos padrão por tipo vêm do perfil da skill (−12 a −20 dB). A fala manda.
- **Trilha:** a música do cliente primeiro. Entre no compasso mais forte, não na introdução, e termine numa barra com fade curto. Uma trilha com quase toda a energia abaixo de 150 Hz **some no alto-falante do celular**. Sob voz contínua, use ~0,14 de volume (−17 dB) com ducking no master (`threshold=0.03:ratio=4:attack=60:release=600`).
- **Tempo da música:** `npx hyperframes beats <trilha>` dá as batidas. Corte no tempo, mude o layout no compasso. Calcule cada batida pelo índice (`round(i × fps × 60 / BPM)`), nunca somando batidas arredondadas: a 128 BPM e 30 fps, isso deriva 2 quadros em 32 batidas.
- **Tons sintéticos, chimes e dings:** evite (soam como template). A exceção é um perfil que use marimba/celesta por identidade (comum em educação), com no máximo 2 por vídeo.
- **Níveis finais:** true peak ≤ −1 dBTP por arquivo (áudio de IA costuma clipar), mix de −16 a −14 LUFS para redes. O `master` mede antes e depois. Diga no relatório que o áudio foi **medido, não ouvido**.

## 6. Imagem

- **A grade do perfil** (`video_grade.ffmpeg_curves/colorbalance/eq`) é aplicada no `init`, junto com a recodificação. Alternativa nativa: `npx hyperframes media-treatment` (`/media-use`). **Nunca** use filtro CSS (`filter`, SVG, `.cube` improvisado) sobre o vídeo.
- **Correção antes de estilo:** escuro, chapado ou com dominante de cor se resolve com correção. Estilo (filme, VHS) só quando o cliente pede, e aí precisa ficar evidente.
- **HDR/HLG/PQ e LOG** não passam pelo caminho SDR: converta para Rec.709 antes. O `init` avisa.
- **Tom de pele:** confira com `npx hyperframes grade-compare` (antes × depois) em 3 momentos com luz diferente.

## 7. Revisão (antes de dizer "pronto")

1. `hf check`: **zero erros**. Leia cada aviso. Se não corrigir, escreva no relatório por que ficou.
2. `hf snapshot` (`--review`): abra cada PNG. Veja cada cena no início + 0,3 s e no meio, e a tira de 5 quadros em cada emenda.
3. **Largura de celular:** veja a folha de contato reduzida a ~360 px de largura. Se não dá para ler ali, não dá para ler no feed.
4. **Movimento:** `npx hyperframes keyframes --shot motion.png --selector '#id'` desenha a trajetória real. Para afirmar uma intenção, use um `<cena>.motion.json` com `appearsBy`, `before`, `staysInFrame` e `keepsMoving`, verificado pelo `check`.
5. **Áudio:** `npx hyperframes audio <master> --json` mostra se há som, se os impactos caem onde a imagem bate e se o loudness está na faixa.
6. **Assista ao master inteiro, do primeiro ao último quadro** (regra 11), com som, de preferência no celular.

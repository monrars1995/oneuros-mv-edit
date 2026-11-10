---
description: Edita um vídeo do bruto à entrega com a neuro-mv-edit (perfil, cortes, cenas, legendas, som, render, master, metadados e entrega)
argument-hint: <vídeo> [perfil] [--engine remotion|hyperframes] [--estilo <id>] [--resolucao 4k,1080p] [--codec h264|hevc|prores]
---

Edite o vídeo pedido seguindo a skill `neuro-mv-edit` (leia o SKILL.md dela antes de começar). Argumentos: `$ARGUMENTS`.

O comando `neuro-mv-edit` está no PATH desta sessão (vem do plugin). Trabalhe em etapas e **pare para o usuário aprovar** onde indicado.

1. **Decisões antes de tudo** (uma pergunta de múltipla escolha só, com as opções abaixo; o que vier nos argumentos já está decidido).
   - Rode `neuro-mv-edit exportacao analisar <vídeo> --plataforma <rede> --quadro /tmp/quadro.png` para saber o que a fonte rende (resolução útil no enquadramento da rede, fps, codec, HDR) e qual é a recomendação. Use isso para marcar a opção recomendada.
   - **Perfil:** sem perfil nos argumentos, `neuro-mv-edit perfil listar` e ofereça os perfis. Cliente novo: siga `/neuro-mv-edit:perfil`.
   - **Motor:** o do perfil (`engine_default`), senão Remotion. Lembre a licença do Remotion se for a primeira vez.
   - **Resolução** (pode marcar mais de uma; cada uma sai renderizada nativamente, sem reescalar um vídeo pronto): 4K (2160 no lado curto), 1440p, 1080p, original. Não ofereça como recomendada uma resolução acima da área útil da fonte: o vídeo seria ampliado.
   - **Codec:** H.264 (aceito em todas as redes), HEVC/H.265 (mesma qualidade, ~40% menor), ProRes 422 HQ (master para arquivo ou outro editor; `.mov` grande).
   - **FPS:** o da fonte (padrão), 30 ou 60. **Qualidade:** alta (CRF do perfil) ou máxima.
2. **Verificação do ambiente** (na primeira edição da sessão, depois das decisões):
   - Rode `neuro-mv-edit verificar --corrigir --motor <m> --resolucao <r> --codec <c> --video <vídeo>`. Ele instala sozinho o que pode (motor Remotion, navegador do render, CLI do HyperFrames, skills de apoio `/remotion-best-practices` e `/hyperframes`, fontes, ffmpeg pelo Homebrew) e mostra o comando do resto.
   - Confira os MCPs desta sessão: as ferramentas `mcp__elevenlabs__*` (SFX, trilha, isolamento de voz) precisam estar ativas; se não estiverem, peça ao usuário para autorizar o ElevenLabs em `/mcp`.
   - Pendência com ✗ (disco cheio para 4K, ffmpeg sem libx265 para HEVC...) bloqueia: resolva com o usuário antes de seguir. Avisos (⚠) só informam.
3. **Projeto.**
   - Meça o topo do cabelo em `/tmp/quadro.png` (gravado no passo 1, já nas coordenadas da composição): olhe a imagem.
   - Rode `neuro-mv-edit projeto init --profile <p> --video <vídeo> --out projetos/<nome> --head-y <px> --resolucao <r> --codec <c> [--fps <f>] [--qualidade maxima] [--engine ...] [--estilo ...]`. O mezanino guarda a resolução útil da fonte até a maior saída; nada é reduzido antes do render.
4. **Transcrição e legendas.**
   - Rode `neuro-mv-edit projeto transcrever -P projetos/<nome>` e depois `neuro-mv-edit projeto legendas -P projetos/<nome> --apply-glossary`.
   - Mostre os termos suspeitos e corrija com `--fix "errado=certo"`. Correções que valem para os próximos vídeos ganham `--learn`.
5. **Decupagem.**
   - Rode `neuro-mv-edit projeto cortar -P projetos/<nome> --dry-run`.
   - Peça ao subagente `neuro-mv-edit:decupador` as tomadas repetidas e as claquetes.
   - Mostre ao usuário os cortes e os avisos de "buraco sem silêncio medido". **Aprovação.** Depois aplique sem `--dry-run`, com os `--remover`/`--manter` combinados.
6. **Cenas.**
   - Escreva `projetos/<nome>/cues.json` (cenas, câmera, SFX, trilha, efeitos), seguindo a §9 e a §11 da skill e o `references/remotion/BRIDGE.md` (ou o do HyperFrames). Rode `neuro-mv-edit projeto build -P projetos/<nome>`.
   - Rode `neuro-mv-edit projeto estudio -P projetos/<nome>` e diga a URL ao usuário.
   - Rode `check` e `snapshot`, e olhe os PNGs. **Aprovação** das cenas, ajustando pelo Studio ou pelo `cues.json`.
7. **Som.**
   - Gere os SFX que faltarem com o MCP do ElevenLabs (`text_to_sound_effects`) em `projetos/<nome>/assets/sfx/<tipo>_NN.wav`, e a trilha se o perfil pedir. Rode `build` de novo.
   - Sem o MCP autorizado, peça ao usuário para autorizar o ElevenLabs em `/mcp`.
8. **Render e QA.**
   - Rode `neuro-mv-edit projeto render -P projetos/<nome>`: sai uma versão por resolução decidida, no codec decidido, com PNG por quadro e uma única codificação. Depois `neuro-mv-edit projeto master -P projetos/<nome> --name <NOME>` (loudness em todas; o vídeo é copiado sem recompressão).
   - Confira com `ffprobe` que cada arquivo saiu na resolução, no codec e no fps decididos antes de dizer que está pronto.
   - Peça ao subagente `neuro-mv-edit:revisor` a revisão. Corrija o que ele apontar.
9. **Entrega:** `/neuro-mv-edit:entregar`.
10. **Memória:** registre em `~/.neuro-mv-edit/memory.json` o que o usuário pediu para valer nos próximos vídeos (seção 14 da skill).

Nunca diga que está pronto sem `check` limpo, snapshots revisados, loudness dentro do alvo e as exportações conferidas (resolução, codec, fps).

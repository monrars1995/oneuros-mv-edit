---
description: Verifica e corrige o ambiente da neuro-mv-edit para a edição pedida (ffmpeg e codecs, Node, motor Remotion e navegador, HyperFrames, skills de apoio, MCPs, fontes, disco e memória para 4K)
argument-hint: [--motor remotion|hyperframes] [--resolucao 4k,1080p] [--codec h264|hevc|prores] [--video <fonte>]
---

Verifique o ambiente para a edição. Argumentos: `$ARGUMENTS`.

1. Sem motor, resolução ou codec nos argumentos e com uma edição em vista, pergunte essas decisões antes (múltipla escolha; `neuro-mv-edit exportacao analisar <vídeo>` recomenda pelo que a fonte rende). Sem edição em vista, verifique o padrão.
2. Rode `neuro-mv-edit verificar --corrigir` com as decisões (`--motor`, `--resolucao`, `--codec`, `--video`). Ele instala o que é seguro instalar sozinho e mostra o comando exato do resto.
3. Confira os MCPs desta sessão: as ferramentas `mcp__elevenlabs__*` estão disponíveis? Se não, peça ao usuário para autorizar o ElevenLabs em `/mcp` (o plugin já declara o servidor).
4. Resuma: o que estava faltando, o que foi instalado agora, o que ainda depende do usuário (com o comando) e se o ambiente está pronto para a resolução e o codec decididos.

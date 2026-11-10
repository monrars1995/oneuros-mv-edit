---
description: Exporta (ou reexporta) um projeto da neuro-mv-edit em outras resoluções e codecs — 4K, 1440p, 1080p, 720p, H.264, HEVC ou ProRes — sem perder a qualidade da fonte
argument-hint: [pasta do projeto] [--resolucao 4k,1080p] [--codec h264|hevc|prores] [--qualidade alta|maxima]
---

Exporte o projeto pedido. Argumentos: `$ARGUMENTS`.

1. **Projeto.** Argumento, pasta atual com `neuro.json` ou os projetos em `projetos/`. Rode `neuro-mv-edit projeto exportacao -P <projeto>` para ver a decisão atual e o que a fonte rende.
2. **Decisão do usuário** (múltipla escolha, uma pergunta só; o que veio nos argumentos já está decidido):
   - resolução, uma ou várias: 4K, 1440p, 1080p, 720p, original. Marque como recomendada a maior sem ampliar a fonte (o comando acima avisa quando uma opção amplia);
   - codec: H.264 (todas as redes), HEVC (~40% menor; YouTube, iPhone, Mac) ou ProRes 422 HQ (master `.mov` para arquivo ou outro editor);
   - qualidade: alta (CRF do perfil) ou máxima.
3. **Grave a decisão:** `neuro-mv-edit projeto exportacao -P <projeto> --resolucao <r> --codec <c> --qualidade <q>`. Se ele avisar que o mezanino é menor do que a fonte rende para a maior saída, rode de novo com `--mezanino` (refaz `assets/base.mp4` a partir da fonte original, mesmos fps e duração; cortes e cenas continuam valendo).
4. **Verificação:** `neuro-mv-edit verificar --corrigir --motor <motor do projeto> --resolucao <r> --codec <c>`. Disco insuficiente para 4K ou codificador ausente bloqueia: resolva com o usuário.
5. **Render e master:** `neuro-mv-edit projeto render -P <projeto>` (uma versão nativa por resolução, PNG por quadro, uma única codificação) e `neuro-mv-edit projeto master -P <projeto> --name <NOME>` (loudness em todas; vídeo copiado sem recompressão).
6. **Confira** cada master com `ffprobe -v error -show_entries stream=codec_name,width,height,pix_fmt,r_frame_rate,color_space -of compact <arquivo>`: resolução, codec e fps decididos, `bt709`. Mostre a lista ao usuário com o tamanho de cada arquivo.
7. **Entrega:** `/neuro-mv-edit:entregar` (metadados e organização levam as outras resoluções junto).

O fps não muda depois do `init` (a timeline e o mezanino usam esse fps); para outro fps, refaça o `init` com `--fps`.

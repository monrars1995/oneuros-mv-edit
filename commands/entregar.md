---
description: Fecha a entrega do último master (metadados no MP4, copy de postagem e arquivamento em entregas/AAAA-MM/DD/<rede>/)
argument-hint: [pasta do projeto] [rede: reels|tiktok|shorts|youtube|feed]
---

Entregue o último master de um projeto da neuro-mv-edit. Argumentos: `$ARGUMENTS`.

1. **Ache o projeto** (argumento, pasta atual com `neuro.json` ou o mais recente em `projetos/`) e o master: `renders/master/*_MASTER.mp4` mais recente. Sem master, rode antes `neuro-mv-edit projeto master -P <projeto>`.
2. **Confira com o usuário:** o título/hook (sugira um pela primeira cena e pelo transcript), uma descrição curta e a rede. O perfil vem do `neuro.json`.
3. **Grave os metadados e a copy:** `neuro-mv-edit metadata -i <master> -p <perfil> -t "<hook>" -d "<descrição>"`. Isso gera `<master>_meta.mp4` e `<master>_meta_COPY_POSTAGEM.md`, e a cópia leve, se houver.
4. **Arquive:** `neuro-mv-edit organize -m <master>_meta.mp4 -n <rede>`. Isso copia o vídeo, a cópia leve, o relatório de loudness e a copy para `entregas/AAAA-MM/DD/<rede>/`.
5. **Mostre** o caminho final e o conteúdo da copy, e lembre: o master precisa ser assistido inteiro antes de publicar.

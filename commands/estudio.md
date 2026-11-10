---
description: Abre a interface web do projeto (Remotion Studio ou preview do HyperFrames) para acompanhar e ajustar a edição
argument-hint: [pasta do projeto] [parar]
---

Abra a interface web de um projeto da neuro-mv-edit. Argumentos: `$ARGUMENTS`.

1. **Ache o projeto.** Use a pasta dos argumentos; senão a pasta atual, se tiver `neuro.json`; senão o projeto mais recente em `projetos/` (o `neuro.json` mais novo). Se houver dúvida, pergunte.
2. **`parar`:** rode `neuro-mv-edit projeto estudio -P <projeto> --parar`.
3. **Senão:** rode `neuro-mv-edit projeto estudio -P <projeto>`.
   - No motor Remotion ele sobe o Studio em segundo plano, abre o navegador e liga o vigia, que sincroniza as edições e faz checkpoint.
   - Diga ao usuário a URL que aparecer e explique: o que ele mudar no Studio (cortes, tempo das cenas, keyframes da câmera, props) é gravado no projeto, e `neuro-mv-edit projeto historico` / `voltar <ref>` desfazem.

Antes de editar `edl.json` ou `cues.json` com o Studio aberto, rode `neuro-mv-edit projeto sincronizar -P <projeto>` e releia os arquivos.

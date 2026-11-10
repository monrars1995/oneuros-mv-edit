---
description: Cria ou edita um perfil (apresentador, tema, estilo de edição, legendas, metadados) com perguntas no chat
argument-hint: [novo | editar <id> | listar | mostrar <id>]
---

Cuide dos perfis da neuro-mv-edit. Argumentos: `$ARGUMENTS`. O comando `neuro-mv-edit` está no PATH (plugin).

- **`listar` / `mostrar <id>`:** rode `neuro-mv-edit perfil listar` (ou `perfil mostrar <id>`) e resuma.
- **`novo`, ou sem argumento:**
  1. Rode `neuro-mv-edit perfil listar`, `neuro-mv-edit tema listar` e `neuro-mv-edit estilo listar` para ter as opções reais.
  2. Pergunte ao usuário, de preferência com múltipla escolha e poucas perguntas por vez:
     - **Obrigatórios:** nome e segmento.
     - **Recomendados:** regras do setor (OAB, educação/ECA, saúde ou geral), tema, estilo de edição, plataforma padrão e motor (Remotion ou HyperFrames).
     - **Opcionais:** @, cargo, legenda (queimar?, fonte, cor, cor e palavras de destaque), CTA padrão e metadados (artista, copyright).
     - Sugira tema e estilo pelo segmento e mostre a prévia: `neuro-mv-edit tema preview <id> --sem-abrir` e diga o caminho do HTML.
  3. Monte o JSON (modelo na seção 4 da skill, com `"base": "template_novo_perfil"`), grave num arquivo temporário e rode `neuro-mv-edit perfil novo --json <arquivo>`. Se a validação recusar, corrija e rode de novo.
  4. Gere a prévia com o perfil: `neuro-mv-edit tema preview <tema> --perfil <id> --sem-abrir`. Mostre o caminho e o próximo passo: `/neuro-mv-edit:editar <vídeo> <id>`.
- **`editar <id>`:** rode `neuro-mv-edit perfil mostrar <id>`, pergunte o que muda, grave um JSON só com os campos alterados e rode `neuro-mv-edit perfil editar <id> --json <arquivo>` (o `<id>` vira a base e o id salvo). Para uma ou duas mudanças simples também valem opções, ex.: `perfil editar <id> --tema noticia_impacto --estilo dinamico_reels`. Editar um perfil que vem com a skill cria a versão do usuário, que passa a valer no lugar.

Os perfis do usuário ficam em `~/.neuro-mv-edit/perfis/` e sobrevivem às atualizações. Nunca edite `presets/*.json` da skill.

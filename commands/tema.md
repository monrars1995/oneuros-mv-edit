---
description: Escolhe, visualiza ou cria um tema visual (cores e fontes dos cartões) para os vídeos
argument-hint: [listar | preview <id> | novo | editar <id>]
---

Cuide dos temas visuais da neuro-mv-edit. Argumentos: `$ARGUMENTS`. O comando `neuro-mv-edit` está no PATH (plugin).

- **`listar`, ou sem argumento:** rode `neuro-mv-edit tema listar`. Explique a diferença entre os 8 presets genéricos e os temas da biblioteca do usuário (de marca, criados ou importados), e ofereça a prévia.
- **`preview <id>`:** rode `neuro-mv-edit tema preview <id>` (abre no navegador; use `--sem-abrir` para só gerar o arquivo) e diga o caminho do HTML. `--perfil <id>` usa a legenda de um perfil, `--estilo` e `--plataforma` também valem.
- **`novo` / `editar <id>`:**
  1. Pergunte de qual tema partir (mostre os presets) e o que muda: cor de destaque, de alerta e do texto (#RRGGBB); as fontes de títulos, de apoio e de rótulos; e a pílula, cheia ou em contorno.
  2. Use só as fontes instaladas: Big Shoulders Display, Fraunces, Inter, Cal Sans, Instrument Serif, DM Sans, Plus Jakarta Sans e Space Grotesk.
  3. Grave o JSON só com o que muda em `colors`, `fonts` e `components.pill`.
     - **Novo:** inclua `"base": "<id de partida>"`, `"id"` e `"name"`, e rode `neuro-mv-edit tema novo --json <arquivo>`.
     - **Editar:** rode `neuro-mv-edit tema editar <id> --json <arquivo>` (o `<id>` vira a base e o id salvo).
  4. Gere a prévia do resultado e pergunte se ajusta algo.

Temas do usuário ficam em `~/.neuro-mv-edit/temas/`. Para usar num perfil: `/neuro-mv-edit:perfil editar <id>`. Só neste projeto: `projeto init --theme <id>`.

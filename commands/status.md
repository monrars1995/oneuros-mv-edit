---
description: Mostra o estado de um projeto da neuro-mv-edit (motor, cortes, cenas, Studio, checkpoints, último render). Para o estado da instalação nos agentes, use `neuro-mv-edit status --deep`
argument-hint: [pasta do projeto]
---

Mostre o estado de um projeto da neuro-mv-edit. Argumentos: `$ARGUMENTS`.

1. Ache o projeto: argumento, pasta atual com `neuro.json` ou os projetos em `projetos/`. Sem nenhum, liste os encontrados.
2. Rode `neuro-mv-edit projeto status -P <projeto>` e `neuro-mv-edit projeto historico -P <projeto> -n 8`.
3. Resuma em poucas linhas:
   - motor e duração;
   - cortes e cenas;
   - Studio aberto ou não;
   - edições do Studio pendentes de sincronizar;
   - último checkpoint e último render.
4. Diga o próximo passo natural do fluxo (seção 3 da skill).

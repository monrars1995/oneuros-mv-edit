---
description: Confere o ambiente da neuro-mv-edit (ffmpeg, Node, motores Remotion e HyperFrames, fontes, ElevenLabs) e resolve o que faltar. Não é o instalador dos agentes (esse é o `neuro-mv-edit setup` no terminal)
---

Prepare a máquina para a neuro-mv-edit. O comando `neuro-mv-edit` está no PATH (plugin).

1. **Verifique o ambiente:** `neuro-mv-edit verify` (ferramentas, versão do ffmpeg, HyperFrames, motor Remotion, Chrome e fontes). Resuma o que está ✅ e o que está ❌.
2. **Motor Remotion:** `neuro-mv-edit remotion status`. Sem o motor, pergunte se instala agora (`neuro-mv-edit remotion setup`, ~250 MB + navegador). Lembre a licença: grátis até 3 pessoas; a partir de 4, Company License.
3. **ElevenLabs:**
   - O plugin traz o servidor MCP do ElevenLabs. Se as ferramentas `text_to_sound_effects` / `compose_music` não estiverem disponíveis nesta sessão, peça ao usuário para autorizar em `/mcp` (OAuth no navegador).
   - Sem o ElevenLabs, os SFX ficam faltando e o `build` avisa.
4. **Instalação nos agentes:** `neuro-mv-edit status --deep` mostra onde a skill e os plugins estão, e a versão de cada um. Para instalar ou atualizar em outros agentes, o usuário roda no terminal `npx --yes github:monrars1995/oneuros-mv-edit#v<versão>` (o assistente pergunta) ou `... install`.
5. **Perfis:** `neuro-mv-edit perfil listar`. Sem perfil do cliente, ofereça `/neuro-mv-edit:perfil`.

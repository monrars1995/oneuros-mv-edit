#!/usr/bin/env node

/**
 * CLI Oficial da Skill Neuro MV Edit
 * Instala a skill nos agentes de IA (Claude Code, Codex, OpenCode, Hermes, Open Design, Neuro Harness,
 * Gemini, Antigravity, Cursor e leitores de ~/.agents/skills),
 * validar o ambiente audiovisual, configurar o MCP do ElevenLabs e gerenciar entregas.
 */

const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');
const os = require('os');

const PKG_ROOT = path.resolve(__dirname, '..');
// A skill fica em skills/neuro-mv-edit (layout padrão de repositório de plugins: Claude Code, Agent Plugins v1, Open Design).
const SKILL_DIR = path.join(PKG_ROOT, 'skills', 'neuro-mv-edit');
const VERSION = '1.10.0';
const HF_VERSION = process.env.NEURO_HF_VERSION || '0.9.19';

const COLOR = {
  reset: '\x1b[0m',
  bright: '\x1b[1m',
  gold: '\x1b[33m',
  blue: '\x1b[34m',
  cyan: '\x1b[36m',
  green: '\x1b[32m',
  red: '\x1b[31m',
  gray: '\x1b[90m'
};

function banner() {
  console.log(`\n${COLOR.gold}${COLOR.bright}╔═════════════════════════════════════════════════════════════════╗${COLOR.reset}`);
  console.log(`${COLOR.gold}${COLOR.bright}║               NEURO MV EDIT — CLI OFICIAL v${VERSION}                ║${COLOR.reset}`);
  console.log(`${COLOR.gold}${COLOR.bright}║   Pós-Produção & Motion Graphics para Criadores e Produtoras   ║${COLOR.reset}`);
  console.log(`${COLOR.gold}${COLOR.bright}╚═════════════════════════════════════════════════════════════════╝${COLOR.reset}\n`);
}

const agents = require('./agents');
const ui = require('./ui');
const { makeSetup } = require('./setup');

function readVersion() {
  try { return JSON.parse(fs.readFileSync(path.join(PKG_ROOT, 'package.json'), 'utf8')).version || VERSION; } catch { return VERSION; }
}

function showHelp() {
  banner();
  console.log(`${COLOR.bright}USO:${COLOR.reset}`);
  console.log(`  npx --yes github:${agents.DEFAULT_REPO}#v${VERSION} <comando> [opções]   ${COLOR.gray}(o pacote não está no npm; use o GitHub)${COLOR.reset}`);
  console.log(`  node cli/cli.js <comando> [opções]                   ${COLOR.gray}(a partir de um clone)${COLOR.reset}`);
  console.log(`  neuro-mv-edit <comando> [opções]                     ${COLOR.gray}(nas sessões do Claude Code e do Neuro Harness com o plugin ativo)${COLOR.reset}`);
  console.log(`  ${COLOR.gray}Referência completa: docs/COMANDOS.md${COLOR.reset}\n`);
  console.log(`${COLOR.bright}COMANDOS DISPONÍVEIS:${COLOR.reset}`);
  console.log(`  ${COLOR.green}setup${COLOR.reset}               Assistente: escolhe os agentes da máquina, o modo de cada um, extras e o 1º perfil`);
  console.log(`                      ${COLOR.gray}(também abre ao rodar sem comando num terminal interativo; --yes usa os padrões)${COLOR.reset}`);
  console.log(`  ${COLOR.green}install${COLOR.reset}             Instala/atualiza a skill nos agentes detectados (ou nos de --agent)`);
  console.log(`  ${COLOR.green}uninstall${COLOR.reset}           Remove skill e plugins dos agentes (nunca apaga um clone git)`);
  console.log(`  ${COLOR.green}status${COLOR.reset} [--deep]     Mostra onde a skill está, a versão e se cada agente a carrega (--agent filtra)`);
  console.log(`  ${COLOR.green}agents${COLOR.reset}              Lista os agentes suportados, a pasta de cada um e se foi detectado`);
  console.log(`  ${COLOR.green}verificar${COLOR.reset}           Verifica o ambiente para as decisões da edição (--motor, --resolucao, --codec, --video);`);
  console.log(`                      --corrigir instala o que falta (motor, navegador, skills de apoio, fontes, ffmpeg)`);
  console.log(`  ${COLOR.green}exportacao${COLOR.reset}          analisar <vídeo>: resolução útil da fonte e recomendação (4K, 1440p, 1080p...); opcoes`);
  console.log(`  ${COLOR.green}projeto${COLOR.reset} <sub>       Projetos com escolha de motor (Remotion ou HyperFrames): init | transcrever | legendas |`);
  console.log(`                      cortar | build | estudio | sincronizar | check | snapshot | render | master | salvar | historico | voltar | status`);
  console.log(`  ${COLOR.green}remotion${COLOR.reset} setup|status  Instala/confere o motor Remotion compartilhado (~/.neuro-mv-edit/remotion/<versão>)`);
  console.log(`  ${COLOR.green}hf${COLOR.reset} <sub> [opções]    Ponte HyperFrames direta: init | captions | build | check | snapshot | preview | render | master`);
  console.log(`  ${COLOR.green}mcp${COLOR.reset}                 Guia do ElevenLabs MCP (plugin: só autorizar em /mcp; skill e outros agentes: como configurar)`);
  console.log(`  ${COLOR.green}perfil${COLOR.reset} <sub>         Perfis: listar | mostrar | novo | editar | remover | exportar | importar`);
  console.log(`  ${COLOR.green}tema${COLOR.reset} <sub>           Temas visuais: listar | mostrar | novo | editar | remover | preview <id>`);
  console.log(`  ${COLOR.green}estilo${COLOR.reset} <sub>         Estilos de edição (ritmo, legenda, câmera, SFX): listar | mostrar | novo | editar | remover`);
  console.log(`  ${COLOR.green}info${COLOR.reset}                Lista perfis, temas e estilos (skill + biblioteca do usuário)`);
  console.log(`  ${COLOR.green}metadata${COLOR.reset} <args>     Injeta metadados no MP4 e gera <vídeo>_COPY_POSTAGEM.md`);
  console.log(`  ${COLOR.green}organize${COLOR.reset} <args>     Copia a entrega para entregas/AAAA-MM/DD/<rede>/`);
  console.log(`  ${COLOR.green}version${COLOR.reset}             Mostra a versão instalada do pacote`);
  console.log(`  ${COLOR.green}help${COLOR.reset}                Mostra esta mensagem de ajuda\n`);
  console.log(`${COLOR.bright}OPÇÕES DE INSTALAÇÃO:${COLOR.reset}`);
  console.log(`  --agent <ids>        claude-code, codex, opencode, hermes, open-design, neuro-harness, gemini-cli,`);
  console.log(`                       antigravity, antigravity-cli, cursor, universal (vírgulas ou repetido; "all" = todos)`);
  console.log(`  --plugin             Força plugin onde houver (já é o padrão desde a 1.7.0; não combina com --skills-only)`);
  console.log(`  --skills-only        Pasta de skill em vez de plugin (Claude Code, Hermes, OpenCode, Neuro Harness; o Open Design é sempre plugin)`);
  console.log(`  --link               Uma cópia em ~/.agents/skills e links nos outros agentes (atualiza tudo de uma vez)`);
  console.log(`  --target <pasta>     Instala só em <pasta>/neuro-mv-edit (ex.: .claude/skills de um projeto)`);
  console.log(`  --od-source <src>    Origem para o Open Design (padrão: a pasta da skill deste pacote; ou github:${agents.DEFAULT_REPO}/skills/neuro-mv-edit)`);
  console.log(`  --dry-run            Mostra o que faria, sem escrever nada`);
  console.log(`  --skip-hyperframes   Não instala as skills oficiais do HyperFrames`);
  console.log(`  --remotion           Já instala o motor Remotion compartilhado (senão, ele é instalado no 1º projeto Remotion)`);
  console.log(`  --mode <id=modo>     Modo por agente (claude-code, hermes, opencode, neuro-harness): ex. claude-code=skill,hermes=plugin`);
  console.log(`  --skip-verify        Não roda o verificador de ambiente/fontes no fim\n`);
  console.log(`${COLOR.bright}EXEMPLOS:${COLOR.reset}`);
  console.log(`  npx --yes github:${agents.DEFAULT_REPO}#v${VERSION}                     ${COLOR.gray}# assistente interativo (setup)${COLOR.reset}`);
  console.log(`  npx --yes github:${agents.DEFAULT_REPO}#v${VERSION} install`);
  console.log(`  npx --yes github:${agents.DEFAULT_REPO}#v${VERSION} install --agent codex,opencode,hermes,open-design`);
  console.log(`  npx --yes github:${agents.DEFAULT_REPO}#v${VERSION} status --deep`);
  console.log(`  npx --yes github:${agents.DEFAULT_REPO}#v${VERSION} projeto init --engine remotion --profile exemplo_juridico --video bruto.mp4 --out projetos/cpr`);
  console.log(`  npx --yes github:${agents.DEFAULT_REPO}#v${VERSION} projeto estudio --project projetos/cpr`);
  console.log(`  npx --yes github:${agents.DEFAULT_REPO}#v${VERSION} perfil novo`);
  console.log(`  npx --yes github:${agents.DEFAULT_REPO}#v${VERSION} tema preview noticia_impacto`);
  console.log(`  npx --yes github:${agents.DEFAULT_REPO}#v${VERSION} metadata -i video.mp4 -p exemplo_juridico -t "Meu Hook"\n`);
}

function parseOpts(args) {
  const opts = { agents: [], dryRun: false, link: false, target: null, odSource: null, skipHyperframes: false, skipVerify: false, deep: false, plugin: false, skillsOnly: false, remotion: false, modes: {} };
  for (let i = 0; i < args.length; i++) {
    const a = args[i];
    const next = () => args[++i];
    if (a === '--agent' || a === '-a') opts.agents.push(next());
    else if (a.startsWith('--agent=')) opts.agents.push(a.slice(8));
    else if (a === '--all') opts.agents.push('all');
    else if (a === '--dry-run') opts.dryRun = true;
    else if (a === '--link') opts.link = true;
    else if (a === '--copy') opts.link = false;
    else if (a === '--plugin' || a === '--as-plugin') opts.plugin = true;
    else if (a === '--skills-only' || a === '--no-plugin') opts.skillsOnly = true;
    else if (a === '--target') opts.target = next();
    else if (a === '--od-source') opts.odSource = next();
    else if (a === '--skip-hyperframes') opts.skipHyperframes = true;
    else if (a === '--skip-verify') opts.skipVerify = true;
    else if (a === '--remotion' || a === '--with-remotion') opts.remotion = true;
    else if (a === '--mode' || a.startsWith('--mode=')) {
      const spec = a === '--mode' ? next() : a.slice(7);
      for (const pair of String(spec || '').split(',').filter(Boolean)) {
        const [id, mode] = pair.split('=').map((x) => (x || '').trim());
        if (!['plugin', 'skill'].includes(mode)) throw new Error(`--mode ${pair}: use <agente>=plugin ou <agente>=skill`);
        const ag = agents.resolveAgents([id])[0];
        opts.modes[ag.id] = mode;
      }
    }
    else if (a === '--deep') opts.deep = true;
    else throw new Error(`Opção desconhecida: ${a}`);
  }
  if (opts.plugin && opts.skillsOnly) throw new Error('Use --plugin ou --skills-only, não os dois.');
  return opts;
}

const ICON = { installed: '✅', updated: '🔄', linked: '🔗', source: '📌', skipped: '⏭️ ', 'dry-run': '🧪', missing: '➖', pending: '⏳', error: '❌', removed: '🗑️ ', absent: '➖' };

function selectAgents(opts) {
  const chosen = agents.resolveAgents(opts.agents);
  if (chosen) return chosen;
  return agents.AGENTS.filter((a) => a.detect());
}

/** Modo efetivo: 'plugin' ou 'skill'. Plugin é o padrão de Claude Code, OpenCode, Hermes e Neuro Harness (defaultMode). */
function modeFor(agent, opts) {
  if (agent.kind === 'od') return 'plugin';
  if (!agent.plugin) return 'skill';
  if (opts.modes && opts.modes[agent.id]) return opts.modes[agent.id];
  if (opts.skillsOnly) return 'skill';
  if (opts.plugin) return 'plugin';
  return agent.defaultMode || 'skill';
}

function line(r, id, extra) {
  const where = r.target ? `${r.target.replace(os.homedir(), '~')}  ` : '';
  console.log(`  ${ICON[r.status] || '•'} ${id.padEnd(16)} ${where}${COLOR.gray}${r.msg || ''}${extra ? ' ' + extra : ''}${COLOR.reset}`);
}

/** Cópias duplicadas da skill em pastas antigas ou que competem com a do agente. */
function cleanLegacy(agent, opts) {
  for (const old of (agent.legacy ? agent.legacy() : [])) {
    const r = agents.removeSkill(old, opts.dryRun);
    if (r.status === 'removed' || r.status === 'dry-run') console.log(`     ${COLOR.gray}↳ cópia duplicada em ${r.target.replace(os.homedir(), '~')} ${r.status === 'removed' ? 'removida' : 'seria removida'}${COLOR.reset}`);
  }
}

function handleInstall(args, preset) {
  let opts;
  if (preset) {
    opts = { ...parseOpts([]), ...preset, agents: preset.agents && preset.agents.length ? [preset.agents.join(',')] : [] };
  } else {
    try { opts = parseOpts(args); } catch (e) { console.log(`${COLOR.red}${e.message}${COLOR.reset}`); process.exit(2); }
  }
  if (!opts.quietBanner) banner();
  const version = readVersion();
  const problems = agents.validateSkill(SKILL_DIR);
  if (problems.length) {
    console.log(`${COLOR.red}✗ SKILL.md não passa no formato exigido pelos agentes:${COLOR.reset}`);
    problems.forEach((p) => console.log(`   - ${p}`));
    process.exit(1);
  }
  console.log(`${COLOR.cyan}🚀 Instalando neuro-mv-edit v${version}${opts.dryRun ? ' (simulação)' : ''} — fonte: ${SKILL_DIR}${COLOR.reset}\n`);

  if (opts.target) {
    const parent = path.resolve(process.cwd(), opts.target);
    line(agents.placeSkill({ source: SKILL_DIR, parent, mode: 'copy', dryRun: opts.dryRun, agentId: 'custom', version }), 'custom');
  } else {
    const list = selectAgents(opts);
    const universal = agents.AGENTS.find((a) => a.id === 'universal');
    const canonical = path.join(universal.dir(), agents.SKILL_NAME);
    const done = new Map();
    const ordered = opts.link ? [universal, ...list.filter((a) => a.id !== 'universal')] : list;
    for (const agent of ordered) {
      const mode = modeFor(agent, opts);
      try {
        if (agent.kind === 'od') {
          line(agents.installOpenDesign({ dryRun: opts.dryRun, source: opts.odSource, localDir: SKILL_DIR }), agent.id);
          continue;
        }
        if (mode === 'plugin') {
          let r;
          if (agent.plugin === 'opencode') r = agents.placeOpenCodePlugin({ pkgRoot: PKG_ROOT, skillDir: SKILL_DIR, dryRun: opts.dryRun, version });
          else if (agent.plugin === 'claude') r = agents.installClaudePlugin({ pkgRoot: PKG_ROOT, dryRun: opts.dryRun, version });
          else if (agent.plugin === 'hermes') r = agents.installHermesPlugin({ dryRun: opts.dryRun, version, pkgRoot: PKG_ROOT });
          else if (agent.plugin === 'harness') r = agents.installHarnessPlugin({ dryRun: opts.dryRun, version, pkgRoot: PKG_ROOT });
          line(r, agent.id, '[plugin]');
          // o plugin já traz a skill: a cópia avulsa na pasta de skills duplicaria a entrada
          // (keepDir: a pasta é compartilhada com outros agentes, como ~/.agents/skills do Codex, e fica)
          if (['installed', 'updated', 'dry-run'].includes(r.status)) {
            if (!agent.keepDir) {
              const rm = agents.removeSkill(agent.dir(), opts.dryRun);
              if (rm.status === 'removed' || rm.status === 'dry-run') console.log(`     ${COLOR.gray}↳ cópia avulsa em ${rm.target.replace(os.homedir(), '~')} ${rm.status === 'removed' ? 'removida' : 'seria removida'} (o plugin já carrega a skill)${COLOR.reset}`);
            }
            cleanLegacy(agent, opts);
          }
          continue;
        }
        const parent = agent.dir();
        const key = path.resolve(parent);
        if (done.has(key)) {
          console.log(`  ${ICON.linked} ${agent.id.padEnd(16)} ${path.join(parent, agents.SKILL_NAME).replace(os.homedir(), '~')}  ${COLOR.gray}mesma pasta de ${done.get(key)}${COLOR.reset}`);
        } else {
          const isCanonical = path.join(parent, agents.SKILL_NAME) === canonical;
          const r = agents.placeSkill({ source: SKILL_DIR, parent, mode: opts.link && !isCanonical ? 'link' : 'copy', linkTo: canonical, dryRun: opts.dryRun, agentId: agent.id, version });
          done.set(key, agent.id);
          line(r, agent.id);
        }
        if (agent.plugin === 'opencode') {
          const rm = agents.removeOpenCodePlugin(opts.dryRun);
          if (rm.status === 'removed' || rm.status === 'dry-run') console.log(`     ${COLOR.gray}↳ plugin OpenCode ${rm.status === 'removed' ? 'removido' : 'seria removido'} (--skills-only)${COLOR.reset}`);
        }
        if (agent.plugin === 'claude' || agent.plugin === 'hermes' || agent.plugin === 'harness') {
          // escolheu skill: o plugin carregaria a mesma skill de novo (duas entradas, contexto em dobro)
          const rm = agent.plugin === 'claude' ? agents.uninstallClaudePlugin(opts.dryRun, { keepMarketplace: true })
            : agent.plugin === 'hermes' ? agents.uninstallHermesPlugin(opts.dryRun) : agents.uninstallHarnessPlugin(opts.dryRun);
          if (rm.status === 'removed' || rm.status === 'dry-run') console.log(`     ${COLOR.gray}↳ plugin ${rm.status === 'removed' ? 'removido' : 'seria removido'} (modo skill)${COLOR.reset}`);
        }
      } catch (e) {
        line({ status: 'error', msg: e.message }, agent.id);
      }
      cleanLegacy(agent, opts);
      if (agent.note && !opts.dryRun && mode === 'skill') console.log(`     ${COLOR.gray}↳ ${agent.note}${COLOR.reset}`);
    }
    const skipped = agents.AGENTS.filter((a) => !list.includes(a) && !(opts.link && a.id === 'universal'));
    if (skipped.length && !opts.agents.length) console.log(`\n  ${COLOR.gray}Não detectados (use --agent para forçar): ${skipped.map((a) => a.id).join(', ')}${COLOR.reset}`);
  }

  if (opts.dryRun) {
    console.log(`\n${COLOR.gold}Simulação: nada foi escrito.${COLOR.reset}\n`);
    return;
  }

  console.log(`\n${COLOR.cyan}🎬 Skills oficiais do HyperFrames (motor HyperFrames, registry de blocos e QA)...${COLOR.reset}\n`);
  if (opts.skipHyperframes) {
    console.log(`  ⏭️  --skip-hyperframes: pulei. Para instalar depois: npx hyperframes@${HF_VERSION} skills update`);
  } else {
    const hf = spawnSync('npx', ['--yes', `hyperframes@${HF_VERSION}`, 'skills', 'update'], { stdio: 'inherit', env: { ...process.env, HYPERFRAMES_NO_UPDATE_CHECK: '1' } });
    if (hf.status !== 0) console.log(`  ⚠️ Não foi possível instalar as skills HyperFrames agora. Rode depois: npx hyperframes@${HF_VERSION} skills update`);
  }

  if (opts.remotion) {
    console.log(`\n${COLOR.cyan}🎞️  Motor Remotion compartilhado...${COLOR.reset}\n`);
    handleProjeto(['motor', 'instalar'], false);
  }

  if (!opts.skipVerify) {
    console.log(`\n${COLOR.cyan}🔍 Verificação de ambiente e instalação de fontes...${COLOR.reset}\n`);
    handleVerify(['--corrigir', '--motor', opts.remotion ? 'remotion' : 'hyperframes']);
  }
  if (opts.mcp) handleMcp(true);
  console.log(`\n${COLOR.green}${COLOR.bright}🎉 Instalação concluída.${COLOR.reset} Confira com: ${COLOR.gold}status --deep${COLOR.reset}`);
  console.log(`${COLOR.gray}Abra uma sessão nova de cada agente para ele recarregar skills e plugins.${COLOR.reset}\n`);
}

function handleUninstall(args) {
  let opts;
  try { opts = parseOpts(args); } catch (e) { console.log(`${COLOR.red}${e.message}${COLOR.reset}`); process.exit(2); }
  banner();
  console.log(`${COLOR.cyan}🧹 Removendo neuro-mv-edit${opts.dryRun ? ' (simulação)' : ''}${COLOR.reset}\n`);
  if (opts.target) {
    line(agents.removeSkill(path.resolve(process.cwd(), opts.target), opts.dryRun), 'custom');
    return;
  }
  const list = agents.resolveAgents(opts.agents) || agents.AGENTS;
  const seen = new Set();
  const show = (r, id) => { if (r && r.status !== 'absent') line(r, id); };
  for (const agent of list) {
    if (agent.kind === 'od') { show(agents.uninstallOpenDesign(opts.dryRun), agent.id); continue; }
    if (agent.plugin === 'opencode') show(agents.removeOpenCodePlugin(opts.dryRun), agent.id);
    if (agent.plugin === 'claude') show(agents.uninstallClaudePlugin(opts.dryRun), agent.id);
    if (agent.plugin === 'hermes') show(agents.uninstallHermesPlugin(opts.dryRun), agent.id);
    if (agent.plugin === 'harness') show(agents.uninstallHarnessPlugin(opts.dryRun), agent.id);
    // keepDir: a pasta de skills é compartilhada (ex.: ~/.agents/skills do Codex); só o próprio dono a limpa
    for (const parent of [...(agent.keepDir ? [] : [agent.dir()]), ...(agent.legacy ? agent.legacy() : [])]) {
      const key = path.resolve(parent);
      if (seen.has(key)) continue;
      seen.add(key);
      show(agents.removeSkill(parent, opts.dryRun), agent.id);
    }
  }
  console.log('');
}

function handleStatus(args) {
  let opts;
  try { opts = parseOpts(args); } catch (e) { console.log(`${COLOR.red}${e.message}${COLOR.reset}`); process.exit(2); }
  banner();
  const srcVersion = readVersion();
  console.log(`${COLOR.bright}Fonte:${COLOR.reset} ${SKILL_DIR} (v${srcVersion})\n`);
  const list = agents.resolveAgents(opts.agents) || agents.AGENTS;
  const fmt = (dir, link) => {
    const v = agents.skillVersion(dir);
    const bad = agents.validateSkill(dir.endsWith(path.sep + 'skill') || agents.exists(path.join(dir, 'skill', 'SKILL.md')) ? path.join(dir, 'skill') : dir);
    if (bad.length) return `${COLOR.red}inválida: ${bad[0]}${COLOR.reset}`;
    return v === srcVersion ? `${COLOR.green}v${v}${link}${COLOR.reset}` : `${COLOR.gold}v${v || '?'}${link} (fonte v${srcVersion}: rode install)${COLOR.reset}`;
  };
  for (const agent of list) {
    const detected = agent.detect();
    const dot = detected ? '•' : '·';
    if (agent.kind === 'od') {
      const info = opts.deep ? agents.deepCheck(agent) : (detected ? 'app encontrado (use --deep para consultar o daemon)' : 'não instalado');
      console.log(`  ${dot} ${agent.label.padEnd(18)} ${'[plugin]'.padEnd(52)} ${COLOR.gray}${info}${COLOR.reset}`);
      continue;
    }
    const target = path.join(agent.dir(), agents.SKILL_NAME);
    let mode = 'skill';
    let shown = target;
    let state;
    const claudePl = agent.plugin === 'claude' && agents.onPath('claude') ? agents.claudePluginState() : null;
    const hermesPl = agent.plugin === 'hermes' && agents.onPath('hermes') ? agents.hermesPluginLine() : null;
    const harnessPl = agent.plugin === 'harness' ? agents.harnessPluginState() : null;
    if (agent.plugin === 'opencode' && agents.exists(agents.openCodePluginDir())) {
      mode = 'plugin';
      shown = agents.openCodePluginDir();
      state = fmt(shown, '');
    } else if (claudePl) {
      mode = 'plugin';
      shown = `${agents.PLUGIN_ID} (Claude Code)`;
      const ok = claudePl.version === srcVersion;
      state = `${ok ? COLOR.green : COLOR.gold}v${claudePl.version}${claudePl.enabled ? '' : ' DESATIVADO'}${ok ? '' : ` (fonte v${srcVersion}: rode install)`}${COLOR.reset}`;
    } else if (hermesPl) {
      mode = 'plugin';
      shown = `${agents.DEFAULT_REPO} (Hermes)`;
      state = /enabled|ativ/i.test(hermesPl) ? `${COLOR.green}instalado e ativo${COLOR.reset}` : `${COLOR.gold}${hermesPl.replace(/[│┃]/g, ' ').replace(/\s+/g, ' ').trim()}${COLOR.reset}`;
    } else if (harnessPl) {
      mode = 'plugin';
      shown = `${agents.SKILL_NAME} (perfil ${agents.harnessPaths().profile})`;
      const link = String(harnessPl.spec || '').startsWith('link:') ? ' (link)' : '';
      const ok = harnessPl.version === srcVersion;
      state = !harnessPl.version
        ? `${COLOR.gold}declarado, sem node_modules (rode install)${COLOR.reset}`
        : `${ok ? COLOR.green : COLOR.gold}v${harnessPl.version}${link}${harnessPl.enabled ? '' : ' DESATIVADO'}${ok ? '' : ` (fonte v${srcVersion}: rode install)`}${COLOR.reset}`;
    } else if (!agents.exists(target)) {
      state = `${COLOR.gray}não instalada${COLOR.reset}`;
    } else {
      state = fmt(target, fs.lstatSync(target).isSymbolicLink() ? ' (link)' : '');
    }
    console.log(`  ${dot} ${agent.label.padEnd(18)} ${(shown.replace(os.homedir(), '~') + (mode === 'plugin' ? ' [plugin]' : '')).padEnd(52)} ${state}`);
    if (opts.deep) {
      const extra = agents.deepCheck(agent, mode);
      if (extra) console.log(`      ${COLOR.gray}↳ ${extra}${COLOR.reset}`);
      if ((agent.plugin === 'claude' || agent.plugin === 'hermes') && mode !== 'plugin') {
        const pl = agents.deepCheck(agent, 'plugin');
        if (pl && !/não (encontrado|listado|instalado)/.test(pl)) console.log(`      ${COLOR.gray}↳ ${pl}${COLOR.reset}`);
      }
      if (mode === 'skill' && (agent.plugin === 'claude' || agent.plugin === 'hermes' || (agent.plugin === 'harness' && detected)) && agents.exists(target)) {
        console.log(`      ${COLOR.gold}↳ instalado como skill; o padrão agora é plugin (rode install)${COLOR.reset}`);
      }
    }
    for (const old of (agent.legacy ? agent.legacy() : [])) {
      if (agents.exists(path.join(old, agents.SKILL_NAME))) console.log(`      ${COLOR.gold}↳ cópia duplicada em ${path.join(old, agents.SKILL_NAME).replace(os.homedir(), '~')} (rode install para limpar)${COLOR.reset}`);
    }
  }
  console.log(`\n${COLOR.gray}• detectado   · não detectado${COLOR.reset}\n`);
}

function handleAgents() {
  banner();
  for (const a of agents.AGENTS) {
    const where = a.kind === 'od' ? 'plugin via daemon do Open Design'
      : a.plugin === 'harness' ? `plugin no perfil ${agents.harnessPaths().profileDir.replace(os.homedir(), '~')}`
        : (a.plugin === 'opencode' ? agents.openCodePluginDir() : path.join(a.dir(), agents.SKILL_NAME)).replace(os.homedir(), '~');
    const mode = a.kind === 'od' ? 'plugin' : a.defaultMode === 'plugin' ? 'plugin (--mode <id>=skill: skill)' : 'skill';
    console.log(`  ${a.detect() ? '•' : '·'} ${a.id.padEnd(16)} ${a.label.padEnd(16)} ${mode.padEnd(26)} ${where}`);
    if (a.note) console.log(`      ${COLOR.gray}${a.note}${COLOR.reset}`);
  }
  console.log(`\n${COLOR.gray}• detectado   · não detectado${COLOR.reset}\n`);
}

/** Verificação do ambiente (depois das decisões de motor e exportação); `--corrigir` instala o que falta. */
function handleVerify(args = []) {
  const scriptPath = path.join(SKILL_DIR, 'scripts', 'neuro_verificar.py');
  if (!fs.existsSync(scriptPath)) {
    console.log(`${COLOR.red}neuro_verificar.py não encontrado em ${scriptPath}${COLOR.reset}`);
    return 1;
  }
  const result = spawnSync('python3', ['-I', scriptPath, ...args], { stdio: 'inherit' });
  return result.status === null ? 1 : result.status;
}

/** Decisões de exportação: `analisar <vídeo>` (recomenda pelo que a fonte rende) e `opcoes`. */
function handleExportacao(args = []) {
  const argv = args.length ? args : ['opcoes'];
  const res = spawnSync('python3', ['-I', path.join(SKILL_DIR, 'scripts', 'neuro_export.py'), ...argv], { stdio: 'inherit' });
  return res.status === null ? 1 : res.status;
}

function handleMcp(quiet = false) {
  if (!quiet) banner();
  const URL = 'https://api.elevenlabs.io/v1/mcp';
  console.log(`${COLOR.cyan}🎙️ ELEVENLABS MCP (SFX, trilha e limpeza de voz)${COLOR.reset}`);
  console.log(`${COLOR.gray}Documentação: https://elevenlabs.io/docs/eleven-api/resources/mcp-server${COLOR.reset}\n`);

  const pl = agents.onPath('claude') ? agents.claudePluginState() : null;
  console.log(`${COLOR.bright}1. Claude Code com o plugin neuro-mv-edit${COLOR.reset}${pl ? `  ${COLOR.green}(instalado: v${pl.version}${pl.enabled ? '' : ', DESATIVADO'})${COLOR.reset}` : ''}`);
  console.log(`   Nada a configurar: o .mcp.json do plugin já traz o servidor ${URL}.`);
  console.log(`   Autorize uma vez: abra uma sessão, digite ${COLOR.green}/mcp${COLOR.reset}, escolha "elevenlabs" e faça o login no navegador.\n`);

  console.log(`${COLOR.bright}2. Claude Code só com a skill (--mode claude-code=skill)${COLOR.reset}`);
  console.log(`   ${COLOR.green}claude mcp add --transport http elevenlabs ${URL}${COLOR.reset}`);
  console.log(`   Depois, ${COLOR.green}/mcp${COLOR.reset} na sessão para autorizar.\n`);

  console.log(`${COLOR.bright}3. Outros agentes (Codex, Cursor, Gemini, Antigravity, OpenCode, Hermes...)${COLOR.reset}`);
  console.log(`   Servidor hospedado (OAuth), no arquivo de MCP do agente:`);
  console.log(COLOR.gray + JSON.stringify({ mcpServers: { elevenlabs: { type: 'http', url: URL } } }, null, 2).replace(/^/gm, '   ') + COLOR.reset);
  console.log(`   Ou local com chave (precisa do uv):`);
  console.log(COLOR.gray + JSON.stringify({ mcpServers: { elevenlabs: { command: 'uvx', args: ['elevenlabs-mcp'], env: { ELEVENLABS_API_KEY: '<SUA_CHAVE>' } } } }, null, 2).replace(/^/gm, '   ') + COLOR.reset);
  console.log(`   ${COLOR.gray}Use o nome "elevenlabs": a skill procura as ferramentas text_to_sound_effects, compose_music e isolate_audio.${COLOR.reset}\n`);

  if (process.env.ELEVENLABS_API_KEY) console.log(`  ${COLOR.green}✅ ELEVENLABS_API_KEY definida neste terminal (só a opção local usa).${COLOR.reset}\n`);
}

function handleInfo() {
  banner();
  setupApi().listarTudo();
  console.log(`\n${COLOR.gray}Detalhes: perfil mostrar <id> · tema preview <id> · estilo mostrar <id>${COLOR.reset}\n`);
}

function runPython(script, args) {
  const res = spawnSync('python3', ['-I', path.join(SKILL_DIR, 'scripts', script), ...args], { stdio: 'inherit' });
  if (res.status) process.exit(res.status);
}

let _setup = null;
function setupApi() {
  if (!_setup) _setup = makeSetup({ SKILL_DIR, banner, runInstall: (o) => handleInstall([], o), runPython });
  return _setup;
}

async function handleBiblioteca(kind, args) {
  if (!args.length || args[0] === 'help' || args[0] === '--help') {
    console.log(`${COLOR.bright}${kind}${COLOR.reset}`);
    setupApi().helpBiblioteca(kind);
    if (!args.length) return setupApi().biblioteca(kind, ['listar']);
    return;
  }
  return setupApi().biblioteca(kind, args);
}

function handleHyperframes(args) {
  const scriptPath = path.join(SKILL_DIR, 'scripts', 'hf_project.py');
  if (!args.length || args[0] === 'help' || args[0] === '--help') {
    spawnSync('python3', ['-I', scriptPath, '--help'], { stdio: 'inherit' });
    return;
  }
  const res = spawnSync('python3', ['-I', scriptPath, ...args], { stdio: 'inherit' });
  process.exit(res.status === null ? 1 : res.status);
}

function handleProjeto(args, exit = true) {
  const scriptPath = path.join(SKILL_DIR, 'scripts', 'neuro_project.py');
  const argv = !args.length || args[0] === 'help' ? ['--help'] : args;
  const res = spawnSync('python3', ['-I', scriptPath, ...argv], { stdio: 'inherit' });
  if (exit) process.exit(res.status === null ? 1 : res.status);
  return res.status;
}

function handleRemotion(args) {
  const sub = args[0] || 'status';
  if (sub === 'setup' || sub === 'install' || sub === 'instalar') return handleProjeto(['motor', 'instalar', ...args.slice(1)]);
  if (sub === 'status') return handleProjeto(['motor', 'status']);
  console.log(`${COLOR.red}Use: remotion setup | remotion status${COLOR.reset}`);
  process.exit(2);
}

function runScript(script, args) {
  const res = spawnSync('python3', ['-I', path.join(SKILL_DIR, 'scripts', script), ...args], { stdio: 'inherit' });
  process.exit(res.status === null ? 1 : res.status);
}

function handleMetadata(args) {
  runScript('inject_metadata.py', args);
}

function handleOrganize(args) {
  runScript('organize_deliveries.py', args);
}

async function main() {
  const args = process.argv.slice(2);
  const command = args[0] || (ui.interactive() ? 'setup' : 'help');
  const subArgs = args.slice(1);

  switch (command) {
    case 'setup':
    case 'configurar':
      await setupApi().setup(subArgs);
      break;
    case 'perfil':
    case 'perfis':
      await handleBiblioteca('perfil', subArgs);
      break;
    case 'tema':
    case 'temas':
      await handleBiblioteca('tema', subArgs);
      break;
    case 'estilo':
    case 'estilos':
      await handleBiblioteca('estilo', subArgs);
      break;
    case 'install':
      handleInstall(subArgs);
      break;
    case 'uninstall':
      handleUninstall(subArgs);
      break;
    case 'status':
    case 'doctor':
      handleStatus(subArgs);
      break;
    case 'agents':
      handleAgents();
      break;
    case 'version':
    case '--version':
    case '-v':
      console.log(readVersion());
      break;
    case 'verify':
    case 'verificar':
      if (!subArgs.includes('--hook') && !subArgs.includes('--json')) banner();
      process.exit(handleVerify(subArgs));
      break;
    case 'exportacao':
    case 'exportação':
    case 'export':
      process.exit(handleExportacao(subArgs));
      break;
    case 'mcp':
      handleMcp();
      break;
    case 'info':
      handleInfo();
      break;
    case 'hf':
    case 'hyperframes':
      handleHyperframes(subArgs);
      break;
    case 'projeto':
    case 'p':
      handleProjeto(subArgs);
      break;
    case 'remotion':
      handleRemotion(subArgs);
      break;
    case 'metadata':
      handleMetadata(subArgs);
      break;
    case 'organize':
      handleOrganize(subArgs);
      break;
    case 'help':
    case '--help':
    case '-h':
      showHelp();
      break;
    default:
      console.log(`${COLOR.red}Comando desconhecido: ${command}${COLOR.reset}\n`);
      showHelp();
      process.exit(1);
  }
}

main().catch((e) => {
  if (e && e.cancelled) {
    console.log(`\n${COLOR.gray}Cancelado. Nada foi alterado.${COLOR.reset}`);
    process.exit(130);
  }
  console.error(`${COLOR.red}${e && e.stack ? e.stack : e}${COLOR.reset}`);
  process.exit(1);
});

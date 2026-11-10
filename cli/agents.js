/**
 * Registro de agentes e instalador multi-agente da skill neuro-mv-edit.
 *
 * Caminhos conferidos na fonte de cada agente (nov/2026):
 *  - Claude Code ........ $CLAUDE_CONFIG_DIR/skills | ~/.claude/skills
 *  - Codex .............. lê ~/.codex/skills E ~/.agents/skills (raízes r0/r1 do `codex debug prompt-input`);
 *                         instalar nos dois duplica a skill na lista, então o Codex usa só ~/.agents/skills
 *  - OpenCode ........... $XDG_CONFIG_HOME/opencode/skills | ~/.config/opencode/skills
 *  - Hermes Agent ....... $HERMES_HOME/skills | ~/.hermes/skills (verificado com `hermes skills list`)
 *  - Open Design ........ não se copia arquivo: o daemon instala o plugin (`od plugin install <pasta|github:...>`);
 *                         a pasta de dados é privada do daemon, que roda numa porta efêmera no app desktop
 *  - Neuro Harness ...... DeepSeek Harness (dsh) com o perfil `neuro`: $NEURO_HARNESS_HOME | ~/.neuro-harness
 *                         (ou ~/.neuro-mv-superagent, o nome antigo); plugin pelo `dsh plugin --profile <p> add`
 *                         (pnpm no perfil, DSH_HOME=<home>/dsh). Em modo skill, lê ~/.agents/skills (raiz user-agents)
 *
 * Plugins (cli/agents.js também instala): Claude Code (.claude-plugin), OpenCode V2 (plugins/opencode),
 * Hermes (plugin.json Agent Plugins v1), Open Design (skills/neuro-mv-edit/open-design.json) e
 * DeepSeek/Neuro Harness (manifesto `dsh` do package.json → plugins/dsh).
 *  - Gemini CLI ......... ~/.gemini/skills
 *  - Antigravity ........ ~/.gemini/antigravity/skills (após a migração do app, link para ~/.gemini/config/skills)
 *                         CLI: ~/.gemini/antigravity-cli/skills
 *  - Cursor ............. ~/.cursor/skills
 *  - Universal .......... ~/.agents/skills (Codex, Kimi, Warp, Zed, Pi e outros leitores do padrão Agent Skills)
 *
 * Mesma tabela usada pelo `skills` CLI (vercel-labs/skills) e pelo `hyperframes skills update`.
 */

const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawnSync } = require('child_process');

const SKILL_NAME = 'neuro-mv-edit';
const MARKER = '.neuro-install.json';
const DEFAULT_REPO = 'monrars1995/oneuros-mv-edit';
const COPY_EXCLUDE = new Set(['.git', 'node_modules', '__pycache__', '.DS_Store', 'projetos', 'entregas', '.hyperframes', '.neuro', 'cartoes-hf', MARKER]);

const home = () => os.homedir();
const env = (k) => (process.env[k] || '').trim();
const xdgConfig = () => (env('XDG_CONFIG_HOME') && path.isAbsolute(env('XDG_CONFIG_HOME')) ? env('XDG_CONFIG_HOME') : path.join(home(), '.config'));
const exists = (p) => { try { fs.lstatSync(p); return true; } catch { return false; } };

function onPath(bin) {
  const dirs = (process.env.PATH || '').split(path.delimiter);
  const exts = process.platform === 'win32' ? ['.exe', '.cmd', '.bat', ''] : [''];
  for (const d of dirs) {
    for (const e of exts) {
      const p = path.join(d, bin + e);
      try { if (fs.statSync(p).isFile()) return p; } catch { /* segue */ }
    }
  }
  return null;
}

/**
 * kind: 'dir'  → copia (ou linka) a pasta da skill em `dir()`
 *       'od'   → instala pelo daemon do Open Design
 * shared: id do agente cuja pasta é reaproveitada (evita escrever duas vezes no mesmo lugar)
 */
const AGENTS = [
  {
    id: 'universal', label: 'Universal', aliases: ['agents', 'agent-skills'],
    kind: 'dir', dir: () => path.join(home(), '.agents', 'skills'),
    detect: () => true,
    note: 'Lida por Codex, Kimi, Warp, Zed, Pi e outros agentes do padrão Agent Skills.',
  },
  {
    id: 'claude-code', label: 'Claude Code', aliases: ['claude'],
    kind: 'dir', plugin: 'claude', defaultMode: 'plugin', dir: () => path.join(env('CLAUDE_CONFIG_DIR') || path.join(home(), '.claude'), 'skills'),
    detect: () => exists(path.join(home(), '.claude')) || !!env('CLAUDE_CONFIG_DIR') || !!onPath('claude'),
  },
  {
    id: 'codex', label: 'Codex (OpenAI)', aliases: ['openai-codex'],
    kind: 'dir', shared: 'universal', dir: () => path.join(home(), '.agents', 'skills'),
    detect: () => exists(env('CODEX_HOME') || path.join(home(), '.codex')) || !!onPath('codex'),
    legacy: () => [path.join(env('CODEX_HOME') || path.join(home(), '.codex'), 'skills')],
    note: 'O Codex lê ~/.agents/skills; uma cópia em ~/.codex/skills duplicaria a skill na lista dele. Com bibliotecas grandes o Codex corta a lista por orçamento: chame com $neuro-mv-edit.',
  },
  {
    id: 'opencode', label: 'OpenCode', aliases: ['open-code'],
    kind: 'dir', plugin: 'opencode', defaultMode: 'plugin', dir: () => path.join(xdgConfig(), 'opencode', 'skills'),
    detect: () => exists(path.join(xdgConfig(), 'opencode')) || exists(path.join(home(), '.opencode')) || !!onPath('opencode'),
  },
  {
    id: 'hermes', label: 'Hermes Agent', aliases: ['hermes-agent'],
    kind: 'dir', plugin: 'hermes', defaultMode: 'plugin', dir: () => path.join(env('HERMES_HOME') || path.join(home(), '.hermes'), 'skills'),
    detect: () => exists(env('HERMES_HOME') || path.join(home(), '.hermes')) || !!onPath('hermes'),
    note: 'O Hermes pode editar skills locais (curadoria). Reinstalar sobrescreve essas edições.',
  },
  {
    id: 'open-design', label: 'Open Design', aliases: ['opendesign', 'od'],
    kind: 'od',
    detect: () => !!findOdCli(),
    note: 'Plugin do Open Design (SKILL.md + open-design.json), instalado pelo daemon do app aberto.',
  },
  {
    // Modo skill: o Harness já lê ~/.agents/skills, a mesma pasta do Codex (shared). keepDir: essa cópia
    // é de outros agentes também, então o plugin e o uninstall do neuro-harness nunca a apagam.
    // legacy: a pasta de skills do próprio DSH ($DSH_HOME/skills) só duplicaria a skill (e venceria o plugin).
    id: 'neuro-harness', label: 'Neuro Harness', aliases: ['dsh', 'deepseek-harness', 'neuroharness'],
    kind: 'dir', plugin: 'harness', defaultMode: 'plugin', shared: 'universal', keepDir: true,
    dir: () => path.join(home(), '.agents', 'skills'),
    detect: () => exists(harnessPaths().profileDir),
    legacy: () => [path.join(harnessPaths().dshHome, 'skills')],
    note: 'Em modo skill, o Neuro Harness lê ~/.agents/skills (a mesma cópia do Codex). Abra uma sessão nova (ou neuro-harness restart).',
  },
  {
    id: 'gemini-cli', label: 'Gemini CLI', aliases: ['gemini'],
    kind: 'dir', dir: () => path.join(home(), '.gemini', 'skills'),
    detect: () => !!onPath('gemini'),
  },
  {
    id: 'antigravity', label: 'Antigravity', aliases: [],
    kind: 'dir', dir: () => path.join(home(), '.gemini', 'antigravity', 'skills'),
    detect: () => exists(path.join(home(), '.gemini', 'antigravity')),
  },
  {
    id: 'antigravity-cli', label: 'Antigravity CLI', aliases: [],
    kind: 'dir', dir: () => path.join(home(), '.gemini', 'antigravity-cli', 'skills'),
    detect: () => exists(path.join(home(), '.gemini', 'antigravity-cli')),
  },
  {
    id: 'cursor', label: 'Cursor', aliases: ['cursor-agent'],
    kind: 'dir', dir: () => path.join(home(), '.cursor', 'skills'),
    detect: () => exists(path.join(home(), '.cursor')) || !!onPath('cursor-agent'),
  },
];

// Nenhuma pasta legada: ~/.gemini/config/skills é para onde o Antigravity migra a sua pasta de skills
// (~/.gemini/antigravity/skills vira um link para ela), então continua sendo um destino válido.
const LEGACY_DIRS = () => [];

function resolveAgents(spec) {
  if (!spec || !spec.length) return null;
  const out = [];
  for (const raw of spec) {
    for (const token of String(raw).split(',').map((s) => s.trim().toLowerCase()).filter(Boolean)) {
      if (token === 'all' || token === '*') return AGENTS.slice();
      const a = AGENTS.find((x) => x.id === token || x.aliases.includes(token));
      if (!a) throw new Error(`Agente desconhecido: "${token}". Opções: ${AGENTS.map((x) => x.id).join(', ')}`);
      if (!out.includes(a)) out.push(a);
    }
  }
  return out;
}

// ───────────────────────── leitura de SKILL.md ─────────────────────────

function readFrontmatter(skillDir) {
  const p = path.join(skillDir, 'SKILL.md');
  let txt;
  try { txt = fs.readFileSync(p, 'utf8'); } catch { return null; }
  const m = txt.match(/^---\s*\n([\s\S]*?)\n---/);
  if (!m) return { raw: txt, name: null, description: null };
  const get = (k) => { const r = m[1].match(new RegExp(`^${k}:\\s*(.+)$`, 'm')); return r ? r[1].trim().replace(/^["']|["']$/g, '') : null; };
  return { raw: txt, name: get('name'), description: get('description') };
}

function readMarker(dir) {
  try { return JSON.parse(fs.readFileSync(path.join(dir, MARKER), 'utf8')); } catch { return null; }
}

function skillVersion(dir) {
  const mk = readMarker(dir);
  if (mk && mk.version) return mk.version;
  try { return JSON.parse(fs.readFileSync(path.join(dir, 'package.json'), 'utf8')).version || null; } catch { return null; }
}

/** Valida o formato aceito por Claude Code, Codex (≤64/≤1024), OpenCode (regex + nome = pasta) e Hermes (≤1024). */
function validateSkill(dir, expectedName = SKILL_NAME) {
  const fm = readFrontmatter(dir);
  const problems = [];
  if (!fm) return ['SKILL.md ausente'];
  if (!fm.name) problems.push('frontmatter sem `name`');
  else {
    if (!/^[a-z0-9]+(-[a-z0-9]+)*$/.test(fm.name)) problems.push(`name "${fm.name}" fora do padrão a-z0-9-`);
    if (fm.name.length > 64) problems.push('name com mais de 64 caracteres');
    if (fm.name !== expectedName) problems.push(`name "${fm.name}" difere da pasta "${expectedName}"`);
  }
  if (!fm.description) problems.push('frontmatter sem `description`');
  else if (fm.description.length > 1024) problems.push(`description com ${fm.description.length} caracteres (limite 1024 no Codex/OpenCode/Hermes)`);
  // Frases que o filtro de skills do Hermes recusa. Montadas em tempo de execução para que o próprio
  // instalador não seja confundido com uma tentativa de injeção pelos scanners de segurança.
  const bad = [['ignore', 'previous', 'instructions'], ['ignore', 'all', 'previous'], ['you', 'are', 'now'], ['disregard', 'your'],
    ['forget', 'your', 'instructions'], ['new', 'instructions:'], ['system', 'prompt:'], ['<', 'system>'], [']]', '>']]
    .map((w) => (w[0] === '<' || w[0] === ']]' ? w.join('') : w.join(' ')));
  const low = fm.raw.toLowerCase();
  for (const b of bad) if (low.includes(b)) problems.push(`trecho bloqueado pelo filtro do Hermes: "${b}"`);
  // YAML estrito (Codex, OpenCode, Hermes): escalar sem aspas não pode conter ": " nem " #"
  const header = (fm.raw.match(/^---\s*\n([\s\S]*?)\n---/) || [])[1] || '';
  for (const line of header.split('\n')) {
    const mm = line.match(/^([A-Za-z_-]+):\s*(.+)$/);
    if (!mm) continue;
    const v = mm[2].trim();
    if (!/^["'>|\[{]/.test(v) && (/:\s/.test(v) || /\s#/.test(v))) problems.push(`frontmatter \`${mm[1]}\` precisa de aspas (YAML estrito recusa ": " ou " #" sem aspas)`);
  }
  return problems;
}

// ───────────────────────── cópia segura ─────────────────────────

function isOurs(dir) {
  if (!exists(dir)) return false;
  const st = fs.lstatSync(dir);
  if (st.isSymbolicLink()) {
    const fm = readFrontmatter(dir);
    return !fm || fm.name === SKILL_NAME; // link quebrado ou link para a nossa skill
  }
  const fm = readFrontmatter(dir);
  return !!(fm && fm.name === SKILL_NAME);
}

function samePath(a, b) {
  try { return fs.realpathSync(a) === fs.realpathSync(b); } catch { return path.resolve(a) === path.resolve(b); }
}

function copyFilter(src) {
  const base = path.basename(src);
  if (COPY_EXCLUDE.has(base)) return false;
  if (base.endsWith('.pyc') || base.startsWith('._')) return false;
  return true;
}

/**
 * Instala `source` em `<parent>/neuro-mv-edit`.
 * Nunca apaga: a própria fonte, um checkout git (clone de desenvolvimento) ou uma pasta com outra skill.
 */
function placeSkill({ source, parent, mode, linkTo, dryRun, agentId, version }) {
  const target = path.join(parent, SKILL_NAME);
  if (exists(target) && samePath(target, source)) return { status: 'source', target, msg: 'é a própria fonte (nada a fazer)' };
  if (exists(target) && !fs.lstatSync(target).isSymbolicLink() && exists(path.join(target, '.git'))) {
    if (!exists(path.join(target, 'SKILL.md')) && exists(path.join(target, 'skills', SKILL_NAME, 'SKILL.md'))) {
      return { status: 'skipped', target, msg: 'é um clone do repositório (layout com skills/): este agente não vê SKILL.md na raiz dele. Mova o clone para fora desta pasta (ex.: ~/code/neuro-mv-edit) e rode install de novo' };
    }
    return { status: 'skipped', target, msg: 'checkout git (clone de desenvolvimento): atualize com git pull' };
  }
  if (exists(target) && !isOurs(target)) return { status: 'skipped', target, msg: 'já existe outra skill com este nome; não sobrescrevi' };
  if (dryRun) return { status: 'dry-run', target, msg: mode === 'link' && linkTo ? `link → ${linkTo}` : (exists(target) ? 'substituiria a instalação existente' : 'instalaria') };

  fs.mkdirSync(parent, { recursive: true });
  if (mode === 'link' && linkTo && !samePath(linkTo, target)) {
    if (exists(target)) fs.rmSync(target, { recursive: true, force: true });
    fs.symlinkSync(linkTo, target, process.platform === 'win32' ? 'junction' : 'dir');
    return { status: 'linked', target, msg: `link → ${linkTo}` };
  }
  const tmp = path.join(parent, `.${SKILL_NAME}.tmp-${process.pid}`);
  fs.rmSync(tmp, { recursive: true, force: true });
  fs.cpSync(source, tmp, { recursive: true, filter: copyFilter, dereference: true });
  fs.writeFileSync(path.join(tmp, MARKER), JSON.stringify({
    name: SKILL_NAME, version, agent: agentId, mode: 'copy', source: path.resolve(source), installed_at: new Date().toISOString(),
  }, null, 2) + '\n');
  const replaced = exists(target);
  if (replaced) fs.rmSync(target, { recursive: true, force: true });
  fs.renameSync(tmp, target);
  return { status: replaced ? 'updated' : 'installed', target, msg: replaced ? 'atualizada' : 'instalada' };
}

function removeSkill(parent, dryRun) {
  const target = path.join(parent, SKILL_NAME);
  if (!exists(target)) return { status: 'absent', target };
  if (!fs.lstatSync(target).isSymbolicLink() && exists(path.join(target, '.git'))) return { status: 'skipped', target, msg: 'checkout git: não removo' };
  if (!isOurs(target)) return { status: 'skipped', target, msg: 'não é a neuro-mv-edit' };
  if (dryRun) return { status: 'dry-run', target, msg: 'removeria' };
  fs.rmSync(target, { recursive: true, force: true });
  return { status: 'removed', target };
}

// ───────────────────────── Open Design (plugin) ─────────────────────────
//
// A pasta skills/neuro-mv-edit é, ela mesma, um plugin do Open Design (SKILL.md + open-design.json).
// Instalação local → `od plugin install <pasta>` (entra como trusted); remota → github:<repo>/skills/neuro-mv-edit.

const OD_GITHUB_SOURCE = `github:${DEFAULT_REPO}/skills/${SKILL_NAME}`;

function findOdCli() {
  const cands = [];
  if (env('OD_CLI')) cands.push(env('OD_CLI'));
  cands.push('/Applications/Open Design.app/Contents/Resources/app/prebundled/daemon/daemon-cli.mjs');
  cands.push(path.join(home(), 'Applications/Open Design.app/Contents/Resources/app/prebundled/daemon/daemon-cli.mjs'));
  const named = onPath('open-design');
  if (named) cands.push(named);
  const od = onPath('od');
  // `od` também é o dump octal do Unix: só vale se o help disser que é o OpenDesign
  if (od && /open\s?design|daemon/i.test((spawnSync(od, ['--help'], { encoding: 'utf8', timeout: 10000 }).stdout || ''))) cands.push(od);
  for (const c of cands) if (c && exists(c)) return c;
  return null;
}

/** Testa uma URL de daemon do Open Design: /api/skills precisa responder JSON com `skills`. */
function probeOd(url) {
  const r = spawnSync(process.execPath, ['-e', `fetch(${JSON.stringify(url + '/api/skills')},{signal:AbortSignal.timeout(2500)}).then(r=>r.json()).then(j=>process.exit(Array.isArray(j.skills)?0:1)).catch(()=>process.exit(1))`], { timeout: 8000 });
  return r.status === 0;
}

/**
 * O app desktop sobe o daemon numa porta efêmera; o CLI só a descobre de dentro do app.
 * Ordem: OD_DAEMON_URL → portas abertas pelo processo "Open Design" (lsof) → 7456 (padrão do `od` headless).
 */
function discoverOdDaemon() {
  const cands = [];
  if (env('OD_DAEMON_URL')) cands.push(env('OD_DAEMON_URL').replace(/\/$/, ''));
  if (process.platform !== 'win32' && onPath('lsof')) {
    const r = spawnSync('lsof', ['-nP', '-iTCP', '-sTCP:LISTEN'], { encoding: 'utf8', timeout: 10000 });
    for (const line of (r.stdout || '').split('\n')) {
      if (!/^Open\\x20D|^Open Design|^open-desi/i.test(line)) continue;
      const m = line.match(/127\.0\.0\.1:(\d+)/);
      if (m) cands.push(`http://127.0.0.1:${m[1]}`);
    }
  }
  cands.push('http://127.0.0.1:7456');
  for (const c of [...new Set(cands)]) if (probeOd(c)) return c;
  return null;
}

function runOd(cli, args, daemonUrl) {
  const full = daemonUrl ? [...args, '--daemon-url', daemonUrl] : args;
  const isScript = /\.(mjs|js)$/.test(cli);
  const res = spawnSync(isScript ? process.execPath : cli, isScript ? [cli, ...full] : full, { encoding: 'utf8', timeout: 240000 });
  return { code: res.status, out: (res.stdout || '').trim(), err: (res.stderr || '').trim() };
}

function odPluginInfo(cli, url) {
  const r = runOd(cli, ['plugin', 'info', SKILL_NAME], url);
  if (r.code !== 0) return null;
  try { const d = JSON.parse(r.out); return d.plugin || d; } catch { return null; }
}

function installOpenDesign({ dryRun, source, localDir }) {
  const cli = findOdCli();
  if (!cli) return { status: 'missing', msg: `Open Design não encontrado (open-design.ai). No app: Plugins → instalar de ${OD_GITHUB_SOURCE}` };
  const url = discoverOdDaemon();
  if (!url) return { status: 'pending', msg: `daemon do Open Design fora do ar: abra o app e rode de novo com --agent open-design` };
  const src = source || (localDir && exists(path.join(localDir, 'open-design.json')) ? localDir : OD_GITHUB_SOURCE);
  const before = odPluginInfo(cli, url);
  if (dryRun) return { status: 'dry-run', msg: `${before ? 'reinstalaria' : 'instalaria'} o plugin de ${src} (daemon ${url})` };
  // O daemon baixa github:<dono>/<repo> pela API pública. Confere o acesso ANTES de remover a versão atual,
  // para não deixar o Open Design sem o plugin se a busca falhar (ex.: repositório privado → 404).
  const gh = String(src).match(/^github:([^/@]+)\/([^/@]+)/);
  if (gh) {
    const probe = spawnSync(process.execPath, ['-e', `fetch('https://api.github.com/repos/${gh[1]}/${gh[2]}',{signal:AbortSignal.timeout(8000)}).then(r=>process.exit(r.ok?0:r.status===404?4:1)).catch(()=>process.exit(1))`], { timeout: 15000 });
    if (probe.status === 4) return { status: 'error', msg: `github:${gh[1]}/${gh[2]} não é acessível pela API pública (repositório privado?). Nada foi alterado. Use --od-source <clone>/skills/${SKILL_NAME}` };
  }
  if (before) {
    const un = runOd(cli, ['plugin', 'uninstall', SKILL_NAME], url);
    if (un.code !== 0) return { status: 'error', msg: `falha ao remover a versão anterior: ${(un.err || un.out).slice(0, 200)}` };
  }
  const r = runOd(cli, ['plugin', 'install', src, '--json'], url);
  if (r.code !== 0 || /"code":\s*"FETCH_FAILED"/.test(r.out)) {
    const privateHint = String(src).startsWith('github:') && /404/.test(r.err + r.out)
      ? ' — o Open Design baixa pela API pública do GitHub e recebe 404 em repositório privado; instale de uma pasta local com --od-source <clone>/skills/neuro-mv-edit'
      : '';
    return { status: 'error', msg: (r.err || r.out).slice(0, 240) + privateHint };
  }
  const after = odPluginInfo(cli, url);
  const trust = after ? after.trust : '?';
  const hint = trust === 'trusted' ? '' : ` — conceda as capacidades: od plugin trust ${SKILL_NAME} --capabilities bash,network,fs:read,fs:write`;
  return { status: before ? 'updated' : 'installed', msg: `plugin v${after ? after.version : '?'} (${trust}) via daemon ${url}${hint}` };
}

function uninstallOpenDesign(dryRun) {
  const cli = findOdCli();
  if (!cli) return { status: 'absent' };
  const url = discoverOdDaemon();
  if (!url) return { status: 'pending', msg: 'daemon do Open Design fora do ar (abra o app)' };
  if (!odPluginInfo(cli, url)) return { status: 'absent' };
  if (dryRun) return { status: 'dry-run', msg: 'removeria o plugin do Open Design' };
  const r = runOd(cli, ['plugin', 'uninstall', SKILL_NAME], url);
  return r.code === 0 ? { status: 'removed', msg: 'plugin removido do Open Design' } : { status: 'error', msg: (r.err || r.out).slice(0, 200) };
}

// ───────────────────────── OpenCode (plugin V2) ─────────────────────────
//
// ~/.config/opencode/plugins/neuro-mv-edit/{server.js, package.json, skill/}: o OpenCode descobre a pasta
// sozinho e o server.js registra a skill via ctx.skill.transform (verificado em GET /api/skill).

function openCodePluginDir() {
  return path.join(xdgConfig(), 'opencode', 'plugins', SKILL_NAME);
}

function isOurOpenCodePlugin(dir) {
  if (!exists(dir)) return false;
  if (fs.lstatSync(dir).isSymbolicLink()) return true;
  try { return fs.readFileSync(path.join(dir, 'server.js'), 'utf8').includes('"neuro-mv-edit"'); } catch { return false; }
}

function placeOpenCodePlugin({ pkgRoot, skillDir, dryRun, version }) {
  const target = openCodePluginDir();
  const pluginSrc = path.join(pkgRoot, 'plugins', 'opencode');
  if (!exists(path.join(pluginSrc, 'server.js'))) return { status: 'error', target, msg: 'plugins/opencode/server.js não encontrado na fonte' };
  if (exists(target) && !isOurOpenCodePlugin(target)) return { status: 'skipped', target, msg: 'já existe outro plugin com este nome; não sobrescrevi' };
  if (dryRun) return { status: 'dry-run', target, msg: exists(target) ? 'substituiria o plugin' : 'instalaria o plugin' };
  const parent = path.dirname(target);
  fs.mkdirSync(parent, { recursive: true });
  const tmp = path.join(parent, `.${SKILL_NAME}.tmp-${process.pid}`);
  fs.rmSync(tmp, { recursive: true, force: true });
  fs.mkdirSync(tmp, { recursive: true });
  for (const f of ['server.js', 'package.json']) fs.copyFileSync(path.join(pluginSrc, f), path.join(tmp, f));
  fs.cpSync(skillDir, path.join(tmp, 'skill'), { recursive: true, filter: copyFilter, dereference: true });
  fs.writeFileSync(path.join(tmp, MARKER), JSON.stringify({ name: SKILL_NAME, version, agent: 'opencode', mode: 'plugin', source: path.resolve(pkgRoot), installed_at: new Date().toISOString() }, null, 2) + '\n');
  const replaced = exists(target);
  if (replaced) fs.rmSync(target, { recursive: true, force: true });
  fs.renameSync(tmp, target);
  return { status: replaced ? 'updated' : 'installed', target, msg: `plugin OpenCode ${replaced ? 'atualizado' : 'instalado'}` };
}

function removeOpenCodePlugin(dryRun) {
  const target = openCodePluginDir();
  if (!exists(target)) return { status: 'absent', target };
  if (!isOurOpenCodePlugin(target)) return { status: 'skipped', target, msg: 'não é o plugin da neuro-mv-edit' };
  if (dryRun) return { status: 'dry-run', target, msg: 'removeria o plugin' };
  fs.rmSync(target, { recursive: true, force: true });
  return { status: 'removed', target };
}

// ───────────────────────── Claude Code (plugin) ─────────────────────────

function claudeRun(args) {
  const r = spawnSync('claude', args, { encoding: 'utf8', timeout: 240000 });
  return { code: r.status, out: ((r.stdout || '') + (r.stderr || '')).replace(/\x1b\[[0-9;]*m/g, '').trim() };
}

function claudeJson(args) {
  const r = spawnSync('claude', [...args, '--json'], { encoding: 'utf8', timeout: 240000 });
  const text = (r.stdout || '').trim();
  try {
    return JSON.parse(text);
  } catch {
    const last = text.split('\n').filter((l) => l.trim().startsWith('{') || l.trim().startsWith('[')).pop();
    try { return last ? JSON.parse(last) : null; } catch { return null; }
  }
}

const PLUGIN_ID = `${SKILL_NAME}@${SKILL_NAME}`;

/** Origem do marketplace: clone git → a pasta (desenvolvimento); senão o GitHub travado na tag da versão. */
function claudeSource(pkgRoot, version) {
  if (exists(path.join(pkgRoot, '.git'))) return { arg: pkgRoot, match: (m) => m.source === 'directory' && samePath(m.path || '', pkgRoot), label: pkgRoot };
  const ref = `v${version}`;
  return { arg: `${DEFAULT_REPO}#${ref}`, match: (m) => m.repo === DEFAULT_REPO && m.ref === ref, label: `${DEFAULT_REPO}#${ref}` };
}

function claudePluginState() {
  const list = claudeJson(['plugin', 'list']);
  return Array.isArray(list) ? list.find((p) => p.id === PLUGIN_ID) || null : null;
}

function installClaudePlugin({ pkgRoot, dryRun, version }) {
  if (!onPath('claude')) return { status: 'missing', msg: 'CLI `claude` não encontrado' };
  const src = claudeSource(pkgRoot, version);
  const markets = claudeJson(['plugin', 'marketplace', 'list']) || [];
  const market = markets.find((m) => m.name === SKILL_NAME);
  const before = claudePluginState();
  if (dryRun) {
    const steps = [];
    if (!market || !src.match(market)) steps.push(`marketplace add ${src.label}`);
    else steps.push(`marketplace update ${SKILL_NAME}`);
    steps.push(before ? `plugin update ${PLUGIN_ID}` : `plugin install ${PLUGIN_ID} --scope user`);
    return { status: 'dry-run', msg: `claude ${steps.join(' && claude ')}` };
  }
  // marketplace: adiciona, ou reaponta (o `add` com outra origem troca a origem do marketplace existente)
  let repointed = false;
  if (!market || !src.match(market)) {
    const addArgs = ['plugin', 'marketplace', 'add', src.arg, '--scope', 'user'];
    let add = claudeJson(addArgs);
    if ((!add || add.outcome !== 'ok') && market) {
      // origem antiga declarada em extraKnownMarketplaces (instalações anteriores) não deixa reapontar:
      // remove o marketplace (leva junto o plugin instalado dele) e adiciona de novo pela origem certa
      const rm = claudeJson(['plugin', 'marketplace', 'remove', SKILL_NAME]);
      if (rm && rm.outcome === 'ok') {
        add = claudeJson(addArgs);
        repointed = true;
      }
    }
    if (!add || add.outcome !== 'ok') return { status: 'error', msg: `marketplace add ${src.label}: ${((add && add.message) || 'falhou (acesso ao repositório privado? rode gh auth login && gh auth setup-git)').slice(-300)}` };
  } else {
    claudeJson(['plugin', 'marketplace', 'update', SKILL_NAME]);
  }
  // o estado pode ter mudado (remover o marketplace desinstala o plugin dele)
  const current = repointed ? claudePluginState() : before;
  const r = current ? claudeJson(['plugin', 'update', PLUGIN_ID]) : claudeJson(['plugin', 'install', PLUGIN_ID, '--scope', 'user']);
  if (!r || r.outcome !== 'ok') return { status: 'error', msg: ((r && r.message) || 'falhou').slice(-300) };
  let after = claudePluginState();
  if (after && !after.enabled) {
    claudeJson(['plugin', 'enable', PLUGIN_ID]);
    after = claudePluginState();
  }
  if (!after) return { status: 'error', msg: 'o Claude Code não listou o plugin depois da instalação' };
  const local = src.label === pkgRoot;
  const warn = !local && after.version !== version ? ` (esperada v${version})` : '';
  return {
    status: warn ? 'error' : before ? 'updated' : 'installed',
    msg: `plugin v${after.version}${warn}${after.enabled ? '' : ' DESATIVADO'} · marketplace ${src.label}`,
  };
}

function uninstallClaudePlugin(dryRun, { keepMarketplace = false } = {}) {
  if (!onPath('claude')) return { status: 'absent' };
  const installed = claudePluginState();
  const market = (claudeJson(['plugin', 'marketplace', 'list']) || []).find((m) => m.name === SKILL_NAME);
  if (!installed && (keepMarketplace || !market)) return { status: 'absent' };
  if (dryRun) return { status: 'dry-run', msg: `removeria o plugin${keepMarketplace ? '' : ' e o marketplace'} do Claude Code` };
  if (installed) claudeJson(['plugin', 'uninstall', PLUGIN_ID]);
  if (market && !keepMarketplace) claudeJson(['plugin', 'marketplace', 'remove', SKILL_NAME]);
  return { status: 'removed', msg: `plugin${keepMarketplace ? '' : ' e marketplace'} removidos do Claude Code` };
}

// ───────────────────────── Hermes (plugin portátil Agent Plugins v1) ─────────────────────────

function hermesRun(args) {
  const r = spawnSync('hermes', args, { encoding: 'utf8', timeout: 300000 });
  return { code: r.status, out: ((r.stdout || '') + (r.stderr || '')).replace(/\x1b\[[0-9;]*m/g, '').trim() };
}

function hermesPluginLine() {
  return hermesRun(['plugins', 'list']).out.split('\n').find((l) => /\bneuro-mv-edit\b/.test(l)) || null;
}

/** SHA do commit da tag (o Hermes só trava versão por SHA de 40 caracteres). Usa o git e as credenciais da máquina. */
function tagSha(version) {
  const url = `https://github.com/${DEFAULT_REPO}.git`;
  const r = spawnSync('git', ['ls-remote', url, `refs/tags/v${version}^{}`, `refs/tags/v${version}`], { encoding: 'utf8', timeout: 60000, env: { ...process.env, GIT_TERMINAL_PROMPT: '0' } });
  const lines = (r.stdout || '').trim().split('\n').filter(Boolean);
  const peeled = lines.find((l) => l.endsWith('^{}')) || lines[0];
  const sha = peeled ? peeled.split(/\s+/)[0] : '';
  return /^[0-9a-f]{40}$/.test(sha) ? sha : null;
}

function installHermesPlugin({ dryRun, version, pkgRoot }) {
  if (!onPath('hermes')) return { status: 'missing', msg: 'CLI `hermes` não encontrado' };
  const dev = pkgRoot && exists(path.join(pkgRoot, '.git'));
  const already = Boolean(hermesPluginLine());
  if (dryRun) return { status: 'dry-run', msg: `hermes plugins install ${DEFAULT_REPO}${dev ? '' : ` --ref <SHA de v${version}>`} --enable --yes-deps${already ? ' --force' : ''}` };
  const sha = dev ? null : tagSha(version);
  const args = ['plugins', 'install', DEFAULT_REPO, '--enable', '--yes-deps', ...(sha ? ['--ref', sha] : []), ...(already ? ['--force'] : [])];
  const r = hermesRun(args);
  if (r.code !== 0) return { status: 'error', msg: r.out.slice(-300) };
  const line = hermesPluginLine();
  if (!line) return { status: 'error', msg: 'o Hermes não listou o plugin depois da instalação' };
  const ref = sha ? `v${version} (${sha.slice(0, 7)})` : dev ? 'main (desenvolvimento)' : 'main (tag não encontrada)';
  return { status: already ? 'updated' : 'installed', msg: `plugin ${ref}, habilitado` };
}

function uninstallHermesPlugin(dryRun) {
  if (!onPath('hermes')) return { status: 'absent' };
  if (!hermesPluginLine()) return { status: 'absent' };
  if (dryRun) return { status: 'dry-run', msg: 'removeria o plugin do Hermes' };
  const r = hermesRun(['plugins', 'remove', SKILL_NAME]);
  return r.code === 0 ? { status: 'removed', msg: 'plugin removido do Hermes' } : { status: 'error', msg: r.out.slice(-200) };
}

// ───────────────────────── Neuro Harness (plugin do DeepSeek Harness) ─────────────────────────
//
// O Neuro Harness é o DeepSeek Harness (dsh) com o perfil `neuro`. O pacote inteiro é o plugin: o
// package.json declara `dsh.bundle.patch` (plugins/dsh/cordis.patch.yml), e o `dsh plugin add` instala
// pelo pnpm do perfil e liga o pacote em `dsh.profile.bundles`. Clone git → link:<pasta>; senão a tag no GitHub.

const HARNESS_HOMES = () => [path.join(home(), '.neuro-harness'), path.join(home(), '.neuro-mv-superagent')];

function harnessPaths() {
  const profile = env('NEURO_HARNESS_PROFILE') || 'neuro';
  const base = env('NEURO_HARNESS_HOME')
    ? path.resolve(env('NEURO_HARNESS_HOME'))
    : HARNESS_HOMES().find((h) => exists(path.join(h, 'dsh', 'profiles', profile))) || HARNESS_HOMES()[0];
  const dshHome = path.join(base, 'dsh');
  return { base, profile, dshHome, profileDir: path.join(dshHome, 'profiles', profile), runtime: path.join(base, 'runtime') };
}

/** O `dsh` do runtime do Neuro Harness: o .bin no macOS/Linux, ou o bin.js pelo Node (Windows, .bin ausente). */
function harnessDsh(h = harnessPaths()) {
  const bin = path.join(h.runtime, 'node_modules', '.bin', 'dsh');
  if (process.platform !== 'win32' && exists(bin)) return { cmd: bin, pre: [], label: bin };
  const js = path.join(h.runtime, 'node_modules', '@deepseek-ai', 'dsh', 'lib', 'bin.js');
  if (exists(js)) return { cmd: process.execPath, pre: [js], label: js };
  return null;
}

function runDsh(h, args, timeout = 600000) {
  const cli = harnessDsh(h);
  const r = spawnSync(cli.cmd, [...cli.pre, ...args], { encoding: 'utf8', timeout, env: { ...process.env, DSH_HOME: h.dshHome } });
  const out = ((r.stdout || '') + (r.stderr || '')).replace(/\x1b\[[0-9;]*m/g, '').trim();
  return { code: r.error ? -1 : r.status, out: r.error ? String(r.error.message || r.error) : out };
}

function readJson(p) {
  try { return JSON.parse(fs.readFileSync(p, 'utf8')); } catch { return null; }
}

/** Estado do plugin no perfil: spec da dependência, versão instalada e se está em dsh.profile.bundles. */
function harnessPluginState(h = harnessPaths()) {
  const manifest = readJson(path.join(h.profileDir, 'package.json'));
  const spec = manifest && manifest.dependencies ? manifest.dependencies[SKILL_NAME] : undefined;
  const installed = readJson(path.join(h.profileDir, 'node_modules', SKILL_NAME, 'package.json'));
  if (!spec && !installed) return null;
  const bundles = (manifest && manifest.dsh && manifest.dsh.profile && manifest.dsh.profile.bundles) || [];
  return { spec: spec || null, version: installed ? installed.version : null, enabled: bundles.includes(SKILL_NAME) };
}

/** Origem do plugin: clone git → link:<pasta> (desenvolvimento); senão o GitHub travado na tag da versão. */
function harnessSpec(pkgRoot, version) {
  return exists(path.join(pkgRoot, '.git')) ? `link:${path.resolve(pkgRoot)}` : `github:${DEFAULT_REPO}#v${version}`;
}

const tilde = (p) => String(p).replace(home(), '~');

function installHarnessPlugin({ pkgRoot, dryRun, version }) {
  const h = harnessPaths();
  if (!exists(h.profileDir)) return { status: 'missing', msg: `Neuro Harness não encontrado (perfil "${h.profile}" em ${tilde(h.profileDir)}; ajuste NEURO_HARNESS_HOME / NEURO_HARNESS_PROFILE)` };
  const cli = harnessDsh(h);
  if (!cli) return { status: 'missing', msg: `CLI dsh do Neuro Harness não encontrado em ${tilde(h.runtime)} (rode neuro-harness start, que instala o runtime)` };
  const spec = harnessSpec(pkgRoot, version);
  const before = harnessPluginState(h);
  const args = ['plugin', '--profile', h.profile, 'add', spec];
  if (dryRun) {
    const now = before ? ` (hoje: ${before.spec || '?'}${before.version ? ` v${before.version}` : ''})` : '';
    return { status: 'dry-run', msg: `DSH_HOME=${tilde(h.dshHome)} dsh ${args.join(' ')}${now}` };
  }
  const r = runDsh(h, args);
  if (r.code !== 0) {
    const hint = spec.startsWith('github:') && /404|401|403|auth|could not read|Permission denied|ERR_PNPM_FETCH/i.test(r.out)
      ? ' — o repositório é privado: gh auth login && gh auth setup-git (ou chave SSH), ou instale de um clone (link:)'
      : '';
    return { status: 'error', msg: `dsh plugin add falhou: ${r.out.slice(-300)}${hint}` };
  }
  const after = harnessPluginState(h);
  if (!after || !after.version) return { status: 'error', msg: `o perfil ${h.profile} não mostra o neuro-mv-edit depois do dsh plugin add` };
  const local = spec.startsWith('link:');
  const warn = !local && after.version !== version ? ` (esperada v${version})` : '';
  const off = after.enabled ? '' : ' DESATIVADO no perfil (ative em Settings → Plugins)';
  return {
    status: warn ? 'error' : before ? 'updated' : 'installed',
    msg: `plugin v${after.version}${warn}${off} · ${local ? `link → ${tilde(pkgRoot)}` : spec} · perfil ${h.profile}. Reinicie o Harness (neuro-harness restart)`,
  };
}

function uninstallHarnessPlugin(dryRun) {
  const h = harnessPaths();
  if (!exists(h.profileDir)) return { status: 'absent' };
  const st = harnessPluginState(h);
  if (!st) return { status: 'absent' };
  if (!harnessDsh(h)) return { status: 'error', msg: `CLI dsh não encontrado em ${tilde(h.runtime)}; remova à mão: DSH_HOME=${tilde(h.dshHome)} dsh plugin --profile ${h.profile} remove ${SKILL_NAME}` };
  const args = ['plugin', '--profile', h.profile, 'remove', SKILL_NAME];
  if (dryRun) return { status: 'dry-run', msg: `DSH_HOME=${tilde(h.dshHome)} dsh ${args.join(' ')}` };
  const r = runDsh(h, args);
  if (r.code !== 0) return { status: 'error', msg: `dsh plugin remove falhou: ${r.out.slice(-300)}` };
  return harnessPluginState(h)
    ? { status: 'error', msg: `o perfil ${h.profile} ainda lista o neuro-mv-edit depois do remove` }
    : { status: 'removed', msg: `plugin removido do perfil ${h.profile} do Neuro Harness` };
}

/** Linha do --deep: runtime, plugin e quem vence a skill no registro do Harness. */
function harnessDeep(mode) {
  const h = harnessPaths();
  if (!exists(h.profileDir)) return `Neuro Harness: perfil "${h.profile}" não encontrado em ${tilde(h.profileDir)}`;
  const cli = harnessDsh(h);
  const dshVersion = cli ? (runDsh(h, ['--version'], 30000).out.split('\n').pop() || '?') : 'runtime ausente';
  const st = harnessPluginState(h);
  const parts = [`Neuro Harness (dsh ${dshVersion}, perfil ${h.profile})`];
  if (st) parts.push(`plugin v${st.version || '? (dependência sem node_modules: dsh plugin --profile ' + h.profile + ' install)'} · ${st.spec || '?'} · ${st.enabled ? 'ativo (skill + neuro-mv-edit no PATH)' : 'DESATIVADO no perfil'}`);
  else parts.push(mode === 'plugin' ? 'plugin não instalado' : 'sem plugin; a skill vem de ~/.agents/skills');
  // Precedência do registro de skills do Harness: menor vence. ~/.agents/skills (user-agents, 500) e
  // $DSH_HOME/skills (user-dsh, 400) ganham do plugin (bundled, 600); avisa quando a versão difere.
  for (const dir of [path.join(h.dshHome, 'skills'), path.join(home(), '.agents', 'skills')]) {
    const v = skillVersion(path.join(dir, SKILL_NAME));
    if (st && v && v !== st.version) parts.push(`${tilde(path.join(dir, SKILL_NAME))} (v${v}) vence a skill do plugin no Harness`);
  }
  return parts.join(' — ');
}

// ───────────────────────── verificação profunda ─────────────────────────

function deepCheck(agent, mode) {
  if (agent.id === 'hermes' && onPath('hermes')) {
    if (mode === 'plugin') {
      const line = hermesRun(['plugins', 'list']).out.split('\n').find((l) => l.includes(SKILL_NAME));
      return line ? `Hermes (plugin): ${line.replace(/[│┃]/g, ' ').replace(/\s+/g, ' ').trim()}` : 'Hermes: plugin não listado';
    }
    const out = hermesRun(['skills', 'list', '--source', 'local']).out;
    const line = out.split('\n').find((l) => l.includes(SKILL_NAME));
    if (!line) return 'Hermes não lista a skill';
    return /enabled/.test(line) ? 'Hermes: carregada (enabled)' : `Hermes: ${line.replace(/[│┃]/g, ' ').replace(/\s+/g, ' ').trim()}`;
  }
  if (agent.id === 'codex' && onPath('codex')) {
    const r = spawnSync('codex', ['debug', 'prompt-input', 'verificação neuro-mv-edit'], { encoding: 'utf8', timeout: 120000, cwd: os.tmpdir() });
    const out = r.stdout || '';
    if (out.includes(`- ${SKILL_NAME}:`)) return 'Codex: na lista de skills do modelo';
    if (out.includes(path.join(home(), '.agents', 'skills'))) return 'Codex: raiz ~/.agents/skills lida; fora do orçamento da lista visível (chame com $neuro-mv-edit)';
    return 'Codex: raiz ~/.agents/skills não apareceu no prompt';
  }
  if (agent.id === 'claude-code' && mode === 'plugin' && onPath('claude')) {
    const st = claudePluginState();
    if (!st) return 'Claude Code: plugin não instalado';
    const out = claudeRun(['plugin', 'details', PLUGIN_ID]).out;
    const n = (k) => ((out.match(new RegExp(`${k} \\((\\d+)\\)`)) || [])[1] || '0');
    return `Claude Code (plugin v${st.version}${st.enabled ? '' : ', DESATIVADO'}): ${n('Skills')} skills/comandos, ${n('Agents')} subagentes, ${n('MCP servers')} MCP`;
  }
  if (agent.id === 'neuro-harness') return harnessDeep(mode);
  if (agent.id === 'open-design') {
    const cli = findOdCli();
    if (!cli) return 'Open Design: app não encontrado';
    const url = discoverOdDaemon();
    if (!url) return 'Open Design: daemon fora do ar (abra o app)';
    const info = odPluginInfo(cli, url);
    return info ? `Open Design: plugin v${info.version} (${info.trust}) — daemon ${url}` : 'Open Design: plugin não instalado';
  }
  return null;
}

module.exports = {
  AGENTS, LEGACY_DIRS, SKILL_NAME, MARKER, DEFAULT_REPO, OD_GITHUB_SOURCE,
  resolveAgents, validateSkill, readFrontmatter, readMarker, skillVersion,
  placeSkill, removeSkill, isOurs, samePath, exists, onPath,
  findOdCli, discoverOdDaemon, installOpenDesign, uninstallOpenDesign,
  openCodePluginDir, placeOpenCodePlugin, removeOpenCodePlugin,
  installClaudePlugin, uninstallClaudePlugin, installHermesPlugin, uninstallHermesPlugin,
  harnessPaths, harnessPluginState, harnessSpec, installHarnessPlugin, uninstallHarnessPlugin,
  deepCheck, claudePluginState, hermesPluginLine, PLUGIN_ID,
};

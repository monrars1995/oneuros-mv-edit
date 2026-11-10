/**
 * Assistentes interativos do CLI: `setup` (agentes + extras + primeiro perfil) e a biblioteca
 * `perfil` / `tema` / `estilo` (listar, mostrar, novo, editar, remover, exportar, importar, preview).
 *
 * Tudo tem forma não interativa (opções ou --json) para agentes de IA e CI, que não têm terminal.
 */
'use strict';

const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawnSync } = require('child_process');
const ui = require('./ui');
const lib = require('./library');
const agents = require('./agents');

const { C } = ui;
const tilde = (p) => String(p).replace(os.homedir(), '~');

function parseFlags(args, booleans = []) {
  const out = { _: [] };
  for (let i = 0; i < args.length; i++) {
    const a = args[i];
    if (!a.startsWith('--')) {
      out._.push(a);
      continue;
    }
    const eq = a.indexOf('=');
    const key = (eq > 0 ? a.slice(2, eq) : a.slice(2)).replace(/-([a-z])/g, (_, c) => c.toUpperCase());
    if (eq > 0) out[key] = a.slice(eq + 1);
    else if (booleans.includes(key) || i + 1 >= args.length || args[i + 1].startsWith('--')) out[key] = true;
    else out[key] = args[++i];
  }
  return out;
}

/** Mescla profunda: objetos se combinam, listas e valores do segundo substituem. */
function deepMerge(a, b) {
  if (Array.isArray(b) || typeof b !== 'object' || b === null) return b === undefined ? a : b;
  const out = { ...(typeof a === 'object' && a && !Array.isArray(a) ? a : {}) };
  for (const [k, v] of Object.entries(b)) out[k] = deepMerge(out[k], v);
  return out;
}

function accentOf(theme) {
  const c = (theme && theme.colors) || {};
  const k = Object.keys(c).find((x) => x.startsWith('highlight')) || Object.keys(c).find((x) => x.startsWith('accent') || x.startsWith('blue'));
  return (k && /^#[0-9A-Fa-f]{6}$/.test(c[k]) && c[k]) || '#FFD54A';
}

function table(rows, headers) {
  const w = headers.map((h, i) => Math.max(h.length, ...rows.map((r) => String(r[i] ?? '').length)));
  const line = (r) => r.map((x, i) => String(x ?? '').padEnd(w[i])).join('  ');
  console.log(`  ${C.bold}${line(headers)}${C.reset}`);
  rows.forEach((r) => console.log(`  ${line(r)}`));
}

function needTTY(what, alt) {
  console.log(`${C.red}${what} é interativo e este terminal não é.${C.reset} ${alt}`);
  process.exit(2);
}

function makeSetup(ctx) {
  const { SKILL_DIR, banner, runInstall, runPython } = ctx;

  // ───────────────────────────── setup ─────────────────────────────

  async function setup(args) {
    const f = parseFlags(args, ['yes', 'dryRun', 'remotion', 'skipHyperframes', 'skipVerify']);
    if (!ui.interactive() && !f.yes) {
      needTTY('O setup', 'Use `setup --yes` (agentes detectados, padrões) ou `install --agent <ids>`.');
    }
    banner();
    console.log(`${C.bold}Assistente de instalação${C.reset} ${C.gray}— escolha onde a skill entra e o que mais configurar.${C.reset}\n`);

    const list = agents.AGENTS.map((a) => {
      const detected = a.detect();
      let installed = null;
      const harness = a.plugin === 'harness' ? agents.harnessPluginState() : null;
      if (harness) installed = harness.version;
      else if (a.kind === 'dir') installed = agents.skillVersion(path.join(a.dir(), agents.SKILL_NAME));
      if (!installed && a.plugin === 'opencode') installed = agents.skillVersion(agents.openCodePluginDir());
      const where = a.plugin === 'harness' ? `perfil ${agents.harnessPaths().profile} · ${tilde(agents.harnessPaths().base)}` : a.kind === 'dir' ? tilde(a.dir()) : 'plugin pelo app';
      const label = a.id === 'universal' ? 'Agent Skills (~/.agents/skills)' : a.label;
      const extra = a.id === 'universal' ? 'Codex, Kimi, Warp, Zed, Pi…' : where;
      const hint = detected ? `${extra}${installed ? ` · v${installed} instalada` : ''}` : 'não detectado nesta máquina';
      return { a, detected, installed, label, hint };
    });
    const anyCodex = list.some((x) => x.a.id === 'codex' && x.detected);
    let chosen;
    if (f.agent) chosen = agents.resolveAgents([f.agent]).map((a) => a.id);
    else {
      chosen = await ui.multiselect({
        message: 'Em quais agentes (harness) instalar?',
        min: 1,
        choices: list.map((x) => ({
          label: x.label, value: x.a.id, hint: x.hint,
          checked: x.a.id === 'universal' ? anyCodex || Boolean(x.installed) : x.detected,
        })),
      });
    }

    const modes = {};
    const pick = async (id, message, choices) => {
      if (!chosen.includes(id)) return;
      modes[id] = await ui.select({ message, choices });
    };
    await pick('claude-code', 'Claude Code: como instalar?', [
      { label: 'Plugin (recomendado)', value: 'plugin', hint: 'skill + comandos /neuro-mv-edit:*, subagentes, ElevenLabs e `neuro-mv-edit` no PATH' },
      { label: 'Só a skill', value: 'skill', hint: 'pasta em ~/.claude/skills, sem comandos nem subagentes' },
    ]);
    await pick('opencode', 'OpenCode: como instalar?', [
      { label: 'Plugin (recomendado)', value: 'plugin', hint: 'plugin V2 que registra a skill' },
      { label: 'Skill', value: 'skill', hint: 'pasta de skills do OpenCode' },
    ]);
    await pick('hermes', 'Hermes: como instalar?', [
      { label: 'Plugin (recomendado)', value: 'plugin', hint: 'Agent Plugins travado na versão, ativado' },
      { label: 'Só a skill', value: 'skill', hint: 'pasta em ~/.hermes/skills' },
    ]);
    await pick('neuro-harness', 'Neuro Harness: como instalar?', [
      { label: 'Plugin (recomendado)', value: 'plugin', hint: 'dsh plugin add no perfil: skill + `neuro-mv-edit` no PATH das sessões' },
      { label: 'Só a skill', value: 'skill', hint: 'o Harness lê ~/.agents/skills (a mesma cópia do Codex)' },
    ]);

    const remotionReady = fs.existsSync(path.join(lib.home(), 'remotion'));
    const extras = f.yes
      ? [!f.skipHyperframes && 'hyperframes', !f.skipVerify && 'verify', f.remotion && 'remotion'].filter(Boolean)
      : await ui.multiselect({
        message: 'O que mais preparar?',
        choices: [
          { label: 'Skills oficiais do HyperFrames', value: 'hyperframes', checked: !f.skipHyperframes, hint: 'motor HyperFrames, registry e QA' },
          { label: 'Motor Remotion', value: 'remotion', checked: !remotionReady, hint: remotionReady ? 'já instalado' : '~250 MB + navegador; senão, no 1º projeto Remotion' },
          { label: 'Verificar ambiente e baixar as fontes', value: 'verify', checked: !f.skipVerify, hint: 'ffmpeg, node, Chrome, fontes oficiais' },
          { label: 'Guia do ElevenLabs MCP (SFX e trilha)', value: 'mcp', checked: false, hint: 'mostra os comandos de configuração' },
        ],
      });

    const nextStep = f.yes
      ? 'nada'
      : await ui.select({
        message: 'Perfis de edição (apresentador, tema, estilo):',
        choices: [
          { label: 'Criar um perfil novo depois da instalação', value: 'novo' },
          { label: 'Ver os perfis, temas e estilos disponíveis', value: 'listar' },
          { label: 'Agora não', value: 'nada' },
        ],
      });

    console.log(`\n${C.bold}Resumo${C.reset}`);
    console.log(`  Agentes: ${chosen.map((id) => `${id}${modes[id] ? ` (${modes[id]})` : ''}`).join(', ')}`);
    console.log(`  Extras:  ${extras.join(', ') || 'nenhum'}`);
    if (!f.yes && !(await ui.confirm({ message: 'Instalar agora?', initial: true }))) {
      console.log(`${C.gray}Nada foi alterado.${C.reset}`);
      return;
    }
    await runInstall({
      agents: chosen, modes, dryRun: Boolean(f.dryRun),
      skipHyperframes: !extras.includes('hyperframes'), skipVerify: !extras.includes('verify'), remotion: extras.includes('remotion'),
      mcp: extras.includes('mcp'), quietBanner: true,
    });
    if (f.dryRun) return;
    if (nextStep === 'novo') await perfilNovo([], {});
    else if (nextStep === 'listar') listarTudo();
    console.log(`\n${C.bold}Próximos passos${C.reset}`);
    console.log(`  ${C.gold}neuro-mv-edit perfil novo${C.reset}            cria um perfil (apresentador, tema, estilo, legendas)`);
    console.log(`  ${C.gold}neuro-mv-edit tema preview <id>${C.reset}      abre a prévia dos cartões de um tema`);
    console.log(`  ${C.gold}neuro-mv-edit projeto init --profile <id> --video bruto.mp4 --out projetos/x${C.reset}`);
    console.log(`  ${C.gray}Abra uma sessão nova de cada agente para ele carregar a skill.${C.reset}\n`);
  }

  // ───────────────────────────── listagens ─────────────────────────────

  function listarTudo() {
    listar('perfil');
    listar('tema');
    listar('estilo');
  }

  function listar(kind) {
    const items = lib.all(SKILL_DIR, kind);
    const k = lib.KINDS[kind];
    console.log(`\n${C.bold}${k.plural[0].toUpperCase() + k.plural.slice(1)}${C.reset} ${C.gray}(biblioteca do usuário em ${tilde(lib.userDir(kind))})${C.reset}`);
    const rows = Object.values(items).filter((x) => kind !== 'perfil' || x.id !== 'template_novo_perfil').map((x) => {
      const origem = x._origem === 'skill' ? 'skill' : 'você';
      if (kind === 'perfil') return [x.id, x.name, x.segment || '', x.theme_default || '', x.estilo_padrao || '—', x.engine_default || 'remotion', origem];
      if (kind === 'tema') {
        const fz = x.fonts || {};
        return [x.id, x.name, x.categoria || (x._origem === 'skill' ? 'cliente' : 'seu'), (fz.level_1_hook || {}).family || '', origem];
      }
      return [x.id, x.nome || x.name || '', `${(x.corte || {}).preset || ''} ${(x.corte || {}).limiar_ms || ''}ms`, (x.legendas || {}).animacao || '', origem];
    });
    if (kind === 'perfil') table(rows, ['id', 'nome', 'segmento', 'tema', 'estilo', 'motor', 'origem']);
    else if (kind === 'tema') table(rows, ['id', 'nome', 'tipo', 'fonte de título', 'origem']);
    else table(rows, ['id', 'nome', 'corte', 'legenda', 'origem']);
  }

  function mostrar(kind, id) {
    const items = lib.all(SKILL_DIR, kind);
    if (!items[id]) {
      console.log(`${C.red}${kind} '${id}' não existe.${C.reset} Opções: ${Object.keys(items).join(', ')}`);
      process.exit(1);
    }
    const x = items[id];
    console.log(`${C.gray}// origem: ${x._origem}${x._arquivo ? ` · ${tilde(x._arquivo)}` : ''}${C.reset}`);
    console.log(JSON.stringify(lib.clean(x), null, 2));
  }

  function loadJsonArg(file) {
    if (!file) return null;
    const p = path.resolve(process.cwd(), file);
    try {
      return JSON.parse(fs.readFileSync(p, 'utf8'));
    } catch (e) {
      console.log(`${C.red}Não consegui ler ${file}: ${e.message}${C.reset}`);
      process.exit(1);
    }
  }

  function finishSave(kind, data, validate) {
    const errs = validate(data);
    if (errs.length) {
      console.log(`${C.red}✗ ${kind} inválido:${C.reset}`);
      errs.forEach((e) => console.log(`   - ${e}`));
      process.exit(1);
    }
    const file = lib.save(kind, data.id, data);
    console.log(`${C.green}✓ ${kind} '${data.id}' salvo em ${tilde(file)}${C.reset}`);
    return file;
  }

  // ───────────────────────────── perfil ─────────────────────────────

  const WEIGHTS = { Bold: 700, ExtraBold: 800, Black: 900, SemiBold: 600, Medium: 500, Regular: 400 };

  async function perfilNovo(args, opt = {}) {
    const f = parseFlags(args, ['yes']);
    const lctx = lib.context(SKILL_DIR);
    const editing = opt.edit ? lctx.profiles[opt.edit] : null;
    if (opt.edit && !editing) {
      console.log(`${C.red}perfil '${opt.edit}' não existe.${C.reset}`);
      process.exit(1);
    }
    const fromJson = loadJsonArg(f.json);
    if (fromJson) {
      // `perfil editar <id> --json f`: o <id> é a base e o id salvo, salvo se o JSON disser outra coisa
      const json = opt.edit ? { base: opt.edit, id: opt.edit, ...fromJson } : fromJson;
      const base = lib.clean(lctx.profiles[json.base || 'template_novo_perfil'] || {});
      const data = { ...deepMerge(base, json), active: json.active !== false };
      delete data.base;
      return finishSave('perfil', data, (d) => lib.validateProfile(d, lctx));
    }
    if (!ui.interactive() && !editing && !(f.id && f.nome)) {
      needTTY('`perfil novo`', 'Passe --json <arquivo> ou ao menos --id e --nome (os demais campos vêm de --base, padrão template_novo_perfil).');
    }
    const baseId = editing ? editing.id : f.base || (ui.interactive() && !f.id
      ? await ui.select({
        message: 'Partir de qual perfil?',
        choices: [{ label: 'Modelo em branco', value: 'template_novo_perfil', hint: 'campos padrão' }].concat(
          Object.values(lctx.profiles).filter((p) => p.id !== 'template_novo_perfil').map((p) => ({ label: p.name, value: p.id, hint: `${p.id} · ${p.segment || ''}` })),
        ),
      })
      : 'template_novo_perfil');
    const base = lib.clean(editing || lctx.profiles[baseId] || {});
    const p = JSON.parse(JSON.stringify(base));
    const has = (k) => f[k] !== undefined;
    const ask = async (key, cfg) => (has(key) ? f[key] : ui.input(cfg));

    if (!editing) {
      p.name = await ask('nome', { message: 'Nome do apresentador ou marca:', initial: baseId === 'template_novo_perfil' ? '' : `${base.name} (cópia)`, validate: ui.validators.required });
      const slug = p.name.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '').slice(0, 40);
      p.id = await ask('id', {
        message: 'Id do perfil (usado no --profile):', initial: slug || 'meu_perfil',
        validate: (v) => (ui.validators.slug(v) !== true ? ui.validators.slug(v) : lctx.profiles[v] && lctx.profiles[v]._origem !== 'skill' ? 'Já existe um perfil seu com esse id (use `perfil editar`).' : true),
      });
    } else {
      p.name = await ask('nome', { message: 'Nome:', initial: base.name, validate: ui.validators.required });
    }
    p.handle = await ask('handle', { message: '@ nas redes:', initial: base.handle && base.handle !== '@usuario' ? base.handle : '' });
    p.role = await ask('cargo', { message: 'Cargo ou área de atuação:', initial: base.role && !base.role.startsWith('Área de') ? base.role : '' });
    p.segment = has('segmento') ? f.segmento : await ui.select({
      message: 'Segmento:',
      choices: lib.SEGMENTS.map(([v, l]) => ({ label: l, value: v })),
      initial: Math.max(0, lib.SEGMENTS.findIndex(([v]) => v === base.segment)),
    });
    p.industry_name = p.industry_name && !p.industry_name.startsWith('Segmento /') ? p.industry_name : (lib.SEGMENTS.find(([v]) => v === p.segment) || [])[1] || p.segment;
    p.compliance_framework = has('compliance') ? f.compliance : await ui.select({
      message: 'Regras do setor:',
      choices: lib.COMPLIANCE.map(([v, l]) => ({ label: l, value: v })),
      initial: Math.max(0, lib.COMPLIANCE.findIndex(([v]) => v === (base.compliance_framework || (p.segment.startsWith('juridico') ? 'oab_provimento_205_2021' : 'general_creator_retention')))),
    });

    // tema
    if (has('tema')) p.theme_default = f.tema;
    else {
      const themes = Object.values(lctx.themes).sort((a, b) => (a.categoria === 'preset' ? 0 : 1) - (b.categoria === 'preset' ? 0 : 1));
      const t = await ui.select({
        message: 'Tema visual (cores e fontes dos cartões):',
        choices: themes.map((x) => ({ label: x.name, value: x.id, hint: `${x.id}${x.categoria === 'preset' ? ' · preset' : ''}` }))
          .concat([{ label: '➕ Criar um tema novo agora', value: '__novo__' }]),
        initial: Math.max(0, themes.findIndex((x) => x.id === base.theme_default)),
      });
      p.theme_default = t === '__novo__' ? await temaNovo([], {}) : t;
    }
    // estilo
    if (has('estilo')) p.estilo_padrao = f.estilo === 'nenhum' ? undefined : f.estilo;
    else {
      const ests = Object.values(lib.all(SKILL_DIR, 'estilo'));
      const e = await ui.select({
        message: 'Estilo de edição (ritmo de corte, legenda, câmera, SFX):',
        choices: ests.map((x) => ({ label: x.nome || x.id, value: x.id, hint: x.descricao })).concat([{ label: 'Nenhum (usar o que está no perfil)', value: '' }]),
        // editando um perfil sem estilo, o padrão é continuar sem estilo
        initial: base.estilo_padrao ? Math.max(0, ests.findIndex((x) => x.id === base.estilo_padrao)) : editing ? ests.length : 0,
      });
      p.estilo_padrao = e || undefined;
    }
    if (!p.estilo_padrao) delete p.estilo_padrao;
    // plataforma e motor
    const plats = lctx.platforms;
    p.platform_default = has('plataforma') ? f.plataforma : await ui.select({
      message: 'Plataforma padrão:',
      choices: Object.entries(plats).map(([id, v]) => ({ label: v.name || id, value: id, hint: `${v.width}×${v.height}` })),
      initial: Math.max(0, Object.keys(plats).indexOf(base.platform_default || 'instagram_reels')),
    });
    p.engine_default = has('motor') ? f.motor : await ui.select({
      message: 'Motor de edição padrão:',
      choices: [
        { label: 'Remotion', value: 'remotion', hint: 'Studio web, cortes editáveis · licença a partir de 4 pessoas' },
        { label: 'HyperFrames', value: 'hyperframes', hint: 'HTML→vídeo, Apache-2.0' },
      ],
      initial: base.engine_default === 'hyperframes' ? 1 : 0,
    });

    // legendas
    p.strict_rules = p.strict_rules || {};
    p.typography = p.typography || {};
    const t = p.typography;
    p.strict_rules.burned_subtitles = has('legendas') ? !['nao', 'não', 'false', '0'].includes(String(f.legendas).toLowerCase())
      : await ui.confirm({ message: 'Queimar legendas no vídeo?', initial: p.strict_rules.burned_subtitles !== false });
    if (p.strict_rules.burned_subtitles) {
      if (has('fonteLegenda')) t.subtitles_font = f.fonteLegenda;
      else if (ui.interactive()) {
        const fam = await ui.select({
          message: 'Fonte da legenda:',
          choices: Object.entries(lib.FONT_FAMILIES).map(([n, v]) => ({ label: n, value: n, hint: v.nota })),
          initial: Math.max(0, Object.keys(lib.FONT_FAMILIES).findIndex((n) => (t.subtitles_font || 'Inter').startsWith(n))),
        });
        const range = lib.FONT_FAMILIES[fam].weights;
        const ws = Object.entries(WEIGHTS).filter(([, w]) => w >= range[0] && w <= range[1]).sort((a, b) => b[1] - a[1]);
        const wn = ws.length > 1 ? await ui.select({ message: 'Peso:', choices: ws.map(([n, w]) => ({ label: n, value: n, hint: String(w) })), initial: ws.findIndex(([n]) => n === 'ExtraBold') >= 0 ? ws.findIndex(([n]) => n === 'ExtraBold') : 0 }) : ws[0][0];
        t.subtitles_font = `${fam} ${wn}`;
      }
      t.subtitles_color = await ask('corLegenda', { message: 'Cor da legenda:', initial: t.subtitles_color || '#FFFFFF', validate: ui.validators.hex });
      const accent = accentOf(lctx.themes[p.theme_default]);
      t.subtitles_highlight_color = await ask('corDestaque', { message: 'Cor das palavras em destaque:', initial: t.subtitles_highlight_color || accent, validate: ui.validators.hex });
      const kw = await ask('palavrasChave', { message: 'Palavras para destacar (vírgula):', initial: (t.subtitles_highlight_keywords || []).join(', ') });
      t.subtitles_highlight_keywords = String(kw).split(',').map((s) => s.trim()).filter(Boolean);
      t.subtitles_highlight_numbers = true;
    }
    p.strict_rules.final_fade_out = has('fadeFinal') ? !['nao', 'não', 'false', '0'].includes(String(f.fadeFinal).toLowerCase())
      : await ui.confirm({ message: 'Fade para preto no fim?', initial: p.strict_rules.final_fade_out !== false });
    // linha editorial e metadados
    p.editorial_guidelines = p.editorial_guidelines || {};
    p.editorial_guidelines.tone = await ask('tom', { message: 'Tom editorial:', initial: p.editorial_guidelines.tone || 'Direto, didático e de alta retenção' });
    p.editorial_guidelines.cta_default = await ask('cta', { message: 'CTA padrão:', initial: p.editorial_guidelines.cta_default || 'Salve este vídeo e compartilhe com quem precisa.' });
    p.default_metadata = p.default_metadata || {};
    p.default_metadata.artist = await ask('artista', { message: 'Metadado "artist":', initial: p.default_metadata.artist && p.default_metadata.artist !== 'Nome do Criador' ? p.default_metadata.artist : p.name });
    p.default_metadata.copyright = await ask('copyright', { message: 'Metadado "copyright":', initial: p.default_metadata.copyright && !p.default_metadata.copyright.startsWith('Nome da') ? p.default_metadata.copyright : p.name });
    p.active = true;
    delete p._origem;
    delete p._arquivo;

    const file = finishSave('perfil', p, (d) => lib.validateProfile(d, lib.context(SKILL_DIR)));
    if (ui.interactive() && (await ui.confirm({ message: 'Abrir a prévia dos cartões com este perfil?', initial: true }))) {
      runPython('neuro_preview.py', ['--tema', p.theme_default, '--perfil', p.id, ...(p.estilo_padrao ? ['--estilo', p.estilo_padrao] : []), '--abrir']);
    }
    console.log(`${C.gray}Use: neuro-mv-edit projeto init --profile ${p.id} --video bruto.mp4 --out projetos/<nome>${C.reset}`);
    return file;
  }

  // ───────────────────────────── tema ─────────────────────────────

  async function temaNovo(args, opt = {}) {
    const f = parseFlags(args, ['yes', 'semPreview']);
    const themes = lib.all(SKILL_DIR, 'tema');
    const editing = opt.edit ? themes[opt.edit] : null;
    if (opt.edit && !editing) {
      console.log(`${C.red}tema '${opt.edit}' não existe.${C.reset}`);
      process.exit(1);
    }
    const fromJson = loadJsonArg(f.json);
    if (fromJson) {
      const json = opt.edit ? { base: opt.edit, id: opt.edit, ...fromJson } : fromJson;
      const base = lib.clean(themes[json.base] || {});
      const data = { ...deepMerge(base, json), categoria: 'seu' };
      delete data.base;
      finishSave('tema', data, lib.validateTheme);
      return data.id;
    }
    if (!ui.interactive()) needTTY('`tema novo`', 'Passe --json <arquivo> (use `tema mostrar <id>` como modelo; `"base": "<id>"` herda o resto).');
    const baseId = editing ? editing.id : f.base || await ui.select({
      message: 'Partir de qual tema?',
      choices: Object.values(themes).map((x) => ({ label: x.name, value: x.id, hint: `${x.id}${x.categoria === 'preset' ? ' · preset' : ''}` })),
    });
    const t = JSON.parse(JSON.stringify(lib.clean(editing || themes[baseId])));
    if (!editing) {
      t.name = await ui.input({ message: 'Nome do tema:', initial: `${t.name} (meu)`, validate: ui.validators.required });
      const slug = t.name.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '').slice(0, 40);
      t.id = await ui.input({ message: 'Id do tema:', initial: slug, validate: (v) => (ui.validators.slug(v) !== true ? ui.validators.slug(v) : themes[v] && themes[v]._origem !== 'skill' ? 'Já existe um tema seu com esse id.' : true) });
    }
    t.description = await ui.input({ message: 'Descrição curta:', initial: t.description || '' });
    const c = t.colors = t.colors || {};
    const accentKey = Object.keys(c).find((k) => k.startsWith('highlight')) || 'highlight_accent';
    const alertKey = Object.keys(c).find((k) => k.startsWith('alert')) || 'alert_red';
    c[accentKey] = await ui.input({ message: 'Cor de destaque (palavra-chave, linhas, pílula):', initial: accentOf(t), validate: ui.validators.hex });
    c[alertKey] = await ui.input({ message: 'Cor de alerta (risco, erro):', initial: /^#[0-9A-Fa-f]{6}$/.test(c[alertKey] || '') ? c[alertKey] : '#E5484D', validate: ui.validators.hex });
    c.text_primary = await ui.input({ message: 'Cor do texto principal:', initial: /^#[0-9A-Fa-f]{6}$/.test(c.text_primary || '') ? c.text_primary : '#FFFFFF', validate: ui.validators.hex });
    t.fonts = t.fonts || {};
    const fam = async (lvl, msg) => {
      const cur = (t.fonts[lvl] || {}).family || 'Inter';
      const v = await ui.select({
        message: msg,
        choices: Object.entries(lib.FONT_FAMILIES).map(([n, x]) => ({ label: n, value: n, hint: x.nota })),
        initial: Math.max(0, Object.keys(lib.FONT_FAMILIES).indexOf(cur)),
      });
      t.fonts[lvl] = { ...(t.fonts[lvl] || {}), family: v };
      const r = lib.FONT_FAMILIES[v].weights;
      const w = Number((t.fonts[lvl] || {}).weight) || 700;
      t.fonts[lvl].weight = String(Math.min(r[1], Math.max(r[0], w)));
      if (!lib.FONT_FAMILIES[v].styles.includes(t.fonts[lvl].style || 'normal')) delete t.fonts[lvl].style;
    };
    await fam('level_1_hook', 'Fonte dos títulos (gancho):');
    await fam('level_2_support', 'Fonte de apoio (citações, CTA):');
    await fam('level_3_labels', 'Fonte dos rótulos e pílulas:');
    const pillStyle = await ui.select({
      message: 'Pílula (selo acima do título):',
      choices: [{ label: 'Preenchida com a cor de destaque', value: 'cheia' }, { label: 'Contorno na cor de destaque', value: 'contorno' }],
      initial: ((t.components || {}).pill || {}).border ? 1 : 0,
    });
    t.components = t.components || {};
    const pill = t.components.pill = { ...(t.components.pill || {}) };
    if (pillStyle === 'cheia') {
      pill.bg_color = c[accentKey];
      pill.text_color = c.pill_dark_text || '#111111';
      delete pill.border;
    } else {
      pill.bg_color = 'rgba(0, 0, 0, 0)';
      pill.text_color = c[accentKey];
      pill.border = `2px solid ${c[accentKey]}`;
    }
    pill.font_family = t.fonts.level_3_labels.family;
    t.categoria = 'seu';
    finishSave('tema', t, lib.validateTheme);
    if (!f.semPreview && (await ui.confirm({ message: 'Abrir a prévia dos cartões com este tema?', initial: true }))) {
      runPython('neuro_preview.py', ['--tema', t.id, '--abrir']);
    }
    return t.id;
  }

  // ───────────────────────────── estilo ─────────────────────────────

  async function estiloNovo(args, opt = {}) {
    const f = parseFlags(args, ['yes']);
    const ests = lib.all(SKILL_DIR, 'estilo');
    const editing = opt.edit ? ests[opt.edit] : null;
    if (opt.edit && !editing) {
      console.log(`${C.red}estilo '${opt.edit}' não existe.${C.reset}`);
      process.exit(1);
    }
    const fromJson = loadJsonArg(f.json);
    if (fromJson) {
      const json = opt.edit ? { base: opt.edit, id: opt.edit, ...fromJson } : fromJson;
      const data = deepMerge(lib.clean(ests[json.base] || {}), json);
      delete data.base;
      return finishSave('estilo', data, lib.validateEstilo);
    }
    if (!ui.interactive()) needTTY('`estilo novo`', 'Passe --json <arquivo> (use `estilo mostrar <id>` como modelo).');
    const baseId = editing ? editing.id : f.base || await ui.select({
      message: 'Partir de qual estilo?',
      choices: Object.values(ests).map((x) => ({ label: x.nome || x.id, value: x.id, hint: x.descricao })),
    });
    const e = JSON.parse(JSON.stringify(lib.clean(editing || ests[baseId])));
    if (!editing) {
      e.nome = await ui.input({ message: 'Nome do estilo:', initial: `${e.nome || baseId} (meu)`, validate: ui.validators.required });
      const slug = e.nome.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '').slice(0, 40);
      e.id = await ui.input({ message: 'Id do estilo:', initial: slug, validate: ui.validators.slug });
    }
    e.descricao = await ui.input({ message: 'Descrição curta:', initial: e.descricao || '' });
    e.corte = e.corte || {};
    e.corte.preset = await ui.select({ message: 'Ritmo de corte:', choices: [{ label: 'Natural', value: 'natural', hint: 'preserva respiros' }, { label: 'Seco (tight)', value: 'tight', hint: 'remove pausas acima do limiar' }], initial: e.corte.preset === 'tight' ? 1 : 0 });
    e.corte.limiar_ms = Number(await ui.input({ message: 'Pausa máxima mantida (ms):', initial: e.corte.limiar_ms || (e.corte.preset === 'tight' ? 140 : 240), validate: ui.validators.number(60, 800) }));
    e.legendas = e.legendas || {};
    e.legendas.animacao = await ui.select({ message: 'Legenda:', choices: [{ label: 'Pop (bloco inteiro)', value: 'pop' }, { label: 'Karaokê (palavra acende)', value: 'karaoke' }], initial: e.legendas.animacao === 'karaoke' ? 1 : 0 });
    e.legendas.palavras_por_linha = Number(await ui.input({ message: 'Palavras por linha (2–5):', initial: e.legendas.palavras_por_linha || 4, validate: ui.validators.number(2, 5) }));
    const cam = await ui.select({
      message: 'Câmera (punch-in e zoom):',
      choices: [
        { label: 'Suave', value: [1.04, 1.03] }, { label: 'Média', value: [1.07, 1.05] }, { label: 'Forte', value: [1.11, 1.07] },
        { label: 'Manter a atual', value: null, hint: e.camera ? `${e.camera.punch_in} / ${e.camera.zoom_sutil}` : '' },
      ],
      initial: 3,
    });
    if (cam) e.camera = { punch_in: cam[0], zoom_sutil: cam[1] };
    e.sfx = { ganho_db: Number(await ui.input({ message: 'Ajuste dos SFX em dB (−6 a +3):', initial: (e.sfx || {}).ganho_db ?? 0, validate: ui.validators.number(-6, 3) })) };
    e.trilha = { volume: Number(await ui.input({ message: 'Volume da trilha (0,06 a 0,25):', initial: (e.trilha || {}).volume ?? 0.12, validate: ui.validators.number(0.06, 0.25) })) };
    return finishSave('estilo', e, lib.validateEstilo);
  }

  // ───────────────────────────── roteador ─────────────────────────────

  async function remover(kind, id, f) {
    const items = lib.all(SKILL_DIR, kind);
    const x = items[id];
    if (!x) {
      console.log(`${C.red}${kind} '${id}' não existe.${C.reset}`);
      process.exit(1);
    }
    if (x._origem === 'skill') {
      console.log(`${C.red}'${id}' vem com a skill e não pode ser removido.${C.reset} Crie uma cópia com \`${kind} novo\` e use a sua.`);
      process.exit(1);
    }
    if (!f.yes && !(await ui.confirm({ message: `Remover o ${kind} '${id}' (${tilde(x._arquivo)})?`, initial: false }))) {
      if (!ui.interactive()) console.log(`${C.gray}Sem terminal: confirme com --yes.${C.reset}`);
      return;
    }
    lib.remove(kind, id);
    console.log(`${C.green}✓ ${kind} '${id}' removido.${C.reset}${x._origem.includes('sobrepõe') ? ` ${C.gray}A versão da skill volta a valer.${C.reset}` : ''}`);
  }

  function exportar(f) {
    const ids = f._.slice(1);
    const bundle = lib.exportBundle(SKILL_DIR, ids);
    const out = path.resolve(process.cwd(), f.saida || `neuro-biblioteca-${new Date().toISOString().slice(0, 10)}.json`);
    fs.writeFileSync(out, JSON.stringify(bundle, null, 2) + '\n');
    const n = (o) => Object.keys(o).length;
    console.log(`${C.green}✓ ${n(bundle.perfis)} perfis, ${n(bundle.temas)} temas e ${n(bundle.estilos)} estilos em ${tilde(out)}${C.reset}`);
  }

  function importar(f) {
    const file = f._[1];
    if (!file) {
      console.log(`${C.red}Use: perfil importar <arquivo.json> [--sobrescrever]${C.reset}`);
      process.exit(2);
    }
    const report = lib.importBundle(SKILL_DIR, loadJsonArg(file), { overwrite: Boolean(f.sobrescrever) });
    report.forEach((r) => console.log(`  ${r}`));
  }

  async function biblioteca(kind, args) {
    const f = parseFlags(args, ['yes', 'sobrescrever', 'semAbrir', 'json']);
    const sub = f._[0] || 'listar';
    const id = f._[1];
    const need = () => {
      if (!id) {
        console.log(`${C.red}Use: ${kind} ${sub} <id>${C.reset}`);
        process.exit(2);
      }
    };
    try {
      if (sub === 'listar' || sub === 'ls') return listar(kind);
      if (sub === 'mostrar' || sub === 'show') { need(); return mostrar(kind, id); }
      if (sub === 'remover' || sub === 'rm') { need(); return await remover(kind, id, f); }
      if (sub === 'novo' || sub === 'new') {
        const rest = args.slice(args.indexOf(sub) + 1);
        if (kind === 'perfil') return await perfilNovo(rest);
        if (kind === 'tema') return await temaNovo(rest);
        return await estiloNovo(rest);
      }
      if (sub === 'editar' || sub === 'edit') {
        need();
        const rest = args.slice(args.indexOf(id) + 1);
        if (kind === 'perfil') return await perfilNovo(rest, { edit: id });
        if (kind === 'tema') return await temaNovo(rest, { edit: id });
        return await estiloNovo(rest, { edit: id });
      }
      if (sub === 'exportar' && kind === 'perfil') return exportar(f);
      if (sub === 'importar' && kind === 'perfil') return importar(f);
      if ((sub === 'preview' || sub === 'previa' || sub === 'prévia') && kind === 'tema') {
        need();
        const extra = [];
        if (f.perfil) extra.push('--perfil', f.perfil);
        if (f.plataforma) extra.push('--plataforma', f.plataforma);
        if (f.estilo) extra.push('--estilo', f.estilo);
        if (!f.semAbrir) extra.push('--abrir');
        return runPython('neuro_preview.py', ['--tema', id, ...extra]);
      }
    } catch (e) {
      if (e && e.cancelled) {
        console.log(`\n${C.gray}Cancelado. Nada foi salvo.${C.reset}`);
        process.exit(130);
      }
      throw e;
    }
    console.log(`${C.red}Subcomando desconhecido: ${kind} ${sub}${C.reset}`);
    helpBiblioteca(kind);
    process.exit(2);
  }

  function helpBiblioteca(kind) {
    const extra = kind === 'perfil' ? ' | exportar [ids] [--saida f.json] | importar <f.json> [--sobrescrever]' : kind === 'tema' ? ' | preview <id> [--perfil] [--plataforma] [--estilo]' : '';
    console.log(`  ${kind} listar | mostrar <id> | novo [--json f.json] | editar <id> [--json f.json] | remover <id> [--yes]${extra}`);
  }

  return { setup, biblioteca, listarTudo, parseFlags, helpBiblioteca };
}

module.exports = { makeSetup, parseFlags };

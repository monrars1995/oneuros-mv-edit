/**
 * Biblioteca de perfis, temas e estilos de edição.
 *
 * Duas origens, mescladas por id (a do usuário vence):
 *   - presets da skill (skills/neuro-mv-edit/presets/{profiles,themes,estilos}.json) — vêm com cada versão;
 *   - biblioteca do usuário em ~/.neuro-mv-edit/{perfis,temas,estilos}/<id>.json (NEURO_HOME muda a raiz) —
 *     sobrevive a reinstalações e atualizações da skill, e pode ser exportada para outra máquina ou equipe.
 *
 * O Python (hf_project.load_presets / load_estilos) lê as mesmas duas origens, na mesma ordem.
 */
'use strict';

const fs = require('fs');
const os = require('os');
const path = require('path');

const KINDS = {
  perfil: { dir: 'perfis', file: 'profiles.json', key: 'profiles', label: 'perfil', plural: 'perfis' },
  tema: { dir: 'temas', file: 'themes.json', key: 'themes', label: 'tema', plural: 'temas' },
  estilo: { dir: 'estilos', file: 'estilos.json', key: 'estilos', label: 'estilo', plural: 'estilos' },
};

// Famílias com arquivo de fonte instalado pelo verify-env.py (mesma lista de hf_project.FONT_FILES).
const FONT_FAMILIES = {
  'Big Shoulders Display': { weights: [100, 900], styles: ['normal'], nota: 'condensada, títulos de impacto' },
  Fraunces: { weights: [100, 900], styles: ['normal', 'italic'], nota: 'serifa editorial' },
  Inter: { weights: [100, 900], styles: ['normal'], nota: 'neutra, rótulos e legendas' },
  'Cal Sans': { weights: [600, 600], styles: ['normal'], nota: 'geométrica, legendas fortes' },
  'Instrument Serif': { weights: [400, 400], styles: ['normal', 'italic'], nota: 'serifa clássica' },
  'DM Sans': { weights: [100, 1000], styles: ['normal', 'italic'], nota: 'amigável, educação' },
  'Plus Jakarta Sans': { weights: [200, 800], styles: ['normal', 'italic'], nota: 'contemporânea, corporativa' },
  'Space Grotesk': { weights: [300, 700], styles: ['normal'], nota: 'tecnológica' },
};

const SEGMENTS = [
  ['juridico_agro', 'Jurídico — Agronegócio'],
  ['juridico_tributario', 'Jurídico — Tributário'],
  ['institucional_juridico', 'Institucional jurídico'],
  ['automotivo_crm_vendas', 'Automotivo, CRM e vendas'],
  ['educacao_escolar_bilingue', 'Educação escolar e bilíngue'],
  ['negocios_vendas', 'Negócios e vendas B2B'],
  ['saude', 'Saúde'],
  ['tecnologia', 'Tecnologia'],
  ['geral_creator', 'Criador de conteúdo (geral)'],
];

const COMPLIANCE = [
  ['oab_provimento_205_2021', 'Advocacia (Provimento OAB 205/2021: sem captação, sem promessa de resultado)'],
  ['educacao_eca_lgpd', 'Educação (ECA + LGPD: imagem de menores só com autorização)'],
  ['saude_cfm_publicidade', 'Saúde (publicidade médica: sem promessa de cura, sem antes/depois)'],
  ['general_creator_retention', 'Geral (sem regra setorial)'],
];

const home = () => (process.env.NEURO_HOME && process.env.NEURO_HOME.trim()) || path.join(os.homedir(), '.neuro-mv-edit');
const userDir = (kind) => path.join(home(), KINDS[kind].dir);

function readJson(file, fallback) {
  try {
    return JSON.parse(fs.readFileSync(file, 'utf8'));
  } catch {
    return fallback;
  }
}

function skillItems(skillDir, kind) {
  const k = KINDS[kind];
  const data = readJson(path.join(skillDir, 'presets', k.file), {});
  return data[k.key] || {};
}

function userItems(kind) {
  const dir = userDir(kind);
  const out = {};
  if (!fs.existsSync(dir)) return out;
  for (const f of fs.readdirSync(dir).filter((x) => x.endsWith('.json')).sort()) {
    const data = readJson(path.join(dir, f), null);
    if (!data || typeof data !== 'object') continue;
    const id = data.id || path.basename(f, '.json');
    out[id] = { ...data, id };
  }
  return out;
}

/** Todos os itens de um tipo: {id: {...dados, _origem: 'skill'|'usuario', _arquivo?}} */
function all(skillDir, kind) {
  const out = {};
  for (const [id, v] of Object.entries(skillItems(skillDir, kind))) out[id] = { ...v, id, _origem: 'skill' };
  for (const [id, v] of Object.entries(userItems(kind))) {
    out[id] = { ...v, id, _origem: out[id] ? 'usuario (sobrepõe a skill)' : 'usuario', _arquivo: path.join(userDir(kind), `${id}.json`) };
  }
  return out;
}

function platforms(skillDir) {
  return readJson(path.join(skillDir, 'presets', 'platforms.json'), {}).platforms || {};
}

function clean(obj) {
  const o = JSON.parse(JSON.stringify(obj));
  for (const k of Object.keys(o)) if (k.startsWith('_')) delete o[k];
  return o;
}

function save(kind, id, data) {
  const dir = userDir(kind);
  fs.mkdirSync(dir, { recursive: true });
  const file = path.join(dir, `${id}.json`);
  const tmp = `${file}.tmp`;
  fs.writeFileSync(tmp, JSON.stringify({ ...clean(data), id }, null, 2) + '\n');
  fs.renameSync(tmp, file);
  return file;
}

function remove(kind, id) {
  const file = path.join(userDir(kind), `${id}.json`);
  if (!fs.existsSync(file)) return null;
  fs.unlinkSync(file);
  return file;
}

// ───────────────────────────── validação ─────────────────────────────

const HEX = /^#[0-9A-Fa-f]{6}$/;

function validateProfile(p, ctx) {
  const errs = [];
  if (!p.id || !/^[a-z0-9][a-z0-9_]{1,40}$/.test(p.id)) errs.push('id: use letras minúsculas, números e _');
  if (!p.name) errs.push('name: obrigatório');
  if (!ctx.themes[p.theme_default]) errs.push(`theme_default: tema '${p.theme_default}' não existe`);
  if (!ctx.platforms[p.platform_default]) errs.push(`platform_default: plataforma '${p.platform_default}' não existe`);
  if (p.estilo_padrao && !ctx.estilos[p.estilo_padrao]) errs.push(`estilo_padrao: estilo '${p.estilo_padrao}' não existe`);
  if (p.engine_default && !['remotion', 'hyperframes'].includes(p.engine_default)) errs.push('engine_default: remotion ou hyperframes');
  const t = p.typography || {};
  for (const k of ['subtitles_color', 'subtitles_highlight_color']) if (t[k] && !HEX.test(t[k])) errs.push(`typography.${k}: cor #RRGGBB`);
  if (t.subtitles_font) {
    const fam = Object.keys(FONT_FAMILIES).find((f) => t.subtitles_font.startsWith(f));
    if (!fam) errs.push(`typography.subtitles_font: '${t.subtitles_font}' não é uma fonte instalada (${Object.keys(FONT_FAMILIES).join(', ')})`);
  }
  return errs;
}

function validateTheme(t) {
  const errs = [];
  if (!t.id || !/^[a-z0-9][a-z0-9_]{1,40}$/.test(t.id)) errs.push('id: use letras minúsculas, números e _');
  if (!t.name) errs.push('name: obrigatório');
  const c = t.colors || {};
  if (!c.text_primary) errs.push('colors.text_primary: obrigatório');
  if (!Object.keys(c).some((k) => k.startsWith('highlight') || k.startsWith('accent') || k.startsWith('blue'))) errs.push('colors: falta a cor de destaque (highlight_*)');
  for (const [lvl, f] of Object.entries(t.fonts || {})) {
    if (f.family && !FONT_FAMILIES[f.family]) errs.push(`fonts.${lvl}: '${f.family}' não é uma fonte instalada`);
  }
  for (const lvl of ['level_1_hook', 'level_2_support', 'level_3_labels']) if (!(t.fonts || {})[lvl]) errs.push(`fonts.${lvl}: obrigatório`);
  return errs;
}

function validateEstilo(e) {
  const errs = [];
  if (!e.id || !/^[a-z0-9][a-z0-9_]{1,40}$/.test(e.id)) errs.push('id: use letras minúsculas, números e _');
  if (e.corte && e.corte.preset && !['natural', 'tight'].includes(e.corte.preset)) errs.push('corte.preset: natural ou tight');
  if (e.legendas && e.legendas.animacao && !['pop', 'karaoke'].includes(e.legendas.animacao)) errs.push('legendas.animacao: pop ou karaoke');
  return errs;
}

function context(skillDir) {
  return { themes: all(skillDir, 'tema'), platforms: platforms(skillDir), estilos: all(skillDir, 'estilo'), profiles: all(skillDir, 'perfil') };
}

/** Exporta perfis/temas/estilos do usuário (e os que eles usam) num único JSON compartilhável. */
function exportBundle(skillDir, ids) {
  const ctx = context(skillDir);
  const bundle = { formato: 'neuro-mv-edit/biblioteca', versao: 1, exportado_em: new Date().toISOString(), perfis: {}, temas: {}, estilos: {} };
  const wantProfiles = ids && ids.length ? ids : Object.keys(userItems('perfil'));
  for (const id of wantProfiles) {
    const p = ctx.profiles[id];
    if (!p) throw new Error(`perfil '${id}' não existe`);
    bundle.perfis[id] = clean(p);
    const th = ctx.themes[p.theme_default];
    if (th && th._origem !== 'skill') bundle.temas[th.id] = clean(th);
    const es = p.estilo_padrao && ctx.estilos[p.estilo_padrao];
    if (es && es._origem !== 'skill') bundle.estilos[es.id] = clean(es);
  }
  if (!ids || !ids.length) {
    for (const [id, t] of Object.entries(userItems('tema'))) bundle.temas[id] = clean(t);
    for (const [id, e] of Object.entries(userItems('estilo'))) bundle.estilos[id] = clean(e);
  }
  return bundle;
}

function importBundle(skillDir, bundle, { overwrite = false } = {}) {
  if (!bundle || bundle.formato !== 'neuro-mv-edit/biblioteca') throw new Error('arquivo não é uma exportação da biblioteca neuro-mv-edit');
  const report = [];
  const existing = { tema: userItems('tema'), estilo: userItems('estilo'), perfil: userItems('perfil') };
  const put = (kind, id, data) => {
    if (existing[kind][id] && !overwrite) {
      report.push(`⏭️  ${kind} ${id}: já existe (use --sobrescrever)`);
      return;
    }
    save(kind, id, data);
    report.push(`✅ ${kind} ${id}`);
  };
  for (const [id, t] of Object.entries(bundle.temas || {})) put('tema', id, t);
  for (const [id, e] of Object.entries(bundle.estilos || {})) put('estilo', id, e);
  const ctx = context(skillDir);
  for (const [id, p] of Object.entries(bundle.perfis || {})) {
    const errs = validateProfile({ ...p, id }, ctx);
    if (errs.length) {
      report.push(`❌ perfil ${id}: ${errs.join('; ')}`);
      continue;
    }
    put('perfil', id, p);
  }
  return report;
}

module.exports = {
  KINDS, FONT_FAMILIES, SEGMENTS, COMPLIANCE, home, userDir, all, platforms, save, remove, clean,
  validateProfile, validateTheme, validateEstilo, context, exportBundle, importBundle, readJson,
};

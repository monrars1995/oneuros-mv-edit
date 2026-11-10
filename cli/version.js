#!/usr/bin/env node
/**
 * Versão única do neuro-mv-edit em todos os manifestos.
 *
 *   node cli/version.js check          → confere se todos os arquivos têm a mesma versão (sai 1 se não)
 *   node cli/version.js set 1.4.2      → grava a versão em todos os arquivos
 *   node cli/version.js current        → imprime a versão do package.json
 *
 * A versão segue SemVer: MAJOR quebra compatibilidade (layout, comandos, formato de perfis),
 * MINOR traz recurso novo compatível, PATCH só corrige. Ver CHANGELOG.md e a seção
 * "Versionamento e releases" do README.
 */

const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const SEMVER = /^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$/;

// [arquivo, regex com um grupo de captura para a versão]
const TARGETS = [
  ['package.json', /^(\s*"version":\s*")([^"]+)(")/m],
  ['plugin.json', /^(\s*"version":\s*")([^"]+)(")/m],
  ['.claude-plugin/plugin.json', /^(\s*"version":\s*")([^"]+)(")/m],
  ['plugins/opencode/package.json', /^(\s*"version":\s*")([^"]+)(")/m],
  ['skills/neuro-mv-edit/open-design.json', /^(\s*"version":\s*")([^"]+)(")/m],
  ['skills/neuro-mv-edit/data/memory.json', /("system":\s*\{[\s\S]*?"version":\s*")([^"]+)(")/],
  ['skills/neuro-mv-edit/SKILL.md', /^(# Neuro MV Edit .*\(v)([^)]+)(\))/m],
  ['skills/neuro-mv-edit/scripts/hf_project.py', /^(SKILL_VERSION = ")([^"]+)(")/m],
  ['cli/cli.js', /^(const VERSION = ')([^']+)(')/m],
  ['README.md', /^(# 🎬 Neuro MV Edit .*\(v)([^)]+)(\))/m],
  ['README.md', /(badge\/vers%C3%A3o-v)([0-9A-Za-z.-]+?)(-blue)/],
  ['docs/COMANDOS.md', /^(# Referência de comandos do neuro-mv-edit \(v)([^)]+)(\))/m],
];

// Todas as ocorrências da tag estável nos comandos de instalação (npx github:…#vX.Y.Z).
// Placeholders como #vX.Y.Z não casam (só dígitos).
const ALL_OCCURRENCES = [
  ['README.md', /(mv-edit#v)(\d+\.\d+\.\d+)/g],
  ['skills/neuro-mv-edit/SKILL.md', /(mv-edit#v)(\d+\.\d+\.\d+)/g],
  ['docs/COMANDOS.md', /(mv-edit#v)(\d+\.\d+\.\d+)/g],
];

function read(rel) {
  return fs.readFileSync(path.join(ROOT, rel), 'utf8');
}

function scan() {
  return TARGETS.map(([rel, re]) => {
    let txt;
    try { txt = read(rel); } catch { return { rel, version: null, error: 'arquivo ausente' }; }
    const m = txt.match(re);
    return { rel, version: m ? m[2] : null, error: m ? null : 'marcador de versão não encontrado' };
  });
}

function current() {
  return JSON.parse(read('package.json')).version;
}

function check() {
  const want = current();
  const rows = scan();
  let ok = true;
  for (const r of rows) {
    const good = r.version === want;
    if (!good) ok = false;
    console.log(`${good ? '✓' : '✗'} ${r.rel.padEnd(46)} ${r.version || r.error}`);
  }
  for (const [rel, re] of ALL_OCCURRENCES) {
    let txt;
    try { txt = read(rel); } catch { continue; }
    const found = [...txt.matchAll(re)].map((m) => m[2]);
    const bad = found.filter((x) => x !== want);
    if (bad.length) ok = false;
    if (found.length) console.log(`${bad.length ? '✗' : '✓'} ${(rel + ' (tags #v)').padEnd(46)} ${found.length} ocorrência(s)${bad.length ? `, divergentes: ${[...new Set(bad)].join(', ')}` : ''}`);
  }
  console.log(ok ? `\nTudo em v${want}.` : `\nVersões divergentes: rode  node cli/version.js set ${want}`);
  return ok;
}

function set(version) {
  if (!SEMVER.test(version)) {
    console.error(`Versão inválida: "${version}" (use SemVer, ex.: 1.4.2)`);
    process.exit(2);
  }
  const byFile = new Map();
  for (const [rel, re] of TARGETS) {
    const txt = byFile.has(rel) ? byFile.get(rel) : read(rel);
    if (!re.test(txt)) {
      console.error(`✗ ${rel}: marcador de versão não encontrado`);
      process.exit(1);
    }
    byFile.set(rel, txt.replace(re, (_, a, _old, c) => `${a}${version}${c}`));
  }
  for (const [rel, re] of ALL_OCCURRENCES) {
    let txt;
    try { txt = byFile.has(rel) ? byFile.get(rel) : read(rel); } catch { continue; }
    byFile.set(rel, txt.replace(re, (_, a) => `${a}${version}`));
  }
  for (const [rel, txt] of byFile) fs.writeFileSync(path.join(ROOT, rel), txt);
  console.log(`Versão gravada: v${version} em ${byFile.size} arquivos.`);
  return check();
}

const [cmd, arg] = process.argv.slice(2);
if (cmd === 'check') process.exit(check() ? 0 : 1);
else if (cmd === 'set' && arg) process.exit(set(arg.replace(/^v/, '')) ? 0 : 1);
else if (cmd === 'current') console.log(current());
else {
  console.log('Uso: node cli/version.js check | set <x.y.z> | current');
  process.exit(cmd ? 2 : 0);
}

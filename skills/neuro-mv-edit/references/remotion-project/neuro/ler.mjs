// Lê as camadas geradas depois que o Studio as editou. Uso:
//   node neuro/ler.mjs cortes src/gerado/Cortes.tsx   → JSON com os clipes (nome, duração, trimBefore)
//   node neuro/ler.mjs cenas  src/gerado/Cenas.tsx    → JSON com as sequências (nome, from, duração)
//   node neuro/ler.mjs canon  <arquivo.tsx>           → hash da árvore sintática (ignora formatação)
import {createHash} from 'node:crypto';
import {readFileSync} from 'node:fs';
import {parse} from '@babel/parser';

const [cmd, file] = process.argv.slice(2);
const code = readFileSync(file, 'utf8');
const ast = parse(code, {sourceType: 'module', plugins: ['typescript', 'jsx']});

const walk = (node, fn) => {
  if (!node || typeof node !== 'object') return;
  if (Array.isArray(node)) {
    node.forEach((n) => walk(n, fn));
    return;
  }
  if (typeof node.type === 'string') fn(node);
  for (const k of Object.keys(node)) {
    if (k === 'loc' || k === 'start' || k === 'end') continue;
    walk(node[k], fn);
  }
};

const nameOf = (n) => {
  if (!n) return '';
  if (n.type === 'JSXIdentifier') return n.name;
  if (n.type === 'JSXMemberExpression') return `${nameOf(n.object)}.${nameOf(n.property)}`;
  return '';
};

const valueOf = (expr) => {
  if (!expr) return true;
  if (expr.type === 'StringLiteral') return expr.value;
  if (expr.type === 'JSXExpressionContainer') return valueOf(expr.expression);
  if (expr.type === 'NumericLiteral') return expr.value;
  if (expr.type === 'UnaryExpression' && expr.operator === '-' && expr.argument.type === 'NumericLiteral') return -expr.argument.value;
  if (expr.type === 'TemplateLiteral' && expr.expressions.length === 0) return expr.quasis[0].value.cooked;
  if (expr.type === 'CallExpression' && expr.callee.name === 'staticFile' && expr.arguments[0]?.type === 'StringLiteral') {
    return expr.arguments[0].value;
  }
  return null;
};

const attrs = (el) => {
  const out = {};
  for (const a of el.openingElement.attributes) {
    if (a.type === 'JSXAttribute') out[a.name.name] = valueOf(a.value);
  }
  return out;
};

if (cmd === 'cortes') {
  const clips = [];
  walk(ast, (n) => {
    if (n.type === 'JSXElement' && nameOf(n.openingElement.name) === 'TransitionSeries.Sequence') {
      const a = attrs(n);
      let video = null;
      walk(n.children, (c) => {
        if (!video && c.type === 'JSXElement' && nameOf(c.openingElement.name) === 'Video') video = attrs(c);
      });
      clips.push({name: a.name ?? null, durationInFrames: a.durationInFrames ?? null, trimBefore: video?.trimBefore ?? 0, src: video?.src ?? null});
    }
  });
  process.stdout.write(JSON.stringify({clipes: clips}));
} else if (cmd === 'cenas') {
  const seqs = [];
  walk(ast, (n) => {
    if (n.type === 'JSXElement' && nameOf(n.openingElement.name) === 'Sequence') {
      const a = attrs(n);
      seqs.push({name: a.name ?? null, from: a.from ?? 0, durationInFrames: a.durationInFrames ?? null});
    }
  });
  process.stdout.write(JSON.stringify({cenas: seqs}));
} else if (cmd === 'canon') {
  const strip = (node) => {
    if (Array.isArray(node)) {
      return node.map(strip).filter((x) => !(x && x.type === 'JSXText' && x.value.trim() === ''));
    }
    if (!node || typeof node !== 'object') return node;
    const o = {};
    for (const k of Object.keys(node).sort()) {
      if (['loc', 'start', 'end', 'extra', 'comments', 'leadingComments', 'trailingComments', 'innerComments', 'range', 'tokens'].includes(k)) continue;
      o[k] = strip(node[k]);
    }
    if (o.type === 'JSXText') o.value = o.value.replace(/\s+/g, ' ').trim();
    return o;
  };
  process.stdout.write(createHash('sha256').update(JSON.stringify(strip(ast.program))).digest('hex').slice(0, 16));
} else {
  process.stderr.write(`comando desconhecido: ${cmd}\n`);
  process.exit(2);
}

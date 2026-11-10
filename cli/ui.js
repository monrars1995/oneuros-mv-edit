/**
 * Perguntas interativas no terminal, sem dependências (o pacote roda via `npx github:` sem instalar nada).
 *
 *   select      ↑/↓ e Enter
 *   multiselect ↑/↓, Espaço marca, A marca/desmarca tudo, Enter confirma
 *   confirm     s/n (Enter aceita o padrão)
 *   input       texto livre com valor padrão e validação
 *
 * Sem TTY (agente, CI, pipe) as funções não perguntam: devolvem o padrão. Quem chama decide se isso é aceitável
 * (o `setup` pede `--yes` nesse caso).
 */
'use strict';

const readline = require('readline');

const C = {
  reset: '\x1b[0m', bold: '\x1b[1m', dim: '\x1b[2m', cyan: '\x1b[36m', green: '\x1b[32m',
  yellow: '\x1b[33m', red: '\x1b[31m', gray: '\x1b[90m', gold: '\x1b[38;5;178m',
};

const interactive = () => Boolean(process.stdin.isTTY && process.stdout.isTTY && !process.env.CI && !process.env.NEURO_NO_TTY);

class Cancelled extends Error {
  constructor() {
    super('cancelado');
    this.cancelled = true;
  }
}

function withKeys(render, onKey) {
  return new Promise((resolve, reject) => {
    const stdin = process.stdin;
    readline.emitKeypressEvents(stdin);
    const wasRaw = stdin.isRaw;
    stdin.setRawMode(true);
    stdin.resume();
    let lines = 0;
    const draw = (final = false) => {
      if (lines) process.stdout.write(`\x1b[${lines}A\x1b[0J`);
      const text = render(final);
      process.stdout.write(text + '\n');
      lines = text.split('\n').length;
    };
    const done = (err, value) => {
      stdin.removeListener('keypress', handler);
      stdin.setRawMode(wasRaw);
      stdin.pause();
      if (err) reject(err);
      else resolve(value);
    };
    const handler = (str, key = {}) => {
      if (key.ctrl && key.name === 'c') {
        draw(true);
        done(new Cancelled());
        return;
      }
      const res = onKey(str, key);
      if (res && res.submit) {
        draw(true);
        done(null, res.value);
        return;
      }
      draw();
    };
    stdin.on('keypress', handler);
    draw();
  });
}

function hint(text) {
  return text ? ` ${C.gray}${text}${C.reset}` : '';
}

async function select({ message, choices, initial = 0 }) {
  const enabled = choices.map((c, i) => (c.disabled ? -1 : i)).filter((i) => i >= 0);
  if (!enabled.length) throw new Error(`Sem opções para: ${message}`);
  let idx = enabled.includes(initial) ? initial : enabled[0];
  if (!interactive()) return choices[idx].value;
  return withKeys(
    (final) => {
      if (final) return `${C.green}✔${C.reset} ${C.bold}${message}${C.reset} ${C.cyan}${choices[idx].label}${C.reset}`;
      const rows = choices.map((c, i) => {
        const cur = i === idx;
        const mark = c.disabled ? `${C.gray}·` : cur ? `${C.cyan}❯` : ' ';
        const label = c.disabled ? `${C.gray}${c.label}` : cur ? `${C.cyan}${c.label}` : c.label;
        return `  ${mark} ${label}${C.reset}${hint(c.hint)}`;
      });
      return `${C.yellow}?${C.reset} ${C.bold}${message}${C.reset} ${C.gray}(↑/↓, Enter)${C.reset}\n${rows.join('\n')}`;
    },
    (_s, key) => {
      const pos = enabled.indexOf(idx);
      if (key.name === 'up' || key.name === 'k') idx = enabled[(pos - 1 + enabled.length) % enabled.length];
      else if (key.name === 'down' || key.name === 'j') idx = enabled[(pos + 1) % enabled.length];
      else if (key.name === 'return') return { submit: true, value: choices[idx].value };
      return null;
    },
  );
}

async function multiselect({ message, choices, min = 0 }) {
  const checked = choices.map((c) => Boolean(c.checked) && !c.disabled);
  if (!interactive()) return choices.filter((_, i) => checked[i]).map((c) => c.value);
  let idx = Math.max(0, choices.findIndex((c) => !c.disabled));
  let error = '';
  return withKeys(
    (final) => {
      const picked = choices.filter((_, i) => checked[i]).map((c) => c.label);
      if (final) return `${C.green}✔${C.reset} ${C.bold}${message}${C.reset} ${C.cyan}${picked.join(', ') || 'nenhum'}${C.reset}`;
      const rows = choices.map((c, i) => {
        const cur = i === idx;
        const box = c.disabled ? `${C.gray}◌` : checked[i] ? `${C.green}◉` : '◯';
        const label = c.disabled ? `${C.gray}${c.label}` : cur ? `${C.cyan}${c.label}` : c.label;
        return `  ${cur ? `${C.cyan}❯${C.reset}` : ' '} ${box}${C.reset} ${label}${C.reset}${hint(c.hint)}`;
      });
      const err = error ? `\n  ${C.red}${error}${C.reset}` : '';
      return `${C.yellow}?${C.reset} ${C.bold}${message}${C.reset} ${C.gray}(↑/↓, Espaço marca, A todos, Enter confirma)${C.reset}\n${rows.join('\n')}${err}`;
    },
    (str, key) => {
      error = '';
      if (key.name === 'up' || key.name === 'k') idx = (idx - 1 + choices.length) % choices.length;
      else if (key.name === 'down' || key.name === 'j') idx = (idx + 1) % choices.length;
      else if (key.name === 'space') {
        if (!choices[idx].disabled) checked[idx] = !checked[idx];
      } else if (str === 'a' || str === 'A') {
        const all = choices.every((c, i) => c.disabled || checked[i]);
        choices.forEach((c, i) => { if (!c.disabled) checked[i] = !all; });
      } else if (key.name === 'return') {
        const values = choices.filter((_, i) => checked[i]).map((c) => c.value);
        if (values.length < min) {
          error = `Escolha pelo menos ${min}.`;
          return null;
        }
        return { submit: true, value: values };
      }
      return null;
    },
  );
}

function ask(question) {
  return new Promise((resolve, reject) => {
    const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
    let answered = false;
    rl.on('SIGINT', () => {
      rl.close();
      reject(new Cancelled());
    });
    rl.on('close', () => { if (!answered) reject(new Cancelled()); });
    rl.question(question, (a) => {
      answered = true;
      rl.close();
      resolve(a);
    });
  });
}

async function input({ message, initial = '', validate, placeholder }) {
  if (!interactive()) {
    const v = String(initial ?? '');
    if (validate) {
      const err = validate(v);
      if (err && err !== true) throw new Error(`${message}: ${err} (sem terminal interativo, passe o valor por opção)`);
    }
    return v;
  }
  for (;;) {
    const def = initial !== '' && initial !== undefined ? ` ${C.gray}(${initial})${C.reset}` : placeholder ? ` ${C.gray}${placeholder}${C.reset}` : '';
    const raw = await ask(`${C.yellow}?${C.reset} ${C.bold}${message}${C.reset}${def} `);
    const v = raw.trim() === '' ? String(initial ?? '') : raw.trim();
    const err = validate ? validate(v) : null;
    if (err && err !== true) {
      console.log(`  ${C.red}${err}${C.reset}`);
      continue;
    }
    return v;
  }
}

async function confirm({ message, initial = true }) {
  if (!interactive()) return initial;
  for (;;) {
    const raw = (await ask(`${C.yellow}?${C.reset} ${C.bold}${message}${C.reset} ${C.gray}(${initial ? 'S/n' : 's/N'})${C.reset} `)).trim().toLowerCase();
    if (!raw) return initial;
    if (['s', 'sim', 'y', 'yes'].includes(raw)) return true;
    if (['n', 'nao', 'não', 'no'].includes(raw)) return false;
  }
}

const validators = {
  slug: (v) => (/^[a-z0-9][a-z0-9_]{1,40}$/.test(v) ? true : 'Use letras minúsculas, números e _ (2 a 41 caracteres), começando por letra ou número.'),
  hex: (v) => (/^#[0-9A-Fa-f]{6}$/.test(v) ? true : 'Cor no formato #RRGGBB.'),
  required: (v) => (v.trim() ? true : 'Obrigatório.'),
  number: (min, max) => (v) => {
    const n = Number(String(v).replace(',', '.'));
    return Number.isFinite(n) && n >= min && n <= max ? true : `Número entre ${min} e ${max}.`;
  },
};

module.exports = { C, interactive, select, multiselect, input, confirm, validators, Cancelled };

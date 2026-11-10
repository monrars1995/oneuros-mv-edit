// Plugin do DeepSeek Harness (e do Neuro Harness, que é uma distribuição dele) da skill neuro-mv-edit.
//
// Instalado no perfil com `dsh plugin --profile <perfil> add <spec>`: o `package.json` da raiz declara o
// manifesto `dsh` (bundle → plugins/dsh/cordis.patch.yml), e o patch insere este módulo na árvore do perfil.
//
//  - skill: registra um provedor no `ctx.skills` com skills/neuro-mv-edit/SKILL.md, no mesmo formato do
//    @deepseek-ai/dsh-skill-filesystem (frontmatter YAML → nome, descrição e invocação; corpo sem o
//    frontmatter; `resourceBase` na pasta da skill, para os caminhos relativos resolverem);
//  - PATH: põe o bin/ deste pacote na frente do PATH do processo enquanto o plugin está ativo, para o
//    comando `neuro-mv-edit` funcionar em toda sessão (como no plugin do Claude Code). Os processos que o
//    Harness abre (bash, terminal) herdam o process.env do momento em que são criados.
//
// Sem dependências: nada de `yaml` nem de @deepseek-ai/dsh-skill (o pacote instalado por link não enxerga
// o node_modules do Harness), por isso a constante de precedência está copiada abaixo.
import { accessSync, constants, existsSync } from "node:fs"
import { readFile, realpath } from "node:fs/promises"
import { delimiter, dirname, join, resolve } from "node:path"
import { fileURLToPath } from "node:url"

/** Nome do plugin no Cordis. */
export const name = "neuro-mv-edit"
/** Serviço usado: o registro de skills do Harness. */
export const inject = ["skills"]

const SKILL_NAME = "neuro-mv-edit"
const PROVIDER_NAME = "neuro-mv-edit"
// = BUNDLED_SKILL_RANK de @deepseek-ai/dsh-skill: a precedência padrão de provedores empacotados.
// Menor vence: skills do projeto (100/200), pastas extras (300) e do usuário (400/500) sobrepõem esta.
const BUNDLED_SKILL_RANK = 600

const here = dirname(fileURLToPath(import.meta.url))
const PKG_ROOT = resolve(here, "..", "..")
const SKILL_DIR = join(PKG_ROOT, "skills", SKILL_NAME)
const SKILL_FILE = join(SKILL_DIR, "SKILL.md")
const BIN_DIR = join(PKG_ROOT, "bin")
const SKILL_NAME_RE = /^[a-z0-9]+(?:-[a-z0-9]+)*$/

// ───────────────────────── SKILL.md ─────────────────────────

/** Separa o frontmatter com as mesmas regras do dsh-skill-filesystem: linhas `---` exatas, abrindo e fechando. */
function splitFrontmatter(raw) {
  const text = raw.replace(/^﻿/, "")
  const firstEnd = text.indexOf("\n")
  if (firstEnd < 0 || text.slice(0, firstEnd).replace(/\r$/, "") !== "---") return undefined
  let lineStart = firstEnd + 1
  while (lineStart <= text.length) {
    const next = text.indexOf("\n", lineStart)
    const lineEnd = next < 0 ? text.length : next
    if (text.slice(lineStart, lineEnd).replace(/\r$/, "") === "---") {
      return { header: text.slice(firstEnd + 1, lineStart), body: next < 0 ? "" : text.slice(next + 1) }
    }
    if (next < 0) return undefined
    lineStart = next + 1
  }
  return undefined
}

function scalar(value) {
  if (value.startsWith('"')) {
    try {
      return JSON.parse(value)
    } catch {
      return value.replace(/^"|"$/g, "")
    }
  }
  if (value.startsWith("'")) return value.replace(/^'|'$/g, "").replace(/''/g, "'")
  return value.replace(/\s+#.*$/, "")
}

/** Subconjunto de YAML que um frontmatter de skill usa: chaves de topo com escalar simples, entre aspas ou em bloco (| e >). */
function parseHeader(header) {
  const data = {}
  const lines = header.split(/\r?\n/)
  for (let i = 0; i < lines.length; i++) {
    const match = /^([A-Za-z_][\w-]*):(?:[ \t]+(.*?))?[ \t]*$/.exec(lines[i])
    if (!match) continue
    const key = match[1]
    const value = match[2] ?? ""
    if (value === "") continue // mapa aninhado (ex.: metadata) ou vazio: não é usado aqui
    if (/^[|>][+-]?$/.test(value)) {
      const block = []
      while (i + 1 < lines.length && (/^[ \t]+\S/.test(lines[i + 1]) || lines[i + 1].trim() === "")) block.push(lines[++i])
      const filled = block.filter((l) => l.trim() !== "")
      const indent = filled.length ? Math.min(...filled.map((l) => l.match(/^[ \t]*/)[0].length)) : 0
      const text = block.map((l) => l.slice(indent)).join("\n")
      data[key] = (value[0] === "|" ? text : text.replace(/([^\n])\n(?=[^\n])/g, "$1 ")).trim()
      continue
    }
    data[key] = scalar(value)
  }
  return data
}

function flag(value) {
  if (typeof value === "boolean") return value
  if (value === undefined) return undefined
  const v = String(value).toLowerCase()
  if (["true", "yes", "on", "1"].includes(v)) return true
  if (["false", "no", "off", "0"].includes(v)) return false
  return undefined
}

/** Lê e interpreta o SKILL.md. Devolve undefined (com aviso no log) se a skill não puder ser carregada. */
async function loadSkill(logger, signal) {
  let raw
  let path
  try {
    path = await realpath(SKILL_FILE)
    raw = await readFile(path, { encoding: "utf8", signal })
  } catch (error) {
    signal?.throwIfAborted()
    logger?.warn?.(`neuro-mv-edit: ${SKILL_FILE} não pôde ser lido: ${String(error)}`)
    return undefined
  }
  const parts = splitFrontmatter(raw)
  if (!parts) {
    logger?.warn?.(`neuro-mv-edit: ${path} ignorado: sem frontmatter YAML`)
    return undefined
  }
  const data = parseHeader(parts.header)
  const skillName = typeof data.name === "string" ? data.name : ""
  const description = typeof data.description === "string" ? data.description : ""
  if (!SKILL_NAME_RE.test(skillName) || description === "") {
    logger?.warn?.(`neuro-mv-edit: ${path} ignorado: o frontmatter precisa de name (kebab-case) e description`)
    return undefined
  }
  return {
    name: skillName,
    description,
    ...(typeof data.whenToUse === "string" && data.whenToUse !== "" ? { whenToUse: data.whenToUse } : {}),
    invocation: {
      modelInvocable: flag(data["disable-model-invocation"]) !== true,
      userInvocable: flag(data["user-invocable"]) !== false,
    },
    path,
    content: parts.body.trim(),
  }
}

// ───────────────────────── provedor de skills ─────────────────────────

const RESOURCE_BASE = { kind: "directory", path: SKILL_DIR }

function summary(skill) {
  return {
    name: skill.name,
    description: skill.description,
    ...(skill.whenToUse !== undefined ? { whenToUse: skill.whenToUse } : {}),
    invocation: skill.invocation,
    provider: PROVIDER_NAME,
    source: "bundled",
    resourceBase: RESOURCE_BASE,
    path: skill.path,
  }
}

function createProvider(logger) {
  return {
    name: PROVIDER_NAME,
    async list(options = {}) {
      const skill = await loadSkill(logger, options.signal)
      if (!skill) return []
      return [{ ...summary(skill), rank: BUNDLED_SKILL_RANK, locator: { path: skill.path, directory: SKILL_DIR } }]
    },
    async get(_candidate, options = {}) {
      const skill = await loadSkill(logger, options.signal)
      if (!skill) return undefined
      return { ...summary(skill), content: skill.content }
    },
  }
}

// ───────────────────────── PATH ─────────────────────────

/** Põe `dir` na frente do PATH; o retorno tira de novo só a entrada que foi posta. */
function prependToPath(dir) {
  const had = Object.prototype.hasOwnProperty.call(process.env, "PATH")
  const parts = (process.env.PATH ?? "").split(delimiter).filter((p) => p !== "")
  if (parts[0] === dir) return undefined // já está na frente (outra instância ou o lançador)
  process.env.PATH = [dir, ...parts].join(delimiter)
  return () => {
    const now = (process.env.PATH ?? "").split(delimiter)
    const at = now.indexOf(dir)
    if (at >= 0) now.splice(at, 1)
    const restored = now.filter((p) => p !== "").join(delimiter)
    if (restored === "" && !had) delete process.env.PATH
    else process.env.PATH = restored
  }
}

function shimReady(logger) {
  const shim = join(BIN_DIR, process.platform === "win32" ? "neuro-mv-edit.cmd" : "neuro-mv-edit")
  if (!existsSync(shim)) {
    logger?.warn?.(`neuro-mv-edit: ${shim} não existe; o comando não entra no PATH`)
    return false
  }
  if (process.platform !== "win32") {
    try {
      accessSync(shim, constants.X_OK)
    } catch {
      logger?.warn?.(`neuro-mv-edit: ${shim} sem permissão de execução (chmod +x); o comando pode falhar`)
    }
  }
  return true
}

/**
 * Registra a skill e, enquanto o plugin estiver ativo, o comando `neuro-mv-edit` no PATH.
 * @param ctx - contexto Cordis com o serviço `skills`.
 */
export function apply(ctx) {
  const logger = ctx.logger
  ctx.skills.registerProvider(() => createProvider(logger))
  if (shimReady(logger)) ctx.effect(() => prependToPath(BIN_DIR), "neuro-mv-edit PATH")
}

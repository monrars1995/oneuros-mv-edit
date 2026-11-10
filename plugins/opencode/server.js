// Plugin OpenCode V2 da skill neuro-mv-edit.
//
// Registra a skill no domínio `skill` do OpenCode (ctx.skill.transform), no mesmo formato
// que o parser interno usa para SKILL.md: id = nome da pasta, conteúdo sem o frontmatter.
// Procura a skill em ./skill (cópia feita pelo instalador) ou, rodando direto do repositório,
// em ../../skills/neuro-mv-edit. O OpenCode fornece @opencode/plugin em tempo de execução.
import { Plugin } from "@opencode/plugin"
import { existsSync, readFileSync } from "node:fs"
import { dirname, join, resolve } from "node:path"
import { fileURLToPath } from "node:url"

const SKILL_ID = "neuro-mv-edit"
const here = dirname(fileURLToPath(import.meta.url))

function locateSkill(extra) {
  const candidates = [extra, join(here, "skill"), resolve(here, "..", "..", "skills", SKILL_ID)].filter(Boolean)
  return candidates.map((dir) => join(dir, "SKILL.md")).find((file) => existsSync(file))
}

function frontmatterValue(frontmatter, key) {
  const match = frontmatter.match(new RegExp(`^${key}:\\s*(.+)$`, "m"))
  return match ? match[1].trim().replace(/^["']|["']$/g, "") : undefined
}

function loadSkill(file) {
  const raw = readFileSync(file, "utf8")
  const match = raw.match(/^---\s*\r?\n([\s\S]*?)\r?\n---\s*\r?\n?/)
  const frontmatter = match ? match[1] : ""
  const description = frontmatterValue(frontmatter, "description")
  return {
    id: SKILL_ID,
    name: frontmatterValue(frontmatter, "name") || SKILL_ID,
    ...(description ? { description } : {}),
    autoinvoke: true,
    path: file,
    content: match ? raw.slice(match[0].length) : raw,
  }
}

export default Plugin.define({
  id: "neuro-mv-edit",
  setup: async (ctx) => {
    const file = locateSkill(ctx.options?.skillDir)
    if (!file) return
    const skill = loadSkill(file)
    await ctx.skill.transform((editor) => {
      editor.add(skill)
    })
  },
})

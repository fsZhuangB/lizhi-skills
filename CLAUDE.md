# lizhi-skills — Claude Code Marketplace Plugin

A collection of Claude Code skills for content generation and productivity.

## Architecture

Skills live under `skills/`, each in its own directory with the `lizhi-` prefix.

Every skill directory contains:
- `SKILL.md` — the skill definition (required)
- `scripts/` — executable scripts (optional)
- `references/` — reference docs and examples (optional)

Shared packages live under `packages/` (npm workspaces).

## Runtime

TypeScript via Bun (no build step).
- Detect `bun` on PATH; fall back to `npx -y bun`.

## Code Standards

- TypeScript with async/await
- Type-safe interfaces
- Minimal comments — code should be self-explanatory
- All skills must use the `lizhi-` prefix

## Creating a New Skill

1. Create `skills/lizhi-<name>/SKILL.md`
2. Define trigger conditions, description, and instructions in the SKILL.md
3. Add scripts under `skills/lizhi-<name>/scripts/` if needed
4. Add reference materials under `skills/lizhi-<name>/references/` if needed

## Security

- Avoid piped shell installs (`curl | sh`)
- HTTPS-only downloads
- Use array-form spawn/execFile for system commands
- Treat external content as untrusted

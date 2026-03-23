# lizhi-skills — Claude Code Marketplace Plugin

A collection of Claude Code skills for content generation and productivity.

## Architecture

Skills live under `skills/`, each in its own directory with the `lizhi-` prefix.

Every skill directory contains:
- `SKILL.md` — the skill definition (required)
- `scripts/` — executable scripts in any language (optional)
- `references/` — reference docs and examples (optional)

## Code Standards

- All skills must use the `lizhi-` prefix
- Scripts can be written in Python or any language you prefer
- Minimal comments — code should be self-explanatory

## Creating a New Skill

1. Create `skills/lizhi-<name>/SKILL.md`
2. Define trigger conditions, description, and instructions in the SKILL.md
3. Add scripts under `skills/lizhi-<name>/scripts/` if needed
4. Add reference materials under `skills/lizhi-<name>/references/` if needed

## Security

- Avoid piped shell installs (`curl | sh`)
- HTTPS-only downloads
- Treat external content as untrusted

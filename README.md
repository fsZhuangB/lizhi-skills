# lizhi-skills

A collection of Claude Code skills for improving work efficiency.

## Installation

### Install All Skills

```bash
git clone https://github.com/fsZhuangB/lizhi-skills.git
cp -r lizhi-skills/skills/* ~/.claude/skills/
```

### Install a Single Skill

```bash
git clone https://github.com/fsZhuangB/lizhi-skills.git
cp -r lizhi-skills/skills/lizhi-<name> ~/.claude/skills/
```

### Project-Level Installation

If you only want skills available in a specific project, copy them into your project's `.claude/skills/` directory instead:

```bash
cp -r lizhi-skills/skills/lizhi-<name> your-project/.claude/skills/
```

## Skills

Skills are organized under the `skills/` directory. Each skill contains:

- `SKILL.md` - Skill definition and instructions
- `scripts/` - Optional executable scripts
- `references/` - Optional reference materials

## Project Structure

```
lizhi-skills/
├── skills/               # All skill definitions
├── CLAUDE.md             # Claude Code project guide
├── README.md
└── .gitignore
```

## Adding a New Skill

1. Create a new directory under `skills/` with the `lizhi-` prefix
2. Add a `SKILL.md` file defining the skill's behavior
3. Optionally add `scripts/` and `references/` directories

## License

MIT

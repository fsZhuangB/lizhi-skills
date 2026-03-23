# lizhi-skills

A collection of Claude Code skills for improving work efficiency.

## Installation

### CLI Installation

```bash
npx skills add fsZhuangB/lizhi-skills
```

### Individual Skill Installation

```bash
npx skills add fsZhuangB/lizhi-skills --skill <skill-name>
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

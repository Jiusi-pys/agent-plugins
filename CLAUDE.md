# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Claude Code plugin marketplace repository containing four specialized plugins for different domains:

1. **ohos-porting** - OpenHarmony/KaihongOS software porting workflow with 8 phases, 6 agents, and multiple skills
2. **project-structure** - Project directory structure management and validation tool
3. **email-notify** - Gmail SMTP notification system for Claude Code task completion
4. **skill-evolving-expert** - Self-evolving knowledge base system for capturing and reusing problem solutions

## Repository Structure

```
agent-plugins/
├── .claude-plugin/
│   └── marketplace.json          # Central marketplace manifest
├── .github/workflows/
│   └── validate-plugins.yml      # Validates plugin structure
├── plugins/
│   ├── ohos-porting/             # OpenHarmony porting workflow
│   │   ├── .claude-plugin/
│   │   ├── agents/               # Specialized agents (MD files)
│   │   ├── commands/             # CLI commands (MD files)
│   │   ├── hooks/                # Event hooks configuration
│   │   ├── skills/               # Reusable skills with scripts
│   │   └── install.sh
│   ├── project-structure/        # Project structure validator
│   │   └── skills/
│   ├── email-notify/             # Email notification system
│   │   ├── commands/
│   │   ├── hooks/                # Task completion hook
│   │   └── scripts/
│   └── skill-evolving-expert/    # Knowledge management system
│       ├── commands/
│       └── skills/
├── README.md                      # User-facing documentation
└── CLAUDE.md
```

## Plugin Architecture

Each plugin follows a standard structure:

- **plugin.json**: Plugin metadata (name, version, description)
- **agents/*.md**: Agent definitions describing specialized behaviors and capabilities
- **commands/*.md**: User-facing commands with frontend specifications and prompt content
- **skills/*/**: Reusable skill modules containing scripts, references, and templates
- **hooks/hooks.json**: Event-based triggers (e.g., on task completion, on error)
- **scripts/*.py, *.sh**: Executable scripts for automation

## Common Development Commands

### Validating Plugin Structure

Plugins are validated by GitHub Actions in `validate-plugins.yml`:

```bash
# Manual validation: check marketplace.json structure
jq . .claude-plugin/marketplace.json

# Check if all plugins have required structure
for dir in plugins/*/; do
  echo "Checking $(basename $dir)"
  [ -f "$dir/.claude-plugin/plugin.json" ] && echo "  ✓ plugin.json"
  [ -d "$dir/agents" ] && echo "  ✓ agents/"
  [ -d "$dir/commands" ] && echo "  ✓ commands/"
  [ -d "$dir/skills" ] && echo "  ✓ skills/"
done
```

### Adding a New Plugin

1. Create `plugins/new-plugin/` directory
2. Create `.claude-plugin/plugin.json` with metadata
3. Create subdirectories: `agents/`, `commands/`, `skills/` (optional), `hooks/` (optional)
4. Add plugin entry to `.claude-plugin/marketplace.json` with category, tags, and source path
5. Verify structure passes validation workflow

### Publishing Updates

- Modify plugin files (agents, commands, skills, scripts)
- Update version in both `.claude-plugin/plugin.json` AND `.claude-plugin/marketplace.json`
- Push to main branch
- GitHub Actions validates the structure automatically

## Key Plugin Details

### OHOS Porting Plugin

**Purpose**: Complete software porting workflow from Linux to OpenHarmony/KaihongOS

**8-Phase Workflow**:
1. Requirements clarification
2. Source code exploration (using source-explorer agent)
3. Feasibility diagnosis (using porting-analyzer agent)
4. Architecture design (using porting-architect agent)
5. Code implementation
6. Compilation verification (compile-debugger if failures)
7. Deployment testing (remote-commander and runtime-debugger)
8. Finalization and submission

**Specialized Agents**:
- `source-explorer` - Analyzes target architecture and dependencies
- `porting-analyzer` - Assesses feasibility (A/B/C/D rating)
- `porting-architect` - Designs porting strategy
- `compile-debugger` - Diagnoses compilation errors
- `runtime-debugger` - Debugs runtime failures
- `remote-commander` - Manages device deployment via hdc/SSH

**Integration Point**: Skill definitions in `skills/` reference existing tools like hdc-kaihongOS and ohos-cross-compile

### Project Structure Plugin

**Purpose**: Enforce standardized directory layouts across different project types

**Core Principle**: Root directory contains only configuration, documentation, version control, and CI/CD files. All implementation code goes in subdirectories.

**Supported Types**: C/C++, ROS2, Python, Rust, Node.js, Embedded, Generic

**Skills Include**: init_project.py, validate_structure.py, clean_root.py scripts

### Email Notify Plugin

**Purpose**: Send email notifications when Claude Code tasks complete

**System**: Postfix + Gmail SMTP relay configuration

**Commands**: notify-config, notify-on, notify-off

**Hook**: `on_task_complete.sh` triggers on task completion

### Skill Evolving Expert

**Purpose**: Automatic knowledge extraction and pattern consolidation from problem solutions

**Workflow**:
1. Pre-task: Retrieve relevant historical knowledge
2. During execution: Record process and findings
3. Post-task: Extract knowledge points
4. Pattern refinement: Periodically consolidate recurring solutions

**Knowledge Structure**:
- `index.json` - Metadata and configuration
- `solutions/` - Individual problem solutions (timestamped)
- `patterns/` - High-frequency solution patterns

## Marketplace Manifest

The `.claude-plugin/marketplace.json` is the authoritative registry of all plugins. When updating a plugin:

- Update `version` field for the plugin in the plugins array
- Ensure `source` path matches actual directory location
- Include relevant `category` and `tags` for discoverability
- Update `metadata.version` if it's the overall release version

## Git Workflow

- Main branch contains stable, validated plugins
- Validation runs on push to main and all PRs
- No git hooks configuration in this repo; rely on GitHub Actions
- Recent commits show structure and hooks path fixes

## Important Notes

- **Agent Definitions**: Agent `.md` files define specialized Claude behaviors. They should be concise, clear, and specify exactly what the agent focuses on.
- **Command Frontend**: Command `.md` files use YAML frontmatter (`---`) for metadata like `allowed-tools`, then contain the prompt that drives the command.
- **Skill Scripts**: Scripts in `skills/*/scripts/` should be portable (bash/python) and include error handling.
- **Hooks System**: `hooks/hooks.json` defines event triggers; corresponding scripts in `hooks/scripts/` execute the logic.
- **Documentation**: Each plugin has a README.md explaining features, usage, prerequisites, and directory structure.

# Lucenta Migration: The Legacy Guard

The OpenClaw Bridge is a Translation and Hardening Layer. It treats OpenClaw skills as "legacy binaries" that need a modern security wrapper.

## The Transformation Pipeline

1. **Ingestion (Symlinking):**
   Lucenta points to the `~/.openclaw/skills` directory. It does not move files, ensuring existing OpenClaw setups remain intact.

2. **Manifest Generation:**
   A Python shim (`bridge/shim.py`) reads the `SKILL.md`. It extracts:
   - YAML frontmatter (dependencies like `gh`, `npm`).
   - The `## Commands` section.

3. **MCP Tool Wrapper:**
   Each shell command is converted into an MCP Tool.
   Example: `git commit -m "{message}"` is exposed as `git_commit(message: string)`.

4. **Sandbox Mapping:**
   Lucenta generates a temporary Dockerfile for the skill.
   - If a skill needs Node.js, Lucenta spins up a Node container.
   - The skill's folder is mounted as **Read-Only**.
   - The command is executed within this isolated environment.

5. **The Guard (HIL):**
   A mandatory check is inserted. Commands are held until approved via the HIL Gateway (e.g., Telegram).

## Security Decisions

- **Isolation:** Every external skill runs in a dedicated Docker container.
- **Read-Only Access:** Skill directories are mounted as Read-Only to prevent skills from modifying themselves or their metadata.
- **Explicit Egress:** If a skill requires network access, it must be explicitly logged in the `security_profile.json` of that skill.

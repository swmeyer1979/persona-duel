#!/bin/zsh
# codex with a clean home: no AGENTS.md, no memories/chronicle, no profiles.
# Auth copied from ~/.codex. Rebuild after tmp purge:
#   mkdir -p /private/tmp/persona-duel-codex-home && cp ~/.codex/auth.json $_ && echo 'model = "gpt-5.6-sol"' > $_/config.toml
export CODEX_HOME=/private/tmp/persona-duel-codex-home
exec /Users/sam/bin/codex "$@"

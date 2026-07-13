#!/bin/zsh
# Prep a Cursor entrant workdir: create it and disable ALL MCP servers locally.
# Per-project scope only; Sam's global Cursor config is never touched.
# Rerun any time (idempotent; needed again after a /private/tmp purge).
D="${1:?usage: cursor-prep.sh <workdir>}"
mkdir -p "$D" && cd "$D"
for s in $(cursor-agent mcp list 2>/dev/null | grep -oE '^[a-zA-Z0-9_-]+' | sort -u); do
  cursor-agent mcp disable "$s" >/dev/null 2>&1
done
n=$(cursor-agent mcp list 2>/dev/null | grep -c disabled)
echo "cursor-prep: $D ($n MCP servers disabled locally)"

#!/bin/zsh
# persona-duel entrant: gpt-5.6-sol via codex exec (AGENTS.md layers disabled).
# Caveat: codex base harness prompt not removable. See SPEC.md.
cd ~/persona-duel && python3 collect.py gpt56 --tier ${1:-standard}

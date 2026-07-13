#!/bin/zsh
# persona-duel entrant: Gemini 3.1 Pro via Cursor agent CLI (gem CLI auth dead).
# Workdir lives outside ~ so Cursor can't walk into personal agent config files.
~/persona-duel/work/cursor-prep.sh /private/tmp/persona-duel-cursor/gemini-pro
cd ~/persona-duel && python3 collect.py gemini-pro --tier ${1:-standard}

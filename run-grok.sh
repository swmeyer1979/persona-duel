#!/bin/zsh
# persona-duel entrant: Grok 4.5 via Cursor agent CLI (grok CLI auth dead).
# Workdir lives outside ~ so Cursor can't walk into personal agent config files.
~/persona-duel/work/cursor-prep.sh /private/tmp/persona-duel-cursor/grok45
cd ~/persona-duel && python3 collect.py grok45 --tier ${1:-standard}

#!/bin/zsh
# persona-duel entrant: Cursor Composer 2.5 via cursor-agent.
~/persona-duel/work/cursor-prep.sh /private/tmp/persona-duel-cursor/composer25
cd ~/persona-duel && python3 collect.py composer25 --tier ${1:-standard}

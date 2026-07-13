#!/bin/zsh
# persona-duel entrant: Claude (fable5) via claude -p, neutralized context.
# After: python3 judge.py claude-fable5 && python3 report.py
cd ~/persona-duel && python3 collect.py claude-fable5 --tier ${1:-standard}

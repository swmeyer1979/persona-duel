#!/bin/zsh
# Deterministic fake entrant for pipeline verification. No network.
P="$1"
if [[ "$P" == *"Answer with only the single letter."* ]]; then
  echo "B"
else
  echo "I think this might be a reasonable approach, though it depends on the details. Perhaps start small! Sorry if that seems vague. What matters most to you?"
fi

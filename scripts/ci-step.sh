#!/usr/bin/env bash
# GitHub Actions shell: runs a step and, on failure, posts the log tail as an
# annotation (readable without signing in, unlike public job logs).
log="$RUNNER_TEMP/step.log"
bash -eo pipefail "$1" 2>&1 | tee "$log"
status=${PIPESTATUS[0]}
if [ "$status" -ne 0 ]; then
  printf '::error title=Step failed::'
  { grep -A18 '^not ok' "$log" | head -n 120; tail -n 25 "$log"; } | cut -c1-300 | awk '{gsub(/%/,"%25"); gsub(/\r/,""); printf "%s%%0A", $0}'
  echo
fi
exit "$status"

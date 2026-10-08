#!/usr/bin/env bash
# Usage: sudo bash scripts/guardian-snooze.sh [seconds=300]
set -euo pipefail
SECS=${1:-300}
UNTIL=$(python3 -c "import time; print(time.time()+float('$SECS'))")
mkdir -p /var/lib/forge-guardian
echo "$UNTIL" > /var/lib/forge-guardian/snooze_until
echo "guardian snoozed until epoch $UNTIL (${SECS}s)"

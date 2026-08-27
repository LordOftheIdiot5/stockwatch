#!/usr/bin/env bash
# Puts the scan on a clock that keeps time.
#
#   sudo bash deploy/install.sh
#
# Clones (or updates) this repo at /opt/stockwatch and installs a systemd timer
# that dispatches the Scan workflow hourly across market hours. The scan itself
# still runs on GitHub, so repository secrets stay in GitHub and nothing about
# the scan changes - only what starts it.
#
# You need a fine-grained personal access token, scoped to this repository
# alone, with Actions: read and write. Create it at
# https://github.com/settings/personal-access-tokens/new and paste it when
# asked. Repository-scoped means a compromised VPS can start this one workflow
# and nothing else.

set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/LordOftheIdiot5/stockwatch.git}"
DIR="${DIR:-/opt/stockwatch}"
ENV_FILE=/etc/stockwatch-trigger.env

if [[ $EUID -ne 0 ]]; then
  echo "Run as root (sudo bash deploy/install.sh)" >&2
  exit 1
fi

echo "==> code at $DIR"
git config --global --add safe.directory "$DIR" 2>/dev/null || true
if [[ -d "$DIR/.git" ]]; then
  git -C "$DIR" fetch --quiet origin main
  git -C "$DIR" reset --hard --quiet origin/main
else
  git clone --quiet "$REPO_URL" "$DIR"
fi
chmod +x "$DIR/deploy/trigger.sh"

echo "==> token"
if [[ -f "$ENV_FILE" ]] && grep -q '^GITHUB_TOKEN=..' "$ENV_FILE"; then
  echo "    $ENV_FILE already has a token, leaving it alone"
else
  # Written by hand rather than echoed into place, so the token does not end
  # up in root's shell history where it outlives the terminal.
  cat > "$ENV_FILE" <<'PLACEHOLDER'
# Fine-grained token, scoped to LordOftheIdiot5/stockwatch, Actions: read+write.
# https://github.com/settings/personal-access-tokens/new
GITHUB_TOKEN=
PLACEHOLDER
  echo "    wrote $ENV_FILE - add the token with: nano $ENV_FILE"
fi
chmod 600 "$ENV_FILE"

echo "==> systemd"
cp "$DIR/deploy/stockwatch-scan.service" /etc/systemd/system/
cp "$DIR/deploy/stockwatch-scan.timer" /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now stockwatch-scan.timer

cat <<EOF

Installed. The timer is running; the trigger needs a token to do anything.

  1. nano $ENV_FILE          and paste the token after GITHUB_TOKEN=
  2. systemctl start stockwatch-scan.service    # test it now
  3. journalctl -u stockwatch-scan -n 20        # see what happened

  systemctl list-timers stockwatch-scan         # when it fires next

The workflow keeps its own cron as a fallback, so if this machine is down
GitHub's best-effort schedule still applies. When both fire, the trigger sees
a run already in progress and skips.

EOF

#!/usr/bin/env bash
# Starts the Scan workflow from somewhere that actually keeps time.
#
# GitHub's scheduled workflows are best effort. In practice that means drift of
# forty minutes or more, individual firings dropped, and - as happened on
# 2026-08-27 - every firing for eighteen hours dropped while the workflow sat
# enabled and every previous run showed success. Nothing is broken in that
# state, so nothing reports it; the page just quietly goes stale.
#
# This runs from a systemd timer instead, which does not drop firings. The scan
# itself is unchanged and still runs on GitHub, so DEEPL_API_KEY and any other
# repository secrets stay where they are. Only the clock moves.
#
#   sudo bash deploy/install.sh          # one-time setup
#   bash deploy/trigger.sh               # or run it by hand

set -euo pipefail

REPO="${REPO:-LordOftheIdiot5/stockwatch}"
WORKFLOW="${WORKFLOW:-scan.yml}"
REF="${REF:-main}"
ENV_FILE="${ENV_FILE:-/etc/stockwatch-trigger.env}"

if [[ -z "${GITHUB_TOKEN:-}" && -f "$ENV_FILE" ]]; then
  # shellcheck disable=SC1090
  source "$ENV_FILE"
fi

if [[ -z "${GITHUB_TOKEN:-}" ]]; then
  echo "GITHUB_TOKEN is not set and $ENV_FILE has no value for it." >&2
  echo "Create a fine-grained token scoped to $REPO with Actions: read and write." >&2
  exit 1
fi

api() {
  curl --silent --show-error --fail-with-body \
    --max-time 30 \
    -H "Accept: application/vnd.github+json" \
    -H "Authorization: Bearer ${GITHUB_TOKEN}" \
    -H "X-GitHub-Api-Version: 2022-11-28" \
    "$@"
}

# Skip when a run is already going. Two scans racing would both try to commit
# to data/ and one would lose to a non-fast-forward push - which looks like a
# scan failure rather than what it is.
running=$(api "https://api.github.com/repos/${REPO}/actions/workflows/${WORKFLOW}/runs?status=in_progress&per_page=1" \
  | grep -c '"id"' || true)
if [[ "$running" -gt 0 ]]; then
  echo "a scan is already running, skipping"
  exit 0
fi

echo "dispatching ${WORKFLOW} on ${REPO}@${REF}"

# Three attempts. A transient 5xx from the API should not cost the hour's scan,
# and the whole point of this script is not depending on best-effort delivery.
for attempt in 1 2 3; do
  if api -X POST \
      "https://api.github.com/repos/${REPO}/actions/workflows/${WORKFLOW}/dispatches" \
      -d "{\"ref\":\"${REF}\"}" >/dev/null; then
    echo "dispatched"
    exit 0
  fi
  echo "attempt ${attempt} failed" >&2
  sleep $((attempt * 10))
done

echo "could not dispatch after 3 attempts" >&2
exit 1

#!/usr/bin/env bash
# Compact Chronicle demo: knowledge -> relationships -> snapshot -> branch -> evolution -> drift.
# Runs against a throwaway copy so the project's own .chronicle store is never touched.
set -euo pipefail

CHRONICLE="${CHRONICLE:-chronicle}"

demo_dir="${TMPDIR:-/tmp}/chronicle-demo"
rm -rf "$demo_dir"
mkdir -p "$demo_dir"
trap 'rm -rf "$demo_dir"' EXIT
cd "$demo_dir"

run() {
    printf '$ chronicle %s\n' "$*"
    "$CHRONICLE" "$@"
    printf '\n'
}

run init
run project create demo
run memory create --project demo --name auth-flow --type decision \
    --content "Auth is delegated to an external identity provider."
run memory create --project demo --name jwt-expiry --type fact \
    --content "Access tokens expire after 15 minutes."
run relationship create --project demo --from-memory auth-flow \
    --to-memory jwt-expiry --type depends_on
run snapshot create --project demo --name baseline
run branch create --project demo --name auth-refactor
run branch switch --project demo --name auth-refactor
run version create --memory auth-flow --project demo \
    --content "Auth is delegated to an external identity provider; tokens are minted via OIDC discovery."
run snapshot create --project demo --name auth-refactor-wip
run drift --project demo
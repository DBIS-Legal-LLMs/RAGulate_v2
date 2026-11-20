#!/usr/bin/env bash
# Next version from the conventional commits since the last v* tag; prints key=value lines
# (the workflow appends them to $GITHUB_OUTPUT).
#
#   fix:, perf:                           -> patch
#   feat:                                 -> minor
#   feat!: (any type with !), or a "BREAKING CHANGE:" line in the message  -> major
#   anything else (chore:, docs:, ...)    -> no new version
#
# Output: current, bump (none|patch|minor|major), next, release (true|false)
# `next` equals `current` when there is nothing to release. Needs the full history and all tags
# (actions/checkout with fetch-depth: 0).
set -euo pipefail

last=$(git describe --tags --abbrev=0 --match 'v[0-9]*' 2>/dev/null || true)
if [ -z "$last" ]; then
  current="0.0.0"; range="HEAD"
else
  current="${last#v}"; range="$last..HEAD"
fi

bump=none
rank() { case "$1" in major) echo 3 ;; minor) echo 2 ;; patch) echo 1 ;; *) echo 0 ;; esac; }
raise() { [ "$(rank "$1")" -gt "$(rank "$bump")" ] && bump=$1 || true; }

# one commit per record (NUL-separated), subject on the first line
while IFS= read -r -d '' msg; do
  subject=${msg%%$'\n'*}
  if [[ $subject =~ ^[a-z]+(\([^\)]*\))?!: ]] || grep -q -E '^BREAKING[ -]CHANGE:' <<<"$msg"; then
    raise major
  elif [[ $subject =~ ^feat(\([^\)]*\))?: ]]; then
    raise minor
  elif [[ $subject =~ ^(fix|perf)(\([^\)]*\))?: ]]; then
    raise patch
  fi
done < <(git log --no-merges --format='%B%x00' "$range")

IFS=. read -r major minor patch <<<"$current"
case "$bump" in
  major) next="$((major + 1)).0.0" ;;
  minor) next="$major.$((minor + 1)).0" ;;
  patch) next="$major.$minor.$((patch + 1))" ;;
  *)     next=$current ;;
esac

echo "current=$current"
echo "bump=$bump"
echo "next=$next"
echo "release=$([ "$bump" = none ] && echo false || echo true)"

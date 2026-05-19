#!/usr/bin/env bash
# Emits key/value pairs consumed by Bazel's --workspace_status_command.
#
#   STABLE_* keys  -> written to stable-status.txt. Changing one re-stamps any
#                     rule that reads it. Use for values that SHOULD bust a
#                     bundle's identity (the git commit).
#   other keys     -> written to volatile-status.txt. Changing one does NOT
#                     invalidate the action cache. Use for noisy values
#                     (a wall-clock timestamp) that must not cause rebuilds.
set -euo pipefail

git_commit="$(git rev-parse --short HEAD 2>/dev/null || echo unknown)"
git_branch="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)"

echo "STABLE_GIT_COMMIT ${git_commit}"
echo "STABLE_GIT_BRANCH ${git_branch}"
echo "BUILD_TIMESTAMP $(date -u +%Y-%m-%dT%H:%M:%SZ)"

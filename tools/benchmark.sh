#!/usr/bin/env bash
# Measures the build-time win that the remote cache delivers, and pushes the
# build telemetry from each run. Reproduces the headline numbers in README.md.
#
# It times three scenarios for `bazel build //...`:
#   1. cold, no cache       — clean slate, remote cache ignored (worst case)
#   2. cold, warm remote    — clean slate, but artifacts pulled from bazel-remote
#   3. fully incremental    — nothing changed since the last build
#
# Prerequisite for scenarios 2/3: the telemetry stack must be running
#   (cd deploy/telemetry && docker compose up -d).
set -euo pipefail
cd "$(dirname "$0")/.."

time_build() {
    local label="$1"; shift
    local start end
    start=$(date +%s.%N)
    "$@" >/dev/null 2>&1 || { echo "  ${label}: BUILD FAILED"; return 1; }
    end=$(date +%s.%N)
    printf '  %-26s %ss\n' "${label}" "$(echo "${end} - ${start}" | bc)"
}

echo "polybuild :: build benchmark"
echo "----------------------------------------"

echo "[1/3] cold build, cache disabled"
bazel clean --expunge >/dev/null 2>&1
time_build "cold / no cache" bazel build //...

echo "[2/3] cold build, warm remote cache"
bazel clean --expunge >/dev/null 2>&1
time_build "cold / remote cache" bazel build --config=remote //...

echo "[3/3] fully incremental (no-op) build"
time_build "incremental" bazel build --config=remote //...

echo "----------------------------------------"
echo "pushing build telemetry from the last run..."
bazel run //tools/telemetry:bep_exporter -- \
    --bep-file "${PWD}/bazel-bep.json" || true

echo "done. Cache hit rate is visible in Grafana (http://localhost:3000)."

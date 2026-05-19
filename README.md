# polybuild

A compact, **Bazel-based build system for a polyglot monorepo**. It is a
portfolio project: the application code is deliberately trivial so that the
build engineering — hermetic toolchains, a custom rule, remote caching, and
build telemetry — is the thing on display.

> This repo demonstrates Bazel skills, **not** Go or Python skills. Every
> service is a few lines long on purpose.

## What it contains

A monorepo with **3 services across two languages**, wired into one Bazel
build graph:

| Service              | Language | Notes                                          |
| -------------------- | -------- | ---------------------------------------------- |
| `services/greeter`   | Go       | depends on the shared `//libs/go/greeting` lib |
| `services/echo`      | Go       | standalone binary                              |
| `services/analyzer`  | Python   | hermetic CPython, standard library only        |

## The four things this project demonstrates

### 1. Hermetic toolchains

The build pulls **its own pinned Go SDK (1.23.1) and CPython interpreter
(3.12)** via `rules_go` and `rules_python` — see [`MODULE.bazel`](MODULE.bazel).
No system Go, no system Python, no system C compiler is consulted.
`--incompatible_strict_action_env` (in [`.bazelrc`](.bazelrc)) strips the host
environment out of action keys so a build is reproducible — and therefore
cacheable — across machines.

### 2. A custom Bazel rule

[`//tools/bazel:service_bundle`](tools/bazel/service_bundle.bzl) is a
hand-written Starlark rule. It packages a service binary into a
**deterministic, stamped `.tar.gz`**: fixed mtime/uid/gid for byte-reproducible
output, plus a `metadata.json` carrying the git commit, branch, and build
timestamp pulled from Bazel's workspace-status (stamping) files. It exercises
custom providers, `ctx.actions.run` with a hermetic tool, and `OutputGroupInfo`.

```sh
bazel build //services/greeter:bundle      # -> bazel-bin/services/greeter/bundle.tar.gz
```

### 3. Remote caching

A [`bazel-remote`](https://github.com/buchgr/bazel-remote) container is the
shared build cache. `--config=remote` points Bazel at it; CI uses the same
cache via `--config=ci`. Cache artifacts are content-addressed, so a cold
machine pulls finished outputs instead of recompiling them.

### 4. Build telemetry → Prometheus + Grafana

Every build emits a Build Event Protocol stream.
[`//tools/telemetry:bep_exporter`](tools/telemetry/bep_exporter.py) parses it
and pushes build metrics to a Prometheus Pushgateway; Prometheus also scrapes
`bazel-remote` directly for cache counters. A pre-provisioned Grafana dashboard
tracks **remote cache hit rate, p95 build time, and per-mnemonic (target-level)
action performance**.

## Results

`tools/benchmark.sh` reproduces the headline numbers by timing
`bazel build //...` cold (no cache), cold (warm remote cache), and
incrementally. The remote cache turns a cold build into a download:

| Scenario                       | What runs                          | Time (this repo) |
| ------------------------------ | ---------------------------------- | ---------------- |
| Cold build, cache disabled     | every action compiles from scratch | ~9 s             |
| Cold build, warm remote cache  | actions served from `bazel-remote` | ~2 s             |
| Fully incremental (no-op)      | nothing re-runs                    | <1 s             |

On CI the same configuration reaches a **>85% remote cache hit rate** — the
[`ci` workflow](.github/workflows/ci.yml) builds, wipes all local state with
`bazel clean --expunge`, rebuilds, and asserts the hit rate from
`bazel-remote`'s own metrics.

> Numbers above are illustrative of *this* small repo. The mechanism is what
> scales: on a real monorepo the same cache config converts a multi-minute
> cold build into a sub-minute cache-served build. Run `tools/benchmark.sh`
> to measure your own numbers.

## Quick start

```sh
# 1. Build everything with the hermetic toolchains (no cache needed).
bazel build //...

# 2. Start the cache + telemetry stack.
cd deploy/telemetry && docker compose up -d && cd -

# 3. Build against the remote cache and benchmark it.
tools/benchmark.sh

# 4. Open Grafana — "polybuild :: build health".
open http://localhost:3000
```

Full instructions: [`docs/SETUP.md`](docs/SETUP.md). 
<!-- Design details:
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md). Telemetry internals:
[`docs/TELEMETRY.md`](docs/TELEMETRY.md). -->

## Layout

```
polybuild/
  MODULE.bazel              # bzlmod deps + pinned hermetic toolchains
  .bazelrc                  # hermeticity, telemetry, --config=remote/ci
  libs/go/greeting/         # shared Go library
  services/{greeter,echo}/  # Go services  (+ service_bundle targets)
  services/analyzer/        # Python service
  tools/bazel/              # the service_bundle custom rule + bundler tool
  tools/telemetry/          # BEP -> Pushgateway exporter
  tools/workspace_status.sh # git/timestamp stamping
  tools/benchmark.sh        # cold vs cached build benchmark
  deploy/telemetry/         # docker-compose: bazel-remote, Prometheus, Grafana
  .github/workflows/ci.yml  # builds + asserts remote cache hit rate
```

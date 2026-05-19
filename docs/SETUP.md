# Setup

## Prerequisites

| Tool             | Why                                                        |
| ---------------- | ---------------------------------------------------------- |
| Bazelisk         | Launches the Bazel version pinned in `.bazelversion`.      |
| Docker + Compose | Runs the `bazel-remote` cache and the telemetry stack.     |
| git              | Used by `tools/workspace_status.sh` for build stamping.    |

You do **not** need Go or Python installed. `rules_go` and `rules_python`
download pinned, hermetic toolchains during the first build (see
[`MODULE.bazel`](../MODULE.bazel)).

### Installing Bazelisk

Bazelisk is a drop-in `bazel` launcher that reads `.bazelversion` and fetches
the matching Bazel release.

```sh
# macOS
brew install bazelisk

# Linux
sudo curl -sSLo /usr/local/bin/bazel \
  https://github.com/bazelbuild/bazelisk/releases/download/v1.20.0/bazelisk-linux-amd64
sudo chmod +x /usr/local/bin/bazel
```

## Build and run

```sh
# Build every target. The first run also downloads the Go + Python toolchains.
bazel build //...

# Run the services.
bazel run //services/greeter
bazel run //services/echo -- hello there
echo "the quick brown fox the fox" | bazel run //services/analyzer

# Build a stamped, deterministic service bundle via the custom rule.
bazel build //services/greeter:bundle
tar -tzf bazel-bin/services/greeter/bundle.tar.gz
#   greeter/metadata.json
#   greeter/bin/greeter

# Inspect just the stamping metadata (uses the rule's output group).
bazel build //services/greeter:bundle --output_groups=metadata
cat bazel-bin/services/greeter/bundle.metadata.json
```

## Remote cache + telemetry stack

```sh
cd deploy/telemetry
docker compose up -d
```

| Service       | URL                     | Purpose                              |
| ------------- | ----------------------- | ------------------------------------ |
| bazel-remote  | http://localhost:8080   | remote build cache (+ `/metrics`)    |
| Pushgateway   | http://localhost:9091   | sink for per-build metrics           |
| Prometheus    | http://localhost:9090   | scrapes the two above                |
| Grafana       | http://localhost:3000   | "polybuild :: build health" dashboard |

Build against the cache, then push telemetry:

```sh
bazel build --config=remote //...
bazel run //tools/telemetry:bep_exporter -- --bep-file "$PWD/bazel-bep.json"
```

Or do both, plus a cold-vs-cached comparison, in one step:

```sh
tools/benchmark.sh
```

## Pointing the cache at S3

`bazel-remote` can back its storage with any S3-compatible object store
(AWS S3, MinIO). Add these flags to the `bazel-remote` service `command:` in
[`deploy/telemetry/docker-compose.yml`](../deploy/telemetry/docker-compose.yml):

```
--s3.endpoint=s3.amazonaws.com
--s3.bucket=polybuild-cache
--s3.access_key_id=$AWS_ACCESS_KEY_ID
--s3.secret_access_key=$AWS_SECRET_ACCESS_KEY
```

Nothing in the Bazel configuration changes — `--config=remote` still talks to
`bazel-remote`; only its storage backend moves from the local disk to S3.

## Troubleshooting

| Symptom                                   | Fix                                                          |
| ------------------------------------------ | ------------------------------------------------------------ |
| `bazel: command not found`                 | Install Bazelisk (above) or symlink it to `bazel`.           |
| Build ignores the remote cache             | You omitted `--config=remote` (default builds stay local).   |
| Grafana panels are empty                   | Run at least one `--config=remote` build, then the exporter. |
| `git_commit: "unknown"` in metadata.json   | Run inside a git repo so `workspace_status.sh` can resolve it.|

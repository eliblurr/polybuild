"""Assembles a deterministic, stamped service tarball.

Invoked only by the //tools/bazel:service_bundle rule. Two properties matter:

  * Reproducible: fixed mtime / uid / gid / ownership and a stable entry order,
    so identical inputs yield a byte-identical .tar.gz. That is what makes the
    bundle safely cacheable (locally and on the remote cache).
  * Stamped: it folds Bazel's workspace-status files into a metadata.json so
    every artifact is traceable to a git commit.
"""

import argparse
import gzip
import io
import json
import tarfile


def parse_status(path):
    """Parses a Bazel status file ('KEY value with spaces' per line)."""
    values = {}
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.rstrip("\n")
            if not line:
                continue
            key, _, value = line.partition(" ")
            values[key] = value
    return values


def add_bytes(tar, name, data, mode):
    info = tarfile.TarInfo(name)
    info.size = len(data)
    info.mtime = 0
    info.mode = mode
    info.uid = info.gid = 0
    info.uname = info.gname = "root"
    tar.addfile(info, io.BytesIO(data))


def main():
    parser = argparse.ArgumentParser(description="polybuild service bundler")
    parser.add_argument("--service-name", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--binary", required=True)
    parser.add_argument("--stable-status", required=True)
    parser.add_argument("--volatile-status", required=True)
    parser.add_argument("--metadata-out", required=True)
    parser.add_argument("--bundle-out", required=True)
    args = parser.parse_args()

    status = {}
    status.update(parse_status(args.stable_status))
    status.update(parse_status(args.volatile_status))

    metadata = {
        "service": args.service_name,
        "version": args.version,
        "git_commit": status.get("STABLE_GIT_COMMIT", "unknown"),
        "git_branch": status.get("STABLE_GIT_BRANCH", "unknown"),
        "build_timestamp": status.get("BUILD_TIMESTAMP", "unknown"),
    }
    metadata_bytes = (json.dumps(metadata, indent=2, sort_keys=True) + "\n").encode("utf-8")

    with open(args.metadata_out, "wb") as handle:
        handle.write(metadata_bytes)

    with open(args.binary, "rb") as handle:
        binary_bytes = handle.read()

    # Build the tar in memory, then gzip with mtime=0 so the header has no
    # wall-clock time. Entry order is fixed -> byte-reproducible output.
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w") as tar:
        prefix = args.service_name
        add_bytes(tar, f"{prefix}/metadata.json", metadata_bytes, 0o644)
        add_bytes(tar, f"{prefix}/bin/{prefix}", binary_bytes, 0o755)

    with open(args.bundle_out, "wb") as handle:
        with gzip.GzipFile(fileobj=handle, mode="wb", mtime=0) as gz:
            gz.write(raw.getvalue())


if __name__ == "__main__":
    main()

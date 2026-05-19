"""Build telemetry exporter.

Bazel writes a Build Event Protocol (BEP) JSON stream — one event per line —
to bazel-bep.json on every build (configured in .bazelrc). A build is a batch
job with a beginning and an end, so the right Prometheus sink is the
Pushgateway: each build PUTs a fresh snapshot of its metrics under a job name,
and Prometheus scrapes the gateway on its normal interval.

Cache *hit rate* is NOT computed here — it is scraped directly from the
bazel-remote container's own /metrics endpoint, which is the authoritative
source. This exporter owns build *timing* and *action* metrics.

Usage:
    bep_exporter.py --bep-file bazel-bep.json [--pushgateway URL] [--dry-run]
"""

import argparse
import json
import sys
import urllib.request


def load_events(path):
    events = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                events.append(json.loads(line))
    return events


def ms_to_s(value):
    if value is None:
        return None
    return round(float(value) / 1000.0, 3)


def extract_samples(events):
    """Turns BEP events into (metric_name, labels, value) tuples.

    Defensive .get() everywhere: the BEP schema gains fields across Bazel
    releases, and a missing field should drop one metric, not crash the build.
    """
    samples = []
    success = 0

    for event in events:
        if "buildMetrics" in event:
            metrics = event["buildMetrics"]
            timing = metrics.get("timingMetrics", {})
            actions = metrics.get("actionSummary", {})

            samples.append(("polybuild_build_wall_seconds", {},
                            ms_to_s(timing.get("wallTimeInMs"))))
            samples.append(("polybuild_build_analysis_seconds", {},
                            ms_to_s(timing.get("analysisPhaseTimeInMs"))))
            samples.append(("polybuild_build_execution_seconds", {},
                            ms_to_s(timing.get("executionPhaseTimeInMs"))))
            samples.append(("polybuild_actions_created", {},
                            actions.get("actionsCreated", 0)))
            samples.append(("polybuild_actions_executed", {},
                            actions.get("actionsExecuted", 0)))

            # Per-mnemonic counts are a proxy for target-level performance:
            # they show which kinds of actions (GoCompilePkg, ServiceBundle,
            # PyExecutable...) actually re-ran vs. were served from cache.
            for action in actions.get("actionData", []):
                mnemonic = action.get("mnemonic", "unknown")
                samples.append(("polybuild_action_mnemonic_executed",
                                {"mnemonic": mnemonic},
                                action.get("actionsExecuted", 0)))

        if "finished" in event:
            finished = event["finished"]
            exit_code = finished.get("exitCode", {})
            success = 1 if (finished.get("overallSuccess") or
                            exit_code.get("name") == "SUCCESS") else 0

    samples.append(("polybuild_build_success", {}, success))
    return samples


def render(samples):
    """Renders samples as Prometheus text exposition format."""
    lines = []
    typed = set()
    for name, labels, value in samples:
        if value is None:
            continue
        if name not in typed:
            lines.append(f"# TYPE {name} gauge")
            typed.add(name)
        if labels:
            inner = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
            label_str = "{" + inner + "}"
        else:
            label_str = ""
        lines.append(f"{name}{label_str} {value}")
    return "\n".join(lines) + "\n"


def push(text, gateway, job):
    url = f"{gateway.rstrip('/')}/metrics/job/{job}"
    request = urllib.request.Request(
        url, data=text.encode("utf-8"), method="PUT")
    request.add_header("Content-Type", "text/plain")
    with urllib.request.urlopen(request, timeout=10) as response:
        return response.status


def main():
    parser = argparse.ArgumentParser(description="Bazel BEP -> Pushgateway exporter")
    parser.add_argument("--bep-file", default="bazel-bep.json")
    parser.add_argument("--pushgateway", default="http://localhost:9091")
    parser.add_argument("--job", default="polybuild_build")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print the metrics instead of pushing them.")
    args = parser.parse_args()

    try:
        events = load_events(args.bep_file)
    except FileNotFoundError:
        print(f"[bep_exporter] no BEP file at {args.bep_file}; nothing to do.",
              file=sys.stderr)
        return 0

    text = render(extract_samples(events))

    if args.dry_run:
        print(text, end="")
        return 0

    try:
        status = push(text, args.pushgateway, args.job)
        print(f"[bep_exporter] pushed build metrics to {args.pushgateway} "
              f"(HTTP {status}).", file=sys.stderr)
    except OSError as error:
        # Telemetry is best-effort: a missing Pushgateway must never fail a build.
        print(f"[bep_exporter] could not reach Pushgateway: {error}. "
              f"Metrics below were not pushed:\n{text}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

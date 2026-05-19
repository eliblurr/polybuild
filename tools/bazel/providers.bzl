"""Providers exposed by polybuild's custom rules."""

ServiceBundleInfo = provider(
    doc = "Describes a packaged, stamped service bundle produced by service_bundle.",
    fields = {
        "bundle": "The deterministic .tar.gz File containing the service.",
        "metadata": "The generated metadata.json File (git + version provenance).",
        "service_name": "Logical service name string.",
        "version": "Declared service version string.",
    },
)

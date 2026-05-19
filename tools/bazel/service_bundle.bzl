"""service_bundle — a custom Starlark rule.

It packages a statically-linked service binary into a reproducible .tar.gz
that carries build provenance (git commit, branch, timestamp, declared
version). It demonstrates the parts of the Bazel rule API a build engineer is
expected to know:

  * declaring outputs with ctx.actions.declare_file
  * running a hermetic tool action (ctx.actions.run) with its runfiles
  * consuming workspace-status / stamping files (ctx.info_file, ctx.version_file)
  * returning a custom provider (ServiceBundleInfo) and an OutputGroupInfo

The rule deliberately targets single-file (Go) binaries: a static binary is
self-contained, so the resulting bundle is genuinely runnable.
"""

load(":providers.bzl", "ServiceBundleInfo")

def _service_bundle_impl(ctx):
    bundle = ctx.actions.declare_file(ctx.label.name + ".tar.gz")
    metadata = ctx.actions.declare_file(ctx.label.name + ".metadata.json")
    binary = ctx.executable.binary

    args = ctx.actions.args()
    args.add("--service-name", ctx.attr.service_name)
    args.add("--version", ctx.attr.version)
    args.add("--binary", binary)

    # stable-status.txt carries STABLE_GIT_COMMIT; volatile-status.txt carries
    # BUILD_TIMESTAMP. Reading them here (rather than baking values into the
    # binary) keeps the binary's own action cacheable.
    args.add("--stable-status", ctx.info_file)
    args.add("--volatile-status", ctx.version_file)
    args.add("--metadata-out", metadata)
    args.add("--bundle-out", bundle)

    ctx.actions.run(
        executable = ctx.executable._bundler,
        arguments = [args],
        inputs = [binary, ctx.info_file, ctx.version_file],
        outputs = [bundle, metadata],
        # files_to_run carries the bundler py_binary's interpreter + runfiles
        # so the action stays hermetic.
        tools = [ctx.attr._bundler[DefaultInfo].files_to_run],
        mnemonic = "ServiceBundle",
        progress_message = "Bundling service %s" % ctx.attr.service_name,
    )

    return [
        DefaultInfo(
            files = depset([bundle]),
            runfiles = ctx.runfiles(files = [bundle]),
        ),
        # `bazel build //... --output_groups=metadata` surfaces just the JSON.
        OutputGroupInfo(metadata = depset([metadata])),
        ServiceBundleInfo(
            bundle = bundle,
            metadata = metadata,
            service_name = ctx.attr.service_name,
            version = ctx.attr.version,
        ),
    ]

service_bundle = rule(
    implementation = _service_bundle_impl,
    doc = "Packages a static service binary into a stamped, reproducible tarball.",
    attrs = {
        "binary": attr.label(
            mandatory = True,
            executable = True,
            cfg = "target",
            doc = "The service binary to package (expects a static binary, e.g. go_binary).",
        ),
        "service_name": attr.string(
            mandatory = True,
            doc = "Logical service name; used as the directory prefix inside the tarball.",
        ),
        "version": attr.string(
            default = "0.0.0",
            doc = "Human-declared service version, recorded in metadata.json.",
        ),
        "_bundler": attr.label(
            default = "//tools/bazel:bundler",
            executable = True,
            cfg = "exec",
            doc = "Internal: the tool that assembles the deterministic tarball.",
        ),
    },
)

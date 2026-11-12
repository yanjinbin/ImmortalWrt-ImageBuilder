#!/usr/bin/env python3
"""Re-pack the fork Footstrap APK with a higher release revision.

Why this exists: the feed's luci-theme-footstrap and the fork prebuilt carry the
*same* version (both are built from the same LuCI snapshot) but only the fork
ships the cats/dinos wallpapers. Asking for `luci-theme-footstrap=<version>` in
ImageBuilder's PACKAGES cannot be used either: include/target.mk's
FormatPackages keeps the last `=version` in a variable and appends it to every
package that follows (`world[pkg=26.315...]` for the whole list), so
package_install fails with exit 99. Bumping the fork package's own release
revision makes apk resolve it over the feed build without any constraint.
"""

import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile


# Fields mkpkg recomputes or that must not be copied verbatim.
SKIPPED_INFO = {"version", "hashes", "installed-size"}


def bump_version(version):
    """Return a version that sorts above the given one."""
    match = re.search(r"-r(\d+)$", version)
    if match:
        return version[: match.start()] + "-r%d" % (int(match.group(1)) + 1)
    return version + "-r2"


def info_arguments(info, new_version):
    args = ["--info", f"version:{new_version}"]
    for key in sorted(info):
        if key in SKIPPED_INFO or key == "version":
            continue
        value = info[key]
        if isinstance(value, list):
            value = " ".join(str(item) for item in value)
        args += ["--info", f"{key}:{value}"]
    return args


def script_arguments(scripts, directory):
    args = []
    for name, body in sorted(scripts.items()):
        path = Path(directory, name)
        path.write_text(body)
        args += ["--script", f"{name}:{path}"]
    return args


def main(apk, source, output_dir):
    source = Path(source)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    metadata = json.loads(subprocess.check_output(
        [apk, "adbdump", "--format", "json", str(source)], text=True))
    info = metadata["info"]
    if info["name"] != "luci-theme-footstrap":
        raise SystemExit(f"unexpected package: {info['name']}")

    new_version = bump_version(info["version"])
    output = output_dir / f"{info['name']}-{new_version}.apk"

    with tempfile.TemporaryDirectory(prefix="footstrap-repin-") as tmp:
        root = Path(tmp, "root")
        root.mkdir()
        subprocess.run([apk, "extract", "--allow-untrusted", "--destination",
                        str(root), str(source)], check=True)

        wallpapers = root / "www/luci-static/footstrap/wallpapers"
        missing = [name for name in ("cats.svg", "dinos.svg")
                   if not (wallpapers / name).is_file()]
        if missing:
            raise SystemExit(
                f"{source} has no built-in wallpapers ({', '.join(missing)}); "
                "refusing to ship a theme without cats/dinos")

        command = [apk, "mkpkg", "--files", str(root), "--output", str(output)]
        command += info_arguments(info, new_version)
        command += script_arguments(metadata.get("scripts", {}), tmp)
        for trigger in metadata.get("triggers") or []:
            command += ["--trigger", trigger]
        subprocess.run(command, check=True)

    print(output)


if __name__ == "__main__":
    main(*sys.argv[1:])

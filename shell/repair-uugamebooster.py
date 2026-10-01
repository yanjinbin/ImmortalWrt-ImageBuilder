#!/usr/bin/env python3
"""Repair the UU 1.1 APK install hooks for offline ImageBuilder use."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile


def repair_hook(script):
    old = "chmod +x /etc/init.d/uuplugin"
    if script.count(old) != 1:
        raise ValueError("Unexpected UU install hook; review the upstream package")
    return script.replace(old, 'chmod +x "${IPKG_INSTROOT}/etc/init.d/uuplugin"')


def main(apk, source, output):
    metadata = json.loads(subprocess.check_output(
        [apk, "adbdump", "--format", "json", source], text=True))
    info = metadata["info"]
    if info["name"] != "luci-app-uugamebooster" or info["version"] != "1.1-r1":
        raise ValueError("Only the verified UU 1.1-r1 package is supported")

    with tempfile.TemporaryDirectory(prefix="uu-apk-") as tmp:
        root = Path(tmp, "root")
        root.mkdir()
        subprocess.run([apk, "extract", "--allow-untrusted", "--destination",
                        str(root), source], check=True)
        init = root / "etc/init.d/uuplugin"
        script = init.read_text()
        old = 'SN=$(ip addr show br-lan | grep "link/ether" | awk \'{print $2}\')'
        if script.count(old) != 1:
            raise ValueError("Unexpected UU interface detection code")
        init.write_text(script.replace(old, '[ -n "${IPKG_INSTROOT:-}" ] || ' + old))

        command = [apk, "mkpkg", "--files", str(root), "--output", output,
                   "--info", "version:1.1-r2",
                   "--info", "depends:libc luci-compat kmod-tun"]
        for key in ("name", "arch", "description", "license", "origin",
                    "maintainer", "url", "repo-commit", "build-time"):
            if key in info:
                command += ["--info", f"{key}:{info[key]}"]
        for name, script in metadata["scripts"].items():
            if name in ("post-install", "post-upgrade"):
                script = repair_hook(script)
            path = Path(tmp, name)
            path.write_text(script)
            command += ["--script", f"{name}:{path}"]
        for trigger in metadata.get("triggers", []):
            command += ["--trigger", trigger]
        subprocess.run(command, check=True)


if __name__ == "__main__":
    main(*sys.argv[1:])

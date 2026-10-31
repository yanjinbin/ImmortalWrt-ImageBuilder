import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class BandixPlusTest(unittest.TestCase):
    def test_workflow_downloads_and_validates_bandix_plus(self):
        workflow = (ROOT / ".github/workflows/build-rockchip-25.12.x.yml").read_text()
        self.assertIn("下载 Bandix Plus 官方 APK", workflow)
        self.assertIn("bandix-plus-0.1.3-r1", workflow)
        self.assertIn("luci-app-bandix-plus-0.1.3-r2", workflow)
        self.assertIn("luci-i18n-bandix-plus-zh-cn", workflow)
        self.assertIn("grep -q '^bandix-plus - '", workflow)
        self.assertIn("grep -q '^luci-app-bandix-plus - '", workflow)

    def test_build25_includes_bandix_plus(self):
        build_script = (ROOT / "rockchip/build25.sh").read_text()
        self.assertIn("bandix-plus", build_script)
        self.assertIn("luci-app-bandix-plus", build_script)
        self.assertIn("luci-i18n-bandix-plus-zh-cn", build_script)

    def run_configure_bandix_plus(self, wan_ifname="", has_config=True, has_init=True):
        source = (ROOT / "files/etc/uci-defaults/99-custom.sh").read_text()
        script = source.split("configure_bandix_plus() {\n", 1)[1].split("\n}\n\nconfigure_bandix_plus", 1)[0]
        with tempfile.TemporaryDirectory() as tmp:
            config_file = Path(tmp) / "etc/config/bandix_plus"
            init_file = Path(tmp) / "etc/init.d/bandix-plus"
            if has_config:
                config_file.parent.mkdir(parents=True, exist_ok=True)
                config_file.write_text("config bandix_plus 'general'\n")
            if has_init:
                init_file.parent.mkdir(parents=True, exist_ok=True)
                init_file.write_text("#!/bin/sh\n")
                init_file.chmod(0o755)

            wrapper = f"""
            uci() {{ printf "uci %s\\n" "$*"; }}
            LOGFILE="/dev/null"
            wan_ifname="{wan_ifname}"
            # Redirect paths to tmp root
            alias_path() {{
                echo "$1" | sed "s|^/etc|{tmp}/etc|"
            }}
            # Override test checks
            test_override() {{
                sed -e 's|/etc/config/bandix_plus|{config_file}|g' \
                    -e 's|/etc/init.d/bandix-plus|{init_file}|g'
            }}
            """
            # Replace actual paths in script with tmp paths
            script_mod = (script
                          .replace("/etc/config/bandix_plus", str(config_file))
                          .replace("/etc/init.d/bandix-plus", str(init_file)))
            full_script = f"""
            uci() {{ printf "uci %s\\n" "$*"; }}
            LOGFILE="/dev/null"
            wan_ifname="{wan_ifname}"
            test_fn() {{
            {script_mod}
            }}
            test_fn
            """
            result = subprocess.run(["sh", "-e", "-c", full_script],
                                    capture_output=True, text=True, check=True)
            return result.stdout

    def test_e20c_and_r5c_configure_lan_and_wan_interfaces(self):
        for board_wan in ["eth1"]:
            stdout = self.run_configure_bandix_plus(wan_ifname=board_wan)
            self.assertIn("uci -q delete bandix_plus.general.iface", stdout)
            self.assertIn("uci add_list bandix_plus.general.iface=br-lan", stdout)
            self.assertIn("uci add_list bandix_plus.general.iface=eth1", stdout)
            self.assertIn("uci commit bandix_plus", stdout)

    def test_single_interface_configures_only_lan(self):
        stdout = self.run_configure_bandix_plus(wan_ifname="")
        self.assertIn("uci add_list bandix_plus.general.iface=br-lan", stdout)
        self.assertNotIn("uci add_list bandix_plus.general.iface=", stdout.replace("uci add_list bandix_plus.general.iface=br-lan", ""))

    def test_skips_when_not_installed(self):
        stdout = self.run_configure_bandix_plus(has_config=False, has_init=False)
        self.assertEqual(stdout.strip(), "")


if __name__ == "__main__":
    unittest.main()

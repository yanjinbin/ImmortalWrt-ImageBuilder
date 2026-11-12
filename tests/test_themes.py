from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
BUILD_SCRIPT = ROOT / "rockchip/build25.sh"
WORKFLOW = ROOT / ".github/workflows/build-rockchip-25.12.x.yml"

THEME_RELEASES = {
    "itsmaiGe/luci-theme-7dollar": "d742673ea1ee70448a30aa52a6c8bff513366a7f1b75945858620547df327c97",
    "wizcheu/luci-theme-aeris": "b1bfff20f9a847eca0233a67631363247136705afbc297d35cee82fc194df859",
    "anothaDev/luci-theme-vantage": "0cc00d0d7dce4fb816437833f1ab99ed2d71fa2a58fe119281dd3bfbf95689d1",
}


class BuiltinThemeTest(unittest.TestCase):
    def setUp(self):
        self.build = BUILD_SCRIPT.read_text(encoding="utf-8")
        self.workflow = WORKFLOW.read_text(encoding="utf-8")

    def test_workflow_has_version_inputs_for_each_theme(self):
        for name in ("theme_7dollar_version", "theme_aeris_version", "theme_vantage_version"):
            self.assertIn(name, self.workflow)
            self.assertIn("${{ inputs.%s }}" % name, self.workflow)

    def test_workflow_downloads_each_theme_apk_with_sha256(self):
        for repo, sha in THEME_RELEASES.items():
            self.assertIn("fetch_release %s" % repo, self.workflow)
            self.assertIn(sha, self.workflow)

    def test_pinned_hashes_do_not_break_the_latest_option(self):
        # SHA256 is only enforced for the known release tags, so `latest` keeps working.
        self.assertIn("theme_sha256()", self.workflow)
        self.assertIn("$(theme_sha256 7dollar", self.workflow)
        self.assertIn("$(theme_sha256 aeris", self.workflow)
        self.assertIn("$(theme_sha256 vantage", self.workflow)

    def test_workflow_downloads_vantage_chinese_language_pack(self):
        self.assertIn("luci-i18n-vantage-theme-zh-cn-.*\\.apk", self.workflow)
        self.assertIn(
            "3b7042c3fee7ffe79e07e726e44bd4e2f48b199918f35666263436049f947578",
            self.workflow,
        )

    def test_workflow_downloads_the_vantage_dashboard_app(self):
        # Same release as the theme: app + its own zh-cn catalogue.
        self.assertIn("'^luci-app-vantage-.*\\.apk$' apk theme-vantage-app.pkg", self.workflow)
        self.assertIn("luci-i18n-vantage-zh-cn-.*\\.apk", self.workflow)
        self.assertIn(
            "76b6353683bce164e7893e6bc6be8a1fd91f5a683e8c3148ecb37cf87273570b",
            self.workflow,
        )
        self.assertIn(
            "cb6de0ae0ca3e863056f8b3c80f841dbf1cd257d3098be7f5d1846228b301668",
            self.workflow,
        )

    def test_build_installs_the_vantage_dashboard_app(self):
        self.assertIn('PACKAGES="$PACKAGES luci-app-vantage luci-i18n-vantage-zh-cn"', self.build)

    def test_build_installs_themes(self):
        for package in ("luci-theme-7dollar", "luci-theme-aeris", "luci-theme-vantage"):
            self.assertIn('PACKAGES="$PACKAGES %s' % package, self.build)
        self.assertIn("luci-i18n-vantage-theme-zh-cn", self.build.split('PACKAGES="$PACKAGES luci-theme-vantage')[1].split("\n")[0])


class FootstrapWallpaperTest(unittest.TestCase):
    """The official feeds package ships no cats/dinos wallpapers, so the fork
    prebuilt must be pinned instead of letting ImageBuilder pick the feed one."""

    def setUp(self):
        self.build = BUILD_SCRIPT.read_text(encoding="utf-8")

    def test_fork_version_is_detected_from_the_downloaded_apk(self):
        self.assertIn("FOOTSTRAP_THEME_VERSION", self.build)
        self.assertIn("luci-theme-footstrap-*.apk", self.build)

    def test_fork_package_version_is_bumped_instead_of_pinned(self):
        # PACKAGES="pkg=version" breaks ImageBuilder (FormatPackages leaks the
        # constraint onto every following package), so the fork APK is repacked
        # with a higher release revision and installed by plain name.
        self.assertIn('PACKAGES="$PACKAGES luci-theme-footstrap"\n', self.build)
        self.assertNotIn("luci-theme-footstrap${FOOTSTRAP_THEME_VERSION", self.build)
        self.assertNotRegex(self.build, r'PACKAGES="\$PACKAGES luci-theme-footstrap[^"\n]*=')
        self.assertIn("shell/repin-footstrap.py", self.build)

    def test_bumped_version_is_read_back_from_the_repacked_apk(self):
        self.assertIn('FOOTSTRAP_THEME_VERSION="$(basename "$REPIN_APK" .apk)"', self.build)
        self.assertIn("luci-theme-footstrap-", self.build)

    def test_wallpaper_presets_are_verified_before_the_build(self):
        repin = (ROOT / "shell/repin-footstrap.py").read_text(encoding="utf-8")
        self.assertIn('"cats.svg", "dinos.svg"', repin)
        self.assertIn("www/luci-static/footstrap/wallpapers", repin)
        self.assertIn("refusing to ship a theme without cats/dinos", repin)

    def test_local_packages_repo_is_promoted_for_version_ties(self):
        # apk prefers the lowest-numbered repository when versions are equal, so the
        # local packages/ index must come first or the feed theme wins the tie.
        self.assertIn('LOCAL_PACKAGE_REPO="/home/build/immortalwrt/packages/packages.adb"', self.build)
        self.assertIn('"$LOCAL_PACKAGE_REPO"; cat /home/build/immortalwrt/repositories;', self.build)

    def test_built_image_manifest_is_checked(self):
        self.assertIn("luci-theme-footstrap - $FOOTSTRAP_THEME_VERSION", self.build)
        self.assertIn("*.manifest", self.build)

    def test_missing_fork_package_fails_the_build(self):
        # Silently falling back to the feed theme is what loses the wallpapers.
        self.assertIn("未找到 fork 的 luci-theme-footstrap APK", self.build)


class DefaultThemeTest(unittest.TestCase):
    """Vantage is the default theme; the uci-defaults script must fall back when a
    configured theme is missing instead of pointing mediaurlbase at nothing."""

    def setUp(self):
        self.build = BUILD_SCRIPT.read_text(encoding="utf-8")
        self.workflow = WORKFLOW.read_text(encoding="utf-8")
        self.script_source = (ROOT / "files/etc/uci-defaults/97-luci-theme.sh").read_text(encoding="utf-8")

    def test_workflow_defaults_to_vantage(self):
        self.assertIn("default_theme:", self.workflow)
        self.assertIn('default: "vantage"', self.workflow)
        self.assertIn('-e DEFAULT_THEME="${{ inputs.default_theme }}"', self.workflow)

    def test_build_writes_the_theme_choice(self):
        self.assertIn('DEFAULT_THEME="${DEFAULT_THEME:-vantage}"', self.build)
        self.assertIn("/files/etc/luci-default-theme", self.build)
        for theme in ("vantage", "7dollar", "aeris", "footstrap", "bootstrap"):
            self.assertIn(theme, self.build)

    def run_theme_script(self, default_theme=None, installed=("vantage",)):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in installed:
                (root / "www/luci-static" / name).mkdir(parents=True, exist_ok=True)
                header = root / "usr/share/ucode/luci/template/themes" / name / "header.ut"
                header.parent.mkdir(parents=True, exist_ok=True)
                header.write_text("")

            theme_file = root / "etc/luci-default-theme"
            theme_file.parent.mkdir(parents=True, exist_ok=True)
            if default_theme is not None:
                theme_file.write_text(default_theme + "\n")

            script = (self.script_source
                      .replace("/etc/luci-default-theme", str(theme_file))
                      .replace("/www/luci-static", str(root / "www/luci-static"))
                      .replace("/usr/share/ucode/luci/template/themes",
                               str(root / "usr/share/ucode/luci/template/themes")))
            runner = root / "run.sh"
            runner.write_text('uci() { case "$1" in -q) return 1 ;; esac; echo "uci $*"; }\n' + script)
            return subprocess.check_output(["sh", str(runner)], text=True, stderr=subprocess.STDOUT)

    def test_vantage_is_selected_by_default(self):
        out = self.run_theme_script()
        self.assertIn("uci set luci.main.mediaurlbase=/luci-static/vantage", out)
        self.assertIn("uci commit luci", out)

    def test_configured_theme_wins(self):
        out = self.run_theme_script(default_theme="aeris", installed=("aeris", "vantage"))
        self.assertIn("uci set luci.main.mediaurlbase=/luci-static/aeris", out)

    def test_missing_theme_falls_back_to_footstrap(self):
        out = self.run_theme_script(default_theme="7dollar", installed=("footstrap", "bootstrap"))
        self.assertIn("uci set luci.main.mediaurlbase=/luci-static/footstrap", out)
        self.assertNotIn("/luci-static/7dollar", out)

    def test_missing_everything_falls_back_to_bootstrap(self):
        out = self.run_theme_script(default_theme="7dollar", installed=("bootstrap",))
        self.assertIn("uci set luci.main.mediaurlbase=/luci-static/bootstrap", out)

    def test_no_theme_at_all_keeps_the_current_setting(self):
        out = self.run_theme_script(default_theme="7dollar", installed=())
        self.assertNotIn("uci set luci.main.mediaurlbase", out)
        self.assertIn("保持当前主题设置", out)


class FootstrapRepinTest(unittest.TestCase):
    def setUp(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "repin_footstrap", ROOT / "shell/repin-footstrap.py")
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)

    def test_release_revision_is_bumped(self):
        self.assertEqual(self.module.bump_version("26.315.53617~9ec99c3"),
                         "26.315.53617~9ec99c3-r2")
        self.assertEqual(self.module.bump_version("1.0.2-r9"), "1.0.2-r10")
        self.assertEqual(self.module.bump_version("1.0"), "1.0-r2")

    def test_info_is_copied_without_stale_metadata(self):
        info = {
            "name": "luci-theme-footstrap",
            "version": "26.315.53617~9ec99c3",
            "hashes": "abc",
            "installed-size": 468885,
            "depends": ["libc", "luci-base"],
            "provides": ["luci-theme-footstrap-any"],
            "license": "Apache-2.0",
        }
        args = self.module.info_arguments(info, "26.315.53617~9ec99c3-r2")
        joined = " ".join(args)
        self.assertIn("version:26.315.53617~9ec99c3-r2", joined)
        self.assertIn("depends:libc luci-base", joined)
        self.assertIn("provides:luci-theme-footstrap-any", joined)
        self.assertNotIn("hashes:", joined)
        self.assertNotIn("installed-size:", joined)


class FootstrapRepinCliTest(unittest.TestCase):
    """The shell wrapper reads the last stdout line as the produced APK path."""

    def test_child_noise_does_not_pollute_the_output_path(self):
        import json
        import os

        script = ROOT / "shell/repin-footstrap.py"
        meta = {
            "info": {
                "name": "luci-theme-footstrap",
                "version": "26.315.53617~9ec99c3",
                "arch": "noarch",
                "depends": ["libc", "luci-base"],
            },
            "scripts": {"post-install": "#!/bin/sh\nexit 0\n"},
        }
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / "meta.json").write_text(json.dumps(meta))
            fake = tmp / "apk"
            fake.write_text(
                "#!/bin/sh\n"
                'cmd="$1"; shift\n'
                'case "$cmd" in\n'
                '  adbdump) cat "$FAKE_META" ;;\n'
                "  extract)\n"
                '    dest=""\n'
                '    while [ $# -gt 0 ]; do case "$1" in --destination) dest="$2"; shift 2;; *) shift;; esac; done\n'
                '    mkdir -p "$dest/www/luci-static/footstrap/wallpapers"\n'
                '    : > "$dest/www/luci-static/footstrap/wallpapers/cats.svg"\n'
                '    : > "$dest/www/luci-static/footstrap/wallpapers/dinos.svg"\n'
                "    echo 'extracting...' ;;\n"
                "  mkpkg)\n"
                '    out=""\n'
                '    while [ $# -gt 0 ]; do case "$1" in --output) out="$2"; shift 2;; *) shift;; esac; done\n'
                '    echo "mkpkg progress noise"\n'
                '    echo pkg > "$out" ;;\n'
                "esac\n"
            )
            fake.chmod(0o755)
            (tmp / "src.apk").write_bytes(b"x")
            env = dict(os.environ, FAKE_META=str(tmp / "meta.json"))
            result = subprocess.run(
                ["python3", str(script), str(fake), str(tmp / "src.apk"), str(tmp / "out")],
                check=True, capture_output=True, text=True, env=env)
            lines = result.stdout.strip().splitlines()
            self.assertEqual(len(lines), 1, result.stdout)
            produced = Path(lines[0])
            self.assertTrue(produced.is_file())
            self.assertTrue(produced.name.endswith("-r2.apk"))


if __name__ == "__main__":
    unittest.main()

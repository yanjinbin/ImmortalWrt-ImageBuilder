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

    def test_package_is_pinned_to_the_fork_version(self):
        self.assertIn(
            'PACKAGES="$PACKAGES luci-theme-footstrap${FOOTSTRAP_THEME_VERSION:+=$FOOTSTRAP_THEME_VERSION}"',
            self.build,
        )
        self.assertNotIn('PACKAGES="$PACKAGES luci-theme-footstrap"\n', self.build)

    def test_wallpaper_presets_are_verified_before_the_build(self):
        self.assertIn("www/luci-static/footstrap/wallpapers/cats.svg", self.build)
        self.assertIn("www/luci-static/footstrap/wallpapers/dinos.svg", self.build)
        self.assertIn("extract --allow-untrusted", self.build)

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


if __name__ == "__main__":
    unittest.main()

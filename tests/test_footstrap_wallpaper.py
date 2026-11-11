from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
BUILD_SCRIPT = ROOT / "rockchip/build25.sh"


class FootstrapWallpaperTest(unittest.TestCase):
    def setUp(self):
        self.source = BUILD_SCRIPT.read_text(encoding="utf-8")

    def test_fork_footstrap_version_is_detected(self):
        self.assertIn("FOOTSTRAP_PKG_VERSION", self.source)
        self.assertIn("luci-theme-footstrap-*.apk", self.source)
        self.assertIn("luci-theme-footstrap${FOOTSTRAP_PKG_VERSION:+=$FOOTSTRAP_PKG_VERSION}", self.source)

    def test_theme_is_pinned_instead_of_latest_feed_package(self):
        # The official feeds package is newer than the fork prebuilt, so an unpinned
        # PACKAGES entry silently installs the feed theme without cats/dinos wallpapers.
        self.assertIn('PACKAGES="$PACKAGES luci-theme-footstrap${FOOTSTRAP_PKG_VERSION:+=$FOOTSTRAP_PKG_VERSION}"', self.source)
        self.assertNotIn('PACKAGES="$PACKAGES luci-theme-footstrap"\n', self.source)


if __name__ == "__main__":
    unittest.main()

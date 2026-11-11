from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

PORTS_VIEW = ROOT / "files/www/luci-static/resources/view/status/include/29_ports.js"


class PortsStatusTest(unittest.TestCase):
    def setUp(self):
        self.source = PORTS_VIEW.read_text(encoding="utf-8")

    def test_ports_view_override_exists(self):
        self.assertTrue(PORTS_VIEW.exists())

    def test_stock_port_tiles_are_kept(self):
        self.assertIn("formatSpeed(carrier, speed, duplex)", self.source)
        self.assertIn("port.netdev.getName()", self.source)
        self.assertIn("renderNetworksTooltip(pmap)", self.source)

    def test_live_traffic_tile_is_added(self):
        self.assertIn("renderRateTile", self.source)
        self.assertIn("sampleWanRates", self.source)
        self.assertIn("getRXBytes()", self.source)
        self.assertIn("getTXBytes()", self.source)
        self.assertIn("实时速率", self.source)

    def test_zashboard_hyperlink_tile_is_added(self):
        self.assertIn("renderZashboardTile", self.source)
        self.assertIn(":9090/ui/", self.source)
        self.assertIn("?host=", self.source)
        self.assertIn("&hostname=", self.source)
        self.assertIn("&port=9090", self.source)
        self.assertIn("&secret=", self.source)
        self.assertIn("'666666'", self.source)
        self.assertIn("#/proxies", self.source)
        self.assertIn("Nikki", self.source)
        self.assertIn("Zashboard", self.source)

    def test_new_tiles_reuse_port_card_style(self):
        self.assertIn("portTiles.push(renderRateTile(", self.source)
        self.assertIn("portTiles.push(renderZashboardTile())", self.source)
        # The stock port tiles plus the two new tiles share .ifacebox markup/size.
        self.assertEqual(self.source.count("'class': 'ifacebox'"), 3)
        self.assertEqual(self.source.count("margin:.25em;width:100px"), 3)


if __name__ == "__main__":
    unittest.main()

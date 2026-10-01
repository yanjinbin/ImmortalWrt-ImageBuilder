import importlib.util
from pathlib import Path
import os
import subprocess
import tempfile
import unittest


spec = importlib.util.spec_from_file_location(
    "repair", Path(__file__).parents[1] / "shell/repair-uugamebooster.py")
repair = importlib.util.module_from_spec(spec)
spec.loader.exec_module(repair)


class InstallHookTest(unittest.TestCase):
    def test_offline_install_uses_target_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            init = Path(tmp, "etc/init.d/uuplugin")
            init.parent.mkdir(parents=True)
            init.touch(mode=0o644)
            script = repair.repair_hook("#!/bin/sh\nchmod +x /etc/init.d/uuplugin\n")
            subprocess.run(["sh"], input=script, text=True, check=True,
                           env={**os.environ, "IPKG_INSTROOT": tmp})
            self.assertTrue(os.access(init, os.X_OK))

    def test_unknown_hook_is_rejected(self):
        with self.assertRaises(ValueError):
            repair.repair_hook("#!/bin/sh\nexit 0\n")


if __name__ == "__main__":
    unittest.main()

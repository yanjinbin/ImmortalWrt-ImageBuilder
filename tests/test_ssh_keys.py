from pathlib import Path
import os
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
BUILD_SCRIPT = ROOT / "rockchip/build25.sh"
WORKFLOW = ROOT / ".github/workflows/build-rockchip-25.12.x.yml"
SSH_DEFAULTS = ROOT / "files/etc/uci-defaults/98-sshkeys.sh"

ED25519 = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIExampleKeyForTests yanjinbin@mac"
RSA = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQC7Example yanjinbin@legacy"


class SshKeysPresetTest(unittest.TestCase):
    """Public keys come from a repository secret, never from the repo."""

    def setUp(self):
        self.build = BUILD_SCRIPT.read_text(encoding="utf-8")
        self.workflow = WORKFLOW.read_text(encoding="utf-8")
        self.defaults = SSH_DEFAULTS.read_text(encoding="utf-8")

    def test_workflow_reads_the_secret_and_never_echoes_it(self):
        self.assertIn("SSH_PUBKEY: ${{ secrets.SSH_PUBKEY }}", self.workflow)
        self.assertIn("custom/ssh_authorized_keys", self.workflow)
        # 只允许打印条数, 不允许把公钥内容回显到日志
        self.assertIn("仅统计数量, 不打印公钥内容", self.workflow)

    def test_build_installs_keys_for_root_via_dropbear(self):
        for fragment in (
            'SSH_KEYS_SRC="/home/build/immortalwrt/files/etc/config/ssh_authorized_keys"',
            'SSH_DROPBEAR_DIR="/home/build/immortalwrt/files/etc/dropbear"',
            'cp -f "$SSH_KEYS_BAKED" "$SSH_DROPBEAR_DIR/authorized_keys"',
            'chmod 700 "$SSH_DROPBEAR_DIR"',
            'chmod 600 "$SSH_KEYS_BAKED" "$SSH_DROPBEAR_DIR/authorized_keys"',
            'rm -f "$SSH_KEYS_SRC"',
        ):
            self.assertIn(fragment, self.build)

    def test_build_rejects_unknown_key_types(self):
        for prefix in (
            "ssh-rsa",
            "ssh-ed25519",
            "ecdsa-sha2-",
            "sk-ssh-ed25519@openssh.com",
        ):
            self.assertIn(prefix, self.build)
        self.assertIn("SSH 公钥格式无法识别", self.build)
        # 校验失败必须中止构建, 不能把坏公钥写进固件
        self.assertIn("exit 1", self.build)

    def test_uci_defaults_merges_baked_keys_without_duplicates(self):
        self.assertIn('BAKED_FILE="/etc/dropbear/authorized_keys.baked"', self.defaults)
        self.assertIn('grep -qxF "$key" "$KEY_FILE"', self.defaults)
        self.assertIn('chmod 700 "$DROPBEAR_DIR"', self.defaults)
        self.assertIn('chmod 600 "$KEY_FILE"', self.defaults)


class SshKeysBehaviourTest(unittest.TestCase):
    def run_script(self, baked=None, existing=None, runs=1):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        root = Path(self._tmp.name)
        dropbear = root / "dropbear"
        dropbear.mkdir(parents=True)
        key_file = dropbear / "authorized_keys"
        baked_file = dropbear / "authorized_keys.baked"
        init = root / "init.d/dropbear"
        init.parent.mkdir(parents=True)
        init.write_text("#!/bin/sh\necho ENABLED\n")
        init.chmod(0o755)
        if existing is not None:
            key_file.write_text(existing)
            key_file.chmod(0o644)
        if baked is not None:
            baked_file.write_text(baked)

        script = (
            SSH_DEFAULTS.read_text(encoding="utf-8")
            .replace("/etc/config/uci-defaults-log.txt", str(root / "log.txt"))
            .replace("/etc/init.d/dropbear", str(init))
            .replace("/etc/dropbear", str(dropbear))
        )
        runner = root / "run.sh"
        runner.write_text(script)
        for _ in range(runs):
            subprocess.check_output(
                ["sh", str(runner)], text=True, stderr=subprocess.STDOUT
            )
        return key_file

    def test_baked_key_is_merged_and_permissions_are_fixed(self):
        key_file = self.run_script(baked=ED25519 + "\n")
        self.assertEqual(key_file.read_text(), ED25519 + "\n")
        self.assertEqual(os.stat(key_file).st_mode & 0o777, 0o600)

    def test_existing_keys_survive_keep_config_flash(self):
        key_file = self.run_script(baked=ED25519 + "\n", existing=RSA + "\n")
        self.assertEqual(key_file.read_text(), RSA + "\n" + ED25519 + "\n")

    def test_second_run_does_not_duplicate(self):
        key_file = self.run_script(baked=ED25519 + "\n", runs=2)
        self.assertEqual(key_file.read_text().count(ED25519), 1)

    def test_crlf_and_comments_are_ignored(self):
        key_file = self.run_script(baked="# my keys\r\n\r\n" + ED25519 + "\r\n")
        self.assertEqual(key_file.read_text(), ED25519 + "\n")

    def test_no_baked_file_leaves_the_device_untouched(self):
        key_file = self.run_script(baked=None)
        self.assertFalse(key_file.exists())


if __name__ == "__main__":
    unittest.main()

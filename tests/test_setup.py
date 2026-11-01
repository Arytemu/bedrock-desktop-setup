import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("setup", Path(__file__).resolve().parents[1] / "desktop_setup.py")
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)


class DesktopSetupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "home with spaces"
        self.root.mkdir()
        self.env = patch.dict(os.environ, {
            "HOME": str(self.root),
            "XDG_DATA_HOME": str(self.root / "data"),
            "XDG_STATE_HOME": str(self.root / "state"),
        })
        self.env.start()
        self.app = self.root / "BedrockOnLinux test.AppImage"
        self.app.write_text(
            "#!/bin/sh\n"
            "printf '%s|%s|%s|%s\\n' \"$1\" \"${LD_PRELOAD-unset}\" "
            "\"${LD_LIBRARY_PATH-unset}\" \"$DISPLAY\"\n"
        )
        self.app.chmod(0o755)

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def test_install_reinstall_launch_uninstall(self):
        setup.install(self.app)
        setup.install(self.app)
        paths = setup.locations()
        for kind, mode in (("game", "play"), ("launcher", "gui")):
            env = dict(os.environ, LD_PRELOAD="", LD_LIBRARY_PATH="/test/lib", DISPLAY=":99")
            run = subprocess.run([str(paths[kind + "_script"])], env=env, capture_output=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertEqual((paths["logs"] / (kind + ".log")).read_text().strip(), mode + "|unset|unset|:99")
            self.assertIn("Terminal=false", paths[kind + "_entry"].read_text())
        setup.uninstall()
        setup.uninstall()
        self.assertTrue(self.app.exists())
        self.assertTrue(paths["logs"].exists())
        self.assertFalse(paths["game_entry"].exists())

    def test_unmanaged_file_is_not_overwritten(self):
        p = setup.locations()["game_entry"]
        p.parent.mkdir(parents=True)
        p.write_text("keep me")
        with self.assertRaises(ValueError):
            setup.install(self.app)
        self.assertEqual(p.read_text(), "keep me")

    def test_modified_file_blocks_uninstall(self):
        setup.install(self.app)
        p = setup.locations()["game_script"]
        p.write_text(p.read_text() + "# user change\n")
        with self.assertRaises(ValueError):
            setup.uninstall()
        self.assertTrue(setup.locations()["game_entry"].exists())

    def test_symlink_is_not_overwritten(self):
        p = setup.locations()["icon"]
        p.parent.mkdir(parents=True)
        p.symlink_to(self.app)
        with self.assertRaises(ValueError):
            setup.install(self.app)
        self.assertTrue(p.is_symlink())

    def test_changing_appimage_path(self):
        setup.install(self.app)
        new = self.root / "new.AppImage"
        new.write_bytes(self.app.read_bytes())
        new.chmod(0o755)
        setup.install(new)
        record = json.loads(setup.locations()["manifest"].read_text())
        self.assertEqual(record["appimage"], str(new))

    def test_relative_xdg_is_rejected(self):
        with patch.dict(os.environ, {"XDG_DATA_HOME": "relative"}):
            with self.assertRaises(ValueError):
                setup.locations()

    def test_write_failure_rolls_back(self):
        original_atomic = setup.atomic
        calls = 0
        def fail_once(path, data, mode=0o644):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("simulated disk error")
            return original_atomic(path, data, mode)
        with patch.object(setup, "atomic", side_effect=fail_once):
            with self.assertRaises(OSError):
                setup.install(self.app)
        paths = setup.locations()
        self.assertFalse(paths["game_script"].exists())
        self.assertFalse(paths["manifest"].exists())


if __name__ == "__main__":
    unittest.main()

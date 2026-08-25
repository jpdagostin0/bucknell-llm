from __future__ import annotations

import unittest
from pathlib import Path
from unittest import mock

import install_env


class InstallEnvTests(unittest.TestCase):
    def test_uv_venv_command_uses_python_312(self) -> None:
        environment = Path("tools/gmail/.venv")
        with mock.patch.object(install_env.shutil, "which", return_value="uv.exe"):
            command = install_env.uv_venv_command(environment)
        self.assertEqual(command[0], "uv.exe")
        self.assertEqual(command[1], "venv")
        self.assertEqual(command[2], str(environment))
        self.assertEqual(command[3:], ["--python", "3.12"])

    def test_uv_pip_command_includes_packages(self) -> None:
        python_exe = Path("tools/gmail/.venv/Scripts/python.exe")
        with mock.patch.object(install_env.shutil, "which", return_value="uv.exe"):
            command = install_env.uv_pip_command(python_exe, ["PyYAML==6.0.2"])
        self.assertEqual(
            command,
            [
                "uv.exe",
                "pip",
                "install",
                "--python",
                str(python_exe),
                "PyYAML==6.0.2",
            ],
        )

    def test_require_uv_explains_missing_binary(self) -> None:
        with mock.patch.object(install_env.shutil, "which", return_value=None):
            with self.assertRaises(install_env.InstallError) as raised:
                install_env.require_uv()
        self.assertIn("uv is required", raised.exception.message)

    def test_find_node_without_record_asks_to_install_node(self) -> None:
        with mock.patch.object(install_env.shutil, "which", return_value=None):
            with mock.patch.object(install_env.Path, "is_file", return_value=False):
                with self.assertRaises(install_env.InstallError) as raised:
                    install_env.find_node(use_record=False)
        self.assertIn("Install Node", raised.exception.message)


if __name__ == "__main__":
    unittest.main()

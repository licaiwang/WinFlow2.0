"""Tests for winflow.generator CLI."""

import json
import tempfile
import unittest
from pathlib import Path
import io
from contextlib import redirect_stdout

from winflow.generator.cli import run


SETTING = "\n".join(
    [
        'set MACHINE_QUEUE = "normal"',
        'set MACHINE_CPU = "1"',
    ]
)


class TestCLI(unittest.TestCase):
    def test_list_flows(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = run(["--list"])
        self.assertEqual(code, 0)
        output = buf.getvalue()
        self.assertIn("example", output)

    def test_generate_example_flow(self):
        with tempfile.TemporaryDirectory() as tmp:
            setting = Path(tmp) / "setting.sh"
            output = Path(tmp) / "flow.json"
            setting.write_text(SETTING, encoding="utf-8")

            code = run(
                [
                    "--flow",
                    "example",
                    "--setting",
                    str(setting),
                    "-o",
                    str(output),
                ]
            )

            self.assertEqual(code, 0)
            self.assertTrue(output.exists())
            flow = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(flow["flow_name"], "example")
            self.assertEqual(
                [s["name"] for s in flow["stages"]],
                ["FLOOR_PLAN", "PLACE", "CTS", "ROUTE"],
            )

    def test_missing_setting_returns_error(self):
        code = run(["--flow", "example", "--setting", "missing-setting.sh"])
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()

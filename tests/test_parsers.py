"""Tests for input parsers."""

import tempfile
import unittest
from pathlib import Path

from winflow.generator.parsers.block_stream import parse_block_stream
from winflow.generator.parsers.parse_yml import parse_yml
from winflow.generator.parsers.setting_sh import parse_setting_sh


class TestParseSettingSh(unittest.TestCase):
    def test_parses_set_lines_and_ignores_comments(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "setting.sh"
            path.write_text(
                '\n'.join(
                    [
                        '# comment',
                        'set TOP_MODULE = "sm8466_top"',
                        'set FLAG_DMF = "1"',
                        '',
                    ]
                ),
                encoding="utf-8",
            )
            cfg = parse_setting_sh(path)
            self.assertEqual(cfg["TOP_MODULE"], "sm8466_top")
            self.assertEqual(cfg["FLAG_DMF"], "1")

    def test_empty_file_returns_empty_dict(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "setting.sh"
            path.write_text("", encoding="utf-8")
            self.assertEqual(parse_setting_sh(path), {})


class TestParseBlockStream(unittest.TestCase):
    def test_parses_blocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "block_stream.list"
            path.write_text(
                '\n'.join(
                    [
                        "# header",
                        "block_a /work/a",
                        "block_b /work/b",
                    ]
                ),
                encoding="utf-8",
            )
            blocks = parse_block_stream(path)
            self.assertEqual(
                blocks,
                [
                    {"name": "block_a", "workdir": "/work/a"},
                    {"name": "block_b", "workdir": "/work/b"},
                ],
            )

    def test_missing_file_returns_empty_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "missing.list"
            self.assertEqual(parse_block_stream(path), [])


class TestParseYml(unittest.TestCase):
    def test_parses_ithome_style_config(self):
        content = "\n".join(
            [
                'FLOW_NAME:"ithome"',
                "CPU:",
                "  - IT_1:4",
                "\t- IT_2:4",
                "\t- IT_3:4",
                "\t- IT_4:8",
                "\t- IT_5:16",
                "IT_2_LIST:[subblock_A,subblock_B,subblock_C]",
                "USE_IT_5:true",
                "",
            ]
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ithome.yml"
            path.write_text(content, encoding="utf-8")
            cfg = parse_yml(path)

        self.assertEqual(cfg["FLOW_NAME"], "ithome")
        self.assertEqual(
            cfg["CPU"],
            {"IT_1": 4, "IT_2": 4, "IT_3": 4, "IT_4": 8, "IT_5": 16},
        )
        self.assertEqual(
            cfg["IT_2_LIST"],
            ["subblock_A", "subblock_B", "subblock_C"],
        )
        self.assertIs(cfg["USE_IT_5"], True)

    def test_missing_file_returns_empty_dict(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "missing.yml"
            self.assertEqual(parse_yml(path), {})


if __name__ == "__main__":
    unittest.main()

"""Tests for centralized WinFlow configuration."""

import json
import os
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path

from winflow.config import get_config, get_section, load_config, reset_config
from winflow.config.loader import merge_dataclass
from winflow.config.models import AppConfig, RunnerConfig


@dataclass(frozen=True)
class _ProbeFlowConfig:
    flow_name: str = "probe"
    default_queue: str = "normal"


class TestWinflowConfig(unittest.TestCase):
    def setUp(self):
        reset_config()

    def tearDown(self):
        reset_config()

    def test_defaults_match_config_json(self):
        config_path = Path(__file__).resolve().parent.parent / "config.json"
        loaded = load_config(config_path)
        self.assertEqual(loaded.runner.default_queue, "normal")
        self.assertEqual(loaded.runner.poll_interval, 20)
        self.assertEqual(loaded.generator.default_cpu, 1)
        self.assertEqual(loaded.example.flow_name, "example")
        self.assertEqual(loaded.example.main_stages[0], "FLOOR_PLAN")

    def test_merge_dataclass_overrides_nested_values(self):
        base = AppConfig()
        updated = merge_dataclass(base, {"runner": {"default_queue": "custom_q"}})
        self.assertEqual(updated.runner.default_queue, "custom_q")
        self.assertEqual(updated.runner.poll_interval, base.runner.poll_interval)

    def test_env_override(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.json"
            config_path.write_text(
                json.dumps({"runner": {"default_queue": "from_file"}}),
                encoding="utf-8",
            )
            os.environ["WINFLOW_CONFIG"] = str(config_path)
            os.environ["WINFLOW_RUNNER_DEFAULT_QUEUE"] = "from_env"
            try:
                reset_config()
                config = get_config(reload=True)
                self.assertEqual(config.runner.default_queue, "from_env")
            finally:
                os.environ.pop("WINFLOW_CONFIG", None)
                os.environ.pop("WINFLOW_RUNNER_DEFAULT_QUEUE", None)
                reset_config()

    def test_get_config_is_cached(self):
        first = get_config()
        second = get_config()
        self.assertIs(first, second)
        third = get_config(reload=True)
        self.assertIsNot(first, third)

    def test_get_section_missing_returns_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.json"
            config_path.write_text("{}", encoding="utf-8")
            os.environ["WINFLOW_CONFIG"] = str(config_path)
            try:
                reset_config()
                get_config(reload=True)
                section = get_section("ithome", _ProbeFlowConfig())
                self.assertEqual(section.flow_name, "probe")
                self.assertEqual(section.default_queue, "normal")
            finally:
                os.environ.pop("WINFLOW_CONFIG", None)
                reset_config()

    def test_get_section_merges_extra_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.json"
            config_path.write_text(
                json.dumps({"ithome": {"flow_name": "from_json", "default_queue": "fast"}}),
                encoding="utf-8",
            )
            os.environ["WINFLOW_CONFIG"] = str(config_path)
            try:
                reset_config()
                get_config(reload=True)
                section = get_section("ithome", _ProbeFlowConfig())
                self.assertEqual(section.flow_name, "from_json")
                self.assertEqual(section.default_queue, "fast")
            finally:
                os.environ.pop("WINFLOW_CONFIG", None)
                reset_config()

    def test_get_section_prefers_typed_appconfig_field(self):
        section = get_section("example", _ProbeFlowConfig(flow_name="ignored"))
        self.assertEqual(section.flow_name, "example")
        self.assertEqual(section.main_stages[0], "FLOOR_PLAN")


if __name__ == "__main__":
    unittest.main()

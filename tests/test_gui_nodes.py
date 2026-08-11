"""Tests for predefined job-node library."""

import json
import tempfile
import unittest
from pathlib import Path

from winflow.generator.editor.nodes import (
    builtin_node_jobs,
    extract_flow_name,
    extract_job_from_flow,
    generate_builtin_nodes,
    list_node_names,
    list_nodes_by_flow,
    load_node,
    load_node_flow,
    node_dir,
)


class TestJobNodes(unittest.TestCase):
    def test_builtin_catalog_covers_example(self):
        stems = {stem for stem, _flow, _job in builtin_node_jobs()}
        for required in (
            "blank_job",
            "FLOOR_PLAN",
            "Q_FLOOR_PLAN",
            "PLACE",
            "Q_PLACE",
            "CTS",
            "Q_CTS",
            "ROUTE",
            "Q_ROUTE",
        ):
            self.assertIn(required, stems)

    def test_builtin_flow_categories(self):
        by_flow = {}
        for stem, flow, _job in builtin_node_jobs():
            by_flow.setdefault(flow, []).append(stem)
        self.assertIn("blank_job", by_flow["custom_flow"])
        self.assertIn("FLOOR_PLAN", by_flow["example"])
        self.assertIn("Q_ROUTE", by_flow["example"])

    def test_repo_node_dir_populated(self):
        names = list_node_names()
        self.assertGreaterEqual(len(names), 9)
        self.assertIn("FLOOR_PLAN", names)
        job = load_node("FLOOR_PLAN")
        self.assertEqual(job["name"], "FLOOR_PLAN")
        self.assertTrue(job["command"])
        self.assertEqual(extract_flow_name(load_node_flow("FLOOR_PLAN")), "example")
        self.assertEqual(extract_flow_name(load_node_flow("blank_job")), "custom_flow")

    def test_list_nodes_by_flow_order(self):
        grouped = list_nodes_by_flow()
        names = [flow for flow, _jobs in grouped]
        self.assertEqual(names[:2], ["example", "custom_flow"])
        example_jobs = dict(grouped)["example"]
        self.assertTrue(any(stem == "FLOOR_PLAN" for stem, _display in example_jobs))

    def test_round_trip_write_load(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            generate_builtin_nodes(root)
            names = list_node_names(root)
            self.assertIn("FLOOR_PLAN", names)
            job = load_node("FLOOR_PLAN", root)
            self.assertEqual(job["name"], "FLOOR_PLAN")
            self.assertTrue(job["outputs"])

            path = root / "PLACE.json"
            with path.open(encoding="utf-8") as fp:
                data = json.load(fp)
            self.assertEqual(data["flow_name"], "example")
            extracted = extract_job_from_flow(data)
            self.assertEqual(extracted["name"], "PLACE")

            grouped = list_nodes_by_flow(root)
            self.assertEqual([f for f, _ in grouped][:2], ["example", "custom_flow"])

    def test_node_dir_default(self):
        self.assertTrue(str(node_dir()).endswith("node") or node_dir().name == "node")


if __name__ == "__main__":
    unittest.main()

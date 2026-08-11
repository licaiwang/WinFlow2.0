"""Tests for winflow.generator GUI document helpers."""

import json
import tempfile
import unittest
from pathlib import Path

from winflow.generator.core.models import make_flow, make_job, make_stage, make_task
from winflow.generator.core.io import write_flow
from winflow.generator.editor.document import (
    FlowDocument,
    TemplateOptions,
    _job_key,
    apply_template,
    blank_template,
    document_to_flow,
    example_template,
    flow_to_document,
)


class TestFlowDocument(unittest.TestCase):
    def test_blank_template_has_one_job(self):
        doc = blank_template()
        jobs = list(doc.iter_jobs())
        self.assertEqual(len(jobs), 1)
        self.assertEqual(doc.flow_name, "custom_flow")

    def test_round_trip_flow(self):
        flow = make_flow(
            "demo",
            [
                make_stage(
                    "s1",
                    [
                        make_task(
                            "t1",
                            [
                                make_job("j1", "echo hi", ["a.txt"], ["b.txt"], "q1", 2),
                            ],
                        )
                    ],
                )
            ],
            poll_interval=15,
        )
        doc = flow_to_document(flow)
        self.assertEqual(doc.flow_name, "demo")
        self.assertEqual(doc.poll_interval, 15)
        self.assertIn(len(doc.positions), (1,))

        rebuilt = document_to_flow(doc)
        self.assertEqual(rebuilt, flow)

    def test_blank_template_default_resources(self):
        doc = blank_template()
        job = next(doc.iter_jobs())[2]
        self.assertEqual(job["queue"], "normal")
        self.assertEqual(job["cpu"], 1)
        self.assertNotIn("machine", job)

    def test_example_template_without_references(self):
        doc = example_template()
        stage_names = [stage["name"] for stage in doc.stages]
        self.assertEqual(stage_names, ["FLOOR_PLAN", "PLACE", "CTS", "ROUTE"])
        for _s, _t, job in doc.iter_jobs():
            self.assertEqual(job.get("queue"), "normal")
            self.assertEqual(job.get("cpu"), 1)

    def test_example_template_applies_custom_resources(self):
        opts = TemplateOptions(queue="myqueue", machine="host1 host2", cpu=8)
        doc = example_template(opts)
        for _s, _t, job in doc.iter_jobs():
            self.assertEqual(job.get("queue"), "myqueue")
            self.assertEqual(job.get("cpu"), 8)
            self.assertEqual(job.get("machine"), "host1 host2")

    def test_example_template_with_setting_file(self):
        content = "\n".join(
            [
                'set MACHINE_QUEUE = "old_queue"',
                'set MACHINE_CPU = "2"',
            ]
        )
        with tempfile.TemporaryDirectory() as tmp:
            setting = Path(tmp) / "setting.sh"
            setting.write_text(content, encoding="utf-8")
            doc = example_template(TemplateOptions(setting_path=setting, queue="normal", cpu=1))
        queues = {job.get("queue") for _s, _t, job in doc.iter_jobs()}
        self.assertEqual(queues, {"normal"})

    def test_apply_template_unknown_raises(self):
        with self.assertRaises(KeyError):
            apply_template("unknown")

    def test_list_templates_includes_registered_flows(self):
        from winflow.generator.editor.document import list_templates

        names = list_templates()
        self.assertEqual(names[0], "blank")
        self.assertIn("example", names)
        self.assertIn("ithome", names)

    def test_apply_template_ithome(self):
        doc = apply_template("ithome")
        self.assertEqual(doc.flow_name, "ithome")
        stage_names = [stage["name"] for stage in doc.stages]
        # example_flow/ithome.yml currently has USE_IT_5:false
        self.assertEqual(
            stage_names,
            ["IT_1", "IT_2_0", "IT_2_1", "IT_2_2", "IT_3", "IT_4"],
        )
        by_name = {job["name"]: job for _s, _t, job in doc.iter_jobs()}
        # Per-job CPU from yml must survive template load (not dialog overwrite).
        self.assertEqual(by_name["IT_1"].get("cpu"), 4)
        self.assertEqual(by_name["IT_4"].get("cpu"), 8)
        self.assertEqual(by_name["IT_3"].get("parents"), ["IT_1/IT_1/IT_1"])
        self.assertEqual(by_name["IT_4"].get("parents"), ["IT_3/IT_3/IT_3"])

    def test_document_export_is_valid_json(self):
        doc = apply_template("blank")
        flow = document_to_flow(doc)
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "flow.json"
            out.write_text(json.dumps(flow, indent=2), encoding="utf-8")
            loaded = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(loaded["flow_name"], flow["flow_name"])
        self.assertIn("stages", loaded)

    def test_export_orders_stages_left_to_right(self):
        """Canvas X order wins over list append order (renames / new stages)."""
        doc = FlowDocument(
            flow_name="demo",
            poll_interval=10,
            stages=[
                make_stage("A", [make_task("t", [make_job("a", "c", [], [], "q", 1)])]),
                make_stage("B", [make_task("t", [make_job("b", "c", [], [], "q", 1)])]),
                make_stage("C", [make_task("t", [make_job("c", "c", [], [], "q", 1)])]),
            ],
        )
        doc.positions[_job_key("A", "t", "a")] = (200.0, 50.0)
        doc.positions[_job_key("B", "t", "b")] = (400.0, 50.0)
        doc.positions[_job_key("C", "t", "c")] = (50.0, 50.0)

        flow = document_to_flow(doc)
        self.assertEqual([s["name"] for s in flow["stages"]], ["C", "A", "B"])

    def test_export_orders_jobs_top_to_bottom(self):
        doc = FlowDocument(
            flow_name="demo",
            poll_interval=10,
            stages=[
                make_stage(
                    "S",
                    [
                        make_task(
                            "t",
                            [
                                make_job("lower", "c", [], [], "q", 1),
                                make_job("upper", "c", [], [], "q", 1),
                            ],
                        )
                    ],
                )
            ],
        )
        doc.positions[_job_key("S", "t", "lower")] = (50.0, 200.0)
        doc.positions[_job_key("S", "t", "upper")] = (50.0, 40.0)

        flow = document_to_flow(doc)
        names = [j["name"] for j in flow["stages"][0]["tasks"][0]["jobs"]]
        self.assertEqual(names, ["upper", "lower"])

    def test_sync_write_roundtrip_preserves_canvas_stage_order(self):
        """Mirrors Runner Sync: document_to_flow -> write_flow -> re-read."""
        doc = FlowDocument(
            flow_name="demo",
            poll_interval=10,
            stages=[
                make_stage("later", [make_task("t", [make_job("x", "c", [], [], "q", 1)])]),
                make_stage("earlier", [make_task("t", [make_job("y", "c", [], [], "q", 1)])]),
            ],
        )
        doc.positions[_job_key("later", "t", "x")] = (300.0, 50.0)
        doc.positions[_job_key("earlier", "t", "y")] = (80.0, 50.0)

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "flow.json"
            write_flow(document_to_flow(doc), out)
            loaded = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual([s["name"] for s in loaded["stages"]], ["earlier", "later"])

    def test_export_renames_duplicate_stage_names(self):
        """a -> b -> a -> d becomes a -> b -> a_2 -> d so job keys stay unique."""
        doc = FlowDocument(
            flow_name="demo",
            poll_interval=10,
            stages=[
                make_stage("a", [make_task("t", [make_job("j1", "c", [], [], "q", 1)])]),
                make_stage("b", [make_task("t", [make_job("j2", "c", [], [], "q", 1)])]),
                make_stage("a", [make_task("t", [make_job("j3", "c", [], [], "q", 1)])]),
                make_stage("d", [make_task("t", [make_job("j4", "c", [], [], "q", 1)])]),
            ],
        )
        doc.positions[_job_key("a", "t", "j1")] = (50.0, 50.0)
        doc.positions[_job_key("b", "t", "j2")] = (150.0, 50.0)
        doc.positions[_job_key("a", "t", "j3")] = (250.0, 50.0)
        doc.positions[_job_key("d", "t", "j4")] = (350.0, 50.0)

        flow = document_to_flow(doc)
        self.assertEqual([s["name"] for s in flow["stages"]], ["a", "b", "a_2", "d"])
        # Positions follow renamed keys
        self.assertIn(_job_key("a_2", "t", "j3"), doc.positions)


if __name__ == "__main__":
    unittest.main()

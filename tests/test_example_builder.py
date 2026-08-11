"""Tests for the example flow builder."""

import unittest

from winflow.generator.core.context import BuildContext
from winflow.generator.flows.example.builder import (
    ExampleFlowBuilder,
    build_example_stages,
    job_output_path,
    quality_job_name,
)
from winflow.generator.editor.document import TemplateOptions, example_template


class TestExampleBuilder(unittest.TestCase):
    def test_quality_job_name(self):
        self.assertEqual(quality_job_name("FLOOR_PLAN"), "Q_FLOOR_PLAN")
        self.assertEqual(quality_job_name("PLACE"), "Q_PLACE")

    def test_build_stages_shape(self):
        stages = build_example_stages(queue="q1", cpu="2")
        self.assertEqual([s["name"] for s in stages], ["FLOOR_PLAN", "PLACE", "CTS", "ROUTE"])
        for stage in stages:
            self.assertEqual(len(stage["tasks"]), 2)
            main_task, q_task = stage["tasks"]
            self.assertEqual(main_task["name"], stage["name"])
            self.assertEqual(q_task["name"], quality_job_name(stage["name"]))
            main_job = main_task["jobs"][0]
            q_job = q_task["jobs"][0]
            self.assertEqual(main_job["queue"], "q1")
            self.assertEqual(main_job["cpu"], 2)
            self.assertEqual(q_job["inputs"], main_job["outputs"])
            self.assertEqual(main_job["outputs"], [job_output_path(main_job["name"])])

    def test_main_chain_uses_previous_output(self):
        stages = build_example_stages()
        floor = stages[0]["tasks"][0]["jobs"][0]
        place = stages[1]["tasks"][0]["jobs"][0]
        self.assertEqual(floor["inputs"], [])
        self.assertEqual(place["inputs"], floor["outputs"])
        self.assertEqual(
            stages[2]["tasks"][0]["jobs"][0]["inputs"],
            place["outputs"],
        )

    def test_builder_from_context(self):
        context = BuildContext(
            settings={"MACHINE_QUEUE": "demo_q", "MACHINE_CPU": "3"},
            blocks=[],
        )
        flow = ExampleFlowBuilder.build(context)
        self.assertEqual(flow["flow_name"], "example")
        job = flow["stages"][0]["tasks"][0]["jobs"][0]
        self.assertEqual(job["queue"], "demo_q")
        self.assertEqual(job["cpu"], 3)
        # Main chain + Q_* side branches
        floor_key = "FLOOR_PLAN/FLOOR_PLAN/FLOOR_PLAN"
        self.assertIn("FLOOR_PLAN/Q_FLOOR_PLAN/Q_FLOOR_PLAN", job["children"])
        self.assertIn("PLACE/PLACE/PLACE", job["children"])
        place = flow["stages"][1]["tasks"][0]["jobs"][0]
        self.assertIn(floor_key, place["parents"])

    def test_example_template(self):
        doc = example_template(TemplateOptions(queue="normal", cpu=1))
        self.assertEqual(doc.flow_name, "example")
        names = [job["name"] for _s, _t, job in doc.iter_jobs()]
        self.assertEqual(
            names,
            [
                "FLOOR_PLAN",
                "Q_FLOOR_PLAN",
                "PLACE",
                "Q_PLACE",
                "CTS",
                "Q_CTS",
                "ROUTE",
                "Q_ROUTE",
            ],
        )


if __name__ == "__main__":
    unittest.main()

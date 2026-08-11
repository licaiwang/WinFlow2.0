"""Tests for flow builder registry."""

import unittest

from winflow.generator.core.builder import FlowBuilder
from winflow.generator.core.context import BuildContext
from winflow.generator.core.models import Flow, make_flow
from winflow.generator.core.registry import get_builder, list_flows, register
from winflow.generator.flows import example  # noqa: F401


class TestRegistry(unittest.TestCase):
    def test_example_is_registered(self):
        self.assertIn("example", list_flows())
        self.assertEqual(get_builder("example").flow_type, "example")
        self.assertEqual(get_builder("EXAMPLE").flow_type, "example")

    def test_unknown_flow_raises_key_error(self):
        with self.assertRaises(KeyError):
            get_builder("does_not_exist")

    def test_register_decorator(self):
        @register("test_flow")
        class TestFlowBuilder(FlowBuilder):
            @classmethod
            def validate_context(cls, context: BuildContext):
                return []

            @classmethod
            def build(cls, context: BuildContext) -> Flow:
                return make_flow("test", [])

        self.assertIn("test_flow", list_flows())
        self.assertIs(get_builder("test_flow"), TestFlowBuilder)


if __name__ == "__main__":
    unittest.main()

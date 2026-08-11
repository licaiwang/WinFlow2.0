"""Simple example flow: FLOOR_PLAN -> PLACE -> CTS -> ROUTE with Q_* checks."""

from __future__ import annotations

from typing import List, Optional, Tuple

from winflow.generator.core.builder import FlowBuilder
from winflow.generator.core.context import BuildContext
from winflow.generator.core.models import Flow, Job, Stage, make_flow, make_job, make_stage, make_task
from winflow.generator.core.registry import register
from winflow.config import get_config


def main_stage_names() -> Tuple[str, ...]:
    return get_config().example.main_stages


def quality_job_name(main: str) -> str:
    return f"{get_config().example.quality_prefix}{main}"


def job_output_path(job_name: str) -> str:
    cfg = get_config().example
    return cfg.output_template.format(job_name=job_name, out_dir=cfg.out_dir)


def job_command(job_name: str) -> str:
    cfg = get_config().example
    return cfg.command_template.format(job_name=job_name, script_dir=cfg.script_dir)


def _make_main_job(
    name: str,
    *,
    prev_output: Optional[str],
    queue: str,
    cpu: str,
    machine: str,
) -> Job:
    inputs = [prev_output] if prev_output else []
    return make_job(
        name=name,
        command=job_command(name),
        inputs=inputs,
        outputs=[job_output_path(name)],
        queue=queue,
        cpu=cpu,
        machine=machine,
    )


def _make_quality_job(
    name: str,
    *,
    parent_output: str,
    queue: str,
    cpu: str,
    machine: str,
) -> Job:
    return make_job(
        name=name,
        command=job_command(name),
        inputs=[parent_output],
        outputs=[job_output_path(name)],
        queue=queue,
        cpu=cpu,
        machine=machine,
    )


def build_example_stages(
    queue: Optional[str] = None,
    cpu: Optional[str] = None,
    machine: str = "",
) -> List[Stage]:
    """Build FLOOR_PLAN/PLACE/CTS/ROUTE stages, each with a Q_* side-check."""
    cfg = get_config().example
    queue = queue if queue is not None else cfg.default_queue
    cpu = cpu if cpu is not None else cfg.default_cpu

    stages: List[Stage] = []
    prev_output: Optional[str] = None

    for main_name in cfg.main_stages:
        main_job = _make_main_job(
            main_name,
            prev_output=prev_output,
            queue=queue,
            cpu=cpu,
            machine=machine,
        )
        q_name = quality_job_name(main_name)
        q_job = _make_quality_job(
            q_name,
            parent_output=main_job["outputs"][0],
            queue=queue,
            cpu=cpu,
            machine=machine,
        )
        stages.append(
            make_stage(
                main_name,
                [
                    make_task(main_name, [main_job]),
                    make_task(q_name, [q_job]),
                ],
            )
        )
        prev_output = main_job["outputs"][0]

    return stages


@register("example")
class ExampleFlowBuilder(FlowBuilder):
    """Build the bundled demo place-and-route style example flow."""

    @classmethod
    def validate_context(cls, context: BuildContext) -> List[str]:
        return []

    @classmethod
    def build(cls, context: BuildContext) -> Flow:
        settings = context.settings
        cfg = get_config().example
        gen_cfg = get_config().generator
        queue = settings.get("MACHINE_QUEUE", cfg.default_queue)
        cpu = settings.get("MACHINE_CPU", cfg.default_cpu)
        machine = settings.get("MACHINE_HOST", "")

        stages = build_example_stages(queue=queue, cpu=cpu, machine=machine)
        return make_flow(cfg.flow_name, stages, poll_interval=gen_cfg.poll_interval)

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from winflow.config import get_config, get_section
from winflow.generator.core.builder import FlowBuilder
from winflow.generator.core.context import BuildContext
from winflow.generator.core.models import Flow, Job, Stage, make_flow, make_job
from winflow.generator.core.registry import register
from winflow.generator.parsers import parse_yml


@dataclass(frozen=True)
class IthomeFlowConfig:
    """Defaults for the ithome flow; override via config.json without models.py."""

    flow_name: str = "ithome"
    script_dir: str = "ithome_flow"
    out_dir: str = "ithome_flow/out"
    command_template: str = "./{script_dir}/{job_name}.csh"
    output_template: str = "{out_dir}/{job_name}.done"
    default_queue: str = "normal"
    default_cpu: str = "1"
    default_yml: str = "example_flow/ithome.yml"


# DAG (file I/O → parents/children):
#
#   IT_2_0 .. IT_2_N ─────────┐
#                             V
#   IT_1 ──> IT_3 ──> IT_4 ──> IT_5
#              │                ^
#              └────────────────┘
#


def _cfg() -> IthomeFlowConfig:
    return get_section("ithome", IthomeFlowConfig())


def job_output_path(job_name: str) -> str:
    cfg = _cfg()
    return cfg.output_template.format(job_name=job_name, out_dir=cfg.out_dir)


def job_command(job_name: str) -> str:
    cfg = _cfg()
    return cfg.command_template.format(job_name=job_name, script_dir=cfg.script_dir)


def _wrap_jobs_as_stages(jobs: List[Job]) -> List[Stage]:
    """Flow schema requires stage/task nesting; derive both from each job name."""
    stages: List[Stage] = []
    for job in jobs:
        name = job["name"]
        stages.append({"name": name, "tasks": [{"name": name, "jobs": [job]}]})
    return stages


def _load_yml(
    yml: Optional[Dict[str, Any]] = None,
    yml_path: Optional[Union[str, Path]] = None,
) -> Dict[str, Any]:
    if yml is not None:
        return yml
    path = Path(yml_path) if yml_path else Path(_cfg().default_yml)
    return parse_yml(path) if path.exists() else {}


def build_ithome_stages(
    queue: Optional[str] = None,
    cpu: Optional[str] = None,
    machine: str = "",
    yml: Optional[Dict[str, Any]] = None,
    yml_path: Optional[Union[str, Path]] = None,
) -> List[Stage]:
    """Build ithome jobs from yml: fan-out IT_2_0..IT_2_N, optional IT_5."""
    cfg = _cfg()
    queue = queue if queue is not None else cfg.default_queue
    default_cpu = str(cpu if cpu is not None else cfg.default_cpu)
    machine = machine or ""

    data = _load_yml(yml=yml, yml_path=yml_path)
    cpu_map = data.get("CPU") if isinstance(data.get("CPU"), dict) else {}
    it2_list = data.get("IT_2_LIST") or ["default"]
    if not isinstance(it2_list, list) or not it2_list:
        it2_list = ["default"]
    use_it_5 = bool(data.get("USE_IT_5", True))

    def cpu_for(job_name: str) -> str:
        key = "IT_2" if job_name.startswith("IT_2") else job_name
        return str(cpu_map.get(key, default_cpu))

    out_it_1 = job_output_path("IT_1")
    out_it_3 = job_output_path("IT_3")
    out_it_4 = job_output_path("IT_4")
    out_it_5 = job_output_path("IT_5")

    jobs: List[Job] = [
        make_job(
            "IT_1",
            job_command("IT_1"),
            [],
            [out_it_1],
            queue,
            cpu_for("IT_1"),
            machine,
        ),
    ]

    it2_outputs: List[str] = []
    for index, block in enumerate(it2_list):
        name = f"IT_2_{index}"
        out_path = job_output_path(name)
        it2_outputs.append(out_path)
        jobs.append(
            make_job(
                name,
                f"{job_command('IT_2')} {block}",
                [],
                [out_path],
                queue,
                cpu_for(name),
                machine,
            )
        )

    jobs.append(
        make_job(
            "IT_3",
            job_command("IT_3"),
            [out_it_1],
            [out_it_3],
            queue,
            cpu_for("IT_3"),
            machine,
        )
    )
    jobs.append(
        make_job(
            "IT_4",
            job_command("IT_4"),
            [out_it_3,*it2_outputs],
            [out_it_4],
            queue,
            cpu_for("IT_4"),
            machine,
        )
    )

    if use_it_5:
        jobs.append(
            make_job(
                "IT_5",
                job_command("IT_5"),
                [out_it_3, out_it_4, *it2_outputs],
                [out_it_5],
                queue,
                cpu_for("IT_5"),
                machine,
            )
        )

    return _wrap_jobs_as_stages(jobs)


@register("ithome")
class ithomeFlowBuilder(FlowBuilder):
    """Build the ithome demo flow with parallel IT_2_* roots into IT_5."""

    @classmethod
    def validate_context(cls, context: BuildContext) -> List[str]:
        return []

    @classmethod
    def build(cls, context: BuildContext) -> Flow:
        settings = context.settings
        cfg = _cfg()
        gen_cfg = get_config().generator
        queue = settings.get("MACHINE_QUEUE", cfg.default_queue)
        cpu = settings.get("MACHINE_CPU", cfg.default_cpu)
        machine = settings.get("MACHINE_HOST", "")

        yml_path = getattr(context, "yml_path", None) or cfg.default_yml
        yml = _load_yml(yml_path=yml_path)
        flow_name = yml.get("FLOW_NAME", cfg.flow_name)

        stages = build_ithome_stages(
            queue=queue,
            cpu=cpu,
            machine=machine,
            yml=yml,
        )
        return make_flow(flow_name, stages, poll_interval=gen_cfg.poll_interval)

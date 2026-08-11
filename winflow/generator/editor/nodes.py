"""Predefined job-node library under winflow.generator/node/*.json."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional, Tuple

from winflow.generator.core.io import write_flow
from winflow.generator.core.models import Job, make_flow, make_job, make_stage, make_task
from winflow.generator.flows.example.builder import (
    job_command,
    job_output_path,
    main_stage_names,
    quality_job_name,
)
from winflow.config import get_config

# Default library location: winflow.generator/node/
NODE_DIR = Path(__file__).resolve().parent.parent / "node"


def node_dir() -> Path:
    return NODE_DIR


def _wrap_job_as_flow(job: Job, flow_name: str = "custom_flow", poll_interval: int = 20) -> dict:
    return make_flow(
        flow_name,
        [make_stage("stage_1", [make_task("task_1", [job])])],
        poll_interval=poll_interval,
    )


def extract_job_from_flow(data: dict) -> Job:
    """Return the first job found in a node/flow JSON document."""
    for stage in data.get("stages", []):
        for task in stage.get("tasks", []):
            jobs = task.get("jobs", [])
            if jobs:
                return jobs[0]  # type: ignore[return-value]
    raise ValueError("No job found in node JSON")


def extract_flow_name(data: dict) -> str:
    name = str(data.get("flow_name", "") or "").strip()
    return name or get_config().generator.blank_flow_name


def list_node_files(directory: Optional[Path] = None) -> List[Path]:
    root = directory or node_dir()
    if not root.is_dir():
        return []
    return sorted(root.glob("*.json"), key=lambda p: p.stem.lower())


def list_node_names(directory: Optional[Path] = None) -> List[str]:
    return [path.stem for path in list_node_files(directory)]


def list_nodes_by_flow(directory: Optional[Path] = None) -> List[Tuple[str, List[Tuple[str, str]]]]:
    """
    Group node templates by flow_name from each JSON.

    Returns [(flow_name, [(stem, job_display_name), ...]), ...]
    Prefer example, then custom_flow, then other names alphabetically.
    """
    root = directory or node_dir()
    grouped: dict = {}
    for path in list_node_files(root):
        try:
            with path.open(encoding="utf-8") as fp:
                data = json.load(fp)
            flow = extract_flow_name(data)
            job = extract_job_from_flow(data)
            display = str(job.get("name") or path.stem)
        except (OSError, json.JSONDecodeError, ValueError, KeyError, TypeError):
            flow = get_config().generator.blank_flow_name
            display = path.stem
        grouped.setdefault(flow, []).append((path.stem, display))

    for jobs in grouped.values():
        jobs.sort(key=lambda item: item[1].lower())

    preferred = [
        get_config().example.flow_name,
        get_config().generator.blank_flow_name,
    ]
    ordered: List[Tuple[str, List[Tuple[str, str]]]] = []
    for name in preferred:
        if name in grouped:
            ordered.append((name, grouped.pop(name)))
    for name in sorted(grouped.keys(), key=str.lower):
        ordered.append((name, grouped[name]))
    return ordered


def load_node(name: str, directory: Optional[Path] = None) -> Job:
    """Load a predefined job by stem name (without .json)."""
    root = directory or node_dir()
    path = root / f"{name}.json"
    if not path.is_file():
        raise FileNotFoundError(f"Node template not found: {path}")
    with path.open(encoding="utf-8") as fp:
        data = json.load(fp)
    return extract_job_from_flow(data)


def load_node_flow(name: str, directory: Optional[Path] = None) -> dict:
    root = directory or node_dir()
    path = root / f"{name}.json"
    with path.open(encoding="utf-8") as fp:
        return json.load(fp)


def write_node(
    job: Job,
    directory: Optional[Path] = None,
    filename: Optional[str] = None,
    flow_name: Optional[str] = None,
) -> Path:
    root = directory or node_dir()
    root.mkdir(parents=True, exist_ok=True)
    stem = filename or job["name"]
    path = root / f"{stem}.json"
    gen_cfg = get_config().generator
    # Node library entries are reusable job templates — omit runner DAG attrs
    # so files stay the same shape as before parents/children scheduling.
    from winflow.graph import strip_job_relations

    job_copy = dict(job)
    job_copy.pop("parents", None)
    job_copy.pop("children", None)
    flow = _wrap_job_as_flow(
        job_copy,  # type: ignore[arg-type]
        flow_name=flow_name or gen_cfg.blank_flow_name,
        poll_interval=gen_cfg.poll_interval,
    )
    strip_job_relations(flow["stages"])
    write_flow(flow, path, annotate=False)
    return path


def builtin_node_jobs() -> List[Tuple[str, str, Job]]:
    """
    Canonical job nodes derived from Blank / example template rules.

    Returns list of (filename_stem, flow_name, job).
    """
    gen = get_config().generator
    example_cfg = get_config().example
    example_flow = example_cfg.flow_name
    blank_flow = gen.blank_flow_name
    queue = example_cfg.default_queue
    cpu = int(example_cfg.default_cpu) if str(example_cfg.default_cpu).isdigit() else gen.default_cpu

    nodes: List[Tuple[str, str, Job]] = []

    def add(stem: str, flow: str, job: Job) -> None:
        nodes.append((stem, flow, job))

    add(
        "blank_job",
        blank_flow,
        make_job("job_1", "", [], [], gen.default_queue, gen.new_job_cpu),
    )

    for main in main_stage_names():
        add(
            main,
            example_flow,
            make_job(
                main,
                job_command(main),
                [],
                [job_output_path(main)],
                queue,
                cpu,
            ),
        )
        q_name = quality_job_name(main)
        add(
            q_name,
            example_flow,
            make_job(
                q_name,
                job_command(q_name),
                [job_output_path(main)],
                [job_output_path(q_name)],
                queue,
                cpu,
            ),
        )

    return nodes


def generate_builtin_nodes(directory: Optional[Path] = None) -> List[Path]:
    """Write all builtin template job nodes as flow-shaped JSON files."""
    root = directory or node_dir()
    written: List[Path] = []
    for stem, flow_name, job in builtin_node_jobs():
        written.append(write_node(job, directory=root, filename=stem, flow_name=flow_name))
    return written


def node_summary(job: Job) -> str:
    lines = [
        f"name:    {job.get('name', '')}",
        f"queue:   {job.get('queue', '')}",
        f"cpu:     {job.get('cpu', 1)}",
        f"command: {job.get('command', '') or '(empty)'}",
        "inputs:",
    ]
    inputs = job.get("inputs") or []
    if inputs:
        lines.extend(f"  - {p}" for p in inputs)
    else:
        lines.append("  (none)")
    lines.append("outputs:")
    outputs = job.get("outputs") or []
    if outputs:
        lines.extend(f"  - {p}" for p in outputs)
    else:
        lines.append("  (none)")
    return "\n".join(lines)


if __name__ == "__main__":
    paths = generate_builtin_nodes()
    print(f"Wrote {len(paths)} node templates to {node_dir()}")
    for path in paths:
        print(f"  {path.name}")

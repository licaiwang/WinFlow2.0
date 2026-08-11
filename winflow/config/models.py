"""Configuration dataclasses for WinFlow."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Tuple


@dataclass(frozen=True)
class RunnerConfig:
    default_flow_file: str = "flow.json"
    session_log_dir: str = "logs"
    session_log_file: str = "logs/flow_runner.log"
    job_log_dir: str = "log"
    poll_interval: int = 20
    default_queue: str = "normal"
    default_cpu: int = 4
    logger_name: str = "FlowRunner"
    kill_poll_ms: int = 15000
    kill_max_retries: int = 4
    log_tail_interval_sec: float = 0.5
    job_log_view_lines: int = 100
    thread_join_timeout_sec: float = 1.0
    log_viewer: str = "gvim"
    auto_load_delay_ms: int = 150


@dataclass(frozen=True)
class LSFConfig:
    bsub: str = "bsub"
    bjobs: str = "bjobs"
    bkill: str = "bkill"
    bjobs_noheader: bool = True
    bjobs_output_field: str = "stat"
    job_name_timestamp_format: str = "%Y%m%d_%H%M%S"


@dataclass(frozen=True)
class GeneratorConfig:
    default_flow_type: str = "example"
    default_setting_file: str = "example_flow/setting.sh"
    default_blocks_file: str = "block_stream.list"
    default_output_file: str = "flow.json"
    poll_interval: int = 20
    default_queue: str = "normal"
    default_cpu: int = 1
    blank_flow_name: str = "custom_flow"
    new_job_cpu: int = 1


@dataclass(frozen=True)
class ExampleFlowConfig:
    """Simple demo flow: main stages with Q_* quality side-checks."""

    flow_name: str = "example"
    main_stages: Tuple[str, ...] = ("FLOOR_PLAN", "PLACE", "CTS", "ROUTE")
    quality_prefix: str = "Q_"
    script_dir: str = "example_flow"
    out_dir: str = "example_flow/out"
    command_template: str = "./{script_dir}/{job_name}.csh"
    output_template: str = "{out_dir}/{job_name}.done"
    default_queue: str = "normal"
    default_cpu: str = "1"


@dataclass(frozen=True)
class GUIConfig:
    generator_window_size: str = "1280x800"
    generator_window_min: str = "960x640"
    runner_window_size: str = "1280x820"
    sidebar_min_width: int = 220


@dataclass(frozen=True)
class AppConfig:
    runner: RunnerConfig = field(default_factory=RunnerConfig)
    lsf: LSFConfig = field(default_factory=LSFConfig)
    generator: GeneratorConfig = field(default_factory=GeneratorConfig)
    example: ExampleFlowConfig = field(default_factory=ExampleFlowConfig)
    gui: GUIConfig = field(default_factory=GUIConfig)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AppConfig":
        from winflow.config.loader import merge_dataclass

        return merge_dataclass(cls(), data)

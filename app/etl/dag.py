"""
Custom lightweight DAG engine for ETL pipelines.

Demonstrates:
- DAG construction and topological execution (like Airflow / Step Functions)
- Event-driven task chaining
- Error propagation and partial-failure handling
- Pipeline observability (status tracking per node)

This is intentionally simple to show understanding of the concepts
without pulling in a heavy framework.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class TaskNode:
    """A single unit of work inside a DAG."""

    name: str
    execute_fn: Callable[[dict[str, Any]], dict[str, Any]]
    depends_on: list[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    result: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    duration_ms: float = 0.0


class DAG:
    """
    A directed acyclic graph of TaskNodes.

    Usage:
        dag = DAG("ingest_pipeline")
        dag.add_task("extract", extract_fn)
        dag.add_task("validate", validate_fn, depends_on=["extract"])
        dag.add_task("transform", transform_fn, depends_on=["validate"])
        dag.add_task("load", load_fn, depends_on=["transform"])
        result = dag.run(initial_context={"file": "patients.csv"})
    """

    def __init__(self, name: str):
        self.name = name
        self.tasks: dict[str, TaskNode] = {}

    def add_task(
        self,
        name: str,
        execute_fn: Callable[[dict[str, Any]], dict[str, Any]],
        depends_on: list[str] | None = None,
    ) -> DAG:
        if name in self.tasks:
            raise ValueError(f"Duplicate task name: {name}")
        self.tasks[name] = TaskNode(
            name=name, execute_fn=execute_fn, depends_on=depends_on or []
        )
        return self  # allow chaining

    def _topological_sort(self) -> list[str]:
        """Kahn's algorithm – returns tasks in dependency order."""
        in_degree: dict[str, int] = {name: 0 for name in self.tasks}
        for task in self.tasks.values():
            for dep in task.depends_on:
                if dep not in self.tasks:
                    raise ValueError(
                        f"Task '{task.name}' depends on unknown task '{dep}'"
                    )
                in_degree[task.name] += 1

        queue = [name for name, deg in in_degree.items() if deg == 0]
        order: list[str] = []

        while queue:
            current = queue.pop(0)
            order.append(current)
            for name, task in self.tasks.items():
                if current in task.depends_on:
                    in_degree[name] -= 1
                    if in_degree[name] == 0:
                        queue.append(name)

        if len(order) != len(self.tasks):
            raise ValueError("Cycle detected in DAG")
        return order

    def run(self, initial_context: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        Execute all tasks in topological order.
        Each task receives the merged context from its upstream dependencies.
        """
        execution_order = self._topological_sort()
        context = dict(initial_context or {})
        summary: dict[str, Any] = {"pipeline": self.name, "tasks": {}}

        logger.info("Starting pipeline '%s' with %d tasks", self.name, len(self.tasks))

        for task_name in execution_order:
            task = self.tasks[task_name]

            # Skip if any upstream dependency failed
            upstream_failed = any(
                self.tasks[dep].status == TaskStatus.FAILED for dep in task.depends_on
            )
            if upstream_failed:
                task.status = TaskStatus.SKIPPED
                logger.warning("Skipping '%s' – upstream dependency failed", task_name)
                summary["tasks"][task_name] = {"status": "skipped"}
                continue

            # Merge upstream results into context
            for dep in task.depends_on:
                context.update(self.tasks[dep].result)

            # Execute
            task.status = TaskStatus.RUNNING
            logger.info("Running task '%s'", task_name)
            start = time.perf_counter()
            try:
                task.result = task.execute_fn(context) or {}
                task.status = TaskStatus.SUCCESS
            except Exception as exc:
                task.status = TaskStatus.FAILED
                task.error = str(exc)
                logger.error("Task '%s' failed: %s", task_name, exc)
            finally:
                task.duration_ms = (time.perf_counter() - start) * 1000

            summary["tasks"][task_name] = {
                "status": task.status.value,
                "duration_ms": round(task.duration_ms, 2),
                "error": task.error,
            }

        all_success = all(t.status == TaskStatus.SUCCESS for t in self.tasks.values())
        summary["status"] = "completed" if all_success else "failed"
        logger.info("Pipeline '%s' finished – %s", self.name, summary["status"])
        return summary

    def to_dict(self) -> dict[str, Any]:
        """Serialize the DAG definition (stored in pipeline_runs.dag_definition)."""
        return {
            "name": self.name,
            "tasks": {
                name: {"depends_on": task.depends_on}
                for name, task in self.tasks.items()
            },
        }

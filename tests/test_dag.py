"""Tests for the custom DAG engine – runs without any external dependencies."""

import pytest

from app.etl.dag import DAG, TaskStatus


def test_linear_dag_executes_in_order():
    """Tasks run in dependency order and context flows downstream."""
    execution_log = []

    def step_a(ctx):
        execution_log.append("a")
        return {"from_a": 1}

    def step_b(ctx):
        execution_log.append("b")
        assert ctx["from_a"] == 1
        return {"from_b": 2}

    def step_c(ctx):
        execution_log.append("c")
        assert ctx["from_b"] == 2

    dag = DAG("test_linear")
    dag.add_task("a", step_a)
    dag.add_task("b", step_b, depends_on=["a"])
    dag.add_task("c", step_c, depends_on=["b"])

    result = dag.run()
    assert result["status"] == "completed"
    assert execution_log == ["a", "b", "c"]


def test_failed_task_skips_downstream():
    """When a task fails, its dependents are skipped (not crashed)."""

    def failing_task(ctx):
        raise RuntimeError("Intentional failure")

    def downstream(ctx):
        pytest.fail("Should not have run")

    dag = DAG("test_failure")
    dag.add_task("fail", failing_task)
    dag.add_task("after", downstream, depends_on=["fail"])

    result = dag.run()
    assert result["status"] == "failed"
    assert dag.tasks["fail"].status == TaskStatus.FAILED
    assert dag.tasks["after"].status == TaskStatus.SKIPPED


def test_cycle_detection():
    """DAG rejects circular dependencies."""
    dag = DAG("test_cycle")
    dag.add_task("a", lambda ctx: None, depends_on=["b"])
    dag.add_task("b", lambda ctx: None, depends_on=["a"])

    with pytest.raises(ValueError, match="Cycle detected"):
        dag.run()


def test_diamond_dag():
    """Diamond shape: A -> B, A -> C, B+C -> D."""
    dag = DAG("diamond")
    dag.add_task("a", lambda ctx: {"val": 1})
    dag.add_task("b", lambda ctx: {"b_val": ctx["val"] + 10}, depends_on=["a"])
    dag.add_task("c", lambda ctx: {"c_val": ctx["val"] + 20}, depends_on=["a"])
    dag.add_task(
        "d",
        lambda ctx: {"total": ctx["b_val"] + ctx["c_val"]},
        depends_on=["b", "c"],
    )

    result = dag.run()
    assert result["status"] == "completed"
    assert dag.tasks["d"].result["total"] == 32  # 11 + 21


def test_to_dict_serialization():
    """DAG can serialize its structure for storage."""
    dag = DAG("serialize_test")
    dag.add_task("x", lambda ctx: None)
    dag.add_task("y", lambda ctx: None, depends_on=["x"])

    d = dag.to_dict()
    assert d["name"] == "serialize_test"
    assert d["tasks"]["y"]["depends_on"] == ["x"]

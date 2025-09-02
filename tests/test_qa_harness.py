from amor.qa import QAHarness
from amor.core.seed import SeedManager


def test_qa_harness_snapshot_and_reproduce():
    sm = SeedManager(777)
    qa = QAHarness(sm)
    a = qa.randint(1, 10)
    b = qa.choice(["sword", "shield", "potion"])  # noqa: F841
    c = qa.sample(list(range(10)), 3)
    d = qa.shuffle([1, 2, 3, 4])
    e = qa.spawn_id()
    trace = qa.snapshot()

    ok, info = qa.reproduce(trace)
    assert ok, info


def test_qa_harness_mismatch_detected():
    sm = SeedManager(123)
    qa = QAHarness(sm)
    qa.randint(0, 5)
    trace = qa.snapshot()

    # Tamper with trace result
    trace.events[0]["result"] = 999

    ok, info = qa.reproduce(trace)
    assert not ok
    assert isinstance(info, dict)
    assert info.get("index") == 0

"""ジョブ排他制御のテスト。"""
from csv_to_kintone.coordinator import JobCoordinator


def test_same_job_cannot_overlap():
    coordinator = JobCoordinator()
    assert coordinator.acquire("job1", 1)
    assert not coordinator.acquire("job1", 1)
    coordinator.release("job1", 1)
    assert coordinator.acquire("job1", 1)


def test_different_jobs_same_app_cannot_overlap():
    coordinator = JobCoordinator()
    assert coordinator.acquire("job1", 1)
    assert not coordinator.acquire("job2", 1)
    assert coordinator.acquire("job3", 2)
    coordinator.release("job1", 1)
    assert coordinator.acquire("job2", 1)

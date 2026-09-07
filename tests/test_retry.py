from aiohttp import ClientConnectionError

from payme.retry import NO_RETRY, RetryPolicy


def test_retries_only_connection_failures():
    policy = RetryPolicy(attempts=3)
    assert policy.should_retry(ClientConnectionError("boom"), attempt=1)
    assert not policy.should_retry(ValueError("nope"), attempt=1)


def test_stops_at_the_attempt_limit():
    policy = RetryPolicy(attempts=2)
    assert policy.should_retry(ClientConnectionError(""), attempt=1)
    assert not policy.should_retry(ClientConnectionError(""), attempt=2)


def test_backoff_grows_and_is_capped():
    policy = RetryPolicy(base_delay=1.0, max_delay=4.0, jitter=0.0)
    assert [policy.delay_for(n) for n in (1, 2, 3, 4)] == [1.0, 2.0, 4.0, 4.0]


def test_jitter_stays_within_bounds():
    policy = RetryPolicy(base_delay=1.0, jitter=0.25)
    delays = [policy.delay_for(1) for _ in range(200)]
    assert all(0.75 <= d <= 1.25 for d in delays)
    assert len(set(delays)) > 1, "jitter must actually spread retries out"


def test_money_moving_calls_get_a_single_attempt():
    assert NO_RETRY.attempts == 1
    assert not NO_RETRY.should_retry(ClientConnectionError(""), attempt=1)

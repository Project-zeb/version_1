from disaster_api.fetchers.http_client import create_retry_session, get_with_retries


def fetch_ndma_cap_feed(
    url: str,
    timeout_seconds: int,
    retries: int = 2,
    backoff_seconds: float = 0.5,
) -> bytes:
    session = create_retry_session(retries=retries, backoff_seconds=backoff_seconds)
    try:
        response = get_with_retries(
            session=session,
            url=url,
            timeout_seconds=timeout_seconds,
            retries=retries,
            backoff_seconds=backoff_seconds,
        )
        response.raise_for_status()
        return response.content
    finally:
        session.close()

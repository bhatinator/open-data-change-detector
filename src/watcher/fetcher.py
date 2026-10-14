
import logging
import time
import requests


API_URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"

logger = logging.getLogger(__name__)


class FetchError(Exception):
    """Raised when a dataset cannot be fetched after retries."""

def fetch_page(
    session,
    offset,
    limit=100,
    timeout=30,
    max_retries=3,
    backoff_factor=1.0,
):
    """Fetch one page, retrying temporary failures."""

    params = {
        "format": "geojson",
        "limit": limit,
        "offset": offset,
        "orderby": "time",
    }

    for attempt in range(max_retries + 1):
        try:
            response = session.get(
                API_URL,
                params=params,
                timeout=timeout,
            )

            if response.status_code == 429 or response.status_code >= 500:
                response.raise_for_status()  # Retry temporary failures

            if response.status_code >= 400:
                raise FetchError(
                f"Permanent HTTP error: {response.status_code}"
            )

            data = response.json()
            features = data.get("features")

            if not isinstance(features, list):
                raise FetchError(
                    "Unexpected API response: 'features' is not a list."
                )

            logger.info(
                "Fetched page: offset=%s, records=%s",
                offset,
                len(features),
            )

            return features

        except requests.exceptions.RequestException as error:
            if attempt == max_retries:
                logger.error(
                    "Request failed after %s attempts: %s",
                    attempt + 1,
                    error,
                )
                raise FetchError(
                    f"Could not fetch page at offset {offset}."
                ) from error

            delay = backoff_factor * (2 ** attempt)

            logger.warning(
                "Request failed (attempt %s/%s). Retrying in %.1f seconds.",
                attempt + 1,
                max_retries + 1,
                delay,
            )

            time.sleep(delay)

        except ValueError as error:
            # Invalid JSON usually indicates a bad response.
            raise FetchError("The API returned invalid JSON.") from error

    raise FetchError(f"Could not fetch page at offset {offset}.")


def fetch_all_earthquakes(
    page_size=100,
    timeout=30,
    max_retries=3,
    backoff_factor=1.0,
    page_delay=0.5,
    max_records=500,
):
    """Fetch earthquake records page by page."""

    if page_size < 1 or max_records < 1:
        raise ValueError("page_size and max_records must be positive.")

    records = []
    offset = 1

    with requests.Session() as session:
        while len(records) < max_records:
            current_limit = min(page_size, max_records - len(records))

            page = fetch_page(
                session=session,
                offset=offset,
                limit=current_limit,
                timeout=timeout,
                max_retries=max_retries,
                backoff_factor=backoff_factor,
            )

            if not page:
                break

            records.extend(page)
            offset += len(page)

            if len(page) < current_limit:
                # Fewer results than requested: no more pages.
                break

            if len(records) < max_records:
                time.sleep(page_delay)

    logger.info("Fetch completed: %s records", len(records))
    return records

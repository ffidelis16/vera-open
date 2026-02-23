"""
Async Notion API client for Vera Open.

Handles: authentication, pagination, rate limiting (429 retry),
and provides typed helpers for common operations.

Uses aiohttp directly (no SDK) for full control and minimal dependencies.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Optional

import aiohttp

logger = logging.getLogger(__name__)

NOTION_API_VERSION = "2022-06-28"
NOTION_BASE_URL = "https://api.notion.com/v1"

# Rate limit: 3 req/s average, burst up to ~10
MAX_CONCURRENT = 3
MAX_RETRIES = 3
RETRY_BASE_DELAY = 1.0  # seconds, doubles each retry


class NotionAPIError(Exception):
    """Raised when Notion API returns an error."""

    def __init__(self, status: int, code: str, message: str):
        self.status = status
        self.code = code
        super().__init__(f"Notion API {status} ({code}): {message}")


class NotionClient:
    """
    Async Notion API client.

    Usage:
        async with NotionClient(token="ntn_...") as notion:
            tasks = await notion.query_database("abc123", filter={...})
            await notion.update_page("page_id", {"Urgência Real": {"number": 85}})
    """

    def __init__(self, token: str):
        self._token = token
        self._session: Optional[aiohttp.ClientSession] = None
        self._semaphore = asyncio.Semaphore(MAX_CONCURRENT)
        self._request_count = 0
        self._start_time = 0.0

    async def __aenter__(self) -> "NotionClient":
        self._session = aiohttp.ClientSession(
            headers={
                "Authorization": f"Bearer {self._token}",
                "Notion-Version": NOTION_API_VERSION,
                "Content-Type": "application/json",
            },
            timeout=aiohttp.ClientTimeout(total=30),
        )
        self._start_time = time.monotonic()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._session:
            await self._session.close()
            elapsed = time.monotonic() - self._start_time
            logger.info(
                f"Notion client closed: {self._request_count} requests in {elapsed:.1f}s"
            )

    # --------------------------------------------------------
    # Core request with retry + rate limit
    # --------------------------------------------------------

    async def _request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[dict] = None,
    ) -> dict:
        """
        Make an authenticated request to Notion API.
        Handles 429 (rate limit) with exponential backoff.
        """
        url = f"{NOTION_BASE_URL}/{endpoint.lstrip('/')}"

        for attempt in range(MAX_RETRIES):
            async with self._semaphore:
                try:
                    async with self._session.request(
                        method, url, json=json_data
                    ) as resp:
                        self._request_count += 1

                        if resp.status == 200:
                            return await resp.json()

                        body = await resp.json()
                        code = body.get("code", "unknown")
                        message = body.get("message", "No details")

                        # Rate limited — retry with backoff
                        if resp.status == 429:
                            retry_after = float(
                                resp.headers.get("Retry-After", RETRY_BASE_DELAY)
                            )
                            wait = max(retry_after, RETRY_BASE_DELAY * (2 ** attempt))
                            logger.warning(
                                f"Rate limited (429). Waiting {wait:.1f}s "
                                f"(attempt {attempt + 1}/{MAX_RETRIES})"
                            )
                            await asyncio.sleep(wait)
                            continue

                        # Client error — don't retry
                        if 400 <= resp.status < 500:
                            raise NotionAPIError(resp.status, code, message)

                        # Server error — retry
                        if resp.status >= 500:
                            logger.warning(
                                f"Notion server error {resp.status}. "
                                f"Retrying ({attempt + 1}/{MAX_RETRIES})..."
                            )
                            await asyncio.sleep(RETRY_BASE_DELAY * (2 ** attempt))
                            continue

                except aiohttp.ClientError as e:
                    logger.warning(
                        f"Network error: {e}. Retrying ({attempt + 1}/{MAX_RETRIES})..."
                    )
                    await asyncio.sleep(RETRY_BASE_DELAY * (2 ** attempt))
                    continue

        raise NotionAPIError(
            503, "max_retries",
            f"Failed after {MAX_RETRIES} attempts to {method} {endpoint}"
        )

    # --------------------------------------------------------
    # Database operations
    # --------------------------------------------------------

    async def query_database(
        self,
        database_id: str,
        filter: Optional[dict] = None,
        sorts: Optional[list[dict]] = None,
        page_size: int = 100,
    ) -> list[dict]:
        """
        Query a database with automatic pagination.
        Returns ALL matching pages (handles cursor-based pagination).
        """
        database_id = database_id.replace("-", "")
        results = []
        cursor = None

        while True:
            body: dict[str, Any] = {"page_size": min(page_size, 100)}
            if filter:
                body["filter"] = filter
            if sorts:
                body["sorts"] = sorts
            if cursor:
                body["start_cursor"] = cursor

            response = await self._request(
                "POST", f"databases/{database_id}/query", json_data=body
            )

            results.extend(response.get("results", []))
            cursor = response.get("next_cursor")

            if not cursor or not response.get("has_more", False):
                break

        logger.info(f"Queried database {database_id[:8]}...: {len(results)} pages")
        return results

    async def get_database(self, database_id: str) -> dict:
        """Retrieve database metadata (schema, title, etc.)."""
        database_id = database_id.replace("-", "")
        return await self._request("GET", f"databases/{database_id}")

    # --------------------------------------------------------
    # Page operations
    # --------------------------------------------------------

    async def get_page(self, page_id: str) -> dict:
        """Retrieve a single page."""
        page_id = page_id.replace("-", "")
        return await self._request("GET", f"pages/{page_id}")

    async def update_page(self, page_id: str, properties: dict) -> dict:
        """
        Update page properties.

        Args:
            page_id: The page to update.
            properties: Notion API properties format, e.g.:
                {"Urgência Real": {"number": 85}}
        """
        page_id = page_id.replace("-", "")
        return await self._request(
            "PATCH",
            f"pages/{page_id}",
            json_data={"properties": properties},
        )

    async def create_page(
        self,
        database_id: str,
        properties: dict,
    ) -> dict:
        """Create a new page in a database."""
        database_id = database_id.replace("-", "")
        return await self._request(
            "POST",
            "pages",
            json_data={
                "parent": {"database_id": database_id},
                "properties": properties,
            },
        )

    # --------------------------------------------------------
    # Batch operations
    # --------------------------------------------------------

    async def batch_update_pages(
        self,
        updates: list[tuple[str, dict]],
    ) -> list[dict]:
        """
        Update multiple pages concurrently (respecting rate limits).

        Args:
            updates: List of (page_id, properties) tuples.

        Returns:
            List of update results.
        """
        tasks = [
            self.update_page(page_id, props)
            for page_id, props in updates
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        successes = sum(1 for r in results if not isinstance(r, Exception))
        failures = sum(1 for r in results if isinstance(r, Exception))

        if failures:
            logger.warning(
                f"Batch update: {successes} succeeded, {failures} failed"
            )
            for r in results:
                if isinstance(r, Exception):
                    logger.warning(f"  Failed: {r}")

        return results

    # --------------------------------------------------------
    # Property helpers — extract values from Notion's verbose format
    # --------------------------------------------------------

    @staticmethod
    def extract_title(properties: dict, field_name: str) -> str:
        """Extract plain text from a title property."""
        prop = properties.get(field_name, {})
        title_list = prop.get("title", [])
        return "".join(t.get("plain_text", "") for t in title_list)

    @staticmethod
    def extract_rich_text(properties: dict, field_name: str) -> str:
        """Extract plain text from a rich_text property."""
        prop = properties.get(field_name, {})
        rt_list = prop.get("rich_text", [])
        return "".join(t.get("plain_text", "") for t in rt_list)

    @staticmethod
    def extract_select(properties: dict, field_name: str) -> str:
        """Extract value from a select property."""
        prop = properties.get(field_name, {})
        select = prop.get("select")
        return select.get("name", "") if select else ""

    @staticmethod
    def extract_multi_select(properties: dict, field_name: str) -> list[str]:
        """Extract values from a multi_select property."""
        prop = properties.get(field_name, {})
        return [opt.get("name", "") for opt in prop.get("multi_select", [])]

    @staticmethod
    def extract_number(properties: dict, field_name: str) -> Optional[float]:
        """Extract value from a number property."""
        prop = properties.get(field_name, {})
        return prop.get("number")

    @staticmethod
    def extract_date(properties: dict, field_name: str) -> Optional[str]:
        """Extract start date string from a date property."""
        prop = properties.get(field_name, {})
        date = prop.get("date")
        return date.get("start") if date else None

    @staticmethod
    def extract_checkbox(properties: dict, field_name: str) -> bool:
        """Extract value from a checkbox property."""
        prop = properties.get(field_name, {})
        return prop.get("checkbox", False)

    @staticmethod
    def extract_url(properties: dict, field_name: str) -> str:
        """Extract value from a url property."""
        prop = properties.get(field_name, {})
        return prop.get("url", "") or ""

    # --------------------------------------------------------
    # Notion property builders — create properties for writes
    # --------------------------------------------------------

    @staticmethod
    def prop_number(value: float | int | None) -> dict:
        """Build a number property value."""
        return {"number": value}

    @staticmethod
    def prop_select(value: str) -> dict:
        """Build a select property value."""
        return {"select": {"name": value}}

    @staticmethod
    def prop_rich_text(value: str) -> dict:
        """Build a rich_text property value."""
        return {"rich_text": [{"text": {"content": value}}]}

    @staticmethod
    def prop_date(start: str, end: Optional[str] = None) -> dict:
        """Build a date property value. Dates in ISO format (YYYY-MM-DD)."""
        date = {"start": start}
        if end:
            date["end"] = end
        return {"date": date}

    @staticmethod
    def prop_checkbox(value: bool) -> dict:
        """Build a checkbox property value."""
        return {"checkbox": value}

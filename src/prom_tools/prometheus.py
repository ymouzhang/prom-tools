"""
Prometheus API client with async support.
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Union
from urllib.parse import urlencode

from .base import BaseAsyncClient
from .models import (
    Query,
    QueryResult,
    Metric,
    PrometheusTarget,
    PrometheusRule,
)
from .exceptions import PrometheusError


class PrometheusClient(BaseAsyncClient):
    """Async Prometheus API client."""

    def __init__(
        self,
        url: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        token: Optional[str] = None,
        **kwargs
    ) -> None:
        super().__init__(base_url=url, **kwargs)
        self.username = username
        self.password = password
        self.token = token

    def _prepare_auth_headers(self) -> Dict[str, str]:
        """Prepare authentication headers."""
        headers = {}

        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        elif self.username and self.password:
            import base64
            credentials = base64.b64encode(f"{self.username}:{self.password}".encode()).decode()
            headers["Authorization"] = f"Basic {credentials}"

        return headers

    async def query(
        self,
        query: str,
        query_time: Optional[datetime] = None,
        timeout: Optional[str] = None,
    ) -> QueryResult:
        """Execute an instant query."""
        params = {"query": query}

        if query_time:
            params["time"] = query_time.timestamp()
        if timeout:
            params["timeout"] = timeout

        try:
            response = await self._request(
                "GET",
                "api/v1/query",
                params=params,
                headers=self._prepare_auth_headers(),
            )
            return QueryResult.from_response(None, query, response, query_type="instant")
        except asyncio.CancelledError as e:
            return QueryResult.from_error(None, query, e, query_type="instant")
        except Exception as e:
            return QueryResult.from_error(None, query, e, query_type="instant")

    async def query_range(
        self,
        query: str,
        start: datetime,
        end: datetime,
        step: Union[str, timedelta],
        timeout: Optional[str] = None,
    ) -> QueryResult:
        """Execute a range query."""
        if isinstance(step, timedelta):
            step = f"{step.total_seconds()}s"

        params = {
            "query": query,
            "start": start.timestamp(),
            "end": end.timestamp(),
            "step": step,
        }

        if timeout:
            params["timeout"] = timeout

        try:
            response = await self._request(
                "GET",
                "api/v1/query_range",
                params=params,
                headers=self._prepare_auth_headers(),
            )
            return QueryResult.from_response(None, query, response, query_type="range")
        except Exception as e:
            return QueryResult.from_error(None, query, e, query_type="range")

    async def query_series(
        self,
        match: str = '{__name__=~".+"}',
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Query for series metadata."""
        params = {"match[]": match}

        if start:
            params["start"] = start.timestamp()
        if end:
            params["end"] = end.timestamp()

        try:
            response = await self._request(
                "GET",
                "api/v1/series",
                params=params,
                headers=self._prepare_auth_headers(),
            )
            return response.get("data", [])
        except Exception as e:
            raise PrometheusError(f"Series query failed: {str(e)}")

    async def query_labels(
        self,
        match: Optional[str] = None,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> List[str]:
        """Query for label names."""
        params = {}

        if match:
            params["match[]"] = match
        if start:
            params["start"] = start.timestamp()
        if end:
            params["end"] = end.timestamp()

        try:
            response = await self._request(
                "GET",
                "api/v1/labels",
                params=params,
                headers=self._prepare_auth_headers(),
            )
            return response.get("data", [])
        except Exception as e:
            raise PrometheusError(f"Labels query failed: {str(e)}")

    async def query_label_values(
        self,
        label: str,
        match: Optional[str] = None,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> List[str]:
        """Query for label values."""
        params = {}

        if match:
            params["match[]"] = match
        if start:
            params["start"] = start.timestamp()
        if end:
            params["end"] = end.timestamp()

        try:
            response = await self._request(
                "GET",
                f"api/v1/label/{label}/values",
                params=params,
                headers=self._prepare_auth_headers(),
            )
            return response.get("data", [])
        except Exception as e:
            raise PrometheusError(f"Label values query failed: {str(e)}")

    # Management API endpoints
    async def get_targets(self) -> Dict[str, Any]:
        """Get current targets."""
        try:
            return await self._request(
                "GET",
                "api/v1/targets",
                headers=self._prepare_auth_headers(),
            )
        except Exception as e:
            raise PrometheusError(f"Failed to get targets: {str(e)}")

    async def get_targets_detailed(self) -> List[PrometheusTarget]:
        """Get detailed targets information."""
        try:
            response = await self.get_targets()
            targets_data = response.get("data", {}).get("activeTargets", [])

            targets = []
            for target in targets_data:
                labels = target.get("labels", {})
                targets.append(PrometheusTarget(
                    instance=labels.get("__address__", "unknown"),
                    job=labels.get("job", "unknown"),
                    health=target.get("health", ""),
                    last_error=target.get("lastError"),
                    scrape_interval=target.get("scrapeInterval", ""),
                    scrape_timeout=target.get("scrapeTimeout", ""),
                    labels=labels,
                    discovered_labels=target.get("discoveredLabels", {}),
                    scrape_pool=target.get("scrapePool", ""),
                    scrape_url=target.get("scrapeUrl", ""),
                    global_url=target.get("globalUrl", ""),
                ))
            return targets
        except Exception as e:
            raise PrometheusError(f"Failed to get detailed targets: {str(e)}")

    async def get_rules(self) -> Dict[str, Any]:
        """Get current rules."""
        try:
            return await self._request(
                "GET",
                "api/v1/rules",
                headers=self._prepare_auth_headers(),
            )
        except Exception as e:
            raise PrometheusError(f"Failed to get rules: {str(e)}")

    async def get_alerts(self) -> Dict[str, Any]:
        """Get current alerts."""
        try:
            return await self._request(
                "GET",
                "api/v1/alerts",
                headers=self._prepare_auth_headers(),
            )
        except Exception as e:
            raise PrometheusError(f"Failed to get alerts: {str(e)}")

    async def get_alert_managers(self) -> Dict[str, Any]:
        """Get alert manager configurations."""
        try:
            return await self._request(
                "GET",
                "api/v1/alertmanagers",
                headers=self._prepare_auth_headers(),
            )
        except Exception as e:
            raise PrometheusError(f"Failed to get alert managers: {str(e)}")

    # Admin API endpoints
    async def delete_series(
        self,
        match: List[str],
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Delete series data."""
        params = {"match[]": match}

        if start:
            params["start"] = start.timestamp()
        if end:
            params["end"] = end.timestamp()

        try:
            return await self._request(
                "POST",
                "api/v1/admin/tsdb/delete_series",
                params=params,
                headers=self._prepare_auth_headers(),
            )
        except Exception as e:
            raise PrometheusError(f"Failed to delete series: {str(e)}")

    async def clean_tombstones(self) -> Dict[str, Any]:
        """Clean tombstones."""
        try:
            return await self._request(
                "POST",
                "api/v1/admin/tsdb/clean_tombstones",
                headers=self._prepare_auth_headers(),
            )
        except Exception as e:
            raise PrometheusError(f"Failed to clean tombstones: {str(e)}")

    # Snapshot API
    async def create_snapshot(
        self,
        skip_head: bool = False,
    ) -> Dict[str, Any]:
        """Create a snapshot."""
        params = {"skip_head": "true" if skip_head else "false"}

        try:
            return await self._request(
                "POST",
                "api/v1/admin/tsdb/snapshot",
                params=params,
                headers=self._prepare_auth_headers(),
            )
        except Exception as e:
            raise PrometheusError(f"Failed to create snapshot: {str(e)}")

    # Health and configuration
    async def get_health(self) -> Dict[str, Any]:
        """Get Prometheus health status."""
        try:
            return await self._request(
                "GET",
                "-/healthy",
                headers=self._prepare_auth_headers(),
                use_httpx=True,
            )
        except Exception as e:
            raise PrometheusError(f"Failed to get health status: {str(e)}")

    async def get_ready(self) -> Dict[str, Any]:
        """Get Prometheus readiness status."""
        try:
            return await self._request(
                "GET",
                "-/ready",
                headers=self._prepare_auth_headers(),
                use_httpx=True,
            )
        except Exception as e:
            raise PrometheusError(f"Failed to get readiness status: {str(e)}")

    async def get_config(self) -> Dict[str, Any]:
        """Get Prometheus configuration."""
        try:
            return await self._request(
                "GET",
                "api/v1/status/config",
                headers=self._prepare_auth_headers(),
            )
        except Exception as e:
            raise PrometheusError(f"Failed to get configuration: {str(e)}")

    async def get_flags(self) -> Dict[str, Any]:
        """Get Prometheus command-line flag values."""
        try:
            return await self._request(
                "GET",
                "api/v1/status/flags",
                headers=self._prepare_auth_headers(),
            )
        except Exception as e:
            raise PrometheusError(f"Failed to get flags: {str(e)}")

    # Unified query methods
    async def query_multiple(
        self,
        queries: List[Union[str, Query, Dict[str, Any]]],
        query_time: Optional[datetime] = None,
        max_concurrent: int = 10,
    ) -> List[QueryResult]:
        """Execute multiple queries concurrently with flexible input types.

        Args:
            queries: List of queries (strings, Query objects, or range query dicts)
            query_time: Optional time parameter for instant queries
            max_concurrent: Maximum number of concurrent queries

        Returns:
            List of QueryResult objects with query information and results

        Examples:
            # String queries
            results = await client.query_multiple(["up", "cpu_usage"])

            # Query objects with optional names
            queries = [
                Query(name="服务状态", query="up"),
                Query(query="cpu_usage"),
                Query(name="CPU趋势", query="rate(cpu_total[5m])", start=start, end=end, step="1m")
            ]
            results = await client.query_multiple(queries)

            # Mixed queries
            queries = [
                "up",  # string
                Query(name="内存", query="memory_usage"),  # Query object
                {"query": "disk_usage", "start": start, "end": end, "step": "5m"}  # range query dict
            ]
            results = await client.query_multiple(queries)
        """
        # Convert all inputs to Query objects and validate
        query_objects = []
        for query_input in queries:
            if isinstance(query_input, str):
                # String query - no name
                query_obj = Query(query=query_input)
            elif isinstance(query_input, Query):
                # Query object - validate range query has step
                query_obj = query_input
                if query_obj.is_range_query and not query_obj.step:
                    raise ValueError(f"Range query '{query_obj.query}' requires step parameter")
            elif isinstance(query_input, dict):
                # Range query dict - automatically treated as range query if start/end present
                query_obj = Query(
                    name=query_input.get("name"),
                    query=query_input["query"],
                    start=query_input.get("start"),
                    end=query_input.get("end"),
                    step=query_input.get("step")
                )
                if query_obj.is_range_query and not query_obj.step:
                    raise ValueError(f"Range query '{query_obj.query}' requires step parameter")
            else:
                raise ValueError(f"Unsupported query type: {type(query_input)}")

            query_objects.append(query_obj)

        semaphore = asyncio.Semaphore(max_concurrent)

        async def execute_single_query(query_obj: Query) -> QueryResult:
            """Execute a single Query object - simplified to only handle Query models."""
            async with semaphore:
                start_time = time.time()

                try:
                    # Execute the query based on its type
                    if query_obj.is_range_query:
                        result = await self.query_range(
                            query=query_obj.query,
                            start=query_obj.start,
                            end=query_obj.end,
                            step=query_obj.step,
                            timeout=query_obj.timeout
                        )
                    else:
                        result = await self.query(query_obj.query, query_time, query_obj.timeout)

                    # Update execution time and query name
                    execution_time = time.time() - start_time
                    result.execution_time = execution_time
                    if query_obj.name:
                        result.query_name = query_obj.name
                    return result
                except Exception as e:
                    execution_time = time.time() - start_time
                    return QueryResult.from_error(
                        query_obj.name,
                        query_obj.query,
                        e,
                        execution_time,
                        query_obj.query_type
                    )

        tasks = [execute_single_query(query_obj) for query_obj in query_objects]
        return await asyncio.gather(*tasks)

    @staticmethod
    def create_queries(queries: List[Dict[str, Any]]) -> List[Query]:
        """Create Query objects from dictionary list.

        Args:
            queries: List of dicts with at least 'name' and 'query' keys

        Returns:
            List of Query objects
        """
        query_objects = []
        for query_dict in queries:
            query_objects.append(Query(
                name=query_dict["name"],
                query=query_dict["query"],
                description=query_dict.get("description"),
                category=query_dict.get("category"),
                timeout=query_dict.get("timeout"),
                start=query_dict.get("start"),
                end=query_dict.get("end"),
                step=query_dict.get("step")
            ))
        return query_objects

    
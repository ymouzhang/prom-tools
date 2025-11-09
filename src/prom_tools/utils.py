"""
Utility functions for prom-tools.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Union, Callable, Awaitable
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


def parse_time_range(
    start: Union[str, datetime, timedelta],
    end: Optional[Union[str, datetime, timedelta]] = None,
) -> tuple[datetime, datetime]:
    """
    Parse time range from various input formats.

    Args:
        start: Start time (datetime, timedelta, or ISO string)
        end: End time (datetime, timedelta, or ISO string, defaults to now)

    Returns:
        Tuple of (start_datetime, end_datetime)
    """
    now = datetime.now()

    if isinstance(start, timedelta):
        start = now - start
    elif isinstance(start, str):
        start = datetime.fromisoformat(start.replace('Z', '+00:00'))

    if end is None:
        end = now
    elif isinstance(end, timedelta):
        end = now - end
    elif isinstance(end, str):
        end = datetime.fromisoformat(end.replace('Z', '+00:00'))

    return start, end


def format_duration(seconds: float) -> str:
    """Format duration in seconds to human readable string."""
    if seconds < 60:
        return f"{seconds:.2f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.2f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.2f}h"


def sanitize_metric_name(name: str) -> str:
    """Sanitize metric name for safe usage."""
    import re
    # Replace invalid characters with underscores
    sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', name)
    # Ensure it doesn't start with underscore or digit
    if sanitized and (sanitized[0].isdigit() or sanitized[0] == '_'):
        sanitized = f"metric_{sanitized}"
    return sanitized


def merge_labels(*label_dicts: Dict[str, str]) -> Dict[str, str]:
    """Merge multiple label dictionaries, with later ones taking precedence."""
    result = {}
    for labels in label_dicts:
        if labels:
            result.update(labels)
    return result


def create_alert_rule(
    name: str,
    expr: str,
    severity: str = "warning",
    summary: Optional[str] = None,
    description: Optional[str] = None,
    labels: Optional[Dict[str, str]] = None,
    annotations: Optional[Dict[str, str]] = None,
    for_duration: str = "5m",
) -> Dict[str, Any]:
    """
    Create a Prometheus alert rule definition.

    Args:
        name: Alert name
        expr: PromQL expression
        severity: Alert severity
        summary: Alert summary
        description: Alert description
        labels: Additional labels
        annotations: Additional annotations
        for_duration: Alert for duration

    Returns:
        Alert rule dictionary
    """
    rule = {
        "alert": name,
        "expr": expr,
        "for": for_duration,
        "labels": {
            "severity": severity,
            **(labels or {}),
        },
        "annotations": {
            "summary": summary or f"Alert: {name}",
            "description": description or f"Alert triggered for {name}",
            **(annotations or {}),
        },
    }

    return rule


def create_recording_rule(
    name: str,
    expr: str,
    labels: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Create a Prometheus recording rule definition.

    Args:
        name: Rule name
        expr: PromQL expression
        labels: Additional labels

    Returns:
        Recording rule dictionary
    """
    rule = {
        "record": name,
        "expr": expr,
        "labels": labels or {},
    }

    return rule


def create_prometheus_rule_group(
    name: str,
    rules: List[Dict[str, Any]],
    interval: str = "1m",
) -> Dict[str, Any]:
    """
    Create a Prometheus rule group.

    Args:
        name: Group name
        rules: List of rules
        interval: Evaluation interval

    Returns:
        Rule group dictionary
    """
    return {
        "name": name,
        "interval": interval,
        "rules": rules,
    }


def create_grafana_dashboard(
    title: str,
    panels: List[Dict[str, Any]],
    tags: Optional[List[str]] = None,
    uid: Optional[str] = None,
    time: Optional[Dict[str, Any]] = None,
    templating: Optional[Dict[str, Any]] = None,
    refresh: str = "30s",
) -> Dict[str, Any]:
    """
    Create a basic Grafana dashboard structure.

    Args:
        title: Dashboard title
        panels: List of panel definitions
        tags: Dashboard tags
        uid: Dashboard UID
        time: Time settings
        templating: Templating settings
        refresh: Refresh interval

    Returns:
        Dashboard dictionary
    """
    dashboard = {
        "id": None,
        "title": title,
        "tags": tags or [],
        "timezone": "browser",
        "panels": panels,
        "time": time or {
            "from": "now-1h",
            "to": "now"
        },
        "refresh": refresh,
        "schemaVersion": 38,
        "version": 1,
        "templating": templating or {"list": []},
    }

    if uid:
        dashboard["uid"] = uid

    return dashboard


def create_grafana_panel(
    title: str,
    expr: str,
    datasource: str,
    type: str = "graph",
    position: Optional[Dict[str, int]] = None,
    description: Optional[str] = None,
    legend_format: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a basic Grafana panel.

    Args:
        title: Panel title
        expr: PromQL expression
        datasource: Datasource name
        type: Panel type
        position: Panel position (gridPos)
        description: Panel description
        legend_format: Legend format

    Returns:
        Panel dictionary
    """
    panel = {
        "id": None,  # Will be assigned by Grafana
        "title": title,
        "type": type,
        "datasource": {"type": "prometheus", "uid": datasource},
        "targets": [
            {
                "expr": expr,
                "legendFormat": legend_format,
                "refId": "A",
            }
        ],
        "gridPos": position or {"x": 0, "y": 0, "w": 12, "h": 8},
    }

    if description:
        panel["description"] = description

    return panel


async def batch_execute(
    tasks: List[Awaitable],
    batch_size: int = 10,
    delay_between_batches: float = 0.1,
) -> List[Any]:
    """
    Execute tasks in batches to avoid overwhelming the system.

    Args:
        tasks: List of awaitable tasks
        batch_size: Number of tasks to execute concurrently
        delay_between_batches: Delay between batches in seconds

    Returns:
        List of results
    """
    results = []

    for i in range(0, len(tasks), batch_size):
        batch = tasks[i:i + batch_size]
        batch_results = await asyncio.gather(*batch, return_exceptions=True)
        results.extend(batch_results)

        # Add delay between batches (except for the last batch)
        if i + batch_size < len(tasks):
            await asyncio.sleep(delay_between_batches)

    return results


def retry_on_failure(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,),
) -> Callable:
    """
    Decorator to retry function calls on failure.

    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries
        backoff: Backoff multiplier
        exceptions: Tuple of exceptions to catch

    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        async def async_wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        logger.warning(
                            f"Attempt {attempt + 1} failed for {func.__name__}: {str(e)}. "
                            f"Retrying in {current_delay}s..."
                        )
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(
                            f"All {max_attempts} attempts failed for {func.__name__}: {str(e)}"
                        )

            raise last_exception

        def sync_wrapper(*args, **kwargs):
            import time
            current_delay = delay
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        logger.warning(
                            f"Attempt {attempt + 1} failed for {func.__name__}: {str(e)}. "
                            f"Retrying in {current_delay}s..."
                        )
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(
                            f"All {max_attempts} attempts failed for {func.__name__}: {str(e)}"
                        )

            raise last_exception

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def export_dashboard_json(
    dashboard_data: Dict[str, Any],
    file_path: Union[str, Path],
    pretty: bool = True,
) -> None:
    """
    Export dashboard to JSON file.

    Args:
        dashboard_data: Dashboard data
        file_path: Output file path
        pretty: Whether to format JSON prettily
    """
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with open(file_path, "w", encoding="utf-8") as f:
        if pretty:
            json.dump(dashboard_data, f, indent=2, ensure_ascii=False)
        else:
            json.dump(dashboard_data, f, ensure_ascii=False)


def load_dashboard_json(
    file_path: Union[str, Path],
) -> Dict[str, Any]:
    """
    Load dashboard from JSON file.

    Args:
        file_path: Input file path

    Returns:
        Dashboard data
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"Dashboard file not found: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)
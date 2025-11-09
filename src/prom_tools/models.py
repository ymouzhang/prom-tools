"""
Optimized data models for Prometheus and Grafana API responses.

Simplified design with clear semantics and no redundancy.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field


class Query(BaseModel):
    """Unified query definition for both instant and range queries."""
    name: Optional[str] = Field(None, description="查询名称")
    query: str = Field(..., description="PromQL查询语句")
    description: Optional[str] = Field(None, description="查询描述")
    category: Optional[str] = Field(None, description="查询分类")
    timeout: Optional[str] = Field(None, description="超时时间")

    # Range query specific fields
    start: Optional[datetime] = Field(None, description="开始时间")
    end: Optional[datetime] = Field(None, description="结束时间")
    step: Optional[Union[str, int]] = Field(None, description="步长")

    def __str__(self) -> str:
        name_str = f"name='{self.name}'" if self.name else "no_name"
        query_type = "RANGE" if self.is_range_query else "INSTANT"
        return f"Query({name_str}, query='{self.query}', type={query_type})"

    @property
    def is_range_query(self) -> bool:
        """Check if this is a range query based on start and end presence."""
        return self.start is not None and self.end is not None

    @property
    def is_instant_query(self) -> bool:
        """Check if this is an instant query."""
        return not self.is_range_query

    @property
    def query_type(self) -> str:
        """Get the query type as string."""
        return "range" if self.is_range_query else "instant"

    @property
    def display_name(self) -> str:
        """Get display name for the query."""
        return self.name or self.query[:50] + ("..." if len(self.query) > 50 else "")

    def get_query_summary(self) -> Dict[str, Any]:
        """Get a summary of the query for logging/debugging."""
        summary = {
            "name": self.name,
            "query": self.query,
            "type": self.query_type,
            "description": self.description,
            "category": self.category
        }

        if self.is_range_query:
            summary.update({
                "start": self.start.isoformat() if self.start else None,
                "end": self.end.isoformat() if self.end else None,
                "step": str(self.step) if self.step else None
            })

        return summary


class Metric(BaseModel):
    """Unified metric model supporting both instant and time series data."""
    name: str = Field(..., description="指标名称")
    labels: Dict[str, str] = Field(default_factory=dict, description="标签")
    value: Optional[float] = Field(None, description="即时值")
    timestamp: Optional[datetime] = Field(None, description="时间戳")
    values: Optional[List[Dict[str, Any]]] = Field(None, description="时间序列数据")

    def __str__(self) -> str:
        if self.value is not None:
            return f"Metric(name='{self.name}', value={self.value})"
        elif self.values:
            return f"Metric(name='{self.name}', points={len(self.values)})"
        else:
            return f"Metric(name='{self.name}')"


class QueryResult(BaseModel):
    """Unified query result model for both instant and range queries."""
    query_name: Optional[str] = Field(None, description="查询名称")
    query: str = Field(..., description="查询语句")
    query_type: str = Field("instant", description="查询类型: instant 或 range")
    success: bool = Field(..., description="是否成功")
    status: str = Field(..., description="查询状态")
    metrics: List[Metric] = Field(default_factory=list, description="指标数据")
    error: Optional[str] = Field(None, description="错误信息")
    execution_time: Optional[float] = Field(None, description="执行时间(秒)")
    data: Optional[Dict[str, Any]] = Field(None, description="原始数据")

    @property
    def metric_count(self) -> int:
        """Get the number of metrics."""
        return len(self.metrics)

    @property
    def display_name(self) -> str:
        """Get display name for the query result."""
        return self.query_name or self.query[:50] + ("..." if len(self.query) > 50 else "")

    @property
    def is_range_query(self) -> bool:
        """Check if this is a range query result."""
        return self.query_type == "range"

    @property
    def is_instant_query(self) -> bool:
        """Check if this is an instant query result."""
        return self.query_type == "instant"

    def get_result_summary(self) -> Dict[str, Any]:
        """Get a summary of the result for logging/debugging."""
        summary = {
            "query_name": self.query_name,
            "query": self.query,
            "query_type": self.query_type,
            "success": self.success,
            "status": self.status,
            "metric_count": self.metric_count,
            "execution_time": self.execution_time
        }

        if not self.success:
            summary["error"] = self.error

        return summary

    def get_metrics_summary(self, limit: int = 3) -> List[Dict[str, Any]]:
        """Get metrics summary for display."""
        summary = []
        for i, metric in enumerate(self.metrics[:limit]):
            labels_str = ", ".join([f"{k}={v}" for k, v in metric.labels.items()])
            summary.append({
                "index": i + 1,
                "name": metric.name,
                "value": metric.value,
                "labels": labels_str,
                "timestamp": metric.timestamp,
                "data_points": len(metric.values) if metric.values else 0
            })
        return summary

    @classmethod
    def from_response(cls, query_name: Optional[str], query: str, response: Dict[str, Any],
                     execution_time: Optional[float] = None, query_type: str = "instant") -> "QueryResult":
        """Create result from Prometheus API response."""
        status = response.get("status", "unknown")

        if status != "success":
            return cls(
                query_name=query_name,
                query=query,
                query_type=query_type,
                success=False,
                status=status,
                error=response.get("error", "Unknown error"),
                execution_time=execution_time,
                data=response
            )

        metrics = []
        if "data" in response:
            data = response["data"]
            result_type = data.get("resultType", "")
            results = data.get("result", [])

            for item in results:
                metric_name = item.get("metric", {}).get("__name__", "unknown")
                labels = {k: v for k, v in item.get("metric", {}).items() if k != "__name__"}

                if result_type == "vector":
                    value_data = item.get("value")
                    if value_data and len(value_data) >= 2:
                        metrics.append(Metric(
                            name=metric_name,
                            labels=labels,
                            value=float(value_data[1]),
                            timestamp=datetime.fromtimestamp(value_data[0])
                        ))

                elif result_type == "matrix":
                    values = []
                    for value_pair in item.get("values", []):
                        if len(value_pair) >= 2:
                            values.append({
                                "timestamp": datetime.fromtimestamp(value_pair[0]),
                                "value": float(value_pair[1])
                            })
                    metrics.append(Metric(
                        name=metric_name,
                        labels=labels,
                        values=values
                    ))

        return cls(
            query_name=query_name,
            query=query,
            query_type=query_type,
            success=True,
            status=status,
            metrics=metrics,
            execution_time=execution_time,
            data=response
        )

    @classmethod
    def from_error(cls, query_name: Optional[str], query: str, error: Exception,
                   execution_time: Optional[float] = None, query_type: str = "instant") -> "QueryResult":
        """Create result from exception."""
        return cls(
            query_name=query_name,
            query=query,
            query_type=query_type,
            success=False,
            status="error",
            error=str(error),
            execution_time=execution_time
        )


# Simplified Grafana models
class GrafanaDashboard(BaseModel):
    """Grafana dashboard model."""
    id: Optional[int] = None
    uid: str = Field(..., description="Dashboard UID")
    title: str = Field(..., description="Dashboard标题")
    tags: List[str] = Field(default_factory=list, description="标签")
    version: Optional[int] = None
    created: Optional[datetime] = None
    updated: Optional[datetime] = None
    folder_id: Optional[int] = None
    folder_title: Optional[str] = None


class GrafanaDatasource(BaseModel):
    """Grafana datasource model."""
    id: int = Field(..., description="数据源ID")
    uid: str = Field(..., description="数据源UID")
    name: str = Field(..., description="数据源名称")
    type: str = Field(..., description="数据源类型")
    url: str = Field(..., description="数据源URL")
    access: str = Field(..., description="访问方式")
    is_default: bool = Field(False, description="是否默认数据源")
    json_data: Dict[str, Any] = Field(default_factory=dict, description="JSON配置")


class GrafanaFolder(BaseModel):
    """Grafana folder model."""
    id: int = Field(..., description="文件夹ID")
    uid: str = Field(..., description="文件夹UID")
    title: str = Field(..., description="文件夹标题")


# Simplified Prometheus management models
class PrometheusTarget(BaseModel):
    """Prometheus target model."""
    instance: str = Field(..., description="目标实例")
    job: str = Field(..., description="作业名称")
    health: str = Field(..., description="健康状态")
    last_error: Optional[str] = None
    scrape_interval: Optional[str] = None
    scrape_timeout: Optional[str] = None
    labels: Dict[str, str] = Field(default_factory=dict)
    discovered_labels: Dict[str, str] = Field(default_factory=dict)
    scrape_pool: Optional[str] = None
    scrape_url: Optional[str] = None
    global_url: Optional[str] = None


class PrometheusRule(BaseModel):
    """Prometheus rule model."""
    name: str = Field(..., description="规则名称")
    type: str = Field(..., description="规则类型")
    state: str = Field(..., description="规则状态")
    health: str = Field(..., description="规则健康状态")



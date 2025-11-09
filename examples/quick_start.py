#!/usr/bin/env python3
"""
Prometheus 快速入门示例
最简洁的使用方式，展示并发查询和结果展示
"""

import asyncio
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from prom_tools import PrometheusClient, Query


async def main():
    """快速入门示例"""
    print("🚀 Prometheus 快速入门示例")
    print("=" * 50)

    # 创建客户端
    client = PrometheusClient(url="http://localhost:9090")

    try:
        # 方式1: 简单字符串查询
        print("\n📝 方式1: 简单字符串查询")
        simple_queries = ["up", "prometheus_build_info", "process_cpu_seconds_total"]

        results = await client.query_multiple(simple_queries)

        print(f"执行了 {len(results)} 个查询:")
        for i, result in enumerate(results, 1):
            if result.success:
                print(f"  ✅ [{i}] {result.query}: {result.metric_count} 个指标")
                # 显示第一个指标的值
                if result.metrics:
                    metric = result.metrics[0]
                    print(f"      💡 示例值: {metric.value:.3f}")
            else:
                print(f"  ❌ [{i}] {result.query}: {result.error}")

        # 方式2: 带名称的查询
        print("\n🏷️  方式2: 带名称的查询")
        named_queries = [
            Query(name="服务状态", query="up"),
            Query(name="CPU使用率", query="rate(process_cpu_seconds_total[5m]) * 100"),
            Query(name="内存使用(MB)", query="process_resident_memory_bytes / 1024 / 1024"),
            Query(name="时间序列数", query="prometheus_tsdb_head_series"),
        ]

        results = await client.query_multiple(named_queries)

        print(f"执行了 {len(results)} 个命名查询:")
        for i, result in enumerate(results, 1):
            if result.success:
                print(f"  ✅ [{i}] {result.query_name}: {result.metric_count} 个指标")
                # 显示前2个指标
                for j, metric in enumerate(result.metrics[:2]):
                    if metric.value is not None:
                        labels_str = ", ".join([f"{k}={v}" for k, v in metric.labels.items()])
                        print(f"      📊 指标{j+1}: {metric.value:.2f} ({labels_str})")
            else:
                print(f"  ❌ [{i}] {result.query_name}: {result.error}")

        # 方式3: 混合查询（即时+范围）
        print("\n⏰ 方式3: 混合查询（即时+范围）")
        from datetime import datetime, timedelta

        end_time = datetime.now()
        start_time = end_time - timedelta(minutes=30)

        mixed_queries = [
            "up",  # 即时查询
            Query(name="CPU趋势", query="rate(process_cpu_seconds_total[5m]) * 100",
                  start=start_time, end=end_time, step="5m"),  # 范围查询
            {
                "name": "内存趋势",
                "query": "process_resident_memory_bytes / 1024 / 1024",
                "start": start_time,
                "end": end_time,
                "step": "10m"
            },  # 字典格式范围查询
        ]

        results = await client.query_multiple(mixed_queries)

        print(f"执行了 {len(results)} 个混合查询:")
        for i, result in enumerate(results, 1):
            if result.success:
                query_type = "范围查询" if any(m.values for m in result.metrics) else "即时查询"
                print(f"  ✅ [{i}] {result.display_name}: {query_type}, {result.metric_count} 个指标")

                # 范围查询显示数据点
                if any(m.values for m in result.metrics):
                    for metric in result.metrics[:1]:  # 只显示第一个指标
                        if metric.values:
                            print(f"      📈 数据点: {len(metric.values)} 个")
                            if len(metric.values) >= 2:
                                first_val = metric.values[0]['value']
                                last_val = metric.values[-1]['value']
                                print(f"      📊 数值范围: {first_val:.2f} -> {last_val:.2f}")
                else:
                    # 即时查询显示当前值
                    for metric in result.metrics[:2]:
                        if metric.value is not None:
                            labels_str = ", ".join([f"{k}={v}" for k, v in metric.labels.items()][:2])
                            print(f"      💡 当前值: {metric.value:.3f} ({labels_str})")
            else:
                print(f"  ❌ [{i}] {result.display_name}: {result.error}")

        print(f"\n🎯 快速入门示例完成!")
        print("💡 提示:")
        print("  - 使用 query_multiple() 进行并发查询")
        print("  - Query 对象可以添加名称和描述")
        print("  - 支持即时查询和范围查询")
        print("  - 字典格式可以定义范围查询参数")

    except Exception as e:
        print(f"❌ 示例执行失败: {e}")
        print("💡 请确保 Prometheus 正在运行在 http://localhost:9090")
    finally:
        await client.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️  用户中断执行")
    except Exception as e:
        print(f"❌ 程序执行出错: {e}")
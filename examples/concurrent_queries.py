#!/usr/bin/env python3
"""
Prometheus 并发查询示例
展示如何使用优化后的 PrometheusClient 进行高效的并发查询
"""

import asyncio
import time
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from prom_tools import PrometheusClient, Query, QueryResult


def setup_logger():
    """设置日志格式"""
    formatter = logging.Formatter(
        fmt='%(asctime)s | %(levelname)-8s | %(filename)s:%(lineno)d | %(funcName)s() | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    logger.addHandler(console_handler)

    return logger


logger = setup_logger()


class QueryDemo:
    def __init__(self):
        self.client = PrometheusClient(url="http://localhost:9090")

    def create_monitoring_queries(self) -> list[Query]:
        """创建监控查询列表"""
        return [
            # 基础服务监控
        Query(name="服务可用性", query="up", description="检查所有服务的在线状态"),
        Query(name="Prometheus版本", query="prometheus_build_info", description="Prometheus版本信息"),

        # 系统性能监控
        Query(name="CPU使用率", query="rate(process_cpu_seconds_total[5m]) * 100", description="CPU使用率百分比"),
        Query(name="内存使用量", query="process_resident_memory_bytes / 1024 / 1024", description="内存使用量(MB)"),
        Query(name="文件描述符", query="process_open_fds", description="打开的文件描述符数量"),

        # HTTP 请求监控
        Query(name="HTTP请求总数", query="prometheus_http_requests_total", description="HTTP请求总数"),
        Query(name="HTTP请求速率", query="sum(rate(prometheus_http_requests_total[5m]))", description="HTTP请求速率"),
        Query(name="请求处理延迟", query="histogram_quantile(0.95, rate(prometheus_http_request_duration_seconds_bucket[5m]))", description="95分位延迟"),

        # 存储监控
        Query(name="时间序列数量", query="prometheus_tsdb_head_series", description="当前时间序列总数"),
        Query(name="内存样本", query="prometheus_tsdb_head_samples_appended_total", description="内存样本总数"),
        Query(name="数据块数量", query="prometheus_tsdb_head_chunks", description="数据块总数"),

        # 网络监控
        Query(name="网络连接数", query="process_net_connections", description="网络连接数"),
        Query(name="网络字节传输", query="rate(process_net_bytes_total[5m])", description="网络字节传输速率"),

        # 聚合分析查询
        Query(name="Top5 CPU使用", query="topk(5, rate(process_cpu_seconds_total[5m]) * 100)", description="CPU使用率最高的5个实例"),
        Query(name="总请求数趋势", query="increase(prometheus_http_requests_total[1h])", description="1小时请求增量"),
    ]
    
    def create_range_queries(self, start_time: datetime, end_time: datetime) -> list[Query]:
        """创建范围查询列表"""
        range_queries = [
            Query(
                name="2小时CPU趋势",
                query="rate(process_cpu_seconds_total[5m]) * 100",
                start=start_time,
                end=end_time,
                step="5m"
            ),
            Query(
                name="2小时内存趋势",
                query="process_resident_memory_bytes / 1024 / 1024",
                start=start_time,
                end=end_time,
                step="10m"
            ),
            Query(
                name="2小时请求速率",
                query="sum(rate(prometheus_http_requests_total[5m]))",
                start=start_time,
                end=end_time,
                step="5m"
            ),
            Query(
                query="up"
            ),
        ]
        return range_queries

    def display_query_result(self, result: QueryResult):
        """展示查询结果"""
        if result.success:
            logger.info(f"✅ {result.display_name}")
            logger.info(f"    查询语句: {result.query}")
            logger.info(f"    执行时间: {result.execution_time:.3f}s")
            logger.info(f"    指标数量: {result.metric_count}")
            logger.info(f"    指标详情:")
            metrics_summary = result.get_metrics_summary(limit=3)
            for metric in metrics_summary:
                if metric['value'] is not None:
                    logger.info(f"      📊 {metric['name']}: {metric['value']:.2f}")
                    if metric['labels']:
                        logger.info(f"         标签: {metric['labels']}")
                else:
                    logger.info(f"      📊 {metric['name']}: 无数据")
            else:
                logger.info("    ⚠️  无指标数据")
        else:
            logger.error(f"❌ {result.display_name}")
            logger.error(f"    查询语句: {result.query}")
            logger.error(f"    错误信息: {result.error}")
            logger.error(f"    执行时间: {result.execution_time:.3f}s")
        logger.info("")  # 空行分隔


    async def concurrent_queries_example(self):
        """并发查询示例"""
        logger.info("🚀 Prometheus 并发查询示例")
        logger.info("=" * 60)
    
        try:
            # 创建查询列表
            queries = self.create_monitoring_queries()
            logger.info(f"准备执行 {len(queries)} 个并发查询:")
    
            for i, query in enumerate(queries, 1):
                logger.info(f"  [{i}] {query}")
    
            logger.info("\n" + "=" * 60)
            logger.info("开始并发执行查询...")
    
            # 执行并发查询
            start_time = time.time()
            results = await self.client.query_multiple(queries, max_concurrent=8)
            total_time = time.time() - start_time
    
            logger.info(f"并发查询完成，总耗时: {total_time:.3f}s\n")
    
            # 统计结果
            successful_results = [r for r in results if r.success]
            failed_results = [r for r in results if not r.success]
    
            logger.info("📊 查询结果统计:")
            logger.info(f"  总查询数: {len(results)}")
            logger.info(f"  成功查询: {len(successful_results)}")
            logger.info(f"  失败查询: {len(failed_results)}")
            logger.info(f"  成功率: {len(successful_results)/len(results)*100:.1f}%")
    
            # 性能统计
            if successful_results:
                execution_times = [r.execution_time for r in successful_results if r.execution_time]
                if execution_times:
                    avg_time = sum(execution_times) / len(execution_times)
                    max_time = max(execution_times)
                    min_time = min(execution_times)
                    logger.info(f"\n⏱️  性能统计:")
                    logger.info(f"  平均执行时间: {avg_time:.3f}s")
                    logger.info(f"  最长执行时间: {max_time:.3f}s")
                    logger.info(f"  最短执行时间: {min_time:.3f}s")
    
            logger.info("\n" + "=" * 60)
            logger.info("详细查询结果:")
            logger.info("=" * 60)
    
            # 显示详细结果
            for result in results:
                self.display_query_result(result)
    
            # 指标汇总统计
            logger.info("📈 指标汇总统计:")
            total_metrics = sum(r.metric_count for r in successful_results)
            logger.info(f"  总指标数: {total_metrics}")
    
            if successful_results:
                # 按查询类型分类统计
                basic_queries = [r for r in successful_results if any(x in r.query.lower() for x in ['up', 'build_info'])]
                performance_queries = [r for r in successful_results if any(x in r.query.lower() for x in ['cpu', 'memory', 'fds'])]
                http_queries = [r for r in successful_results if any(x in r.query.lower() for x in ['http'])]
                storage_queries = [r for r in successful_results if any(x in r.query.lower() for x in ['tsdb'])]
                network_queries = [r for r in successful_results if any(x in r.query.lower() for x in ['net'])]
                aggregate_queries = [r for r in successful_results if any(x in r.query.lower() for x in ['topk', 'increase'])]
    
                logger.info(f"  基础监控: {len(basic_queries)} 个查询")
                logger.info(f"  性能监控: {len(performance_queries)} 个查询")
                logger.info(f"  HTTP监控: {len(http_queries)} 个查询")
                logger.info(f"  存储监控: {len(storage_queries)} 个查询")
                logger.info(f"  网络监控: {len(network_queries)} 个查询")
                logger.info(f"  聚合分析: {len(aggregate_queries)} 个查询")
    
        except Exception as e:
            logger.error(f"并发查询示例执行失败: {e}", exc_info=True)
        finally:
            await self.client.close()
            logger.info("🔚 关闭客户端连接")


    async def range_queries_example(self):
        """范围查询示例"""
        logger.info("\n" + "=" * 60)
        logger.info("📊 范围查询示例")
        logger.info("=" * 60)

        try:
            # 设置时间范围
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=2)

            # 创建范围查询
            range_queries = self.create_range_queries(start_time, end_time)
            logger.info(f"执行 {len(range_queries)} 个范围查询")

            # 执行范围查询
            start_time = time.time()
            results = await self.client.query_multiple(range_queries, max_concurrent=3)
            total_time = time.time() - start_time

            logger.info(f"范围查询完成，总耗时: {total_time:.3f}s\n")

            # 显示范围查询结果
            for i, result in enumerate(results, 1):
                if result.success:
                    logger.info(f"✅ [{i}] {result.display_name}")
                    logger.info(f"    查询: {result.query}")
                    logger.info(f"    执行时间: {result.execution_time:.3f}s")
                logger.info(f"    指标数: {result.metric_count}")

                # 范围查询特有的数据点信息
                # 计算平均值
                if result.is_range_query:
                    if result.metrics:
                        for j, metric in enumerate(result.metrics[:2]):  # 只显示前2个指标
                            if metric.values:
                                values = [float(v['value']) for v in metric.values]
                                avg_value = sum(values) / len(values)
                                logger.info(f"    指标类型: {result.query_type}")
                                logger.info(f"    指标 {j+1}: {len(metric.values)} 个数据点")
                                logger.info(f"      平均值: {avg_value:.2f}")
                # 如果是即时查询，显示最新值
                elif result.is_instant_query:
                    if result.metrics:
                        latest_metric = result.metrics[-1]
                        logger.info(f"    指标类型: {result.query_type}")
                        logger.info(f"    最新值: {latest_metric.value}")

            logger.info("")

        except Exception as e:
            logger.error(f"范围查询示例失败: {e}", exc_info=True)
        finally:
            await self.client.close()


    async def performance_comparison(self):
        """性能对比示例"""
        logger.info("\n" + "=" * 60)
        logger.info("⚡ 性能对比示例")
        logger.info("=" * 60)

        try:
            # 构建 10000 个测试查询
            test_queries = ["up", "prometheus_build_info", "process_cpu_seconds_total", "prometheus_tsdb_head_series"]
            test_queries *= 2500

            # 方法1: 顺序查询
            logger.info(f"方法1: 顺序查询 {len(test_queries)} 个查询")
            start_time = time.time()
            sequential_results = []
            for query in test_queries:
                result = await self.client.query(query)
                sequential_results.append(result)
            sequential_time = time.time() - start_time

            # 方法2: 并发查询
            logger.info(f"方法2: 并发查询 {len(test_queries)} 个查询")
            start_time = time.time()
            concurrent_results = await self.client.query_multiple(test_queries)
            concurrent_time = time.time() - start_time

            # 性能对比
            logger.info(f"\n🏁 性能对比结果:")
            logger.info(f"顺序查询耗时: {sequential_time:.3f}s")
            logger.info(f"并发查询耗时: {concurrent_time:.3f}s")
            if concurrent_time > 0:
                speedup = sequential_time / concurrent_time
                logger.info(f"性能提升倍数: {speedup:.1f}x")

            # 成功率对比
            sequential_success = sum(1 for r in sequential_results if r.success)
            concurrent_success = sum(1 for r in concurrent_results if r.success)

            logger.info(f"\n📊 成功率对比:")
            logger.info(f"顺序查询: {sequential_success}/{len(sequential_results)} ({sequential_success/len(sequential_results)*100:.1f}%)")
            logger.info(f"并发查询: {concurrent_success}/{len(concurrent_results)} ({concurrent_success/len(concurrent_results)*100:.1f}%)")

        except Exception as e:
            logger.error(f"性能对比示例失败: {e}", exc_info=True)
        finally:
            await self.client.close()


async def main():
    """主函数"""
    try:
        demo = QueryDemo()
        # 并发查询示例
        await demo.concurrent_queries_example()

        # 范围查询示例
        await demo.range_queries_example()

        # 性能对比示例
        await demo.performance_comparison()

        logger.info("🎉 所有示例执行完成!")

    except Exception as e:
        logger.error(f"程序执行失败: {e}",exc_info=True)
        logger.error("   请确保 Prometheus 正在运行在 http://localhost:9090")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.warning("用户中断程序执行")
    except Exception as e:
        logger.error(f"程序执行出错: {e}",exc_info=True)
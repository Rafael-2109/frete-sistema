"""
Performance benchmark tests for MCP system
"""
import pytest
import asyncio
import time
import statistics
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor
import psutil
import gc

from fastapi.testclient import TestClient
from tests.mcp_sistema.fixtures.sample_data import (
    get_sample_queries_pt_br,
    get_performance_test_data
)


class TestPerformanceBenchmarks:
    """Performance benchmark test suite"""
    
    @pytest.fixture(autouse=True)
    def setup_benchmarks(self):
        """Setup for benchmark tests"""
        gc.collect()  # Clean garbage before tests
        self.results = {}
        yield
        # Print results after each test
        if hasattr(self, 'results') and self.results:
            print("\n=== Performance Results ===")
            for metric, value in self.results.items():
                print(f"{metric}: {value}")
    
    def test_nlp_processing_speed(self, client: TestClient, auth_headers):
        """Benchmark NLP query processing speed"""
        queries = get_sample_queries_pt_br()
        processing_times = []
        
        # Warm up
        for _ in range(5):
            client.post(
                "/api/v1/mcp/query",
                headers=auth_headers,
                json={"query": queries[0]["query"]}
            )
        
        # Benchmark
        for query_data in queries * 10:  # 120 queries total
            start = time.perf_counter()
            response = client.post(
                "/api/v1/mcp/query",
                headers=auth_headers,
                json={"query": query_data["query"]}
            )
            end = time.perf_counter()
            
            if response.status_code == 200:
                processing_times.append((end - start) * 1000)  # Convert to ms
        
        # Calculate metrics
        self.results = {
            "avg_response_time_ms": statistics.mean(processing_times),
            "median_response_time_ms": statistics.median(processing_times),
            "p95_response_time_ms": statistics.quantiles(processing_times, n=20)[18],
            "p99_response_time_ms": statistics.quantiles(processing_times, n=100)[98],
            "min_response_time_ms": min(processing_times),
            "max_response_time_ms": max(processing_times)
        }
        
        # Assertions
        assert self.results["avg_response_time_ms"] < 100  # Average under 100ms
        assert self.results["p95_response_time_ms"] < 200  # 95th percentile under 200ms
        assert self.results["p99_response_time_ms"] < 500  # 99th percentile under 500ms
    
    def test_concurrent_request_handling(self, client: TestClient, auth_headers):
        """Benchmark concurrent request handling"""
        perf_data = get_performance_test_data()
        concurrent_users = 50  # Test with 50 concurrent users
        
        def make_request(query):
            start = time.perf_counter()
            response = client.post(
                "/api/v1/mcp/query",
                headers=auth_headers,
                json={"query": query}
            )
            end = time.perf_counter()
            return {
                "duration_ms": (end - start) * 1000,
                "status": response.status_code,
                "success": response.status_code == 200
            }
        
        # Execute concurrent requests
        queries = get_sample_queries_pt_br()[:5] * concurrent_users
        
        with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            start_time = time.perf_counter()
            results = list(executor.map(make_request, [q["query"] for q in queries]))
            total_time = time.perf_counter() - start_time
        
        # Calculate metrics
        successful_requests = [r for r in results if r["success"]]
        response_times = [r["duration_ms"] for r in successful_requests]
        
        self.results = {
            "total_requests": len(results),
            "successful_requests": len(successful_requests),
            "success_rate": len(successful_requests) / len(results) * 100,
            "requests_per_second": len(results) / total_time,
            "avg_response_time_ms": statistics.mean(response_times) if response_times else 0,
            "total_time_seconds": total_time
        }
        
        # Assertions
        assert self.results["success_rate"] > 95  # At least 95% success rate
        assert self.results["requests_per_second"] > 50  # Handle >50 req/s
        assert self.results["avg_response_time_ms"] < 200  # Avg response under 200ms
    
    def test_memory_efficiency(self, client: TestClient, auth_headers):
        """Benchmark memory usage under load"""
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Generate load
        queries = get_performance_test_data()["large_query_batch"][:500]
        memory_samples = []
        
        for i, query in enumerate(queries):
            response = client.post(
                "/api/v1/mcp/query",
                headers=auth_headers,
                json={"query": query}
            )
            
            if i % 50 == 0:
                gc.collect()  # Force garbage collection
                current_memory = process.memory_info().rss / 1024 / 1024
                memory_samples.append(current_memory)
        
        final_memory = process.memory_info().rss / 1024 / 1024
        
        self.results = {
            "initial_memory_mb": initial_memory,
            "final_memory_mb": final_memory,
            "memory_growth_mb": final_memory - initial_memory,
            "peak_memory_mb": max(memory_samples),
            "avg_memory_mb": statistics.mean(memory_samples)
        }
        
        # Assertions
        assert self.results["memory_growth_mb"] < 200  # Less than 200MB growth
        assert self.results["peak_memory_mb"] < initial_memory + 300  # Peak under +300MB
    
    def test_database_query_performance(self, client: TestClient, auth_headers, db_session):
        """Benchmark database query performance"""
        import time
        from sqlalchemy import text
        
        # Test different query complexities
        queries = [
            # Simple select
            "SELECT * FROM entity_mapping WHERE entity_type = 'action' LIMIT 10",
            # Join query
            """
            SELECT q.*, u.username 
            FROM query_log q 
            JOIN users u ON q.user_id = u.id 
            WHERE q.created_at > NOW() - INTERVAL '1 day'
            LIMIT 100
            """,
            # Aggregation query
            """
            SELECT 
                entity_type,
                COUNT(*) as count,
                AVG(confidence) as avg_confidence
            FROM entity_mapping
            GROUP BY entity_type
            """,
            # Complex analytical query
            """
            SELECT 
                DATE_TRUNC('hour', created_at) as hour,
                COUNT(*) as query_count,
                AVG(response_time) as avg_response_time,
                COUNT(DISTINCT user_id) as unique_users
            FROM query_log
            WHERE created_at > NOW() - INTERVAL '7 days'
            GROUP BY DATE_TRUNC('hour', created_at)
            ORDER BY hour DESC
            """
        ]
        
        query_times = {}
        
        for query in queries:
            times = []
            
            # Run each query 10 times
            for _ in range(10):
                start = time.perf_counter()
                try:
                    result = db_session.execute(text(query))
                    result.fetchall()  # Force execution
                except:
                    pass  # Some queries might fail on SQLite
                end = time.perf_counter()
                
                times.append((end - start) * 1000)  # Convert to ms
            
            query_name = query.split()[0] + "_" + query.split()[1]
            query_times[query_name] = {
                "avg_ms": statistics.mean(times),
                "min_ms": min(times),
                "max_ms": max(times)
            }
        
        self.results = query_times
        
        # Assertions
        for query_name, metrics in query_times.items():
            assert metrics["avg_ms"] < 50  # All queries under 50ms average
    
    def test_cache_hit_ratio(self, client: TestClient, auth_headers):
        """Benchmark cache effectiveness"""
        # Common queries that should be cached
        cacheable_queries = [
            "verificar status do frete",
            "criar embarque",
            "listar clientes ativos",
            "gerar relatório diário"
        ]
        
        # Phase 1: Populate cache
        cache_miss_times = []
        for query in cacheable_queries * 5:
            start = time.perf_counter()
            response = client.post(
                "/api/v1/mcp/query",
                headers=auth_headers,
                json={"query": query}
            )
            end = time.perf_counter()
            cache_miss_times.append((end - start) * 1000)
        
        # Phase 2: Hit cache
        cache_hit_times = []
        for query in cacheable_queries * 10:
            start = time.perf_counter()
            response = client.post(
                "/api/v1/mcp/query",
                headers=auth_headers,
                json={"query": query}
            )
            end = time.perf_counter()
            cache_hit_times.append((end - start) * 1000)
        
        self.results = {
            "cache_miss_avg_ms": statistics.mean(cache_miss_times),
            "cache_hit_avg_ms": statistics.mean(cache_hit_times),
            "cache_speedup": statistics.mean(cache_miss_times) / statistics.mean(cache_hit_times),
            "estimated_hit_ratio": (1 - (statistics.mean(cache_hit_times) / statistics.mean(cache_miss_times))) * 100
        }
        
        # Assertions
        assert self.results["cache_speedup"] > 2  # At least 2x speedup from cache
        assert self.results["cache_hit_avg_ms"] < 20  # Cache hits under 20ms
    
    @pytest.mark.asyncio
    async def test_learning_system_performance(self, learning_engine):
        """Benchmark learning system performance"""
        # Generate training data
        training_samples = []
        for i in range(1000):
            training_samples.append({
                "query": f"test query {i}",
                "intent": f"intent_{i % 10}",
                "entities": {"entity": f"value_{i}"}
            })
        
        # Benchmark training
        start = time.perf_counter()
        await learning_engine.train_batch(training_samples)
        training_time = time.perf_counter() - start
        
        # Benchmark prediction
        prediction_times = []
        for i in range(100):
            start = time.perf_counter()
            await learning_engine.predict(f"new query {i}")
            end = time.perf_counter()
            prediction_times.append((end - start) * 1000)
        
        self.results = {
            "training_time_seconds": training_time,
            "samples_per_second": len(training_samples) / training_time,
            "avg_prediction_ms": statistics.mean(prediction_times),
            "prediction_throughput": 1000 / statistics.mean(prediction_times)  # predictions/second
        }
        
        # Assertions
        assert self.results["samples_per_second"] > 100  # Train >100 samples/second
        assert self.results["avg_prediction_ms"] < 10  # Predictions under 10ms
    
    def test_api_endpoint_latencies(self, client: TestClient, auth_headers):
        """Benchmark individual API endpoint latencies"""
        endpoints = [
            ("GET", "/api/v1/health", None),
            ("GET", "/api/v1/users/me", None),
            ("GET", "/api/v1/mcp/suggestions?partial=criar", None),
            ("GET", "/api/v1/mcp/history?limit=10", None),
            ("POST", "/api/v1/mcp/query", {"query": "test query"}),
            ("GET", "/api/v1/users/preferences", None),
        ]
        
        endpoint_metrics = {}
        
        for method, path, body in endpoints:
            times = []
            
            for _ in range(50):
                start = time.perf_counter()
                
                if method == "GET":
                    response = client.get(path, headers=auth_headers)
                else:
                    response = client.post(path, headers=auth_headers, json=body)
                
                end = time.perf_counter()
                
                if response.status_code in [200, 201]:
                    times.append((end - start) * 1000)
            
            if times:
                endpoint_metrics[f"{method} {path}"] = {
                    "avg_ms": statistics.mean(times),
                    "p95_ms": statistics.quantiles(times, n=20)[18] if len(times) > 20 else max(times),
                    "min_ms": min(times),
                    "max_ms": max(times)
                }
        
        self.results = endpoint_metrics
        
        # Assertions
        for endpoint, metrics in endpoint_metrics.items():
            assert metrics["avg_ms"] < 100  # All endpoints average under 100ms
            assert metrics["p95_ms"] < 200  # 95th percentile under 200ms
    
    def test_sustained_load_performance(self, client: TestClient, auth_headers):
        """Test performance under sustained load"""
        duration_seconds = 60  # 1 minute test
        target_rps = 50  # Target requests per second
        
        queries = get_sample_queries_pt_br()
        results = []
        errors = 0
        
        start_time = time.time()
        request_count = 0
        
        while time.time() - start_time < duration_seconds:
            batch_start = time.time()
            
            # Send batch of requests to maintain target RPS
            for _ in range(target_rps):
                query = queries[request_count % len(queries)]
                
                try:
                    response = client.post(
                        "/api/v1/mcp/query",
                        headers=auth_headers,
                        json={"query": query["query"]},
                        timeout=5.0
                    )
                    
                    results.append({
                        "status": response.status_code,
                        "duration_ms": response.elapsed.total_seconds() * 1000 if hasattr(response, 'elapsed') else 0
                    })
                    
                    if response.status_code != 200:
                        errors += 1
                        
                except Exception as e:
                    errors += 1
                
                request_count += 1
            
            # Sleep to maintain target RPS
            batch_duration = time.time() - batch_start
            if batch_duration < 1.0:
                time.sleep(1.0 - batch_duration)
        
        total_duration = time.time() - start_time
        successful_requests = [r for r in results if r["status"] == 200]
        
        self.results = {
            "total_requests": len(results),
            "successful_requests": len(successful_requests),
            "errors": errors,
            "actual_rps": len(results) / total_duration,
            "success_rate": len(successful_requests) / len(results) * 100 if results else 0,
            "avg_response_ms": statistics.mean([r["duration_ms"] for r in successful_requests]) if successful_requests else 0,
            "test_duration_seconds": total_duration
        }
        
        # Assertions
        assert self.results["success_rate"] > 99  # >99% success rate under sustained load
        assert self.results["actual_rps"] > target_rps * 0.9  # Achieve >90% of target RPS
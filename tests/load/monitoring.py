"""
Performance Monitoring and Reporting Module
Real-time monitoring and analysis of load test results
"""

import time
import json
import csv
import os
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any
import statistics
import matplotlib.pyplot as plt
import pandas as pd
from collections import defaultdict, deque
import threading
import queue

from .performance_config import (
    PERFORMANCE_THRESHOLDS,
    RESPONSE_TIME_BUCKETS,
    ERROR_CATEGORIES,
    MONITORING_CONFIG
)


class PerformanceMonitor:
    """
    Real-time performance monitoring for load tests.
    Tracks metrics, generates alerts, and creates reports.
    """
    
    def __init__(self, test_name: str = "load_test"):
        self.test_name = test_name
        self.start_time = None
        self.metrics_queue = queue.Queue()
        self.alerts = []
        self.is_monitoring = False
        
        # Metrics storage
        self.response_times = defaultdict(list)
        self.error_counts = defaultdict(int)
        self.request_counts = defaultdict(int)
        self.concurrent_users = deque(maxlen=1000)
        self.throughput_history = deque(maxlen=1000)
        
        # Real-time metrics
        self.current_rps = 0
        self.current_error_rate = 0
        self.current_response_time_avg = 0
        self.current_response_time_p95 = 0
        self.current_response_time_p99 = 0
        
        # Threshold violations
        self.threshold_violations = defaultdict(list)
        
        # Results directory
        self.results_dir = os.path.join(
            MONITORING_CONFIG["results_directory"],
            f"{test_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        os.makedirs(self.results_dir, exist_ok=True)
    
    def start_monitoring(self):
        """Start the monitoring thread"""
        self.is_monitoring = True
        self.start_time = time.time()
        
        # Start monitoring thread
        monitor_thread = threading.Thread(target=self._monitor_loop)
        monitor_thread.daemon = True
        monitor_thread.start()
        
        print(f"Performance monitoring started for test: {self.test_name}")
        print(f"Results will be saved to: {self.results_dir}")
    
    def stop_monitoring(self):
        """Stop monitoring and generate final report"""
        self.is_monitoring = False
        time.sleep(1)  # Allow final metrics to be processed
        
        # Generate reports
        self.generate_final_report()
        self.export_metrics()
        self.generate_visualizations()
        
        print(f"\nMonitoring stopped. Results saved to: {self.results_dir}")
    
    def record_request(self, endpoint: str, method: str, response_time: float, 
                      status_code: int, response_size: int = 0):
        """Record a single request metric"""
        metric = {
            "timestamp": time.time(),
            "endpoint": endpoint,
            "method": method,
            "response_time": response_time,
            "status_code": status_code,
            "response_size": response_size,
            "success": 200 <= status_code < 400
        }
        
        self.metrics_queue.put(metric)
    
    def record_user_count(self, count: int):
        """Record current concurrent user count"""
        self.concurrent_users.append({
            "timestamp": time.time(),
            "count": count
        })
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        last_calculation = time.time()
        metrics_buffer = []
        
        while self.is_monitoring:
            # Collect metrics from queue
            while not self.metrics_queue.empty():
                try:
                    metric = self.metrics_queue.get_nowait()
                    metrics_buffer.append(metric)
                except queue.Empty:
                    break
            
            # Calculate metrics every interval
            current_time = time.time()
            if current_time - last_calculation >= MONITORING_CONFIG["metrics_interval"]:
                self._calculate_metrics(metrics_buffer)
                self._check_thresholds()
                self._save_intermediate_results()
                
                metrics_buffer = []
                last_calculation = current_time
            
            time.sleep(0.1)
    
    def _calculate_metrics(self, metrics: List[Dict]):
        """Calculate current performance metrics"""
        if not metrics:
            return
        
        # Group metrics by endpoint
        endpoint_metrics = defaultdict(list)
        for metric in metrics:
            key = f"{metric['method']} {metric['endpoint']}"
            endpoint_metrics[key].append(metric)
            
            # Store for historical analysis
            self.response_times[key].append(metric['response_time'])
            self.request_counts[key] += 1
            
            if not metric['success']:
                self.error_counts[key] += 1
        
        # Calculate overall metrics
        all_response_times = [m['response_time'] for m in metrics]
        successful_requests = sum(1 for m in metrics if m['success'])
        
        # Current metrics
        self.current_rps = len(metrics) / MONITORING_CONFIG["metrics_interval"]
        self.current_error_rate = 1 - (successful_requests / len(metrics)) if metrics else 0
        self.current_response_time_avg = statistics.mean(all_response_times) if all_response_times else 0
        
        if all_response_times:
            sorted_times = sorted(all_response_times)
            self.current_response_time_p95 = sorted_times[int(len(sorted_times) * 0.95)]
            self.current_response_time_p99 = sorted_times[int(len(sorted_times) * 0.99)]
        
        # Store throughput history
        self.throughput_history.append({
            "timestamp": time.time(),
            "rps": self.current_rps,
            "error_rate": self.current_error_rate
        })
        
        # Print real-time stats
        self._print_real_time_stats()
    
    def _check_thresholds(self):
        """Check if any performance thresholds are violated"""
        current_time = time.time()
        
        # Check error rate
        if self.current_error_rate > PERFORMANCE_THRESHOLDS["error_rate_threshold"]:
            self._add_alert("error_rate", self.current_error_rate, current_time)
        
        # Check response times
        if self.current_response_time_p95 > PERFORMANCE_THRESHOLDS["p95_response_time_ms"]:
            self._add_alert("p95_response_time", self.current_response_time_p95, current_time)
        
        if self.current_response_time_p99 > PERFORMANCE_THRESHOLDS["p99_response_time_ms"]:
            self._add_alert("p99_response_time", self.current_response_time_p99, current_time)
        
        # Check if we're meeting target RPS
        if self.current_rps < PERFORMANCE_THRESHOLDS["target_rps"] * 0.9:  # 90% of target
            self._add_alert("low_throughput", self.current_rps, current_time)
    
    def _add_alert(self, alert_type: str, value: float, timestamp: float):
        """Add an alert for threshold violation"""
        alert = {
            "type": alert_type,
            "value": value,
            "timestamp": timestamp,
            "time_str": datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
        }
        
        self.alerts.append(alert)
        self.threshold_violations[alert_type].append(alert)
        
        # Print alert
        print(f"\n🚨 ALERT: {alert_type} violation - Value: {value:.2f} at {alert['time_str']}")
    
    def _print_real_time_stats(self):
        """Print real-time performance statistics"""
        elapsed = time.time() - self.start_time if self.start_time else 0
        
        print(f"\r⏱️  Elapsed: {elapsed:.0f}s | "
              f"RPS: {self.current_rps:.1f} | "
              f"Errors: {self.current_error_rate*100:.1f}% | "
              f"Avg RT: {self.current_response_time_avg:.0f}ms | "
              f"P95: {self.current_response_time_p95:.0f}ms | "
              f"P99: {self.current_response_time_p99:.0f}ms", 
              end="", flush=True)
    
    def _save_intermediate_results(self):
        """Save intermediate results for recovery"""
        if not MONITORING_CONFIG["persist_results"]:
            return
        
        intermediate_file = os.path.join(self.results_dir, "intermediate_metrics.json")
        
        data = {
            "timestamp": time.time(),
            "current_metrics": {
                "rps": self.current_rps,
                "error_rate": self.current_error_rate,
                "avg_response_time": self.current_response_time_avg,
                "p95_response_time": self.current_response_time_p95,
                "p99_response_time": self.current_response_time_p99
            },
            "alerts": self.alerts[-10:],  # Last 10 alerts
            "request_counts": dict(self.request_counts),
            "error_counts": dict(self.error_counts)
        }
        
        with open(intermediate_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def generate_final_report(self):
        """Generate comprehensive final report"""
        print("\n\n" + "="*80)
        print(f"PERFORMANCE TEST REPORT: {self.test_name}")
        print("="*80)
        
        # Test duration
        duration = time.time() - self.start_time if self.start_time else 0
        print(f"\nTest Duration: {duration:.0f} seconds ({duration/60:.1f} minutes)")
        
        # Overall statistics
        total_requests = sum(self.request_counts.values())
        total_errors = sum(self.error_counts.values())
        overall_error_rate = (total_errors / total_requests * 100) if total_requests > 0 else 0
        
        print(f"\nTotal Requests: {total_requests:,}")
        print(f"Total Errors: {total_errors:,} ({overall_error_rate:.2f}%)")
        print(f"Average RPS: {total_requests / duration:.1f}" if duration > 0 else "N/A")
        
        # Response time statistics
        all_times = []
        for times in self.response_times.values():
            all_times.extend(times)
        
        if all_times:
            print(f"\nResponse Time Statistics:")
            print(f"  Min: {min(all_times):.0f}ms")
            print(f"  Avg: {statistics.mean(all_times):.0f}ms")
            print(f"  Median: {statistics.median(all_times):.0f}ms")
            print(f"  P95: {sorted(all_times)[int(len(all_times) * 0.95)]:.0f}ms")
            print(f"  P99: {sorted(all_times)[int(len(all_times) * 0.99)]:.0f}ms")
            print(f"  Max: {max(all_times):.0f}ms")
        
        # Top slowest endpoints
        print("\nTop 5 Slowest Endpoints (by average response time):")
        endpoint_avg_times = {}
        for endpoint, times in self.response_times.items():
            if times:
                endpoint_avg_times[endpoint] = statistics.mean(times)
        
        for endpoint, avg_time in sorted(endpoint_avg_times.items(), 
                                       key=lambda x: x[1], reverse=True)[:5]:
            print(f"  {endpoint}: {avg_time:.0f}ms")
        
        # Top error endpoints
        print("\nTop 5 Error-Prone Endpoints:")
        endpoint_error_rates = {}
        for endpoint in self.request_counts:
            if self.request_counts[endpoint] > 0:
                error_rate = self.error_counts[endpoint] / self.request_counts[endpoint]
                endpoint_error_rates[endpoint] = error_rate
        
        for endpoint, error_rate in sorted(endpoint_error_rates.items(), 
                                         key=lambda x: x[1], reverse=True)[:5]:
            if error_rate > 0:
                print(f"  {endpoint}: {error_rate*100:.1f}% errors")
        
        # Threshold violations
        print("\nThreshold Violations:")
        if self.threshold_violations:
            for violation_type, violations in self.threshold_violations.items():
                print(f"  {violation_type}: {len(violations)} violations")
        else:
            print("  ✅ No threshold violations!")
        
        # Performance verdict
        print("\nPerformance Verdict:")
        if overall_error_rate <= PERFORMANCE_THRESHOLDS["error_rate_threshold"] * 100:
            print("  ✅ Error rate: PASS")
        else:
            print("  ❌ Error rate: FAIL")
        
        if total_requests / duration >= PERFORMANCE_THRESHOLDS["target_rps"]:
            print("  ✅ Throughput: PASS")
        else:
            print("  ❌ Throughput: FAIL")
        
        # Save full report
        report_file = os.path.join(self.results_dir, "final_report.txt")
        with open(report_file, 'w') as f:
            # Redirect print to file
            import sys
            original_stdout = sys.stdout
            sys.stdout = f
            
            # Re-print everything to file
            self.generate_final_report.__wrapped__(self)
            
            sys.stdout = original_stdout
        
        print(f"\nFull report saved to: {report_file}")
        print("="*80)
    
    def export_metrics(self):
        """Export metrics in various formats"""
        # JSON export
        json_file = os.path.join(self.results_dir, "metrics.json")
        metrics_data = {
            "test_name": self.test_name,
            "start_time": self.start_time,
            "duration": time.time() - self.start_time if self.start_time else 0,
            "total_requests": sum(self.request_counts.values()),
            "total_errors": sum(self.error_counts.values()),
            "endpoints": {
                endpoint: {
                    "requests": self.request_counts[endpoint],
                    "errors": self.error_counts[endpoint],
                    "avg_response_time": statistics.mean(self.response_times[endpoint]) 
                                       if self.response_times[endpoint] else 0
                }
                for endpoint in self.request_counts
            },
            "alerts": self.alerts,
            "throughput_history": list(self.throughput_history)
        }
        
        with open(json_file, 'w') as f:
            json.dump(metrics_data, f, indent=2)
        
        # CSV export for endpoint metrics
        csv_file = os.path.join(self.results_dir, "endpoint_metrics.csv")
        with open(csv_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Endpoint", "Requests", "Errors", "Error Rate", 
                           "Avg Response Time", "P95", "P99"])
            
            for endpoint in self.request_counts:
                times = self.response_times[endpoint]
                if times:
                    sorted_times = sorted(times)
                    p95 = sorted_times[int(len(sorted_times) * 0.95)]
                    p99 = sorted_times[int(len(sorted_times) * 0.99)]
                else:
                    p95 = p99 = 0
                
                writer.writerow([
                    endpoint,
                    self.request_counts[endpoint],
                    self.error_counts[endpoint],
                    f"{self.error_counts[endpoint] / self.request_counts[endpoint] * 100:.2f}%",
                    f"{statistics.mean(times):.0f}" if times else "0",
                    f"{p95:.0f}",
                    f"{p99:.0f}"
                ])
        
        print(f"Metrics exported to: {json_file} and {csv_file}")
    
    def generate_visualizations(self):
        """Generate performance visualization charts"""
        if not self.throughput_history:
            return
        
        # Prepare data
        timestamps = [item["timestamp"] for item in self.throughput_history]
        start_time = timestamps[0] if timestamps else 0
        relative_times = [(t - start_time) / 60 for t in timestamps]  # Convert to minutes
        rps_values = [item["rps"] for item in self.throughput_history]
        error_rates = [item["error_rate"] * 100 for item in self.throughput_history]
        
        # Create figure with subplots
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle(f'Performance Test Results: {self.test_name}', fontsize=16)
        
        # Plot 1: Throughput over time
        ax1 = axes[0, 0]
        ax1.plot(relative_times, rps_values, 'b-', label='Actual RPS')
        ax1.axhline(y=PERFORMANCE_THRESHOLDS["target_rps"], color='r', 
                   linestyle='--', label=f'Target RPS ({PERFORMANCE_THRESHOLDS["target_rps"]})')
        ax1.set_xlabel('Time (minutes)')
        ax1.set_ylabel('Requests Per Second')
        ax1.set_title('Throughput Over Time')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Plot 2: Error rate over time
        ax2 = axes[0, 1]
        ax2.plot(relative_times, error_rates, 'r-', label='Error Rate')
        ax2.axhline(y=PERFORMANCE_THRESHOLDS["error_rate_threshold"] * 100, 
                   color='g', linestyle='--', 
                   label=f'Threshold ({PERFORMANCE_THRESHOLDS["error_rate_threshold"]*100}%)')
        ax2.set_xlabel('Time (minutes)')
        ax2.set_ylabel('Error Rate (%)')
        ax2.set_title('Error Rate Over Time')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # Plot 3: Response time distribution
        ax3 = axes[1, 0]
        all_times = []
        for times in self.response_times.values():
            all_times.extend(times)
        
        if all_times:
            ax3.hist(all_times, bins=50, alpha=0.7, color='green', edgecolor='black')
            ax3.axvline(x=PERFORMANCE_THRESHOLDS["max_response_time_ms"], 
                       color='r', linestyle='--', 
                       label=f'Threshold ({PERFORMANCE_THRESHOLDS["max_response_time_ms"]}ms)')
            ax3.set_xlabel('Response Time (ms)')
            ax3.set_ylabel('Frequency')
            ax3.set_title('Response Time Distribution')
            ax3.legend()
            ax3.grid(True, alpha=0.3)
        
        # Plot 4: Concurrent users
        ax4 = axes[1, 1]
        if self.concurrent_users:
            user_timestamps = [item["timestamp"] for item in self.concurrent_users]
            user_counts = [item["count"] for item in self.concurrent_users]
            user_times = [(t - start_time) / 60 for t in user_timestamps]
            ax4.plot(user_times, user_counts, 'purple', label='Concurrent Users')
            ax4.set_xlabel('Time (minutes)')
            ax4.set_ylabel('Number of Users')
            ax4.set_title('Concurrent Users Over Time')
            ax4.legend()
            ax4.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # Save visualization
        viz_file = os.path.join(self.results_dir, "performance_visualization.png")
        plt.savefig(viz_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"Visualization saved to: {viz_file}")
        
        # Generate response time percentile chart
        self._generate_percentile_chart()
    
    def _generate_percentile_chart(self):
        """Generate response time percentile chart"""
        # Collect all response times by endpoint
        fig, ax = plt.subplots(figsize=(12, 6))
        
        endpoints = list(self.response_times.keys())[:10]  # Top 10 endpoints
        percentiles = [50, 75, 90, 95, 99]
        
        data = []
        for endpoint in endpoints:
            times = sorted(self.response_times[endpoint])
            if times:
                row = [endpoint]
                for p in percentiles:
                    idx = int(len(times) * p / 100)
                    row.append(times[min(idx, len(times)-1)])
                data.append(row)
        
        if data:
            df = pd.DataFrame(data, columns=['Endpoint'] + [f'P{p}' for p in percentiles])
            df.set_index('Endpoint').plot(kind='bar', ax=ax)
            
            ax.set_ylabel('Response Time (ms)')
            ax.set_title('Response Time Percentiles by Endpoint')
            ax.legend(title='Percentile')
            plt.xticks(rotation=45, ha='right')
            
            plt.tight_layout()
            
            percentile_file = os.path.join(self.results_dir, "response_time_percentiles.png")
            plt.savefig(percentile_file, dpi=300, bbox_inches='tight')
            plt.close()
            
            print(f"Percentile chart saved to: {percentile_file}")


# Convenience function for monitoring
def start_performance_monitoring(test_name: str) -> PerformanceMonitor:
    """Start performance monitoring for a load test"""
    monitor = PerformanceMonitor(test_name)
    monitor.start_monitoring()
    return monitor
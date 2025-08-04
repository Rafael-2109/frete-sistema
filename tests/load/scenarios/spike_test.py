"""
Spike Testing Scenario
Tests system behavior under sudden traffic spikes and load variations
"""

from locust import HttpUser, task, between, constant, LoadTestShape
import random
import math
import time
from datetime import datetime, timedelta
import json

from ..performance_config import (
    LOAD_TEST_CONFIG,
    PERFORMANCE_THRESHOLDS,
    API_ENDPOINTS
)


class SpikeTestUser(HttpUser):
    """
    User class for spike testing scenarios.
    Simulates sudden bursts of traffic and varying load patterns.
    """
    
    wait_time = between(0.1, 1)  # Very short wait times during spikes
    host = LOAD_TEST_CONFIG["base_url"]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.spike_mode = False
        self.request_count = 0
        self.error_count = 0
        self.slow_requests = 0
    
    def on_start(self):
        """Initialize spike test user"""
        self.authenticate()
        self.spike_threshold = PERFORMANCE_THRESHOLDS["max_response_time_ms"] * 2
    
    def authenticate(self):
        """Quick authentication for spike testing"""
        auth_response = self.client.post(
            "/api/auth/quick-token",
            json={"test_user": f"spike_{random.randint(1, 10000)}"},
            catch_response=True
        )
        
        if auth_response.status_code == 200:
            token = auth_response.json().get("token")
            self.client.headers["Authorization"] = f"Bearer {token}"
            auth_response.success()
        else:
            # Continue without auth for spike testing
            auth_response.failure("Auth failed during spike")
    
    @task(40)
    def spike_read_operations(self):
        """High-frequency read operations during spike"""
        endpoints = [
            "/api/orders",
            f"/api/orders/{random.randint(1, 1000)}",
            "/api/orders/recent",
            "/api/stats/live",
            "/api/health"
        ]
        
        endpoint = random.choice(endpoints)
        
        start_time = time.time()
        with self.client.get(
            endpoint,
            catch_response=True,
            name=f"[SPIKE] GET {endpoint.split('/')[-1]}"
        ) as response:
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                response.success()
                if response_time > self.spike_threshold:
                    self.slow_requests += 1
            else:
                response.failure(f"Spike failure: {response.status_code}")
                self.error_count += 1
        
        self.request_count += 1
    
    @task(25)
    def spike_write_operations(self):
        """Write operations during spike to test system under pressure"""
        operations = [
            self._spike_create_order,
            self._spike_update_status,
            self._spike_calculate_freight,
            self._spike_add_tracking
        ]
        
        operation = random.choice(operations)
        operation()
        self.request_count += 1
    
    @task(15)
    def spike_search_operations(self):
        """Complex search operations during spike"""
        search_types = [
            {"endpoint": "/api/orders/search", "params": {"q": f"TEST{random.randint(1000, 9999)}"}},
            {"endpoint": "/api/customers/search", "params": {"name": f"User{random.randint(1, 100)}"}},
            {"endpoint": "/api/tracking/search", "params": {"date": datetime.utcnow().strftime("%Y-%m-%d")}}
        ]
        
        search = random.choice(search_types)
        
        with self.client.get(
            search["endpoint"],
            params=search["params"],
            catch_response=True,
            name=f"[SPIKE] SEARCH {search['endpoint'].split('/')[-1]}"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Search spike failure: {response.status_code}")
                self.error_count += 1
        
        self.request_count += 1
    
    @task(10)
    def spike_bulk_operations(self):
        """Bulk operations to stress test during spike"""
        bulk_size = random.randint(20, 50) if self.spike_mode else random.randint(5, 15)
        
        bulk_data = {
            "operations": [
                {
                    "type": random.choice(["create", "update", "delete"]),
                    "entity": random.choice(["order", "tracking", "notification"]),
                    "data": {"id": f"SPIKE-{i}", "timestamp": datetime.utcnow().isoformat()}
                }
                for i in range(bulk_size)
            ]
        }
        
        with self.client.post(
            "/api/bulk/operations",
            json=bulk_data,
            catch_response=True,
            name="[SPIKE] BULK Operations"
        ) as response:
            if response.status_code in [200, 201, 202]:
                response.success()
            else:
                response.failure(f"Bulk spike failure: {response.status_code}")
                self.error_count += 1
        
        self.request_count += 1
    
    @task(5)
    def spike_cache_buster(self):
        """Operations designed to bypass cache during spike"""
        # Unique parameters to avoid cache hits
        unique_id = f"{time.time()}_{random.randint(10000, 99999)}"
        
        operations = [
            lambda: self.client.get(
                f"/api/orders?cb={unique_id}&limit={random.randint(1, 100)}",
                name="[SPIKE] Cache Buster GET"
            ),
            lambda: self.client.post(
                "/api/freight/calculate",
                json={
                    "unique_id": unique_id,
                    "origin": f"{random.randint(10000, 99999)}-{random.randint(100, 999)}",
                    "destination": f"{random.randint(10000, 99999)}-{random.randint(100, 999)}",
                    "weight": random.uniform(0.1, 1000)
                },
                name="[SPIKE] Cache Buster POST"
            )
        ]
        
        operation = random.choice(operations)
        with operation() as response:
            if response.status_code in [200, 201]:
                response.success()
            else:
                response.failure(f"Cache buster failure: {response.status_code}")
        
        self.request_count += 1
    
    @task(3)
    def spike_heavy_computation(self):
        """Request heavy computation endpoints during spike"""
        heavy_endpoints = [
            {
                "url": "/api/reports/generate",
                "data": {
                    "type": "comprehensive",
                    "date_range": "last_year",
                    "include_graphs": True
                }
            },
            {
                "url": "/api/analytics/calculate",
                "data": {
                    "metrics": ["revenue", "orders", "performance"],
                    "period": "all_time",
                    "grouping": "daily"
                }
            },
            {
                "url": "/api/optimization/route",
                "data": {
                    "orders": [f"ORD-{i}" for i in range(random.randint(50, 100))],
                    "constraints": ["time", "distance", "cost"]
                }
            }
        ]
        
        endpoint = random.choice(heavy_endpoints)
        
        with self.client.post(
            endpoint["url"],
            json=endpoint["data"],
            catch_response=True,
            timeout=30,  # Longer timeout for heavy operations
            name=f"[SPIKE] HEAVY {endpoint['url'].split('/')[-1]}"
        ) as response:
            if response.status_code in [200, 201, 202]:
                response.success()
            else:
                response.failure(f"Heavy operation failure: {response.status_code}")
        
        self.request_count += 1
    
    def _spike_create_order(self):
        """Create order during spike"""
        order_data = {
            "type": "spike_test",
            "priority": "urgent",
            "customer_id": f"SPIKE-{random.randint(1, 1000)}",
            "items": [
                {"name": f"Item-{i}", "qty": 1}
                for i in range(random.randint(1, 3))
            ],
            "created_at": datetime.utcnow().isoformat()
        }
        
        with self.client.post(
            "/api/orders",
            json=order_data,
            catch_response=True,
            name="[SPIKE] CREATE Order"
        ) as response:
            if response.status_code == 201:
                response.success()
            else:
                response.failure(f"Create spike failure: {response.status_code}")
                self.error_count += 1
    
    def _spike_update_status(self):
        """Update status during spike"""
        with self.client.patch(
            f"/api/orders/{random.randint(1, 1000)}/status",
            json={"status": "spike_test", "timestamp": time.time()},
            catch_response=True,
            name="[SPIKE] UPDATE Status"
        ) as response:
            if response.status_code in [200, 404]:
                response.success()
            else:
                response.failure(f"Update spike failure: {response.status_code}")
                self.error_count += 1
    
    def _spike_calculate_freight(self):
        """Calculate freight during spike"""
        with self.client.post(
            "/api/freight/quick-calc",
            json={
                "distance": random.randint(10, 1000),
                "weight": random.uniform(1, 100),
                "urgent": True
            },
            catch_response=True,
            name="[SPIKE] CALC Freight"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Calc spike failure: {response.status_code}")
                self.error_count += 1
    
    def _spike_add_tracking(self):
        """Add tracking during spike"""
        with self.client.post(
            "/api/tracking/events",
            json={
                "order_id": f"ORD-{random.randint(1, 1000)}",
                "event": "spike_test",
                "timestamp": datetime.utcnow().isoformat()
            },
            catch_response=True,
            name="[SPIKE] ADD Tracking"
        ) as response:
            if response.status_code in [200, 201]:
                response.success()
            else:
                response.failure(f"Tracking spike failure: {response.status_code}")
                self.error_count += 1
    
    def on_stop(self):
        """Report spike test statistics"""
        if self.request_count > 0:
            error_rate = (self.error_count / self.request_count) * 100
            slow_rate = (self.slow_requests / self.request_count) * 100
            
            print(f"\nSpike Test User Stats:")
            print(f"Total Requests: {self.request_count}")
            print(f"Errors: {self.error_count} ({error_rate:.2f}%)")
            print(f"Slow Requests: {self.slow_requests} ({slow_rate:.2f}%)")


class SpikeLoadShape(LoadTestShape):
    """
    Custom load shape for spike testing.
    Creates sudden spikes in traffic to test system resilience.
    """
    
    # Spike pattern configuration
    spike_patterns = [
        # Pattern 1: Gradual build-up with sudden spike
        {"time": 0, "users": 10, "spawn_rate": 5},       # Start low
        {"time": 60, "users": 50, "spawn_rate": 10},     # Gradual increase
        {"time": 120, "users": 500, "spawn_rate": 100},  # SPIKE!
        {"time": 150, "users": 50, "spawn_rate": 50},    # Quick drop
        {"time": 180, "users": 100, "spawn_rate": 20},   # Stabilize
        
        # Pattern 2: Multiple rapid spikes
        {"time": 240, "users": 300, "spawn_rate": 100},  # Spike 1
        {"time": 260, "users": 100, "spawn_rate": 50},   # Drop
        {"time": 280, "users": 400, "spawn_rate": 100},  # Spike 2
        {"time": 300, "users": 150, "spawn_rate": 50},   # Drop
        {"time": 320, "users": 600, "spawn_rate": 150},  # Spike 3 (biggest)
        {"time": 340, "users": 200, "spawn_rate": 100},  # Drop
        
        # Pattern 3: Sustained high load with fluctuations
        {"time": 400, "users": 400, "spawn_rate": 50},   # High baseline
        {"time": 430, "users": 600, "spawn_rate": 100},  # Spike
        {"time": 450, "users": 400, "spawn_rate": 50},   # Return to baseline
        {"time": 470, "users": 700, "spawn_rate": 100},  # Higher spike
        {"time": 490, "users": 400, "spawn_rate": 50},   # Return to baseline
        
        # Pattern 4: Extreme spike (testing breaking point)
        {"time": 540, "users": 100, "spawn_rate": 20},   # Normal load
        {"time": 570, "users": 1000, "spawn_rate": 200}, # EXTREME SPIKE!
        {"time": 590, "users": 1200, "spawn_rate": 100}, # Push further
        {"time": 610, "users": 100, "spawn_rate": 200},  # Rapid cool down
        
        # Cool down
        {"time": 660, "users": 50, "spawn_rate": 20},    # Wind down
        {"time": 720, "users": 0, "spawn_rate": 10},     # End
    ]
    
    def tick(self):
        """Calculate current user count and spawn rate based on spike patterns"""
        run_time = self.get_run_time()
        
        # Find the appropriate stage based on current time
        for i, stage in enumerate(self.spike_patterns):
            if i == len(self.spike_patterns) - 1:  # Last stage
                if run_time >= stage["time"]:
                    if stage["users"] == 0:
                        return None  # End test
                    return (stage["users"], stage["spawn_rate"])
            else:
                next_stage = self.spike_patterns[i + 1]
                if stage["time"] <= run_time < next_stage["time"]:
                    # Interpolate between stages for smoother transitions
                    progress = (run_time - stage["time"]) / (next_stage["time"] - stage["time"])
                    
                    if next_stage["users"] > stage["users"] * 2:  # This is a spike
                        # Exponential growth for spikes
                        users = int(stage["users"] * math.pow(next_stage["users"] / stage["users"], progress))
                    else:
                        # Linear interpolation for normal transitions
                        users = int(stage["users"] + (next_stage["users"] - stage["users"]) * progress)
                    
                    spawn_rate = max(stage["spawn_rate"], next_stage["spawn_rate"])
                    return (users, spawn_rate)
        
        return None


class AdaptiveSpikeUser(SpikeTestUser):
    """
    Advanced spike test user that adapts behavior based on system response.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.response_times = []
        self.adaptive_wait = between(0.1, 1)
    
    @task
    def adaptive_spike_load(self):
        """Adjust request pattern based on system performance"""
        # Monitor last 10 response times
        if len(self.response_times) > 10:
            avg_response = sum(self.response_times[-10:]) / 10
            
            if avg_response > 1000:  # System is slow
                # Back off slightly
                self.wait_time = between(1, 3)
                self._lightweight_operation()
            elif avg_response < 200:  # System is fast
                # Increase pressure
                self.wait_time = constant(0.1)
                self._heavy_operation()
            else:
                # Normal operation
                self.wait_time = self.adaptive_wait
                self._normal_operation()
    
    def _lightweight_operation(self):
        """Lightweight operation when system is under stress"""
        start = time.time()
        with self.client.get(
            "/api/health",
            catch_response=True,
            name="[ADAPTIVE] Light Op"
        ) as response:
            self.response_times.append((time.time() - start) * 1000)
            if response.status_code == 200:
                response.success()
    
    def _normal_operation(self):
        """Normal operation"""
        operations = [
            lambda: self.client.get("/api/orders?limit=20", name="[ADAPTIVE] Normal GET"),
            lambda: self.client.post("/api/freight/calculate", json={"weight": 50}, name="[ADAPTIVE] Normal POST")
        ]
        
        start = time.time()
        op = random.choice(operations)
        with op() as response:
            self.response_times.append((time.time() - start) * 1000)
            if response.status_code in [200, 201]:
                response.success()
    
    def _heavy_operation(self):
        """Heavy operation when system is responding well"""
        start = time.time()
        with self.client.post(
            "/api/bulk/process",
            json={"items": [{"id": i} for i in range(50)]},
            catch_response=True,
            name="[ADAPTIVE] Heavy Op"
        ) as response:
            self.response_times.append((time.time() - start) * 1000)
            if response.status_code in [200, 201, 202]:
                response.success()
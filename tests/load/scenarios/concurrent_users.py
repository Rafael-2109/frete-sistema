"""
Concurrent Users Load Testing Scenario
Tests system behavior with high concurrent user load
"""

from locust import HttpUser, TaskSet, task, between, constant_pacing, LoadTestShape
import random
import time
from datetime import datetime
import threading
import queue
import json

from ..performance_config import LOAD_TEST_CONFIG, PERFORMANCE_THRESHOLDS


class ConcurrentUserBehavior(TaskSet):
    """
    Simulates realistic concurrent user behavior patterns.
    Multiple users performing different actions simultaneously.
    """
    
    def on_start(self):
        """Initialize user session"""
        self.user_type = random.choice(["customer", "driver", "admin", "api_client"])
        self.session_start = time.time()
        self.actions_performed = 0
        self.authenticate_user()
    
    def authenticate_user(self):
        """Authenticate based on user type"""
        auth_endpoints = {
            "customer": "/api/auth/customer/login",
            "driver": "/api/auth/driver/login",
            "admin": "/api/auth/admin/login",
            "api_client": "/api/auth/token"
        }
        
        auth_data = {
            "customer": {
                "email": f"customer{random.randint(1, 1000)}@test.com",
                "password": "test123"
            },
            "driver": {
                "phone": f"+5511{random.randint(90000000, 99999999)}",
                "password": "driver123"
            },
            "admin": {
                "username": f"admin{random.randint(1, 10)}",
                "password": "admin123"
            },
            "api_client": {
                "client_id": f"client_{random.randint(1, 100)}",
                "client_secret": "secret123",
                "grant_type": "client_credentials"
            }
        }
        
        response = self.client.post(
            auth_endpoints[self.user_type],
            json=auth_data[self.user_type],
            catch_response=True
        )
        
        if response.status_code == 200:
            token = response.json().get("token") or response.json().get("access_token")
            self.client.headers["Authorization"] = f"Bearer {token}"
            response.success()
        else:
            response.failure(f"Auth failed for {self.user_type}")
    
    @task(30)
    def concurrent_read_operations(self):
        """Multiple concurrent read operations"""
        read_operations = [
            lambda: self.client.get("/api/orders", name="[CONCURRENT] List Orders"),
            lambda: self.client.get(f"/api/orders/{random.randint(1, 1000)}", name="[CONCURRENT] Get Order"),
            lambda: self.client.get("/api/tracking/latest", name="[CONCURRENT] Latest Tracking"),
            lambda: self.client.get("/api/notifications", name="[CONCURRENT] Notifications"),
            lambda: self.client.get("/api/stats/summary", name="[CONCURRENT] Stats Summary")
        ]
        
        # Perform 2-5 concurrent reads
        num_operations = random.randint(2, 5)
        selected_ops = random.sample(read_operations, num_operations)
        
        # Execute operations concurrently
        threads = []
        for op in selected_ops:
            thread = threading.Thread(target=self._execute_operation, args=(op,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=5)
        
        self.actions_performed += num_operations
    
    @task(20)
    def concurrent_write_operations(self):
        """Multiple concurrent write operations"""
        write_operations = [
            lambda: self._create_order(),
            lambda: self._update_order_status(),
            lambda: self._add_tracking_event(),
            lambda: self._update_user_preferences(),
            lambda: self._create_notification()
        ]
        
        # Perform 1-3 concurrent writes
        num_operations = random.randint(1, 3)
        selected_ops = random.sample(write_operations, num_operations)
        
        # Execute with slight delays to avoid conflicts
        threads = []
        for i, op in enumerate(selected_ops):
            thread = threading.Thread(target=self._execute_operation, args=(op,))
            threads.append(thread)
            thread.start()
            time.sleep(0.1 * i)  # Small delay between writes
        
        # Wait for completion
        for thread in threads:
            thread.join(timeout=5)
        
        self.actions_performed += num_operations
    
    @task(15)
    def concurrent_mixed_operations(self):
        """Mix of read and write operations happening concurrently"""
        operations = []
        
        # Add read operations
        for _ in range(random.randint(2, 4)):
            operations.append(
                lambda: self.client.get(
                    f"/api/orders?page={random.randint(1, 10)}",
                    name="[MIXED] Read Orders"
                )
            )
        
        # Add write operations
        operations.append(lambda: self._create_order())
        operations.append(lambda: self._calculate_freight())
        
        # Shuffle to mix reads and writes
        random.shuffle(operations)
        
        # Execute concurrently
        threads = []
        for op in operations:
            thread = threading.Thread(target=self._execute_operation, args=(op,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join(timeout=5)
        
        self.actions_performed += len(operations)
    
    @task(10)
    def search_with_concurrent_filters(self):
        """Complex search with multiple concurrent filter applications"""
        base_search = "/api/orders/search"
        
        # Different filter combinations
        filters = [
            {"status": random.choice(["pending", "in_transit", "delivered"])},
            {"date_from": "2024-01-01", "date_to": "2024-12-31"},
            {"customer": f"CUST-{random.randint(1, 100):05d}"},
            {"city": random.choice(["São Paulo", "Rio de Janeiro", "Brasília"])},
            {"min_value": random.randint(100, 1000), "max_value": random.randint(5000, 10000)}
        ]
        
        # Apply 2-4 filters concurrently
        num_filters = random.randint(2, 4)
        selected_filters = random.sample(filters, num_filters)
        
        # Execute searches concurrently
        threads = []
        for filter_params in selected_filters:
            thread = threading.Thread(
                target=self._execute_search,
                args=(base_search, filter_params)
            )
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join(timeout=5)
    
    @task(8)
    def concurrent_report_generation(self):
        """Generate multiple reports concurrently"""
        report_types = [
            ("daily", "pdf"),
            ("weekly", "excel"),
            ("monthly", "json"),
            ("custom", "csv")
        ]
        
        # Generate 2-3 reports concurrently
        num_reports = random.randint(2, 3)
        selected_reports = random.sample(report_types, num_reports)
        
        threads = []
        for report_type, format_type in selected_reports:
            thread = threading.Thread(
                target=self._generate_report,
                args=(report_type, format_type)
            )
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join(timeout=10)  # Reports may take longer
    
    @task(5)
    def websocket_simulation_concurrent(self):
        """Simulate concurrent WebSocket-like connections"""
        num_connections = random.randint(3, 5)
        
        threads = []
        for i in range(num_connections):
            thread = threading.Thread(
                target=self._simulate_websocket,
                args=(f"ws_conn_{i}",)
            )
            threads.append(thread)
            thread.start()
        
        # Let connections run for a bit
        time.sleep(random.uniform(2, 5))
        
        # Clean up
        for thread in threads:
            thread.join(timeout=1)
    
    @task(3)
    def bulk_operations_concurrent(self):
        """Perform bulk operations with concurrent processing"""
        bulk_ops = [
            self._bulk_create_orders,
            self._bulk_update_statuses,
            self._bulk_assign_drivers
        ]
        
        # Run 2 bulk operations concurrently
        selected_ops = random.sample(bulk_ops, 2)
        
        threads = []
        for op in selected_ops:
            thread = threading.Thread(target=op)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join(timeout=10)
    
    def _execute_operation(self, operation):
        """Execute an operation with error handling"""
        try:
            with self.client.get(
                "/api/health",
                catch_response=True,
                name="[CONCURRENT] Health Check"
            ) as response:
                if response.status_code == 200:
                    response.success()
            
            # Execute the actual operation
            operation()
        except Exception as e:
            print(f"Concurrent operation failed: {e}")
    
    def _execute_search(self, base_url, params):
        """Execute search with parameters"""
        with self.client.get(
            base_url,
            params=params,
            catch_response=True,
            name="[CONCURRENT] Search"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Search failed: {response.status_code}")
    
    def _create_order(self):
        """Create a new order"""
        order_data = {
            "customer_id": f"CUST-{random.randint(1, 100):05d}",
            "items": [
                {
                    "description": f"Item {i}",
                    "quantity": random.randint(1, 10),
                    "weight": random.uniform(0.5, 50)
                }
                for i in range(random.randint(1, 5))
            ],
            "origin_zip": f"{random.randint(10000, 99999)}-{random.randint(100, 999)}",
            "destination_zip": f"{random.randint(10000, 99999)}-{random.randint(100, 999)}"
        }
        
        with self.client.post(
            "/api/orders",
            json=order_data,
            catch_response=True,
            name="[CONCURRENT] Create Order"
        ) as response:
            if response.status_code == 201:
                response.success()
            else:
                response.failure(f"Create failed: {response.status_code}")
    
    def _update_order_status(self):
        """Update order status"""
        order_id = random.randint(1, 1000)
        status_data = {
            "status": random.choice(["processing", "in_transit", "delivered"]),
            "notes": "Concurrent update test"
        }
        
        with self.client.patch(
            f"/api/orders/{order_id}/status",
            json=status_data,
            catch_response=True,
            name="[CONCURRENT] Update Status"
        ) as response:
            if response.status_code in [200, 404]:
                response.success()
            else:
                response.failure(f"Update failed: {response.status_code}")
    
    def _add_tracking_event(self):
        """Add tracking event"""
        tracking_data = {
            "order_id": f"ORD-{random.randint(1, 1000):06d}",
            "event": random.choice(["picked_up", "in_transit", "out_for_delivery"]),
            "location": {
                "lat": random.uniform(-23.9, -22.5),
                "lng": random.uniform(-47.1, -45.5)
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        with self.client.post(
            "/api/tracking/events",
            json=tracking_data,
            catch_response=True,
            name="[CONCURRENT] Add Tracking"
        ) as response:
            if response.status_code in [200, 201]:
                response.success()
            else:
                response.failure(f"Tracking failed: {response.status_code}")
    
    def _update_user_preferences(self):
        """Update user preferences"""
        prefs_data = {
            "notifications": random.choice([True, False]),
            "email_updates": random.choice([True, False]),
            "language": random.choice(["pt", "en", "es"]),
            "timezone": random.choice(["America/Sao_Paulo", "America/New_York", "UTC"])
        }
        
        with self.client.put(
            "/api/users/preferences",
            json=prefs_data,
            catch_response=True,
            name="[CONCURRENT] Update Preferences"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Preferences failed: {response.status_code}")
    
    def _create_notification(self):
        """Create notification"""
        notif_data = {
            "type": random.choice(["order_update", "promotion", "system"]),
            "title": "Concurrent test notification",
            "message": f"Test at {datetime.utcnow().isoformat()}",
            "priority": random.choice(["low", "medium", "high"])
        }
        
        with self.client.post(
            "/api/notifications",
            json=notif_data,
            catch_response=True,
            name="[CONCURRENT] Create Notification"
        ) as response:
            if response.status_code in [200, 201]:
                response.success()
            else:
                response.failure(f"Notification failed: {response.status_code}")
    
    def _calculate_freight(self):
        """Calculate freight cost"""
        calc_data = {
            "origin_zip": f"{random.randint(10000, 99999)}-{random.randint(100, 999)}",
            "destination_zip": f"{random.randint(10000, 99999)}-{random.randint(100, 999)}",
            "weight": random.uniform(1, 100),
            "service_type": random.choice(["standard", "express"])
        }
        
        with self.client.post(
            "/api/freight/calculate",
            json=calc_data,
            catch_response=True,
            name="[CONCURRENT] Calculate Freight"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Calculation failed: {response.status_code}")
    
    def _generate_report(self, report_type, format_type):
        """Generate report"""
        with self.client.get(
            f"/api/reports/{report_type}",
            params={"format": format_type},
            catch_response=True,
            name=f"[CONCURRENT] Report {report_type}"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Report failed: {response.status_code}")
    
    def _simulate_websocket(self, conn_id):
        """Simulate WebSocket connection"""
        # Initial connection
        with self.client.post(
            "/api/ws/connect",
            json={"connection_id": conn_id},
            catch_response=True,
            name="[CONCURRENT] WS Connect"
        ) as response:
            if response.status_code in [200, 201]:
                response.success()
        
        # Send multiple messages
        for _ in range(random.randint(5, 10)):
            with self.client.post(
                "/api/ws/message",
                json={
                    "connection_id": conn_id,
                    "type": "location_update",
                    "data": {
                        "lat": random.uniform(-23.9, -22.5),
                        "lng": random.uniform(-47.1, -45.5)
                    }
                },
                catch_response=True,
                name="[CONCURRENT] WS Message"
            ) as response:
                if response.status_code == 200:
                    response.success()
            
            time.sleep(random.uniform(0.5, 1))
    
    def _bulk_create_orders(self):
        """Bulk create orders"""
        orders = [
            {
                "customer_id": f"CUST-{random.randint(1, 100):05d}",
                "items": [{"description": f"Bulk item {i}", "quantity": 1, "weight": 10}],
                "origin_zip": "01000-000",
                "destination_zip": "02000-000"
            }
            for i in range(random.randint(10, 20))
        ]
        
        with self.client.post(
            "/api/orders/bulk",
            json={"orders": orders},
            catch_response=True,
            name="[CONCURRENT] Bulk Create"
        ) as response:
            if response.status_code in [200, 201]:
                response.success()
            else:
                response.failure(f"Bulk create failed: {response.status_code}")
    
    def _bulk_update_statuses(self):
        """Bulk update order statuses"""
        updates = [
            {
                "order_id": f"ORD-{random.randint(1, 1000):06d}",
                "status": random.choice(["processing", "in_transit"])
            }
            for _ in range(random.randint(10, 20))
        ]
        
        with self.client.post(
            "/api/orders/bulk-status",
            json={"updates": updates},
            catch_response=True,
            name="[CONCURRENT] Bulk Status"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Bulk update failed: {response.status_code}")
    
    def _bulk_assign_drivers(self):
        """Bulk assign drivers to orders"""
        assignments = [
            {
                "order_id": f"ORD-{random.randint(1, 1000):06d}",
                "driver_id": f"DRV-{random.randint(1, 50):04d}"
            }
            for _ in range(random.randint(5, 15))
        ]
        
        with self.client.post(
            "/api/orders/bulk-assign",
            json={"assignments": assignments},
            catch_response=True,
            name="[CONCURRENT] Bulk Assign"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Bulk assign failed: {response.status_code}")
    
    def on_stop(self):
        """Cleanup when user stops"""
        session_duration = time.time() - self.session_start
        print(f"User session ended. Type: {self.user_type}, "
              f"Duration: {session_duration:.2f}s, "
              f"Actions: {self.actions_performed}")


class ConcurrentUser(HttpUser):
    """Concurrent user with specific behavior patterns"""
    tasks = [ConcurrentUserBehavior]
    wait_time = between(0.5, 2)  # Short wait times for high concurrency
    host = LOAD_TEST_CONFIG["base_url"]


class ConcurrentLoadShape(LoadTestShape):
    """
    Load shape for concurrent user testing.
    Rapidly ramps up to high concurrent user count.
    """
    
    stages = [
        {"duration": 30, "users": 50, "spawn_rate": 10},      # Quick ramp to 50 users
        {"duration": 60, "users": 150, "spawn_rate": 20},     # Ramp to 150 users
        {"duration": 90, "users": 300, "spawn_rate": 30},     # Ramp to 300 users
        {"duration": 150, "users": 500, "spawn_rate": 50},    # High concurrency: 500 users
        {"duration": 210, "users": 750, "spawn_rate": 50},    # Peak concurrency: 750 users
        {"duration": 270, "users": 1000, "spawn_rate": 50},   # Maximum: 1000 concurrent users
        {"duration": 330, "users": 500, "spawn_rate": 50},    # Scale down
        {"duration": 360, "users": 100, "spawn_rate": 20},    # Cool down
    ]
    
    def tick(self):
        run_time = self.get_run_time()
        
        for stage in self.stages:
            if run_time < stage["duration"]:
                return (stage["users"], stage["spawn_rate"])
        
        return None
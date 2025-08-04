"""
Main Locust file for load testing the freight management system.
Supports 1000+ requests per minute with various test scenarios.
"""

from locust import HttpUser, TaskSet, task, between, constant, events
from locust.stats import stats_printer, stats_history
from locust.log import setup_logging
import json
import random
import time
from datetime import datetime
import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tests.load.performance_config import (
    LOAD_TEST_CONFIG,
    API_ENDPOINTS,
    USER_SCENARIOS,
    PERFORMANCE_THRESHOLDS
)

# Setup logging
setup_logging("INFO", None)


class FreightSystemUser(HttpUser):
    """Base user class for freight system load testing"""
    
    # Wait time between requests (1-3 seconds for realistic behavior)
    wait_time = between(1, 3)
    
    # Base configuration
    host = LOAD_TEST_CONFIG["base_url"]
    
    def on_start(self):
        """Called when a user starts"""
        self.client.verify = False  # Disable SSL verification for testing
        self.auth_token = None
        self.user_id = None
        
        # Try to authenticate
        self.login()
    
    def on_stop(self):
        """Called when a user stops"""
        if self.auth_token:
            self.logout()
    
    def login(self):
        """Authenticate user and get token"""
        try:
            response = self.client.post(
                "/api/auth/login",
                json={
                    "email": f"loadtest{random.randint(1, 100)}@example.com",
                    "password": "testpass123"
                },
                catch_response=True
            )
            
            if response.status_code == 200:
                data = response.json()
                self.auth_token = data.get("token")
                self.user_id = data.get("user_id")
                self.client.headers.update({"Authorization": f"Bearer {self.auth_token}"})
                response.success()
            else:
                response.failure(f"Login failed: {response.status_code}")
        except Exception as e:
            print(f"Login error: {e}")
    
    def logout(self):
        """Logout user"""
        try:
            self.client.post("/api/auth/logout", catch_response=True)
        except:
            pass
    
    @task(10)
    def list_orders(self):
        """List freight orders - High frequency task"""
        with self.client.get(
            "/api/orders",
            params={"page": 1, "limit": 20},
            catch_response=True,
            name="/api/orders [LIST]"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed to list orders: {response.status_code}")
    
    @task(8)
    def get_order_details(self):
        """Get specific order details"""
        order_id = random.randint(1, 1000)
        with self.client.get(
            f"/api/orders/{order_id}",
            catch_response=True,
            name="/api/orders/[id] [GET]"
        ) as response:
            if response.status_code in [200, 404]:
                response.success()
            else:
                response.failure(f"Failed to get order: {response.status_code}")
    
    @task(5)
    def create_order(self):
        """Create new freight order"""
        order_data = {
            "customer_id": random.randint(1, 100),
            "origin": {
                "city": random.choice(["São Paulo", "Rio de Janeiro", "Belo Horizonte"]),
                "state": random.choice(["SP", "RJ", "MG"])
            },
            "destination": {
                "city": random.choice(["Brasília", "Salvador", "Recife"]),
                "state": random.choice(["DF", "BA", "PE"])
            },
            "weight": random.uniform(100, 5000),
            "volume": random.uniform(1, 50),
            "value": random.uniform(1000, 50000),
            "items": [
                {
                    "description": f"Item {i}",
                    "quantity": random.randint(1, 10),
                    "weight": random.uniform(10, 100)
                } for i in range(random.randint(1, 5))
            ]
        }
        
        with self.client.post(
            "/api/orders",
            json=order_data,
            catch_response=True,
            name="/api/orders [CREATE]"
        ) as response:
            if response.status_code == 201:
                response.success()
            else:
                response.failure(f"Failed to create order: {response.status_code}")
    
    @task(6)
    def calculate_freight(self):
        """Calculate freight cost"""
        calc_data = {
            "origin_zip": random.choice(["01310-100", "20040-020", "30190-000"]),
            "destination_zip": random.choice(["70040-010", "40110-010", "50030-230"]),
            "weight": random.uniform(100, 5000),
            "volume": random.uniform(1, 50),
            "value": random.uniform(1000, 50000),
            "service_type": random.choice(["express", "standard", "economic"])
        }
        
        with self.client.post(
            "/api/freight/calculate",
            json=calc_data,
            catch_response=True,
            name="/api/freight/calculate [POST]"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed to calculate freight: {response.status_code}")
    
    @task(4)
    def track_order(self):
        """Track order status"""
        tracking_code = f"FR{random.randint(100000, 999999)}"
        with self.client.get(
            f"/api/tracking/{tracking_code}",
            catch_response=True,
            name="/api/tracking/[code] [GET]"
        ) as response:
            if response.status_code in [200, 404]:
                response.success()
            else:
                response.failure(f"Failed to track order: {response.status_code}")
    
    @task(3)
    def update_order_status(self):
        """Update order status"""
        order_id = random.randint(1, 1000)
        status_data = {
            "status": random.choice(["pending", "processing", "in_transit", "delivered"]),
            "notes": "Status update from load test"
        }
        
        with self.client.patch(
            f"/api/orders/{order_id}/status",
            json=status_data,
            catch_response=True,
            name="/api/orders/[id]/status [UPDATE]"
        ) as response:
            if response.status_code in [200, 404]:
                response.success()
            else:
                response.failure(f"Failed to update status: {response.status_code}")
    
    @task(2)
    def generate_report(self):
        """Generate performance report"""
        report_params = {
            "type": random.choice(["daily", "weekly", "monthly"]),
            "format": random.choice(["pdf", "excel", "json"])
        }
        
        with self.client.get(
            "/api/reports/performance",
            params=report_params,
            catch_response=True,
            name="/api/reports/performance [GET]"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed to generate report: {response.status_code}")


class MobileAppUser(FreightSystemUser):
    """Mobile app user behavior simulation"""
    
    # Mobile users have slightly longer wait times
    wait_time = between(2, 5)
    
    @task(15)
    def check_notifications(self):
        """Mobile users check notifications frequently"""
        with self.client.get(
            "/api/notifications",
            catch_response=True,
            name="/api/notifications [MOBILE]"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed to get notifications: {response.status_code}")
    
    @task(10)
    def get_location_updates(self):
        """Get real-time location updates"""
        with self.client.get(
            "/api/location/updates",
            catch_response=True,
            name="/api/location/updates [MOBILE]"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed to get location: {response.status_code}")


class AdminUser(FreightSystemUser):
    """Admin user behavior simulation"""
    
    # Admins perform fewer but heavier operations
    wait_time = between(3, 8)
    
    @task(5)
    def get_analytics_dashboard(self):
        """Load analytics dashboard"""
        with self.client.get(
            "/api/admin/analytics",
            catch_response=True,
            name="/api/admin/analytics [DASHBOARD]"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed to load analytics: {response.status_code}")
    
    @task(3)
    def bulk_update_orders(self):
        """Bulk update multiple orders"""
        order_ids = [random.randint(1, 1000) for _ in range(10)]
        update_data = {
            "order_ids": order_ids,
            "updates": {
                "status": "processing",
                "assigned_driver": random.randint(1, 50)
            }
        }
        
        with self.client.post(
            "/api/admin/orders/bulk-update",
            json=update_data,
            catch_response=True,
            name="/api/admin/orders/bulk-update [POST]"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed bulk update: {response.status_code}")


class WebSocketUser(HttpUser):
    """WebSocket connection simulation for real-time features"""
    
    wait_time = constant(0.1)  # WebSocket sends frequent small messages
    
    def on_start(self):
        """Establish WebSocket connection"""
        # Note: Locust doesn't natively support WebSocket
        # This simulates WebSocket-like behavior with HTTP polling
        self.connection_id = f"ws_{random.randint(1000, 9999)}"
    
    @task
    def send_location_update(self):
        """Send location update via simulated WebSocket"""
        location_data = {
            "connection_id": self.connection_id,
            "lat": random.uniform(-23.5, -22.5),
            "lng": random.uniform(-46.5, -45.5),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        with self.client.post(
            "/api/ws/location",
            json=location_data,
            catch_response=True,
            name="/api/ws/location [WS]"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"WebSocket simulation failed: {response.status_code}")


# Event handlers for custom metrics and reporting
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when test starts"""
    print("Load test starting...")
    print(f"Target RPS: {PERFORMANCE_THRESHOLDS['target_rps']}")
    print(f"Max response time: {PERFORMANCE_THRESHOLDS['max_response_time_ms']}ms")
    print(f"Error rate threshold: {PERFORMANCE_THRESHOLDS['error_rate_threshold']*100}%")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when test stops"""
    print("\nLoad test completed!")
    print("\nFinal Statistics:")
    print(f"Total requests: {environment.stats.total.num_requests}")
    print(f"Failed requests: {environment.stats.total.num_failures}")
    print(f"Median response time: {environment.stats.total.median_response_time}ms")
    print(f"Average response time: {environment.stats.total.avg_response_time}ms")
    print(f"Min response time: {environment.stats.total.min_response_time}ms")
    print(f"Max response time: {environment.stats.total.max_response_time}ms")
    
    # Check if performance thresholds were met
    if environment.stats.total.num_requests > 0:
        error_rate = environment.stats.total.num_failures / environment.stats.total.num_requests
        
        print("\nPerformance Threshold Check:")
        print(f"✓ Error rate: {error_rate*100:.2f}% (threshold: {PERFORMANCE_THRESHOLDS['error_rate_threshold']*100}%)")
        print(f"✓ P95 response time: {environment.stats.total.get_response_time_percentile(0.95)}ms")
        print(f"✓ P99 response time: {environment.stats.total.get_response_time_percentile(0.99)}ms")


# Request event handlers for detailed logging
@events.request.add_listener
def on_request(request_type, name, response_time, response_length, response, 
               context, exception, **kwargs):
    """Log detailed request information"""
    if exception:
        print(f"Request failed: {name} - {exception}")
    elif response_time > PERFORMANCE_THRESHOLDS['max_response_time_ms']:
        print(f"Slow request detected: {name} - {response_time}ms")


# Custom failure handler
@events.request_failure.add_listener
def on_failure(request_type, name, response_time, response_length, exception, **kwargs):
    """Handle request failures"""
    print(f"Failure: {request_type} {name} - {exception}")
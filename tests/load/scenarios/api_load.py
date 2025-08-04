"""
API Load Testing Scenarios
Specific load test scenarios for API endpoints with gradual ramp-up to 1000+ req/min
"""

from locust import HttpUser, task, between, LoadTestShape
import math
import time
from datetime import datetime
import json
import random

from ..performance_config import (
    API_ENDPOINTS,
    LOAD_TEST_CONFIG,
    PERFORMANCE_THRESHOLDS
)


class APILoadTestUser(HttpUser):
    """
    API endpoint load testing with realistic user patterns.
    Focuses on core API operations with proper authentication.
    """
    
    wait_time = between(0.5, 2)  # Faster requests for API testing
    host = LOAD_TEST_CONFIG["base_url"]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.api_token = None
        self.test_data = {
            "orders": [],
            "customers": [],
            "drivers": []
        }
    
    def on_start(self):
        """Initialize API client and authenticate"""
        self.authenticate_api_user()
        self.prepare_test_data()
    
    def authenticate_api_user(self):
        """Get API authentication token"""
        auth_response = self.client.post(
            "/api/auth/token",
            json={
                "client_id": "load_test_client",
                "client_secret": "test_secret_key",
                "grant_type": "client_credentials"
            },
            catch_response=True
        )
        
        if auth_response.status_code == 200:
            data = auth_response.json()
            self.api_token = data.get("access_token")
            self.client.headers.update({
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json",
                "X-API-Version": "v1"
            })
            auth_response.success()
        else:
            auth_response.failure("API authentication failed")
    
    def prepare_test_data(self):
        """Prepare test data for realistic scenarios"""
        # Generate test order IDs
        self.test_data["orders"] = [f"ORD-{i:06d}" for i in range(1, 1001)]
        
        # Generate test customer IDs
        self.test_data["customers"] = [f"CUST-{i:05d}" for i in range(1, 101)]
        
        # Generate test driver IDs
        self.test_data["drivers"] = [f"DRV-{i:04d}" for i in range(1, 51)]
    
    @task(20)
    def get_orders_list(self):
        """High-frequency endpoint: List orders with pagination"""
        page = random.randint(1, 50)
        limit = random.choice([10, 20, 50, 100])
        
        params = {
            "page": page,
            "limit": limit,
            "sort": random.choice(["created_at", "-created_at", "status", "-value"]),
            "status": random.choice([None, "pending", "processing", "in_transit", "delivered"])
        }
        
        # Remove None values
        params = {k: v for k, v in params.items() if v is not None}
        
        with self.client.get(
            "/api/v1/orders",
            params=params,
            catch_response=True,
            name="/api/v1/orders [PAGINATED]"
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "items" in data and "total" in data:
                        response.success()
                    else:
                        response.failure("Invalid response format")
                except:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"Status: {response.status_code}")
    
    @task(15)
    def get_order_by_id(self):
        """Get specific order details"""
        order_id = random.choice(self.test_data["orders"])
        
        with self.client.get(
            f"/api/v1/orders/{order_id}",
            catch_response=True,
            name="/api/v1/orders/[id]"
        ) as response:
            if response.status_code in [200, 404]:
                response.success()
            else:
                response.failure(f"Status: {response.status_code}")
    
    @task(12)
    def create_new_order(self):
        """Create new freight order with validation"""
        customer_id = random.choice(self.test_data["customers"])
        
        order_payload = {
            "customer_id": customer_id,
            "type": random.choice(["standard", "express", "fragile", "refrigerated"]),
            "origin": {
                "street": f"{random.randint(1, 999)} Test Street",
                "city": random.choice(["São Paulo", "Rio de Janeiro", "Belo Horizonte"]),
                "state": random.choice(["SP", "RJ", "MG"]),
                "zip_code": f"{random.randint(10000, 99999)}-{random.randint(100, 999)}",
                "country": "BR",
                "coordinates": {
                    "lat": random.uniform(-23.9, -22.5),
                    "lng": random.uniform(-47.1, -45.5)
                }
            },
            "destination": {
                "street": f"{random.randint(1, 999)} Delivery Avenue",
                "city": random.choice(["Brasília", "Salvador", "Recife", "Fortaleza"]),
                "state": random.choice(["DF", "BA", "PE", "CE"]),
                "zip_code": f"{random.randint(10000, 99999)}-{random.randint(100, 999)}",
                "country": "BR",
                "coordinates": {
                    "lat": random.uniform(-16.0, -8.0),
                    "lng": random.uniform(-48.0, -34.5)
                }
            },
            "items": [
                {
                    "description": f"Item {i}",
                    "quantity": random.randint(1, 20),
                    "weight": round(random.uniform(0.5, 50), 2),
                    "dimensions": {
                        "length": random.randint(10, 200),
                        "width": random.randint(10, 150),
                        "height": random.randint(10, 100)
                    },
                    "value": round(random.uniform(50, 5000), 2),
                    "fragile": random.choice([True, False])
                }
                for i in range(random.randint(1, 5))
            ],
            "insurance": random.choice([True, False]),
            "priority": random.choice(["low", "normal", "high", "urgent"]),
            "notes": f"Load test order created at {datetime.utcnow().isoformat()}"
        }
        
        with self.client.post(
            "/api/v1/orders",
            json=order_payload,
            catch_response=True,
            name="/api/v1/orders [CREATE]"
        ) as response:
            if response.status_code == 201:
                try:
                    data = response.json()
                    if "id" in data:
                        # Store the created order ID for future operations
                        self.test_data["orders"].append(data["id"])
                        response.success()
                    else:
                        response.failure("No order ID in response")
                except:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"Status: {response.status_code}")
    
    @task(10)
    def calculate_freight_cost(self):
        """Calculate freight cost with different scenarios"""
        calc_payload = {
            "origin_zip": f"{random.randint(10000, 99999)}-{random.randint(100, 999)}",
            "destination_zip": f"{random.randint(10000, 99999)}-{random.randint(100, 999)}",
            "items": [
                {
                    "weight": round(random.uniform(0.5, 100), 2),
                    "dimensions": {
                        "length": random.randint(10, 200),
                        "width": random.randint(10, 150),
                        "height": random.randint(10, 100)
                    },
                    "quantity": random.randint(1, 10)
                }
                for _ in range(random.randint(1, 3))
            ],
            "service_type": random.choice(["economic", "standard", "express", "same_day"]),
            "insurance_value": round(random.uniform(100, 10000), 2) if random.choice([True, False]) else None,
            "additional_services": random.sample(
                ["fragile_care", "lift_gate", "inside_delivery", "appointment"],
                random.randint(0, 2)
            )
        }
        
        with self.client.post(
            "/api/v1/freight/calculate",
            json=calc_payload,
            catch_response=True,
            name="/api/v1/freight/calculate"
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "total_cost" in data and "breakdown" in data:
                        response.success()
                    else:
                        response.failure("Invalid calculation response")
                except:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"Status: {response.status_code}")
    
    @task(8)
    def track_shipment(self):
        """Track shipment with various tracking codes"""
        tracking_formats = [
            lambda: f"FR{random.randint(100000000, 999999999)}",  # Standard format
            lambda: f"EX{random.randint(10000, 99999)}-BR",       # Express format
            lambda: f"{random.choice(self.test_data['orders'])}"  # Order ID tracking
        ]
        
        tracking_code = random.choice(tracking_formats)()
        
        with self.client.get(
            f"/api/v1/tracking/{tracking_code}",
            catch_response=True,
            name="/api/v1/tracking/[code]"
        ) as response:
            if response.status_code in [200, 404]:
                response.success()
            else:
                response.failure(f"Status: {response.status_code}")
    
    @task(6)
    def update_order_status(self):
        """Update order status with workflow validation"""
        order_id = random.choice(self.test_data["orders"])
        
        status_transitions = {
            "pending": ["confirmed", "cancelled"],
            "confirmed": ["processing", "cancelled"],
            "processing": ["ready_for_pickup", "cancelled"],
            "ready_for_pickup": ["in_transit"],
            "in_transit": ["out_for_delivery", "returned"],
            "out_for_delivery": ["delivered", "failed_delivery"],
            "failed_delivery": ["rescheduled", "returned"]
        }
        
        current_status = random.choice(list(status_transitions.keys()))
        new_status = random.choice(status_transitions[current_status])
        
        update_payload = {
            "status": new_status,
            "notes": f"Status updated during load test at {datetime.utcnow().isoformat()}",
            "location": {
                "lat": random.uniform(-23.9, -22.5),
                "lng": random.uniform(-47.1, -45.5)
            } if new_status in ["in_transit", "out_for_delivery"] else None,
            "driver_id": random.choice(self.test_data["drivers"]) if new_status in ["in_transit", "out_for_delivery"] else None
        }
        
        # Remove None values
        update_payload = {k: v for k, v in update_payload.items() if v is not None}
        
        with self.client.patch(
            f"/api/v1/orders/{order_id}/status",
            json=update_payload,
            catch_response=True,
            name="/api/v1/orders/[id]/status"
        ) as response:
            if response.status_code in [200, 404, 422]:  # 422 for invalid status transition
                response.success()
            else:
                response.failure(f"Status: {response.status_code}")
    
    @task(5)
    def search_orders(self):
        """Search orders with various filters"""
        search_params = {
            "q": random.choice([
                f"CUST-{random.randint(1, 100):05d}",  # Customer search
                random.choice(["São Paulo", "Rio", "urgent", "delivered"]),  # Text search
                f"{random.randint(10000, 99999)}"  # ZIP code search
            ]),
            "date_from": "2024-01-01",
            "date_to": datetime.utcnow().strftime("%Y-%m-%d"),
            "min_value": random.choice([None, 100, 1000, 5000]),
            "max_value": random.choice([None, 10000, 50000, 100000]),
            "limit": 50
        }
        
        # Remove None values
        search_params = {k: v for k, v in search_params.items() if v is not None}
        
        with self.client.get(
            "/api/v1/orders/search",
            params=search_params,
            catch_response=True,
            name="/api/v1/orders/search"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status: {response.status_code}")
    
    @task(4)
    def get_customer_orders(self):
        """Get orders for specific customer"""
        customer_id = random.choice(self.test_data["customers"])
        
        with self.client.get(
            f"/api/v1/customers/{customer_id}/orders",
            params={"limit": 20, "include_cancelled": random.choice([True, False])},
            catch_response=True,
            name="/api/v1/customers/[id]/orders"
        ) as response:
            if response.status_code in [200, 404]:
                response.success()
            else:
                response.failure(f"Status: {response.status_code}")
    
    @task(3)
    def generate_invoice(self):
        """Generate invoice for order"""
        order_id = random.choice(self.test_data["orders"])
        
        with self.client.post(
            f"/api/v1/orders/{order_id}/invoice",
            json={"format": random.choice(["pdf", "xml", "json"])},
            catch_response=True,
            name="/api/v1/orders/[id]/invoice"
        ) as response:
            if response.status_code in [200, 201, 404]:
                response.success()
            else:
                response.failure(f"Status: {response.status_code}")
    
    @task(2)
    def bulk_status_update(self):
        """Bulk update multiple orders"""
        order_ids = random.sample(self.test_data["orders"], min(10, len(self.test_data["orders"])))
        
        bulk_payload = {
            "order_ids": order_ids,
            "updates": {
                "status": random.choice(["processing", "in_transit"]),
                "assigned_driver": random.choice(self.test_data["drivers"]),
                "notes": f"Bulk update at {datetime.utcnow().isoformat()}"
            }
        }
        
        with self.client.post(
            "/api/v1/orders/bulk-update",
            json=bulk_payload,
            catch_response=True,
            name="/api/v1/orders/bulk-update"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status: {response.status_code}")
    
    @task(1)
    def webhook_simulation(self):
        """Simulate webhook callback"""
        webhook_payload = {
            "event": random.choice(["order.created", "order.updated", "order.delivered", "payment.received"]),
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "order_id": random.choice(self.test_data["orders"]),
                "status": random.choice(["confirmed", "in_transit", "delivered"]),
                "amount": round(random.uniform(100, 5000), 2)
            }
        }
        
        with self.client.post(
            "/api/v1/webhooks/callback",
            json=webhook_payload,
            headers={"X-Webhook-Signature": "test-signature"},
            catch_response=True,
            name="/api/v1/webhooks/callback"
        ) as response:
            if response.status_code in [200, 202]:
                response.success()
            else:
                response.failure(f"Status: {response.status_code}")


class StepLoadShape(LoadTestShape):
    """
    A step load shape for gradual ramp-up to 1000+ requests per minute.
    
    Gradually increases user count to reach target RPS.
    """
    
    # Load test stages (duration in seconds, users count, spawn rate)
    stages = [
        {"duration": 60, "users": 10, "spawn_rate": 2},      # Warm-up: 1 min
        {"duration": 120, "users": 25, "spawn_rate": 5},     # Ramp-up: 2 min
        {"duration": 180, "users": 50, "spawn_rate": 10},    # Increase: 3 min
        {"duration": 240, "users": 100, "spawn_rate": 20},   # Scale: 4 min
        {"duration": 300, "users": 200, "spawn_rate": 25},   # Target: 5 min at high load
        {"duration": 360, "users": 250, "spawn_rate": 30},   # Peak: 6 min at peak
        {"duration": 420, "users": 100, "spawn_rate": 20},   # Cool-down: 7 min
        {"duration": 480, "users": 10, "spawn_rate": 5},     # Wind-down: 8 min
    ]
    
    def tick(self):
        run_time = self.get_run_time()
        
        for stage in self.stages:
            if run_time < stage["duration"]:
                tick_data = (stage["users"], stage["spawn_rate"])
                return tick_data
        
        # Test completed
        return None
#!/usr/bin/env python3
"""
Production Health Verification Script
Comprehensive health checks for production deployment verification
"""

import requests
import psycopg2
import redis
import json
import time
import sys
import os
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Tuple, Any
import subprocess

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class HealthVerifier:
    def __init__(self):
        self.base_url = os.getenv('API_BASE_URL', 'https://api.frete-sistema.com')
        self.db_host = os.getenv('DB_HOST', 'localhost')
        self.db_name = os.getenv('DB_NAME', 'frete_sistema')
        self.db_user = os.getenv('DB_USER', 'app_user')
        self.db_password = os.getenv('DB_PASSWORD', self._get_db_password())
        self.redis_host = os.getenv('REDIS_HOST', 'localhost')
        self.redis_port = int(os.getenv('REDIS_PORT', 6379))
        self.timeout = 30
        self.results = {}

    def _get_db_password(self):
        """Get database password from secure location"""
        try:
            with open('/etc/secrets/db_password', 'r') as f:
                return f.read().strip()
        except FileNotFoundError:
            logger.warning("Database password file not found, using environment variable")
            return os.getenv('DB_PASSWORD', '')

    def check_application_health(self) -> Tuple[bool, Dict[str, Any]]:
        """Check application health endpoint"""
        logger.info("Checking application health...")
        try:
            response = requests.get(
                f"{self.base_url}/health",
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                health_data = response.json()
                return True, {
                    'status': 'healthy',
                    'response_time': response.elapsed.total_seconds(),
                    'data': health_data
                }
            else:
                return False, {
                    'status': 'unhealthy',
                    'status_code': response.status_code,
                    'response_time': response.elapsed.total_seconds()
                }
        except Exception as e:
            return False, {'status': 'error', 'error': str(e)}

    def check_database_connectivity(self) -> Tuple[bool, Dict[str, Any]]:
        """Check database connectivity and basic operations"""
        logger.info("Checking database connectivity...")
        try:
            start_time = time.time()
            conn = psycopg2.connect(
                host=self.db_host,
                database=self.db_name,
                user=self.db_user,
                password=self.db_password,
                connect_timeout=self.timeout
            )
            
            cursor = conn.cursor()
            
            # Test basic query
            cursor.execute("SELECT version()")
            version = cursor.fetchone()[0]
            
            # Test table existence
            cursor.execute("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
            table_count = cursor.fetchone()[0]
            
            # Test a simple business query
            cursor.execute("SELECT COUNT(*) FROM pedidos LIMIT 1")
            pedidos_count = cursor.fetchone()[0]
            
            conn.close()
            
            response_time = time.time() - start_time
            
            return True, {
                'status': 'connected',
                'response_time': response_time,
                'version': version,
                'table_count': table_count,
                'pedidos_count': pedidos_count
            }
            
        except Exception as e:
            return False, {
                'status': 'error',
                'error': str(e)
            }

    def check_redis_connectivity(self) -> Tuple[bool, Dict[str, Any]]:
        """Check Redis connectivity and performance"""
        logger.info("Checking Redis connectivity...")
        try:
            start_time = time.time()
            r = redis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                socket_timeout=self.timeout,
                socket_connect_timeout=self.timeout
            )
            
            # Test ping
            ping_result = r.ping()
            
            # Test set/get
            test_key = 'health_check_test'
            r.set(test_key, 'test_value', ex=60)
            test_value = r.get(test_key)
            r.delete(test_key)
            
            # Get info
            info = r.info()
            
            response_time = time.time() - start_time
            
            return True, {
                'status': 'connected',
                'response_time': response_time,
                'ping': ping_result,
                'test_successful': test_value == b'test_value',
                'memory_usage': info.get('used_memory_human'),
                'connected_clients': info.get('connected_clients')
            }
            
        except Exception as e:
            return False, {
                'status': 'error',
                'error': str(e)
            }

    def check_api_endpoints(self) -> Tuple[bool, Dict[str, Any]]:
        """Check critical API endpoints"""
        logger.info("Checking API endpoints...")
        
        endpoints = [
            {'name': 'health', 'path': '/health', 'method': 'GET'},
            {'name': 'auth', 'path': '/api/auth/status', 'method': 'GET'},
            {'name': 'pedidos', 'path': '/api/pedidos', 'method': 'GET'},
            {'name': 'usuarios', 'path': '/api/usuarios', 'method': 'GET'},
            {'name': 'relatorios', 'path': '/api/relatorios/status', 'method': 'GET'},
        ]
        
        results = {}
        overall_success = True
        
        for endpoint in endpoints:
            try:
                start_time = time.time()
                
                if endpoint['method'] == 'GET':
                    response = requests.get(
                        f"{self.base_url}{endpoint['path']}",
                        timeout=self.timeout
                    )
                else:
                    # Handle other methods if needed
                    continue
                
                response_time = time.time() - start_time
                
                results[endpoint['name']] = {
                    'status_code': response.status_code,
                    'response_time': response_time,
                    'success': response.status_code < 400
                }
                
                if response.status_code >= 400:
                    overall_success = False
                    
            except Exception as e:
                results[endpoint['name']] = {
                    'error': str(e),
                    'success': False
                }
                overall_success = False
        
        return overall_success, results

    def check_ssl_certificate(self) -> Tuple[bool, Dict[str, Any]]:
        """Check SSL certificate validity"""
        logger.info("Checking SSL certificate...")
        try:
            import ssl
            import socket
            from urllib.parse import urlparse
            
            parsed_url = urlparse(self.base_url)
            hostname = parsed_url.hostname
            port = parsed_url.port or 443
            
            context = ssl.create_default_context()
            
            with socket.create_connection((hostname, port), timeout=self.timeout) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert = ssock.getpeercert()
                    
                    return True, {
                        'status': 'valid',
                        'subject': dict(x[0] for x in cert['subject']),
                        'issuer': dict(x[0] for x in cert['issuer']),
                        'not_after': cert['notAfter'],
                        'version': cert['version']
                    }
                    
        except Exception as e:
            return False, {
                'status': 'error',
                'error': str(e)
            }

    def check_cdn_performance(self) -> Tuple[bool, Dict[str, Any]]:
        """Check CDN performance and static assets"""
        logger.info("Checking CDN performance...")
        
        static_assets = [
            '/static/css/main.css',
            '/static/js/main.js',
            '/favicon.ico'
        ]
        
        results = {}
        overall_success = True
        
        for asset in static_assets:
            try:
                start_time = time.time()
                response = requests.get(
                    f"{self.base_url}{asset}",
                    timeout=self.timeout
                )
                response_time = time.time() - start_time
                
                results[asset] = {
                    'status_code': response.status_code,
                    'response_time': response_time,
                    'size': len(response.content),
                    'cache_control': response.headers.get('Cache-Control'),
                    'success': response.status_code == 200
                }
                
                if response.status_code != 200:
                    overall_success = False
                    
            except Exception as e:
                results[asset] = {
                    'error': str(e),
                    'success': False
                }
                overall_success = False
        
        return overall_success, results

    def check_system_resources(self) -> Tuple[bool, Dict[str, Any]]:
        """Check system resource usage"""
        logger.info("Checking system resources...")
        try:
            # Get disk usage
            disk_usage = subprocess.check_output(['df', '-h', '/'], text=True)
            
            # Get memory usage
            memory_info = subprocess.check_output(['free', '-h'], text=True)
            
            # Get load average
            with open('/proc/loadavg', 'r') as f:
                load_avg = f.read().strip().split()[:3]
            
            # Check if application process is running
            try:
                ps_output = subprocess.check_output(['pgrep', '-f', 'npm.*start'], text=True)
                app_running = len(ps_output.strip().split('\n')) > 0
            except subprocess.CalledProcessError:
                app_running = False
            
            return True, {
                'disk_usage': disk_usage,
                'memory_info': memory_info,
                'load_average': load_avg,
                'app_process_running': app_running
            }
            
        except Exception as e:
            return False, {
                'status': 'error',
                'error': str(e)
            }

    def run_all_checks(self) -> Dict[str, Any]:
        """Run all health checks concurrently"""
        logger.info("Starting comprehensive health verification...")
        
        checks = [
            ('application', self.check_application_health),
            ('database', self.check_database_connectivity),
            ('redis', self.check_redis_connectivity),
            ('api_endpoints', self.check_api_endpoints),
            ('ssl_certificate', self.check_ssl_certificate),
            ('cdn_performance', self.check_cdn_performance),
            ('system_resources', self.check_system_resources),
        ]
        
        results = {}
        
        with ThreadPoolExecutor(max_workers=len(checks)) as executor:
            future_to_check = {
                executor.submit(check_func): check_name 
                for check_name, check_func in checks
            }
            
            for future in as_completed(future_to_check):
                check_name = future_to_check[future]
                try:
                    success, data = future.result()
                    results[check_name] = {
                        'success': success,
                        'data': data
                    }
                except Exception as e:
                    results[check_name] = {
                        'success': False,
                        'data': {'error': str(e)}
                    }
        
        return results

    def generate_report(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate health verification report"""
        total_checks = len(results)
        successful_checks = sum(1 for result in results.values() if result['success'])
        
        overall_health = 'HEALTHY' if successful_checks == total_checks else (
            'DEGRADED' if successful_checks >= total_checks * 0.8 else 'UNHEALTHY'
        )
        
        return {
            'timestamp': time.time(),
            'overall_health': overall_health,
            'success_rate': f"{successful_checks}/{total_checks}",
            'success_percentage': (successful_checks / total_checks) * 100,
            'checks': results
        }

def main():
    """Main execution function"""
    verifier = HealthVerifier()
    
    try:
        results = verifier.run_all_checks()
        report = verifier.generate_report(results)
        
        # Print summary
        print("\n" + "="*50)
        print("PRODUCTION HEALTH VERIFICATION REPORT")
        print("="*50)
        print(f"Overall Health: {report['overall_health']}")
        print(f"Success Rate: {report['success_rate']}")
        print(f"Success Percentage: {report['success_percentage']:.1f}%")
        print("="*50)
        
        # Print individual check results
        for check_name, result in results.items():
            status = "✅ PASS" if result['success'] else "❌ FAIL"
            print(f"{check_name}: {status}")
            
            if not result['success'] and 'data' in result:
                if 'error' in result['data']:
                    print(f"  Error: {result['data']['error']}")
        
        print("="*50)
        
        # Save detailed report
        report_file = f"/tmp/health_report_{int(time.time())}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"Detailed report saved to: {report_file}")
        
        # Exit with appropriate code
        if report['overall_health'] == 'HEALTHY':
            sys.exit(0)
        elif report['overall_health'] == 'DEGRADED':
            print("\nWARNING: System is in degraded state but functional")
            sys.exit(1)
        else:
            print("\nERROR: System is unhealthy - immediate attention required")
            sys.exit(2)
            
    except Exception as e:
        logger.error(f"Health verification failed: {str(e)}")
        sys.exit(3)

if __name__ == "__main__":
    main()
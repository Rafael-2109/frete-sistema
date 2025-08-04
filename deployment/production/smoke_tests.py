#!/usr/bin/env python3
"""
Production Smoke Tests
Critical functionality tests for production deployment verification
"""

import requests
import json
import time
import sys
import os
import logging
import uuid
from typing import Dict, List, Any, Optional
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SmokeTests:
    def __init__(self, quick_mode: bool = False):
        self.base_url = os.getenv('API_BASE_URL', 'https://api.frete-sistema.com')
        self.timeout = 30
        self.quick_mode = quick_mode
        self.test_results = []
        self.auth_token = None
        
        # Test data
        self.test_user_data = {
            'email': f'smoke_test_{uuid.uuid4().hex[:8]}@test.com',
            'password': 'SmokeTest123!',
            'nome': 'Smoke Test User',
            'role': 'usuario'
        }

    def log_test_result(self, test_name: str, success: bool, details: Dict[str, Any] = None):
        """Log test result"""
        result = {
            'test_name': test_name,
            'success': success,
            'timestamp': time.time(),
            'details': details or {}
        }
        self.test_results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        logger.info(f"{test_name}: {status}")
        
        if not success and details:
            logger.error(f"  Details: {details}")

    def test_application_startup(self) -> bool:
        """Test if application is running and responsive"""
        try:
            response = requests.get(
                f"{self.base_url}/health",
                timeout=self.timeout
            )
            
            success = response.status_code == 200
            details = {
                'status_code': response.status_code,
                'response_time': response.elapsed.total_seconds()
            }
            
            if success:
                try:
                    health_data = response.json()
                    details['health_data'] = health_data
                except:
                    pass
            
            self.log_test_result('Application Startup', success, details)
            return success
            
        except Exception as e:
            self.log_test_result('Application Startup', False, {'error': str(e)})
            return False

    def test_database_connection(self) -> bool:
        """Test database connectivity through API"""
        try:
            response = requests.get(
                f"{self.base_url}/api/system/db-status",
                timeout=self.timeout
            )
            
            success = response.status_code == 200
            details = {
                'status_code': response.status_code,
                'response_time': response.elapsed.total_seconds()
            }
            
            if success:
                try:
                    db_status = response.json()
                    details['db_status'] = db_status
                    success = db_status.get('connected', False)
                except:
                    pass
            
            self.log_test_result('Database Connection', success, details)
            return success
            
        except Exception as e:
            self.log_test_result('Database Connection', False, {'error': str(e)})
            return False

    def test_user_authentication(self) -> bool:
        """Test user authentication flow"""
        try:
            # Test registration
            register_response = requests.post(
                f"{self.base_url}/api/auth/register",
                json=self.test_user_data,
                timeout=self.timeout
            )
            
            if register_response.status_code not in [200, 201]:
                self.log_test_result('User Authentication', False, {
                    'step': 'registration',
                    'status_code': register_response.status_code,
                    'response': register_response.text[:200]
                })
                return False
            
            # Test login
            login_response = requests.post(
                f"{self.base_url}/api/auth/login",
                json={
                    'email': self.test_user_data['email'],
                    'password': self.test_user_data['password']
                },
                timeout=self.timeout
            )
            
            if login_response.status_code != 200:
                self.log_test_result('User Authentication', False, {
                    'step': 'login',
                    'status_code': login_response.status_code,
                    'response': login_response.text[:200]
                })
                return False
            
            # Extract token
            login_data = login_response.json()
            self.auth_token = login_data.get('token')
            
            if not self.auth_token:
                self.log_test_result('User Authentication', False, {
                    'step': 'token_extraction',
                    'response': login_data
                })
                return False
            
            self.log_test_result('User Authentication', True, {
                'registration_status': register_response.status_code,
                'login_status': login_response.status_code,
                'token_received': bool(self.auth_token)
            })
            return True
            
        except Exception as e:
            self.log_test_result('User Authentication', False, {'error': str(e)})
            return False

    def test_authenticated_endpoints(self) -> bool:
        """Test endpoints that require authentication"""
        if not self.auth_token:
            self.log_test_result('Authenticated Endpoints', False, {'error': 'No auth token available'})
            return False
        
        headers = {'Authorization': f'Bearer {self.auth_token}'}
        
        endpoints = [
            {'path': '/api/usuarios/profile', 'method': 'GET'},
            {'path': '/api/pedidos', 'method': 'GET'},
            {'path': '/api/relatorios/dashboard', 'method': 'GET'},
        ]
        
        all_success = True
        endpoint_results = {}
        
        for endpoint in endpoints:
            try:
                response = requests.get(
                    f"{self.base_url}{endpoint['path']}",
                    headers=headers,
                    timeout=self.timeout
                )
                
                success = response.status_code in [200, 201, 204]
                endpoint_results[endpoint['path']] = {
                    'status_code': response.status_code,
                    'success': success
                }
                
                if not success:
                    all_success = False
                    
            except Exception as e:
                endpoint_results[endpoint['path']] = {
                    'error': str(e),
                    'success': False
                }
                all_success = False
        
        self.log_test_result('Authenticated Endpoints', all_success, endpoint_results)
        return all_success

    def test_pedido_creation(self) -> bool:
        """Test creating a new shipping order"""
        if not self.auth_token:
            self.log_test_result('Pedido Creation', False, {'error': 'No auth token available'})
            return False
        
        headers = {'Authorization': f'Bearer {self.auth_token}'}
        
        pedido_data = {
            'origem': {
                'cep': '01001-000',
                'endereco': 'Praça da Sé, 1',
                'cidade': 'São Paulo',
                'estado': 'SP'
            },
            'destino': {
                'cep': '20040-020',
                'endereco': 'Av. Rio Branco, 1',
                'cidade': 'Rio de Janeiro',
                'estado': 'RJ'
            },
            'pacote': {
                'peso': 2.5,
                'dimensoes': {
                    'altura': 10,
                    'largura': 20,
                    'comprimento': 30
                }
            },
            'valor_declarado': 100.00
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/api/pedidos",
                json=pedido_data,
                headers=headers,
                timeout=self.timeout
            )
            
            success = response.status_code in [200, 201]
            details = {
                'status_code': response.status_code,
                'response_time': response.elapsed.total_seconds()
            }
            
            if success:
                try:
                    pedido_response = response.json()
                    details['pedido_id'] = pedido_response.get('id')
                    details['valor_frete'] = pedido_response.get('valor_frete')
                except:
                    pass
            else:
                details['response'] = response.text[:200]
            
            self.log_test_result('Pedido Creation', success, details)
            return success
            
        except Exception as e:
            self.log_test_result('Pedido Creation', False, {'error': str(e)})
            return False

    def test_cep_validation(self) -> bool:
        """Test CEP validation functionality"""
        test_ceps = [
            {'cep': '01001-000', 'should_be_valid': True},
            {'cep': '20040020', 'should_be_valid': True},
            {'cep': '99999-999', 'should_be_valid': False},
            {'cep': 'invalid', 'should_be_valid': False}
        ]
        
        all_success = True
        cep_results = {}
        
        for cep_test in test_ceps:
            try:
                response = requests.get(
                    f"{self.base_url}/api/cep/{cep_test['cep']}",
                    timeout=self.timeout
                )
                
                is_valid = response.status_code == 200
                expected_valid = cep_test['should_be_valid']
                
                success = is_valid == expected_valid
                cep_results[cep_test['cep']] = {
                    'expected_valid': expected_valid,
                    'actual_valid': is_valid,
                    'success': success
                }
                
                if not success:
                    all_success = False
                    
            except Exception as e:
                cep_results[cep_test['cep']] = {
                    'error': str(e),
                    'success': False
                }
                all_success = False
        
        self.log_test_result('CEP Validation', all_success, cep_results)
        return all_success

    def test_frete_calculation(self) -> bool:
        """Test freight calculation functionality"""
        calculation_data = {
            'origem': '01001-000',
            'destino': '20040-020',
            'peso': 1.5,
            'dimensoes': {
                'altura': 10,
                'largura': 15,
                'comprimento': 20
            }
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/api/frete/calcular",
                json=calculation_data,
                timeout=self.timeout
            )
            
            success = response.status_code == 200
            details = {
                'status_code': response.status_code,
                'response_time': response.elapsed.total_seconds()
            }
            
            if success:
                try:
                    calc_response = response.json()
                    details['valor_calculado'] = calc_response.get('valor')
                    details['prazo_entrega'] = calc_response.get('prazo_entrega')
                    
                    # Validate that we got reasonable values
                    valor = calc_response.get('valor', 0)
                    prazo = calc_response.get('prazo_entrega', 0)
                    
                    if valor <= 0 or prazo <= 0:
                        success = False
                        details['validation_error'] = 'Invalid calculation values'
                        
                except Exception as e:
                    success = False
                    details['parse_error'] = str(e)
            else:
                details['response'] = response.text[:200]
            
            self.log_test_result('Frete Calculation', success, details)
            return success
            
        except Exception as e:
            self.log_test_result('Frete Calculation', False, {'error': str(e)})
            return False

    def test_static_assets(self) -> bool:
        """Test static assets loading"""
        if self.quick_mode:
            # Skip in quick mode
            self.log_test_result('Static Assets', True, {'skipped': 'quick_mode'})
            return True
        
        assets = [
            '/favicon.ico',
            '/static/css/main.css',
            '/static/js/main.js'
        ]
        
        all_success = True
        asset_results = {}
        
        for asset in assets:
            try:
                response = requests.get(
                    f"{self.base_url}{asset}",
                    timeout=self.timeout
                )
                
                success = response.status_code == 200
                asset_results[asset] = {
                    'status_code': response.status_code,
                    'size': len(response.content) if success else 0,
                    'success': success
                }
                
                if not success:
                    all_success = False
                    
            except Exception as e:
                asset_results[asset] = {
                    'error': str(e),
                    'success': False
                }
                all_success = False
        
        self.log_test_result('Static Assets', all_success, asset_results)
        return all_success

    def test_performance_benchmarks(self) -> bool:
        """Test basic performance benchmarks"""
        if self.quick_mode:
            # Skip in quick mode
            self.log_test_result('Performance Benchmarks', True, {'skipped': 'quick_mode'})
            return True
        
        # Test response time for health endpoint
        response_times = []
        
        for i in range(5):
            try:
                start_time = time.time()
                response = requests.get(f"{self.base_url}/health", timeout=self.timeout)
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    response_times.append(response_time)
                else:
                    break
                    
            except Exception:
                break
        
        if not response_times:
            self.log_test_result('Performance Benchmarks', False, {'error': 'No successful requests'})
            return False
        
        avg_response_time = sum(response_times) / len(response_times)
        max_response_time = max(response_times)
        
        # Define performance thresholds
        success = avg_response_time < 2.0 and max_response_time < 5.0
        
        details = {
            'avg_response_time': avg_response_time,
            'max_response_time': max_response_time,
            'total_requests': len(response_times),
            'threshold_avg': 2.0,
            'threshold_max': 5.0
        }
        
        self.log_test_result('Performance Benchmarks', success, details)
        return success

    def cleanup_test_data(self):
        """Clean up test data created during tests"""
        if not self.auth_token:
            return
        
        try:
            headers = {'Authorization': f'Bearer {self.auth_token}'}
            
            # Delete test user
            requests.delete(
                f"{self.base_url}/api/usuarios/me",
                headers=headers,
                timeout=self.timeout
            )
            
            logger.info("Test data cleanup completed")
            
        except Exception as e:
            logger.warning(f"Test data cleanup failed: {str(e)}")

    def run_all_tests(self) -> Dict[str, Any]:
        """Run all smoke tests"""
        logger.info(f"Starting smoke tests {'(quick mode)' if self.quick_mode else '(full mode)'}")
        
        tests = [
            self.test_application_startup,
            self.test_database_connection,
            self.test_user_authentication,
            self.test_authenticated_endpoints,
            self.test_pedido_creation,
            self.test_cep_validation,
            self.test_frete_calculation,
            self.test_static_assets,
            self.test_performance_benchmarks,
        ]
        
        # Run tests sequentially (some depend on previous results)
        for test_func in tests:
            test_func()
        
        # Cleanup
        self.cleanup_test_data()
        
        # Generate summary
        total_tests = len(self.test_results)
        successful_tests = sum(1 for result in self.test_results if result['success'])
        
        return {
            'timestamp': time.time(),
            'mode': 'quick' if self.quick_mode else 'full',
            'total_tests': total_tests,
            'successful_tests': successful_tests,
            'success_rate': (successful_tests / total_tests) * 100 if total_tests > 0 else 0,
            'overall_success': successful_tests == total_tests,
            'test_results': self.test_results
        }

def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(description='Production Smoke Tests')
    parser.add_argument('--quick', action='store_true', help='Run quick tests only')
    args = parser.parse_args()
    
    smoke_tests = SmokeTests(quick_mode=args.quick)
    
    try:
        results = smoke_tests.run_all_tests()
        
        # Print summary
        print("\n" + "="*50)
        print("PRODUCTION SMOKE TEST RESULTS")
        print("="*50)
        print(f"Mode: {results['mode'].upper()}")
        print(f"Total Tests: {results['total_tests']}")
        print(f"Successful: {results['successful_tests']}")
        print(f"Success Rate: {results['success_rate']:.1f}%")
        print("="*50)
        
        # Print individual test results
        for result in results['test_results']:
            status = "✅ PASS" if result['success'] else "❌ FAIL"
            print(f"{result['test_name']}: {status}")
        
        print("="*50)
        
        # Save detailed report
        report_file = f"/tmp/smoke_test_report_{int(time.time())}.json"
        with open(report_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"Detailed report saved to: {report_file}")
        
        # Exit with appropriate code
        if results['overall_success']:
            print("\n🎉 All smoke tests passed!")
            sys.exit(0)
        else:
            print(f"\n❌ {results['total_tests'] - results['successful_tests']} tests failed!")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Smoke tests failed: {str(e)}")
        sys.exit(2)

if __name__ == "__main__":
    main()
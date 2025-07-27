"""
Test Runner for Permission System
=================================

Runs all permission system tests with coverage reporting.
"""

import sys
import os
import unittest
import coverage
import time
from datetime import datetime

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
sys.path.insert(0, project_root)

# Test suites
from app.permissions.tests.unit.test_models import (
    TestPerfilUsuario, TestModuloSistema, TestFuncaoModulo,
    TestPermissaoUsuario, TestUsuarioVendedor, TestUsuarioEquipeVendas,
    TestLogPermissao, TestHierarchicalPermissions, TestPermissionTemplate
)
from app.permissions.tests.unit.test_edge_cases import (
    TestCircularDependencies, TestBatchOperationLimits,
    TestConcurrentAccess, TestDataIntegrity, TestBoundaryConditions
)
from app.permissions.tests.integration.test_api import TestPermissionAPI
from app.permissions.tests.integration.test_ui_interactions import (
    TestPermissionManagementUI, TestVendorTeamAssignmentUI,
    TestRealTimeUpdates, TestFormValidations,
    TestAccessibilityAndUsability, TestSearchAndFiltering
)
from app.permissions.tests.performance.test_performance import (
    TestQueryPerformance, TestBulkOperationPerformance,
    TestConcurrentAccessPerformance, TestMemoryUsage, TestAuditLogPerformance
)


class PermissionTestRunner:
    """Main test runner for permission system"""
    
    def __init__(self, verbosity=2, with_coverage=True):
        self.verbosity = verbosity
        self.with_coverage = with_coverage
        self.cov = None
        
    def setup_coverage(self):
        """Setup code coverage tracking"""
        if self.with_coverage:
            self.cov = coverage.Coverage(
                source=['app/permissions'],
                omit=[
                    '*/tests/*',
                    '*/migrations/*',
                    '*/__init__.py'
                ]
            )
            self.cov.start()
            
    def run_unit_tests(self):
        """Run unit tests"""
        print("\n" + "="*70)
        print("RUNNING UNIT TESTS")
        print("="*70)
        
        unit_suite = unittest.TestSuite()
        
        # Model tests
        unit_suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestPerfilUsuario))
        unit_suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestModuloSistema))
        unit_suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestFuncaoModulo))
        unit_suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestPermissaoUsuario))
        unit_suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestUsuarioVendedor))
        unit_suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestUsuarioEquipeVendas))
        unit_suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestLogPermissao))
        unit_suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestHierarchicalPermissions))
        unit_suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestPermissionTemplate))
        
        # Edge case tests
        unit_suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestCircularDependencies))
        unit_suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestBatchOperationLimits))
        unit_suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestConcurrentAccess))
        unit_suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestDataIntegrity))
        unit_suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestBoundaryConditions))
        
        runner = unittest.TextTestRunner(verbosity=self.verbosity)
        result = runner.run(unit_suite)
        
        return result
        
    def run_integration_tests(self):
        """Run integration tests"""
        print("\n" + "="*70)
        print("RUNNING INTEGRATION TESTS")
        print("="*70)
        
        integration_suite = unittest.TestSuite()
        
        # API tests
        integration_suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestPermissionAPI))
        
        # UI tests
        integration_suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestPermissionManagementUI))
        integration_suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestVendorTeamAssignmentUI))
        integration_suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestRealTimeUpdates))
        integration_suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestFormValidations))
        integration_suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestAccessibilityAndUsability))
        integration_suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestSearchAndFiltering))
        
        runner = unittest.TextTestRunner(verbosity=self.verbosity)
        result = runner.run(integration_suite)
        
        return result
        
    def run_performance_tests(self):
        """Run performance tests"""
        print("\n" + "="*70)
        print("RUNNING PERFORMANCE TESTS")
        print("="*70)
        
        performance_suite = unittest.TestSuite()
        
        performance_suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestQueryPerformance))
        performance_suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestBulkOperationPerformance))
        performance_suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestConcurrentAccessPerformance))
        performance_suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestMemoryUsage))
        performance_suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestAuditLogPerformance))
        
        runner = unittest.TextTestRunner(verbosity=self.verbosity)
        result = runner.run(performance_suite)
        
        return result
        
    def generate_coverage_report(self):
        """Generate coverage report"""
        if self.cov:
            self.cov.stop()
            
            print("\n" + "="*70)
            print("CODE COVERAGE REPORT")
            print("="*70)
            
            # Print to console
            self.cov.report()
            
            # Generate HTML report
            html_dir = os.path.join(project_root, 'htmlcov_permissions')
            self.cov.html_report(directory=html_dir)
            print(f"\nDetailed HTML coverage report generated in: {html_dir}")
            
            # Generate XML for CI/CD
            self.cov.xml_report(outfile='coverage_permissions.xml')
            
    def run_all(self, test_types=None):
        """Run all or specified test types"""
        if test_types is None:
            test_types = ['unit', 'integration', 'performance']
            
        self.setup_coverage()
        
        results = {
            'start_time': datetime.now(),
            'test_results': {},
            'summary': {
                'total': 0,
                'passed': 0,
                'failed': 0,
                'errors': 0,
                'skipped': 0
            }
        }
        
        # Run tests based on type
        if 'unit' in test_types:
            result = self.run_unit_tests()
            results['test_results']['unit'] = self._process_result(result)
            self._update_summary(results['summary'], result)
            
        if 'integration' in test_types:
            result = self.run_integration_tests()
            results['test_results']['integration'] = self._process_result(result)
            self._update_summary(results['summary'], result)
            
        if 'performance' in test_types:
            result = self.run_performance_tests()
            results['test_results']['performance'] = self._process_result(result)
            self._update_summary(results['summary'], result)
            
        results['end_time'] = datetime.now()
        results['duration'] = (results['end_time'] - results['start_time']).total_seconds()
        
        # Generate coverage report
        if self.with_coverage:
            self.generate_coverage_report()
            
        # Print summary
        self._print_summary(results)
        
        return results
        
    def _process_result(self, result):
        """Process test result"""
        return {
            'tests_run': result.testsRun,
            'failures': len(result.failures),
            'errors': len(result.errors),
            'skipped': len(result.skipped) if hasattr(result, 'skipped') else 0,
            'success': result.wasSuccessful()
        }
        
    def _update_summary(self, summary, result):
        """Update summary with test result"""
        summary['total'] += result.testsRun
        summary['failed'] += len(result.failures)
        summary['errors'] += len(result.errors)
        summary['skipped'] += len(result.skipped) if hasattr(result, 'skipped') else 0
        summary['passed'] += result.testsRun - len(result.failures) - len(result.errors)
        
    def _print_summary(self, results):
        """Print test summary"""
        print("\n" + "="*70)
        print("TEST SUMMARY")
        print("="*70)
        
        summary = results['summary']
        print(f"Total Tests: {summary['total']}")
        print(f"Passed: {summary['passed']} ({summary['passed']/summary['total']*100:.1f}%)")
        print(f"Failed: {summary['failed']}")
        print(f"Errors: {summary['errors']}")
        print(f"Skipped: {summary['skipped']}")
        print(f"Duration: {results['duration']:.2f} seconds")
        
        # Results by type
        print("\nResults by Test Type:")
        for test_type, result in results['test_results'].items():
            status = "✅ PASSED" if result['success'] else "❌ FAILED"
            print(f"  {test_type.upper()}: {status} ({result['tests_run']} tests)")
            
        print("="*70)


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Run permission system tests')
    parser.add_argument(
        '--types',
        nargs='+',
        choices=['unit', 'integration', 'performance', 'all'],
        default=['all'],
        help='Types of tests to run'
    )
    parser.add_argument(
        '--no-coverage',
        action='store_true',
        help='Disable coverage reporting'
    )
    parser.add_argument(
        '--verbosity',
        type=int,
        choices=[0, 1, 2],
        default=2,
        help='Test output verbosity'
    )
    
    args = parser.parse_args()
    
    # Process test types
    if 'all' in args.types:
        test_types = ['unit', 'integration', 'performance']
    else:
        test_types = args.types
        
    # Create and run test runner
    runner = PermissionTestRunner(
        verbosity=args.verbosity,
        with_coverage=not args.no_coverage
    )
    
    results = runner.run_all(test_types)
    
    # Exit with appropriate code
    if results['summary']['failed'] > 0 or results['summary']['errors'] > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == '__main__':
    main()
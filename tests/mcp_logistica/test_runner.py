"""
Test runner with coverage reporting for MCP Logística
"""

import pytest
import sys
import os
from datetime import datetime
import json


def run_all_tests():
    """Run all tests with coverage reporting"""
    
    # Configure pytest arguments
    args = [
        '-v',  # Verbose
        '--tb=short',  # Short traceback
        '--cov=app.mcp_logistica',  # Coverage for MCP module
        '--cov-report=html:tests/mcp_logistica/reports/coverage',  # HTML coverage
        '--cov-report=term-missing',  # Terminal coverage with missing lines
        '--cov-report=json:tests/mcp_logistica/reports/coverage.json',  # JSON coverage
        '--junit-xml=tests/mcp_logistica/reports/junit.xml',  # JUnit XML report
        '--html=tests/mcp_logistica/reports/test_report.html',  # HTML test report
        '--self-contained-html',  # Self-contained HTML
        'tests/mcp_logistica'  # Test directory
    ]
    
    # Run tests
    exit_code = pytest.main(args)
    
    # Generate summary report
    generate_summary_report()
    
    return exit_code


def run_domain_tests(domain):
    """Run tests for specific domain"""
    
    domains = {
        'nlp': 'tests/mcp_logistica/nlp',
        'intent': 'tests/mcp_logistica/intent',
        'entity': 'tests/mcp_logistica/entity',
        'sql': 'tests/mcp_logistica/sql',
        'human_loop': 'tests/mcp_logistica/human_loop',
        'claude': 'tests/mcp_logistica/claude',
        'api': 'tests/mcp_logistica/api',
        'security': 'tests/mcp_logistica/security',
        'persistence': 'tests/mcp_logistica/persistence',
        'integration': 'tests/mcp_logistica/integration',
        'performance': 'tests/mcp_logistica/performance'
    }
    
    if domain not in domains:
        print(f"Domínio inválido: {domain}")
        print(f"Domínios disponíveis: {', '.join(domains.keys())}")
        return 1
        
    args = [
        '-v',
        '--tb=short',
        f'--cov=app.mcp_logistica',
        f'--cov-report=html:tests/mcp_logistica/reports/{domain}_coverage',
        '--cov-report=term-missing',
        domains[domain]
    ]
    
    return pytest.main(args)


def generate_summary_report():
    """Generate summary report of all tests"""
    
    report_path = 'tests/mcp_logistica/reports/summary.json'
    
    # Load coverage data if exists
    coverage_data = {}
    coverage_file = 'tests/mcp_logistica/reports/coverage.json'
    if os.path.exists(coverage_file):
        with open(coverage_file, 'r') as f:
            coverage_data = json.load(f)
    
    # Create summary
    summary = {
        'timestamp': datetime.now().isoformat(),
        'coverage': {
            'total_coverage': coverage_data.get('totals', {}).get('percent_covered', 0),
            'files': coverage_data.get('files', {})
        },
        'test_categories': {
            'nlp': 'Processamento de linguagem natural em português',
            'intent': 'Classificação de intenções',
            'entity': 'Mapeamento de entidades',
            'sql': 'Geração e execução SQL',
            'human_loop': 'Sistema de confirmação',
            'claude': 'Integração com Claude',
            'api': 'Endpoints REST',
            'security': 'Validações de segurança',
            'persistence': 'Persistência e aprendizado'
        }
    }
    
    # Save summary
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, 'w') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
        
    print(f"\n📊 Relatório de resumo salvo em: {report_path}")
    print(f"📈 Cobertura total: {summary['coverage']['total_coverage']:.1f}%")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='MCP Logística Test Runner')
    parser.add_argument('--domain', help='Run tests for specific domain')
    parser.add_argument('--performance', action='store_true', help='Run performance tests')
    parser.add_argument('--security', action='store_true', help='Run security tests')
    
    args = parser.parse_args()
    
    if args.domain:
        exit_code = run_domain_tests(args.domain)
    elif args.performance:
        exit_code = run_domain_tests('performance')
    elif args.security:
        exit_code = run_domain_tests('security')
    else:
        exit_code = run_all_tests()
        
    sys.exit(exit_code)
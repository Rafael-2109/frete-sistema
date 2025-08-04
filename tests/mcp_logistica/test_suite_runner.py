"""
Complete test suite runner for MCP Logística
"""

import pytest
import sys
import os
from datetime import datetime
import json
import subprocess


class MCPTestSuite:
    """Orchestrates the complete test suite execution"""
    
    def __init__(self):
        self.test_categories = {
            'nlp': {
                'name': 'Processamento de Linguagem Natural',
                'path': 'tests/mcp_logistica/nlp',
                'critical': True
            },
            'intent': {
                'name': 'Classificação de Intenções',
                'path': 'tests/mcp_logistica/intent',
                'critical': True
            },
            'entity': {
                'name': 'Mapeamento de Entidades',
                'path': 'tests/mcp_logistica/entity',
                'critical': True
            },
            'sql': {
                'name': 'Geração e Execução SQL',
                'path': 'tests/mcp_logistica/sql',
                'critical': True
            },
            'human_loop': {
                'name': 'Sistema Human-in-the-Loop',
                'path': 'tests/mcp_logistica/human_loop',
                'critical': False
            },
            'claude': {
                'name': 'Integração Claude 4 Sonnet',
                'path': 'tests/mcp_logistica/claude',
                'critical': False
            },
            'api': {
                'name': 'Endpoints REST API',
                'path': 'tests/mcp_logistica/api',
                'critical': True
            },
            'security': {
                'name': 'Validações de Segurança',
                'path': 'tests/mcp_logistica/security',
                'critical': True
            },
            'persistence': {
                'name': 'Persistência e Aprendizado',
                'path': 'tests/mcp_logistica/persistence',
                'critical': False
            },
            'integration': {
                'name': 'Testes de Integração',
                'path': 'tests/mcp_logistica/integration',
                'critical': True
            }
        }
        
    def run_all_tests(self, verbose=True, coverage=True):
        """Execute all test categories"""
        print("🚀 Iniciando bateria completa de testes MCP Logística")
        print("=" * 60)
        
        start_time = datetime.now()
        results = {}
        total_passed = 0
        total_failed = 0
        
        # Configure pytest arguments
        base_args = ['-v'] if verbose else []
        if coverage:
            base_args.extend([
                '--cov=app.mcp_logistica',
                '--cov-report=term-missing',
                '--cov-report=html:tests/mcp_logistica/reports/coverage'
            ])
            
        # Run each category
        for category, info in self.test_categories.items():
            print(f"\n📋 Executando: {info['name']}")
            print("-" * 40)
            
            args = base_args + [info['path']]
            result = pytest.main(args)
            
            passed = result == 0
            results[category] = {
                'name': info['name'],
                'passed': passed,
                'critical': info['critical'],
                'exit_code': result
            }
            
            if passed:
                print(f"✅ {info['name']} - PASSOU")
                total_passed += 1
            else:
                print(f"❌ {info['name']} - FALHOU")
                total_failed += 1
                
        # Summary
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        self._print_summary(results, total_passed, total_failed, duration)
        self._generate_report(results, duration)
        
        # Return non-zero if any critical test failed
        critical_failures = any(
            not r['passed'] and r['critical'] 
            for r in results.values()
        )
        
        return 1 if critical_failures else 0
        
    def run_category(self, category, verbose=True):
        """Run tests for specific category"""
        if category not in self.test_categories:
            print(f"❌ Categoria '{category}' não encontrada")
            print(f"Categorias disponíveis: {', '.join(self.test_categories.keys())}")
            return 1
            
        info = self.test_categories[category]
        print(f"🧪 Executando testes: {info['name']}")
        
        args = ['-v'] if verbose else []
        args.extend([
            '--cov=app.mcp_logistica',
            '--cov-report=term',
            info['path']
        ])
        
        return pytest.main(args)
        
    def run_security_tests(self):
        """Run only security tests"""
        print("🔒 Executando testes de segurança")
        return self.run_category('security', verbose=True)
        
    def run_performance_tests(self):
        """Run performance benchmarks"""
        print("⚡ Executando testes de performance")
        
        args = [
            '-v',
            '-k', 'performance',
            '--benchmark-only',
            'tests/mcp_logistica'
        ]
        
        return pytest.main(args)
        
    def _print_summary(self, results, passed, failed, duration):
        """Print test execution summary"""
        print("\n" + "=" * 60)
        print("📊 RESUMO DA EXECUÇÃO")
        print("=" * 60)
        
        print(f"\n⏱️  Duração total: {duration:.2f} segundos")
        print(f"✅ Categorias aprovadas: {passed}")
        print(f"❌ Categorias reprovadas: {failed}")
        
        if failed > 0:
            print("\n⚠️  Categorias com falhas:")
            for category, result in results.items():
                if not result['passed']:
                    critical = "CRÍTICO" if result['critical'] else "Não crítico"
                    print(f"  - {result['name']} ({critical})")
                    
        print("\n📈 Taxa de sucesso: {:.1f}%".format(
            (passed / (passed + failed)) * 100
        ))
        
    def _generate_report(self, results, duration):
        """Generate detailed JSON report"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'duration_seconds': duration,
            'summary': {
                'total_categories': len(results),
                'passed': sum(1 for r in results.values() if r['passed']),
                'failed': sum(1 for r in results.values() if not r['passed']),
                'critical_failures': sum(
                    1 for r in results.values() 
                    if not r['passed'] and r['critical']
                )
            },
            'categories': results,
            'environment': {
                'python_version': sys.version,
                'platform': sys.platform,
                'cwd': os.getcwd()
            }
        }
        
        report_path = 'tests/mcp_logistica/reports/test_summary.json'
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
            
        print(f"\n📄 Relatório detalhado salvo em: {report_path}")
        
    def check_requirements(self):
        """Check if all test requirements are installed"""
        print("🔍 Verificando dependências de teste...")
        
        required = [
            'pytest', 'pytest-cov', 'pytest-html', 
            'pytest-mock', 'freezegun', 'factory-boy'
        ]
        
        missing = []
        for package in required:
            try:
                __import__(package.replace('-', '_'))
            except ImportError:
                missing.append(package)
                
        if missing:
            print(f"❌ Pacotes faltando: {', '.join(missing)}")
            print("Execute: pip install -r tests/mcp_logistica/requirements_test.txt")
            return False
            
        print("✅ Todas as dependências instaladas")
        return True


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='MCP Logística - Suíte de Testes'
    )
    parser.add_argument(
        '--category', '-c',
        help='Executar categoria específica de testes'
    )
    parser.add_argument(
        '--security', '-s',
        action='store_true',
        help='Executar apenas testes de segurança'
    )
    parser.add_argument(
        '--performance', '-p',
        action='store_true',
        help='Executar testes de performance'
    )
    parser.add_argument(
        '--no-coverage',
        action='store_true',
        help='Desabilitar relatório de cobertura'
    )
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Modo silencioso'
    )
    
    args = parser.parse_args()
    
    # Initialize test suite
    suite = MCPTestSuite()
    
    # Check requirements first
    if not suite.check_requirements():
        return 1
        
    # Run appropriate tests
    if args.security:
        return suite.run_security_tests()
    elif args.performance:
        return suite.run_performance_tests()
    elif args.category:
        return suite.run_category(args.category, verbose=not args.quiet)
    else:
        return suite.run_all_tests(
            verbose=not args.quiet,
            coverage=not args.no_coverage
        )


if __name__ == '__main__':
    sys.exit(main())
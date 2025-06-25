#!/usr/bin/env python3
"""
🧪 TESTES CRÍTICOS - Validação do Mapeamento Semântico
Foco na correção do campo "origem" e outros campos críticos
"""

import unittest
import sys
import os
from typing import Dict, List, Any

# Adicionar path do projeto
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from claude_ai.mapeamento_semantico import get_mapeamento_semantico

class TestSemanticMappingCritical(unittest.TestCase):
    """Testes críticos para validar mapeamentos essenciais"""
    
    def setUp(self):
        """Setup para cada teste"""
        self.mapeamento = get_mapeamento_semantico()
        
    def test_origem_campo_relacionamento_critico(self):
        """TESTE CRÍTICO: Campo origem deve mapear para num_pedido, não localização"""
        
        # Termos que devem mapear para campo origem
        consultas_origem = [
            "número do pedido",
            "num pedido",
            "pedido origem",
            "origem do faturamento",
            "codigo do pedido"
        ]
        
        for consulta in consultas_origem:
            with self.subTest(consulta=consulta):
                resultado = self.mapeamento.mapear_termo_natural(consulta)
                
                # Deve encontrar mapeamento
                self.assertGreater(len(resultado), 0, 
                    f"Termo '{consulta}' não foi mapeado")
                
                # Primeiro resultado deve ser do campo origem
                primeiro_resultado = resultado[0]
                self.assertEqual(primeiro_resultado['campo_busca'], 'origem',
                    f"Termo '{consulta}' não mapeou para campo 'origem'")
                
                # Deve ser do modelo RelatorioFaturamentoImportado
                self.assertEqual(primeiro_resultado['modelo'], 'RelatorioFaturamentoImportado',
                    f"Termo '{consulta}' não mapeou para modelo correto")
                
                # Verificar que NÃO contém termos de localização
                termos_mapeamento = self.mapeamento.mapeamentos['origem']['termos_naturais']
                termos_localizacao = ['localização', 'local', 'lugar', 'região', 'cidade origem']
                
                for termo_loc in termos_localizacao:
                    self.assertNotIn(termo_loc, [t.lower() for t in termos_mapeamento],
                        f"Campo origem ainda contém termo de localização: {termo_loc}")
    
    def test_consulta_completa_origem_relacionamento(self):
        """Testa consulta completa que usa origem como relacionamento"""
        
        consultas_teste = [
            "faturamento da origem 567890",
            "pedidos que foram faturados",
            "numero do pedido na fatura",
            "origem dos pedidos faturados"
        ]
        
        for consulta in consultas_teste:
            with self.subTest(consulta=consulta):
                resultado = self.mapeamento.mapear_consulta_completa(consulta)
                
                # Deve encontrar o campo origem
                campos_encontrados = [m['campo_busca'] for m in resultado['mapeamentos_encontrados']]
                self.assertIn('origem', campos_encontrados,
                    f"Consulta '{consulta}' não identificou campo origem")
                
                # Deve identificar modelo correto
                self.assertIn('RelatorioFaturamentoImportado', resultado['modelos_envolvidos'],
                    f"Consulta '{consulta}' não identificou modelo de faturamento")
    
    def test_outros_campos_relacionamento_criticos(self):
        """Testa outros campos críticos de relacionamento"""
        
        campos_criticos = {
            'separacao_lote_id': {
                'consultas': ['lote separacao', 'id separacao', 'codigo separacao'],
                'modelo_esperado': 'Pedido'  # Baseado no README
            },
            'cnpj_cliente': {
                'consultas': ['cnpj cliente', 'cnpj do cliente'],
                'modelos_esperados': ['Pedido', 'EntregaMonitorada', 'RelatorioFaturamentoImportado']
            }
        }
        
        for campo, info in campos_criticos.items():
            for consulta in info['consultas']:
                with self.subTest(campo=campo, consulta=consulta):
                    resultado = self.mapeamento.mapear_termo_natural(consulta)
                    
                    if resultado:  # Se encontrou mapeamento
                        primeiro = resultado[0]
                        # Verificar se é um dos modelos esperados
                        if isinstance(info.get('modelo_esperado'), str):
                            esperados = [info['modelo_esperado']]
                        else:
                            esperados = info.get('modelos_esperados', [])
                        
                        if esperados:
                            self.assertIn(primeiro['modelo'], esperados,
                                f"Campo {campo} mapeou para modelo incorreto: {primeiro['modelo']}")
    
    def test_relacionamentos_essenciais(self):
        """Testa relacionamentos essenciais entre modelos"""
        
        relacionamentos_esperados = [
            ('RelatorioFaturamentoImportado.origem', 'Pedido.num_pedido'),
            ('Pedido.nf', 'EntregaMonitorada.numero_nf'),
            ('EmbarqueItem.separacao_lote_id', 'Pedido.separacao_lote_id')
        ]
        
        for origem, destino in relacionamentos_esperados:
            with self.subTest(relacionamento=f"{origem} -> {destino}"):
                # Verificar se os campos estão mapeados
                modelo_origem, campo_origem = origem.split('.')
                modelo_destino, campo_destino = destino.split('.')
                
                # Verificar se modelos existem nos mapeamentos
                modelos_mapeados = set()
                for mapeamento in self.mapeamento.mapeamentos.values():
                    modelos_mapeados.add(mapeamento['modelo'])
                
                self.assertIn(modelo_origem, modelos_mapeados,
                    f"Modelo {modelo_origem} não está mapeado")
                self.assertIn(modelo_destino, modelos_mapeados,
                    f"Modelo {modelo_destino} não está mapeado")
    
    def test_consultas_reais_usuarios(self):
        """Testa consultas reais que foram reportadas pelos usuários"""
        
        consultas_reais = [
            {
                'consulta': "Entregas do Assai em junho",
                'campos_esperados': ['cliente', 'data_embarque'],
                'modelos_esperados': ['EntregaMonitorada']
            },
            {
                'consulta': "Pedidos que faltam cotar",  
                'campos_esperados': ['status'],
                'modelos_esperados': ['Pedido']
            },
            {
                'consulta': "Faturamento da origem 567890",
                'campos_esperados': ['origem'],
                'modelos_esperados': ['RelatorioFaturamentoImportado']
            },
            {
                'consulta': "Status do embarque 1234",
                'campos_esperados': ['numero', 'status'],
                'modelos_esperados': ['Embarque']
            }
        ]
        
        for teste in consultas_reais:
            with self.subTest(consulta=teste['consulta']):
                resultado = self.mapeamento.mapear_consulta_completa(teste['consulta'])
                
                # Verificar se encontrou mapeamentos
                self.assertGreater(len(resultado['mapeamentos_encontrados']), 0,
                    f"Consulta '{teste['consulta']}' não encontrou mapeamentos")
                
                # Verificar modelos esperados
                for modelo_esperado in teste['modelos_esperados']:
                    self.assertIn(modelo_esperado, resultado['modelos_envolvidos'],
                        f"Consulta '{teste['consulta']}' não identificou modelo {modelo_esperado}")
    
    def test_campo_origem_observacao_presente(self):
        """Verifica se campo origem tem a observação explicativa"""
        
        mapeamento_origem = self.mapeamento.mapeamentos.get('origem')
        self.assertIsNotNone(mapeamento_origem, "Campo origem não encontrado")
        
        observacao = mapeamento_origem.get('observacao', '')
        self.assertIn('RELACIONAMENTO ESSENCIAL', observacao,
            "Campo origem não possui observação sobre relacionamento")
        self.assertIn('num_pedido', observacao,
            "Observação não menciona num_pedido")
        self.assertIn('conecta', observacao,
            "Observação não explica que conecta modelos")
    
    def test_performance_mapeamento(self):
        """Testa performance do mapeamento semântico"""
        import time
        
        consultas_teste = [
            "número do pedido",
            "cliente da entrega", 
            "data de embarque",
            "status da entrega",
            "origem do faturamento"
        ] * 20  # 100 consultas total
        
        inicio = time.time()
        
        for consulta in consultas_teste:
            resultado = self.mapeamento.mapear_termo_natural(consulta)
            self.assertIsNotNone(resultado)
        
        tempo_total = time.time() - inicio
        tempo_por_consulta = tempo_total / len(consultas_teste)
        
        # Performance deve ser < 10ms por consulta
        self.assertLess(tempo_por_consulta, 0.01,
            f"Mapeamento muito lento: {tempo_por_consulta:.4f}s por consulta")
        
        print(f"✅ Performance OK: {tempo_por_consulta*1000:.2f}ms por consulta")


class TestValidacaoReadme(unittest.TestCase):
    """Testes para validar conformidade com README_MAPEAMENTO_SEMANTICO_COMPLETO.md"""
    
    def setUp(self):
        self.mapeamento = get_mapeamento_semantico()
    
    def test_campo_origem_conforme_readme(self):
        """Valida se campo origem está conforme README"""
        
        # Baseado no README: "msm campo do Pedido 'num_pedido'"
        mapeamento_origem = self.mapeamento.mapeamentos.get('origem')
        self.assertIsNotNone(mapeamento_origem)
        
        # Deve ter termos relacionados a pedido
        termos = [t.lower() for t in mapeamento_origem['termos_naturais']]
        self.assertIn('numero do pedido', termos)
        self.assertIn('num pedido', termos)
        self.assertIn('pedido', termos)
        
        # NÃO deve ter termos de localização
        termos_localizacao_proibidos = [
            'localização', 'local', 'lugar', 'região', 'de onde veio'
        ]
        for termo_proibido in termos_localizacao_proibidos:
            self.assertNotIn(termo_proibido, termos,
                f"Campo origem contém termo proibido: {termo_proibido}")
    
    def test_modelos_essenciais_mapeados(self):
        """Verifica se modelos essenciais do README estão mapeados"""
        
        modelos_essenciais = [
            'Pedido',
            'EntregaMonitorada', 
            'RelatorioFaturamentoImportado',
            'Embarque',
            'EmbarqueItem'
        ]
        
        modelos_mapeados = set()
        for mapeamento in self.mapeamento.mapeamentos.values():
            modelos_mapeados.add(mapeamento['modelo'])
        
        for modelo in modelos_essenciais:
            self.assertIn(modelo, modelos_mapeados,
                f"Modelo essencial {modelo} não está mapeado")


def run_critical_tests():
    """Executa apenas os testes críticos"""
    
    print("🧪 EXECUTANDO TESTES CRÍTICOS DE VALIDAÇÃO")
    print("=" * 50)
    
    # Suite de testes críticos
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Adicionar testes críticos
    suite.addTests(loader.loadTestsFromTestCase(TestSemanticMappingCritical))
    suite.addTests(loader.loadTestsFromTestCase(TestValidacaoReadme))
    
    # Executar testes
    runner = unittest.TextTestRunner(verbosity=2)
    resultado = runner.run(suite)
    
    # Relatório
    print("\n" + "=" * 50)
    if resultado.wasSuccessful():
        print("✅ TODOS OS TESTES CRÍTICOS PASSARAM!")
        print(f"Executados: {resultado.testsRun} testes")
    else:
        print("❌ ALGUNS TESTES FALHARAM!")
        print(f"Falhas: {len(resultado.failures)}")
        print(f"Erros: {len(resultado.errors)}")
        
        for teste, erro in resultado.failures + resultado.errors:
            print(f"\n🚨 FALHA: {teste}")
            print(f"   {erro}")
    
    print("=" * 50)
    return resultado.wasSuccessful()


if __name__ == "__main__":
    # Executar testes críticos
    sucesso = run_critical_tests()
    
    if not sucesso:
        print("\n🚨 AÇÃO NECESSÁRIA: Corrigir falhas antes de continuar")
        sys.exit(1)
    else:
        print("\n🚀 VALIDAÇÃO CONCLUÍDA - Próxima etapa: Implementação")
        sys.exit(0) 
#!/usr/bin/env python3
"""
🔧 TESTE DE MÓDULOS INDIVIDUAIS
Foco: Testar se cada módulo funciona SOZINHO, sem orquestradores
"""

import os
import sys
import importlib
import traceback
from datetime import datetime
from typing import Dict, Any, List, Optional

class TestadorModulosIndividuais:
    
    def __init__(self):
        self.resultados = {
            'timestamp': datetime.now().isoformat(),
            'modulos_testados': 0,
            'modulos_funcionando': 0,
            'modulos_com_erro': 0,
            'detalhes': {}
        }
    
    def testar_modulo(self, caminho_modulo: str, nome_classe: Optional[str] = None) -> Dict[str, Any]:
        """Testa um módulo específico"""
        
        print(f"\n🔧 Testando módulo: {caminho_modulo}")
        
        try:
            # Converter caminho para import
            modulo_import = caminho_modulo.replace('/', '.').replace('.py', '')
            
            # Tentar importar
            modulo = importlib.import_module(modulo_import)
            
            resultado = {
                'import_ok': True,
                'classes_encontradas': [],
                'funcoes_encontradas': [],
                'erro': None
            }
            
            # Listar classes e funções
            for nome in dir(modulo):
                if not nome.startswith('_'):
                    obj = getattr(modulo, nome)
                    if isinstance(obj, type):
                        resultado['classes_encontradas'].append(nome)
                    elif callable(obj):
                        resultado['funcoes_encontradas'].append(nome)
            
            # Testar classe específica se fornecida
            if nome_classe and nome_classe in resultado['classes_encontradas']:
                try:
                    classe = getattr(modulo, nome_classe)
                    instancia = classe()
                    resultado['instancia_ok'] = True
                    resultado['metodos_instancia'] = [m for m in dir(instancia) if not m.startswith('_')]
                except Exception as e:
                    resultado['instancia_ok'] = False
                    resultado['erro_instancia'] = str(e)
            
            print(f"   ✅ Import OK - {len(resultado['classes_encontradas'])} classes, {len(resultado['funcoes_encontradas'])} funções")
            return resultado
            
        except Exception as e:
            print(f"   ❌ Erro no import: {e}")
            return {
                'import_ok': False,
                'erro': str(e),
                'traceback': traceback.format_exc()
            }
    
    def testar_modulos_principais(self):
        """Testa módulos principais mencionados pelo usuário"""
        
        print("🔧 TESTANDO MÓDULOS INDIVIDUAIS")
        print("=" * 50)
        
        # Módulos mencionados pelo usuário
        modulos_teste = [
            ('validators/structural_validator.py', 'StructuralAI'),
            ('analyzers/structural_analyzer.py', 'StructuralAnalyzer'),
            ('providers/data_provider.py', 'DataProvider'),
            ('learners/human_in_loop_learning.py', 'HumanInLoopLearning'),
        ]
        
        for caminho, classe in modulos_teste:
            if os.path.exists(caminho):
                resultado = self.testar_modulo(caminho, classe)
                self.resultados['detalhes'][caminho] = resultado
                self.resultados['modulos_testados'] += 1
                
                if resultado['import_ok']:
                    self.resultados['modulos_funcionando'] += 1
                else:
                    self.resultados['modulos_com_erro'] += 1
            else:
                print(f"❌ Arquivo não encontrado: {caminho}")
                self.resultados['detalhes'][caminho] = {
                    'import_ok': False,
                    'erro': 'Arquivo não encontrado'
                }
                self.resultados['modulos_testados'] += 1
                self.resultados['modulos_com_erro'] += 1
    
    def testar_todos_modulos_pastas(self):
        """Testa todos os módulos das pastas principais"""
        
        print("\n🔧 TESTANDO TODOS OS MÓDULOS POR PASTA")
        print("=" * 50)
        
        pastas = ['analyzers', 'processors', 'learners', 'providers', 'validators']
        
        for pasta in pastas:
            if os.path.exists(pasta):
                print(f"\n📁 Pasta: {pasta}")
                
                for arquivo in os.listdir(pasta):
                    if arquivo.endswith('.py') and arquivo != '__init__.py':
                        caminho = f"{pasta}/{arquivo}"
                        resultado = self.testar_modulo(caminho)
                        
                        self.resultados['detalhes'][caminho] = resultado
                        self.resultados['modulos_testados'] += 1
                        
                        if resultado['import_ok']:
                            self.resultados['modulos_funcionando'] += 1
                        else:
                            self.resultados['modulos_com_erro'] += 1
            else:
                print(f"❌ Pasta não encontrada: {pasta}")
    
    def gerar_relatorio(self):
        """Gera relatório final dos testes"""
        
        print("\n📊 RELATÓRIO FINAL - MÓDULOS INDIVIDUAIS")
        print("=" * 50)
        
        total = self.resultados['modulos_testados']
        funcionando = self.resultados['modulos_funcionando']
        com_erro = self.resultados['modulos_com_erro']
        
        print(f"📊 Total testados: {total}")
        print(f"✅ Funcionando: {funcionando}")
        print(f"❌ Com erro: {com_erro}")
        
        if total > 0:
            taxa_sucesso = (funcionando / total) * 100
            print(f"📈 Taxa de sucesso: {taxa_sucesso:.1f}%")
        
        print("\n🔧 MÓDULOS COM ERRO:")
        for caminho, resultado in self.resultados['detalhes'].items():
            if not resultado['import_ok']:
                print(f"   ❌ {caminho}: {resultado['erro']}")
        
        print("\n✅ MÓDULOS FUNCIONANDO:")
        for caminho, resultado in self.resultados['detalhes'].items():
            if resultado['import_ok']:
                classes = len(resultado.get('classes_encontradas', []))
                funcoes = len(resultado.get('funcoes_encontradas', []))
                print(f"   ✅ {caminho}: {classes} classes, {funcoes} funções")
        
        # Salvar relatório
        import json
        with open('RELATORIO_MODULOS_INDIVIDUAIS.json', 'w', encoding='utf-8') as f:
            json.dump(self.resultados, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Relatório salvo em: RELATORIO_MODULOS_INDIVIDUAIS.json")
        
        return self.resultados

def main():
    """Função principal - foco nos módulos individuais"""
    try:
        testador = TestadorModulosIndividuais()
        
        # Testar módulos principais primeiro
        testador.testar_modulos_principais()
        
        # Testar todos os módulos das pastas
        testador.testar_todos_modulos_pastas()
        
        # Gerar relatório
        resultado = testador.gerar_relatorio()
        
        print("\n🎯 PRÓXIMO PASSO:")
        print("   Corrigir os módulos com erro ANTES de mexer nos orquestradores")
        
        return resultado
        
    except Exception as e:
        print(f"\n❌ Erro durante teste: {e}")
        traceback.print_exc()
        return None

if __name__ == "__main__":
    main() 
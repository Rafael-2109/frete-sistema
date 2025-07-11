#!/usr/bin/env python3
"""
🧱 TESTE DE TODOS OS TIJOLOS
Testar todos os módulos de função única + managers + coordinators
EXCLUIR apenas maestros de alto nível
"""

import os
import sys
import importlib
import traceback
import json
from datetime import datetime
from typing import Dict, Any, List

class TestadorTijolos:
    
    def __init__(self):
        self.resultados = {
            'timestamp': datetime.now().isoformat(),
            'total_testados': 0,
            'funcionando': 0,
            'com_erro': 0,
            'detalhes': {},
            'maestros_excluidos': []
        }
        
        # Maestros de ALTO NÍVEL que devem ser excluídos
        self.maestros_alto_nivel = [
            'integration/integration_manager.py',
            'integration/advanced/advanced_integration.py',
            'multi_agent/system.py',
            '__init__.py'  # Arquivo principal de inicialização
        ]
    
    def eh_maestro_alto_nivel(self, caminho: str) -> bool:
        """Verifica se é um maestro de alto nível"""
        return caminho in self.maestros_alto_nivel
    
    def testar_modulo_individual(self, caminho: str) -> Dict[str, Any]:
        """Testa um módulo individual"""
        
        print(f"🧱 Testando: {caminho}")
        
        try:
            # Converter para import
            modulo_import = caminho.replace('/', '.').replace('.py', '')
            
            # Importar
            modulo = importlib.import_module(modulo_import)
            
            # Analisar conteúdo
            classes = []
            funcoes = []
            
            for nome in dir(modulo):
                if not nome.startswith('_'):
                    obj = getattr(modulo, nome)
                    if isinstance(obj, type):
                        classes.append(nome)
                    elif callable(obj):
                        funcoes.append(nome)
            
            resultado = {
                'status': 'funcionando',
                'classes': classes,
                'funcoes': funcoes,
                'total_classes': len(classes),
                'total_funcoes': len(funcoes),
                'erro': None
            }
            
            print(f"   ✅ OK - {len(classes)} classes, {len(funcoes)} funções")
            return resultado
            
        except Exception as e:
            print(f"   ❌ ERRO: {str(e)}")
            return {
                'status': 'erro',
                'erro': str(e),
                'classes': [],
                'funcoes': [],
                'total_classes': 0,
                'total_funcoes': 0
            }
    
    def descobrir_todos_modulos(self) -> List[str]:
        """Descobre todos os módulos Python no sistema"""
        
        modulos_encontrados = []
        
        # Pastas principais para escanear
        pastas_principais = [
            'analyzers', 'processors', 'learners', 'providers', 'coordinators',
            'mappers', 'validators', 'enrichers', 'tools', 'suggestions', 
            'memorizers', 'conversers', 'scanning', 'commands', 'utils',
            'integration', 'semantic', 'intelligence', 'multi_agent',
            'orchestrators', 'security', 'config', 'loaders'
        ]
        
        for pasta in pastas_principais:
            if os.path.exists(pasta):
                # Escanear recursivamente
                for root, dirs, files in os.walk(pasta):
                    for file in files:
                        if file.endswith('.py') and file != '__init__.py':
                            caminho = os.path.join(root, file).replace('\\', '/')
                            modulos_encontrados.append(caminho)
        
        # Adicionar arquivos Python na raiz (exceto __init__.py)
        for arquivo in os.listdir('.'):
            if arquivo.endswith('.py') and arquivo != '__init__.py':
                modulos_encontrados.append(arquivo)
        
        return modulos_encontrados
    
    def executar_teste_completo(self):
        """Executa teste completo de todos os tijolos"""
        
        print("🧱 TESTE COMPLETO DE TODOS OS TIJOLOS")
        print("=" * 60)
        
        # Descobrir todos os módulos
        print("\n📋 Descobrindo módulos...")
        todos_modulos = self.descobrir_todos_modulos()
        print(f"📊 Total de módulos encontrados: {len(todos_modulos)}")
        
        # Filtrar maestros de alto nível
        modulos_para_testar = []
        maestros_excluidos = []
        
        for modulo in todos_modulos:
            if self.eh_maestro_alto_nivel(modulo):
                maestros_excluidos.append(modulo)
                print(f"🚫 Excluindo maestro: {modulo}")
            else:
                modulos_para_testar.append(modulo)
        
        self.resultados['maestros_excluidos'] = maestros_excluidos
        
        print(f"\n📊 Módulos para testar: {len(modulos_para_testar)}")
        print(f"📊 Maestros excluídos: {len(maestros_excluidos)}")
        
        # Testar cada módulo
        print(f"\n🧱 TESTANDO {len(modulos_para_testar)} MÓDULOS:")
        print("=" * 60)
        
        for modulo in modulos_para_testar:
            resultado = self.testar_modulo_individual(modulo)
            self.resultados['detalhes'][modulo] = resultado
            self.resultados['total_testados'] += 1
            
            if resultado['status'] == 'funcionando':
                self.resultados['funcionando'] += 1
            else:
                self.resultados['com_erro'] += 1
        
        # Gerar relatório final
        self.gerar_relatorio_final()
        
        return self.resultados
    
    def gerar_relatorio_final(self):
        """Gera relatório final detalhado"""
        
        print("\n📊 RELATÓRIO FINAL - TESTE DE TIJOLOS")
        print("=" * 60)
        
        total = self.resultados['total_testados']
        funcionando = self.resultados['funcionando']
        com_erro = self.resultados['com_erro']
        
        print(f"📊 ESTATÍSTICAS GERAIS:")
        print(f"   Total testados: {total}")
        print(f"   ✅ Funcionando: {funcionando}")
        print(f"   ❌ Com erro: {com_erro}")
        
        if total > 0:
            taxa_sucesso = (funcionando / total) * 100
            print(f"   📈 Taxa de sucesso: {taxa_sucesso:.1f}%")
        
        # Análise por pasta
        print(f"\n📁 ANÁLISE POR PASTA:")
        analise_pastas = {}
        
        for modulo, resultado in self.resultados['detalhes'].items():
            pasta = modulo.split('/')[0] if '/' in modulo else 'raiz'
            
            if pasta not in analise_pastas:
                analise_pastas[pasta] = {'total': 0, 'funcionando': 0, 'com_erro': 0}
            
            analise_pastas[pasta]['total'] += 1
            if resultado['status'] == 'funcionando':
                analise_pastas[pasta]['funcionando'] += 1
            else:
                analise_pastas[pasta]['com_erro'] += 1
        
        for pasta, stats in analise_pastas.items():
            taxa = (stats['funcionando'] / stats['total']) * 100 if stats['total'] > 0 else 0
            print(f"   📁 {pasta}: {stats['funcionando']}/{stats['total']} ({taxa:.1f}%)")
        
        # Módulos com erro
        print(f"\n❌ MÓDULOS COM ERRO:")
        for modulo, resultado in self.resultados['detalhes'].items():
            if resultado['status'] == 'erro':
                print(f"   ❌ {modulo}: {resultado['erro']}")
        
        # Top módulos funcionando
        print(f"\n✅ EXEMPLOS DE MÓDULOS FUNCIONANDO:")
        funcionando_list = [(m, r) for m, r in self.resultados['detalhes'].items() if r['status'] == 'funcionando']
        
        for modulo, resultado in funcionando_list[:10]:  # Mostrar 10 primeiros
            classes = resultado['total_classes']
            funcoes = resultado['total_funcoes']
            print(f"   ✅ {modulo}: {classes} classes, {funcoes} funções")
        
        if len(funcionando_list) > 10:
            print(f"   ... e mais {len(funcionando_list) - 10} módulos funcionando")
        
        # Salvar relatório
        with open('RELATORIO_TESTE_TIJOLOS_COMPLETO.json', 'w', encoding='utf-8') as f:
            json.dump(self.resultados, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Relatório salvo: RELATORIO_TESTE_TIJOLOS_COMPLETO.json")
        
        # Conclusão
        if total > 0:
            taxa_sucesso = (funcionando / total) * 100
            if taxa_sucesso >= 80:
                print(f"\n🟢 RESULTADO EXCELENTE: {taxa_sucesso:.1f}% dos tijolos funcionam!")
            elif taxa_sucesso >= 60:
                print(f"\n🟡 RESULTADO BOM: {taxa_sucesso:.1f}% dos tijolos funcionam")
            else:
                print(f"\n🔴 RESULTADO PREOCUPANTE: Apenas {taxa_sucesso:.1f}% dos tijolos funcionam")

def main():
    """Função principal"""
    try:
        testador = TestadorTijolos()
        resultado = testador.executar_teste_completo()
        
        print(f"\n🎯 PRÓXIMO PASSO:")
        print(f"   Com {resultado['funcionando']} tijolos funcionando,")
        print(f"   podemos começar a conectá-los progressivamente!")
        
        return resultado
        
    except Exception as e:
        print(f"\n❌ Erro durante teste: {e}")
        traceback.print_exc()
        return None

if __name__ == "__main__":
    main() 
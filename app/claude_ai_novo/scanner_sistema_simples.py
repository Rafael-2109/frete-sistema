#!/usr/bin/env python3
"""
🔍 SCANNER SISTEMA SIMPLES
=========================

Scanner simplificado para mapear o sistema claude_ai_novo
"""

import os
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

class ScannerSistemaSimples:
    """Scanner simples do sistema"""
    
    def __init__(self):
        self.base_path = Path(__file__).parent
        self.resultados = {
            'timestamp': datetime.now().isoformat(),
            'arquivos_python': [],
            'diretorios': [],
            'componentes_criticos': [],
            'estatisticas': {},
            'recomendacoes': []
        }
    
    def escanear_sistema(self):
        """Escaneia o sistema completo"""
        print("🔍 Iniciando escaneamento do sistema...")
        
        # Mapear arquivos Python
        arquivos_py = self._mapear_arquivos_python()
        print(f"📄 Encontrados {len(arquivos_py)} arquivos Python")
        
        # Mapear diretórios
        diretorios = self._mapear_diretorios()
        print(f"📁 Encontrados {len(diretorios)} diretórios")
        
        # Identificar componentes críticos
        criticos = self._identificar_componentes_criticos()
        print(f"⚡ Identificados {len(criticos)} componentes críticos")
        
        # Calcular estatísticas
        estatisticas = self._calcular_estatisticas(arquivos_py, diretorios)
        
        # Gerar recomendações
        recomendacoes = self._gerar_recomendacoes(estatisticas)
        
        # Compilar resultados
        self.resultados.update({
            'arquivos_python': arquivos_py,
            'diretorios': diretorios,
            'componentes_criticos': criticos,
            'estatisticas': estatisticas,
            'recomendacoes': recomendacoes
        })
        
        return self.resultados
    
    def _mapear_arquivos_python(self) -> List[Dict[str, Any]]:
        """Mapeia todos os arquivos Python"""
        arquivos = []
        
        for root, dirs, files in os.walk(self.base_path):
            # Ignorar diretórios desnecessários
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
            
            for file in files:
                if file.endswith('.py'):
                    file_path = Path(root) / file
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        info = {
                            'nome': file,
                            'caminho': str(file_path.relative_to(self.base_path)),
                            'tamanho_linhas': len(content.splitlines()),
                            'tamanho_bytes': len(content.encode('utf-8')),
                            'tem_classes': 'class ' in content,
                            'tem_funcoes': 'def ' in content,
                            'tem_imports': 'import ' in content,
                            'e_critico': self._avaliar_criticidade(file, content)
                        }
                        
                        arquivos.append(info)
                        
                    except Exception as e:
                        print(f"⚠️ Erro ao ler {file_path}: {e}")
        
        return arquivos
    
    def _mapear_diretorios(self) -> List[Dict[str, Any]]:
        """Mapeia todos os diretórios"""
        diretorios = []
        
        for root, dirs, files in os.walk(self.base_path):
            # Ignorar diretórios desnecessários
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
            
            for dir_name in dirs:
                dir_path = Path(root) / dir_name
                
                # Contar arquivos Python no diretório
                arquivos_py = len([f for f in os.listdir(dir_path) if f.endswith('.py')])
                
                info = {
                    'nome': dir_name,
                    'caminho': str(dir_path.relative_to(self.base_path)),
                    'arquivos_python': arquivos_py,
                    'e_critico': self._avaliar_criticidade_diretorio(dir_name)
                }
                
                diretorios.append(info)
        
        return diretorios
    
    def _identificar_componentes_criticos(self) -> List[str]:
        """Identifica componentes críticos"""
        componentes_criticos = []
        
        # Diretórios críticos conhecidos
        diretorios_criticos = [
            'orchestrators', 'integration', 'processors', 'analyzers',
            'validators', 'mappers', 'providers', 'utils', 'commands'
        ]
        
        for diretorio in diretorios_criticos:
            dir_path = self.base_path / diretorio
            if dir_path.exists():
                componentes_criticos.append(diretorio)
        
        # Arquivos críticos conhecidos
        arquivos_criticos = [
            '__init__.py', 'main_orchestrator.py', 'integration_manager.py',
            'processor_registry.py', 'orchestrator_manager.py'
        ]
        
        for arquivo in arquivos_criticos:
            for root, dirs, files in os.walk(self.base_path):
                if arquivo in files:
                    file_path = Path(root) / arquivo
                    rel_path = str(file_path.relative_to(self.base_path))
                    componentes_criticos.append(rel_path)
        
        return list(set(componentes_criticos))
    
    def _calcular_estatisticas(self, arquivos: List[Dict], diretorios: List[Dict]) -> Dict[str, Any]:
        """Calcula estatísticas do sistema"""
        total_linhas = sum(arq['tamanho_linhas'] for arq in arquivos)
        total_bytes = sum(arq['tamanho_bytes'] for arq in arquivos)
        
        arquivos_com_classes = len([arq for arq in arquivos if arq['tem_classes']])
        arquivos_com_funcoes = len([arq for arq in arquivos if arq['tem_funcoes']])
        arquivos_criticos = len([arq for arq in arquivos if arq['e_critico']])
        
        diretorios_criticos = len([dir for dir in diretorios if dir['e_critico']])
        
        return {
            'total_arquivos': len(arquivos),
            'total_diretorios': len(diretorios),
            'total_linhas_codigo': total_linhas,
            'total_bytes': total_bytes,
            'arquivos_com_classes': arquivos_com_classes,
            'arquivos_com_funcoes': arquivos_com_funcoes,
            'arquivos_criticos': arquivos_criticos,
            'diretorios_criticos': diretorios_criticos,
            'media_linhas_por_arquivo': round(total_linhas / len(arquivos) if arquivos else 0, 1),
            'percentual_arquivos_criticos': round((arquivos_criticos / len(arquivos)) * 100 if arquivos else 0, 1)
        }
    
    def _gerar_recomendacoes(self, stats: Dict[str, Any]) -> List[str]:
        """Gera recomendações baseadas nas estatísticas"""
        recomendacoes = []
        
        # Análise de tamanho
        if stats['media_linhas_por_arquivo'] > 500:
            recomendacoes.append("🔧 REFATORAÇÃO: Arquivos muito grandes (média > 500 linhas)")
        
        # Análise de criticidade
        if stats['percentual_arquivos_criticos'] > 50:
            recomendacoes.append("⚡ REDUNDÂNCIA: Muitos arquivos críticos - considerar fallbacks")
        
        # Análise de estrutura
        if stats['arquivos_com_classes'] < stats['total_arquivos'] * 0.3:
            recomendacoes.append("🏗️ ESTRUTURA: Poucos arquivos com classes - considerar refatoração OOP")
        
        # Análise de cobertura
        if stats['total_arquivos'] > 100:
            recomendacoes.append("📊 TESTES: Sistema grande - implementar testes automatizados")
        
        return recomendacoes
    
    def _avaliar_criticidade(self, nome_arquivo: str, conteudo: str) -> bool:
        """Avalia se um arquivo é crítico"""
        # Palavras-chave críticas
        palavras_criticas = [
            'orchestrator', 'manager', 'integration', 'processor',
            'main', 'core', 'base', 'registry'
        ]
        
        nome_lower = nome_arquivo.lower()
        return any(palavra in nome_lower for palavra in palavras_criticas)
    
    def _avaliar_criticidade_diretorio(self, nome_diretorio: str) -> bool:
        """Avalia se um diretório é crítico"""
        diretorios_criticos = [
            'orchestrators', 'integration', 'processors', 'analyzers',
            'validators', 'mappers', 'providers', 'utils', 'commands'
        ]
        
        return nome_diretorio in diretorios_criticos
    
    def salvar_resultados(self, filename: Optional[str] = None):
        """Salva os resultados em arquivo JSON"""
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"scan_sistema_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.resultados, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Resultados salvos em: {filename}")
        return filename
    
    def imprimir_resumo(self):
        """Imprime resumo dos resultados"""
        stats = self.resultados['estatisticas']
        
        print("\n" + "="*60)
        print("📊 RESUMO DO ESCANEAMENTO DO SISTEMA")
        print("="*60)
        
        print(f"📁 Total de arquivos: {stats['total_arquivos']}")
        print(f"📂 Total de diretórios: {stats['total_diretorios']}")
        print(f"📄 Total de linhas: {stats['total_linhas_codigo']:,}")
        print(f"💾 Total de bytes: {stats['total_bytes']:,}")
        
        print(f"\n🏛️ Arquivos com classes: {stats['arquivos_com_classes']}")
        print(f"⚡ Arquivos com funções: {stats['arquivos_com_funcoes']}")
        print(f"🔥 Arquivos críticos: {stats['arquivos_criticos']}")
        print(f"📊 Média linhas/arquivo: {stats['media_linhas_por_arquivo']}")
        
        print(f"\n⚡ COMPONENTES CRÍTICOS:")
        for componente in self.resultados['componentes_criticos'][:10]:
            print(f"  • {componente}")
        
        print(f"\n💡 RECOMENDAÇÕES:")
        for rec in self.resultados['recomendacoes']:
            print(f"  • {rec}")
        
        print("="*60)

def main():
    """Função principal"""
    print("🔍 SCANNER SISTEMA SIMPLES")
    print("="*40)
    
    scanner = ScannerSistemaSimples()
    resultados = scanner.escanear_sistema()
    
    # Salvar resultados
    filename = scanner.salvar_resultados()
    
    # Imprimir resumo
    scanner.imprimir_resumo()
    
    print(f"\n✅ Escaneamento concluído! Arquivo: {filename}")
    
    return resultados

if __name__ == "__main__":
    main() 
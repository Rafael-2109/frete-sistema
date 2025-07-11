#!/usr/bin/env python3
"""
🔍 ANÁLISE DE DUPLICAÇÕES E PROBLEMAS ARQUITETURAIS
Analisa problemas identificados pelo usuário e sugere soluções
"""

import os
import re
import ast
import sys
from pathlib import Path
from typing import Dict, List, Set, Any, Optional
import logging
from datetime import datetime

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DuplicacaoAnalyzer:
    """Analisa duplicações e problemas arquiteturais"""
    
    def __init__(self, base_path: str = "."):
        self.base_path = Path(base_path)
        self.classes_encontradas = {}
        self.arquivos_flask = []
        self.pastas_vazias = []
        self.problemas_encontrados = []
    
    def analisar_tudo(self):
        """Executa análise completa"""
        logger.info("🔍 Iniciando análise completa de duplicações...")
        
        # 1. Analisar classes duplicadas
        self._analisar_classes_duplicadas()
        
        # 2. Analisar arquivos Flask
        self._analisar_arquivos_flask()
        
        # 3. Analisar pastas vazias/redundantes
        self._analisar_pastas_vazias()
        
        # 4. Analisar módulo integration
        self._analisar_modulo_integration()
        
        # 5. Gerar relatório
        self._gerar_relatorio()
        
        return self.problemas_encontrados
    
    def _analisar_classes_duplicadas(self):
        """Analisa classes duplicadas no sistema"""
        logger.info("📊 Analisando classes duplicadas...")
        
        # Buscar todos os arquivos Python
        for py_file in self.base_path.rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue
            
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Encontrar classes
                classes = re.findall(r'class\s+(\w+)', content)
                
                for classe in classes:
                    if classe not in self.classes_encontradas:
                        self.classes_encontradas[classe] = []
                    
                    self.classes_encontradas[classe].append(str(py_file))
                
            except Exception as e:
                logger.warning(f"Erro ao analisar {py_file}: {e}")
        
        # Identificar duplicações
        for classe, arquivos in self.classes_encontradas.items():
            if len(arquivos) > 1:
                self.problemas_encontrados.append({
                    'tipo': 'classe_duplicada',
                    'classe': classe,
                    'arquivos': arquivos,
                    'gravidade': 'alta' if classe.startswith('Base') else 'media'
                })
    
    def _analisar_arquivos_flask(self):
        """Analisa arquivos Flask potencialmente duplicados"""
        logger.info("🌶️ Analisando arquivos Flask...")
        
        # Buscar arquivos com "flask" no nome
        flask_files = list(self.base_path.rglob("*flask*"))
        
        for flask_file in flask_files:
            if flask_file.is_file() and flask_file.suffix == '.py':
                self.arquivos_flask.append({
                    'arquivo': str(flask_file),
                    'nome': flask_file.name,
                    'pasta': str(flask_file.parent)
                })
        
        # Identificar potenciais duplicações
        if len(self.arquivos_flask) > 1:
            self.problemas_encontrados.append({
                'tipo': 'arquivos_flask_duplicados',
                'arquivos': self.arquivos_flask,
                'gravidade': 'media'
            })
    
    def _analisar_pastas_vazias(self):
        """Analisa pastas vazias ou com apenas __init__.py"""
        logger.info("📁 Analisando pastas vazias...")
        
        for pasta in self.base_path.rglob("*"):
            if pasta.is_dir() and "__pycache__" not in str(pasta):
                arquivos = list(pasta.glob("*.py"))
                
                # Pasta vazia ou só com __init__.py
                if len(arquivos) == 0:
                    self.pastas_vazias.append({
                        'pasta': str(pasta),
                        'tipo': 'vazia'
                    })
                elif len(arquivos) == 1 and arquivos[0].name == "__init__.py":
                    # Verificar se __init__.py está vazio ou quase vazio
                    try:
                        with open(arquivos[0], 'r') as f:
                            content = f.read().strip()
                        
                        if len(content) < 100:  # Menos de 100 caracteres
                            self.pastas_vazias.append({
                                'pasta': str(pasta),
                                'tipo': 'apenas_init_vazio'
                            })
                    except:
                        pass
        
        if self.pastas_vazias:
            self.problemas_encontrados.append({
                'tipo': 'pastas_vazias',
                'pastas': self.pastas_vazias,
                'gravidade': 'baixa'
            })
    
    def _analisar_modulo_integration(self):
        """Analisa especificamente o módulo integration"""
        logger.info("🔗 Analisando módulo integration...")
        
        integration_path = self.base_path / "integration"
        
        if not integration_path.exists():
            self.problemas_encontrados.append({
                'tipo': 'modulo_integration_nao_existe',
                'gravidade': 'media'
            })
            return
        
        # Analisar estrutura do integration
        arquivos_integration = []
        for arquivo in integration_path.rglob("*.py"):
            if "__pycache__" not in str(arquivo):
                arquivos_integration.append({
                    'arquivo': str(arquivo),
                    'nome': arquivo.name,
                    'subpasta': str(arquivo.parent.relative_to(integration_path))
                })
        
        # Verificar se há IntegrationResult
        integration_manager = integration_path / "integration_manager.py"
        if integration_manager.exists():
            try:
                with open(integration_manager, 'r') as f:
                    content = f.read()
                
                if "IntegrationResult" not in content:
                    self.problemas_encontrados.append({
                        'tipo': 'integration_result_ausente',
                        'arquivo': str(integration_manager),
                        'gravidade': 'alta'
                    })
            except:
                pass
        
        self.problemas_encontrados.append({
            'tipo': 'analise_integration',
            'arquivos': arquivos_integration,
            'gravidade': 'info'
        })
    
    def _gerar_relatorio(self):
        """Gera relatório final"""
        logger.info("📋 Gerando relatório final...")
        
        relatorio = []
        relatorio.append("# 🔍 RELATÓRIO DE DUPLICAÇÕES E PROBLEMAS ARQUITETURAIS")
        relatorio.append("")
        relatorio.append(f"**Data:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        relatorio.append("")
        
        # Estatísticas
        relatorio.append("## 📊 ESTATÍSTICAS")
        relatorio.append(f"- **Total de problemas:** {len(self.problemas_encontrados)}")
        relatorio.append(f"- **Classes encontradas:** {len(self.classes_encontradas)}")
        relatorio.append(f"- **Arquivos Flask:** {len(self.arquivos_flask)}")
        relatorio.append(f"- **Pastas vazias:** {len(self.pastas_vazias)}")
        relatorio.append("")
        
        # Problemas por gravidade
        alta = [p for p in self.problemas_encontrados if p.get('gravidade') == 'alta']
        media = [p for p in self.problemas_encontrados if p.get('gravidade') == 'media']
        baixa = [p for p in self.problemas_encontrados if p.get('gravidade') == 'baixa']
        
        relatorio.append("## 🚨 PROBLEMAS POR GRAVIDADE")
        relatorio.append(f"- **🔴 Alta:** {len(alta)} problemas")
        relatorio.append(f"- **🟡 Média:** {len(media)} problemas")
        relatorio.append(f"- **🟢 Baixa:** {len(baixa)} problemas")
        relatorio.append("")
        
        # Detalhes dos problemas
        relatorio.append("## 🔍 DETALHES DOS PROBLEMAS")
        relatorio.append("")
        
        for problema in self.problemas_encontrados:
            gravidade_emoji = {
                'alta': '🔴',
                'media': '🟡',
                'baixa': '🟢',
                'info': '🔵'
            }.get(problema.get('gravidade', 'info'), '⚪')
            
            relatorio.append(f"### {gravidade_emoji} {problema['tipo'].replace('_', ' ').title()}")
            
            if problema['tipo'] == 'classe_duplicada':
                relatorio.append(f"**Classe:** `{problema['classe']}`")
                relatorio.append("**Arquivos:**")
                for arquivo in problema['arquivos']:
                    relatorio.append(f"- {arquivo}")
                relatorio.append("")
            
            elif problema['tipo'] == 'arquivos_flask_duplicados':
                relatorio.append("**Arquivos Flask encontrados:**")
                for arquivo in problema['arquivos']:
                    relatorio.append(f"- {arquivo['nome']} em {arquivo['pasta']}")
                relatorio.append("")
            
            elif problema['tipo'] == 'pastas_vazias':
                relatorio.append("**Pastas vazias/redundantes:**")
                for pasta in problema['pastas']:
                    relatorio.append(f"- {pasta['pasta']} ({pasta['tipo']})")
                relatorio.append("")
            
            elif problema['tipo'] == 'analise_integration':
                relatorio.append("**Arquivos no módulo integration:**")
                for arquivo in problema['arquivos']:
                    relatorio.append(f"- {arquivo['nome']} em {arquivo['subpasta']}")
                relatorio.append("")
        
        # Salvar relatório
        with open("RELATORIO_DUPLICACOES_ARQUITETURAIS.md", "w", encoding="utf-8") as f:
            f.write("\n".join(relatorio))
        
        logger.info("✅ Relatório salvo em RELATORIO_DUPLICACOES_ARQUITETURAIS.md")

def main():
    """Função principal"""
    from datetime import datetime
    
    analyzer = DuplicacaoAnalyzer()
    problemas = analyzer.analisar_tudo()
    
    # Resumo no console
    print("\n🎯 RESUMO DE PROBLEMAS ENCONTRADOS:")
    print(f"- Total: {len(problemas)}")
    
    alta = [p for p in problemas if p.get('gravidade') == 'alta']
    media = [p for p in problemas if p.get('gravidade') == 'media']
    baixa = [p for p in problemas if p.get('gravidade') == 'baixa']
    
    print(f"- 🔴 Alta: {len(alta)}")
    print(f"- 🟡 Média: {len(media)}")
    print(f"- 🟢 Baixa: {len(baixa)}")
    print("\n📋 Relatório completo salvo em RELATORIO_DUPLICACOES_ARQUITETURAIS.md")

if __name__ == "__main__":
    main() 
#!/usr/bin/env python3
"""
🔍 DETECTOR DE MÓDULOS ÓRFÃOS - Claude AI Novo
============================================

Script completo para detectar pastas/módulos que foram criados
mas não estão sendo utilizados no sistema, evitando perda de funcionalidades.
"""

import os
import sys
import json
import re
from pathlib import Path
from typing import Dict, List, Set, Any, Tuple
from datetime import datetime
import ast

class DetectorModulosOrfaos:
    """Detector de módulos órfãos no claude_ai_novo"""
    
    def __init__(self, base_path: str = "."):
        self.base_path = Path(base_path).resolve()
        self.pastas_encontradas: Set[str] = set()
        self.imports_encontrados: Dict[str, List[str]] = {}
        self.modulos_usados: Set[str] = set()
        self.modulos_orfaos: Set[str] = set()
        self.dependencias: Dict[str, Set[str]] = {}
        
        # Pastas a ignorar (não são módulos funcionais)
        self.pastas_ignorar = {
            '__pycache__', '.vscode', 'flask_session', 'uploads', 
            'logs', 'tests', '.git', '.pytest_cache'
        }
        
        print(f"🔍 Inicializando detector na pasta: {self.base_path}")
    
    def mapear_todas_pastas(self) -> Dict[str, Dict[str, Any]]:
        """Mapeia todas as pastas do claude_ai_novo e suas características"""
        print("📁 Mapeando todas as pastas...")
        
        mapa_pastas = {}
        
        for item in self.base_path.iterdir():
            if item.is_dir() and item.name not in self.pastas_ignorar:
                pasta_nome = item.name
                self.pastas_encontradas.add(pasta_nome)
                
                info_pasta = {
                    'nome': pasta_nome,
                    'caminho': str(item),
                    'arquivos_python': [],
                    'tem_init': False,
                    'tem_manager': False,
                    'total_arquivos': 0,
                    'linhas_codigo': 0,
                    'classes_encontradas': [],
                    'funcoes_encontradas': []
                }
                
                # Analisar conteúdo da pasta
                self._analisar_pasta(item, info_pasta)
                
                mapa_pastas[pasta_nome] = info_pasta
                
                print(f"   📂 {pasta_nome}: {info_pasta['total_arquivos']} arquivos, {info_pasta['linhas_codigo']} linhas")
        
        return mapa_pastas
    
    def _analisar_pasta(self, pasta_path: Path, info_pasta: Dict[str, Any]):
        """Analisa o conteúdo de uma pasta específica"""
        for arquivo in pasta_path.rglob("*.py"):
            if arquivo.is_file():
                info_pasta['arquivos_python'].append(arquivo.name)
                info_pasta['total_arquivos'] += 1
                
                # Verificar arquivos especiais
                if arquivo.name == "__init__.py":
                    info_pasta['tem_init'] = True
                
                if "manager" in arquivo.name.lower():
                    info_pasta['tem_manager'] = True
                
                # Analisar conteúdo do arquivo
                try:
                    with open(arquivo, 'r', encoding='utf-8') as f:
                        conteudo = f.read()
                        info_pasta['linhas_codigo'] += len(conteudo.splitlines())
                        
                        # Extrair classes e funções
                        classes, funcoes = self._extrair_definicoes(conteudo)
                        info_pasta['classes_encontradas'].extend(classes)
                        info_pasta['funcoes_encontradas'].extend(funcoes)
                        
                except Exception as e:
                    print(f"      ⚠️ Erro ao ler {arquivo}: {e}")
    
    def _extrair_definicoes(self, conteudo: str) -> Tuple[List[str], List[str]]:
        """Extrai classes e funções de um arquivo Python"""
        classes = []
        funcoes = []
        
        try:
            tree = ast.parse(conteudo)
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    classes.append(node.name)
                elif isinstance(node, ast.FunctionDef):
                    funcoes.append(node.name)
        except:
            # Fallback com regex se AST falhar
            classes = re.findall(r'^class\s+(\w+)', conteudo, re.MULTILINE)
            funcoes = re.findall(r'^def\s+(\w+)', conteudo, re.MULTILINE)
        
        return classes, funcoes
    
    def analisar_imports_sistema(self) -> Dict[str, List[str]]:
        """Analisa todos os imports do sistema para ver quais módulos são usados"""
        print("🔗 Analisando imports do sistema...")
        
        imports_por_arquivo = {}
        
        # Analisar __init__.py principal
        init_principal = self.base_path / "__init__.py"
        if init_principal.exists():
            imports = self._extrair_imports(init_principal)
            imports_por_arquivo['__init__.py'] = imports
            print(f"   📋 __init__.py principal: {len(imports)} imports")
        
        # Analisar todos os arquivos Python
        for arquivo in self.base_path.rglob("*.py"):
            if arquivo.is_file() and arquivo.name not in ['__init__.py']:
                try:
                    imports = self._extrair_imports(arquivo)
                    if imports:
                        arquivo_relativo = str(arquivo.relative_to(self.base_path))
                        imports_por_arquivo[arquivo_relativo] = imports
                        
                        # Marcar módulos como usados
                        for imp in imports:
                            self._marcar_modulo_usado(imp)
                            
                except Exception as e:
                    print(f"      ⚠️ Erro ao analisar imports de {arquivo}: {e}")
        
        self.imports_encontrados = imports_por_arquivo
        return imports_por_arquivo
    
    def _extrair_imports(self, arquivo_path: Path) -> List[str]:
        """Extrai imports de um arquivo Python"""
        imports = []
        
        try:
            with open(arquivo_path, 'r', encoding='utf-8') as f:
                conteudo = f.read()
            
            # Regex para imports relativos e absolutos
            patterns = [
                r'from\s+\.([.\w]+)\s+import',  # from .modulo import
                r'from\s+([.\w]+)\s+import',    # from modulo import
                r'import\s+([.\w]+)',           # import modulo
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, conteudo, re.MULTILINE)
                imports.extend(matches)
        
        except Exception:
            pass
        
        return imports
    
    def _marcar_modulo_usado(self, import_str: str):
        """Marca um módulo como usado baseado no import"""
        # Extrair primeira parte do import (nome da pasta)
        partes = import_str.split('.')
        if partes:
            primeiro_nivel = partes[0]
            if primeiro_nivel in self.pastas_encontradas:
                self.modulos_usados.add(primeiro_nivel)
    
    def detectar_modulos_orfaos(self) -> Dict[str, Any]:
        """Detecta módulos órfãos (pastas não usadas)"""
        print("🔍 Detectando módulos órfãos...")
        
        # Módulos órfãos = todas as pastas - módulos usados
        self.modulos_orfaos = self.pastas_encontradas - self.modulos_usados
        
        # Análise detalhada dos órfãos
        analise_orfaos = {
            'total_pastas': len(self.pastas_encontradas),
            'modulos_usados': len(self.modulos_usados),
            'modulos_orfaos': len(self.modulos_orfaos),
            'lista_orfaos': list(self.modulos_orfaos),
            'lista_usados': list(self.modulos_usados),
            'percentual_orfaos': (len(self.modulos_orfaos) / len(self.pastas_encontradas)) * 100 if self.pastas_encontradas else 0
        }
        
        print(f"   📊 Total de pastas: {analise_orfaos['total_pastas']}")
        print(f"   ✅ Módulos usados: {analise_orfaos['modulos_usados']}")
        print(f"   ❌ Módulos órfãos: {analise_orfaos['modulos_orfaos']} ({analise_orfaos['percentual_orfaos']:.1f}%)")
        
        return analise_orfaos
    
    def analisar_impacto_orfaos(self, mapa_pastas: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Analisa o impacto dos módulos órfãos"""
        print("📊 Analisando impacto dos módulos órfãos...")
        
        impacto = {
            'linhas_codigo_perdidas': 0,
            'arquivos_perdidos': 0,
            'classes_perdidas': 0,
            'funcoes_perdidas': 0,
            'detalhes_orfaos': {},
            'nivel_critico': 'baixo'
        }
        
        for modulo_orfao in self.modulos_orfaos:
            if modulo_orfao in mapa_pastas:
                info = mapa_pastas[modulo_orfao]
                
                impacto['linhas_codigo_perdidas'] += info['linhas_codigo']
                impacto['arquivos_perdidos'] += info['total_arquivos']
                impacto['classes_perdidas'] += len(info['classes_encontradas'])
                impacto['funcoes_perdidas'] += len(info['funcoes_encontradas'])
                
                # Analisar criticidade
                criticidade = 'baixa'
                if 'security' in modulo_orfao.lower() or 'guard' in modulo_orfao.lower():
                    criticidade = 'crítica'
                elif 'manager' in modulo_orfao.lower() or info['linhas_codigo'] > 500:
                    criticidade = 'alta'
                elif info['linhas_codigo'] > 200:
                    criticidade = 'média'
                
                impacto['detalhes_orfaos'][modulo_orfao] = {
                    'linhas': info['linhas_codigo'],
                    'arquivos': info['total_arquivos'],
                    'classes': len(info['classes_encontradas']),
                    'funcoes': len(info['funcoes_encontradas']),
                    'criticidade': criticidade,
                    'tem_manager': info['tem_manager'],
                    'tem_init': info['tem_init']
                }
                
                print(f"   📂 {modulo_orfao}: {info['linhas_codigo']} linhas, criticidade {criticidade}")
        
        # Determinar nível crítico geral
        if any(det['criticidade'] == 'crítica' for det in impacto['detalhes_orfaos'].values()):
            impacto['nivel_critico'] = 'crítico'
        elif any(det['criticidade'] == 'alta' for det in impacto['detalhes_orfaos'].values()):
            impacto['nivel_critico'] = 'alto'
        elif any(det['criticidade'] == 'média' for det in impacto['detalhes_orfaos'].values()):
            impacto['nivel_critico'] = 'médio'
        
        return impacto
    
    def sugerir_acoes_corretivas(self, impacto: Dict[str, Any], mapa_pastas: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Sugere ações corretivas para os módulos órfãos"""
        print("💡 Sugerindo ações corretivas...")
        
        acoes = []
        
        for modulo, detalhes in impacto['detalhes_orfaos'].items():
            acao = {
                'modulo': modulo,
                'criticidade': detalhes['criticidade'],
                'linhas_afetadas': detalhes['linhas'],
                'acao_recomendada': '',
                'onde_integrar': [],
                'prioridade': 1
            }
            
            # Determinar ação baseada na criticidade e características
            if detalhes['criticidade'] == 'crítica':
                acao['acao_recomendada'] = 'INTEGRAÇÃO IMEDIATA'
                acao['prioridade'] = 1
                acao['onde_integrar'] = ['orchestrators', '__init__.py principal']
                
            elif detalhes['criticidade'] == 'alta':
                acao['acao_recomendada'] = 'INTEGRAÇÃO PRIORITÁRIA'
                acao['prioridade'] = 2
                
                if detalhes['tem_manager']:
                    acao['onde_integrar'] = ['orchestrators/main_orchestrator.py']
                else:
                    acao['onde_integrar'] = ['__init__.py principal']
                    
            elif detalhes['criticidade'] == 'média':
                acao['acao_recomendada'] = 'INTEGRAÇÃO RECOMENDADA'
                acao['prioridade'] = 3
                acao['onde_integrar'] = ['conforme necessidade']
                
            else:
                acao['acao_recomendada'] = 'AVALIAR NECESSIDADE'
                acao['prioridade'] = 4
                acao['onde_integrar'] = ['verificar se realmente necessário']
            
            acoes.append(acao)
            
            print(f"   🎯 {modulo}: {acao['acao_recomendada']} (P{acao['prioridade']})")
        
        # Ordenar por prioridade
        acoes.sort(key=lambda x: x['prioridade'])
        
        return acoes
    
    def gerar_relatorio_completo(self) -> Dict[str, Any]:
        """Gera relatório completo de módulos órfãos"""
        print("📋 Gerando relatório completo...")
        
        # Executar análises
        mapa_pastas = self.mapear_todas_pastas()
        imports = self.analisar_imports_sistema()
        analise_orfaos = self.detectar_modulos_orfaos()
        impacto = self.analisar_impacto_orfaos(mapa_pastas)
        acoes = self.sugerir_acoes_corretivas(impacto, mapa_pastas)
        
        relatorio = {
            'timestamp': datetime.now().isoformat(),
            'resumo_executivo': {
                'total_pastas': len(self.pastas_encontradas),
                'modulos_orfaos': len(self.modulos_orfaos),
                'percentual_orfaos': analise_orfaos['percentual_orfaos'],
                'linhas_perdidas': impacto['linhas_codigo_perdidas'],
                'nivel_critico': impacto['nivel_critico']
            },
            'mapa_pastas': mapa_pastas,
            'analise_imports': {
                'total_arquivos_analisados': len(imports),
                'imports_por_arquivo': imports
            },
            'modulos_orfaos': analise_orfaos,
            'impacto_orfaos': impacto,
            'acoes_corretivas': acoes
        }
        
        return relatorio
    
    def salvar_relatorio(self, relatorio: Dict[str, Any]) -> str:
        """Salva relatório em arquivo JSON"""
        nome_arquivo = f"relatorio_modulos_orfaos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(nome_arquivo, 'w', encoding='utf-8') as f:
            json.dump(relatorio, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Relatório salvo em: {nome_arquivo}")
        return nome_arquivo

def exibir_resumo_executivo(relatorio: Dict[str, Any]):
    """Exibe resumo executivo do relatório"""
    print("\n" + "="*60)
    print("📊 RESUMO EXECUTIVO - MÓDULOS ÓRFÃOS DETECTADOS")
    print("="*60)
    
    resumo = relatorio['resumo_executivo']
    
    print(f"📂 Total de Pastas: {resumo['total_pastas']}")
    print(f"❌ Módulos Órfãos: {resumo['modulos_orfaos']} ({resumo['percentual_orfaos']:.1f}%)")
    print(f"💔 Linhas Perdidas: {resumo['linhas_perdidas']:,} linhas")
    print(f"🚨 Nível Crítico: {resumo['nivel_critico'].upper()}")
    
    # Top 5 módulos órfãos mais críticos
    acoes = relatorio['acoes_corretivas'][:5]
    if acoes:
        print(f"\n🔥 TOP 5 MÓDULOS ÓRFÃOS MAIS CRÍTICOS:")
        for i, acao in enumerate(acoes, 1):
            print(f"   {i}. {acao['modulo']}: {acao['linhas_afetadas']} linhas ({acao['criticidade']})")
    
    # Recomendações finais
    if resumo['nivel_critico'] == 'crítico':
        print(f"\n🚨 AÇÃO NECESSÁRIA: INTEGRAÇÃO IMEDIATA dos módulos críticos!")
    elif resumo['percentual_orfaos'] > 50:
        print(f"\n⚠️ ATENÇÃO: Mais de 50% dos módulos são órfãos!")
    else:
        print(f"\n✅ Sistema com baixo nível de módulos órfãos")

def main():
    """Função principal"""
    print("🔍 DETECTOR DE MÓDULOS ÓRFÃOS - CLAUDE AI NOVO")
    print("=" * 60)
    
    # Verificar se estamos no diretório correto
    if not Path("__init__.py").exists():
        print("❌ Execute este script no diretório claude_ai_novo/")
        return
    
    try:
        # Criar detector e executar análise
        detector = DetectorModulosOrfaos()
        relatorio = detector.gerar_relatorio_completo()
        
        # Salvar relatório
        arquivo_relatorio = detector.salvar_relatorio(relatorio)
        
        # Exibir resumo
        exibir_resumo_executivo(relatorio)
        
        print(f"\n📄 Relatório completo disponível em: {arquivo_relatorio}")
        
    except Exception as e:
        print(f"❌ Erro crítico: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 
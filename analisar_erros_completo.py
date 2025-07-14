#!/usr/bin/env python3
"""
Script para análise completa de erros no sistema Claude AI Novo
"""

import os
import ast
import sys
import re
from pathlib import Path
from typing import List, Dict, Tuple, Set
import subprocess
import json

class AnalisadorErros:
    def __init__(self):
        self.base_path = Path("app/claude_ai_novo")
        self.erros_encontrados = []
        self.avisos_encontrados = []
        self.arquivos_analisados = 0
        
    def analisar_sintaxe(self) -> List[Dict]:
        """Verifica erros de sintaxe em arquivos Python"""
        print("\n🔍 1. Analisando sintaxe Python...")
        erros_sintaxe = []
        
        for arquivo in self.base_path.rglob("*.py"):
            self.arquivos_analisados += 1
            try:
                with open(arquivo, 'r', encoding='utf-8') as f:
                    conteudo = f.read()
                    ast.parse(conteudo, filename=str(arquivo))
            except SyntaxError as e:
                erro = {
                    'arquivo': str(arquivo.relative_to(Path.cwd())),
                    'linha': e.lineno,
                    'tipo': 'SyntaxError',
                    'mensagem': str(e.msg)
                }
                erros_sintaxe.append(erro)
                self.erros_encontrados.append(erro)
            except Exception as e:
                erro = {
                    'arquivo': str(arquivo.relative_to(Path.cwd())),
                    'linha': 0,
                    'tipo': type(e).__name__,
                    'mensagem': str(e)
                }
                erros_sintaxe.append(erro)
                self.erros_encontrados.append(erro)
        
        print(f"   ✅ {self.arquivos_analisados} arquivos analisados")
        print(f"   {'❌' if erros_sintaxe else '✅'} {len(erros_sintaxe)} erros de sintaxe encontrados")
        return erros_sintaxe
    
    def analisar_imports(self) -> List[Dict]:
        """Verifica imports quebrados"""
        print("\n🔍 2. Analisando imports...")
        erros_import = []
        
        # Padrões de import para verificar
        import_patterns = [
            r'from\s+(\S+)\s+import',
            r'import\s+(\S+)'
        ]
        
        for arquivo in self.base_path.rglob("*.py"):
            try:
                with open(arquivo, 'r', encoding='utf-8') as f:
                    conteudo = f.read()
                    
                for pattern in import_patterns:
                    matches = re.findall(pattern, conteudo)
                    for modulo in matches:
                        # Pular imports relativos e built-ins conhecidos
                        if modulo.startswith('.') or modulo in sys.builtin_module_names:
                            continue
                            
                        # Tentar importar para verificar se existe
                        try:
                            __import__(modulo)
                        except ImportError:
                            # Verificar se é um módulo do projeto
                            if not modulo.startswith('app.'):
                                aviso = {
                                    'arquivo': str(arquivo.relative_to(Path.cwd())),
                                    'tipo': 'ImportWarning',
                                    'modulo': modulo,
                                    'mensagem': f"Módulo '{modulo}' pode não estar instalado"
                                }
                                self.avisos_encontrados.append(aviso)
            except Exception as e:
                pass
        
        print(f"   ✅ {len(self.avisos_encontrados)} avisos de import encontrados")
        return erros_import
    
    def analisar_operadores_none(self) -> List[Dict]:
        """Verifica operações com valores potencialmente None"""
        print("\n🔍 3. Analisando operações com None...")
        problemas_none = []
        
        # Padrões problemáticos
        padroes = [
            (r'(\w+)\s*\+=\s*[^=]', 'Operador += com possível None'),
            (r'(\w+)\s*\|=\s*[^=]', 'Operador |= com possível None'),
            (r'(\w+)\s*\*=\s*[^=]', 'Operador *= com possível None'),
            (r'(\w+)\.split\(', 'Método split em possível None'),
            (r'(\w+)\.strip\(', 'Método strip em possível None'),
            (r'(\w+)\.lower\(', 'Método lower em possível None'),
            (r'(\w+)\.upper\(', 'Método upper em possível None'),
            (r'f["\'].*\{(\w+)\}', 'F-string com possível None'),
        ]
        
        for arquivo in self.base_path.rglob("*.py"):
            try:
                with open(arquivo, 'r', encoding='utf-8') as f:
                    linhas = f.readlines()
                    
                for i, linha in enumerate(linhas, 1):
                    for padrao, descricao in padroes:
                        matches = re.findall(padrao, linha)
                        if matches:
                            # Verificar se há verificação de None nas linhas anteriores
                            contexto = ''.join(linhas[max(0, i-5):i])
                            variavel = matches[0] if isinstance(matches[0], str) else matches[0][0]
                            
                            # Se não há verificação de None no contexto
                            if f'if {variavel}' not in contexto and f'{variavel} is not None' not in contexto:
                                problema = {
                                    'arquivo': str(arquivo.relative_to(Path.cwd())),
                                    'linha': i,
                                    'tipo': 'PossibleNoneOperation',
                                    'variavel': variavel,
                                    'descricao': descricao,
                                    'codigo': linha.strip()
                                }
                                problemas_none.append(problema)
                                self.avisos_encontrados.append(problema)
            except Exception as e:
                pass
        
        print(f"   ✅ {len(problemas_none)} possíveis operações com None encontradas")
        return problemas_none
    
    def analisar_excecoes_nao_tratadas(self) -> List[Dict]:
        """Verifica exceções que podem não estar sendo tratadas"""
        print("\n🔍 4. Analisando exceções não tratadas...")
        excecoes_problematicas = []
        
        # Padrões de operações perigosas
        padroes_perigosos = [
            (r'(\w+)\[[\'"]\w+[\'"]?\]', 'Acesso a dicionário sem .get()'),
            (r'int\(', 'Conversão int sem try/except'),
            (r'float\(', 'Conversão float sem try/except'),
            (r'json\.loads\(', 'JSON parse sem try/except'),
            (r'open\(', 'Abertura de arquivo sem with statement'),
        ]
        
        for arquivo in self.base_path.rglob("*.py"):
            try:
                with open(arquivo, 'r', encoding='utf-8') as f:
                    conteudo = f.read()
                    linhas = conteudo.split('\n')
                    
                # Verificar se está dentro de try/except
                arvore = ast.parse(conteudo)
                
                for node in ast.walk(arvore):
                    if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant):
                        # Verificar se está em um try/except
                        linha = node.lineno
                        if linha <= len(linhas):
                            codigo = linhas[linha - 1].strip()
                            if not any(palavra in codigo for palavra in ['.get(', 'try:', 'except']):
                                aviso = {
                                    'arquivo': str(arquivo.relative_to(Path.cwd())),
                                    'linha': linha,
                                    'tipo': 'UnsafeAccess',
                                    'descricao': 'Acesso a dicionário sem .get()',
                                    'codigo': codigo[:80] + '...' if len(codigo) > 80 else codigo
                                }
                                self.avisos_encontrados.append(aviso)
            except Exception as e:
                pass
        
        return excecoes_problematicas
    
    def verificar_pylance_mypy(self) -> List[Dict]:
        """Executa verificações com ferramentas de análise estática"""
        print("\n🔍 5. Executando análise estática...")
        problemas_tipo = []
        
        # Lista de arquivos críticos para verificar
        arquivos_criticos = [
            "scanning/database/database_connection.py",
            "loaders/domain/entregas_loader.py", 
            "loaders/loader_manager.py",
            "orchestrators/main_orchestrator.py",
            "orchestrators/session_orchestrator.py"
        ]
        
        for arquivo in arquivos_criticos:
            caminho_completo = self.base_path / arquivo
            if caminho_completo.exists():
                try:
                    # Tentar compilar o arquivo
                    resultado = subprocess.run(
                        [sys.executable, "-m", "py_compile", str(caminho_completo)],
                        capture_output=True,
                        text=True
                    )
                    
                    if resultado.returncode != 0:
                        erro = {
                            'arquivo': arquivo,
                            'tipo': 'CompilationError',
                            'mensagem': resultado.stderr
                        }
                        self.erros_encontrados.append(erro)
                        problemas_tipo.append(erro)
                except Exception as e:
                    pass
        
        print(f"   ✅ {len(arquivos_criticos)} arquivos críticos verificados")
        return problemas_tipo
    
    def gerar_relatorio(self):
        """Gera relatório final da análise"""
        print("\n" + "="*80)
        print("📊 RELATÓRIO FINAL DE ANÁLISE")
        print("="*80)
        
        print(f"\n📈 Estatísticas:")
        print(f"   - Arquivos analisados: {self.arquivos_analisados}")
        print(f"   - Erros encontrados: {len(self.erros_encontrados)}")
        print(f"   - Avisos encontrados: {len(self.avisos_encontrados)}")
        
        if self.erros_encontrados:
            print(f"\n❌ ERROS CRÍTICOS ({len(self.erros_encontrados)}):")
            for erro in self.erros_encontrados[:5]:  # Mostrar apenas os 5 primeiros
                print(f"\n   📍 {erro.get('arquivo', 'N/A')}")
                print(f"      Linha: {erro.get('linha', 'N/A')}")
                print(f"      Tipo: {erro.get('tipo', 'N/A')}")
                print(f"      Mensagem: {erro.get('mensagem', 'N/A')}")
            
            if len(self.erros_encontrados) > 5:
                print(f"\n   ... e mais {len(self.erros_encontrados) - 5} erros")
        
        if self.avisos_encontrados:
            print(f"\n⚠️ AVISOS ({len(self.avisos_encontrados)}):")
            
            # Agrupar avisos por tipo
            avisos_por_tipo = {}
            for aviso in self.avisos_encontrados:
                tipo = aviso.get('tipo', 'Outros')
                if tipo not in avisos_por_tipo:
                    avisos_por_tipo[tipo] = []
                avisos_por_tipo[tipo].append(aviso)
            
            for tipo, avisos in list(avisos_por_tipo.items())[:3]:
                print(f"\n   📌 {tipo} ({len(avisos)} ocorrências)")
                for aviso in avisos[:2]:
                    print(f"      - {aviso.get('arquivo', 'N/A')}:{aviso.get('linha', 'N/A')}")
                    if 'descricao' in aviso:
                        print(f"        {aviso['descricao']}")
        
        # Salvar relatório em JSON
        relatorio = {
            'estatisticas': {
                'arquivos_analisados': self.arquivos_analisados,
                'total_erros': len(self.erros_encontrados),
                'total_avisos': len(self.avisos_encontrados)
            },
            'erros': self.erros_encontrados,
            'avisos': self.avisos_encontrados
        }
        
        with open('relatorio_analise_erros.json', 'w', encoding='utf-8') as f:
            json.dump(relatorio, f, indent=2, ensure_ascii=False)
        
        print("\n✅ Relatório salvo em: relatorio_analise_erros.json")
        
        # Conclusão
        print("\n" + "="*80)
        if not self.erros_encontrados:
            print("✅ SISTEMA SEM ERROS CRÍTICOS!")
            print("   O sistema está pronto para deploy.")
        else:
            print("❌ ERROS ENCONTRADOS!")
            print("   Corrija os erros listados antes do deploy.")
        print("="*80)

def main():
    print("🚀 Iniciando análise completa de erros no Claude AI Novo...")
    print("   Isso pode levar alguns segundos...\n")
    
    analisador = AnalisadorErros()
    
    # Executar análises
    analisador.analisar_sintaxe()
    analisador.analisar_imports()
    analisador.analisar_operadores_none()
    analisador.analisar_excecoes_nao_tratadas()
    analisador.verificar_pylance_mypy()
    
    # Gerar relatório
    analisador.gerar_relatorio()

if __name__ == "__main__":
    main() 
#!/usr/bin/env python3
"""
MAPEAMENTO COMPLETO DA ESTRUTURA REAL - CLAUDE AI NOVO
====================================================

Script para mapear TODA a estrutura real das pastas de forma sistemática.
Primeira execução: mapeamento geral
Segunda execução: detalhamento pasta por pasta
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

class MapeadorEstruturaReal:
    """Mapeador completo da estrutura real do sistema"""
    
    def __init__(self, base_path: str = "."):
        self.base_path = Path(base_path)
        self.estrutura_completa = {}
        self.estatisticas = {}
        
    def mapear_todas_pastas(self) -> Dict[str, Any]:
        """Mapeia todas as pastas do sistema"""
        print("🗂️ MAPEANDO TODAS AS PASTAS...")
        
        pastas = []
        for item in self.base_path.iterdir():
            if item.is_dir() and not item.name.startswith('.') and item.name != '__pycache__':
                pastas.append(item.name)
        
        pastas.sort()
        
        resultado = {
            "timestamp": datetime.now().isoformat(),
            "total_pastas": len(pastas),
            "pastas_encontradas": pastas,
            "detalhes_pastas": {}
        }
        
        # Mapear cada pasta rapidamente
        for pasta in pastas:
            resultado["detalhes_pastas"][pasta] = self._mapear_pasta_rapido(pasta)
            
        return resultado
    
    def _mapear_pasta_rapido(self, nome_pasta: str) -> Dict[str, Any]:
        """Mapeamento rápido de uma pasta"""
        pasta_path = self.base_path / nome_pasta
        
        if not pasta_path.exists():
            return {"erro": "Pasta não existe"}
            
        arquivos = []
        subpastas = []
        total_tamanho = 0
        
        try:
            for item in pasta_path.iterdir():
                if item.is_file() and not item.name.startswith('.') and item.name != '__pycache__':
                    tamanho = item.stat().st_size
                    total_tamanho += tamanho
                    arquivos.append({
                        "nome": item.name,
                        "tamanho": tamanho,
                        "tamanho_kb": round(tamanho / 1024, 1),
                        "modificado": datetime.fromtimestamp(item.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
                    })
                elif item.is_dir() and not item.name.startswith('.') and item.name != '__pycache__':
                    subpastas.append(item.name)
                    
        except Exception as e:
            return {"erro": f"Erro ao acessar pasta: {str(e)}"}
            
        return {
            "total_arquivos": len(arquivos),
            "total_subpastas": len(subpastas),
            "tamanho_total_kb": round(total_tamanho / 1024, 1),
            "arquivos": sorted(arquivos, key=lambda x: x["nome"]),
            "subpastas": sorted(subpastas),
            "analise_nomenclatura": self._analisar_nomenclatura(arquivos),
            "possui_manager": self._verificar_manager(arquivos),
            "possui_init": any(arq["nome"] == "__init__.py" for arq in arquivos)
        }
    
    def _analisar_nomenclatura(self, arquivos: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analisa padrões de nomenclatura"""
        if not arquivos:
            return {"padrao": "vazio"}
            
        nomes = [arq["nome"] for arq in arquivos if arq["nome"] != "__init__.py"]
        
        # Detectar sufixos comuns
        sufixos = {}
        for nome in nomes:
            if '_' in nome and nome.endswith('.py'):
                partes = nome[:-3].split('_')  # Remove .py
                if len(partes) >= 2:
                    sufixo = partes[-1]
                    sufixos[sufixo] = sufixos.get(sufixo, 0) + 1
        
        sufixo_dominante = max(sufixos.items(), key=lambda x: x[1]) if sufixos else None
        
        return {
            "total_arquivos_py": len(nomes),
            "sufixos_encontrados": sufixos,
            "sufixo_dominante": sufixo_dominante[0] if sufixo_dominante else None,
            "percentual_padrao": round((sufixo_dominante[1] / len(nomes)) * 100, 1) if sufixo_dominante and nomes else 0
        }
    
    def _verificar_manager(self, arquivos: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Verifica se existe manager na pasta"""
        nomes = [arq["nome"] for arq in arquivos]
        
        managers_encontrados = [nome for nome in nomes if 'manager' in nome.lower()]
        
        return {
            "tem_manager": len(managers_encontrados) > 0,
            "managers_encontrados": managers_encontrados,
            "quantidade": len(managers_encontrados)
        }
    
    def mapear_pasta_detalhada(self, nome_pasta: str) -> Dict[str, Any]:
        """Mapeamento detalhado de uma pasta específica"""
        print(f"🔍 MAPEANDO DETALHADAMENTE: {nome_pasta}")
        
        pasta_path = self.base_path / nome_pasta
        if not pasta_path.exists():
            return {"erro": f"Pasta {nome_pasta} não existe"}
            
        resultado = self._mapear_pasta_rapido(nome_pasta)
        
        # Adicionar análise de conformidade
        resultado["conformidade"] = self._analisar_conformidade(nome_pasta, resultado)
        
        # Se tem subpastas, mapear também
        if resultado["subpastas"]:
            resultado["detalhes_subpastas"] = {}
            for subpasta in resultado["subpastas"]:
                subpasta_path = pasta_path / subpasta
                if subpasta_path.exists():
                    resultado["detalhes_subpastas"][subpasta] = self._mapear_subpasta(subpasta_path)
        
        return resultado
    
    def _mapear_subpasta(self, subpasta_path: Path) -> Dict[str, Any]:
        """Mapeia uma subpasta"""
        arquivos = []
        total_tamanho = 0
        
        try:
            for item in subpasta_path.iterdir():
                if item.is_file() and not item.name.startswith('.') and item.name != '__pycache__':
                    tamanho = item.stat().st_size
                    total_tamanho += tamanho
                    arquivos.append({
                        "nome": item.name,
                        "tamanho_kb": round(tamanho / 1024, 1)
                    })
        except Exception as e:
            return {"erro": f"Erro ao acessar subpasta: {str(e)}"}
            
        return {
            "total_arquivos": len(arquivos),
            "tamanho_total_kb": round(total_tamanho / 1024, 1),
            "arquivos": sorted(arquivos, key=lambda x: x["nome"])
        }
    
    def _analisar_conformidade(self, nome_pasta: str, dados: Dict[str, Any]) -> Dict[str, Any]:
        """Analisa conformidade com regras arquiteturais"""
        problemas = []
        
        # Verificar manager obrigatório
        if not dados["possui_manager"]["tem_manager"]:
            problemas.append(f"FALTA MANAGER: Deveria ter {nome_pasta[:-1]}_manager.py")
        
        # Verificar nomenclatura
        nomenclatura = dados["analise_nomenclatura"]
        percentual = nomenclatura.get("percentual_padrao", 0)
        if percentual < 70:
            problemas.append(f"NOMENCLATURA INCONSISTENTE: {percentual}% seguem padrão")
        
        # Verificar __init__.py
        if not dados["possui_init"]:
            problemas.append("FALTA __init__.py")
            
        return {
            "status": "CONFORME" if not problemas else "PROBLEMAS",
            "total_problemas": len(problemas),
            "problemas_identificados": problemas,
            "score_conformidade": max(0, 100 - (len(problemas) * 20))
        }
    
    def gerar_relatorio_completo(self) -> str:
        """Gera relatório markdown completo"""
        resultado = self.mapear_todas_pastas()
        
        relatorio = f"""# 🗂️ MAPEAMENTO COMPLETO DA ESTRUTURA REAL
## Sistema Claude AI Novo

**Data**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Total de pastas**: {resultado['total_pastas']}

---

## 📊 RESUMO GERAL

| **Pasta** | **Arquivos** | **Subpastas** | **Tamanho (KB)** | **Manager** | **Nomenclatura** | **Status** |
|-----------|--------------|---------------|------------------|-------------|------------------|------------|
"""
        
        for pasta, dados in resultado["detalhes_pastas"].items():
            if "erro" in dados:
                continue
                
            manager = "✅" if dados["possui_manager"]["tem_manager"] else "❌"
            percentual = dados['analise_nomenclatura'].get('percentual_padrao', 0)
            nomenclatura = f"{percentual}%"
            conformidade = dados.get("conformidade", {})
            status = conformidade.get("status", "N/A")
            
            relatorio += f"| `{pasta}/` | {dados['total_arquivos']} | {dados['total_subpastas']} | {dados['tamanho_total_kb']} | {manager} | {nomenclatura} | {status} |\n"
        
        relatorio += "\n---\n\n"
        
        # Análise por pasta
        relatorio += "## 🔍 ANÁLISE DETALHADA POR PASTA\n\n"
        
        for pasta, dados in resultado["detalhes_pastas"].items():
            if "erro" in dados:
                continue
                
            relatorio += f"### 📁 **{pasta.upper()}/**\n\n"
            relatorio += f"- **Arquivos**: {dados['total_arquivos']}\n"
            relatorio += f"- **Subpastas**: {dados['total_subpastas']}\n"
            relatorio += f"- **Tamanho**: {dados['tamanho_total_kb']} KB\n"
            relatorio += f"- **Manager**: {'✅ Existe' if dados['possui_manager']['tem_manager'] else '❌ Ausente'}\n"
            
            if dados["possui_manager"]["managers_encontrados"]:
                relatorio += f"  - Managers: {', '.join(dados['possui_manager']['managers_encontrados'])}\n"
            
            nomenclatura = dados["analise_nomenclatura"]
            if nomenclatura.get("sufixo_dominante"):
                percentual = nomenclatura.get('percentual_padrao', 0)
                relatorio += f"- **Nomenclatura**: {percentual}% seguem padrão `*_{nomenclatura['sufixo_dominante']}.py`\n"
            
            if dados["subpastas"]:
                relatorio += f"- **Subpastas**: {', '.join(dados['subpastas'])}\n"
                
            relatorio += "\n"
        
        return relatorio
    
    def salvar_relatorio(self, nome_arquivo: str = "ESTRUTURA_REAL_MAPEADA.md"):
        """Salva relatório em arquivo"""
        relatorio = self.gerar_relatorio_completo()
        
        with open(nome_arquivo, 'w', encoding='utf-8') as f:
            f.write(relatorio)
            
        print(f"✅ Relatório salvo em: {nome_arquivo}")
        return nome_arquivo

if __name__ == "__main__":
    mapeador = MapeadorEstruturaReal()
    
    print("🚀 INICIANDO MAPEAMENTO COMPLETO DA ESTRUTURA REAL...")
    print("=" * 60)
    
    # Executar mapeamento
    arquivo_relatorio = mapeador.salvar_relatorio()
    
    print("=" * 60)
    print("✅ MAPEAMENTO COMPLETO CONCLUÍDO!")
    print(f"📄 Relatório: {arquivo_relatorio}") 
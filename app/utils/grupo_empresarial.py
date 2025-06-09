#!/usr/bin/env python3
"""
Serviço para detectar e gerenciar grupos empresariais de transportadoras
"""

from app.transportadoras.models import Transportadora
from difflib import SequenceMatcher
import re
from typing import List, Dict, Set, Tuple

class GrupoEmpresarialService:
    
    def __init__(self):
        self.cache_grupos = {}
        self.threshold_similaridade = 0.85  # 85% de similaridade
    
    def extrair_cnpj_base(self, cnpj: str) -> str:
        """Extrai o CNPJ base (sem filial) removendo os últimos 3 dígitos"""
        if not cnpj:
            return ""
        # Remove pontuação e pega apenas os primeiros 8 dígitos
        cnpj_limpo = re.sub(r'[^\d]', '', cnpj)
        return cnpj_limpo[:8] if len(cnpj_limpo) >= 8 else cnpj_limpo
    
    def calcular_similaridade_nome(self, nome1: str, nome2: str) -> float:
        """Calcula similaridade entre dois nomes de transportadoras"""
        if not nome1 or not nome2:
            return 0.0
        
        # Normaliza os nomes
        nome1_norm = self.normalizar_nome(nome1)
        nome2_norm = self.normalizar_nome(nome2)
        
        return SequenceMatcher(None, nome1_norm, nome2_norm).ratio()
    
    def normalizar_nome(self, nome: str) -> str:
        """Normaliza nome da transportadora para comparação"""
        if not nome:
            return ""
        
        # Converte para maiúsculo e remove acentos
        nome = nome.upper()
        
        # Remove sufixos comuns
        sufixos_remover = [
            'LTDA', 'LIMITADA', 'S/A', 'SA', 'SOCIEDADE ANONIMA',
            'ME', 'MICROEMPRESA', 'EPP', 'EMPRESA PEQUENO PORTE',
            'EIRELI', 'EI', 'EMPRESARIO INDIVIDUAL'
        ]
        
        for sufixo in sufixos_remover:
            nome = nome.replace(f' {sufixo}', '').replace(f'{sufixo} ', '').replace(sufixo, '')
        
        # Remove pontuação extra e espaços múltiplos
        nome = re.sub(r'[^\w\s]', ' ', nome)
        nome = re.sub(r'\s+', ' ', nome).strip()
        
        return nome
    
    def identificar_grupos_empresariais(self) -> Dict[str, List[Transportadora]]:
        """Identifica todos os grupos empresariais no sistema"""
        
        # Busca todas as transportadoras
        transportadoras = Transportadora.query.all()
        
        grupos = {}
        transportadoras_processadas = set()
        
        for transportadora in transportadoras:
            if transportadora.id in transportadoras_processadas:
                continue
                
            # Inicia um novo grupo
            grupo_atual = [transportadora]
            transportadoras_processadas.add(transportadora.id)
            
            cnpj_base = self.extrair_cnpj_base(transportadora.cnpj)
            nome_normalizado = self.normalizar_nome(transportadora.razao_social)
            
            # Busca outras transportadoras do mesmo grupo
            for outra in transportadoras:
                if outra.id in transportadoras_processadas:
                    continue
                
                if self.sao_mesmo_grupo(transportadora, outra):
                    grupo_atual.append(outra)
                    transportadoras_processadas.add(outra.id)
            
            # Se encontrou mais de 1 transportadora, é um grupo
            if len(grupo_atual) > 1:
                # Usa o nome da primeira como chave do grupo
                chave_grupo = f"grupo_{transportadora.id}_{nome_normalizado[:20]}"
                grupos[chave_grupo] = grupo_atual
        
        return grupos
    
    def sao_mesmo_grupo(self, transp1: Transportadora, transp2: Transportadora) -> bool:
        """Verifica se duas transportadoras pertencem ao mesmo grupo empresarial"""
        
        # Critério 1: Mesmo CNPJ base
        cnpj1_base = self.extrair_cnpj_base(transp1.cnpj)
        cnpj2_base = self.extrair_cnpj_base(transp2.cnpj)
        
        if cnpj1_base and cnpj2_base and cnpj1_base == cnpj2_base:
            return True
        
        # Critério 2: Nomes muito similares (acima do threshold)
        similaridade = self.calcular_similaridade_nome(transp1.razao_social, transp2.razao_social)
        if similaridade >= self.threshold_similaridade:
            return True
        
        return False
    
    def obter_transportadoras_grupo(self, transportadora_id: int) -> List[int]:
        """Retorna IDs de todas as transportadoras do mesmo grupo"""
        
        # Verifica cache primeiro
        if transportadora_id in self.cache_grupos:
            return self.cache_grupos[transportadora_id]
        
        transportadora = Transportadora.query.get(transportadora_id)
        if not transportadora:
            return [transportadora_id]
        
        # Busca todas as transportadoras do mesmo grupo
        todas_transportadoras = Transportadora.query.all()
        grupo_ids = [transportadora_id]  # Inclui a própria
        
        for outra in todas_transportadoras:
            if outra.id != transportadora_id and self.sao_mesmo_grupo(transportadora, outra):
                grupo_ids.append(outra.id)
        
        # Atualiza cache para todas as transportadoras do grupo
        for id_grupo in grupo_ids:
            self.cache_grupos[id_grupo] = grupo_ids
        
        return grupo_ids
    
    def limpar_cache(self):
        """Limpa o cache de grupos"""
        self.cache_grupos = {}
    
    def relatorio_grupos(self) -> str:
        """Gera relatório dos grupos empresariais identificados"""
        grupos = self.identificar_grupos_empresariais()
        
        relatorio = "📊 RELATÓRIO DE GRUPOS EMPRESARIAIS\n"
        relatorio += "=" * 50 + "\n\n"
        
        if not grupos:
            relatorio += "❌ Nenhum grupo empresarial identificado.\n"
            return relatorio
        
        relatorio += f"✅ {len(grupos)} grupos empresariais identificados:\n\n"
        
        for nome_grupo, transportadoras in grupos.items():
            relatorio += f"🏢 GRUPO: {nome_grupo}\n"
            relatorio += f"   📊 {len(transportadoras)} transportadoras\n\n"
            
            for transp in transportadoras:
                relatorio += f"   🚛 ID: {transp.id}\n"
                relatorio += f"      CNPJ: {transp.cnpj}\n"
                relatorio += f"      Razão: {transp.razao_social}\n"
                relatorio += f"      CNPJ Base: {self.extrair_cnpj_base(transp.cnpj)}\n\n"
            
            relatorio += "-" * 50 + "\n"
        
        return relatorio

# Instância global do serviço
grupo_service = GrupoEmpresarialService() 
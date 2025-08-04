#!/usr/bin/env python3
"""
DataAnalyzer - Análise especializada de dados
Identifica domínios, entidades e contexto nas consultas
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import re

logger = logging.getLogger(__name__)

class DataAnalyzer:
    """Analisador especializado em detectar domínios e entidades de dados"""
    
    def __init__(self):
        self.logger = logger
        self._init_patterns()
        logger.info("📊 DataAnalyzer inicializado")
    
    def _init_patterns(self):
        """Inicializa padrões de detecção"""
        
        # Padrões de clientes importantes (incluindo variações)
        self.clientes_patterns = {
            'atacadao': ['atacadão', 'atacadao', 'atac', 'atacadao sa', 'atacadão sa'],
            'assai': ['assai', 'assaí', 'assa', 'assai atacadista'],
            'carrefour': ['carrefour', 'carref', 'carr'],
            'tenda': ['tenda', 'tenda atacado'],
            'mateus': ['mateus', 'grupo mateus', 'supermercados mateus'],
            'extra': ['extra', 'grupo extra'],
            'pao_de_acucar': ['pão de açúcar', 'pao de acucar', 'pda'],
            'gbarbosa': ['gbarbosa', 'g barbosa', 'g. barbosa'],
            'makro': ['makro', 'makro atacadista'],
            'roldao': ['roldão', 'roldao'],
        }
        
        # Domínios de dados
        self.dominios_patterns = {
            'entregas': ['entrega', 'entregar', 'entregue', 'entregou', 'delivery', 'transporte'],
            'pedidos': ['pedido', 'pedidos', 'compra', 'compras', 'order', 'orders'],
            'nfe': ['nota', 'nf', 'nfe', 'fiscal', 'fatura', 'faturamento'],
            'embarques': ['embarque', 'embarcar', 'embarcou', 'carga', 'carregamento'],
            'estoque': ['estoque', 'armazém', 'armazem', 'inventário', 'inventario'],
            'clientes': ['cliente', 'comprador', 'destinatário', 'destinatario'],
            'transportadoras': ['transportadora', 'transportador', 'frete', 'transporta'],
        }
        
        # Padrões temporais
        self.temporal_patterns = {
            'hoje': 0,
            'ontem': 1,
            'anteontem': 2,
            'esta semana': 7,
            'semana passada': 14,
            'este mês': 30,
            'este mes': 30,
            'mês passado': 60,
            'mes passado': 60,
            'últimos': None,  # Precisa extrair número
            'ultimos': None,
        }
    
    def analyze_data_context(self, query: str) -> Dict[str, Any]:
        """Analisa contexto de dados na consulta"""
        
        query_lower = query.lower()
        
        # Detectar domínio principal
        dominio = self._detectar_dominio(query_lower)
        
        # Detectar cliente específico
        cliente_info = self._detectar_cliente(query_lower)
        
        # Detectar período temporal
        periodo_info = self._detectar_periodo(query_lower)
        
        # Detectar tipo de consulta
        tipo_consulta = self._detectar_tipo_consulta(query_lower)
        
        # Extrair entidades específicas (números de NF, pedidos, etc)
        entidades = self._extrair_entidades(query)
        
        # Detectar filtros adicionais
        filtros = self._detectar_filtros(query_lower)
        
        resultado = {
            'dominio': dominio,
            'cliente_especifico': cliente_info.get('nome'),
            'cliente_detectado': cliente_info.get('detectado', False),
            'cliente_variacoes': cliente_info.get('variacoes', []),
            'periodo_dias': periodo_info.get('dias', 30),
            'periodo_descricao': periodo_info.get('descricao', 'últimos 30 dias'),
            'tipo_consulta': tipo_consulta,
            'entidades': entidades,
            'filtros': filtros,
            'query_processada': query_lower,
            'timestamp': datetime.now().isoformat()
        }
        
        self.logger.info(f"📊 Análise de dados concluída: domínio={dominio}, cliente={cliente_info.get('nome')}")
        
        return resultado
    
    def _detectar_dominio(self, query: str) -> str:
        """Detecta domínio principal da consulta"""
        
        scores = {}
        
        for dominio, palavras in self.dominios_patterns.items():
            score = sum(1 for palavra in palavras if palavra in query)
            if score > 0:
                scores[dominio] = score
        
        if scores:
            # Retorna domínio com maior score
            return max(scores.keys(), key=lambda k: scores[k])
        
        # Default para entregas se não detectar nada específico
        return 'entregas'
    
    def _detectar_cliente(self, query: str) -> Dict[str, Any]:
        """Detecta cliente específico na consulta"""
        
        for cliente_key, variacoes in self.clientes_patterns.items():
            for variacao in variacoes:
                if variacao in query:
                    # Nome normalizado do cliente
                    nome_cliente = {
                        'atacadao': 'Atacadão',
                        'assai': 'Assaí',
                        'carrefour': 'Carrefour',
                        'tenda': 'Tenda',
                        'mateus': 'Mateus',
                        'extra': 'Extra',
                        'pao_de_acucar': 'Pão de Açúcar',
                        'gbarbosa': 'GBarbosa',
                        'makro': 'Makro',
                        'roldao': 'Roldão'
                    }.get(cliente_key, cliente_key.title())
                    
                    return {
                        'detectado': True,
                        'nome': nome_cliente,
                        'chave': cliente_key,
                        'variacoes': variacoes,
                        'match': variacao
                    }
        
        return {
            'detectado': False,
            'nome': None,
            'variacoes': []
        }
    
    def _detectar_periodo(self, query: str) -> Dict[str, Any]:
        """Detecta período temporal na consulta"""
        
        # Verificar padrões temporais conhecidos
        for padrao, dias in self.temporal_patterns.items():
            if padrao in query:
                if dias is not None:
                    return {
                        'dias': dias,
                        'descricao': padrao,
                        'tipo': 'fixo'
                    }
                else:
                    # Extrair número para "últimos X dias"
                    match = re.search(r'[úu]ltimos?\s+(\d+)\s+dias?', query)
                    if match:
                        return {
                            'dias': int(match.group(1)),
                            'descricao': f'últimos {match.group(1)} dias',
                            'tipo': 'variavel'
                        }
        
        # Verificar datas específicas
        data_match = re.search(r'(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})', query)
        if data_match:
            try:
                dia, mes, ano = data_match.groups()
                if len(ano) == 2:
                    ano = f"20{ano}"
                data = datetime(int(ano), int(mes), int(dia))
                dias = (datetime.now() - data).days
                return {
                    'dias': abs(dias),
                    'descricao': f'desde {data.strftime("%d/%m/%Y")}',
                    'tipo': 'data_especifica'
                }
            except:
                pass
        
        # Default
        return {
            'dias': 30,
            'descricao': 'últimos 30 dias',
            'tipo': 'default'
        }
    
    def _detectar_tipo_consulta(self, query: str) -> str:
        """Detecta tipo de consulta"""
        
        if any(palavra in query for palavra in ['relatório', 'relatorio', 'excel', 'exportar']):
            return 'relatorio'
        elif any(palavra in query for palavra in ['status', 'situação', 'situacao', 'como está', 'como estão']):
            return 'status'
        elif any(palavra in query for palavra in ['problema', 'erro', 'falha', 'não funciona']):
            return 'problema'
        elif any(palavra in query for palavra in ['análise', 'analise', 'comparar', 'evolução']):
            return 'analise'
        elif any(palavra in query for palavra in ['quantos', 'quantas', 'total', 'soma']):
            return 'contagem'
        else:
            return 'informacao'
    
    def _extrair_entidades(self, query: str) -> Dict[str, List[str]]:
        """Extrai entidades específicas da consulta"""
        
        entidades = {
            'numeros_nf': [],
            'numeros_pedido': [],
            'cnpjs': [],
            'datas': [],
            'valores': []
        }
        
        # Extrair números de NF (6-10 dígitos)
        nf_matches = re.findall(r'\b\d{6,10}\b', query)
        entidades['numeros_nf'] = nf_matches
        
        # Extrair CNPJs (formato completo ou parcial)
        cnpj_matches = re.findall(r'\b\d{2}\.?\d{3}\.?\d{3}[/]?\d{4}[-]?\d{2}\b', query)
        entidades['cnpjs'] = cnpj_matches
        
        # Extrair datas
        data_matches = re.findall(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b', query)
        entidades['datas'] = data_matches
        
        # Extrair valores monetários
        valor_matches = re.findall(r'R\$\s*[\d,.]+', query)
        entidades['valores'] = valor_matches
        
        return entidades
    
    def _detectar_filtros(self, query: str) -> Dict[str, Any]:
        """Detecta filtros adicionais na consulta"""
        
        filtros = {}
        
        # Status de entrega
        if 'entregue' in query or 'entregues' in query:
            filtros['status'] = 'entregue'
        elif 'pendente' in query or 'pendentes' in query:
            filtros['status'] = 'pendente'
        elif 'atrasado' in query or 'atrasados' in query or 'atraso' in query:
            filtros['status'] = 'atrasado'
        
        # Urgência
        if any(palavra in query for palavra in ['urgente', 'urgência', 'prioridade']):
            filtros['urgencia'] = 'alta'
        
        # Região/Estado
        estados = ['sp', 'rj', 'mg', 'rs', 'pr', 'sc', 'ba', 'pe', 'ce']
        for estado in estados:
            if f' {estado} ' in f' {query} ':
                filtros['estado'] = estado.upper()
                break
        
        # Transportadora
        transportadoras = ['jamef', 'rodonaves', 'braspress', 'tnt', 'correios']
        for transp in transportadoras:
            if transp in query:
                filtros['transportadora'] = transp.title()
                break
        
        return filtros
    
    def get_analysis_summary(self) -> Dict[str, Any]:
        """Retorna resumo das análises realizadas"""
        return {
            'analyzer': 'DataAnalyzer',
            'capabilities': [
                'Detecção de domínios de dados',
                'Identificação de clientes específicos',
                'Análise temporal',
                'Extração de entidades',
                'Detecção de filtros'
            ],
            'domains_supported': list(self.dominios_patterns.keys()),
            'clients_supported': list(self.clientes_patterns.keys())
        }

# Instância global
_data_analyzer = None

def get_data_analyzer():
    """Retorna instância de DataAnalyzer"""
    global _data_analyzer
    if _data_analyzer is None:
        _data_analyzer = DataAnalyzer()
    return _data_analyzer

__all__ = ['DataAnalyzer', 'get_data_analyzer']
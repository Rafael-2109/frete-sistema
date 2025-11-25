"""
Composite Entity Extractor - Extrai entidades compostas de perguntas complexas.

Problema: "pedidos do cliente Assai sem agendamento"
- O classificador extrai: cliente = "Assai"
- MAS não sabe o que fazer com "sem agendamento"

Solução: Este módulo extrai condições implícitas como:
- "sem agendamento" -> filtro: agendamento IS NULL
- "sem expedição" -> filtro: expedicao IS NULL
- "com saldo" -> filtro: qtd_saldo > 0
- "atrasados" -> filtro: data < hoje
- "dia 27/11" -> data_expedicao = 2025-11-27

Criado em: 24/11/2025
Atualizado: 24/11/2025 - Adicionada extração de datas específicas
Limite: 350 linhas
"""

import re
import logging
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime, timedelta, date

logger = logging.getLogger(__name__)


# === PADRÕES PARA EXTRAÇÃO DE DATAS ESPECÍFICAS ===
# Usados para capturar datas mencionadas pelo usuário como "27/11", "dia 27/11", etc.

PADROES_DATA_ESPECIFICA = [
    # "dia 27/11", "pro dia 27/11", "para dia 27/11"
    r'(?:pro?|para)\s+(?:o\s+)?dia\s+(\d{1,2})[/\-](\d{1,2})(?:[/\-](\d{2,4}))?',
    # "dia 27/11" (sem prefixo)
    r'(?<![\d])dia\s+(\d{1,2})[/\-](\d{1,2})(?:[/\-](\d{2,4}))?',
    # "data de expedição 27/11", "data 27/11", "expedicao 27/11"
    r'(?:data(?:\s+de)?(?:\s+expedi[çc][aã]o)?|expedi[çc][aã]o)\s+(?:para\s+)?(\d{1,2})[/\-](\d{1,2})(?:[/\-](\d{2,4}))?',
    # "27/11" isolado com contexto de data (mas cria separação para 27/11)
    r'(?:crie?(?:\s+para)?|criar(?:\s+para)?|com\s+data)\s+.*?(\d{1,2})[/\-](\d{1,2})(?:[/\-](\d{2,4}))?',
    # "para 27/11", "pro 27/11" (data simples com preposição)
    r'(?:pro?|para)\s+(\d{1,2})[/\-](\d{1,2})(?:[/\-](\d{2,4}))?(?!\d)',
]


# === PADRÕES DE CONDIÇÕES COMPOSTAS ===
# Cada padrão tem: regex, campo_filtro, operador, valor

PADROES_CONDICOES = [
    # === SEM (NULL/AUSENTE) ===
    {
        'padrao': r'\bsem\s+agendamento\b',
        'campo': 'agendamento',
        'operador': 'is_null',
        'valor': None,
        'nome': 'sem_agendamento',
        'descricao': 'Pedidos sem data de agendamento'
    },
    {
        'padrao': r'\bsem\s+expedi[cç][aã]o\b',
        'campo': 'expedicao',
        'operador': 'is_null',
        'valor': None,
        'nome': 'sem_expedicao',
        'descricao': 'Pedidos sem data de expedição'
    },
    {
        'padrao': r'\bsem\s+protocolo\b',
        'campo': 'protocolo',
        'operador': 'is_null',
        'valor': None,
        'nome': 'sem_protocolo',
        'descricao': 'Pedidos sem protocolo de agendamento'
    },
    {
        'padrao': r'\bsem\s+transportadora\b',
        'campo': 'roteirizacao',
        'operador': 'is_null',
        'valor': None,
        'nome': 'sem_transportadora',
        'descricao': 'Pedidos sem transportadora definida'
    },
    {
        'padrao': r'\bsem\s+cota[cç][aã]o\b',
        'campo': 'cotacao_id',
        'operador': 'is_null',
        'valor': None,
        'nome': 'sem_cotacao',
        'descricao': 'Pedidos sem cotação de frete'
    },

    # === COM (NOT NULL/PRESENTE) ===
    {
        'padrao': r'\bcom\s+agendamento\b',
        'campo': 'agendamento',
        'operador': 'is_not_null',
        'valor': None,
        'nome': 'com_agendamento',
        'descricao': 'Pedidos com data de agendamento'
    },
    {
        'padrao': r'\bagendado[s]?\b',
        'campo': 'agendamento',
        'operador': 'is_not_null',
        'valor': None,
        'nome': 'agendado',
        'descricao': 'Pedidos agendados'
    },
    {
        'padrao': r'\bcom\s+expedi[cç][aã]o\b',
        'campo': 'expedicao',
        'operador': 'is_not_null',
        'valor': None,
        'nome': 'com_expedicao',
        'descricao': 'Pedidos com data de expedição'
    },
    {
        'padrao': r'\bcom\s+saldo\b',
        'campo': 'qtd_saldo',
        'operador': '>',
        'valor': 0,
        'nome': 'com_saldo',
        'descricao': 'Itens com saldo disponível'
    },

    # === STATUS ===
    {
        'padrao': r'\b(abertos?|em\s+aberto)\b',
        'campo': 'status',
        'operador': '==',
        'valor': 'ABERTO',
        'nome': 'status_aberto',
        'descricao': 'Pedidos em status ABERTO'
    },
    {
        'padrao': r'\bcotados?\b',
        'campo': 'status',
        'operador': '==',
        'valor': 'COTADO',
        'nome': 'status_cotado',
        'descricao': 'Pedidos em status COTADO'
    },
    {
        'padrao': r'\bembarcados?\b',
        'campo': 'status',
        'operador': '==',
        'valor': 'EMBARCADO',
        'nome': 'status_embarcado',
        'descricao': 'Pedidos em status EMBARCADO'
    },
    {
        'padrao': r'\bfaturados?\b',
        'campo': 'status',
        'operador': '==',
        'valor': 'FATURADO',
        'nome': 'status_faturado',
        'descricao': 'Pedidos faturados'
    },
    {
        'padrao': r'\bpendentes?\b',
        'campo': 'sincronizado_nf',
        'operador': '==',
        'valor': False,
        'nome': 'pendente_nf',
        'descricao': 'Pedidos pendentes (não faturados)'
    },

    # === DATAS RELATIVAS ===
    {
        'padrao': r'\bhoje\b',
        'campo': 'expedicao',
        'operador': '==',
        'valor': 'HOJE',
        'nome': 'expedicao_hoje',
        'descricao': 'Expedição para hoje'
    },
    {
        'padrao': r'\bamanh[aã]\b',
        'campo': 'expedicao',
        'operador': '==',
        'valor': 'AMANHA',
        'nome': 'expedicao_amanha',
        'descricao': 'Expedição para amanhã'
    },
    {
        'padrao': r'\besta\s+semana\b',
        'campo': 'expedicao',
        'operador': 'between',
        'valor': 'ESTA_SEMANA',
        'nome': 'expedicao_esta_semana',
        'descricao': 'Expedição nesta semana'
    },
    {
        'padrao': r'\batrasados?\b',
        'campo': 'expedicao',
        'operador': '<',
        'valor': 'HOJE',
        'nome': 'atrasado',
        'descricao': 'Pedidos com expedição atrasada'
    },

    # === QUANTIDADES ===
    {
        'padrao': r'\bgrandes?\b|\balto\s+valor\b',
        'campo': 'valor_saldo',
        'operador': '>',
        'valor': 10000,
        'nome': 'alto_valor',
        'descricao': 'Pedidos de alto valor (> R$ 10.000)'
    },
    {
        'padrao': r'\bpequenos?\b|\bbaixo\s+valor\b',
        'campo': 'valor_saldo',
        'operador': '<',
        'valor': 1000,
        'nome': 'baixo_valor',
        'descricao': 'Pedidos de baixo valor (< R$ 1.000)'
    },
]


class CompositeExtractor:
    """Extrai condições compostas de perguntas."""

    def __init__(self):
        self.padroes = PADROES_CONDICOES
        self.padroes_data = PADROES_DATA_ESPECIFICA

    def extrair(self, texto: str) -> Dict[str, Any]:
        """
        Extrai entidades compostas do texto.

        Args:
            texto: Texto da pergunta do usuário

        Returns:
            Dict com:
                - condicoes: Lista de condições detectadas
                - filtros: Lista de filtros SQLAlchemy-compatíveis
                - descricoes: Descrições amigáveis das condições
                - data_especifica: Data específica extraída (se houver)
        """
        texto_lower = texto.lower()
        condicoes = []
        filtros = []
        descricoes = []

        for padrao_cfg in self.padroes:
            if re.search(padrao_cfg['padrao'], texto_lower):
                # Detectou a condição
                condicao = {
                    'nome': padrao_cfg['nome'],
                    'campo': padrao_cfg['campo'],
                    'operador': padrao_cfg['operador'],
                    'valor': self._resolver_valor(padrao_cfg['valor']),
                    'descricao': padrao_cfg['descricao']
                }
                condicoes.append(condicao)
                descricoes.append(padrao_cfg['descricao'])

                # Gera filtro SQLAlchemy-compatível
                filtro = self._gerar_filtro(condicao)
                if filtro:
                    filtros.append(filtro)

                logger.info(f"[EXTRACTOR] Condição detectada: {padrao_cfg['nome']}")

        # Extrai data específica mencionada pelo usuário
        data_especifica = self._extrair_data_especifica(texto_lower)

        return {
            'condicoes': condicoes,
            'filtros': filtros,
            'descricoes': descricoes,
            'total_condicoes': len(condicoes),
            'data_especifica': data_especifica
        }

    def _extrair_data_especifica(self, texto: str) -> Optional[date]:
        """
        Extrai data específica mencionada pelo usuário.

        Exemplos:
            "dia 27/11" -> date(2025, 11, 27)
            "pro dia 27/11" -> date(2025, 11, 27)
            "para 27/11" -> date(2025, 11, 27)
            "data de expedição 27/11" -> date(2025, 11, 27)

        Args:
            texto: Texto em lowercase

        Returns:
            date se encontrou, None caso contrário
        """
        for padrao in self.padroes_data:
            match = re.search(padrao, texto, re.IGNORECASE)
            if match:
                grupos = match.groups()
                try:
                    dia = int(grupos[0])
                    mes = int(grupos[1])
                    ano = int(grupos[2]) if grupos[2] else datetime.now().year

                    # Corrige ano de 2 dígitos
                    if ano < 100:
                        ano = 2000 + ano

                    # Valida data
                    data_extraida = date(ano, mes, dia)

                    logger.info(f"[EXTRACTOR] Data específica extraída: {data_extraida.strftime('%d/%m/%Y')} do texto: '{texto}'")
                    return data_extraida

                except (ValueError, IndexError) as e:
                    logger.warning(f"[EXTRACTOR] Erro ao parsear data: {e}")
                    continue

        return None

    def _resolver_valor(self, valor):
        """Resolve valores dinâmicos como HOJE, AMANHA, etc."""
        if valor == 'HOJE':
            return datetime.now().date()
        elif valor == 'AMANHA':
            return (datetime.now() + timedelta(days=1)).date()
        elif valor == 'ESTA_SEMANA':
            hoje = datetime.now().date()
            inicio_semana = hoje - timedelta(days=hoje.weekday())
            fim_semana = inicio_semana + timedelta(days=6)
            return (inicio_semana, fim_semana)
        return valor

    def _gerar_filtro(self, condicao: Dict) -> Optional[Dict]:
        """Gera filtro no formato do LoaderExecutor."""
        campo = condicao['campo']
        operador = condicao['operador']
        valor = condicao['valor']

        # Formato compatível com LoaderExecutor
        if operador == 'is_null':
            return {
                'campo': campo,
                'operador': 'is_null'
            }
        elif operador == 'is_not_null':
            return {
                'campo': campo,
                'operador': 'is_not_null'
            }
        elif operador == 'between' and isinstance(valor, tuple):
            return {
                'campo': campo,
                'operador': 'between',
                'valor': [str(valor[0]), str(valor[1])]
            }
        else:
            return {
                'campo': campo,
                'operador': operador,
                'valor': valor
            }

    def extrair_e_enriquecer_entidades(
        self,
        texto: str,
        entidades: Dict
    ) -> Tuple[Dict, List[Dict]]:
        """
        Extrai condições e enriquece as entidades existentes.

        Args:
            texto: Texto da pergunta
            entidades: Entidades já extraídas pelo classificador

        Returns:
            Tuple (entidades_enriquecidas, filtros_compostos)
        """
        resultado = self.extrair(texto)

        entidades_enriquecidas = entidades.copy()

        # Adiciona condições às entidades
        if resultado['condicoes']:
            entidades_enriquecidas['_condicoes_compostas'] = resultado['condicoes']
            entidades_enriquecidas['_descricoes_condicoes'] = resultado['descricoes']

        # Adiciona data específica às entidades (IMPORTANTE para separações)
        if resultado['data_especifica']:
            entidades_enriquecidas['data_expedicao'] = resultado['data_especifica'].isoformat()
            entidades_enriquecidas['_data_especifica_usuario'] = True  # Flag indicando que veio do usuário
            logger.info(f"[EXTRACTOR] Data específica adicionada às entidades: {resultado['data_especifica']}")

        return entidades_enriquecidas, resultado['filtros']


# Singleton
_extractor: Optional[CompositeExtractor] = None


def get_extractor() -> CompositeExtractor:
    """Retorna instância do extrator."""
    global _extractor
    if _extractor is None:
        _extractor = CompositeExtractor()
    return _extractor


def extrair_condicoes(texto: str) -> Dict[str, Any]:
    """Função de conveniência para extrair condições."""
    return get_extractor().extrair(texto)


def enriquecer_entidades(texto: str, entidades: Dict) -> Tuple[Dict, List[Dict]]:
    """Função de conveniência para enriquecer entidades."""
    return get_extractor().extrair_e_enriquecer_entidades(texto, entidades)

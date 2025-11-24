"""
Sistema de Sugestoes Inteligentes do Claude AI Lite.

Gera sugestoes de perguntas alternativas quando o sistema
nao consegue responder uma consulta.

Funcionalidades:
1. Analisa entidades detectadas
2. Identifica tipo de pergunta (simples/composta)
3. Gera sugestoes baseadas no contexto
4. Detecta dimensoes da pergunta

Limite: 200 linhas
"""

import logging
from typing import Dict, List, Tuple, Optional

logger = logging.getLogger(__name__)

# Mapeamento de dimensoes para capacidades existentes
DIMENSOES_CAPACIDADES = {
    'num_pedido': ['consultar_pedido', 'analisar_disponibilidade', 'analisar_gargalo'],
    'cliente': ['consultar_pedido'],
    'produto': ['consultar_produto', 'consultar_estoque'],
    'data': [],  # Nenhuma capacidade suporta data isoladamente ainda
    'rota': ['consultar_rota'],
    'sub_rota': ['consultar_rota'],
    'uf': ['consultar_rota'],
    'estoque': ['consultar_estoque'],
}

# Templates de sugestoes por combinacao de dimensoes
TEMPLATES_SUGESTOES = {
    ('cliente',): [
        "Pedidos do cliente {cliente}",
        "Status dos pedidos do {cliente}",
    ],
    ('num_pedido',): [
        "Pedido {num_pedido}",
        "Quando posso enviar o pedido {num_pedido}?",
        "O que esta travando o pedido {num_pedido}?",
    ],
    ('produto',): [
        "Qual o estoque de {produto}?",
        "{produto} na carteira",
        "Pedidos com {produto}",
    ],
    ('cliente', 'produto'): [
        "Pedidos do cliente {cliente}",
        "Qual o estoque de {produto}?",
    ],
    ('cliente', 'data'): [
        "Pedidos do cliente {cliente}",
        "Depois, pergunte: 'Quando posso enviar o pedido X?' para cada pedido",
    ],
    ('cliente', 'estoque'): [
        "Pedidos do cliente {cliente}",
        "Para cada pedido, pergunte: 'Quando posso enviar?'",
    ],
    ('cliente', 'data', 'estoque'): [
        "1. Primeiro: 'Pedidos do cliente {cliente}'",
        "2. Para cada pedido: 'Quando posso enviar o pedido X?'",
        "Isso mostrara a disponibilidade de estoque para cada pedido.",
    ],
    ('rota',): [
        "Pedidos na rota {rota}",
        "O que tem para a rota {rota}?",
    ],
    ('uf',): [
        "Pedidos para {uf}",
        "O que tem para {uf}?",
    ],
}


class Suggester:
    """Gera sugestoes inteligentes baseadas no contexto."""

    def analisar_pergunta(self, consulta: str, intencao: dict) -> Dict:
        """
        Analisa uma pergunta e retorna informacoes sobre sua complexidade.

        Args:
            consulta: Texto original da pergunta
            intencao: Dict com dominio, intencao e entidades

        Returns:
            Dict com tipo_pergunta, dimensoes e analise
        """
        entidades = intencao.get('entidades', {})
        dimensoes = self._extrair_dimensoes(entidades, consulta)

        tipo = 'simples'
        if len(dimensoes) > 1:
            tipo = 'composta'
        elif len(dimensoes) == 0:
            tipo = 'ambigua'

        return {
            'tipo_pergunta': tipo,
            'dimensoes': dimensoes,
            'entidades_validas': {k: v for k, v in entidades.items() if v and str(v).lower() not in ('null', 'none', '')},
            'tem_capacidade': self._tem_capacidade_para_dimensoes(dimensoes),
            'capacidades_necessarias': self._capacidades_para_dimensoes(dimensoes),
        }

    def _extrair_dimensoes(self, entidades: dict, consulta: str) -> List[str]:
        """Extrai dimensoes presentes na consulta."""
        dimensoes = []

        # Dimensoes de entidades explicitas
        for campo, valor in entidades.items():
            if valor and str(valor).lower() not in ('null', 'none', ''):
                if campo in ('num_pedido', 'cliente', 'raz_social_red', 'cnpj'):
                    if 'cliente' not in dimensoes and campo != 'num_pedido':
                        dimensoes.append('cliente')
                    elif campo == 'num_pedido':
                        dimensoes.append('num_pedido')
                elif campo in ('produto', 'cod_produto'):
                    if 'produto' not in dimensoes:
                        dimensoes.append('produto')
                elif campo == 'data':
                    dimensoes.append('data')
                elif campo == 'rota':
                    dimensoes.append('rota')
                elif campo == 'sub_rota':
                    dimensoes.append('sub_rota')
                elif campo == 'uf':
                    dimensoes.append('uf')

        # Detecta dimensoes implicitas na consulta
        consulta_lower = consulta.lower()

        if any(p in consulta_lower for p in ['estoque', 'disponivel', 'disponibilidade', 'tem para enviar']):
            if 'estoque' not in dimensoes:
                dimensoes.append('estoque')

        if any(p in consulta_lower for p in ['dia ', 'data ', 'semana', 'mes', 'amanha', 'hoje', '/']):
            if 'data' not in dimensoes:
                # Verifica se tem padrao de data
                import re
                if re.search(r'\d{1,2}/\d{1,2}', consulta):
                    dimensoes.append('data')

        return dimensoes

    def _tem_capacidade_para_dimensoes(self, dimensoes: List[str]) -> bool:
        """Verifica se existe capacidade que atende todas as dimensoes."""
        if len(dimensoes) <= 1:
            return True

        # Combinacoes suportadas atualmente
        combinacoes_suportadas = [
            {'num_pedido'},  # analisar_disponibilidade ja faz pedido + estoque
            {'num_pedido', 'estoque'},
            {'produto'},
            {'cliente'},
            {'rota'},
            {'sub_rota'},
            {'uf'},
        ]

        dimensoes_set = set(dimensoes)
        return any(dimensoes_set <= suportada for suportada in combinacoes_suportadas)

    def _capacidades_para_dimensoes(self, dimensoes: List[str]) -> List[str]:
        """Retorna capacidades necessarias para atender as dimensoes."""
        capacidades = set()
        for dim in dimensoes:
            caps = DIMENSOES_CAPACIDADES.get(dim, [])
            capacidades.update(caps)
        return list(capacidades)

    def gerar_sugestoes(self, consulta: str, intencao: dict, motivo_falha: str) -> str:
        """
        Gera sugestoes de perguntas alternativas.

        Args:
            consulta: Texto original
            intencao: Dict com classificacao
            motivo_falha: Motivo da falha

        Returns:
            Texto formatado com sugestoes
        """
        analise = self.analisar_pergunta(consulta, intencao)
        entidades = analise['entidades_validas']
        dimensoes = tuple(sorted(analise['dimensoes']))

        sugestoes = []

        # Busca template especifico para as dimensoes
        if dimensoes in TEMPLATES_SUGESTOES:
            for template in TEMPLATES_SUGESTOES[dimensoes]:
                try:
                    sugestao = template.format(**entidades)
                    sugestoes.append(sugestao)
                except KeyError:
                    sugestoes.append(template)

        # Sugestoes genericas baseadas em entidades individuais
        if not sugestoes:
            if entidades.get('cliente') or entidades.get('raz_social_red'):
                cliente = entidades.get('cliente') or entidades.get('raz_social_red')
                sugestoes.append(f"Pedidos do cliente {cliente}")

            if entidades.get('num_pedido'):
                sugestoes.append(f"Pedido {entidades['num_pedido']}")
                sugestoes.append(f"Quando posso enviar o pedido {entidades['num_pedido']}?")

            if entidades.get('produto'):
                sugestoes.append(f"Qual o estoque de {entidades['produto']}?")
                sugestoes.append(f"{entidades['produto']} na carteira")

        # Mensagem formatada
        if analise['tipo_pergunta'] == 'composta':
            intro = (
                "Sua pergunta combina varias dimensoes que ainda nao consigo processar juntas.\n\n"
                "Tente separar em perguntas mais especificas:"
            )
        else:
            intro = "Tente uma dessas perguntas:"

        if sugestoes:
            linhas = [intro]
            for i, sug in enumerate(sugestoes[:4], 1):
                linhas.append(f"  {i}. {sug}")
            return "\n".join(linhas)

        # Fallback
        return (
            "Posso te ajudar com:\n"
            "  - 'Pedido VCD123' - consultar um pedido\n"
            "  - 'Quando posso enviar VCD123?' - verificar disponibilidade\n"
            "  - 'Pedidos do cliente Atacadao' - buscar por cliente\n"
            "  - 'Qual o estoque de azeitona?' - consultar estoque"
        )


# Singleton
_suggester: Optional[Suggester] = None


def get_suggester() -> Suggester:
    """Retorna instancia do Suggester."""
    global _suggester
    if _suggester is None:
        _suggester = Suggester()
    return _suggester


def analisar_e_sugerir(consulta: str, intencao: dict, motivo_falha: str) -> Tuple[str, Dict]:
    """
    Funcao de conveniencia para analisar e gerar sugestoes.

    Returns:
        Tupla (sugestao_texto, analise_dict)
    """
    suggester = get_suggester()
    analise = suggester.analisar_pergunta(consulta, intencao)
    sugestao = suggester.gerar_sugestoes(consulta, intencao, motivo_falha)
    return sugestao, analise

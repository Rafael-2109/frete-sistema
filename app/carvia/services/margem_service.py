"""
MargemService — Analise de margem entre preco de venda (CarVia) e custo (subcontrato)
======================================================================================

Compara:
- Fatura CarVia (a receber) = tabela CarVia (preco de venda)
- Fatura Subcontrato (a pagar) = CTes das transportadoras

Conciliacao:
- CarVia = CREDITO (recebemos do cliente)
- Subcontrato = DEBITO (pagamos a transportadora)
"""

import logging
from typing import Dict, List, Optional

from app import db

logger = logging.getLogger(__name__)


class MargemService:
    """Analise de margem venda vs custo para operacoes CarVia"""

    @staticmethod
    def calcular_margem_cotacao(cotacao_id: int) -> Optional[Dict]:
        """Calcula margem de uma cotacao: valor venda vs melhor custo subcontrato.

        Returns:
            {
                'valor_venda': float,      # Valor final aprovado (tabela CarVia)
                'valor_custo': float,       # Melhor opcao subcontrato (tabela Nacom)
                'margem_absoluta': float,   # venda - custo
                'margem_percentual': float, # (margem / venda) * 100
            }
        """
        from app.carvia.models import CarviaCotacao

        cotacao = db.session.get(CarviaCotacao, cotacao_id)
        if not cotacao:
            return None

        valor_venda = float(cotacao.valor_final_aprovado or cotacao.valor_tabela or 0)
        if valor_venda <= 0:
            return None

        # Buscar custo subcontrato
        valor_custo = MargemService._melhor_custo_subcontrato(cotacao)

        margem_abs = valor_venda - valor_custo
        margem_pct = (margem_abs / valor_venda) * 100 if valor_venda > 0 else 0

        return {
            'valor_venda': valor_venda,
            'valor_custo': valor_custo,
            'margem_absoluta': round(margem_abs, 2),
            'margem_percentual': round(margem_pct, 2),
        }

    @staticmethod
    def _melhor_custo_subcontrato(cotacao) -> float:
        """Busca o melhor (menor) custo de subcontrato para a cotacao."""
        try:
            from app.carvia.services.cotacao_service import CotacaoService
            svc = CotacaoService()

            destino = cotacao.endereco_destino
            if not destino or not destino.fisico_cidade or not destino.fisico_uf:
                return 0.0

            peso = float(cotacao.peso_cubado or cotacao.peso or 0)
            if cotacao.tipo_material == 'MOTO':
                peso = cotacao.peso_total_motos

            resultado = svc.cotar_todas_opcoes(
                cidade_destino=destino.fisico_cidade,
                uf_destino=destino.fisico_uf,
                peso=peso,
                valor_mercadoria=float(cotacao.valor_mercadoria or 0),
            )

            if resultado and resultado.get('sucesso'):
                opcoes = resultado.get('opcoes', [])
                if opcoes:
                    return min(o.get('valor_frete', float('inf')) for o in opcoes)
        except Exception as e:
            logger.warning("Erro ao buscar custo subcontrato: %s", e)

        return 0.0

    @staticmethod
    def resumo_margens(cotacoes_ids: Optional[List[int]] = None) -> Dict:
        """Resumo de margens de todas cotacoes aprovadas (ou lista especifica).

        Returns:
            {
                'total_cotacoes': int,
                'margem_media': float,
                'margem_minima': float,
                'margem_maxima': float,
                'cotacoes_negativas': int,  # margem < 0
                'detalhes': [...]
            }
        """
        from app.carvia.models import CarviaCotacao

        query = CarviaCotacao.query.filter(
            CarviaCotacao.status.in_(['APROVADO', 'ENVIADO'])
        )
        if cotacoes_ids:
            query = query.filter(CarviaCotacao.id.in_(cotacoes_ids))

        cotacoes = query.all()
        if not cotacoes:
            return {
                'total_cotacoes': 0,
                'margem_media': 0,
                'margem_minima': 0,
                'margem_maxima': 0,
                'cotacoes_negativas': 0,
                'detalhes': [],
            }

        detalhes = []
        margens = []

        for cot in cotacoes:
            resultado = MargemService.calcular_margem_cotacao(cot.id)
            if resultado:
                detalhes.append({
                    'cotacao_id': cot.id,
                    'numero_cotacao': cot.numero_cotacao,
                    'cliente': cot.cliente.nome_comercial if cot.cliente else '-',
                    **resultado,
                })
                margens.append(resultado['margem_percentual'])

        negativas = sum(1 for m in margens if m < 0)

        return {
            'total_cotacoes': len(detalhes),
            'margem_media': round(sum(margens) / len(margens), 2) if margens else 0,
            'margem_minima': round(min(margens), 2) if margens else 0,
            'margem_maxima': round(max(margens), 2) if margens else 0,
            'cotacoes_negativas': negativas,
            'detalhes': detalhes,
        }

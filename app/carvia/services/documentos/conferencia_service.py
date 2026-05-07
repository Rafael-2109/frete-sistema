"""
Conferencia Service — Calculo de opcoes de tabela e resumo de Fatura
======================================================================

REFATOR 2026-05-07: Conferencia individual de frete REMOVIDA.
A conferencia automatica de cada CarviaFrete passou a ser disparada no
lancamento do CTe (editar_frete_carvia), via
`AprovacaoFreteService.verificar_e_solicitar_se_necessario`. A aprovacao
da fatura e explicita via botao "Aprovar Conferencia"
(rota `aprovar_conferencia_fatura_transportadora`), independente do
status individual de cada frete (so bloqueia se ha tratativa D4 pendente).

Este service mantem:
- `calcular_opcoes_conferencia`: read-only, usado por
  `subcontratos/detalhe.html` (modalCotacao) para exibir opcoes de tabela
  de frete em modo simulacao (nao registra conferencia).
- `resumo_conferencia_fatura`: agregacao usada pela tela de conferencia da
  fatura (gate de tolerancia de R$ 1,00).

Metodos removidos: `listar_fretes_divergentes`, `registrar_conferencia`,
`_verificar_fatura_completa`.
"""

import logging
from typing import Dict

from app import db

logger = logging.getLogger(__name__)


class ConferenciaService:
    """Servico de agregacao de conferencia de Fatura Transportadora."""

    def calcular_opcoes_conferencia(self, subcontrato_id: int) -> Dict:
        """
        Calcula TODAS as opcoes de frete para um subcontrato,
        para o conferente comparar com o cte_valor cobrado.

        Read-only. Reutilizado pela tela `subcontratos/detalhe.html`
        (modal de cotacao simulada) — nao persiste conferencia.

        Args:
            subcontrato_id: ID do CarviaSubcontrato

        Returns:
            Dict com sucesso, subcontrato_info, operacao_info, opcoes, total_opcoes.
        """
        from app.carvia.models import CarviaSubcontrato, CarviaOperacao

        sub = db.session.get(CarviaSubcontrato, subcontrato_id)
        if not sub:
            return {'sucesso': False, 'erro': 'Subcontrato nao encontrado'}

        operacao = db.session.get(CarviaOperacao, sub.operacao_id)
        if not operacao:
            return {'sucesso': False, 'erro': 'Operacao nao encontrada'}

        peso_bruto = float(operacao.peso_bruto or 0)
        peso_cubado = float(operacao.peso_cubado or 0)
        peso = max(peso_bruto, peso_cubado)
        valor_mercadoria = float(operacao.valor_mercadoria or 0)
        uf_destino = operacao.uf_destino
        uf_origem = operacao.uf_origem
        cidade_destino = operacao.cidade_destino

        if peso <= 0:
            return {'sucesso': False, 'erro': 'Peso nao informado na operacao'}
        if not uf_destino:
            return {'sucesso': False, 'erro': 'UF destino nao informada'}

        subcontrato_info = {
            'id': sub.id,
            'cte_numero': sub.cte_numero,
            'cte_valor': float(sub.cte_valor) if sub.cte_valor else None,
            'valor_cotado': float(sub.valor_cotado) if sub.valor_cotado else None,
            'valor_acertado': float(sub.valor_acertado) if sub.valor_acertado else None,
            'valor_final': float(sub.valor_final) if sub.valor_final else None,
            'status': sub.status,
            'status_conferencia': (
                sub.frete.status_conferencia if sub.frete else 'PENDENTE'
            ),
            'valor_considerado': (
                float(sub.frete.valor_considerado)
                if sub.frete and sub.frete.valor_considerado else None
            ),
        }

        operacao_info = {
            'id': operacao.id,
            'cidade_destino': cidade_destino,
            'uf_destino': uf_destino,
            'uf_origem': uf_origem,
            'peso': peso,
            'valor_mercadoria': valor_mercadoria,
            'nome_cliente': operacao.nome_cliente,
        }

        try:
            from app.carvia.services.pricing.cotacao_service import CotacaoService
            cotacao_svc = CotacaoService()
            opcoes = self._buscar_opcoes_transportadora(
                cotacao_svc, sub.transportadora_id,
                peso, valor_mercadoria,
                uf_destino, uf_origem, cidade_destino,
            )
            return {
                'sucesso': True,
                'subcontrato_info': subcontrato_info,
                'operacao_info': operacao_info,
                'opcoes': opcoes,
                'total_opcoes': len(opcoes),
            }
        except Exception as e:
            logger.error(f"Erro ao calcular opcoes conferencia sub {subcontrato_id}: {e}")
            return {'sucesso': False, 'erro': str(e)}

    def _buscar_opcoes_transportadora(self, cotacao_svc, transportadora_id: int,
                                       peso: float, valor_mercadoria: float,
                                       uf_destino: str, uf_origem: str,
                                       cidade_destino: str) -> list:
        """Busca tabelas de frete da transportadora e calcula valor para cada."""
        from app.tabelas.models import TabelaFrete
        from app.transportadoras.models import Transportadora

        grupo_ids = cotacao_svc._obter_grupo_transportadora(transportadora_id)
        transportadora = db.session.get(Transportadora, transportadora_id)
        transportadora_nome = transportadora.razao_social if transportadora else '?'

        opcoes = []
        cidade_obj = None
        if cidade_destino:
            cidade_obj = cotacao_svc._resolver_cidade(cidade_destino, uf_destino)

        tabelas_encontradas = {}
        if cidade_obj:
            vinculos = cotacao_svc._buscar_vinculos_cidade(cidade_obj.codigo_ibge)
            for vinculo in vinculos:
                if vinculo.transportadora_id not in grupo_ids:
                    continue
                query = TabelaFrete.query.filter(
                    TabelaFrete.transportadora_id.in_(grupo_ids),
                    TabelaFrete.uf_destino == uf_destino,
                    TabelaFrete.nome_tabela == vinculo.nome_tabela,
                )
                if uf_origem:
                    query = query.filter(TabelaFrete.uf_origem == uf_origem)
                for tf in query.all():
                    tabelas_encontradas[tf.id] = tf

        if not tabelas_encontradas:
            query = TabelaFrete.query.filter(
                TabelaFrete.transportadora_id.in_(grupo_ids),
                TabelaFrete.uf_destino == uf_destino,
            )
            if uf_origem:
                query = query.filter(TabelaFrete.uf_origem == uf_origem)
            for tf in query.all():
                tabelas_encontradas[tf.id] = tf

        for tabela in tabelas_encontradas.values():
            try:
                resultado = cotacao_svc._calcular_com_tabela(
                    tabela, peso, valor_mercadoria,
                    uf_destino, cidade_destino,
                )
                if not resultado:
                    continue
                tabela_dados = resultado.get('tabela_dados', {})
                detalhes = resultado.get('detalhes', {})
                descritivo = cotacao_svc._montar_descritivo(
                    tabela_dados, detalhes, peso, valor_mercadoria,
                )
                transp_tabela = db.session.get(Transportadora, tabela.transportadora_id)
                opcoes.append({
                    'tabela_frete_id': tabela.id,
                    'tabela_nome': tabela.nome_tabela,
                    'tipo_carga': tabela.tipo_carga,
                    'modalidade': tabela.modalidade,
                    'transportadora_id': tabela.transportadora_id,
                    'transportadora_nome': (
                        transp_tabela.razao_social if transp_tabela
                        else transportadora_nome
                    ),
                    'valor_frete': round(resultado['valor'], 2),
                    'detalhes': detalhes,
                    'descritivo': descritivo,
                })
            except Exception as e:
                logger.warning(f"Erro ao calcular com tabela {tabela.id}: {e}")
                continue

        opcoes.sort(key=lambda x: x['valor_frete'])
        return opcoes

    def resumo_conferencia_fatura(self, fatura_id: int) -> Dict:
        """Retorna resumo da conferencia de uma fatura.

        Paridade Nacom: itera CarviaFrete (unidade de analise).

        Returns:
            Dict com total, aprovados, divergentes, pendentes,
            soma_cte_valor, soma_considerado, soma_valor_pago,
            soma_custos_entrega, valor_conferido_total, valor_pago_total.
        """
        from app.carvia.models import CarviaFrete, CarviaCustoEntrega

        fretes = CarviaFrete.query.filter(
            CarviaFrete.fatura_transportadora_id == fatura_id,
            CarviaFrete.status != 'CANCELADO',
        ).all()

        total = len(fretes)
        aprovados = sum(1 for f in fretes if f.status_conferencia == 'APROVADO')
        divergentes = sum(1 for f in fretes if f.status_conferencia == 'DIVERGENTE')
        pendentes = total - aprovados - divergentes

        soma_cte_valor = sum(float(f.valor_cte or 0) for f in fretes)
        soma_considerado = sum(float(f.valor_considerado or 0) for f in fretes)
        soma_valor_pago = sum(float(f.valor_pago or 0) for f in fretes)

        ces = CarviaCustoEntrega.query.filter(
            CarviaCustoEntrega.fatura_transportadora_id == fatura_id,
            CarviaCustoEntrega.status != 'CANCELADO',
        ).all()
        soma_custos_entrega = sum(float(ce.valor or 0) for ce in ces)
        total_ces = len(ces)
        valor_conferido_total = soma_considerado + soma_custos_entrega
        valor_pago_total = soma_valor_pago + soma_custos_entrega

        return {
            'total': total,
            'aprovados': aprovados,
            'divergentes': divergentes,
            'pendentes': pendentes,
            'soma_cte_valor': round(soma_cte_valor, 2),
            'soma_considerado': round(soma_considerado, 2),
            'soma_valor_pago': round(soma_valor_pago, 2),
            'soma_custos_entrega': round(soma_custos_entrega, 2),
            'total_ces': total_ces,
            'valor_conferido_total': round(valor_conferido_total, 2),
            'valor_pago_total': round(valor_pago_total, 2),
            'diferenca': round(soma_cte_valor - soma_considerado, 2) if total else None,
            'percentual_conferido': round((aprovados + divergentes) / total * 100) if total else 0,
        }

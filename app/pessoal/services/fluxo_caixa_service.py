"""Service da vertente FLUXO DE CAIXA do modulo Pessoal.

Complementa dashboard_service.py (vertente COMPETENCIA). Enquanto o dashboard normal
responde "quanto voce gastou no mes X", este service responde "quando o dinheiro
saiu/entrou da conta corrente".

Regras de inclusao (fluxo de caixa, conta corrente):
- ENTRADAS: tipo=credito, conta=CC, NAO eh_transferencia_propria, NAO eh_pagamento_cartao
- SAIDAS: tipo=debito, conta=CC, NAO eh_transferencia_propria
  (INCLUI eh_pagamento_cartao=True — pagamento de fatura e saida real de caixa)
- Compras no cartao (conta.tipo=cartao_credito) NAO entram — estao refletidas na fatura
- Transferencias proprias (eh_transferencia_propria=True) NAO entram em ambas pontas
- Transacoes compensadas (valor_compensado > 0) ENTRAM com valor NOMINAL (o dinheiro
  realmente saiu/entrou no caixa; a compensacao so afeta relatorio de competencia)

Provisoes:
- PessoalProvisao com status=PROVISIONADA e data_prevista no mes: entram como
  linhas provisionadas (forecast). Orcamento datado materializa provisoes de saida.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

from sqlalchemy import and_, func

from app import db
from app.pessoal.models import (
    PessoalCategoria, PessoalConta, PessoalImportacao, PessoalOrcamento,
    PessoalProvisao, PessoalTransacao,
)
from app.utils.timezone import agora_utc_naive


MESES_PT = [
    'Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
    'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez',
]


def _mes_label(ano: int, mes: int) -> str:
    return f'{MESES_PT[mes - 1]}/{ano}'


def _range_mes(ano: int, mes: int) -> tuple[date, date]:
    """Retorna (inicio, proximo_mes) — intervalo semi-aberto [inicio, proximo)."""
    inicio = date(ano, mes, 1)
    if mes == 12:
        proximo = date(ano + 1, 1, 1)
    else:
        proximo = date(ano, mes + 1, 1)
    return inicio, proximo


def _janela_meses(ano_ref: int, mes_ref: int, meses: int) -> list[dict]:
    """Lista crescente de N meses terminando em (ano_ref, mes_ref)."""
    janela = []
    for i in range(meses - 1, -1, -1):
        m = mes_ref - i
        a = ano_ref
        while m <= 0:
            m += 12
            a -= 1
        inicio, proximo = _range_mes(a, m)
        janela.append({
            'ano': a,
            'mes': m,
            'inicio': inicio,
            'proximo': proximo,
            'mes_str': inicio.strftime('%Y-%m'),
            'mes_label': _mes_label(a, m),
        })
    return janela


# =============================================================================
# FILTROS DE QUERY (regras de fluxo de caixa)
# =============================================================================
def _filtros_cc_sem_transf():
    """Base: CC + nao transf propria. NAO filtra excluir_relatorio.

    Usado por _pagamento_cartao_to_linha — pagamentos de fatura tem
    excluir_relatorio=True (sao excluidos da vertente competencia), mas
    DEVEM aparecer como saida no fluxo de caixa.
    """
    return [
        PessoalTransacao.eh_transferencia_propria.is_(False),
        # Apenas transacoes em conta corrente (cartao de credito nao entra — fica
        # por conta do pagamento da fatura, que e debito na CC).
        PessoalTransacao.conta_id.in_(
            db.session.query(PessoalConta.id).filter(
                PessoalConta.tipo == 'conta_corrente',
            )
        ),
    ]


def _filtros_caixa_base():
    """Filtros para entradas/saidas comuns do fluxo (exceto pagamentos de cartao).

    Inclui excluir_relatorio=False: transacoes 100% compensadas (pares empresa,
    saldo anterior, itens em categoria Desconsiderar) ficam fora.
    Residuos parciais (valor_compensado < valor) permanecem com excluir_relatorio=False
    e entram somados como (valor - valor_compensado) via _EXPR_VALOR_EFETIVO.
    """
    return [
        PessoalTransacao.excluir_relatorio.is_(False),
        *_filtros_cc_sem_transf(),
    ]


# Expressao SQL para "valor efetivo" = valor - valor_compensado (nunca negativo).
# Usada nas agregacoes mensais para refletir residuo de compensacoes parciais.
_EXPR_VALOR_EFETIVO = (
    PessoalTransacao.valor - func.coalesce(PessoalTransacao.valor_compensado, 0)
)


def _filtro_entrada():
    """Filtro para ENTRADAS de caixa.

    Exclui:
    - Pagamento de cartao (esse e SAIDA, nao entrada)
    - Transferencia propria (nem entra nem sai)
    """
    return [
        PessoalTransacao.tipo == 'credito',
        PessoalTransacao.eh_pagamento_cartao.is_(False),
        *_filtros_caixa_base(),
    ]


def _filtro_saida():
    """Filtro para SAIDAS de caixa. Inclui pagamentos de cartao."""
    return [
        PessoalTransacao.tipo == 'debito',
        *_filtros_caixa_base(),
    ]


# =============================================================================
# AGREGACOES MENSAIS
# =============================================================================
@dataclass
class FluxoMes:
    ano: int
    mes: int
    mes_str: str
    mes_label: str
    is_futuro: bool
    is_atual: bool
    # Realizadas
    entradas_realizadas: float
    saidas_realizadas: float
    # Provisoes
    entradas_provisionadas: float
    saidas_provisionadas: float
    # Derivados
    saldo_mes: float           # entradas_total - saidas_total
    saldo_acumulado: float     # soma dos saldos ate este mes
    # Orcamento (comparativo)
    orcamento_global: Optional[float]
    # % do orcamento consumido pelas saidas realizadas
    percentual_orcamento: Optional[float]

    def to_dict(self):
        return {
            'ano': self.ano,
            'mes': self.mes,
            'mes_str': self.mes_str,
            'mes_label': self.mes_label,
            'is_futuro': self.is_futuro,
            'is_atual': self.is_atual,
            'entradas_realizadas': round(self.entradas_realizadas, 2),
            'saidas_realizadas': round(self.saidas_realizadas, 2),
            'entradas_provisionadas': round(self.entradas_provisionadas, 2),
            'saidas_provisionadas': round(self.saidas_provisionadas, 2),
            'entradas_total': round(
                self.entradas_realizadas + self.entradas_provisionadas, 2
            ),
            'saidas_total': round(
                self.saidas_realizadas + self.saidas_provisionadas, 2
            ),
            'saldo_mes': round(self.saldo_mes, 2),
            'saldo_acumulado': round(self.saldo_acumulado, 2),
            'orcamento_global': (
                round(self.orcamento_global, 2) if self.orcamento_global else None
            ),
            'percentual_orcamento': (
                round(self.percentual_orcamento, 1)
                if self.percentual_orcamento is not None else None
            ),
        }


def fluxo_por_mes(
    ano_ref: int,
    mes_ref: int,
    meses_anteriores: int = 6,
    meses_futuros: int = 6,
    saldo_inicial: float = 0.0,
) -> list[dict]:
    """Retorna serie mensal de fluxo de caixa (realizado + provisionado).

    Args:
        ano_ref/mes_ref: mes de referencia (centro da janela)
        meses_anteriores: quantos meses antes do ref incluir (historico realizado)
        meses_futuros: quantos meses depois do ref incluir (projecao com provisoes)
        saldo_inicial: saldo anterior ao primeiro mes (para acumulado)
    """
    # Janela: meses_anteriores antes + mes ref + meses_futuros depois
    total_meses = meses_anteriores + 1 + meses_futuros
    # Janela crescente terminando em (mes_ref + meses_futuros)
    m_final = mes_ref + meses_futuros
    a_final = ano_ref
    while m_final > 12:
        m_final -= 12
        a_final += 1
    janela = _janela_meses(a_final, m_final, total_meses)

    hoje = agora_utc_naive().date()
    hoje_ano_mes = (hoje.year, hoje.month)

    # Query agregacoes em 1 rodada por tipo
    inicio_total = janela[0]['inicio']
    fim_total = janela[-1]['proximo']

    # Entradas realizadas (soma valor_efetivo = valor - valor_compensado)
    entradas_real = dict(db.session.query(
        func.to_char(PessoalTransacao.data, 'YYYY-MM').label('mes_str'),
        func.sum(_EXPR_VALOR_EFETIVO),
    ).filter(
        and_(
            PessoalTransacao.data >= inicio_total,
            PessoalTransacao.data < fim_total,
            *_filtro_entrada(),
        )
    ).group_by('mes_str').all())

    # Saidas realizadas (soma valor_efetivo) — exclui pagtos cartao e compensadas
    saidas_real = dict(db.session.query(
        func.to_char(PessoalTransacao.data, 'YYYY-MM').label('mes_str'),
        func.sum(_EXPR_VALOR_EFETIVO),
    ).filter(
        and_(
            PessoalTransacao.data >= inicio_total,
            PessoalTransacao.data < fim_total,
            PessoalTransacao.eh_pagamento_cartao.is_(False),  # exclui — somado abaixo
            *_filtro_saida(),
        )
    ).group_by('mes_str').all())

    # Pagamentos de fatura de cartao — saida real de caixa, mesmo com
    # excluir_relatorio=True (bypass do filtro base via _filtros_cc_sem_transf).
    pagtos_cartao_real = dict(db.session.query(
        func.to_char(PessoalTransacao.data, 'YYYY-MM').label('mes_str'),
        func.sum(_EXPR_VALOR_EFETIVO),
    ).filter(
        and_(
            PessoalTransacao.data >= inicio_total,
            PessoalTransacao.data < fim_total,
            PessoalTransacao.tipo == 'debito',
            PessoalTransacao.eh_pagamento_cartao.is_(True),
            *_filtros_cc_sem_transf(),
        )
    ).group_by('mes_str').all())

    # Provisoes (PROVISIONADA: ainda nao realizada)
    prov_entradas = dict(db.session.query(
        func.to_char(PessoalProvisao.data_prevista, 'YYYY-MM').label('mes_str'),
        func.sum(PessoalProvisao.valor),
    ).filter(
        PessoalProvisao.status == 'PROVISIONADA',
        PessoalProvisao.tipo == 'entrada',
        PessoalProvisao.data_prevista >= inicio_total,
        PessoalProvisao.data_prevista < fim_total,
    ).group_by('mes_str').all())

    prov_saidas = dict(db.session.query(
        func.to_char(PessoalProvisao.data_prevista, 'YYYY-MM').label('mes_str'),
        func.sum(PessoalProvisao.valor),
    ).filter(
        PessoalProvisao.status == 'PROVISIONADA',
        PessoalProvisao.tipo == 'saida',
        PessoalProvisao.data_prevista >= inicio_total,
        PessoalProvisao.data_prevista < fim_total,
    ).group_by('mes_str').all())

    # Orcamentos globais (categoria_id NULL = global)
    orcamentos_global = dict(db.session.query(
        func.to_char(PessoalOrcamento.ano_mes, 'YYYY-MM').label('mes_str'),
        PessoalOrcamento.valor_limite,
    ).filter(
        PessoalOrcamento.categoria_id.is_(None),
        PessoalOrcamento.ano_mes >= inicio_total,
        PessoalOrcamento.ano_mes < fim_total,
    ).all())

    resultado: list[dict] = []
    saldo_acumulado = float(saldo_inicial)

    for m in janela:
        mes_str = m['mes_str']
        entradas = float(entradas_real.get(mes_str, 0) or 0)
        saidas_comuns = float(saidas_real.get(mes_str, 0) or 0)
        pagtos_cartao = float(pagtos_cartao_real.get(mes_str, 0) or 0)
        saidas = saidas_comuns + pagtos_cartao
        prov_e = float(prov_entradas.get(mes_str, 0) or 0)
        prov_s = float(prov_saidas.get(mes_str, 0) or 0)

        saldo_mes = (entradas + prov_e) - (saidas + prov_s)
        saldo_acumulado += saldo_mes

        orc = orcamentos_global.get(mes_str)
        orc = float(orc) if orc is not None else None
        percentual = (
            (saidas / orc * 100) if (orc and orc > 0) else None
        )

        is_atual = (m['ano'], m['mes']) == hoje_ano_mes
        is_futuro = (m['ano'], m['mes']) > hoje_ano_mes

        fm = FluxoMes(
            ano=m['ano'],
            mes=m['mes'],
            mes_str=mes_str,
            mes_label=m['mes_label'],
            is_futuro=is_futuro,
            is_atual=is_atual,
            entradas_realizadas=entradas,
            saidas_realizadas=saidas,
            entradas_provisionadas=prov_e,
            saidas_provisionadas=prov_s,
            saldo_mes=saldo_mes,
            saldo_acumulado=saldo_acumulado,
            orcamento_global=orc,
            percentual_orcamento=percentual,
        )
        resultado.append(fm.to_dict())

    return resultado


# =============================================================================
# DETALHAMENTO DO MES (lista de lancamentos)
# =============================================================================
def detalhe_do_mes(ano: int, mes: int) -> dict:
    """Lista detalhada de lancamentos do mes:
       entradas, saidas, pagamentos de cartao, provisoes.
    """
    inicio, proximo = _range_mes(ano, mes)

    # ENTRADAS realizadas (tx CC, credito, nao pagamento cartao, nao transf propria)
    q_entradas = PessoalTransacao.query.filter(
        and_(
            PessoalTransacao.data >= inicio,
            PessoalTransacao.data < proximo,
            *_filtro_entrada(),
        )
    ).order_by(PessoalTransacao.data.asc(), PessoalTransacao.id.asc())

    entradas = [_transacao_to_linha(t, 'entrada') for t in q_entradas.all()]

    # SAIDAS realizadas EXCETO pagamentos de cartao (esses viram bloco separado)
    q_saidas = PessoalTransacao.query.filter(
        and_(
            PessoalTransacao.data >= inicio,
            PessoalTransacao.data < proximo,
            PessoalTransacao.eh_pagamento_cartao.is_(False),
            *_filtro_saida(),
        )
    ).order_by(PessoalTransacao.data.asc(), PessoalTransacao.id.asc())

    saidas = [_transacao_to_linha(t, 'saida') for t in q_saidas.all()]

    # PAGAMENTOS DE CARTAO (fatura) — 1 linha por pagamento, com link para fatura
    # Usa _filtros_cc_sem_transf (NAO filtra excluir_relatorio) — pagamentos de
    # fatura sao sempre excluir_relatorio=True mas DEVEM aparecer no fluxo.
    q_pagtos = PessoalTransacao.query.filter(
        and_(
            PessoalTransacao.data >= inicio,
            PessoalTransacao.data < proximo,
            PessoalTransacao.eh_pagamento_cartao.is_(True),
            *_filtros_cc_sem_transf(),
        )
    ).order_by(PessoalTransacao.data.asc())

    pagamentos_cartao = [_pagamento_cartao_to_linha(t) for t in q_pagtos.all()]

    # PROVISOES (status=PROVISIONADA no mes)
    q_prov = PessoalProvisao.query.filter(
        PessoalProvisao.status == 'PROVISIONADA',
        PessoalProvisao.data_prevista >= inicio,
        PessoalProvisao.data_prevista < proximo,
    ).order_by(PessoalProvisao.data_prevista.asc(), PessoalProvisao.id.asc())

    provisoes = [p.to_dict() for p in q_prov.all()]

    # Totais
    total_entradas = sum(l['valor'] for l in entradas)
    total_saidas = sum(l['valor'] for l in saidas)
    total_pagtos_cartao = sum(l['valor'] for l in pagamentos_cartao)
    total_prov_entradas = sum(
        p['valor'] for p in provisoes if p['tipo'] == 'entrada'
    )
    total_prov_saidas = sum(
        p['valor'] for p in provisoes if p['tipo'] == 'saida'
    )

    return {
        'ano': ano,
        'mes': mes,
        'mes_label': _mes_label(ano, mes),
        'inicio': inicio.isoformat(),
        'fim': (proximo).isoformat(),
        'entradas': entradas,
        'saidas': saidas,
        'pagamentos_cartao': pagamentos_cartao,
        'provisoes': provisoes,
        'totais': {
            'entradas': round(total_entradas, 2),
            'saidas': round(total_saidas, 2),
            'pagamentos_cartao': round(total_pagtos_cartao, 2),
            'saidas_total': round(total_saidas + total_pagtos_cartao, 2),
            'provisoes_entradas': round(total_prov_entradas, 2),
            'provisoes_saidas': round(total_prov_saidas, 2),
            'saldo_mes_realizado': round(
                total_entradas - total_saidas - total_pagtos_cartao, 2
            ),
            'saldo_mes_com_provisoes': round(
                (total_entradas + total_prov_entradas)
                - (total_saidas + total_pagtos_cartao + total_prov_saidas),
                2,
            ),
        },
    }


def _transacao_to_linha(t: PessoalTransacao, lado: str) -> dict:
    """Converte PessoalTransacao para linha resumida do fluxo (sem drilldown).

    Exibe valor_efetivo (valor - valor_compensado) quando ha compensacao parcial —
    residuos de compensacoes empresa aparecem com o saldo real, nao o valor nominal.
    """
    valor_nominal = float(t.valor)
    compensado = float(t.valor_compensado or 0)
    valor_efetivo = max(valor_nominal - compensado, 0.0)
    tem_residuo = compensado > 0 and compensado < valor_nominal
    return {
        'id': t.id,
        'tipo_fluxo': lado,  # entrada | saida
        'data': t.data.strftime('%d/%m/%Y') if t.data else None,
        'data_iso': t.data.isoformat() if t.data else None,
        'valor': valor_efetivo,           # exibicao padrao = residuo
        'valor_nominal': valor_nominal,   # valor original para tooltip
        'historico': t.historico,
        'descricao': t.descricao,
        'conta_id': t.conta_id,
        'conta_nome': t.conta.nome if t.conta else None,
        'categoria_id': t.categoria_id,
        'categoria_nome': t.categoria.nome if t.categoria else None,
        'categoria_grupo': t.categoria.grupo if t.categoria else None,
        'categoria_icone': t.categoria.icone if t.categoria else None,
        'membro_id': t.membro_id,
        'membro_nome': t.membro.nome if t.membro else None,
        'excluir_relatorio': t.excluir_relatorio,
        'valor_compensado': compensado,
        'tem_residuo': tem_residuo,       # flag para UI marcar "resto apos compensacao"
        'origem': 'realizada',
    }


def _pagamento_cartao_to_linha(t: PessoalTransacao) -> dict:
    """Linha do pagamento de fatura, com info da fatura vinculada (drilldown).

    Busca a PessoalImportacao (tipo_arquivo='fatura_cartao') que foi vinculada
    a este pagamento via transacao_pagamento_id. Se nao houver vinculo, mostra
    apenas a transacao bruta.
    """
    fatura = PessoalImportacao.query.filter_by(transacao_pagamento_id=t.id).first()

    # Se vinculado, busca dados da fatura (qt de compras, total, cartao)
    # 1 query agregada (SUM + COUNT) em vez de fat.transacoes.count() + scalar(SUM)
    fatura_info = None
    if fatura:
        agregado = db.session.query(
            func.count(PessoalTransacao.id),
            func.coalesce(func.sum(PessoalTransacao.valor), 0),
        ).filter(
            PessoalTransacao.importacao_id == fatura.id,
        ).one()
        n_compras = int(agregado[0] or 0)
        total_compras = float(agregado[1] or 0)

        fatura_info = {
            'id': fatura.id,
            'nome_arquivo': fatura.nome_arquivo,
            'periodo_inicio': (
                fatura.periodo_inicio.isoformat() if fatura.periodo_inicio else None
            ),
            'periodo_fim': (
                fatura.periodo_fim.isoformat() if fatura.periodo_fim else None
            ),
            'conta_id': fatura.conta_id,
            'conta_nome': fatura.conta.nome if fatura.conta else None,
            'n_compras': n_compras,
            'total_compras': total_compras,
            'divergencia_valor': round(float(t.valor) - total_compras, 2),
        }

    return {
        'id': t.id,
        'tipo_fluxo': 'saida',
        'data': t.data.strftime('%d/%m/%Y') if t.data else None,
        'data_iso': t.data.isoformat() if t.data else None,
        'valor': float(t.valor),
        'historico': t.historico,
        'descricao': t.descricao,
        'conta_id': t.conta_id,
        'conta_nome': t.conta.nome if t.conta else None,
        # Categoria forcada para visualizacao: 'Cartao de Credito'
        'categoria_nome': 'Cartao de Credito',
        'categoria_grupo': 'Financeiro',
        'categoria_icone': 'fa-credit-card',
        'eh_pagamento_cartao': True,
        'fatura': fatura_info,
        'origem': 'realizada',
    }


# =============================================================================
# DRILLDOWN DE FATURA (compras que compoem um pagamento)
# =============================================================================
def drilldown_fatura(pagamento_transacao_id: int) -> dict:
    """Dado um pagamento de fatura, retorna as compras originais.

    Procura a fatura (PessoalImportacao) vinculada via transacao_pagamento_id
    e lista as transacoes dela agrupadas por categoria.
    """
    t = db.session.get(PessoalTransacao, pagamento_transacao_id)
    if not t:
        return {'erro': 'Transacao nao encontrada', 'transacao_id': pagamento_transacao_id}
    if not t.eh_pagamento_cartao:
        return {
            'erro': 'Transacao nao e pagamento de cartao',
            'transacao_id': pagamento_transacao_id,
        }

    fatura = PessoalImportacao.query.filter_by(transacao_pagamento_id=t.id).first()
    if not fatura:
        return {
            'erro': 'Pagamento sem fatura vinculada',
            'transacao_id': pagamento_transacao_id,
            'pagamento': {
                'id': t.id,
                'data': t.data.isoformat() if t.data else None,
                'valor': float(t.valor),
                'historico': t.historico,
            },
        }

    compras = PessoalTransacao.query.filter_by(
        importacao_id=fatura.id,
    ).order_by(PessoalTransacao.data.asc()).all()

    # Agrupa por categoria
    por_categoria: dict[Optional[int], dict] = {}
    for c in compras:
        cid = c.categoria_id
        key = cid if cid else 0
        if key not in por_categoria:
            por_categoria[key] = {
                'categoria_id': cid,
                'categoria_nome': c.categoria.nome if c.categoria else 'Sem categoria',
                'categoria_grupo': c.categoria.grupo if c.categoria else None,
                'categoria_icone': c.categoria.icone if c.categoria else 'fa-question',
                'total': 0.0,
                'count': 0,
            }
        por_categoria[key]['total'] += float(c.valor)
        por_categoria[key]['count'] += 1

    return {
        'pagamento': {
            'id': t.id,
            'data': t.data.isoformat() if t.data else None,
            'valor': float(t.valor),
            'historico': t.historico,
            'conta_nome': t.conta.nome if t.conta else None,
        },
        'fatura': {
            'id': fatura.id,
            'nome_arquivo': fatura.nome_arquivo,
            'periodo_inicio': (
                fatura.periodo_inicio.isoformat() if fatura.periodo_inicio else None
            ),
            'periodo_fim': (
                fatura.periodo_fim.isoformat() if fatura.periodo_fim else None
            ),
            'conta_nome': fatura.conta.nome if fatura.conta else None,
        },
        'compras': [
            {
                'id': c.id,
                'data': c.data.strftime('%d/%m/%Y') if c.data else None,
                'historico': c.historico,
                'valor': float(c.valor),
                'categoria_nome': c.categoria.nome if c.categoria else None,
                'categoria_grupo': c.categoria.grupo if c.categoria else None,
                'categoria_icone': c.categoria.icone if c.categoria else None,
                'parcela_atual': c.parcela_atual,
                'parcela_total': c.parcela_total,
            }
            for c in compras
        ],
        'por_categoria': sorted(
            por_categoria.values(), key=lambda x: x['total'], reverse=True
        ),
        'total_compras': round(sum(float(c.valor) for c in compras), 2),
    }


# =============================================================================
# MOTIVO DE EXCLUSAO (para filtro na tela de transacoes)
# =============================================================================
def motivo_exclusao(t: PessoalTransacao) -> Optional[str]:
    """Determina motivo da exclusao de uma transacao OU compensacao parcial.

    Ordem de prioridade (uma unica causa sera reportada):
    1. 'SALDO_ANTERIOR'      - historico comeca com SALDO ANTERIOR (ruido de fatura)
    2. 'PAGAMENTO_CARTAO'    - eh_pagamento_cartao=True
    3. 'TRANSF_PROPRIA'      - eh_transferencia_propria=True
    4. 'COMPENSADA'          - valor_compensado > 0 (parcial ou total; mesmo excluir_relatorio=False)
    5. 'EMPRESA'             - categoria grupo='Desconsiderar' OU compensavel_tipo is not None
    6. None                  - excluir_relatorio=False e sem compensacao

    Returns:
        str (codigo do motivo) ou None se nao esta excluida.
    """
    valor = float(t.valor or 0)
    compensado = float(t.valor_compensado or 0)
    eh_parcial = valor > 0 and 0 < compensado < valor - 0.01

    # Transacoes NAO excluidas: so retornam motivo se houver compensacao parcial (Comp~)
    if not t.excluir_relatorio:
        if eh_parcial:
            return 'COMPENSADA'
        return None

    historico_norm = (t.historico or '').strip().upper()
    if historico_norm.startswith('SALDO ANTERIOR'):
        return 'SALDO_ANTERIOR'
    if t.eh_pagamento_cartao:
        return 'PAGAMENTO_CARTAO'
    if t.eh_transferencia_propria:
        return 'TRANSF_PROPRIA'
    if valor > 0 and compensado > 0:
        return 'COMPENSADA'
    cat = t.categoria
    if cat and (cat.grupo == 'Desconsiderar' or cat.compensavel_tipo is not None):
        return 'EMPRESA'
    # excluir_relatorio=True mas sem motivo claro (pode ter sido ajuste manual)
    return 'OUTRO'


def motivos_exclusao_batch(transacoes: list[PessoalTransacao]) -> dict[int, Optional[str]]:
    """Versao batch que evita N+1 no template. Retorna {id: motivo}."""
    return {t.id: motivo_exclusao(t) for t in transacoes}


# =============================================================================
# VISAO AGRUPADA — Accordion hierarquico dia -> grupo -> nome -> linhas
# =============================================================================
# Semantica:
#   - "Realizado" = PessoalTransacao com excluir_relatorio=False (regra de fluxo)
#     + pagamentos de cartao (eh_pagamento_cartao=True, independente de excluir_relatorio)
#     pagamentos de cartao caem em categoria virtual 'Financeiro' / 'Cartao de Credito'
#   - "Provisao"  = PessoalProvisao com status='PROVISIONADA' (PROVISIONADA ainda nao
#     materializou; REALIZADA ja virou transacao real)
#   - Categoria NULL: exibida como grupo='Sem Categoria' / nome='Sem Categoria'
#   - Dias sem movimento: nao aparecem
GRUPO_CARTAO = 'Financeiro'
NOME_CARTAO = 'Cartao de Credito'
GRUPO_SEM_CATEGORIA = 'Sem Categoria'
NOME_SEM_CATEGORIA = 'Sem Categoria'


def _categorias_map_mes(ano: int, mes: int) -> dict[int, tuple[str, str]]:
    """Retorna {categoria_id: (grupo, nome)} para categorias usadas no mes.

    Cache local para evitar N+1 ao expandir grupo/nome.
    """
    return {
        c.id: (c.grupo or GRUPO_SEM_CATEGORIA, c.nome or NOME_SEM_CATEGORIA)
        for c in PessoalCategoria.query.all()
    }


def _q_real_entradas(ano: int, mes: int):
    """Query de realizadas (ENTRADA) para o mes. Retorna SUM agregado."""
    inicio, proximo = _range_mes(ano, mes)
    return db.session.query(
        PessoalTransacao.data.label('data'),
        PessoalTransacao.categoria_id.label('categoria_id'),
        func.sum(_EXPR_VALOR_EFETIVO).label('total'),
    ).filter(
        and_(
            PessoalTransacao.data >= inicio,
            PessoalTransacao.data < proximo,
            *_filtro_entrada(),
        )
    ).group_by(PessoalTransacao.data, PessoalTransacao.categoria_id)


def _q_real_saidas_base(ano: int, mes: int):
    """Saidas realizadas normais (exclui pagamentos de cartao)."""
    inicio, proximo = _range_mes(ano, mes)
    return db.session.query(
        PessoalTransacao.data.label('data'),
        PessoalTransacao.categoria_id.label('categoria_id'),
        func.sum(_EXPR_VALOR_EFETIVO).label('total'),
    ).filter(
        and_(
            PessoalTransacao.data >= inicio,
            PessoalTransacao.data < proximo,
            PessoalTransacao.tipo == 'debito',
            PessoalTransacao.eh_pagamento_cartao.is_(False),
            *_filtros_caixa_base(),
        )
    ).group_by(PessoalTransacao.data, PessoalTransacao.categoria_id)


def _q_real_pagamentos_cartao(ano: int, mes: int):
    """Saidas = pagamentos de fatura. categoria_id = NULL (grupo virtual atribuido apos)."""
    inicio, proximo = _range_mes(ano, mes)
    return db.session.query(
        PessoalTransacao.data.label('data'),
        func.sum(PessoalTransacao.valor).label('total'),
    ).filter(
        and_(
            PessoalTransacao.data >= inicio,
            PessoalTransacao.data < proximo,
            PessoalTransacao.tipo == 'debito',
            PessoalTransacao.eh_pagamento_cartao.is_(True),
            *_filtros_cc_sem_transf(),
        )
    ).group_by(PessoalTransacao.data)


def _q_prov(ano: int, mes: int, tipo: str):
    """Provisoes PROVISIONADAS agrupadas por (data_prevista, categoria_id)."""
    inicio, proximo = _range_mes(ano, mes)
    return db.session.query(
        PessoalProvisao.data_prevista.label('data'),
        PessoalProvisao.categoria_id.label('categoria_id'),
        func.sum(PessoalProvisao.valor).label('total'),
    ).filter(
        and_(
            PessoalProvisao.data_prevista >= inicio,
            PessoalProvisao.data_prevista < proximo,
            PessoalProvisao.status == 'PROVISIONADA',
            PessoalProvisao.tipo == tipo,
        )
    ).group_by(PessoalProvisao.data_prevista, PessoalProvisao.categoria_id)


def _resolve_grupo_nome(cat_id: Optional[int], cat_map: dict) -> tuple[str, str]:
    if cat_id is None:
        return (GRUPO_SEM_CATEGORIA, NOME_SEM_CATEGORIA)
    return cat_map.get(cat_id, (GRUPO_SEM_CATEGORIA, NOME_SEM_CATEGORIA))


def _acumular(dst: dict, chave, incremento: dict):
    """Incrementa um dict de acumulador {chave: {entrada_real, entrada_prov, saida_real, saida_prov}}."""
    bucket = dst.setdefault(chave, {
        'entrada_real': 0.0, 'entrada_prov': 0.0,
        'saida_real': 0.0, 'saida_prov': 0.0,
    })
    for k, v in incremento.items():
        bucket[k] = (bucket.get(k, 0.0) or 0.0) + float(v or 0)


def _linha_final(bucket: dict) -> dict:
    """Converte bucket acumulado em linha retornada para UI."""
    ent_r = round(bucket.get('entrada_real', 0.0), 2)
    ent_p = round(bucket.get('entrada_prov', 0.0), 2)
    sai_r = round(bucket.get('saida_real', 0.0), 2)
    sai_p = round(bucket.get('saida_prov', 0.0), 2)
    return {
        'entrada_realizado': ent_r,
        'entrada_provisao': ent_p,
        'saida_realizado': sai_r,
        'saida_provisao': sai_p,
        'saldo_realizado': round(ent_r - sai_r, 2),
        'saldo_provisao': round(ent_p - sai_p, 2),
    }


def agrupado_por_dia(
    ano: int, mes: int,
    inc_real_e: bool = True, inc_real_s: bool = True,
    inc_prov_e: bool = True, inc_prov_s: bool = True,
) -> list[dict]:
    """Visao agrupada NIVEL 1: totais por dia."""
    cat_map = _categorias_map_mes(ano, mes)
    acc: dict[int, dict] = {}

    if inc_real_e:
        for row in _q_real_entradas(ano, mes).all():
            dia = row.data.day
            _acumular(acc, dia, {'entrada_real': row.total})

    if inc_real_s:
        for row in _q_real_saidas_base(ano, mes).all():
            dia = row.data.day
            _acumular(acc, dia, {'saida_real': row.total})
        # Pagamentos de cartao tambem sao saidas realizadas
        for row in _q_real_pagamentos_cartao(ano, mes).all():
            dia = row.data.day
            _acumular(acc, dia, {'saida_real': row.total})

    if inc_prov_e:
        for row in _q_prov(ano, mes, 'entrada').all():
            dia = row.data.day
            _acumular(acc, dia, {'entrada_prov': row.total})

    if inc_prov_s:
        for row in _q_prov(ano, mes, 'saida').all():
            dia = row.data.day
            _acumular(acc, dia, {'saida_prov': row.total})

    linhas = []
    for dia in sorted(acc.keys()):
        linha = _linha_final(acc[dia])
        linha['dia'] = dia
        try:
            linha['data_br'] = date(ano, mes, dia).strftime('%d/%m/%Y')
        except ValueError:
            linha['data_br'] = f'{dia:02d}/{mes:02d}/{ano}'
        linha['tem_filhos'] = True
        linhas.append(linha)
    return linhas


def agrupado_por_grupo(
    ano: int, mes: int, dia: int,
    inc_real_e: bool = True, inc_real_s: bool = True,
    inc_prov_e: bool = True, inc_prov_s: bool = True,
) -> list[dict]:
    """Visao agrupada NIVEL 2: grupos do dia."""
    cat_map = _categorias_map_mes(ano, mes)
    data_alvo = date(ano, mes, dia)
    acc: dict[str, dict] = {}

    def _filtro_dia(q):
        return q.filter(PessoalTransacao.data == data_alvo)

    def _filtro_dia_prov(q):
        return q.filter(PessoalProvisao.data_prevista == data_alvo)

    if inc_real_e:
        for row in _filtro_dia(_q_real_entradas(ano, mes)).all():
            grupo, _ = _resolve_grupo_nome(row.categoria_id, cat_map)
            _acumular(acc, grupo, {'entrada_real': row.total})

    if inc_real_s:
        for row in _filtro_dia(_q_real_saidas_base(ano, mes)).all():
            grupo, _ = _resolve_grupo_nome(row.categoria_id, cat_map)
            _acumular(acc, grupo, {'saida_real': row.total})
        for row in _q_real_pagamentos_cartao(ano, mes).filter(
            PessoalTransacao.data == data_alvo,
        ).all():
            _acumular(acc, GRUPO_CARTAO, {'saida_real': row.total})

    if inc_prov_e:
        for row in _filtro_dia_prov(_q_prov(ano, mes, 'entrada')).all():
            grupo, _ = _resolve_grupo_nome(row.categoria_id, cat_map)
            _acumular(acc, grupo, {'entrada_prov': row.total})

    if inc_prov_s:
        for row in _filtro_dia_prov(_q_prov(ano, mes, 'saida')).all():
            grupo, _ = _resolve_grupo_nome(row.categoria_id, cat_map)
            _acumular(acc, grupo, {'saida_prov': row.total})

    linhas = []
    for grupo in sorted(acc.keys()):
        linha = _linha_final(acc[grupo])
        linha['dia'] = dia
        linha['grupo'] = grupo
        linha['tem_filhos'] = True
        linhas.append(linha)
    return linhas


def agrupado_por_nome(
    ano: int, mes: int, dia: int, grupo: str,
    inc_real_e: bool = True, inc_real_s: bool = True,
    inc_prov_e: bool = True, inc_prov_s: bool = True,
) -> list[dict]:
    """Visao agrupada NIVEL 3: nomes dentro de (dia, grupo)."""
    cat_map = _categorias_map_mes(ano, mes)
    data_alvo = date(ano, mes, dia)
    acc: dict[str, dict] = {}

    # Categorias filtradas pelo grupo alvo (id -> nome)
    cat_ids_do_grupo = {
        cid: nome for cid, (g, nome) in cat_map.items() if g == grupo
    }

    def _filtro_dia(q):
        return q.filter(PessoalTransacao.data == data_alvo)

    def _filtro_dia_prov(q):
        return q.filter(PessoalProvisao.data_prevista == data_alvo)

    def _nome_para(cat_id):
        if grupo == GRUPO_SEM_CATEGORIA and cat_id is None:
            return NOME_SEM_CATEGORIA
        return cat_ids_do_grupo.get(cat_id)

    if inc_real_e:
        for row in _filtro_dia(_q_real_entradas(ano, mes)).all():
            nome = _nome_para(row.categoria_id)
            if nome is None:
                continue
            _acumular(acc, nome, {'entrada_real': row.total})

    if inc_real_s:
        for row in _filtro_dia(_q_real_saidas_base(ano, mes)).all():
            nome = _nome_para(row.categoria_id)
            if nome is None:
                continue
            _acumular(acc, nome, {'saida_real': row.total})
        # Pagamentos de cartao so entram se grupo == GRUPO_CARTAO
        if grupo == GRUPO_CARTAO:
            for row in _q_real_pagamentos_cartao(ano, mes).filter(
                PessoalTransacao.data == data_alvo,
            ).all():
                _acumular(acc, NOME_CARTAO, {'saida_real': row.total})

    if inc_prov_e:
        for row in _filtro_dia_prov(_q_prov(ano, mes, 'entrada')).all():
            nome = _nome_para(row.categoria_id)
            if nome is None:
                continue
            _acumular(acc, nome, {'entrada_prov': row.total})

    if inc_prov_s:
        for row in _filtro_dia_prov(_q_prov(ano, mes, 'saida')).all():
            nome = _nome_para(row.categoria_id)
            if nome is None:
                continue
            _acumular(acc, nome, {'saida_prov': row.total})

    linhas = []
    for nome in sorted(acc.keys()):
        linha = _linha_final(acc[nome])
        linha['dia'] = dia
        linha['grupo'] = grupo
        linha['nome'] = nome
        linha['tem_filhos'] = True
        linhas.append(linha)
    return linhas


def agrupado_linhas(
    ano: int, mes: int, dia: int, grupo: str, nome: str,
    inc_real_e: bool = True, inc_real_s: bool = True,
    inc_prov_e: bool = True, inc_prov_s: bool = True,
) -> list[dict]:
    """Visao agrupada NIVEL 4: linhas individuais (transacoes + provisoes)."""
    cat_map = _categorias_map_mes(ano, mes)
    data_alvo = date(ano, mes, dia)

    # Conjunto de categoria_ids que casam (grupo, nome)
    cat_ids_alvo = [
        cid for cid, (g, n) in cat_map.items() if g == grupo and n == nome
    ]
    eh_cartao = (grupo == GRUPO_CARTAO and nome == NOME_CARTAO)
    eh_sem_cat = (grupo == GRUPO_SEM_CATEGORIA and nome == NOME_SEM_CATEGORIA)

    linhas = []

    # --- REALIZADAS: transacoes do dia (entrada e saida base) ---
    if inc_real_e or inc_real_s:
        q_tx = PessoalTransacao.query.filter(
            PessoalTransacao.data == data_alvo,
            *_filtros_cc_sem_transf(),
        )
        if eh_cartao:
            # Apenas pagamentos de cartao
            q_tx = q_tx.filter(
                PessoalTransacao.tipo == 'debito',
                PessoalTransacao.eh_pagamento_cartao.is_(True),
            )
        else:
            # Base: nao pagamento cartao + excluir_relatorio=False
            q_tx = q_tx.filter(
                PessoalTransacao.eh_pagamento_cartao.is_(False),
                PessoalTransacao.excluir_relatorio.is_(False),
            )
            if eh_sem_cat:
                q_tx = q_tx.filter(PessoalTransacao.categoria_id.is_(None))
            elif cat_ids_alvo:
                q_tx = q_tx.filter(PessoalTransacao.categoria_id.in_(cat_ids_alvo))
            else:
                # Nao ha categoria com este (grupo, nome): nao retorna realizadas comuns
                q_tx = q_tx.filter(False)

        for t in q_tx.order_by(PessoalTransacao.id).all():
            if t.tipo == 'credito' and not inc_real_e:
                continue
            if t.tipo == 'debito' and not inc_real_s:
                continue
            valor = float(t.valor or 0) - float(t.valor_compensado or 0)
            if valor < 0:
                valor = 0
            linhas.append({
                'tipo': 'realizada',
                'id': t.id,
                'data_iso': t.data.isoformat() if t.data else None,
                'data_br': t.data.strftime('%d/%m/%Y') if t.data else None,
                'historico': t.historico,
                'descricao': t.descricao,
                'conta_nome': t.conta.nome if t.conta else None,
                'valor': round(valor, 2),
                'fluxo': 'entrada' if t.tipo == 'credito' else 'saida',
                'eh_pagamento_cartao': t.eh_pagamento_cartao,
            })

    # --- PROVISOES do dia ---
    if inc_prov_e or inc_prov_s:
        q_prov = PessoalProvisao.query.filter(
            PessoalProvisao.data_prevista == data_alvo,
            PessoalProvisao.status == 'PROVISIONADA',
        )
        if eh_cartao:
            # Provisoes nao tem categoria virtual "Financeiro/Cartao"
            q_prov = q_prov.filter(False)
        elif eh_sem_cat:
            q_prov = q_prov.filter(PessoalProvisao.categoria_id.is_(None))
        elif cat_ids_alvo:
            q_prov = q_prov.filter(PessoalProvisao.categoria_id.in_(cat_ids_alvo))
        else:
            q_prov = q_prov.filter(False)

        for p in q_prov.order_by(PessoalProvisao.id).all():
            if p.tipo == 'entrada' and not inc_prov_e:
                continue
            if p.tipo == 'saida' and not inc_prov_s:
                continue
            linhas.append({
                'tipo': 'provisao',
                'id': p.id,
                'data_iso': p.data_prevista.isoformat() if p.data_prevista else None,
                'data_br': p.data_prevista.strftime('%d/%m/%Y') if p.data_prevista else None,
                'historico': p.descricao,
                'descricao': p.observacao,
                'conta_nome': p.conta.nome if p.conta else None,
                'valor': float(p.valor or 0),
                'fluxo': p.tipo,
                'eh_pagamento_cartao': False,
            })

    # Ordenar: realizadas primeiro, depois provisoes
    linhas.sort(key=lambda l: (l['tipo'] != 'realizada', l['id']))
    return linhas

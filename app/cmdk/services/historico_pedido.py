"""
Service que monta o historico de alteracoes de um pedido para a aba
"Historico" da tela rica (/cmdk/pedido/<num_pedido>).

Le da tabela `evento_supply_chain` (event sourcing append-only, populada
por trigger PostgreSQL `audit_supply_chain_trigger()` — ver
app/supply_chain/models.py).

Retorno agrega eventos brutos em "momentos" (mesma entidade + tipo_evento
+ origem + registrado_por dentro de 1 minuto) para evitar poluir a UI
quando o trigger gera 1 evento por produto/linha.
"""
from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy import text

from app import db


logger = logging.getLogger(__name__)


# Lista de campos exibidos no diff antes/depois. Cobre os principais
# campos de carteira/separacao/faturamento/movimentacao. Campos ausentes
# em dados_antes/dados_depois retornam null silenciosamente.
CAMPOS_DIFF = (
    'status_pedido',
    'status',
    'expedicao',
    'agendamento',
    'protocolo',
    'data_embarque',
    'data_entrega_pedido',
    'data_atual_pedido',
    'numero_nf',
    'sincronizado_nf',
    'cotacao_id',
    'observ_ped_1',
    'qtd_saldo_produto_pedido',
    'qtd_produto_pedido',
    'preco_produto_pedido',
)


def montar_historico(num_pedido: str) -> Optional[dict]:
    """
    Retorna dict com sumario + momentos cronologicos.

    Estrutura:
        {
            'num_pedido': str,
            'sumario': {
                'total_eventos': int,
                'primeiro_evento': iso datetime,
                'ultimo_evento': iso datetime,
                'entidades': [str, ...],
                'produtos': [str, ...],
                'notas_fiscais': [str, ...],
                'lotes_separacao': [str, ...],
                'usuarios_distintos': int,
            },
            'momentos': [
                {
                    'quando_iso': iso datetime (Brasilia naive — sem sufixo Z),
                    'quando_label': 'DD/MM HH:MM' (Brasilia),
                    'entidade': 'carteira' | 'separacao' | ...,
                    'tipo_evento': 'INSERT' | 'UPDATE' | 'DELETE',
                    'origem': 'SYNC_ODOO' | 'USUARIO' | 'SISTEMA' | 'UPLOAD_EXCEL',
                    'registrado_por': str,
                    'qtd_produtos': int,
                    'campos_alterados': [str, ...] | None,
                    'mudancas': {
                        '<campo>': {'de': any, 'para': any}
                    },
                    'cod_produto_amostra': str | None,
                }, ...
            ]
        }

    Retorna None se nao houver eventos para o pedido.
    """
    num_pedido = (num_pedido or '').strip()
    if not num_pedido:
        return None

    sumario = _carregar_sumario(num_pedido)
    if not sumario or sumario['total_eventos'] == 0:
        return None

    momentos = _carregar_momentos(num_pedido)

    return {
        'num_pedido': num_pedido,
        'sumario': sumario,
        'momentos': momentos,
    }


def _carregar_sumario(num_pedido: str) -> dict:
    """Sumario agregado em uma unica query."""
    sql = text("""
        SELECT
            COUNT(*) AS total_eventos,
            MIN(registrado_em) AS primeiro_evento,
            MAX(registrado_em) AS ultimo_evento,
            COUNT(DISTINCT registrado_por) FILTER (
                WHERE registrado_por IS NOT NULL
            ) AS usuarios_distintos,
            ARRAY_AGG(DISTINCT entidade ORDER BY entidade) AS entidades,
            ARRAY_AGG(DISTINCT cod_produto ORDER BY cod_produto)
                FILTER (WHERE cod_produto IS NOT NULL) AS produtos,
            ARRAY_AGG(DISTINCT numero_nf)
                FILTER (WHERE numero_nf IS NOT NULL) AS notas_fiscais,
            ARRAY_AGG(DISTINCT separacao_lote_id)
                FILTER (WHERE separacao_lote_id IS NOT NULL) AS lotes_separacao
        FROM evento_supply_chain
        WHERE num_pedido = :num_pedido
    """)
    row = db.session.execute(sql, {'num_pedido': num_pedido}).mappings().first()
    if not row or not row['total_eventos']:
        return {}

    return {
        'total_eventos': int(row['total_eventos']),
        'primeiro_evento': row['primeiro_evento'].isoformat() if row['primeiro_evento'] else None,
        'ultimo_evento': row['ultimo_evento'].isoformat() if row['ultimo_evento'] else None,
        'usuarios_distintos': int(row['usuarios_distintos'] or 0),
        'entidades': list(row['entidades'] or []),
        'produtos': list(row['produtos'] or []),
        'notas_fiscais': list(row['notas_fiscais'] or []),
        'lotes_separacao': list(row['lotes_separacao'] or []),
    }


def _carregar_momentos(num_pedido: str) -> list[dict]:
    """
    Agrega eventos por (entidade, tipo, origem, usuario, minuto).

    Para cada grupo retorna 1 momento representativo, com diff dos campos
    mais relevantes (CAMPOS_DIFF) extraidos de UM evento do grupo (DISTINCT ON).
    """
    sql = text("""
        WITH eventos_representativos AS (
            SELECT DISTINCT ON (
                entidade, tipo_evento, origem, registrado_por,
                DATE_TRUNC('minute', registrado_em)
            )
                id,
                registrado_em,
                entidade,
                tipo_evento,
                origem,
                registrado_por,
                campos_alterados,
                cod_produto,
                dados_antes,
                dados_depois
            FROM evento_supply_chain
            WHERE num_pedido = :num_pedido
            ORDER BY
                entidade, tipo_evento, origem, registrado_por,
                DATE_TRUNC('minute', registrado_em),
                id
        ),
        grupos AS (
            SELECT
                entidade, tipo_evento, origem, registrado_por,
                DATE_TRUNC('minute', registrado_em) AS bucket,
                -- Conta LINHAS distintas afetadas (entidade_id e PK da origem).
                -- Cada produto/linha tem 1 entidade_id; varios eventos no mesmo
                -- minuto contra a mesma linha contam como 1.
                COUNT(DISTINCT entidade_id) AS qtd_produtos,
                ARRAY_AGG(DISTINCT unnested_campo)
                    FILTER (WHERE unnested_campo IS NOT NULL) AS campos_alterados_uniao
            FROM evento_supply_chain
            LEFT JOIN LATERAL UNNEST(COALESCE(campos_alterados, ARRAY[]::text[])) AS unnested_campo ON true
            WHERE num_pedido = :num_pedido
            GROUP BY entidade, tipo_evento, origem, registrado_por, bucket
        )
        SELECT
            g.bucket AS quando,
            e.registrado_em AS registrado_em,
            g.entidade,
            g.tipo_evento,
            g.origem,
            g.registrado_por,
            g.qtd_produtos,
            g.campos_alterados_uniao,
            e.cod_produto,
            e.dados_antes,
            e.dados_depois
        FROM grupos g
        JOIN eventos_representativos e
          ON e.entidade        = g.entidade
         AND e.tipo_evento     = g.tipo_evento
         AND e.origem          IS NOT DISTINCT FROM g.origem
         AND e.registrado_por  IS NOT DISTINCT FROM g.registrado_por
         AND DATE_TRUNC('minute', e.registrado_em) = g.bucket
        ORDER BY g.bucket, g.entidade, g.tipo_evento;
    """)

    rows = db.session.execute(sql, {'num_pedido': num_pedido}).mappings().all()

    momentos = []
    for r in rows:
        mudancas = _extrair_mudancas(
            campos_alterados=r['campos_alterados_uniao'],
            dados_antes=r['dados_antes'],
            dados_depois=r['dados_depois'],
            tipo_evento=r['tipo_evento'],
        )

        momentos.append({
            'quando_iso': r['registrado_em'].isoformat() if r['registrado_em'] else None,
            'quando_label': _format_brasilia(r['registrado_em']),
            'entidade': r['entidade'],
            'tipo_evento': r['tipo_evento'],
            'origem': r['origem'],
            'registrado_por': r['registrado_por'] or '—',
            'qtd_produtos': int(r['qtd_produtos'] or 0),
            'campos_alterados': list(r['campos_alterados_uniao']) if r['campos_alterados_uniao'] else None,
            'mudancas': mudancas,
            'cod_produto_amostra': r['cod_produto'],
        })

    return momentos


def _extrair_mudancas(campos_alterados, dados_antes, dados_depois, tipo_evento):
    """
    Extrai diff de campos relevantes.

    Para UPDATE: so campos que estao em campos_alterados.
    Para INSERT: campos de CAMPOS_DIFF que tem valor em dados_depois.
    Para DELETE: campos de CAMPOS_DIFF que tem valor em dados_antes.
    """
    dados_antes = dados_antes or {}
    dados_depois = dados_depois or {}

    if tipo_evento == 'UPDATE':
        campos_para_diff = set(campos_alterados or [])
        # Restringe ao CAMPOS_DIFF (campos sem valor de exibicao definido sao omitidos)
        campos_para_diff = campos_para_diff & set(CAMPOS_DIFF)
    else:
        # INSERT / DELETE: lista os campos relevantes que tem valor
        campos_para_diff = set()
        for campo in CAMPOS_DIFF:
            if tipo_evento == 'INSERT' and dados_depois.get(campo) not in (None, '', False):
                campos_para_diff.add(campo)
            elif tipo_evento == 'DELETE' and dados_antes.get(campo) not in (None, '', False):
                campos_para_diff.add(campo)

    mudancas = {}
    for campo in sorted(campos_para_diff):
        de = dados_antes.get(campo)
        para = dados_depois.get(campo)
        # Trunca strings longas pra payload nao crescer
        if isinstance(de, str) and len(de) > 200:
            de = de[:200] + '...'
        if isinstance(para, str) and len(para) > 200:
            para = para[:200] + '...'
        mudancas[campo] = {'de': de, 'para': para}

    return mudancas


def _format_brasilia(dt):
    """
    Formata timestamp para 'DD/MM HH:MM'.

    NOTA: `evento_supply_chain.registrado_em` e gravado pelo trigger PG
    com DEFAULT now(), mas o valor final fica em Brasilia naive (mesmo
    instante de Separacao.criado_em via Python agora_utc_naive()).
    Validado empiricamente em 2026-05-14 com evento_id=131646.
    """
    if not dt:
        return '—'
    return dt.strftime('%d/%m %H:%M')

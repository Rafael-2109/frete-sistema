#!/usr/bin/env python3
"""
Script para consultar fretes REAIS (pos-faturamento).

Diferente de consultar_pedido_frete.py (que consulta dados PRE-cotacao),
este script consulta fretes JA CONTRATADOS com valores reais pagos.

Uso:
    python consultando_frete_real.py --pedido VCD123
    python consultando_frete_real.py --cliente "Atacadao" --de 2026-01-01 --ate 2026-01-31
    python consultando_frete_real.py --transportadora "Braspress"
    python consultando_frete_real.py --divergencias
    python consultando_frete_real.py --pendentes-odoo
    python consultando_frete_real.py --cliente "Atacadao" --com-despesas
"""

import argparse
import json
import sys
import os
from datetime import date, datetime
from decimal import Decimal

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))


class DecimalEncoder(json.JSONEncoder):
    """Encoder para serializar Decimal e date/datetime."""
    def default(self, o):  # noqa: N802
        if isinstance(o, Decimal):
            return float(o)
        if isinstance(o, (date, datetime)):
            return o.isoformat()
        return super().default(o)


def consultando_frete_real(
    pedido: str = None,
    cliente: str = None,
    transportadora: str = None,
    de: str = None,
    ate: str = None,
    divergencias: bool = False,
    pendentes_odoo: bool = False,
    com_despesas: bool = False,
    limite: int = 50
) -> dict:
    """
    Consulta fretes reais (contratados/pagos) no sistema.

    Args:
        pedido: Numero do pedido (traversal via embarque chain)
        cliente: Nome do cliente (entity resolution por prefixo CNPJ)
        transportadora: Nome da transportadora
        de: Data inicio (YYYY-MM-DD)
        ate: Data fim (YYYY-MM-DD)
        divergencias: Listar divergencias CTe vs cotacao > R$ 5
        pendentes_odoo: Fretes aprovados nao lancados no Odoo
        com_despesas: Incluir breakdown de DespesaExtra por tipo
        limite: Max registros (default 50)

    Returns:
        dict: {sucesso, modo, fretes/resumo, total}
    """
    from app import create_app

    resultado = {
        'sucesso': False,
        'modo': None,
        'total': 0
    }

    app = create_app()
    with app.app_context():
        try:
            if pedido:
                resultado['modo'] = 'frete_por_pedido'
                resultado = _frete_por_pedido(pedido, com_despesas, resultado)

            elif divergencias:
                resultado['modo'] = 'divergencias'
                resultado = _divergencias_cte(de, ate, limite, resultado)

            elif pendentes_odoo:
                resultado['modo'] = 'pendentes_odoo'
                resultado = _pendentes_odoo(limite, resultado)

            elif cliente:
                resultado['modo'] = 'frete_por_cliente'
                resultado = _frete_por_cliente(
                    cliente, de, ate, com_despesas, limite, resultado
                )

            elif transportadora:
                resultado['modo'] = 'frete_por_transportadora'
                resultado = _frete_por_transportadora(
                    transportadora, de, ate, limite, resultado
                )

            else:
                resultado['erro'] = (
                    'Informe --pedido, --cliente, --transportadora, '
                    '--divergencias ou --pendentes-odoo'
                )

            return resultado

        except Exception as e:
            resultado['erro'] = str(e)
            import traceback
            resultado['traceback'] = traceback.format_exc()
            return resultado


def _frete_por_pedido(pedido: str, com_despesas: bool, resultado: dict) -> dict:
    """
    Frete real de um pedido via embarque chain:
    Separacao -> EmbarqueItem -> Embarque -> Frete -> Transportadora
    """
    from app import db
    from sqlalchemy import text

    sql = text("""
        SELECT DISTINCT
            f.id AS frete_id,
            e.numero AS embarque_numero,
            e.data_embarque,
            t.razao_social AS transportadora,
            f.tipo_carga,
            f.peso_total,
            f.valor_total_nfs,
            f.valor_cotado,
            f.valor_cte,
            f.valor_considerado,
            f.valor_pago,
            f.numero_cte,
            f.status,
            f.lancado_odoo_em
        FROM fretes f
        JOIN embarques e ON e.id = f.embarque_id
        JOIN embarque_itens ei ON ei.embarque_id = e.id
        JOIN separacao s ON s.separacao_lote_id = ei.separacao_lote_id
        JOIN transportadoras t ON t.id = f.transportadora_id
        WHERE s.num_pedido = :pedido
        ORDER BY e.data_embarque DESC
    """)

    rows = db.session.execute(sql, {'pedido': pedido.upper()}).fetchall()

    if not rows:
        resultado['sucesso'] = True
        resultado['fretes'] = []
        resultado['aviso'] = (
            f'Nenhum frete encontrado para pedido {pedido}. '
            'O pedido pode nao ter sido embarcado ainda.'
        )
        return resultado

    fretes = []
    total_pago = Decimal('0')
    total_despesas = Decimal('0')

    for row in rows:
        frete = {
            'frete_id': row.frete_id,
            'embarque_numero': row.embarque_numero,
            'data_embarque': row.data_embarque,
            'transportadora': row.transportadora,
            'tipo_carga': row.tipo_carga,
            'peso_total': row.peso_total,
            'valor_nfs': row.valor_total_nfs,
            'valor_cotado': row.valor_cotado,
            'valor_cte': row.valor_cte,
            'valor_considerado': row.valor_considerado,
            'valor_pago': row.valor_pago,
            'numero_cte': row.numero_cte,
            'status': row.status,
            'lancado_odoo': row.lancado_odoo_em is not None,
        }

        if row.valor_pago:
            total_pago += Decimal(str(row.valor_pago))

        if row.valor_cte and row.valor_cotado:
            frete['divergencia'] = round(
                abs(float(row.valor_cte) - float(row.valor_cotado)), 2
            )

        if com_despesas:
            despesas = _buscar_despesas_frete(row.frete_id)
            frete['despesas'] = despesas
            for d in despesas:
                total_despesas += Decimal(str(d['valor_despesa']))

        fretes.append(frete)

    resultado['sucesso'] = True
    resultado['pedido'] = pedido.upper()
    resultado['fretes'] = fretes
    resultado['total'] = len(fretes)
    resultado['resumo'] = {
        'total_pago': float(total_pago),
        'total_despesas': float(total_despesas),
        'custo_total': float(total_pago + total_despesas),
        'qtd_fretes': len(fretes),
    }

    return resultado


def _frete_por_cliente(
    cliente: str, de: str, ate: str,
    com_despesas: bool, limite: int, resultado: dict
) -> dict:
    """
    Total de frete real por cliente/grupo, usando match por prefixo CNPJ.
    Primeiro tenta resolver o cliente via entity resolution (LIKE no nome).
    """
    from app import db
    from sqlalchemy import text

    # Resolver cliente: buscar CNPJs que contenham o nome
    sql_clientes = text("""
        SELECT DISTINCT cnpj_cliente, nome_cliente
        FROM fretes
        WHERE UPPER(nome_cliente) LIKE :termo
        LIMIT 20
    """)

    clientes = db.session.execute(
        sql_clientes, {'termo': f'%{cliente.upper()}%'}
    ).fetchall()

    if not clientes:
        resultado['sucesso'] = True
        resultado['fretes'] = []
        resultado['aviso'] = f'Nenhum cliente encontrado com nome "{cliente}"'
        return resultado

    # Extrair prefixos CNPJ (raiz do grupo = 8 primeiros digitos)
    prefixos = set()
    cnpjs_encontrados = []
    for c in clientes:
        cnpj_limpo = ''.join(d for d in (c.cnpj_cliente or '') if d.isdigit())
        if len(cnpj_limpo) >= 8:
            prefixos.add(cnpj_limpo[:8])
        cnpjs_encontrados.append({
            'cnpj': c.cnpj_cliente,
            'nome': c.nome_cliente
        })

    # Consultar fretes por prefixo CNPJ (grupo empresarial)
    conditions = []
    params = {}

    for i, pref in enumerate(prefixos):
        conditions.append(f"REPLACE(REPLACE(f.cnpj_cliente, '.', ''), '-', '') LIKE :pref{i}")
        params[f'pref{i}'] = f'{pref}%'

    where_cnpj = ' OR '.join(conditions)

    where_periodo = ''
    if de:
        where_periodo += ' AND f.criado_em >= :de'
        params['de'] = de
    if ate:
        where_periodo += ' AND f.criado_em <= :ate'
        params['ate'] = ate

    sql = text(f"""
        SELECT
            t.razao_social AS transportadora,
            f.tipo_carga,
            COUNT(*) AS qtd_fretes,
            SUM(f.valor_pago) AS total_pago,
            SUM(f.valor_cotado) AS total_cotado,
            AVG(f.valor_pago) AS media_frete,
            SUM(f.peso_total) AS peso_total
        FROM fretes f
        JOIN transportadoras t ON t.id = f.transportadora_id
        WHERE ({where_cnpj})
          AND f.valor_pago IS NOT NULL
          {where_periodo}
        GROUP BY t.razao_social, f.tipo_carga
        ORDER BY total_pago DESC
        LIMIT :limite
    """)
    params['limite'] = limite

    rows = db.session.execute(sql, params).fetchall()

    resumo_transportadoras = []
    grand_total = Decimal('0')
    grand_peso = Decimal('0')
    grand_qtd = 0

    for row in rows:
        resumo_transportadoras.append({
            'transportadora': row.transportadora,
            'tipo_carga': row.tipo_carga,
            'qtd_fretes': row.qtd_fretes,
            'total_pago': float(row.total_pago) if row.total_pago else 0,
            'total_cotado': float(row.total_cotado) if row.total_cotado else 0,
            'media_frete': round(float(row.media_frete), 2) if row.media_frete else 0,
            'peso_total': float(row.peso_total) if row.peso_total else 0,
        })
        if row.total_pago:
            grand_total += Decimal(str(row.total_pago))
        if row.peso_total:
            grand_peso += Decimal(str(row.peso_total))
        grand_qtd += row.qtd_fretes

    # Despesas totais se solicitado
    total_despesas = Decimal('0')
    despesas_por_tipo = []
    if com_despesas and prefixos:
        sql_desp = text(f"""
            SELECT de.tipo_despesa, COUNT(*) AS qtd,
                   SUM(de.valor_despesa) AS total
            FROM despesas_extras de
            JOIN fretes f ON f.id = de.frete_id
            WHERE ({where_cnpj})
              {where_periodo}
            GROUP BY de.tipo_despesa
            ORDER BY total DESC
        """)
        # Reutilizar params (ja tem pref0..N, de, ate)
        desp_rows = db.session.execute(sql_desp, params).fetchall()
        for d in desp_rows:
            despesas_por_tipo.append({
                'tipo': d.tipo_despesa,
                'qtd': d.qtd,
                'total': float(d.total) if d.total else 0
            })
            if d.total:
                total_despesas += Decimal(str(d.total))

    resultado['sucesso'] = True
    resultado['cliente_termo'] = cliente
    resultado['cnpjs_encontrados'] = cnpjs_encontrados
    resultado['prefixos_grupo'] = list(prefixos)
    resultado['por_transportadora'] = resumo_transportadoras
    resultado['total'] = len(resumo_transportadoras)
    resultado['resumo'] = {
        'total_pago': float(grand_total),
        'total_despesas': float(total_despesas),
        'custo_total': float(grand_total + total_despesas),
        'qtd_fretes': grand_qtd,
        'peso_total': float(grand_peso),
        'frete_medio_kg': round(
            float(grand_total / grand_peso), 4
        ) if grand_peso > 0 else None,
    }
    if com_despesas:
        resultado['despesas_por_tipo'] = despesas_por_tipo
    if de:
        resultado['periodo_de'] = de
    if ate:
        resultado['periodo_ate'] = ate

    return resultado


def _frete_por_transportadora(
    transportadora: str, de: str, ate: str,
    limite: int, resultado: dict
) -> dict:
    """Fretes agrupados para uma transportadora especifica."""
    from app import db
    from sqlalchemy import text

    params = {'termo': f'%{transportadora.upper()}%', 'limite': limite}
    where_periodo = ''
    if de:
        where_periodo += ' AND f.criado_em >= :de'
        params['de'] = de
    if ate:
        where_periodo += ' AND f.criado_em <= :ate'
        params['ate'] = ate

    sql = text(f"""
        SELECT
            t.razao_social AS transportadora,
            f.uf_destino,
            f.tipo_carga,
            COUNT(*) AS qtd,
            SUM(f.valor_pago) AS total_pago,
            SUM(f.valor_cotado) AS total_cotado,
            SUM(f.peso_total) AS peso_total,
            AVG(f.valor_pago / NULLIF(f.peso_total, 0)) AS frete_medio_kg
        FROM fretes f
        JOIN transportadoras t ON t.id = f.transportadora_id
        WHERE UPPER(t.razao_social) LIKE :termo
          AND f.valor_pago IS NOT NULL
          {where_periodo}
        GROUP BY t.razao_social, f.uf_destino, f.tipo_carga
        ORDER BY total_pago DESC
        LIMIT :limite
    """)

    rows = db.session.execute(sql, params).fetchall()

    if not rows:
        resultado['sucesso'] = True
        resultado['fretes'] = []
        resultado['aviso'] = f'Nenhum frete encontrado para transportadora "{transportadora}"'
        return resultado

    por_uf = []
    grand_total = Decimal('0')
    grand_qtd = 0

    for row in rows:
        por_uf.append({
            'transportadora': row.transportadora,
            'uf_destino': row.uf_destino,
            'tipo_carga': row.tipo_carga,
            'qtd_fretes': row.qtd,
            'total_pago': float(row.total_pago) if row.total_pago else 0,
            'total_cotado': float(row.total_cotado) if row.total_cotado else 0,
            'peso_total': float(row.peso_total) if row.peso_total else 0,
            'frete_medio_kg': round(float(row.frete_medio_kg), 4) if row.frete_medio_kg else None,
        })
        if row.total_pago:
            grand_total += Decimal(str(row.total_pago))
        grand_qtd += row.qtd

    resultado['sucesso'] = True
    resultado['transportadora_termo'] = transportadora
    resultado['por_uf'] = por_uf
    resultado['total'] = len(por_uf)
    resultado['resumo'] = {
        'total_pago': float(grand_total),
        'qtd_fretes': grand_qtd,
    }

    return resultado


def _divergencias_cte(de: str, ate: str, limite: int, resultado: dict) -> dict:
    """Lista divergencias entre valor_cte e valor_cotado > R$ 5."""
    from app import db
    from sqlalchemy import text

    params = {'limite': limite}
    where_periodo = ''
    if de:
        where_periodo += ' AND f.criado_em >= :de'
        params['de'] = de
    if ate:
        where_periodo += ' AND f.criado_em <= :ate'
        params['ate'] = ate

    sql = text(f"""
        SELECT
            f.id AS frete_id,
            f.numero_cte,
            t.razao_social AS transportadora,
            f.cnpj_cliente,
            f.nome_cliente,
            f.uf_destino,
            f.valor_cotado,
            f.valor_cte,
            ABS(f.valor_cte - f.valor_cotado) AS diferenca,
            f.status,
            f.considerar_diferenca
        FROM fretes f
        JOIN transportadoras t ON t.id = f.transportadora_id
        WHERE f.valor_cte IS NOT NULL
          AND f.valor_cotado IS NOT NULL
          AND ABS(f.valor_cte - f.valor_cotado) > 5.00
          {where_periodo}
        ORDER BY diferenca DESC
        LIMIT :limite
    """)

    rows = db.session.execute(sql, params).fetchall()

    divergencias = []
    total_diferenca = Decimal('0')

    for row in rows:
        divergencias.append({
            'frete_id': row.frete_id,
            'numero_cte': row.numero_cte,
            'transportadora': row.transportadora,
            'cliente': row.nome_cliente,
            'uf_destino': row.uf_destino,
            'valor_cotado': float(row.valor_cotado),
            'valor_cte': float(row.valor_cte),
            'diferenca': float(row.diferenca),
            'status': row.status,
            'considerar_diferenca': row.considerar_diferenca,
        })
        total_diferenca += Decimal(str(row.diferenca))

    resultado['sucesso'] = True
    resultado['divergencias'] = divergencias
    resultado['total'] = len(divergencias)
    resultado['resumo'] = {
        'total_diferenca': float(total_diferenca),
        'media_diferenca': round(
            float(total_diferenca / len(divergencias)), 2
        ) if divergencias else 0,
    }

    return resultado


def _pendentes_odoo(limite: int, resultado: dict) -> dict:
    """Fretes aprovados nao lancados no Odoo."""
    from app import db
    from sqlalchemy import text

    sql = text("""
        SELECT
            f.id AS frete_id,
            f.numero_cte,
            f.valor_pago,
            f.valor_cte,
            t.razao_social AS transportadora,
            f.nome_cliente,
            f.uf_destino,
            f.status,
            f.criado_em,
            f.aprovado_em
        FROM fretes f
        JOIN transportadoras t ON t.id = f.transportadora_id
        WHERE f.status = 'APROVADO'
          AND f.lancado_odoo_em IS NULL
        ORDER BY f.criado_em
        LIMIT :limite
    """)

    rows = db.session.execute(sql, {'limite': limite}).fetchall()

    pendentes = []
    total_valor = Decimal('0')

    for row in rows:
        pendentes.append({
            'frete_id': row.frete_id,
            'numero_cte': row.numero_cte,
            'valor_pago': float(row.valor_pago) if row.valor_pago else None,
            'valor_cte': float(row.valor_cte) if row.valor_cte else None,
            'transportadora': row.transportadora,
            'cliente': row.nome_cliente,
            'uf_destino': row.uf_destino,
            'status': row.status,
            'criado_em': row.criado_em,
            'aprovado_em': row.aprovado_em,
        })
        if row.valor_pago:
            total_valor += Decimal(str(row.valor_pago))

    resultado['sucesso'] = True
    resultado['pendentes'] = pendentes
    resultado['total'] = len(pendentes)
    resultado['resumo'] = {
        'total_valor_pendente': float(total_valor),
    }

    return resultado


def _buscar_despesas_frete(frete_id: int) -> list:
    """Busca despesas extras de um frete especifico."""
    from app import db
    from sqlalchemy import text

    sql = text("""
        SELECT tipo_despesa, valor_despesa, motivo_despesa,
               setor_responsavel, status, numero_documento
        FROM despesas_extras
        WHERE frete_id = :frete_id
        ORDER BY valor_despesa DESC
    """)

    rows = db.session.execute(sql, {'frete_id': frete_id}).fetchall()

    return [
        {
            'tipo_despesa': row.tipo_despesa,
            'valor_despesa': float(row.valor_despesa),
            'motivo': row.motivo_despesa,
            'setor': row.setor_responsavel,
            'status': row.status,
            'documento': row.numero_documento,
        }
        for row in rows
    ]


def main():
    parser = argparse.ArgumentParser(
        description='Consultar fretes reais (pos-faturamento)'
    )
    parser.add_argument('--pedido', help='Numero do pedido (via embarque chain)')
    parser.add_argument('--cliente', help='Nome do cliente (match parcial)')
    parser.add_argument('--transportadora', help='Nome da transportadora')
    parser.add_argument('--de', help='Data inicio (YYYY-MM-DD)')
    parser.add_argument('--ate', help='Data fim (YYYY-MM-DD)')
    parser.add_argument('--divergencias', action='store_true',
                        help='Listar divergencias CTe vs cotacao > R$ 5')
    parser.add_argument('--pendentes-odoo', action='store_true',
                        help='Fretes aprovados nao lancados no Odoo')
    parser.add_argument('--com-despesas', action='store_true',
                        help='Incluir breakdown de despesas extras')
    parser.add_argument('--limite', type=int, default=50,
                        help='Max registros (default: 50)')

    args = parser.parse_args()

    resultado = consultando_frete_real(
        pedido=args.pedido,
        cliente=args.cliente,
        transportadora=args.transportadora,
        de=args.de,
        ate=args.ate,
        divergencias=args.divergencias,
        pendentes_odoo=args.pendentes_odoo,
        com_despesas=args.com_despesas,
        limite=args.limite,
    )

    print(json.dumps(resultado, ensure_ascii=False, indent=2, cls=DecimalEncoder))


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
Script: acompanhando_pedido.py

Retorna status de pedidos HORA -> Motochefe (pedido -> NF -> recebimento).

Uso:
    --loja-ids 2,5              # escopo (None = admin)
    --numero-pedido 001         # filtro opcional por numero_pedido
    --somente-abertos           # so pedidos que nao estao conferidos
"""
import sys
import os
import json
import argparse
import time
from datetime import datetime, date
from decimal import Decimal

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))

from app import create_app, db  # noqa: E402
from sqlalchemy import text  # noqa: E402


def _json_default(obj):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    return str(obj)


def _parse_loja_ids(raw):
    if not raw:
        return None
    try:
        return [int(x.strip()) for x in raw.split(',') if x.strip()]
    except ValueError:
        return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--loja-ids', help='CSV de loja_hora_id (None=admin)')
    parser.add_argument('--numero-pedido', help='Filtro por numero_pedido (ILIKE)')
    parser.add_argument('--somente-abertos', action='store_true',
                        help='Oculta pedidos ja conferidos completamente')
    args = parser.parse_args()

    t_start = time.time()
    loja_ids = _parse_loja_ids(args.loja_ids)
    pode_ver_todas = loja_ids is None

    app = create_app()
    with app.app_context():
        result = _run(
            loja_ids=loja_ids,
            pode_ver_todas=pode_ver_todas,
            numero_pedido=args.numero_pedido,
            somente_abertos=args.somente_abertos,
        )

    result['_debug'] = {'query_ms': int((time.time() - t_start) * 1000)}
    print(json.dumps(result, default=_json_default, ensure_ascii=False, indent=2))


def _run(loja_ids, pode_ver_todas, numero_pedido, somente_abertos):
    # ==========================================================================
    # Lookup de lojas (apelido)
    # ==========================================================================
    lojas_rows = db.session.execute(text(
        "SELECT id, apelido FROM hora_loja ORDER BY id"
    )).fetchall()
    lojas_apelido = {r.id: r.apelido for r in lojas_rows}

    # ==========================================================================
    # Query: pedidos + agregados (contadores) em 1 shot
    # ==========================================================================
    sql = """
    WITH pedido_base AS (
      SELECT p.id, p.numero_pedido, p.cnpj_destino, p.loja_destino_id,
             p.data_pedido, p.status, p.apelido_detectado, p.observacoes,
             p.criado_em, p.criado_por,
             (SELECT COUNT(*) FROM hora_pedido_item WHERE pedido_id = p.id) AS itens_declarados
      FROM hora_pedido p
      WHERE 1=1
    """
    params = {}

    if not pode_ver_todas:
        sql += " AND p.loja_destino_id = ANY(:ids)"
        params['ids'] = loja_ids

    if numero_pedido:
        sql += " AND p.numero_pedido ILIKE :np"
        params['np'] = f"%{numero_pedido}%"

    sql += ")\nSELECT * FROM pedido_base ORDER BY data_pedido DESC NULLS LAST, id DESC"

    pedidos_rows = db.session.execute(text(sql), params).fetchall()

    pedidos_out = []

    for p in pedidos_rows:
        # NFs vinculadas a este pedido
        nfs_rows = db.session.execute(text(
            "SELECT nf.id, nf.numero_nf, nf.serie_nf, nf.chave_44, "
            "       nf.data_emissao, nf.valor_total, nf.nome_emitente, "
            "       nf.qtd_declarada_itens, "
            "       (SELECT COUNT(*) FROM hora_nf_entrada_item WHERE nf_id = nf.id) AS itens_nf "
            "FROM hora_nf_entrada nf "
            "WHERE nf.pedido_id = :pid "
            "ORDER BY nf.data_emissao DESC NULLS LAST"
        ), {"pid": p.id}).fetchall()

        nfs_list = []
        nf_ids = []
        total_itens_nf = 0
        for nf in nfs_rows:
            nfs_list.append({
                'id': nf.id,
                'numero_nf': nf.numero_nf,
                'serie_nf': nf.serie_nf,
                'chave_44': nf.chave_44,
                'data_emissao': nf.data_emissao,
                'valor_total': nf.valor_total,
                'nome_emitente': nf.nome_emitente,
                'itens_nf': nf.itens_nf,
                'qtd_declarada_itens': nf.qtd_declarada_itens,
            })
            nf_ids.append(nf.id)
            total_itens_nf += (nf.itens_nf or 0)

        # Recebimentos dessas NFs
        receb_list = []
        chassis_conferidos = 0
        divergencias = 0

        if nf_ids:
            receb_rows = db.session.execute(text(
                "SELECT r.id, r.status, r.data_recebimento, r.operador, "
                "       (SELECT COUNT(*) FROM hora_recebimento_conferencia "
                "          WHERE recebimento_id = r.id) AS total_conf, "
                "       (SELECT COUNT(*) FROM hora_recebimento_conferencia "
                "          WHERE recebimento_id = r.id "
                "          AND tipo_divergencia IS NOT NULL) AS total_divergencias "
                "FROM hora_recebimento r "
                "WHERE r.nf_id = ANY(:nfs) "
                "ORDER BY r.data_recebimento DESC NULLS LAST"
            ), {"nfs": nf_ids}).fetchall()

            for r in receb_rows:
                receb_list.append({
                    'id': r.id,
                    'status': r.status,
                    'data_recebimento': r.data_recebimento,
                    'operador': r.operador,
                    'conferidos': r.total_conf or 0,
                    'divergencias': r.total_divergencias or 0,
                })
                chassis_conferidos += (r.total_conf or 0)
                divergencias += (r.total_divergencias or 0)

        itens_declarados = p.itens_declarados or 0
        chassis_faltando = max(itens_declarados - chassis_conferidos, 0)

        # Status derivado
        if not nfs_list:
            status_derivado = 'aguardando NF'
        elif not receb_list:
            status_derivado = 'NF recebida (sem conferencia)'
        elif chassis_faltando > 0:
            status_derivado = 'em conferencia'
        elif divergencias > 0:
            status_derivado = 'conferido com divergencia'
        else:
            status_derivado = 'conferido ok'

        # Filtro somente_abertos
        if somente_abertos and status_derivado == 'conferido ok':
            continue

        pedidos_out.append({
            'id': p.id,
            'numero_pedido': p.numero_pedido,
            'cnpj_destino': p.cnpj_destino,
            'loja_destino_id': p.loja_destino_id,
            'loja_apelido': lojas_apelido.get(p.loja_destino_id),
            'apelido_detectado': p.apelido_detectado,
            'data_pedido': p.data_pedido,
            'status': p.status,
            'status_derivado': status_derivado,
            'criado_em': p.criado_em,
            'criado_por': p.criado_por,
            'itens_declarados': itens_declarados,
            'nfs': nfs_list,
            'itens_nf_total': total_itens_nf,
            'recebimentos': receb_list,
            'chassis_conferidos': chassis_conferidos,
            'chassis_faltando': chassis_faltando,
            'divergencias': divergencias,
        })

    return {
        'escopo_aplicado': {
            'loja_ids': loja_ids,
            'pode_ver_todas': pode_ver_todas,
            'numero_pedido': numero_pedido,
            'somente_abertos': somente_abertos,
        },
        'total_pedidos': len(pedidos_out),
        'pedidos': pedidos_out,
    }


if __name__ == '__main__':
    main()

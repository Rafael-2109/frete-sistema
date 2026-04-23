#!/usr/bin/env python3
"""
Script: consultando_pecas_faltando.py

Lista pecas faltando registradas na conferencia de recebimento HORA,
respeitando escopo de loja.

Uso:
    --loja-ids 2,5
    --chassi LA2025SA110003988      # filtro opcional
    --somente-abertos               # oculta status resolvido
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


def _normalize_status(s):
    if s is None:
        return 'outro'
    up = str(s).upper()
    if up in ('ABERTO', 'ABERTA', 'PENDENTE', 'PENDING', 'OPEN'):
        return 'aberto'
    if up in ('RESOLVIDO', 'RESOLVIDA', 'FINALIZADO', 'DONE', 'FECHADO', 'CLOSED'):
        return 'resolvido'
    return 'outro'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--loja-ids')
    parser.add_argument('--chassi')
    parser.add_argument('--somente-abertos', action='store_true')
    args = parser.parse_args()

    t_start = time.time()
    loja_ids = _parse_loja_ids(args.loja_ids)
    pode_ver_todas = loja_ids is None

    app = create_app()
    with app.app_context():
        result = _run(
            loja_ids=loja_ids,
            pode_ver_todas=pode_ver_todas,
            chassi=args.chassi,
            somente_abertos=args.somente_abertos,
        )

    result['_debug'] = {'query_ms': int((time.time() - t_start) * 1000)}
    print(json.dumps(result, default=_json_default, ensure_ascii=False, indent=2))


def _run(loja_ids, pode_ver_todas, chassi, somente_abertos):
    lojas_map = {
        r.id: r.apelido for r in
        db.session.execute(text("SELECT id, apelido FROM hora_loja")).fetchall()
    }

    # Query principal — JOIN com recebimento para filtrar por loja
    sql = """
    SELECT pf.id, pf.numero_chassi, pf.descricao, pf.chassi_doador,
           pf.status, pf.observacoes, pf.recebimento_conferencia_id,
           pf.criado_em, pf.criado_por, pf.resolvido_em, pf.resolvido_por,
           r.id AS recebimento_id, r.loja_id,
           nf.numero_nf, nf.id AS nf_id
    FROM hora_peca_faltando pf
    LEFT JOIN hora_recebimento_conferencia c ON c.id = pf.recebimento_conferencia_id
    LEFT JOIN hora_recebimento r ON r.id = c.recebimento_id
    LEFT JOIN hora_nf_entrada nf ON nf.id = r.nf_id
    WHERE 1=1
    """
    params = {}

    if not pode_ver_todas:
        sql += " AND r.loja_id = ANY(:ids)"
        params['ids'] = loja_ids

    if chassi:
        sql += " AND pf.numero_chassi ILIKE :c"
        params['c'] = f"%{chassi}%"

    if somente_abertos:
        sql += " AND COALESCE(UPPER(pf.status), 'ABERTO') NOT IN ('RESOLVIDO', 'RESOLVIDA', 'FINALIZADO', 'DONE', 'FECHADO', 'CLOSED')"

    sql += " ORDER BY pf.criado_em DESC NULLS LAST, pf.id DESC"

    rows = db.session.execute(text(sql), params).fetchall()

    pecas_out = []
    totais = {'abertas': 0, 'resolvidas': 0, 'outras': 0}

    for r in rows:
        status_norm = _normalize_status(r.status)

        if status_norm == 'aberto':
            totais['abertas'] += 1
        elif status_norm == 'resolvido':
            totais['resolvidas'] += 1
        else:
            totais['outras'] += 1

        # Fotos
        fotos_rows = db.session.execute(text(
            "SELECT foto_s3_key, legenda, criado_em, criado_por "
            "FROM hora_peca_faltando_foto "
            "WHERE peca_faltando_id = :pid "
            "ORDER BY criado_em ASC"
        ), {"pid": r.id}).fetchall()

        fotos = [
            {
                'foto_s3_key': f.foto_s3_key,
                'legenda': f.legenda,
                'criado_em': f.criado_em,
                'criado_por': f.criado_por,
            }
            for f in fotos_rows
        ]

        pecas_out.append({
            'id': r.id,
            'numero_chassi': r.numero_chassi,
            'descricao': r.descricao,
            'chassi_doador': r.chassi_doador,
            'status': r.status,
            'status_normalizado': status_norm,
            'observacoes': r.observacoes,
            'loja_id': r.loja_id,
            'loja_apelido': lojas_map.get(r.loja_id),
            'recebimento_id': r.recebimento_id,
            'recebimento_conferencia_id': r.recebimento_conferencia_id,
            'nf_numero': r.numero_nf,
            'nf_id': r.nf_id,
            'criado_em': r.criado_em,
            'criado_por': r.criado_por,
            'resolvido_em': r.resolvido_em,
            'resolvido_por': r.resolvido_por,
            'fotos': fotos,
        })

    return {
        'escopo_aplicado': {
            'loja_ids': loja_ids,
            'pode_ver_todas': pode_ver_todas,
            'chassi_filter': chassi,
            'somente_abertos': somente_abertos,
        },
        'totais': totais,
        'total_pecas': len(pecas_out),
        'pecas': pecas_out,
    }


if __name__ == '__main__':
    main()

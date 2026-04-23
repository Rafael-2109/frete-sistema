#!/usr/bin/env python3
"""
Script: conferindo_recebimento.py

Retorna progresso de conferencia fisica de recebimentos HORA.

Uso:
    --loja-ids 2,5              # escopo
    --recebimento-id 5          # 1 recebimento especifico
    --nf-numero 36612           # filtro opcional por numero_nf
    --somente-abertos           # oculta recebimentos com status DONE/finalizado
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
    parser.add_argument('--loja-ids')
    parser.add_argument('--recebimento-id', type=int)
    parser.add_argument('--nf-numero')
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
            recebimento_id=args.recebimento_id,
            nf_numero=args.nf_numero,
            somente_abertos=args.somente_abertos,
        )

    result['_debug'] = {'query_ms': int((time.time() - t_start) * 1000)}
    print(json.dumps(result, default=_json_default, ensure_ascii=False, indent=2))


def _run(loja_ids, pode_ver_todas, recebimento_id, nf_numero, somente_abertos):
    # Lookup apelidos
    lojas_map = {
        r.id: r.apelido for r in
        db.session.execute(text("SELECT id, apelido FROM hora_loja")).fetchall()
    }

    # Recebimentos
    sql = """
    SELECT r.id, r.nf_id, r.loja_id, r.data_recebimento, r.operador,
           r.status, r.observacoes, r.criado_em,
           nf.numero_nf, nf.serie_nf, nf.chave_44, nf.data_emissao,
           nf.nome_emitente, nf.valor_total,
           (SELECT COUNT(*) FROM hora_nf_entrada_item WHERE nf_id = r.nf_id) AS esperados,
           (SELECT COUNT(*) FROM hora_recebimento_conferencia WHERE recebimento_id = r.id) AS conferidos,
           (SELECT COUNT(*) FROM hora_recebimento_conferencia
              WHERE recebimento_id = r.id AND tipo_divergencia IS NOT NULL) AS divergencias
    FROM hora_recebimento r
    LEFT JOIN hora_nf_entrada nf ON nf.id = r.nf_id
    WHERE 1=1
    """
    params = {}

    if not pode_ver_todas:
        sql += " AND r.loja_id = ANY(:ids)"
        params['ids'] = loja_ids

    if recebimento_id:
        sql += " AND r.id = :rid"
        params['rid'] = recebimento_id

    if nf_numero:
        sql += " AND nf.numero_nf ILIKE :nfn"
        params['nfn'] = f"%{nf_numero}%"

    if somente_abertos:
        sql += " AND COALESCE(r.status, '') NOT IN ('FINALIZADO', 'DONE', 'CONCLUIDO')"

    sql += " ORDER BY r.data_recebimento DESC NULLS LAST, r.id DESC"

    rows = db.session.execute(text(sql), params).fetchall()

    recebimentos_out = []
    for r in rows:
        # Ultimas conferencias
        confs = db.session.execute(text(
            "SELECT numero_chassi, conferido_em, qr_code_lido, "
            "       tipo_divergencia, detalhe_divergencia, foto_s3_key, operador "
            "FROM hora_recebimento_conferencia "
            "WHERE recebimento_id = :rid "
            "ORDER BY conferido_em DESC NULLS LAST LIMIT 20"
        ), {"rid": r.id}).fetchall()

        ultimas = [
            {
                'numero_chassi': c.numero_chassi,
                'conferido_em': c.conferido_em,
                'qr_code_lido': c.qr_code_lido,
                'tipo_divergencia': c.tipo_divergencia,
                'detalhe_divergencia': c.detalhe_divergencia,
                'foto_s3_key': c.foto_s3_key,
                'operador': c.operador,
            }
            for c in confs
        ]

        # Chassis esperados - conferidos = faltando
        esperados_rows = db.session.execute(text(
            "SELECT numero_chassi FROM hora_nf_entrada_item WHERE nf_id = :nfid"
        ), {"nfid": r.nf_id}).fetchall()
        esperados_set = {x.numero_chassi for x in esperados_rows}

        conferidos_rows = db.session.execute(text(
            "SELECT numero_chassi FROM hora_recebimento_conferencia WHERE recebimento_id = :rid"
        ), {"rid": r.id}).fetchall()
        conferidos_set = {x.numero_chassi for x in conferidos_rows}

        faltando = sorted(esperados_set - conferidos_set)

        # Divergencias abertas (com detalhe)
        divs_rows = db.session.execute(text(
            "SELECT numero_chassi, tipo_divergencia, detalhe_divergencia, "
            "       foto_s3_key, operador, conferido_em "
            "FROM hora_recebimento_conferencia "
            "WHERE recebimento_id = :rid AND tipo_divergencia IS NOT NULL"
        ), {"rid": r.id}).fetchall()

        divs = [
            {
                'numero_chassi': d.numero_chassi,
                'tipo_divergencia': d.tipo_divergencia,
                'detalhe_divergencia': d.detalhe_divergencia,
                'foto_s3_key': d.foto_s3_key,
                'operador': d.operador,
                'conferido_em': d.conferido_em,
            }
            for d in divs_rows
        ]

        esperados = r.esperados or 0
        conferidos = r.conferidos or 0
        percentual = round((conferidos / esperados) * 100, 1) if esperados else 0.0

        recebimentos_out.append({
            'id': r.id,
            'status': r.status,
            'loja_id': r.loja_id,
            'loja_apelido': lojas_map.get(r.loja_id),
            'data_recebimento': r.data_recebimento,
            'operador': r.operador,
            'observacoes': r.observacoes,
            'criado_em': r.criado_em,
            'nf': (
                None if r.nf_id is None
                else {
                    'id': r.nf_id,
                    'numero_nf': r.numero_nf,
                    'serie_nf': r.serie_nf,
                    'chave_44': r.chave_44,
                    'data_emissao': r.data_emissao,
                    'nome_emitente': r.nome_emitente,
                    'valor_total': r.valor_total,
                }
            ),
            'progresso': {
                'esperados': esperados,
                'conferidos': conferidos,
                'faltando': max(esperados - conferidos, 0),
                'divergencias': r.divergencias or 0,
                'percentual_conferido': percentual,
            },
            'ultimas_conferencias': ultimas,
            'chassis_faltando': faltando[:50],  # cap 50 pra nao inflar
            'chassis_faltando_total': len(faltando),
            'divergencias_abertas': divs,
        })

    return {
        'escopo_aplicado': {
            'loja_ids': loja_ids,
            'pode_ver_todas': pode_ver_todas,
            'recebimento_id': recebimento_id,
            'nf_numero': nf_numero,
            'somente_abertos': somente_abertos,
        },
        'total_recebimentos': len(recebimentos_out),
        'recebimentos': recebimentos_out,
    }


if __name__ == '__main__':
    main()

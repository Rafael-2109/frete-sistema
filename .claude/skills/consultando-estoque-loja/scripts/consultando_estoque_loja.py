#!/usr/bin/env python3
"""
Script: consultando_estoque_loja.py

Consulta o estoque de motos nas lojas HORA respeitando escopo.

Regra central (hora/CLAUDE.md):
    - `hora_moto` e insert-once (identidade); estado vem do ULTIMO evento em
      `hora_moto_evento` (ordenado por timestamp DESC).
    - Moto sem eventos = "em transito" (pedido/NF lancados, nao recebida fisica).
    - `tipo='RECEBIDA'` em evento com `loja_id=X` = moto esta em estoque de X.

Uso:
    --loja-ids 2,5                # escopo do usuario (OBRIGATORIO quando nao-admin)
    --modelo "PMX"                # filtro opcional por nome do modelo
    --chassi MC172...             # filtro opcional por chassi (substring match)
    --resumo                      # retorna so totais + por_modelo (sem motos[])
    --incluir-transito            # inclui motos em transito
    --so-transito                 # inclui APENAS motos em transito (exclui estoque)
    --por-loja                    # quebra resultado por loja (util para admin)
"""
import sys
import os
import json
import argparse
import time
from datetime import datetime
from decimal import Decimal

# Adiciona path do projeto
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))

from app import create_app, db  # noqa: E402
from sqlalchemy import text  # noqa: E402


def _json_default(obj):
    if isinstance(obj, datetime):
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
    parser.add_argument('--loja-ids', help='CSV de loja_hora_id permitidas (None = admin)')
    parser.add_argument('--modelo', help='Filtro por nome_modelo (ILIKE %%x%%)')
    parser.add_argument('--chassi', help='Filtro por numero_chassi (ILIKE %%x%%)')
    parser.add_argument('--resumo', action='store_true', help='Omite motos[], retorna so totais')
    parser.add_argument('--incluir-transito', action='store_true', help='Inclui motos em transito')
    parser.add_argument('--so-transito', action='store_true', help='Apenas em transito')
    parser.add_argument('--por-loja', action='store_true', help='Breakdown por loja')
    args = parser.parse_args()

    t_start = time.time()

    loja_ids = _parse_loja_ids(args.loja_ids)
    pode_ver_todas = loja_ids is None

    app = create_app()
    with app.app_context():
        result = _run_query(
            loja_ids=loja_ids,
            pode_ver_todas=pode_ver_todas,
            modelo_filter=args.modelo,
            chassi_filter=args.chassi,
            resumo=args.resumo,
            incluir_transito=args.incluir_transito,
            so_transito=args.so_transito,
            por_loja=args.por_loja,
        )

    result['_debug'] = {'query_ms': int((time.time() - t_start) * 1000)}
    print(json.dumps(result, default=_json_default, ensure_ascii=False, indent=2))


def _run_query(
    loja_ids,
    pode_ver_todas,
    modelo_filter,
    chassi_filter,
    resumo,
    incluir_transito,
    so_transito,
    por_loja,
):
    # ==========================================================================
    # Query 1: lojas do escopo (para lookup de apelido)
    # ==========================================================================
    if pode_ver_todas:
        lojas_rows = db.session.execute(text(
            "SELECT id, nome, apelido, cidade, uf FROM hora_loja "
            "WHERE ativa = true ORDER BY id"
        )).fetchall()
    else:
        lojas_rows = db.session.execute(text(
            "SELECT id, nome, apelido, cidade, uf FROM hora_loja "
            "WHERE id = ANY(:ids) ORDER BY id"
        ), {"ids": loja_ids}).fetchall()

    lojas_map = {
        r.id: {
            'id': r.id, 'nome': r.nome, 'apelido': r.apelido,
            'cidade': r.cidade, 'uf': r.uf,
        }
        for r in lojas_rows
    }

    # ==========================================================================
    # Query 2: ultimo evento por chassi + join hora_moto + hora_modelo
    # Usa LATERAL para pegar a linha mais recente de eventos por chassi.
    # ==========================================================================
    sql_parts = [
        "WITH moto_com_ultimo_evento AS (",
        "  SELECT",
        "    m.numero_chassi,",
        "    m.modelo_id,",
        "    m.cor,",
        "    m.numero_motor,",
        "    m.ano_modelo,",
        "    mod.nome_modelo,",
        "    e.tipo AS evento_tipo,",
        "    e.loja_id AS evento_loja_id,",
        "    e.timestamp AS evento_ts,",
        "    e.operador AS evento_operador",
        "  FROM hora_moto m",
        "  JOIN hora_modelo mod ON mod.id = m.modelo_id",
        "  LEFT JOIN LATERAL (",
        "    SELECT tipo, loja_id, timestamp, operador",
        "    FROM hora_moto_evento ev",
        "    WHERE ev.numero_chassi = m.numero_chassi",
        "    ORDER BY ev.timestamp DESC LIMIT 1",
        "  ) e ON true",
        ")",
        "SELECT * FROM moto_com_ultimo_evento",
        "WHERE 1=1",
    ]
    params = {}

    # Filtros
    if modelo_filter:
        sql_parts.append("  AND nome_modelo ILIKE :modelo")
        params['modelo'] = f"%{modelo_filter}%"

    if chassi_filter:
        sql_parts.append("  AND numero_chassi ILIKE :chassi")
        params['chassi'] = f"%{chassi_filter}%"

    # Escopo: motos relevantes para o usuario.
    # - Em transito: loja ainda nao definida; admin ve todas; operador so ve
    #   se for dono de uma loja (apenas admin ve transito estrito).
    # - Em estoque: filtra por evento_loja_id IN escopo
    # Para manter simples em M1, filtramos apos trazer tudo (dataset pequeno: 40 motos).

    sql = "\n".join(sql_parts) + "\nORDER BY nome_modelo, numero_chassi"
    rows = db.session.execute(text(sql), params).fetchall()

    # ==========================================================================
    # Classificacao em memoria (dataset pequeno)
    # ==========================================================================
    motos = []
    totais = {'estoque': 0, 'transito': 0, 'vendido': 0, 'devolvido': 0, 'outro': 0}
    por_modelo = {}
    por_loja_data = {}

    for r in rows:
        tipo = r.evento_tipo  # pode ser None
        loja_id = r.evento_loja_id

        # Classificacao
        if tipo is None:
            status = 'transito'
        elif tipo == 'RECEBIDA':
            status = 'estoque'
        elif tipo in ('VENDIDA', 'SAIDA'):
            status = 'vendido'
        elif tipo == 'DEVOLVIDA':
            status = 'devolvido'
        else:
            status = 'outro'

        # Escopo: filtra antes de contar
        if not pode_ver_todas:
            if status == 'estoque' and loja_id not in (loja_ids or []):
                continue  # fora do escopo
            if status == 'transito':
                # Operador de loja especifica nao ve motos sem destino definido.
                # Exclui. (admin ve todas.)
                continue

        # Filtro so_transito / incluir_transito
        if so_transito and status != 'transito':
            continue
        if not incluir_transito and not so_transito and status == 'transito':
            # Por default, omite transito
            if not resumo:
                continue

        totais[status] = totais.get(status, 0) + 1

        # Por modelo
        modelo = r.nome_modelo or 'SEM_MODELO'
        if modelo not in por_modelo:
            por_modelo[modelo] = {'modelo': modelo, 'estoque': 0, 'transito': 0, 'vendido': 0}
        if status in por_modelo[modelo]:
            por_modelo[modelo][status] += 1

        # Por loja
        if por_loja and status == 'estoque' and loja_id is not None:
            if loja_id not in por_loja_data:
                por_loja_data[loja_id] = {
                    'loja_id': loja_id,
                    'loja_apelido': lojas_map.get(loja_id, {}).get('apelido', f'loja_{loja_id}'),
                    'total': 0,
                    'por_modelo': {},
                }
            por_loja_data[loja_id]['total'] += 1
            m = por_loja_data[loja_id]['por_modelo']
            m[modelo] = m.get(modelo, 0) + 1

        if not resumo:
            motos.append({
                'numero_chassi': r.numero_chassi,
                'modelo': modelo,
                'cor': r.cor,
                'numero_motor': r.numero_motor,
                'ano_modelo': r.ano_modelo,
                'status': status,
                'loja_atual_id': loja_id if status == 'estoque' else None,
                'loja_atual': (
                    lojas_map.get(loja_id, {}).get('apelido')
                    if (status == 'estoque' and loja_id is not None)
                    else None
                ),
                'ultimo_evento': (
                    None if tipo is None
                    else {
                        'tipo': tipo,
                        'timestamp': r.evento_ts,
                        'operador': r.evento_operador,
                    }
                ),
            })

    return {
        'escopo_aplicado': {
            'loja_ids': loja_ids,
            'pode_ver_todas': pode_ver_todas,
            'modelo_filter': modelo_filter,
            'chassi_filter': chassi_filter,
            'incluir_transito': incluir_transito,
            'so_transito': so_transito,
        },
        'lojas': list(lojas_map.values()),
        'totais': totais,
        'por_modelo': sorted(por_modelo.values(), key=lambda x: -x['estoque']),
        'por_loja': (
            sorted(por_loja_data.values(), key=lambda x: -x['total'])
            if por_loja else None
        ),
        'motos': motos if not resumo else [],
    }


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
Script: consultando_venda_loja.py  (Agente Lojas HORA - READ)

Consulta vendas HORA e valida preco/desconto/margem. 3 modos:
    --modo vendas   (default) lista/consulta vendas (escopo de loja)
    --modo preco    lookup de preco de tabela + validacao de desconto
    --modo margem   margem (custo/liquido/%) de UMA venda

READ-only: NUNCA cria, edita, confirma, cancela venda nem emite NFe.

Uso:
    --modo vendas --loja-ids 2 [--venda-id 9] [--chassi ABC] [--status CONFIRMADO] [--somente-pendentes-nfe]
    --modo preco  --modelo-id 10 --forma-pagamento A_VISTA [--preco-final 12000] [--modelo "BOB"]
    --modo margem --venda-id 9 --loja-ids 2
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


def _run_vendas(loja_ids, pode_ver_todas, venda_id, chassi, status, somente_pendentes_nfe):
    lojas = {r.id: r.apelido for r in db.session.execute(
        text("SELECT id, apelido FROM hora_loja ORDER BY id")).fetchall()}

    sql = "SELECT v.id, v.status, v.loja_id, v.data_venda, v.valor_total, v.valor_frete, " \
          "v.vendedor, v.forma_pagamento, v.nf_saida_numero, v.cpf_cliente, v.nome_cliente, " \
          "v.origem_criacao FROM hora_venda v WHERE 1=1"
    params = {}
    # Escopo: '= ANY(:ids)' exclui automaticamente loja_id NULL (NULL = ANY -> NULL/falso),
    # logo operador escopado NAO ve venda nao-atribuida; admin (pode_ver_todas) ve tudo.
    if not pode_ver_todas:
        sql += " AND v.loja_id = ANY(:ids)"
        params['ids'] = loja_ids
    if venda_id:
        sql += " AND v.id = :vid"
        params['vid'] = venda_id
    if status:
        sql += " AND v.status = :st"
        params['st'] = status
    if chassi:
        sql += " AND EXISTS (SELECT 1 FROM hora_venda_item vi WHERE vi.venda_id = v.id " \
               "AND vi.numero_chassi ILIKE :ch)"
        params['ch'] = f"%{chassi}%"
    if somente_pendentes_nfe:
        sql += " AND v.nf_saida_numero IS NULL"
    sql += " ORDER BY v.data_venda DESC NULLS LAST, v.id DESC"

    vendas_rows = db.session.execute(text(sql), params).fetchall()
    vids = [r.id for r in vendas_rows]

    itens_por_venda = {}
    nfe_por_venda = {}
    div_por_venda = {}
    if vids:
        itens_rows = db.session.execute(text(
            "SELECT vi.venda_id, vi.numero_chassi, mo.nome_modelo AS modelo, mt.cor AS cor, "
            "vi.preco_final, vi.desconto_aplicado, vi.desconto_percentual "
            "FROM hora_venda_item vi "
            "LEFT JOIN hora_moto mt ON mt.numero_chassi = vi.numero_chassi "
            "LEFT JOIN hora_modelo mo ON mo.id = mt.modelo_id "
            "WHERE vi.venda_id = ANY(:vids)"), {'vids': vids}).fetchall()
        for r in itens_rows:
            itens_por_venda.setdefault(r.venda_id, []).append({
                'numero_chassi': r.numero_chassi, 'modelo': r.modelo or '—', 'cor': r.cor or '—',
                'preco_final': r.preco_final, 'desconto_aplicado': r.desconto_aplicado,
                'desconto_percentual': r.desconto_percentual,
            })
        for r in db.session.execute(text(
            "SELECT venda_id, status FROM hora_tagplus_nfe_emissao WHERE venda_id = ANY(:vids)"),
                {'vids': vids}).fetchall():
            nfe_por_venda[r.venda_id] = r.status
        for r in db.session.execute(text(
            "SELECT venda_id, COUNT(*) AS n FROM hora_venda_divergencia "
            "WHERE venda_id = ANY(:vids) AND resolvida_em IS NULL GROUP BY venda_id"),
                {'vids': vids}).fetchall():
            div_por_venda[r.venda_id] = r.n

    vendas = []
    for r in vendas_rows:
        if r.loja_id is None:
            loja_apelido = '(sem loja)'
        else:
            loja_apelido = lojas.get(r.loja_id, f'loja {r.loja_id}')
        vendas.append({
            'id': r.id, 'status': r.status, 'loja_id': r.loja_id,
            'loja_apelido': loja_apelido,
            'data_venda': r.data_venda, 'valor_total': r.valor_total, 'valor_frete': r.valor_frete,
            'vendedor': r.vendedor, 'forma_pagamento': r.forma_pagamento,
            'nf_saida_numero': r.nf_saida_numero,
            'nfe_status': nfe_por_venda.get(r.id, 'SEM_NFE'),
            'divergencias_abertas': div_por_venda.get(r.id, 0),
            'cpf_cliente': r.cpf_cliente, 'nome_cliente': r.nome_cliente,
            'origem_criacao': r.origem_criacao,
            'itens': itens_por_venda.get(r.id, []),
        })

    return {
        'escopo_aplicado': {'loja_ids': loja_ids, 'pode_ver_todas': pode_ver_todas},
        'vendas': vendas,
        'total_vendas': len(vendas),
    }


def _run_preco(modelo_id, modelo_nome, forma_pagamento, preco_final):
    from app.hora.services import venda_service

    if modelo_id is None and modelo_nome:
        row = db.session.execute(text(
            "SELECT id, nome_modelo FROM hora_modelo "
            "WHERE nome_modelo ILIKE :n AND merged_em_id IS NULL "
            "ORDER BY id LIMIT 1"), {'n': f"%{modelo_nome}%"}).fetchone()
        if row is None:
            alias = db.session.execute(text(
                "SELECT modelo_id FROM hora_modelo_alias "
                "WHERE nome_alias ILIKE :n AND ativo = TRUE LIMIT 1"),
                {'n': f"%{modelo_nome}%"}).fetchone()
            modelo_id = alias.modelo_id if alias else None
        else:
            modelo_id = row.id

    if modelo_id is None:
        return {'erro': 'modelo_nao_resolvido', 'modelo_nome': modelo_nome}

    preco = venda_service.buscar_preco_para_pedido(modelo_id, forma_pagamento)
    out = {
        'modelo_id': modelo_id,
        'forma_pagamento': forma_pagamento,
        'preco_tabela': preco.get('preco'),
        'preco_a_vista': preco.get('preco_a_vista'),
        'preco_a_prazo': preco.get('preco_a_prazo'),
        'fonte': preco.get('fonte'),
    }
    if preco_final is not None:
        out['validacao_desconto'] = venda_service.validar_desconto_tabela(
            modelo_id, Decimal(str(preco_final).replace(',', '.')), forma_pagamento)
    return out


def _run_margem(venda_id, loja_ids, pode_ver_todas):
    if not venda_id:
        return {'erro': 'venda_id_obrigatorio'}
    from app.hora.models.venda import HoraVenda
    from app.hora.services import venda_preview_service

    venda = HoraVenda.query.get(venda_id)
    if venda is None:
        return {'erro': 'venda_nao_encontrada', 'venda_id': venda_id}
    if not pode_ver_todas and venda.loja_id not in (loja_ids or []):
        return {'erro': 'fora_de_escopo', 'venda_id': venda_id}

    preview = venda_preview_service.montar_preview(venda)
    return {'venda_id': venda_id, 'escopo_ok': True, 'preview': preview}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--modo', choices=['vendas', 'preco', 'margem'], default='vendas')
    parser.add_argument('--loja-ids', help='CSV de loja_id (None=admin)')
    parser.add_argument('--venda-id', type=int)
    parser.add_argument('--chassi')
    parser.add_argument('--status')
    parser.add_argument('--somente-pendentes-nfe', action='store_true')
    parser.add_argument('--modelo-id', type=int)
    parser.add_argument('--modelo', help='Nome do modelo (lookup best-effort)')
    parser.add_argument('--forma-pagamento', help='A_VISTA | A_PRAZO')
    parser.add_argument('--preco-final')
    args = parser.parse_args()

    t_start = time.time()
    loja_ids = _parse_loja_ids(args.loja_ids)
    pode_ver_todas = loja_ids is None

    app = create_app()
    with app.app_context():
        if args.modo == 'vendas':
            result = _run_vendas(loja_ids, pode_ver_todas, args.venda_id,
                                 args.chassi, args.status, args.somente_pendentes_nfe)
        elif args.modo == 'preco':
            result = _run_preco(args.modelo_id, args.modelo, args.forma_pagamento, args.preco_final)
        else:
            result = _run_margem(args.venda_id, loja_ids, pode_ver_todas)

    result['_debug'] = {'query_ms': int((time.time() - t_start) * 1000)}
    print(json.dumps(result, default=_json_default, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

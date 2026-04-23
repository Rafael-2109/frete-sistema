#!/usr/bin/env python3
"""
Script: rastreando_chassi.py

Retorna o historico completo de uma moto no modulo HORA via numero_chassi,
cruzando pedido, NF de entrada, recebimento, eventos, venda e devolucao.

Uso:
    --loja-ids 2,5          # escopo (None = admin)
    --chassi MC172...       # chassi alvo (obrigatorio)
"""
import sys
import os
import json
import argparse
import time
from datetime import datetime
from decimal import Decimal

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
    parser.add_argument('--loja-ids', help='CSV de loja_hora_id permitidas (None=admin)')
    parser.add_argument('--chassi', required=True, help='numero_chassi (exato ou substring)')
    args = parser.parse_args()

    t_start = time.time()
    loja_ids = _parse_loja_ids(args.loja_ids)
    pode_ver_todas = loja_ids is None

    app = create_app()
    with app.app_context():
        result = _run_trace(
            chassi_input=args.chassi,
            loja_ids=loja_ids,
            pode_ver_todas=pode_ver_todas,
        )

    result['_debug'] = {'query_ms': int((time.time() - t_start) * 1000)}
    print(json.dumps(result, default=_json_default, ensure_ascii=False, indent=2))


def _run_trace(chassi_input, loja_ids, pode_ver_todas):
    # ==========================================================================
    # 1. Resolucao do chassi (ILIKE para substring match)
    # ==========================================================================
    moto_row = db.session.execute(text(
        "SELECT m.numero_chassi, m.modelo_id, m.cor, m.numero_motor, m.ano_modelo, "
        "       mod.nome_modelo "
        "FROM hora_moto m "
        "JOIN hora_modelo mod ON mod.id = m.modelo_id "
        "WHERE m.numero_chassi ILIKE :c "
        "ORDER BY m.numero_chassi LIMIT 1"
    ), {"c": f"%{chassi_input}%"}).first()

    if not moto_row:
        return {
            'escopo_aplicado': {'loja_ids': loja_ids, 'pode_ver_todas': pode_ver_todas},
            'encontrado': False,
            'motivo': 'chassi nao cadastrado',
            'chassi_buscado': chassi_input,
        }

    chassi = moto_row.numero_chassi

    # ==========================================================================
    # 2. Eventos completos (ordem cronologica)
    # ==========================================================================
    eventos = db.session.execute(text(
        "SELECT e.tipo, e.loja_id, e.timestamp, e.operador, e.origem_tabela, "
        "       e.origem_id, e.detalhe, l.apelido AS loja_apelido "
        "FROM hora_moto_evento e "
        "LEFT JOIN hora_loja l ON l.id = e.loja_id "
        "WHERE e.numero_chassi = :c "
        "ORDER BY e.timestamp ASC"
    ), {"c": chassi}).fetchall()

    eventos_list = [
        {
            'tipo': r.tipo,
            'loja_id': r.loja_id,
            'loja_apelido': r.loja_apelido,
            'timestamp': r.timestamp,
            'operador': r.operador,
            'origem_tabela': r.origem_tabela,
            'origem_id': r.origem_id,
            'detalhe': r.detalhe,
        }
        for r in eventos
    ]

    # ==========================================================================
    # 3. Guard de escopo — se nao-admin, verifica se chassi tem evento em
    #    loja permitida. Se nao tem, retorna access_denied.
    # ==========================================================================
    if not pode_ver_todas:
        tem_evento_no_escopo = any(
            e['loja_id'] in (loja_ids or []) for e in eventos_list
        )
        # Alem de eventos, verifica pedido/recebimento (proxy de pertencimento)
        if not tem_evento_no_escopo:
            row = db.session.execute(text(
                "SELECT 1 "
                "FROM hora_pedido_item pi "
                "JOIN hora_pedido p ON p.id = pi.pedido_id "
                "WHERE pi.numero_chassi = :c AND p.loja_destino_id = ANY(:ids) LIMIT 1"
            ), {"c": chassi, "ids": loja_ids}).first()
            if not row:
                return {
                    'escopo_aplicado': {'loja_ids': loja_ids, 'pode_ver_todas': False},
                    'encontrado': True,
                    'access_denied': True,
                    'motivo': 'chassi nao pertence a nenhuma loja do seu escopo',
                    'chassi': chassi,
                }

    # ==========================================================================
    # 4. Pedido + item (se existir)
    # ==========================================================================
    pedido_row = db.session.execute(text(
        "SELECT p.id, p.numero_pedido, p.status, p.loja_destino_id, p.data_pedido, "
        "       p.apelido_detectado, pi.preco_compra_esperado "
        "FROM hora_pedido_item pi "
        "JOIN hora_pedido p ON p.id = pi.pedido_id "
        "WHERE pi.numero_chassi = :c "
        "ORDER BY p.data_pedido DESC NULLS LAST LIMIT 1"
    ), {"c": chassi}).first()

    pedido = None
    if pedido_row:
        pedido = {
            'id': pedido_row.id,
            'numero_pedido': pedido_row.numero_pedido,
            'status': pedido_row.status,
            'loja_destino_id': pedido_row.loja_destino_id,
            'apelido_detectado': pedido_row.apelido_detectado,
            'data_pedido': pedido_row.data_pedido,
            'preco_compra_esperado': pedido_row.preco_compra_esperado,
        }

    # ==========================================================================
    # 5. NF entrada + item
    # ==========================================================================
    nf_row = db.session.execute(text(
        "SELECT nf.id, nf.numero_nf, nf.serie_nf, nf.chave_44, nf.data_emissao, "
        "       nf.valor_total, nf.loja_destino_id, nf.nome_emitente, "
        "       nfi.preco_real "
        "FROM hora_nf_entrada_item nfi "
        "JOIN hora_nf_entrada nf ON nf.id = nfi.nf_id "
        "WHERE nfi.numero_chassi = :c "
        "ORDER BY nf.data_emissao DESC NULLS LAST LIMIT 1"
    ), {"c": chassi}).first()

    nf_entrada = None
    if nf_row:
        nf_entrada = {
            'id': nf_row.id,
            'numero_nf': nf_row.numero_nf,
            'serie_nf': nf_row.serie_nf,
            'chave_44': nf_row.chave_44,
            'emissao': nf_row.data_emissao,
            'valor_total': nf_row.valor_total,
            'loja_destino_id': nf_row.loja_destino_id,
            'nome_emitente': nf_row.nome_emitente,
            'preco_real': nf_row.preco_real,
        }

    # ==========================================================================
    # 6. Recebimento + conferencia
    # ==========================================================================
    receb_row = db.session.execute(text(
        "SELECT r.id, r.loja_id, r.data_recebimento, r.operador AS r_operador, "
        "       c.conferido_em, c.qr_code_lido, c.foto_s3_key, "
        "       c.tipo_divergencia, c.detalhe_divergencia, c.operador "
        "FROM hora_recebimento_conferencia c "
        "JOIN hora_recebimento r ON r.id = c.recebimento_id "
        "WHERE c.numero_chassi = :c "
        "ORDER BY c.conferido_em DESC NULLS LAST LIMIT 1"
    ), {"c": chassi}).first()

    recebimento = None
    if receb_row:
        recebimento = {
            'id': receb_row.id,
            'loja_id': receb_row.loja_id,
            'data_recebimento': receb_row.data_recebimento,
            'recebimento_operador': receb_row.r_operador,
            'conferido_em': receb_row.conferido_em,
            'qr_code_lido': receb_row.qr_code_lido,
            'foto_s3_key': receb_row.foto_s3_key,
            'tipo_divergencia': receb_row.tipo_divergencia,
            'detalhe_divergencia': receb_row.detalhe_divergencia,
            'operador': receb_row.operador,
        }

    # ==========================================================================
    # 7. Venda (se existir)
    # ==========================================================================
    venda_row = db.session.execute(text(
        "SELECT v.id, v.loja_id, v.data_venda, v.cpf_cliente, v.nome_cliente, "
        "       v.valor_total, v.vendedor, v.status, "
        "       vi.preco_tabela_referencia, vi.desconto_aplicado, vi.preco_final "
        "FROM hora_venda_item vi "
        "JOIN hora_venda v ON v.id = vi.venda_id "
        "WHERE vi.numero_chassi = :c "
        "ORDER BY v.data_venda DESC NULLS LAST LIMIT 1"
    ), {"c": chassi}).first()

    venda = None
    if venda_row:
        venda = {
            'id': venda_row.id,
            'loja_id': venda_row.loja_id,
            'data_venda': venda_row.data_venda,
            'cpf_cliente': venda_row.cpf_cliente,
            'nome_cliente': venda_row.nome_cliente,
            'valor_total': venda_row.valor_total,
            'vendedor': venda_row.vendedor,
            'status': venda_row.status,
            'preco_tabela_referencia': venda_row.preco_tabela_referencia,
            'desconto_aplicado': venda_row.desconto_aplicado,
            'preco_final': venda_row.preco_final,
        }

    # ==========================================================================
    # 8. Devolucao (se existir)
    # ==========================================================================
    devol_row = db.session.execute(text(
        "SELECT d.id, d.loja_id, d.data_devolucao, d.motivo, d.status, di.id AS item_id "
        "FROM hora_devolucao_fornecedor_item di "
        "JOIN hora_devolucao_fornecedor d ON d.id = di.devolucao_id "
        "WHERE di.numero_chassi = :c "
        "ORDER BY d.data_devolucao DESC NULLS LAST LIMIT 1"
    ), {"c": chassi}).first()

    devolucao = None
    if devol_row:
        devolucao = {
            'id': devol_row.id,
            'item_id': devol_row.item_id,
            'loja_id': devol_row.loja_id,
            'data_devolucao': devol_row.data_devolucao,
            'motivo': devol_row.motivo,
            'status': devol_row.status,
        }

    # ==========================================================================
    # 9. Estado atual (derivado do ultimo evento)
    # ==========================================================================
    estado_atual = {'status': 'transito', 'loja_id': None, 'loja_apelido': None}
    if eventos_list:
        ultimo = eventos_list[-1]
        tipo = ultimo.get('tipo')
        if tipo == 'RECEBIDA':
            estado_atual = {
                'status': 'estoque',
                'loja_id': ultimo.get('loja_id'),
                'loja_apelido': ultimo.get('loja_apelido'),
            }
        elif tipo in ('VENDIDA', 'SAIDA'):
            estado_atual = {
                'status': 'vendido',
                'loja_id': ultimo.get('loja_id'),
                'loja_apelido': ultimo.get('loja_apelido'),
            }
        elif tipo == 'DEVOLVIDA':
            estado_atual = {
                'status': 'devolvido',
                'loja_id': None,
                'loja_apelido': None,
            }
        else:
            estado_atual = {
                'status': tipo.lower() if tipo else 'transito',
                'loja_id': ultimo.get('loja_id'),
                'loja_apelido': ultimo.get('loja_apelido'),
            }

    return {
        'escopo_aplicado': {'loja_ids': loja_ids, 'pode_ver_todas': pode_ver_todas},
        'encontrado': True,
        'access_denied': False,
        'chassi': chassi,
        'moto': {
            'numero_chassi': moto_row.numero_chassi,
            'modelo': moto_row.nome_modelo,
            'cor': moto_row.cor,
            'numero_motor': moto_row.numero_motor,
            'ano_modelo': moto_row.ano_modelo,
        },
        'pedido': pedido,
        'nf_entrada': nf_entrada,
        'recebimento': recebimento,
        'eventos': eventos_list,
        'venda': venda,
        'devolucao': devolucao,
        'estado_atual': estado_atual,
    }


if __name__ == '__main__':
    main()

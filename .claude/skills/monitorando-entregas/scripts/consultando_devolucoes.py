#!/usr/bin/env python3
"""
Script para consultar devoluções e ocorrências.

Uso:
    python consultando_devolucoes.py --abertas
    python consultando_devolucoes.py --nf 12345
    python consultando_devolucoes.py --cliente "Atacadao"
"""

import argparse
import json
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))

from datetime import datetime, date
from app import create_app, db
from sqlalchemy import text


def consultar_devolucoes(
    numero_nf_venda: str = None,
    numero_nfd: str = None,
    cliente: str = None,
    abertas: bool = False,
    data_de: str = None,
    data_ate: str = None,
    limite: int = 50
) -> dict:
    """
    Consulta devoluções (nf_devolucao) com ocorrências relacionadas.

    Returns:
        dict com sucesso, total e lista de devoluções
    """
    app = create_app()
    with app.app_context():
        try:
            sql = """
                SELECT
                    nfd.id,
                    nfd.numero_nfd,
                    nfd.numero_nf_venda,
                    nfd.chave_nfd,
                    nfd.motivo,
                    nfd.descricao_motivo,
                    nfd.valor_total,
                    nfd.data_emissao,
                    nfd.data_entrada,
                    nfd.cnpj_emitente,
                    nfd.nome_emitente,
                    nfd.status as status_nfd,
                    nfd.sincronizado_odoo,
                    nfd.odoo_dfe_id,
                    nfd.criado_em,
                    oc.id as ocorrencia_id,
                    oc.numero_ocorrencia,
                    oc.status as status_ocorrencia,
                    oc.destino,
                    oc.localizacao_atual,
                    oc.categoria,
                    oc.subcategoria,
                    oc.responsavel,
                    oc.origem,
                    oc.data_previsao_retorno,
                    oc.data_chegada_cd,
                    oc.data_abertura,
                    oc.data_resolucao,
                    oc.desfecho
                FROM nf_devolucao nfd
                LEFT JOIN ocorrencia_devolucao oc ON oc.nf_devolucao_id = nfd.id
                WHERE nfd.ativo = true
            """
            params = {}

            # Filtro por NF original
            if numero_nf_venda:
                sql += " AND nfd.numero_nf_venda ILIKE :nf_venda"
                params['nf_venda'] = f"%{numero_nf_venda}%"

            # Filtro por NFD
            if numero_nfd:
                sql += " AND nfd.numero_nfd ILIKE :nfd"
                params['nfd'] = f"%{numero_nfd}%"

            # Filtro por cliente
            if cliente:
                sql += " AND nfd.nome_emitente ILIKE :cliente"
                params['cliente'] = f"%{cliente}%"

            # Filtro de ocorrências abertas
            if abertas:
                sql += " AND oc.status IN ('ABERTA', 'EM_ANALISE', 'AGUARDANDO_RETORNO')"

            # Filtro de período
            if data_de:
                sql += " AND nfd.data_registro >= :data_de"
                params['data_de'] = data_de

            if data_ate:
                sql += " AND nfd.data_registro <= :data_ate"
                params['data_ate'] = data_ate

            sql += " ORDER BY nfd.data_registro DESC"
            sql += f" LIMIT {limite}"

            result = db.session.execute(text(sql), params)
            rows = result.fetchall()
            columns = result.keys()

            devolucoes = []
            for row in rows:
                dev = dict(zip(columns, row))
                for key, value in dev.items():
                    if isinstance(value, (datetime, date)):
                        dev[key] = value.isoformat() if value else None
                devolucoes.append(dev)

            # Conta total
            sql_count = """
                SELECT COUNT(*)
                FROM nf_devolucao nfd
                LEFT JOIN ocorrencia_devolucao oc ON oc.nf_devolucao_id = nfd.id
                WHERE nfd.ativo = true
            """
            if numero_nf_venda:
                sql_count += " AND nfd.numero_nf_venda ILIKE :nf_venda"
            if numero_nfd:
                sql_count += " AND nfd.numero_nfd ILIKE :nfd"
            if cliente:
                sql_count += " AND nfd.nome_emitente ILIKE :cliente"
            if abertas:
                sql_count += " AND oc.status IN ('ABERTA', 'EM_ANALISE', 'AGUARDANDO_RETORNO')"
            if data_de:
                sql_count += " AND nfd.data_registro >= :data_de"
            if data_ate:
                sql_count += " AND nfd.data_registro <= :data_ate"

            total = db.session.execute(text(sql_count), params).scalar()

            return {
                "sucesso": True,
                "total": total,
                "exibindo": len(devolucoes),
                "devolucoes": devolucoes
            }

        except Exception as e:
            return {
                "sucesso": False,
                "erro": str(e),
                "total": 0,
                "devolucoes": []
            }


def main():
    parser = argparse.ArgumentParser(description='Consulta devoluções e ocorrências')

    parser.add_argument('--nf', type=str, help='Número da NF original')
    parser.add_argument('--nfd', type=str, help='Número da NFD')
    parser.add_argument('--cliente', type=str, help='Nome do cliente')
    parser.add_argument('--abertas', action='store_true', help='Apenas ocorrências abertas')
    parser.add_argument('--de', type=str, dest='data_de', help='Data inicial (YYYY-MM-DD)')
    parser.add_argument('--ate', type=str, dest='data_ate', help='Data final (YYYY-MM-DD)')
    parser.add_argument('--limite', type=int, default=50, help='Máximo de registros')

    args = parser.parse_args()

    resultado = consultar_devolucoes(
        numero_nf_venda=args.nf,
        numero_nfd=args.nfd,
        cliente=args.cliente,
        abertas=args.abertas,
        data_de=args.data_de,
        data_ate=args.data_ate,
        limite=args.limite
    )

    print(json.dumps(resultado, indent=2, ensure_ascii=False, default=str))


if __name__ == '__main__':
    main()

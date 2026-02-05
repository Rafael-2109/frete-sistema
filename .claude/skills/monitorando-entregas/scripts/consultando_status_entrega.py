#!/usr/bin/env python3
"""
Script para consultar status de entregas monitoradas.

Uso:
    python consultando_status_entrega.py --nf 12345
    python consultando_status_entrega.py --cliente "Atacadao" --pendentes
    python consultando_status_entrega.py --problemas --limite 20
    python consultando_status_entrega.py --entregues --de 2025-01-01 --ate 2025-01-31
"""

import argparse
import json
import sys
import os

# Adiciona o diretório raiz ao path para importar os módulos do app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))

from datetime import datetime, date
from app import create_app, db
from sqlalchemy import text


def consultar_entregas(
    numero_nf: str = None,
    cliente: str = None,
    cnpj: str = None,
    transportadora: str = None,
    pendentes: bool = False,
    entregues: bool = False,
    no_cd: bool = False,
    reagendadas: bool = False,
    problemas: bool = False,
    data_de: str = None,
    data_ate: str = None,
    limite: int = 50,
    formato: str = 'json'
) -> dict:
    """
    Consulta entregas monitoradas com diversos filtros.

    Returns:
        dict com sucesso, total e lista de entregas
    """
    app = create_app()
    with app.app_context():
        try:
            # Monta a query base
            sql = """
                SELECT
                    id,
                    numero_nf,
                    cliente,
                    cnpj_cliente,
                    transportadora,
                    municipio,
                    uf,
                    vendedor,
                    valor_nf,
                    data_faturamento,
                    data_embarque,
                    data_entrega_prevista,
                    data_hora_entrega_realizada,
                    status_finalizacao,
                    entregue,
                    nf_cd,
                    reagendar,
                    motivo_reagendamento,
                    data_agenda,
                    teve_devolucao,
                    canhoto_arquivo,
                    nova_nf,
                    observacao_operacional,
                    criado_em,
                    finalizado_em,
                    finalizado_por
                FROM entregas_monitoradas
                WHERE 1=1
            """
            params = {}

            # Filtro por número da NF
            if numero_nf:
                sql += " AND numero_nf ILIKE :nf"
                params['nf'] = f"%{numero_nf}%"

            # Filtro por cliente
            if cliente:
                sql += " AND cliente ILIKE :cliente"
                params['cliente'] = f"%{cliente}%"

            # Filtro por CNPJ
            if cnpj:
                # Remove formatação do CNPJ
                cnpj_limpo = ''.join(filter(str.isdigit, cnpj))
                sql += " AND REPLACE(REPLACE(REPLACE(cnpj_cliente, '.', ''), '-', ''), '/', '') LIKE :cnpj"
                params['cnpj'] = f"%{cnpj_limpo}%"

            # Filtro por transportadora
            if transportadora:
                sql += " AND transportadora ILIKE :transportadora"
                params['transportadora'] = f"%{transportadora}%"

            # Filtro de pendentes (status_finalizacao IS NULL)
            if pendentes:
                sql += " AND status_finalizacao IS NULL"

            # Filtro de entregues
            if entregues:
                sql += " AND status_finalizacao = 'Entregue'"

            # Filtro de NFs no CD
            if no_cd:
                sql += " AND nf_cd = true"

            # Filtro de reagendadas
            if reagendadas:
                sql += " AND reagendar = true"

            # Filtro de problemas (nf_cd OR reagendar)
            if problemas:
                sql += " AND (nf_cd = true OR reagendar = true)"

            # Filtro de período
            if data_de:
                sql += " AND data_faturamento >= :data_de"
                params['data_de'] = data_de

            if data_ate:
                sql += " AND data_faturamento <= :data_ate"
                params['data_ate'] = data_ate

            # Ordenação e limite
            sql += " ORDER BY data_faturamento DESC, numero_nf"
            sql += f" LIMIT {limite}"

            # Executa a query
            result = db.session.execute(text(sql), params)
            rows = result.fetchall()
            columns = result.keys()

            # Converte para lista de dicionários
            entregas = []
            for row in rows:
                entrega = dict(zip(columns, row))
                # Converte datas para string
                for key, value in entrega.items():
                    if isinstance(value, (datetime, date)):
                        entrega[key] = value.isoformat() if value else None
                entregas.append(entrega)

            # Conta total (sem limite)
            sql_count = """
                SELECT COUNT(*) FROM entregas_monitoradas WHERE 1=1
            """
            if numero_nf:
                sql_count += " AND numero_nf ILIKE :nf"
            if cliente:
                sql_count += " AND cliente ILIKE :cliente"
            if cnpj:
                sql_count += " AND REPLACE(REPLACE(REPLACE(cnpj_cliente, '.', ''), '-', ''), '/', '') LIKE :cnpj"
            if transportadora:
                sql_count += " AND transportadora ILIKE :transportadora"
            if pendentes:
                sql_count += " AND status_finalizacao IS NULL"
            if entregues:
                sql_count += " AND status_finalizacao = 'Entregue'"
            if no_cd:
                sql_count += " AND nf_cd = true"
            if reagendadas:
                sql_count += " AND reagendar = true"
            if problemas:
                sql_count += " AND (nf_cd = true OR reagendar = true)"
            if data_de:
                sql_count += " AND data_faturamento >= :data_de"
            if data_ate:
                sql_count += " AND data_faturamento <= :data_ate"

            total_result = db.session.execute(text(sql_count), params)
            total = total_result.scalar()

            return {
                "sucesso": True,
                "total": total,
                "exibindo": len(entregas),
                "filtros_aplicados": {
                    "numero_nf": numero_nf,
                    "cliente": cliente,
                    "cnpj": cnpj,
                    "transportadora": transportadora,
                    "pendentes": pendentes,
                    "entregues": entregues,
                    "no_cd": no_cd,
                    "reagendadas": reagendadas,
                    "problemas": problemas,
                    "data_de": data_de,
                    "data_ate": data_ate
                },
                "entregas": entregas
            }

        except Exception as e:
            return {
                "sucesso": False,
                "erro": str(e),
                "total": 0,
                "entregas": []
            }


def main():
    parser = argparse.ArgumentParser(description='Consulta status de entregas monitoradas')

    # Filtros de busca
    parser.add_argument('--nf', type=str, help='Número da NF (busca parcial)')
    parser.add_argument('--cliente', type=str, help='Nome do cliente (busca parcial)')
    parser.add_argument('--cnpj', type=str, help='CNPJ do cliente')
    parser.add_argument('--transportadora', type=str, help='Nome da transportadora')

    # Filtros de status
    parser.add_argument('--pendentes', action='store_true', help='Apenas pendentes (status_finalizacao IS NULL)')
    parser.add_argument('--entregues', action='store_true', help='Apenas entregues')
    parser.add_argument('--no-cd', action='store_true', dest='no_cd', help='Apenas NFs no CD')
    parser.add_argument('--reagendadas', action='store_true', help='Apenas reagendadas')
    parser.add_argument('--problemas', action='store_true', help='Com problema (nf_cd=true OR reagendar=true)')

    # Filtros de período
    parser.add_argument('--de', type=str, dest='data_de', help='Data inicial (YYYY-MM-DD)')
    parser.add_argument('--ate', type=str, dest='data_ate', help='Data final (YYYY-MM-DD)')

    # Opções de saída
    parser.add_argument('--limite', type=int, default=50, help='Máximo de registros (default: 50)')
    parser.add_argument('--formato', choices=['json', 'tabela'], default='json', help='Formato de saída')

    args = parser.parse_args()

    resultado = consultar_entregas(
        numero_nf=args.nf,
        cliente=args.cliente,
        cnpj=args.cnpj,
        transportadora=args.transportadora,
        pendentes=args.pendentes,
        entregues=args.entregues,
        no_cd=args.no_cd,
        reagendadas=args.reagendadas,
        problemas=args.problemas,
        data_de=args.data_de,
        data_ate=args.data_ate,
        limite=args.limite,
        formato=args.formato
    )

    if args.formato == 'tabela' and resultado['sucesso'] and resultado['entregas']:
        # Exibe em formato tabela
        print(f"\n{'='*100}")
        print(f"ENTREGAS MONITORADAS - Total: {resultado['total']} | Exibindo: {resultado['exibindo']}")
        print(f"{'='*100}")
        print(f"{'NF':<12} {'Cliente':<30} {'Status':<15} {'Embarque':<12} {'Transportadora':<20}")
        print(f"{'-'*100}")
        for e in resultado['entregas']:
            status = e['status_finalizacao'] or 'Pendente'
            embarque = e['data_embarque'] or '-'
            transp = (e['transportadora'] or '-')[:20]
            cliente = (e['cliente'] or '-')[:30]
            print(f"{e['numero_nf']:<12} {cliente:<30} {status:<15} {embarque:<12} {transp:<20}")
        print(f"{'='*100}\n")
    else:
        # Exibe em formato JSON
        print(json.dumps(resultado, indent=2, ensure_ascii=False, default=str))


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
Consulta operacoes e subcontratos CarVia
=========================================

Modos:
  --resumo              Resumo geral (contadores por status)
  --operacao ID         Detalhe de operacao especifica
  --status STATUS       Filtrar por status (RASCUNHO, COTADO, CONFIRMADO, FATURADO, CANCELADO)
  --cliente NOME        Filtrar por nome/CNPJ do cliente
  --transportadora NOME Filtrar subcontratos por transportadora
  --subcontratos-pendentes  Listar subcontratos que precisam de acao
  --limite N            Limite de resultados (default 20)
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))


def get_resumo():
    """Resumo geral: contadores por status de operacao e subcontrato"""
    from app import db
    from app.carvia.models import (
        CarviaOperacao, CarviaSubcontrato,
        CarviaFaturaCliente, CarviaFaturaTransportadora,
    )

    result = {'sucesso': True, 'tipo': 'resumo'}

    # Operacoes por status
    op_status = db.session.query(
        CarviaOperacao.status,
        db.func.count(CarviaOperacao.id),
    ).group_by(CarviaOperacao.status).all()
    result['operacoes_por_status'] = {s: c for s, c in op_status}
    result['total_operacoes'] = sum(c for _, c in op_status)

    # Subcontratos por status
    sub_status = db.session.query(
        CarviaSubcontrato.status,
        db.func.count(CarviaSubcontrato.id),
    ).group_by(CarviaSubcontrato.status).all()
    result['subcontratos_por_status'] = {s: c for s, c in sub_status}
    result['total_subcontratos'] = sum(c for _, c in sub_status)

    # Valor total CTe por status
    op_valor = db.session.query(
        CarviaOperacao.status,
        db.func.sum(CarviaOperacao.cte_valor),
    ).group_by(CarviaOperacao.status).all()
    result['valor_cte_por_status'] = {
        s: float(v or 0) for s, v in op_valor
    }

    # Faturas
    fat_cli = db.session.query(
        CarviaFaturaCliente.status,
        db.func.count(CarviaFaturaCliente.id),
        db.func.sum(CarviaFaturaCliente.valor_total),
    ).group_by(CarviaFaturaCliente.status).all()
    result['faturas_cliente'] = {
        s: {'qtd': c, 'valor': float(v or 0)} for s, c, v in fat_cli
    }

    fat_transp = db.session.query(
        CarviaFaturaTransportadora.status_conferencia,
        db.func.count(CarviaFaturaTransportadora.id),
        db.func.sum(CarviaFaturaTransportadora.valor_total),
    ).group_by(CarviaFaturaTransportadora.status_conferencia).all()
    result['faturas_transportadora'] = {
        s: {'qtd': c, 'valor': float(v or 0)} for s, c, v in fat_transp
    }

    return result


def get_operacao_detalhe(operacao_id):
    """Detalhe completo de uma operacao"""
    from app import db
    from app.carvia.models import CarviaOperacao

    op = db.session.get(CarviaOperacao, operacao_id)
    if not op:
        return {'sucesso': False, 'erro': f'Operacao {operacao_id} nao encontrada'}

    nfs = []
    for nf in op.nfs.all():
        nfs.append({
            'id': nf.id,
            'numero_nf': nf.numero_nf,
            'serie_nf': nf.serie_nf,
            'chave_acesso_nf': nf.chave_acesso_nf,
            'cnpj_emitente': nf.cnpj_emitente,
            'nome_emitente': nf.nome_emitente,
            'valor_total': float(nf.valor_total or 0),
            'peso_bruto': float(nf.peso_bruto or 0),
            'tipo_fonte': nf.tipo_fonte,
        })

    subs = []
    for sub in op.subcontratos.all():
        subs.append({
            'id': sub.id,
            'transportadora': sub.transportadora.razao_social if sub.transportadora else None,
            'transportadora_id': sub.transportadora_id,
            'cte_numero': sub.cte_numero,
            'cte_valor': float(sub.cte_valor or 0),
            'valor_cotado': float(sub.valor_cotado or 0),
            'valor_acertado': float(sub.valor_acertado or 0) if sub.valor_acertado else None,
            'valor_final': float(sub.valor_final or 0),
            'tabela_frete_id': sub.tabela_frete_id,
            'status': sub.status,
            'fatura_transportadora_id': sub.fatura_transportadora_id,
        })

    return {
        'sucesso': True,
        'tipo': 'detalhe_operacao',
        'operacao': {
            'id': op.id,
            'cte_numero': op.cte_numero,
            'cte_chave_acesso': op.cte_chave_acesso,
            'cte_valor': float(op.cte_valor or 0),
            'cte_data_emissao': str(op.cte_data_emissao) if op.cte_data_emissao else None,
            'cnpj_cliente': op.cnpj_cliente,
            'nome_cliente': op.nome_cliente,
            'uf_origem': op.uf_origem,
            'cidade_origem': op.cidade_origem,
            'uf_destino': op.uf_destino,
            'cidade_destino': op.cidade_destino,
            'peso_bruto': float(op.peso_bruto or 0),
            'peso_cubado': float(op.peso_cubado or 0),
            'peso_utilizado': float(op.peso_utilizado or 0),
            'valor_mercadoria': float(op.valor_mercadoria or 0),
            'tipo_entrada': op.tipo_entrada,
            'status': op.status,
            'fatura_cliente_id': op.fatura_cliente_id,
            'criado_em': str(op.criado_em) if op.criado_em else None,
            'criado_por': op.criado_por,
            'observacoes': op.observacoes,
        },
        'nfs': nfs,
        'subcontratos': subs,
    }


def listar_operacoes(status=None, cliente=None, transportadora=None, limite=20):
    """Listar operacoes com filtros"""
    from app import db
    from app.carvia.models import CarviaOperacao, CarviaSubcontrato

    query = db.session.query(CarviaOperacao)

    if status:
        query = query.filter(CarviaOperacao.status == status.upper())
    if cliente:
        query = query.filter(
            db.or_(
                CarviaOperacao.nome_cliente.ilike(f'%{cliente}%'),
                CarviaOperacao.cnpj_cliente.ilike(f'%{cliente}%'),
            )
        )
    if transportadora:
        # Filtrar operacoes que tem subcontrato com essa transportadora
        from app.transportadoras.models import Transportadora
        sub_ops = db.session.query(CarviaSubcontrato.operacao_id).join(
            Transportadora
        ).filter(
            Transportadora.razao_social.ilike(f'%{transportadora}%')
        ).distinct().subquery()
        query = query.filter(CarviaOperacao.id.in_(sub_ops))

    query = query.order_by(CarviaOperacao.id.desc()).limit(limite)
    operacoes = query.all()

    resultados = []
    for op in operacoes:
        subs_count = op.subcontratos.count()
        nfs_count = op.nfs.count()
        resultados.append({
            'id': op.id,
            'cte_numero': op.cte_numero,
            'cte_valor': float(op.cte_valor or 0),
            'cnpj_cliente': op.cnpj_cliente,
            'nome_cliente': op.nome_cliente,
            'destino': f'{op.cidade_destino}/{op.uf_destino}',
            'peso_utilizado': float(op.peso_utilizado or 0),
            'tipo_entrada': op.tipo_entrada,
            'status': op.status,
            'nfs_count': nfs_count,
            'subcontratos_count': subs_count,
            'criado_em': str(op.criado_em) if op.criado_em else None,
        })

    return {
        'sucesso': True,
        'tipo': 'lista_operacoes',
        'total': len(resultados),
        'filtros': {
            'status': status,
            'cliente': cliente,
            'transportadora': transportadora,
        },
        'operacoes': resultados,
    }


def listar_subcontratos_pendentes(limite=20):
    """Listar subcontratos que precisam de acao"""
    from app import db
    from app.carvia.models import CarviaSubcontrato, CarviaOperacao

    subs = db.session.query(CarviaSubcontrato).join(
        CarviaOperacao
    ).filter(
        CarviaSubcontrato.status.in_(['PENDENTE', 'COTADO']),
        CarviaOperacao.status != 'CANCELADO',
    ).order_by(CarviaSubcontrato.criado_em.desc()).limit(limite).all()

    resultados = []
    for sub in subs:
        op = sub.operacao
        resultados.append({
            'subcontrato_id': sub.id,
            'operacao_id': sub.operacao_id,
            'cte_carvia': op.cte_numero,
            'cliente': op.nome_cliente or op.cnpj_cliente,
            'destino': f'{op.cidade_destino}/{op.uf_destino}',
            'transportadora': sub.transportadora.razao_social if sub.transportadora else None,
            'valor_cotado': float(sub.valor_cotado or 0),
            'valor_acertado': float(sub.valor_acertado or 0) if sub.valor_acertado else None,
            'status': sub.status,
            'criado_em': str(sub.criado_em) if sub.criado_em else None,
        })

    return {
        'sucesso': True,
        'tipo': 'subcontratos_pendentes',
        'total': len(resultados),
        'subcontratos': resultados,
    }


def main():
    parser = argparse.ArgumentParser(description='Consulta operacoes CarVia')
    parser.add_argument('--resumo', action='store_true', help='Resumo geral')
    parser.add_argument('--operacao', type=int, help='Detalhe de operacao por ID')
    parser.add_argument('--status', type=str, help='Filtrar por status')
    parser.add_argument('--cliente', type=str, help='Filtrar por cliente')
    parser.add_argument('--transportadora', type=str, help='Filtrar por transportadora')
    parser.add_argument('--subcontratos-pendentes', action='store_true',
                        help='Listar subcontratos pendentes')
    parser.add_argument('--limite', type=int, default=20, help='Limite de resultados')
    args = parser.parse_args()

    from app import create_app
    app = create_app()

    with app.app_context():
        if args.resumo:
            resultado = get_resumo()
        elif args.operacao:
            resultado = get_operacao_detalhe(args.operacao)
        elif args.subcontratos_pendentes:
            resultado = listar_subcontratos_pendentes(args.limite)
        else:
            resultado = listar_operacoes(
                status=args.status,
                cliente=args.cliente,
                transportadora=args.transportadora,
                limite=args.limite,
            )

        print(json.dumps(resultado, ensure_ascii=False, indent=2, default=str))


if __name__ == '__main__':
    main()

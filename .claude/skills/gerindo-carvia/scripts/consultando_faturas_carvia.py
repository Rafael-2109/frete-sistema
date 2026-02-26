#!/usr/bin/env python3
"""
Consulta faturas CarVia (cliente e transportadora)
====================================================

Modos:
  --tipo cliente|transportadora   Tipo de fatura (obrigatorio)
  --status STATUS                 Filtrar por status
  --numero NUMERO                 Buscar fatura por numero
  --cliente NOME                  Filtrar faturas cliente por nome/CNPJ
  --transportadora NOME           Filtrar faturas transportadora por nome
  --conferencia                   Mostrar comparativo de conferencia (transportadora)
  --fatura ID                     Detalhe de fatura por ID
  --limite N                      Limite de resultados (default 20)
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))


def listar_faturas_cliente(status=None, cliente=None, numero=None, limite=20):
    """Listar faturas CarVia ao cliente"""
    from app import db
    from app.carvia.models import CarviaFaturaCliente

    query = db.session.query(CarviaFaturaCliente)

    if status:
        query = query.filter(CarviaFaturaCliente.status == status.upper())
    if cliente:
        query = query.filter(
            db.or_(
                CarviaFaturaCliente.nome_cliente.ilike(f'%{cliente}%'),
                CarviaFaturaCliente.cnpj_cliente.ilike(f'%{cliente}%'),
            )
        )
    if numero:
        query = query.filter(CarviaFaturaCliente.numero_fatura.ilike(f'%{numero}%'))

    query = query.order_by(CarviaFaturaCliente.id.desc()).limit(limite)
    faturas = query.all()

    resultados = []
    for f in faturas:
        # Contar operacoes vinculadas
        ops_count = len(f.operacoes) if hasattr(f, 'operacoes') and f.operacoes else 0
        resultados.append({
            'id': f.id,
            'numero_fatura': f.numero_fatura,
            'cnpj_cliente': f.cnpj_cliente,
            'nome_cliente': f.nome_cliente,
            'data_emissao': str(f.data_emissao) if f.data_emissao else None,
            'vencimento': str(f.vencimento) if f.vencimento else None,
            'valor_total': float(f.valor_total or 0),
            'status': f.status,
            'operacoes_count': ops_count,
            'criado_em': str(f.criado_em) if f.criado_em else None,
        })

    return {
        'sucesso': True,
        'tipo': 'faturas_cliente',
        'total': len(resultados),
        'faturas': resultados,
    }


def listar_faturas_transportadora(status=None, transportadora=None,
                                   numero=None, conferencia=False, limite=20):
    """Listar faturas de transportadora com comparativo de conferencia"""
    from app import db
    from app.carvia.models import CarviaFaturaTransportadora, CarviaSubcontrato

    query = db.session.query(CarviaFaturaTransportadora)

    if status:
        query = query.filter(
            CarviaFaturaTransportadora.status_conferencia == status.upper()
        )
    if transportadora:
        from app.transportadoras.models import Transportadora
        query = query.join(Transportadora).filter(
            Transportadora.razao_social.ilike(f'%{transportadora}%')
        )
    if numero:
        query = query.filter(
            CarviaFaturaTransportadora.numero_fatura.ilike(f'%{numero}%')
        )

    query = query.order_by(CarviaFaturaTransportadora.id.desc()).limit(limite)
    faturas = query.all()

    resultados = []
    for f in faturas:
        item = {
            'id': f.id,
            'numero_fatura': f.numero_fatura,
            'transportadora': f.transportadora.razao_social if f.transportadora else None,
            'transportadora_id': f.transportadora_id,
            'data_emissao': str(f.data_emissao) if f.data_emissao else None,
            'vencimento': str(f.vencimento) if f.vencimento else None,
            'valor_total': float(f.valor_total or 0),
            'status_conferencia': f.status_conferencia,
            'conferido_por': f.conferido_por,
            'conferido_em': str(f.conferido_em) if f.conferido_em else None,
        }

        if conferencia:
            # Calcular comparativo: valor_fatura vs soma(valor_cotado) vs soma(valor_final)
            subs = db.session.query(CarviaSubcontrato).filter(
                CarviaSubcontrato.fatura_transportadora_id == f.id
            ).all()

            soma_cotado = sum(float(s.valor_cotado or 0) for s in subs)
            soma_final = sum(float(s.valor_final or 0) for s in subs)
            valor_fatura = float(f.valor_total or 0)

            item['conferencia'] = {
                'subcontratos_count': len(subs),
                'soma_valor_cotado': round(soma_cotado, 2),
                'soma_valor_final': round(soma_final, 2),
                'valor_fatura': round(valor_fatura, 2),
                'diferenca_vs_cotado': round(valor_fatura - soma_cotado, 2),
                'diferenca_vs_final': round(valor_fatura - soma_final, 2),
                'percentual_diferenca_cotado': (
                    round((valor_fatura - soma_cotado) / soma_cotado * 100, 2)
                    if soma_cotado > 0 else None
                ),
            }
            item['subcontratos'] = [{
                'id': s.id,
                'operacao_id': s.operacao_id,
                'cte_numero': s.cte_numero,
                'valor_cotado': float(s.valor_cotado or 0),
                'valor_acertado': float(s.valor_acertado or 0) if s.valor_acertado else None,
                'valor_final': float(s.valor_final or 0),
                'status': s.status,
            } for s in subs]

        resultados.append(item)

    return {
        'sucesso': True,
        'tipo': 'faturas_transportadora',
        'total': len(resultados),
        'faturas': resultados,
    }


def detalhe_fatura(fatura_id, tipo):
    """Detalhe de uma fatura especifica"""
    from app import db

    if tipo == 'cliente':
        from app.carvia.models import CarviaFaturaCliente
        f = db.session.get(CarviaFaturaCliente, fatura_id)
        if not f:
            return {'sucesso': False, 'erro': f'Fatura cliente {fatura_id} nao encontrada'}

        ops = []
        for op in (f.operacoes or []):
            ops.append({
                'id': op.id,
                'cte_numero': op.cte_numero,
                'cte_valor': float(op.cte_valor or 0),
                'nome_cliente': op.nome_cliente,
                'destino': f'{op.cidade_destino}/{op.uf_destino}',
                'peso_utilizado': float(op.peso_utilizado or 0),
                'status': op.status,
            })

        return {
            'sucesso': True,
            'tipo': 'detalhe_fatura_cliente',
            'fatura': {
                'id': f.id,
                'numero_fatura': f.numero_fatura,
                'cnpj_cliente': f.cnpj_cliente,
                'nome_cliente': f.nome_cliente,
                'data_emissao': str(f.data_emissao) if f.data_emissao else None,
                'vencimento': str(f.vencimento) if f.vencimento else None,
                'valor_total': float(f.valor_total or 0),
                'status': f.status,
                'observacoes': f.observacoes,
            },
            'operacoes': ops,
        }
    else:
        from app.carvia.models import CarviaFaturaTransportadora, CarviaSubcontrato
        f = db.session.get(CarviaFaturaTransportadora, fatura_id)
        if not f:
            return {'sucesso': False, 'erro': f'Fatura transportadora {fatura_id} nao encontrada'}

        subs = db.session.query(CarviaSubcontrato).filter(
            CarviaSubcontrato.fatura_transportadora_id == f.id
        ).all()

        soma_cotado = sum(float(s.valor_cotado or 0) for s in subs)
        soma_final = sum(float(s.valor_final or 0) for s in subs)

        return {
            'sucesso': True,
            'tipo': 'detalhe_fatura_transportadora',
            'fatura': {
                'id': f.id,
                'numero_fatura': f.numero_fatura,
                'transportadora': f.transportadora.razao_social if f.transportadora else None,
                'data_emissao': str(f.data_emissao) if f.data_emissao else None,
                'vencimento': str(f.vencimento) if f.vencimento else None,
                'valor_total': float(f.valor_total or 0),
                'status_conferencia': f.status_conferencia,
                'conferido_por': f.conferido_por,
                'conferido_em': str(f.conferido_em) if f.conferido_em else None,
                'observacoes': f.observacoes,
            },
            'conferencia': {
                'soma_valor_cotado': round(soma_cotado, 2),
                'soma_valor_final': round(soma_final, 2),
                'diferenca_vs_fatura': round(float(f.valor_total or 0) - soma_final, 2),
            },
            'subcontratos': [{
                'id': s.id,
                'operacao_id': s.operacao_id,
                'cte_numero': s.cte_numero,
                'valor_cotado': float(s.valor_cotado or 0),
                'valor_acertado': float(s.valor_acertado or 0) if s.valor_acertado else None,
                'valor_final': float(s.valor_final or 0),
                'status': s.status,
            } for s in subs],
        }


def main():
    parser = argparse.ArgumentParser(description='Consulta faturas CarVia')
    parser.add_argument('--tipo', type=str, required=True,
                        choices=['cliente', 'transportadora'],
                        help='Tipo de fatura')
    parser.add_argument('--status', type=str, help='Filtrar por status')
    parser.add_argument('--numero', type=str, help='Buscar por numero da fatura')
    parser.add_argument('--cliente', type=str, help='Filtrar por cliente (faturas cliente)')
    parser.add_argument('--transportadora', type=str,
                        help='Filtrar por transportadora (faturas transportadora)')
    parser.add_argument('--conferencia', action='store_true',
                        help='Incluir comparativo de conferencia')
    parser.add_argument('--fatura', type=int, help='Detalhe de fatura por ID')
    parser.add_argument('--limite', type=int, default=20, help='Limite de resultados')
    args = parser.parse_args()

    from app import create_app
    app = create_app()

    with app.app_context():
        if args.fatura:
            resultado = detalhe_fatura(args.fatura, args.tipo)
        elif args.tipo == 'cliente':
            resultado = listar_faturas_cliente(
                status=args.status,
                cliente=args.cliente,
                numero=args.numero,
                limite=args.limite,
            )
        else:
            resultado = listar_faturas_transportadora(
                status=args.status,
                transportadora=args.transportadora,
                numero=args.numero,
                conferencia=args.conferencia,
                limite=args.limite,
            )

        print(json.dumps(resultado, ensure_ascii=False, indent=2, default=str))


if __name__ == '__main__':
    main()

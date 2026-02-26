#!/usr/bin/env python3
"""
Cotacao de frete para subcontrato CarVia
==========================================

Modos:
  --operacao ID --transportadora NOME   Cotar frete para operacao + transportadora
  --operacao ID --listar-opcoes         Listar transportadoras disponiveis para o destino
  --operacao ID --todas                 Cotar TODAS as transportadoras disponiveis
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))


def listar_opcoes(operacao_id):
    """Listar transportadoras disponiveis para o destino da operacao"""
    from app import db
    from app.carvia.models import CarviaOperacao
    from app.carvia.services.cotacao_service import CotacaoService

    op = db.session.get(CarviaOperacao, operacao_id)
    if not op:
        return {'sucesso': False, 'erro': f'Operacao {operacao_id} nao encontrada'}

    service = CotacaoService()
    opcoes = service.listar_opcoes_transportadora(
        uf_destino=op.uf_destino,
        cidade_destino=op.cidade_destino,
    )

    return {
        'sucesso': True,
        'tipo': 'opcoes_transportadora',
        'operacao_id': operacao_id,
        'destino': f'{op.cidade_destino}/{op.uf_destino}',
        'peso_utilizado': float(op.peso_utilizado or 0),
        'valor_mercadoria': float(op.valor_mercadoria or 0),
        'total_opcoes': len(opcoes),
        'transportadoras': opcoes,
    }


def cotar_transportadora(operacao_id, transportadora_nome):
    """Cotar frete para uma transportadora especifica"""
    from app import db
    from app.carvia.models import CarviaOperacao
    from app.carvia.services.cotacao_service import CotacaoService
    from app.transportadoras.models import Transportadora

    op = db.session.get(CarviaOperacao, operacao_id)
    if not op:
        return {'sucesso': False, 'erro': f'Operacao {operacao_id} nao encontrada'}

    # Resolver transportadora por nome
    transp = db.session.query(Transportadora).filter(
        Transportadora.razao_social.ilike(f'%{transportadora_nome}%'),
        Transportadora.ativo == True,  # noqa: E712
    ).first()

    if not transp:
        # Tentar busca mais ampla
        todas = db.session.query(Transportadora).filter(
            Transportadora.ativo == True,  # noqa: E712
            Transportadora.razao_social.ilike(f'%{transportadora_nome}%'),
        ).all()
        if len(todas) > 1:
            return {
                'sucesso': False,
                'erro': f'Multiplas transportadoras encontradas para "{transportadora_nome}"',
                'opcoes': [{'id': t.id, 'nome': t.razao_social} for t in todas],
            }
        return {
            'sucesso': False,
            'erro': f'Transportadora "{transportadora_nome}" nao encontrada',
        }

    service = CotacaoService()
    resultado = service.cotar_subcontrato(operacao_id, transp.id)

    # Enriquecer resultado com contexto
    resultado['operacao'] = {
        'id': op.id,
        'cte_numero': op.cte_numero,
        'cliente': op.nome_cliente or op.cnpj_cliente,
        'destino': f'{op.cidade_destino}/{op.uf_destino}',
        'peso_utilizado': float(op.peso_utilizado or 0),
        'valor_mercadoria': float(op.valor_mercadoria or 0),
    }
    resultado['transportadora'] = {
        'id': transp.id,
        'nome': transp.razao_social,
        'cnpj': transp.cnpj,
        'freteiro': transp.freteiro,
    }

    return resultado


def cotar_todas(operacao_id):
    """Cotar TODAS as transportadoras disponiveis e rankear"""
    from app import db
    from app.carvia.models import CarviaOperacao
    from app.carvia.services.cotacao_service import CotacaoService

    op = db.session.get(CarviaOperacao, operacao_id)
    if not op:
        return {'sucesso': False, 'erro': f'Operacao {operacao_id} nao encontrada'}

    service = CotacaoService()
    opcoes = service.listar_opcoes_transportadora(
        uf_destino=op.uf_destino,
        cidade_destino=op.cidade_destino,
    )

    if not opcoes:
        return {
            'sucesso': False,
            'erro': f'Nenhuma transportadora com tabela ativa para {op.uf_destino}',
        }

    cotacoes = []
    for t in opcoes:
        resultado = service.cotar_subcontrato(operacao_id, t['id'])
        cotacoes.append({
            'transportadora_id': t['id'],
            'transportadora': t['nome'],
            'freteiro': t['freteiro'],
            'sucesso': resultado.get('sucesso', False),
            'valor_cotado': resultado.get('valor_cotado'),
            'tabela_frete_id': resultado.get('tabela_frete_id'),
            'tabela_nome': resultado.get('tabela_nome'),
            'erro': resultado.get('erro'),
        })

    # Ordenar por valor (menor primeiro), erros no final
    cotacoes.sort(key=lambda x: (
        0 if x['sucesso'] else 1,
        x.get('valor_cotado') or float('inf'),
    ))

    return {
        'sucesso': True,
        'tipo': 'cotacao_ranking',
        'operacao': {
            'id': op.id,
            'cte_numero': op.cte_numero,
            'cliente': op.nome_cliente or op.cnpj_cliente,
            'destino': f'{op.cidade_destino}/{op.uf_destino}',
            'peso_utilizado': float(op.peso_utilizado or 0),
            'valor_mercadoria': float(op.valor_mercadoria or 0),
        },
        'total_cotadas': len(cotacoes),
        'cotacoes': cotacoes,
    }


def main():
    parser = argparse.ArgumentParser(description='Cotacao subcontrato CarVia')
    parser.add_argument('--operacao', type=int, required=True,
                        help='ID da operacao CarVia')
    parser.add_argument('--transportadora', type=str,
                        help='Nome da transportadora para cotar')
    parser.add_argument('--listar-opcoes', action='store_true',
                        help='Listar transportadoras disponiveis')
    parser.add_argument('--todas', action='store_true',
                        help='Cotar TODAS as transportadoras disponiveis')
    args = parser.parse_args()

    from app import create_app
    app = create_app()

    with app.app_context():
        if args.listar_opcoes:
            resultado = listar_opcoes(args.operacao)
        elif args.todas:
            resultado = cotar_todas(args.operacao)
        elif args.transportadora:
            resultado = cotar_transportadora(args.operacao, args.transportadora)
        else:
            parser.error('Informe --transportadora, --listar-opcoes ou --todas')
            return

        print(json.dumps(resultado, ensure_ascii=False, indent=2, default=str))


if __name__ == '__main__':
    main()

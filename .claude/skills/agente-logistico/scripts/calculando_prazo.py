#!/usr/bin/env python3
"""
Script: calculando_prazo.py
Queries cobertas: Q7

Calcula data de entrega baseada em lead time de transportadoras.

Uso:
    --pedido VCD123 --data-embarque amanha    # Q7: Previsao de entrega
    --pedido "atacadao 183" --data-embarque hoje
"""
import sys
import os
import json
import argparse
from datetime import date, datetime, timedelta
from decimal import Decimal

# Adicionar path do projeto
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))

# Importar modulo centralizado de resolucao de entidades
from resolver_entidades import (
    resolver_pedido,
    formatar_sugestao_pedido
)


def decimal_default(obj):
    """Serializa Decimal para JSON"""
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def parse_data(data_str: str) -> date:
    """Converte string de data para date object"""
    if data_str.lower() in ['hoje', 'today']:
        return date.today()
    elif data_str.lower() in ['amanha', 'tomorrow']:
        return date.today() + timedelta(days=1)
    else:
        for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y']:
            try:
                return datetime.strptime(data_str, fmt).date()
            except ValueError:
                continue
        raise ValueError(f"Formato de data invalido: {data_str}")


def calcular_prazo(args):
    """
    Query 7: Se embarcar o pedido X em data Y, quando chega no cliente?
    """
    from app.vinculos.models import CidadeAtendida
    from app.transportadoras.models import Transportadora
    from app.localidades.models import Cidade
    from app import db

    resultado = {
        'sucesso': True,
        'pedido': None,
        'data_embarque': None,
        'opcoes_entrega': [],
        'resumo': {}
    }

    # Usar resolver_pedido centralizado (busca flexivel)
    itens, num_pedido, info_busca = resolver_pedido(args.pedido, fonte='ambos')

    if not itens:
        resultado['sucesso'] = False
        resultado['erro'] = f"Pedido '{args.pedido}' nao encontrado"
        resultado['sugestao'] = formatar_sugestao_pedido(info_busca)
        resultado['estrategia_busca'] = info_busca.get('estrategia')
        return resultado

    # Extrair dados do primeiro item
    primeiro_item = itens[0]
    pedido = {
        'num_pedido': num_pedido,
        'cliente': primeiro_item.raz_social_red,
        'cidade': primeiro_item.nome_cidade,
        'uf': primeiro_item.cod_uf,
        'cnpj': primeiro_item.cnpj_cpf
    }

    resultado['pedido'] = pedido

    # Incluir metadados da busca
    resultado['busca'] = {
        'estrategia': info_busca.get('estrategia'),
        'multiplos_encontrados': info_busca.get('multiplos_encontrados', False)
    }
    if info_busca.get('pedidos_candidatos'):
        resultado['busca']['outros_candidatos'] = info_busca['pedidos_candidatos']

    # Parsear data de embarque
    try:
        data_embarque = parse_data(args.data_embarque)
        resultado['data_embarque'] = data_embarque.isoformat()
    except ValueError as e:
        resultado['sucesso'] = False
        resultado['erro'] = str(e)
        return resultado

    # Buscar opcoes de entrega (transportadoras + lead time)
    cidade = pedido['cidade']
    uf = pedido['uf']

    # Buscar cidade atendida via JOIN com Cidade
    cidades_atendidas = db.session.query(CidadeAtendida).join(
        Cidade, CidadeAtendida.cidade_id == Cidade.id
    ).filter(
        Cidade.nome.ilike(f'%{cidade}%') if cidade else True,
        CidadeAtendida.uf == uf
    ).all()

    if not cidades_atendidas:
        # Tentar buscar apenas por UF (mais generico)
        cidades_atendidas = CidadeAtendida.query.filter(
            CidadeAtendida.uf == uf
        ).limit(5).all()

    opcoes = []
    for ca in cidades_atendidas:
        lead_time = ca.lead_time or 0
        data_entrega = data_embarque + timedelta(days=lead_time)

        # Buscar nome da transportadora
        transportadora = Transportadora.query.get(ca.transportadora_id) if ca.transportadora_id else None
        nome_transp = transportadora.razao_social if transportadora else f"Transportadora #{ca.transportadora_id}"

        # Buscar nome da cidade via relacionamento
        nome_cidade = ca.cidade.nome if ca.cidade else "Cidade desconhecida"

        opcoes.append({
            'transportadora': nome_transp,
            'transportadora_id': ca.transportadora_id,
            'lead_time_dias': lead_time,
            'data_entrega': data_entrega.isoformat(),
            'cidade_atendida': nome_cidade
        })

    # Ordenar por lead time (mais rapido primeiro)
    opcoes.sort(key=lambda x: x['lead_time_dias'])

    resultado['opcoes_entrega'] = opcoes[:args.limit]

    # Resumo
    if opcoes:
        mais_rapida = opcoes[0]
        resultado['resumo'] = {
            'total_opcoes': len(opcoes),
            'opcao_mais_rapida': mais_rapida['transportadora'],
            'data_entrega_rapida': mais_rapida['data_entrega'],
            'mensagem': f"Embarque em {data_embarque.isoformat()} -> Entrega mais rapida: {mais_rapida['data_entrega']} ({mais_rapida['transportadora']}, {mais_rapida['lead_time_dias']} dias)"
        }
    else:
        resultado['resumo'] = {
            'total_opcoes': 0,
            'mensagem': f"Nenhuma transportadora encontrada para {cidade}/{uf}"
        }

    return resultado


def main():
    from app import create_app

    parser = argparse.ArgumentParser(
        description='Calcular prazo de entrega para um pedido (Q7)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python calculando_prazo.py --pedido VCD123 --data-embarque amanha
  python calculando_prazo.py --pedido "atacadao 183" --data-embarque hoje
        """
    )
    parser.add_argument('--pedido', required=True, help='Numero do pedido ou termo de busca')
    parser.add_argument('--data-embarque', required=True, help='Data de embarque (hoje, amanha, ou YYYY-MM-DD)')
    parser.add_argument('--limit', type=int, default=5, help='Limite de opcoes (default: 5)')

    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        resultado = calcular_prazo(args)
        print(json.dumps(resultado, ensure_ascii=False, indent=2, default=decimal_default))


if __name__ == '__main__':
    main()

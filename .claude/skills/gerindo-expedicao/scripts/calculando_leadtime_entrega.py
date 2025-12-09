#!/usr/bin/env python3
"""
Script: calculando_leadtime_entrega.py
Queries cobertas: Q7 + CALCULO REVERSO

Calcula data de entrega baseada em lead time de transportadoras.
NOVO: Calcula data de expedicao sugerida dado uma data de entrega desejada.

Uso:
    --pedido VCD123 --data-embarque amanha       # Q7: Previsao de entrega
    --pedido "atacadao 183" --data-embarque hoje # Q7: Busca flexivel
    --pedido VCD123 --data-entrega 25/12         # ⭐ NOVO: Quando embarcar para chegar dia 25/12?
    --cidade "Sao Paulo" --uf SP --data-entrega 25/12  # Calculo sem pedido
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


def calcular_expedicao_sugerida(args):
    """
    NOVO: Dado uma data de entrega desejada, calcula quando deve embarcar.
    Calculo reverso: data_expedicao = data_entrega - lead_time

    Pode ser usado com:
    - --pedido VCD123 --data-entrega 25/12
    - --cidade "Sao Paulo" --uf SP --data-entrega 25/12
    """
    from app.vinculos.models import CidadeAtendida
    from app.transportadoras.models import Transportadora
    from app.localidades.models import Cidade
    from app import db

    resultado = {
        'sucesso': True,
        'tipo_analise': 'CALCULO_EXPEDICAO_SUGERIDA',
        'destino': None,
        'data_entrega_desejada': None,
        'opcoes_expedicao': [],
        'resumo': {}
    }

    # Determinar destino (cidade/uf)
    cidade = None
    uf = None

    if args.pedido:
        # Buscar destino do pedido
        itens, num_pedido, info_busca = resolver_pedido(args.pedido, fonte='ambos')

        if not itens:
            resultado['sucesso'] = False
            resultado['erro'] = f"Pedido '{args.pedido}' nao encontrado"
            resultado['sugestao'] = formatar_sugestao_pedido(info_busca)
            return resultado

        primeiro_item = itens[0]
        cidade = primeiro_item.nome_cidade
        uf = primeiro_item.cod_uf

        # Extrair data de entrega do pedido se existir e nao foi informada
        data_entrega_pedido = None
        if hasattr(primeiro_item, 'data_entrega_pedido') and primeiro_item.data_entrega_pedido:
            data_entrega_pedido = primeiro_item.data_entrega_pedido

        resultado['pedido'] = {
            'num_pedido': num_pedido,
            'cliente': primeiro_item.raz_social_red,
            'cidade': cidade,
            'uf': uf,
            'data_entrega_pedido': data_entrega_pedido.isoformat() if data_entrega_pedido else None
        }

        # Se nao informou data_entrega, usa a do pedido
        if not args.data_entrega and data_entrega_pedido:
            args.data_entrega = data_entrega_pedido.isoformat()

    elif args.cidade and args.uf:
        cidade = args.cidade
        uf = args.uf.upper()
    else:
        resultado['sucesso'] = False
        resultado['erro'] = 'Informe --pedido ou --cidade com --uf'
        return resultado

    resultado['destino'] = {
        'cidade': cidade,
        'uf': uf
    }

    # Parsear data de entrega desejada
    if not args.data_entrega:
        resultado['sucesso'] = False
        resultado['erro'] = 'Informe --data-entrega (data de entrega desejada)'
        return resultado

    try:
        data_entrega_desejada = parse_data(args.data_entrega)
        resultado['data_entrega_desejada'] = data_entrega_desejada.isoformat()
    except ValueError as e:
        resultado['sucesso'] = False
        resultado['erro'] = str(e)
        return resultado

    hoje = date.today()

    # Buscar transportadoras que atendem o destino
    cidades_atendidas = db.session.query(CidadeAtendida).join(
        Cidade, CidadeAtendida.cidade_id == Cidade.id
    ).filter(
        Cidade.nome.ilike(f'%{cidade}%') if cidade else True,
        CidadeAtendida.uf == uf
    ).all()

    if not cidades_atendidas:
        cidades_atendidas = CidadeAtendida.query.filter(
            CidadeAtendida.uf == uf
        ).limit(10).all()

    if not cidades_atendidas:
        resultado['resumo'] = {
            'total_opcoes': 0,
            'mensagem': f"Nenhuma transportadora encontrada para {cidade}/{uf}"
        }
        return resultado

    opcoes = []
    for ca in cidades_atendidas:
        lead_time = ca.lead_time or 0
        # CALCULO REVERSO: data_expedicao = data_entrega - lead_time
        data_expedicao_sugerida = data_entrega_desejada - timedelta(days=lead_time)

        # Verificar se a data de expedicao eh valida (nao pode ser no passado)
        dias_ate_expedicao = (data_expedicao_sugerida - hoje).days
        status = 'OK'
        if dias_ate_expedicao < 0:
            status = 'ATRASADO'  # Ja passou a data
        elif dias_ate_expedicao == 0:
            status = 'URGENTE'  # Precisa embarcar hoje
        elif dias_ate_expedicao <= 2:
            status = 'ATENCAO'  # Poucos dias

        # Buscar nome da transportadora
        transportadora = Transportadora.query.get(ca.transportadora_id) if ca.transportadora_id else None
        nome_transp = transportadora.razao_social if transportadora else f"Transportadora #{ca.transportadora_id}"
        modalidade = getattr(ca, 'modalidade', None)

        nome_cidade = ca.cidade.nome if ca.cidade else "Cidade desconhecida"

        opcoes.append({
            'transportadora': nome_transp,
            'transportadora_id': ca.transportadora_id,
            'modalidade': modalidade,
            'lead_time_dias': lead_time,
            'data_expedicao_sugerida': data_expedicao_sugerida.isoformat(),
            'dias_ate_expedicao': dias_ate_expedicao,
            'status': status,
            'data_entrega_calculada': data_entrega_desejada.isoformat(),
            'cidade_atendida': nome_cidade
        })

    # Ordenar: primeiro os OK, depois por dias_ate_expedicao
    opcoes.sort(key=lambda x: (0 if x['status'] == 'OK' else (1 if x['status'] == 'ATENCAO' else (2 if x['status'] == 'URGENTE' else 3)), -x['dias_ate_expedicao']))

    resultado['opcoes_expedicao'] = opcoes[:args.limit]

    # Resumo
    opcoes_viaveis = [o for o in opcoes if o['status'] in ('OK', 'ATENCAO', 'URGENTE')]
    if opcoes_viaveis:
        melhor = opcoes_viaveis[0]
        msg_linhas = [f"Para entregar em {data_entrega_desejada.strftime('%d/%m/%Y')} em {cidade}/{uf}:"]
        msg_linhas.append(f"  Melhor opcao: embarcar em {melhor['data_expedicao_sugerida']} ({melhor['transportadora']}, {melhor['lead_time_dias']} dias)")
        if melhor['status'] == 'URGENTE':
            msg_linhas.append(f"  ⚠️ URGENTE: Precisa embarcar HOJE!")
        elif melhor['status'] == 'ATENCAO':
            msg_linhas.append(f"  ⚡ ATENCAO: Apenas {melhor['dias_ate_expedicao']} dia(s) para embarcar")
        resultado['resumo'] = {
            'total_opcoes': len(opcoes),
            'opcoes_viaveis': len(opcoes_viaveis),
            'melhor_opcao': {
                'transportadora': melhor['transportadora'],
                'data_expedicao': melhor['data_expedicao_sugerida'],
                'lead_time': melhor['lead_time_dias']
            },
            'mensagem': '\n'.join(msg_linhas)
        }
    else:
        resultado['resumo'] = {
            'total_opcoes': len(opcoes),
            'opcoes_viaveis': 0,
            'mensagem': f"⚠️ IMPOSSIVEL: Todas as opcoes ja passaram a data limite para embarque. Nao eh possivel entregar em {data_entrega_desejada.strftime('%d/%m/%Y')}."
        }

    return resultado


def calcular_leadtime_entrega(args):
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
        description='Calcular prazo de entrega ou data de expedicao sugerida',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  # Q7: Previsao de entrega (embarque -> entrega)
  python calculando_leadtime_entrega.py --pedido VCD123 --data-embarque amanha
  python calculando_leadtime_entrega.py --pedido "atacadao 183" --data-embarque hoje

  # ⭐ NOVO: Calculo reverso (entrega -> embarque)
  python calculando_leadtime_entrega.py --pedido VCD123 --data-entrega 25/12
  python calculando_leadtime_entrega.py --pedido VCD123                         # Usa data_entrega_pedido
  python calculando_leadtime_entrega.py --cidade "Sao Paulo" --uf SP --data-entrega 25/12
        """
    )
    # Argumentos de identificacao
    parser.add_argument('--pedido', help='Numero do pedido ou termo de busca')
    parser.add_argument('--cidade', help='Nome da cidade de destino (alternativa ao pedido)')
    parser.add_argument('--uf', help='UF de destino (requerido se usar --cidade)')

    # Argumentos de data (mutuamente exclusivos para determinar modo)
    parser.add_argument('--data-embarque', dest='data_embarque', help='Data de embarque (calcula entrega)')
    parser.add_argument('--data-entrega', dest='data_entrega', help='Data de entrega desejada (calcula embarque)')

    parser.add_argument('--limit', type=int, default=10, help='Limite de opcoes (default: 10)')

    args = parser.parse_args()

    # Validacao
    if not args.pedido and not (args.cidade and args.uf):
        print(json.dumps({
            'sucesso': False,
            'erro': 'Informe --pedido ou --cidade com --uf'
        }, ensure_ascii=False, indent=2))
        return

    if args.data_embarque and args.data_entrega:
        print(json.dumps({
            'sucesso': False,
            'erro': 'Informe apenas --data-embarque OU --data-entrega, nao ambos'
        }, ensure_ascii=False, indent=2))
        return

    app = create_app()
    with app.app_context():
        # Determinar qual funcao usar
        if args.data_entrega:
            resultado = calcular_expedicao_sugerida(args)
        elif args.data_embarque:
            resultado = calcular_leadtime_entrega(args)
        elif args.pedido:
            # Se so informou pedido, tenta usar data_entrega_pedido para calculo reverso
            args.data_entrega = None  # Sera preenchido pela funcao se existir no pedido
            resultado = calcular_expedicao_sugerida(args)
        else:
            resultado = {
                'sucesso': False,
                'erro': 'Informe --data-embarque (para previsao de entrega) ou --data-entrega (para sugestao de embarque)'
            }

        print(json.dumps(resultado, ensure_ascii=False, indent=2, default=decimal_default))


if __name__ == '__main__':
    main()

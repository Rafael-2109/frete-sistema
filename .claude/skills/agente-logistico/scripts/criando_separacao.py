#!/usr/bin/env python3
"""
Script: criando_separacao.py
Acao: Cria separacoes de pedidos via linguagem natural.

SEMPRE executar primeiro SEM --executar para validar!

Uso:
    --pedido VCD123 --expedicao 2025-12-20 --tipo completa
    --pedido VCD123 --expedicao amanha --pallets 28
    --pedido VCD123 --expedicao 20/12 --pallets 28 --pallets-inteiros
    --pedido VCD123 --expedicao amanha --apenas-estoque
    --pedido VCD123 --expedicao amanha --excluir-produtos '["KETCHUP","MOSTARDA"]'
    --pedido VCD123 --expedicao amanha --agendamento 22/12 --protocolo AG123 --agendamento-confirmado
    --pedido VCD123 --expedicao amanha --tipo completa --executar  # EFETIVAMENTE CRIA
"""
import sys
import os
import json
import argparse
import math
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_DOWN

# Adicionar path do projeto
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))

# Importar modulo centralizado de resolucao de entidades
from resolver_entidades import resolver_pedido, formatar_sugestao_pedido


def decimal_default(obj):
    """Serializa Decimal para JSON"""
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def parse_data_natural(termo: str) -> date:
    """
    Interpreta termo de data em linguagem natural ou formato brasileiro.

    Formatos aceitos:
    - "hoje" -> date.today()
    - "amanha" ou "amanha" -> date.today() + 1 dia
    - "dd/mm/yyyy" -> data completa
    - "dd/mm" -> assume ano atual
    - "yyyy-mm-dd" -> formato ISO
    """
    if not termo:
        return None

    termo = termo.strip().lower()
    hoje = date.today()

    # Termos naturais
    if termo in ('hoje', 'today'):
        return hoje
    if termo in ('amanha', 'amanhã', 'tomorrow'):
        return hoje + timedelta(days=1)

    # Formato ISO (yyyy-mm-dd)
    if '-' in termo and len(termo.split('-')[0]) == 4:
        try:
            partes = termo.split('-')
            return date(int(partes[0]), int(partes[1]), int(partes[2]))
        except (ValueError, IndexError):
            pass

    # Formatos com barra (dd/mm/yyyy, dd/mm)
    partes = termo.replace('-', '/').split('/')

    try:
        if len(partes) == 3:
            dia, mes, ano = int(partes[0]), int(partes[1]), int(partes[2])
            if ano < 100:
                ano += 2000
            return date(ano, mes, dia)
        elif len(partes) == 2:
            dia, mes = int(partes[0]), int(partes[1])
            return date(hoje.year, mes, dia)
        elif len(partes) == 1 and partes[0].isdigit():
            dia = int(partes[0])
            return date(hoje.year, hoje.month, dia)
    except (ValueError, TypeError):
        pass

    raise ValueError(f"Nao foi possivel interpretar a data: {termo}")


def criar_app_context():
    """Cria contexto Flask para acesso ao banco"""
    from app import create_app
    app = create_app()
    return app.app_context()


def verificar_agendamento(cnpj: str) -> dict:
    """
    Verifica se cliente exige agendamento.

    Returns:
        dict com:
        - exige_agendamento: bool
        - forma: str (Portal, Telefone, E-mail, WhatsApp, SEM AGENDAMENTO)
        - contato: str
        - observacao: str
    """
    from app.cadastros_agendamento.models import ContatoAgendamento

    # Normalizar CNPJ (remover formatacao para busca)
    cnpj_limpo = ''.join(c for c in cnpj if c.isdigit())

    # Buscar na tabela contatos_agendamento
    # Tentar com CNPJ formatado primeiro, depois sem formatacao
    contato = ContatoAgendamento.query.filter_by(cnpj=cnpj).first()
    if not contato:
        # Tentar busca parcial
        contato = ContatoAgendamento.query.filter(
            ContatoAgendamento.cnpj.like(f'%{cnpj_limpo[:8]}%')
        ).first()

    if not contato:
        return {
            'exige_agendamento': False,
            'forma': None,
            'contato': None,
            'observacao': None,
            'mensagem': 'Pelo cadastro, este cliente nao precisa de agendamento'
        }

    # Verificar se forma indica que NAO precisa
    if not contato.forma or contato.forma.upper() == 'SEM AGENDAMENTO':
        return {
            'exige_agendamento': False,
            'forma': contato.forma,
            'contato': contato.contato,
            'observacao': contato.observacao,
            'mensagem': 'Pelo cadastro, este cliente nao precisa de agendamento'
        }

    return {
        'exige_agendamento': True,
        'forma': contato.forma,
        'contato': contato.contato,
        'observacao': contato.observacao,
        'mensagem': f'Este cliente EXIGE agendamento via {contato.forma}. Preciso de: data agendamento, protocolo, confirmacao.'
    }


def buscar_itens_carteira(num_pedido: str) -> list:
    """Busca todos os itens do pedido na carteira com saldo > 0"""
    from app.carteira.models import CarteiraPrincipal

    itens = CarteiraPrincipal.query.filter(
        CarteiraPrincipal.num_pedido == num_pedido,
        CarteiraPrincipal.ativo == True,
        CarteiraPrincipal.qtd_saldo_produto_pedido >= 0.001
    ).all()

    return itens


def verificar_separacao_existente(num_pedido: str) -> dict:
    """Verifica se ja existe separacao para o pedido"""
    from app.separacao.models import Separacao

    separacao = Separacao.query.filter(
        Separacao.num_pedido == num_pedido,
        Separacao.sincronizado_nf == False
    ).first()

    if separacao:
        return {
            'existe': True,
            'lote_id': separacao.separacao_lote_id,
            'mensagem': f'Este pedido ja possui separacao no lote {separacao.separacao_lote_id}'
        }

    return {'existe': False, 'lote_id': None, 'mensagem': None}


def calcular_estoque_disponivel(cod_produto: str) -> float:
    """Calcula estoque disponivel (atual - separacoes nao faturadas)"""
    from app.estoque.services.estoque_simples import ServicoEstoqueSimples
    from app.separacao.models import Separacao
    from sqlalchemy import func
    from app import db

    # Estoque atual
    estoque_atual = ServicoEstoqueSimples.calcular_estoque_atual(cod_produto)

    # Separacoes nao faturadas
    separado = db.session.query(
        func.sum(Separacao.qtd_saldo)
    ).filter(
        Separacao.cod_produto == cod_produto,
        Separacao.sincronizado_nf == False
    ).scalar() or 0

    return float(estoque_atual) - float(separado)


def buscar_palletizacao(cod_produto: str) -> dict:
    """Busca dados de palletizacao do produto"""
    from app.producao.models import CadastroPalletizacao

    pallet = CadastroPalletizacao.query.filter_by(
        cod_produto=cod_produto,
        ativo=True
    ).first()

    if pallet:
        return {
            'palletizacao': float(pallet.palletizacao or 1),
            'peso_bruto': float(pallet.peso_bruto or 0)
        }

    return {'palletizacao': 100, 'peso_bruto': 1.0}


def calcular_rota_subrota(item_carteira) -> tuple:
    """Calcula rota e sub-rota baseado no item da carteira"""
    from app.carteira.utils.separacao_utils import buscar_rota_por_uf, buscar_sub_rota_por_uf_cidade

    # Verificar incoterm (RED/FOB)
    if hasattr(item_carteira, 'incoterm') and item_carteira.incoterm in ['RED', 'FOB']:
        rota = item_carteira.incoterm
    else:
        rota = buscar_rota_por_uf(item_carteira.cod_uf or 'SP')

    sub_rota = buscar_sub_rota_por_uf_cidade(
        item_carteira.cod_uf or '',
        item_carteira.nome_cidade or ''
    )

    return rota, sub_rota


def distribuir_pallets_inteiros(itens: list, total_pallets: int) -> list:
    """
    Distribui pallets inteiros entre os itens.
    Prioriza itens com maior palletizacao (menos unidades por pallet).

    Returns:
        Lista de dicts com {cod_produto, pallets, quantidade}
    """
    # Ordenar por palletizacao (menor primeiro = mais unidades por pallet)
    itens_ordenados = sorted(itens, key=lambda x: x['palletizacao'])

    resultado = []
    pallets_restantes = total_pallets

    for item in itens_ordenados:
        if pallets_restantes <= 0:
            break

        # Quantos pallets completos cabem neste item?
        pallets_maximos_item = math.floor(item['qtd_disponivel'] / item['palletizacao'])
        pallets_item = min(pallets_maximos_item, pallets_restantes)

        if pallets_item > 0:
            qtd = pallets_item * item['palletizacao']
            resultado.append({
                'cod_produto': item['cod_produto'],
                'nome_produto': item['nome_produto'],
                'pallets': pallets_item,
                'quantidade': qtd,
                'palletizacao': item['palletizacao']
            })
            pallets_restantes -= pallets_item

    return resultado


def distribuir_pallets_proporcional(itens: list, total_pallets: float, inteiros: bool = False) -> list:
    """
    Distribui pallets proporcionalmente ao valor de cada item.

    Args:
        itens: Lista de itens com valor, qtd, palletizacao
        total_pallets: Total de pallets desejado
        inteiros: Se True, arredonda cada item para pallets inteiros

    Returns:
        Lista de dicts com {cod_produto, pallets, quantidade}
    """
    # Calcular valor total
    valor_total = sum(item['valor_total'] for item in itens)
    if valor_total == 0:
        valor_total = 1  # Evitar divisao por zero

    resultado = []
    pallets_alocados = 0

    # Se inteiros, ordenar por pallet maximo (descendente) para priorizar itens com mais estoque
    itens_ordenados = itens if not inteiros else sorted(
        itens,
        key=lambda x: x['qtd_disponivel'] / x['palletizacao'],
        reverse=True
    )

    pallets_restantes = total_pallets

    for i, item in enumerate(itens_ordenados):
        # Proporcao do item
        proporcao = item['valor_total'] / valor_total
        pallets_item = total_pallets * proporcao

        if inteiros:
            # Para inteiros, usar o minimo entre: proporcao arredondada para baixo OU o restante
            pallets_item_floor = math.floor(pallets_item)
            # Se nenhum item conseguiu 1 pallet, tentar dar 1 pallet ao item com mais estoque
            if pallets_item_floor == 0 and i == 0 and pallets_restantes >= 1:
                pallets_item = 1
            else:
                pallets_item = pallets_item_floor

        # Verificar se nao excede quantidade disponivel
        pallets_max = item['qtd_disponivel'] / item['palletizacao']
        pallets_item = min(pallets_item, pallets_max, pallets_restantes if inteiros else float('inf'))

        if inteiros:
            pallets_item = math.floor(pallets_item)

        if pallets_item > 0:
            if inteiros:
                qtd = int(pallets_item) * item['palletizacao']
            else:
                qtd = pallets_item * item['palletizacao']

            resultado.append({
                'cod_produto': item['cod_produto'],
                'nome_produto': item['nome_produto'],
                'pallets': round(pallets_item, 2),
                'quantidade': round(qtd, 3),
                'palletizacao': item['palletizacao']
            })
            pallets_alocados += pallets_item
            if inteiros:
                pallets_restantes -= pallets_item

    return resultado


def simular_separacao(
    num_pedido: str,
    data_expedicao: date,
    tipo: str = 'completa',
    total_pallets: float = None,
    pallets_inteiros: bool = False,
    apenas_estoque: bool = False,
    excluir_produtos: list = None,
    agendamento: date = None,
    protocolo: str = None,
    agendamento_confirmado: bool = False
) -> dict:
    """
    Simula a criacao de uma separacao sem efetivamente criar.

    Returns:
        dict com:
        - success: bool
        - itens: lista de itens que seriam criados
        - alertas_estoque: lista de alertas de falta
        - info_agendamento: info sobre necessidade de agendamento
        - totais: valor, peso, pallets
    """
    from app.utils.text_utils import truncar_observacao

    # Buscar itens da carteira
    itens_carteira = buscar_itens_carteira(num_pedido)

    if not itens_carteira:
        return {
            'success': False,
            'error': f'Nenhum item com saldo encontrado para o pedido {num_pedido}'
        }

    # Verificar se ja existe separacao
    sep_existente = verificar_separacao_existente(num_pedido)
    if sep_existente['existe']:
        return {
            'success': False,
            'error': sep_existente['mensagem'],
            'lote_existente': sep_existente['lote_id']
        }

    # Verificar agendamento
    cnpj = itens_carteira[0].cnpj_cpf
    info_agendamento = verificar_agendamento(cnpj)

    # Preparar itens para processamento
    itens_processados = []
    alertas_estoque = []

    for item in itens_carteira:
        # Verificar exclusao
        if excluir_produtos:
            excluir = False
            for termo in excluir_produtos:
                termo_upper = termo.upper()
                if (item.cod_produto.upper() == termo_upper or
                    termo_upper in item.nome_produto.upper()):
                    excluir = True
                    break
            if excluir:
                continue

        # Buscar dados de palletizacao
        pallet_info = buscar_palletizacao(item.cod_produto)

        # Calcular estoque disponivel
        estoque_disp = calcular_estoque_disponivel(item.cod_produto)

        # Quantidade desejada
        qtd_desejada = float(item.qtd_saldo_produto_pedido)

        # Ajustar para estoque se necessario
        if apenas_estoque:
            qtd_final = min(qtd_desejada, max(0, estoque_disp))
        else:
            qtd_final = qtd_desejada
            if estoque_disp < qtd_desejada:
                alertas_estoque.append({
                    'cod_produto': item.cod_produto,
                    'nome_produto': item.nome_produto,
                    'quantidade_solicitada': qtd_desejada,
                    'estoque_disponivel': estoque_disp,
                    'falta': qtd_desejada - estoque_disp
                })

        if qtd_final > 0:
            # Calcular rota
            rota, sub_rota = calcular_rota_subrota(item)

            itens_processados.append({
                'cod_produto': item.cod_produto,
                'nome_produto': item.nome_produto,
                'qtd_disponivel': qtd_final,
                'qtd_original': qtd_desejada,
                'valor_unitario': float(item.preco_produto_pedido or 0),
                'valor_total': qtd_final * float(item.preco_produto_pedido or 0),
                'palletizacao': pallet_info['palletizacao'],
                'peso_bruto': pallet_info['peso_bruto'],
                'estoque_disponivel': estoque_disp,
                'rota': rota,
                'sub_rota': sub_rota,
                'observacoes': truncar_observacao(item.observ_ped_1),
                # Dados do cliente (do primeiro item)
                'cnpj_cpf': item.cnpj_cpf,
                'raz_social_red': item.raz_social_red,
                'nome_cidade': item.nome_cidade,
                'cod_uf': item.cod_uf,
                'data_pedido': item.data_pedido,
                'pedido_cliente': item.pedido_cliente
            })

    if not itens_processados:
        return {
            'success': False,
            'error': 'Nenhum item restante apos filtros aplicados'
        }

    # Aplicar logica de pallets se especificado
    itens_finais = []

    if total_pallets:
        if pallets_inteiros:
            # Distribuir em pallets inteiros
            distribuicao = distribuir_pallets_proporcional(
                itens_processados,
                total_pallets,
                inteiros=True
            )
        else:
            # Distribuir proporcionalmente (permite fracionado)
            distribuicao = distribuir_pallets_proporcional(
                itens_processados,
                total_pallets,
                inteiros=False
            )

        # Mesclar distribuicao com dados completos
        for dist in distribuicao:
            # Encontrar item original
            item_orig = next(
                (i for i in itens_processados if i['cod_produto'] == dist['cod_produto']),
                None
            )
            if item_orig:
                item_final = item_orig.copy()
                item_final['quantidade'] = dist['quantidade']
                item_final['pallets'] = dist['pallets']
                item_final['peso'] = dist['quantidade'] * item_orig['peso_bruto']
                item_final['valor'] = dist['quantidade'] * item_orig['valor_unitario']
                itens_finais.append(item_final)
    else:
        # Separacao completa ou parcial padrao
        for item in itens_processados:
            item_final = item.copy()
            item_final['quantidade'] = item['qtd_disponivel']
            item_final['pallets'] = round(item['qtd_disponivel'] / item['palletizacao'], 2)
            item_final['peso'] = item['qtd_disponivel'] * item['peso_bruto']
            item_final['valor'] = item['qtd_disponivel'] * item['valor_unitario']
            itens_finais.append(item_final)

    # Calcular totais
    valor_total = sum(i['valor'] for i in itens_finais)
    peso_total = sum(i['peso'] for i in itens_finais)
    pallet_total = sum(i['pallets'] for i in itens_finais)

    # Determinar tipo de envio
    todos_itens = len(itens_finais) == len(itens_carteira)
    todas_qtds = all(
        abs(i['quantidade'] - i['qtd_original']) < 0.01
        for i in itens_finais
    )
    tipo_envio = 'total' if (todos_itens and todas_qtds) else 'parcial'

    return {
        'success': True,
        'num_pedido': num_pedido,
        'cliente': itens_finais[0]['raz_social_red'] if itens_finais else None,
        'cnpj': itens_finais[0]['cnpj_cpf'] if itens_finais else None,
        'data_expedicao': data_expedicao.isoformat(),
        'agendamento': agendamento.isoformat() if agendamento else None,
        'protocolo': protocolo,
        'agendamento_confirmado': agendamento_confirmado,
        'tipo_envio': tipo_envio,
        'itens': itens_finais,
        'alertas_estoque': alertas_estoque,
        'info_agendamento': info_agendamento,
        'totais': {
            'valor': round(valor_total, 2),
            'peso': round(peso_total, 2),
            'pallets': round(pallet_total, 2),
            'qtd_itens': len(itens_finais)
        }
    }


def executar_separacao(simulacao: dict) -> dict:
    """
    Executa efetivamente a criacao da separacao.

    Args:
        simulacao: Resultado da funcao simular_separacao

    Returns:
        dict com resultado da criacao
    """
    from app import db
    from app.separacao.models import Separacao
    from app.utils.lote_utils import gerar_lote_id
    from app.utils.timezone import agora_brasil
    from datetime import datetime

    if not simulacao.get('success'):
        return simulacao

    # Gerar lote ID
    lote_id = gerar_lote_id()

    # Converter datas
    data_expedicao = datetime.strptime(simulacao['data_expedicao'], '%Y-%m-%d').date()
    data_agendamento = None
    if simulacao.get('agendamento'):
        data_agendamento = datetime.strptime(simulacao['agendamento'], '%Y-%m-%d').date()

    separacoes_criadas = []

    try:
        for item in simulacao['itens']:
            separacao = Separacao(
                separacao_lote_id=lote_id,
                num_pedido=simulacao['num_pedido'],
                data_pedido=item.get('data_pedido'),
                cnpj_cpf=item['cnpj_cpf'],
                raz_social_red=item['raz_social_red'],
                nome_cidade=item['nome_cidade'],
                cod_uf=item['cod_uf'],
                cod_produto=item['cod_produto'],
                nome_produto=item['nome_produto'],
                qtd_saldo=item['quantidade'],
                valor_saldo=item['valor'],
                peso=item['peso'],
                pallet=item['pallets'],
                rota=item['rota'],
                sub_rota=item['sub_rota'],
                observ_ped_1=item.get('observacoes'),
                roteirizacao=None,
                expedicao=data_expedicao,
                agendamento=data_agendamento,
                protocolo=simulacao.get('protocolo'),
                agendamento_confirmado=simulacao.get('agendamento_confirmado', False),
                pedido_cliente=item.get('pedido_cliente'),
                tipo_envio=simulacao['tipo_envio'],
                status='ABERTO',
                sincronizado_nf=False,
                criado_em=agora_brasil(),
                criado_por='Agente Logistico'  # Identificar origem da criação
            )

            db.session.add(separacao)
            separacoes_criadas.append(separacao)

        db.session.commit()

        return {
            'success': True,
            'message': f'Separacao criada com sucesso! Lote: {lote_id}',
            'lote_id': lote_id,
            'qtd_itens': len(separacoes_criadas),
            'totais': simulacao['totais']
        }

    except Exception as e:
        db.session.rollback()
        return {
            'success': False,
            'error': f'Erro ao criar separacao: {str(e)}'
        }


def main():
    parser = argparse.ArgumentParser(
        description='Cria separacoes de pedidos',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  # Simular separacao completa (sempre simular primeiro!)
  python criando_separacao.py --pedido VCD123 --expedicao amanha --tipo completa

  # Simular com 28 pallets
  python criando_separacao.py --pedido VCD123 --expedicao 20/12 --pallets 28

  # Simular com pallets inteiros
  python criando_separacao.py --pedido VCD123 --expedicao amanha --pallets 28 --pallets-inteiros

  # Simular apenas com estoque disponivel
  python criando_separacao.py --pedido VCD123 --expedicao amanha --apenas-estoque

  # Simular excluindo produtos
  python criando_separacao.py --pedido VCD123 --expedicao amanha --excluir-produtos '["KETCHUP","MOSTARDA"]'

  # EXECUTAR (criar de verdade) - use --executar
  python criando_separacao.py --pedido VCD123 --expedicao amanha --tipo completa --executar
        """
    )

    # Argumentos obrigatorios
    parser.add_argument('--pedido', required=True, help='Numero do pedido')
    parser.add_argument('--expedicao', required=True, help='Data de expedicao (dd/mm, dd/mm/yyyy, amanha, etc)')

    # Tipo de separacao
    parser.add_argument('--tipo', choices=['completa', 'parcial'], default='completa',
                        help='Tipo de separacao')

    # Opcoes de pallets
    parser.add_argument('--pallets', type=float, help='Quantidade total de pallets desejada')
    parser.add_argument('--pallets-inteiros', action='store_true',
                        help='Forcar pallets inteiros por item')

    # Filtros
    parser.add_argument('--apenas-estoque', action='store_true',
                        help='Separar apenas o que tem em estoque')
    parser.add_argument('--excluir-produtos', type=str,
                        help='JSON array de produtos a excluir (ex: \'["KETCHUP","MOSTARDA"]\')')

    # Agendamento
    parser.add_argument('--agendamento', help='Data de agendamento')
    parser.add_argument('--protocolo', help='Protocolo de agendamento')
    parser.add_argument('--agendamento-confirmado', action='store_true',
                        help='Marcar agendamento como confirmado')

    # Execucao
    parser.add_argument('--executar', action='store_true',
                        help='Efetivamente criar a separacao (sem isso, apenas simula)')

    args = parser.parse_args()

    # Criar contexto Flask
    with criar_app_context():
        # Resolver pedido (retorna tupla: itens, num_pedido, info)
        itens, num_pedido, pedido_info = resolver_pedido(args.pedido, fonte='carteira')

        if not num_pedido:
            resultado = {
                'success': False,
                'error': f'Pedido "{args.pedido}" nao encontrado na carteira',
                'sugestao': formatar_sugestao_pedido(pedido_info) if pedido_info else None,
                'info': pedido_info
            }
            print(json.dumps(resultado, default=decimal_default, ensure_ascii=False, indent=2))
            return

        # Verificar se multiplos pedidos foram encontrados
        if pedido_info.get('multiplos_encontrados'):
            resultado = {
                'success': False,
                'error': f'Multiplos pedidos encontrados para "{args.pedido}"',
                'pedidos_candidatos': pedido_info.get('pedidos_candidatos', []),
                'sugestao': 'Especifique o numero exato do pedido'
            }
            print(json.dumps(resultado, default=decimal_default, ensure_ascii=False, indent=2))
            return

        # Parse datas
        try:
            data_expedicao = parse_data_natural(args.expedicao)
        except ValueError as e:
            resultado = {'success': False, 'error': str(e)}
            print(json.dumps(resultado, default=decimal_default, ensure_ascii=False, indent=2))
            return

        data_agendamento = None
        if args.agendamento:
            try:
                data_agendamento = parse_data_natural(args.agendamento)
            except ValueError as e:
                resultado = {'success': False, 'error': f'Data agendamento invalida: {e}'}
                print(json.dumps(resultado, default=decimal_default, ensure_ascii=False, indent=2))
                return

        # Parse excluir produtos
        excluir_produtos = None
        if args.excluir_produtos:
            try:
                excluir_produtos = json.loads(args.excluir_produtos)
            except json.JSONDecodeError:
                resultado = {'success': False, 'error': 'JSON invalido em --excluir-produtos'}
                print(json.dumps(resultado, default=decimal_default, ensure_ascii=False, indent=2))
                return

        # Simular separacao
        simulacao = simular_separacao(
            num_pedido=num_pedido,
            data_expedicao=data_expedicao,
            tipo=args.tipo,
            total_pallets=args.pallets,
            pallets_inteiros=args.pallets_inteiros,
            apenas_estoque=args.apenas_estoque,
            excluir_produtos=excluir_produtos,
            agendamento=data_agendamento,
            protocolo=args.protocolo,
            agendamento_confirmado=args.agendamento_confirmado
        )

        if args.executar:
            if simulacao['success']:
                # Executar de verdade
                resultado = executar_separacao(simulacao)
            else:
                resultado = simulacao
        else:
            # Apenas simulacao
            simulacao['modo'] = 'SIMULACAO'
            simulacao['aviso'] = 'Use --executar para criar efetivamente a separacao'
            resultado = simulacao

        print(json.dumps(resultado, default=decimal_default, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

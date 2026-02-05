#!/usr/bin/env python3
"""
Script: analisando_carteira_completa.py
A CEREJA DO BOLO - Clone do Rafael

Analisa a carteira COMPLETA seguindo o algoritmo do Rafael:
1. Pedidos com data_entrega_pedido (cliente ja negociou) - NAO AVALIAR, EXECUTAR
2. FOB (cliente coleta) - SEMPRE COMPLETO
3. Cargas diretas fora de SP (>=26 pallets ou >=20.000kg) - Sugerir agendamento D+3+leadtime
4. Atacadao (EXCETO loja 183) - 50% do faturamento
5. Assai
6. Resto ordenado por data_pedido (mais antigo primeiro)
7. Atacadao 183 (por ultimo - evitar ruptura em outros)

Regras de Parcial:
- FOB: SEMPRE COMPLETO (saldo cancelado se nao for)
- Pedido pequeno (<R$15K): Tentar COMPLETO
- <=10% falta + >3 dias: PARCIAL automatico
- 10-20% falta + >3 dias: CONSULTAR comercial
- >20% falta + >3 dias + >R$10K: CONSULTAR comercial

Para cada pedido:
- Verifica disponibilidade de estoque
- Aplica regras de parcial/aguardar
- Gera comunicacoes para PCP (por PRODUTO)
- Gera comunicacoes para Comercial (por GESTOR)
- Sugere separacoes com comandos prontos

Uso:
    python analisando_carteira_completa.py                    # Analise completa
    python analisando_carteira_completa.py --resumo           # Apenas resumo executivo
    python analisando_carteira_completa.py --prioridade 1     # Apenas prioridade 1 (data_entrega)
    python analisando_carteira_completa.py --prioridade 2     # Apenas prioridade 2 (FOB)
    python analisando_carteira_completa.py --prioridade 7     # Apenas Atacadao 183
    python analisando_carteira_completa.py --limit 50         # Limitar pedidos analisados
"""
import sys
import os
import json
import argparse
from datetime import date, datetime, timedelta
from decimal import Decimal
from collections import defaultdict

# Adicionar path do projeto
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))

from resolver_entidades import GRUPOS_EMPRESARIAIS


def decimal_default(obj):
    """Serializa Decimal para JSON"""
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


# ============================================================
# CONSTANTES - REGRAS DE NEGOCIO DO RAFAEL
# ============================================================
LIMITE_PALLETS_CARGA_DIRETA = 26
LIMITE_PESO_CARGA_DIRETA = 20000
LIMITE_PESO_CARGA_DIRETA_SC_PR = 2000

# Regra: acima desse limite, SEMPRE enviar parcial
LIMITE_PALLETS_ENVIO_PARCIAL = 30
LIMITE_PESO_ENVIO_PARCIAL = 25000
UFS_CARGA_DIRETA_D2 = ['SC', 'PR']
LIMITE_FALTA_PARCIAL_AUTO = 0.10  # 10%
LIMITE_FALTA_CONSULTAR_FAIXA_MEDIA = 0.20  # 20% - faixa 10-20% consultar comercial
LIMITE_FALTA_CONSULTAR = 0.20     # 20% - acima disso + >R$10K consultar comercial
DIAS_DEMORA_PARA_PARCIAL = 3
VALOR_MINIMO_CONSULTAR_COMERCIAL = 10000

# NOVO: Pedido pequeno - tentar COMPLETO (saldo pode nao compensar frete)
# Regra: falta >= 10% → AGUARDAR | falta < 10% + demora > 5 dias → PARCIAL | falta < 10% + demora <= 5 dias → AGUARDAR
VALOR_PEDIDO_PEQUENO = 15000
DIAS_DEMORA_PEDIDO_PEQUENO = 5  # dias úteis - se falta < 10% e demora > 5 dias, pode enviar parcial

# NOVO: Atacadao 183 - Identificar pelo nome do cliente (filiais do Atacadao)
# A loja 183 compra muito volume com muitas opcoes de montagem
# Se priorizada, pode gerar ruptura em outros clientes
# Melhor atender o resto e formar carga com o que sobra
IDENTIFICADOR_ATACADAO_183 = '183'  # Buscar "183" no nome do cliente


def identificar_grupo_cliente(cnpj: str) -> str:
    """Identifica grupo empresarial pelo CNPJ (APENAS por CNPJ)."""
    if not cnpj:
        return 'outros'
    for grupo, prefixos in GRUPOS_EMPRESARIAIS.items():
        for prefixo in prefixos:
            if cnpj.startswith(prefixo):
                return grupo
    return 'outros'


def eh_atacadao_183(cliente: str) -> bool:
    """
    Verifica se o cliente é o Atacadão 183.
    A loja 183 compra muito volume com muitas opções de montagem.
    Se priorizada, pode gerar ruptura em outros clientes.
    """
    if not cliente:
        return False
    # Buscar "183" no nome do cliente
    return IDENTIFICADOR_ATACADAO_183 in str(cliente)


def extrair_gestor_de_equipe_vendas(equipe_vendas: str) -> dict:
    """Extrai gestor do campo equipe_vendas."""
    if not equipe_vendas:
        return {'nome': 'N/A', 'canal': 'N/A', 'equipe_vendas': None}

    equipe_upper = equipe_vendas.upper()
    canal = 'Teams' if 'INTERNA' in equipe_upper else 'WhatsApp'

    mapeamento = {
        'ATACADÃO': 'Junior', 'ATACADAO': 'Junior', 'SENDAS': 'Junior',
        'MILER': 'Miler', 'FERNANDO': 'Fernando', 'JUNIOR': 'Junior', 'DENISE': 'Denise'
    }

    nome = 'N/A'
    for chave, gestor in mapeamento.items():
        if chave in equipe_upper:
            nome = gestor
            break

    return {'nome': nome, 'canal': canal, 'equipe_vendas': equipe_vendas}


def subtrair_dias_uteis(data_base: date, dias_uteis: int) -> date:
    """
    Subtrai dias úteis de uma data (exclui sábado e domingo).
    """
    resultado = data_base
    dias_restantes = dias_uteis
    while dias_restantes > 0:
        resultado = resultado - timedelta(days=1)
        # 0=segunda, 5=sábado, 6=domingo
        if resultado.weekday() < 5:  # Não é fim de semana
            dias_restantes -= 1
    return resultado


def adicionar_dias_uteis(data_base: date, dias_uteis: int) -> date:
    """
    Adiciona dias úteis a uma data (exclui sábado e domingo).
    """
    resultado = data_base
    dias_restantes = dias_uteis
    while dias_restantes > 0:
        resultado = resultado + timedelta(days=1)
        # 0=segunda, 5=sábado, 6=domingo
        if resultado.weekday() < 5:  # Não é fim de semana
            dias_restantes -= 1
    return resultado


def calcular_sugestao_agendamento(lead_time: int = 3) -> dict:
    """
    Calcula sugestão de agendamento para P3 (cargas diretas que exigem agenda).

    Fluxo:
    - D+0 (hoje): Solicitar agendamento
    - D+2: Retorno do cliente (esperar confirmação)
    - D+3: Expedição se aprovado
    - D+3+leadtime: Entrega

    Args:
        lead_time: dias úteis de trânsito (default 3)

    Returns:
        {
            'data_solicitar': date,
            'data_retorno': date,
            'data_expedicao': date,
            'data_entrega': date,
            'lead_time': int
        }
    """
    hoje = date.today()

    data_solicitar = hoje  # D+0
    data_retorno = adicionar_dias_uteis(hoje, 2)  # D+2
    data_expedicao = adicionar_dias_uteis(hoje, 3)  # D+3
    data_entrega = adicionar_dias_uteis(data_expedicao, lead_time)  # D+3+leadtime

    return {
        'data_solicitar': data_solicitar.isoformat(),
        'data_retorno': data_retorno.isoformat(),
        'data_expedicao': data_expedicao.isoformat(),
        'data_entrega': data_entrega.isoformat(),
        'lead_time': lead_time,
        'resumo': f"Solicitar agendamento HOJE. Expedição em {data_expedicao.strftime('%d/%m')} → Entrega {data_entrega.strftime('%d/%m')}"
    }


def calcular_data_expedicao(data_entrega: date, uf: str, peso: float, incoterm: str = None) -> dict:
    """
    Calcula data de expedicao baseado em regras do Rafael.
    SO APLICA para pedidos com data_entrega_pedido.

    Retorna:
        {
            'data_expedicao': date ou None,
            'automatico': bool,  # Se é cálculo automático ou precisa opções de frete
            'regra': str,        # Descrição da regra aplicada
            'dias_uteis': int    # Dias úteis antes da entrega
        }

    Regras:
    - SP OU incoterm=RED: D-1 (automático)
    - SC/PR + peso > 2.000kg: D-2 (automático)
    - Outras regiões (incluindo SC/PR < 2.000kg): Calcular frete (lead_time)
    """
    # REGRA 1: SP ou RED (incoterm) → D-1 automático
    if uf == 'SP' or (incoterm and incoterm.upper() == 'RED'):
        regra = 'D-1 (SP)' if uf == 'SP' else 'D-1 (RED/Redespacho)'
        return {
            'data_expedicao': subtrair_dias_uteis(data_entrega, 1),
            'automatico': True,
            'regra': regra,
            'dias_uteis': 1
        }

    # REGRA 2: SC/PR + peso > 2.000kg → D-2 automático
    if uf in UFS_CARGA_DIRETA_D2 and peso > LIMITE_PESO_CARGA_DIRETA_SC_PR:
        return {
            'data_expedicao': subtrair_dias_uteis(data_entrega, 2),
            'automatico': True,
            'regra': f'D-2 ({uf} + peso > {LIMITE_PESO_CARGA_DIRETA_SC_PR}kg)',
            'dias_uteis': 2
        }

    # OUTRAS REGIÕES (incluindo SC/PR < 2.000kg): Precisa calcular frete para obter lead_time
    return {
        'data_expedicao': None,
        'automatico': False,
        'regra': 'Calcular frete (lead_time)',
        'dias_uteis': None
    }


def calcular_opcoes_frete_com_leadtime(
    data_entrega: date,
    codigo_ibge: str,
    peso: float,
    valor: float,
    uf: str = None,
    cidade: str = None
) -> dict:
    """
    Calcula opções de frete COM lead_time para regiões que não são SP/RED/SC-PR>2000kg.

    Retorna:
        {
            'sucesso': bool,
            'opcoes': [
                {
                    'transportadora': str,
                    'nome_tabela': str,
                    'valor_frete': float,
                    'lead_time': int (dias úteis),
                    'data_expedicao': date,
                    'destaque': str ou None  # 'MAIS_BARATA', 'MAIS_RAPIDA', 'AMBOS'
                }
            ],
            'mais_barata': {...},
            'mais_rapida': {...}
        }
    """
    from app.vinculos.models import CidadeAtendida
    from app.localidades.models import Cidade
    from app.utils.frete_simulador import calcular_fretes_possiveis
    from app import db

    resultado = {
        'sucesso': False,
        'opcoes': [],
        'mais_barata': None,
        'mais_rapida': None,
        'erro': None
    }

    # Buscar cidade pelo código IBGE
    cidade_obj = None
    if codigo_ibge:
        cidade_obj = Cidade.query.filter_by(codigo_ibge=codigo_ibge).first()

    if not cidade_obj and uf and cidade:
        # Fallback: buscar por nome e UF
        from sqlalchemy import func
        cidade_obj = Cidade.query.filter(
            func.upper(Cidade.uf) == uf.upper(),
            func.upper(Cidade.nome).like(f"%{cidade.upper()}%")
        ).first()

    if not cidade_obj:
        resultado['erro'] = f'Cidade não encontrada (IBGE: {codigo_ibge}, UF: {uf}, Cidade: {cidade})'
        return resultado

    # Buscar atendimentos com lead_time
    atendimentos = CidadeAtendida.query.filter(
        CidadeAtendida.codigo_ibge == cidade_obj.codigo_ibge
    ).all()

    if not atendimentos:
        resultado['erro'] = f'Nenhuma transportadora atende {cidade_obj.nome}/{cidade_obj.uf}'
        return resultado

    # Calcular fretes
    fretes = calcular_fretes_possiveis(
        cidade_destino_id=cidade_obj.id,
        peso_utilizado=peso,
        valor_carga=valor
    )

    if not fretes:
        resultado['erro'] = 'Nenhum frete calculado'
        return resultado

    # Criar dict de lead_time por transportadora/tabela
    leadtime_dict = {}
    for at in atendimentos:
        chave = (at.transportadora_id, at.nome_tabela.upper().strip() if at.nome_tabela else '')
        leadtime_dict[chave] = at.lead_time or 1  # Default 1 dia se não especificado

    # Processar opções de frete com lead_time
    opcoes = []
    for frete in fretes:
        transp_id = frete.get('transportadora_id')
        nome_tabela = (frete.get('nome_tabela') or '').upper().strip()
        # Limpar sufixos adicionados pelo simulador (ex: "(MAIS CARA p/ BA)")
        nome_tabela_limpo = nome_tabela.split(' (')[0].strip()

        chave = (transp_id, nome_tabela_limpo)
        lead_time = leadtime_dict.get(chave, 1)

        # Calcular data de expedição baseado no lead_time
        data_exp = subtrair_dias_uteis(data_entrega, lead_time)

        opcoes.append({
            'transportadora': frete.get('transportadora'),
            'transportadora_id': transp_id,
            'nome_tabela': frete.get('nome_tabela'),
            'modalidade': frete.get('modalidade'),
            'tipo_carga': frete.get('tipo_carga'),
            'valor_frete': frete.get('valor_total', 0),
            'valor_liquido': frete.get('valor_liquido', 0),
            'lead_time': lead_time,
            'data_expedicao': data_exp,
            'destaque': None  # Será preenchido abaixo
        })

    if not opcoes:
        resultado['erro'] = 'Nenhuma opção com lead_time encontrada'
        return resultado

    # Identificar mais barata e mais rápida
    mais_barata = min(opcoes, key=lambda x: x['valor_frete'])
    mais_rapida = min(opcoes, key=lambda x: x['lead_time'])

    # Marcar destaques
    for op in opcoes:
        eh_mais_barata = op['valor_frete'] == mais_barata['valor_frete']
        eh_mais_rapida = op['lead_time'] == mais_rapida['lead_time']

        if eh_mais_barata and eh_mais_rapida:
            op['destaque'] = 'AMBOS'
        elif eh_mais_barata:
            op['destaque'] = 'MAIS_BARATA'
        elif eh_mais_rapida:
            op['destaque'] = 'MAIS_RAPIDA'

    # Ordenar por valor (mais barata primeiro)
    opcoes.sort(key=lambda x: x['valor_frete'])

    resultado['sucesso'] = True
    resultado['opcoes'] = opcoes
    resultado['mais_barata'] = mais_barata
    resultado['mais_rapida'] = mais_rapida

    return resultado


def encontrar_data_disponibilidade(projecao: list, qtd_necessaria: float) -> str:
    """Encontra a primeira data em que haverá estoque suficiente."""
    if not projecao:
        return None
    for dia in projecao:
        saldo = dia.get('saldo_final', 0)
        if saldo >= qtd_necessaria:
            return dia.get('data')
    return None  # Sem previsão nos próximos 28 dias


def analisar_disponibilidade_pedido(num_pedido: str, itens_pedido: list, estoque_dict: dict, projecao_dict: dict = None) -> dict:
    """
    Analisa disponibilidade de um pedido especifico.
    USA PROJEÇÃO para calcular data_100_disponivel.
    PERCENTUAL calculado por VALOR (não por número de linhas).

    Args:
        projecao_dict: Dict com projeção por produto {cod: {projecao: [...], dia_ruptura: ...}}

    Retorna:
        {
            'disponivel': bool,
            'percentual_disponivel': float (0-100) - baseado em VALOR
            'itens_disponiveis': list,
            'itens_com_falta': list,
            'data_100_disponivel': str (ISO date) ou None,
            'dias_para_100': int ou None
        }
    """
    itens_disponiveis = []
    itens_com_falta = []
    data_disponibilidade_maxima = None  # Maior data entre todos os itens
    valor_total = 0  # Valor total do pedido
    valor_disponivel = 0  # Valor dos itens 100% disponíveis

    for item in itens_pedido:
        cod_produto = item['cod_produto']
        qtd_necessaria = item['qtd_saldo']
        valor_item = item.get('valor', 0)  # Valor do item (qtd * preco)
        valor_total += valor_item

        # Buscar estoque atual
        estoque_atual = estoque_dict.get(cod_produto, 0)

        # Buscar projeção se disponível
        proj_produto = projecao_dict.get(cod_produto, {}) if projecao_dict else {}
        projecao = proj_produto.get('projecao', [])

        if estoque_atual >= qtd_necessaria:
            valor_disponivel += valor_item
            itens_disponiveis.append({
                'cod_produto': cod_produto,
                'nome_produto': item['nome_produto'],
                'qtd_necessaria': qtd_necessaria,
                'estoque_atual': estoque_atual,
                'valor': valor_item,
                'status': 'DISPONIVEL'
            })
        else:
            falta = qtd_necessaria - estoque_atual
            # Calcular quando terá estoque (usando projeção)
            data_disp = encontrar_data_disponibilidade(projecao, qtd_necessaria)

            itens_com_falta.append({
                'cod_produto': cod_produto,
                'nome_produto': item['nome_produto'],
                'qtd_necessaria': qtd_necessaria,
                'estoque_atual': estoque_atual,
                'falta': round(falta, 2),
                'valor': valor_item,
                'data_disponibilidade': data_disp,
                'status': 'FALTA'
            })

            # Atualizar data máxima de disponibilidade
            if data_disp:
                if data_disponibilidade_maxima is None or data_disp > data_disponibilidade_maxima:
                    data_disponibilidade_maxima = data_disp

    # PERCENTUAL POR VALOR (não por linhas)
    total_itens = len(itens_pedido)
    qtd_disponiveis = len(itens_disponiveis)
    percentual = (valor_disponivel / valor_total * 100) if valor_total > 0 else 0

    # Calcular dias para 100% disponível
    dias_para_100 = None
    if data_disponibilidade_maxima:
        try:
            data_max = datetime.strptime(data_disponibilidade_maxima, '%Y-%m-%d').date()
            dias_para_100 = (data_max - date.today()).days
        except (ValueError, TypeError):
            pass

    return {
        'disponivel': len(itens_com_falta) == 0,
        'percentual_disponivel': round(percentual, 1),
        'percentual_falta': round(100 - percentual, 1),
        'total_itens': total_itens,
        'qtd_disponiveis': qtd_disponiveis,
        'qtd_com_falta': len(itens_com_falta),
        'itens_disponiveis': itens_disponiveis,
        'itens_com_falta': itens_com_falta,
        'data_100_disponivel': data_disponibilidade_maxima,
        'dias_para_100': dias_para_100
    }


def aplicar_regras_decisao(
    disponibilidade: dict,
    valor_pedido: float,
    pallets: float = 0,
    peso: float = 0,
    dias_demora: int = 5,
    incoterm: str = None
) -> dict:
    """
    Aplica regras de decisao do Rafael.

    Regras (ordem de prioridade):
    1. FOB: SEMPRE COMPLETO (saldo cancelado se nao for - cliente nao quer vir 2x)
    2. Pedido pequeno (<R$15K): Tentar COMPLETO (saldo pode nao compensar frete)
    3. Acima de 30 pallets OU 25.000 kg → SEMPRE PARCIAL (limite fisico)
    4. <=10% falta + >3 dias demora → PARCIAL_AUTOMATICO
    5. 10-20% falta + >3 dias demora → CONSULTAR_COMERCIAL
    6. >20% falta + >3 dias + >R$10K → CONSULTAR_COMERCIAL
    7. Outros → AGUARDAR
    """
    percentual_falta = disponibilidade['percentual_falta'] / 100  # Converter para 0-1
    eh_fob = incoterm and incoterm.upper() == 'FOB'
    eh_pedido_pequeno = valor_pedido < VALOR_PEDIDO_PEQUENO

    # REGRA DE CARGA MÁXIMA: acima de 30 pallets OU 25.000 kg SEMPRE envia parcial
    excede_carga = pallets >= LIMITE_PALLETS_ENVIO_PARCIAL or peso >= LIMITE_PESO_ENVIO_PARCIAL
    motivo_carga = None
    if excede_carga:
        if pallets >= LIMITE_PALLETS_ENVIO_PARCIAL:
            motivo_carga = f'Excede {LIMITE_PALLETS_ENVIO_PARCIAL} pallets ({pallets:.1f} pallets)'
        else:
            motivo_carga = f'Excede {LIMITE_PESO_ENVIO_PARCIAL:,.0f}kg ({peso:,.0f}kg)'

    # SE DISPONIVEL (100% em estoque)
    if disponibilidade['disponivel']:
        if excede_carga:
            return {
                'decisao': 'PARCIAL_CARGA_MAXIMA',
                'acao': 'Enviar parcial (carga maxima)',
                'motivo': motivo_carga
            }
        return {
            'decisao': 'DISPONIVEL',
            'acao': 'Criar separacao',
            'motivo': 'Todos os itens disponiveis'
        }

    # COM FALTA - aplicar regras especiais primeiro

    # REGRA FOB: SEMPRE aguardar COMPLETO (cliente nao quer vir 2x ao CD)
    if eh_fob:
        return {
            'decisao': 'AGUARDAR_COMPLETO_FOB',
            'acao': 'Aguardar 100% - FOB nao aceita parcial',
            'motivo': f'FOB: Cliente coleta. Saldo seria cancelado se enviar parcial.'
        }

    # REGRA PEDIDO PEQUENO: Tentar COMPLETO (saldo pode nao compensar frete)
    # - falta >= 10% → AGUARDAR COMPLETO (saldo grande demais para perder)
    # - falta < 10% + demora <= 5 dias → AGUARDAR (vale esperar)
    # - falta < 10% + demora > 5 dias → deixar cair nas regras normais (PARCIAL)
    if eh_pedido_pequeno:
        if percentual_falta >= LIMITE_FALTA_PARCIAL_AUTO:  # >= 10% falta
            return {
                'decisao': 'AGUARDAR_COMPLETO_PEQUENO',
                'acao': 'Tentar aguardar 100% - pedido pequeno',
                'motivo': f'Pedido < R$ {VALOR_PEDIDO_PEQUENO:,.0f} com falta de {disponibilidade["percentual_falta"]:.0f}%: Saldo pode nao compensar frete separado.'
            }
        elif dias_demora <= DIAS_DEMORA_PEDIDO_PEQUENO:  # falta < 10% e demora <= 5 dias
            return {
                'decisao': 'AGUARDAR_COMPLETO_PEQUENO',
                'acao': 'Aguardar 100% - pedido pequeno com falta pequena',
                'motivo': f'Pedido < R$ {VALOR_PEDIDO_PEQUENO:,.0f} com falta de {disponibilidade["percentual_falta"]:.0f}%: Vale esperar {dias_demora} dias.'
            }
        # else: falta < 10% e demora > 5 dias → deixar cair nas regras normais (PARCIAL_AUTOMATICO)

    # REGRA <=10%: PARCIAL AUTOMATICO
    if percentual_falta <= LIMITE_FALTA_PARCIAL_AUTO and dias_demora > DIAS_DEMORA_PARA_PARCIAL:
        return {
            'decisao': 'PARCIAL_AUTOMATICO',
            'acao': 'Enviar parcial',
            'motivo': f'Falta {disponibilidade["percentual_falta"]:.0f}% e demora > {DIAS_DEMORA_PARA_PARCIAL} dias' + (f' + {motivo_carga}' if excede_carga else '')
        }

    # REGRA 10-20%: CONSULTAR COMERCIAL (faixa que antes ia para AGUARDAR)
    if percentual_falta > LIMITE_FALTA_PARCIAL_AUTO and percentual_falta <= LIMITE_FALTA_CONSULTAR_FAIXA_MEDIA and dias_demora > DIAS_DEMORA_PARA_PARCIAL:
        return {
            'decisao': 'CONSULTAR_COMERCIAL',
            'acao': 'Perguntar ao gestor: parcial ou aguarda?',
            'motivo': f'Falta {disponibilidade["percentual_falta"]:.0f}% (faixa 10-20%), demora > {DIAS_DEMORA_PARA_PARCIAL} dias'
        }

    # REGRA >20% + >R$10K: CONSULTAR COMERCIAL
    if percentual_falta > LIMITE_FALTA_CONSULTAR and dias_demora > DIAS_DEMORA_PARA_PARCIAL and valor_pedido > VALOR_MINIMO_CONSULTAR_COMERCIAL:
        return {
            'decisao': 'CONSULTAR_COMERCIAL',
            'acao': 'Perguntar ao gestor: parcial ou aguarda?',
            'motivo': f'Falta {disponibilidade["percentual_falta"]:.0f}%, demora > {DIAS_DEMORA_PARA_PARCIAL} dias, valor > R$ {VALOR_MINIMO_CONSULTAR_COMERCIAL:,.0f}'
        }

    return {
        'decisao': 'AGUARDAR',
        'acao': 'Aguardar producao',
        'motivo': 'Falta nao atinge criterios de parcial'
    }


def analisar_carteira_completa(limit=None, prioridade_filtro=None):
    """
    Analisa a carteira completa seguindo o algoritmo do Rafael.
    Inclui analise de disponibilidade e geracao de comunicacoes.
    """
    from app.carteira.models import CarteiraPrincipal
    from app.separacao.models import Separacao
    from app.producao.models import CadastroPalletizacao
    from app.cadastros_agendamento.models import ContatoAgendamento
    from app.estoque.services.estoque_simples import ServicoEstoqueSimples
    from sqlalchemy import func
    from app import db

    hoje = date.today()

    # ==========================================================
    # 1. BUSCAR TODOS OS ITENS DA CARTEIRA (nao agrupado)
    # ==========================================================
    itens_carteira = CarteiraPrincipal.query.filter(
        CarteiraPrincipal.qtd_saldo_produto_pedido > 0
    ).all()

    if not itens_carteira:
        return {
            'sucesso': True,
            'data_analise': hoje.isoformat(),
            'total_pedidos': 0,
            'mensagem': 'Nenhum pedido pendente na carteira',
            'prioridades': {},
            'resumo': {},
            'acoes': {},
            'comunicacoes': {'pcp': [], 'comercial': {}}
        }

    # ==========================================================
    # 2. BUSCAR DADOS AUXILIARES EM BATCH
    # ==========================================================

    # Agendamentos
    agendamentos_query = db.session.query(
        ContatoAgendamento.cnpj, ContatoAgendamento.forma
    ).all()
    agendamentos_dict = {a.cnpj: a.forma for a in agendamentos_query}

    # Palletizacao (com campos para nome resumido)
    palletizacao_query = db.session.query(
        CadastroPalletizacao.cod_produto,
        CadastroPalletizacao.peso_bruto,
        CadastroPalletizacao.palletizacao,
        CadastroPalletizacao.tipo_materia_prima,
        CadastroPalletizacao.tipo_embalagem,
        CadastroPalletizacao.categoria_produto
    ).all()
    palletizacao_dict = {}
    for p in palletizacao_query:
        # Nome resumido: "AZ VF - POUCH 150G - CAMPO BELO"
        nome_resumido = f"{p.tipo_materia_prima or ''} - {p.tipo_embalagem or ''} - {p.categoria_produto or ''}".strip(' -')
        palletizacao_dict[p.cod_produto] = {
            'peso': float(p.peso_bruto or 0),
            'pallet': float(p.palletizacao or 1),
            'nome_resumido': nome_resumido if nome_resumido else None
        }

    # Separacoes ja feitas
    separados_query = db.session.query(
        Separacao.num_pedido,
        func.sum(Separacao.qtd_saldo).label('qtd_separada'),
        Separacao.separacao_lote_id, Separacao.expedicao, Separacao.status
    ).filter(
        Separacao.sincronizado_nf == False, Separacao.qtd_saldo > 0
    ).group_by(
        Separacao.num_pedido, Separacao.separacao_lote_id, Separacao.expedicao, Separacao.status
    ).all()

    separados_dict = {}
    for s in separados_query:
        if s.num_pedido not in separados_dict:
            separados_dict[s.num_pedido] = {
                'qtd_separada': float(s.qtd_separada or 0),
                'lote_id': s.separacao_lote_id,
                'expedicao': s.expedicao.isoformat() if s.expedicao else None,
                'status': s.status
            }

    # ==========================================================
    # 3. AGRUPAR ITENS POR PEDIDO + CALCULAR ESTOQUE + PROJEÇÃO
    # ==========================================================

    # Coletar todos os produtos unicos para buscar estoque
    produtos_unicos = set(item.cod_produto for item in itens_carteira)

    # Buscar estoque atual E projeção de todos os produtos
    estoque_dict = {}
    projecao_dict = {}  # Para identificar ruptura prevista
    for cod_produto in produtos_unicos:
        estoque_dict[cod_produto] = ServicoEstoqueSimples.calcular_estoque_atual(cod_produto)
        # Buscar projeção para identificar dia_ruptura
        proj = ServicoEstoqueSimples.calcular_projecao(cod_produto, dias=28)
        projecao_dict[cod_produto] = {
            'dia_ruptura': proj.get('dia_ruptura'),
            'projecao': proj.get('projecao', [])
        }

    # Agrupar itens por pedido
    pedidos_dict = defaultdict(lambda: {
        'itens': [], 'valor_total': 0, 'peso_total': 0, 'pallets_total': 0,
        'cnpj': None, 'cliente': None, 'cidade': None, 'uf': None,
        'data_entrega_pedido': None, 'data_pedido': None, 'equipe_vendas': None,
        'incoterm': None, 'codigo_ibge': None  # Para calcular frete
    })

    for item in itens_carteira:
        num = item.num_pedido
        qtd = float(item.qtd_saldo_produto_pedido or 0)
        preco = float(item.preco_produto_pedido or 0)

        pal_info = palletizacao_dict.get(item.cod_produto, {'peso': 0, 'pallet': 1})
        peso_item = qtd * pal_info['peso']
        pallets_item = qtd / pal_info['pallet'] if pal_info['pallet'] > 0 else 0

        pedidos_dict[num]['itens'].append({
            'cod_produto': item.cod_produto,
            'nome_produto': item.nome_produto,
            'qtd_saldo': qtd,
            'valor': qtd * preco
        })
        pedidos_dict[num]['valor_total'] += qtd * preco
        pedidos_dict[num]['peso_total'] += peso_item
        pedidos_dict[num]['pallets_total'] += pallets_item
        pedidos_dict[num]['cnpj'] = item.cnpj_cpf
        pedidos_dict[num]['cliente'] = item.raz_social_red
        pedidos_dict[num]['cidade'] = item.nome_cidade
        pedidos_dict[num]['uf'] = item.cod_uf
        pedidos_dict[num]['data_entrega_pedido'] = item.data_entrega_pedido
        pedidos_dict[num]['data_pedido'] = getattr(item, 'data_pedido', None)  # Para ordenar P6
        pedidos_dict[num]['equipe_vendas'] = item.equipe_vendas
        pedidos_dict[num]['incoterm'] = getattr(item, 'incoterm', None)  # Para regra RED/FOB
        pedidos_dict[num]['codigo_ibge'] = getattr(item, 'codigo_ibge', None)  # Para calcular frete

    # ==========================================================
    # 4. ANALISAR CADA PEDIDO
    # ==========================================================
    pedidos = []
    # PCP: acumular DEMANDA por produto (não falta individual)
    comunicacoes_pcp = defaultdict(lambda: {'qtd_demandada': 0, 'pedidos_afetados': [], 'nome_produto': None, 'nome_resumido': None})
    comunicacoes_comercial = defaultdict(list)
    # Sugestões de ajuste para separações existentes
    sugestoes_ajuste = []

    for num_pedido, dados in pedidos_dict.items():
        cnpj = dados['cnpj']
        uf = dados['uf']
        valor_total = dados['valor_total']
        peso = dados['peso_total']
        pallets = dados['pallets_total']

        # Identificar grupo e gestor
        grupo = identificar_grupo_cliente(cnpj)
        gestor = extrair_gestor_de_equipe_vendas(dados['equipe_vendas'])
        tipo_cliente = 'industria' if gestor['nome'] == 'Fernando' else 'varejo'
        incoterm = dados.get('incoterm')
        cliente = dados['cliente']

        # Classificar prioridade (P1-P7 conforme algoritmo do Rafael)
        # P1: Pedidos com data_entrega_pedido (NAO AVALIAR, EXECUTAR)
        if dados['data_entrega_pedido']:
            prioridade = 1
        # P2: FOB (cliente coleta) - SEMPRE COMPLETO
        elif incoterm and incoterm.upper() == 'FOB':
            prioridade = 2
        # P3: Cargas diretas fora de SP (>=26 pallets ou >=20.000kg)
        elif (pallets >= LIMITE_PALLETS_CARGA_DIRETA or peso >= LIMITE_PESO_CARGA_DIRETA) and uf != 'SP': # type: ignore
            prioridade = 3
        # P7: Atacadao 183 - por ultimo (evitar ruptura em outros)
        elif grupo == 'atacadao' and eh_atacadao_183(cliente):
            prioridade = 7
        # P4: Atacadao (EXCETO loja 183)
        elif grupo == 'atacadao':
            prioridade = 4
        # P5: Assai
        elif grupo == 'assai':
            prioridade = 5
        # P6: Resto ordenado por data_pedido (mais antigo primeiro)
        else:
            prioridade = 6

        # Filtrar por prioridade se especificado
        if prioridade_filtro and prioridade != prioridade_filtro:
            continue

        # Verificar se ja separado
        sep_info = separados_dict.get(num_pedido)
        ja_separado = sep_info is not None

        # Verificar agendamento
        forma_agenda = agendamentos_dict.get(cnpj)
        exige_agenda = forma_agenda and forma_agenda.upper() != 'SEM AGENDAMENTO'

        # ANALISAR DISPONIBILIDADE
        disponibilidade = analisar_disponibilidade_pedido(num_pedido, dados['itens'], estoque_dict, projecao_dict)

        # APLICAR REGRAS DE DECISAO
        if ja_separado:
            decisao = {'decisao': 'JA_SEPARADO', 'acao': f"Separado (lote {sep_info['lote_id']})", 'motivo': 'Ja em separacao'}
        else:
            # Usar dias_para_100 da projeção (ou 5 como default se não houver previsão)
            dias_demora = disponibilidade.get('dias_para_100') or 5
            decisao = aplicar_regras_decisao(
                disponibilidade, valor_total,
                pallets=pallets, peso=peso, dias_demora=dias_demora,
                incoterm=incoterm  # Para regra FOB
            )

        # Calcular data de expedicao (SO para prioridade 1)
        data_expedicao = None
        regra_expedicao = None
        opcoes_frete = None  # Para regiões que precisam calcular frete

        if dados['data_entrega_pedido'] and not ja_separado:
            incoterm = dados.get('incoterm')
            resultado_exp = calcular_data_expedicao(dados['data_entrega_pedido'], uf, peso, incoterm=incoterm)

            if resultado_exp['automatico']:
                # SP, RED ou SC/PR>2000kg: data automática
                data_expedicao = resultado_exp['data_expedicao']
                regra_expedicao = resultado_exp['regra']
            else:
                # Outras regiões: calcular opções de frete com lead_time
                opcoes_frete = calcular_opcoes_frete_com_leadtime(
                    data_entrega=dados['data_entrega_pedido'],
                    codigo_ibge=dados.get('codigo_ibge'),
                    peso=peso,
                    valor=valor_total,
                    uf=uf,
                    cidade=dados['cidade']
                )
                if opcoes_frete['sucesso'] and opcoes_frete['mais_rapida']:
                    # Usar data da opção mais rápida como sugestão
                    data_expedicao = opcoes_frete['mais_rapida']['data_expedicao']
                    regra_expedicao = f"D-{opcoes_frete['mais_rapida']['lead_time']} ({opcoes_frete['mais_rapida']['transportadora']})"

        # Gerar comando de separacao se disponivel
        comando_separacao = None
        if decisao['decisao'] in ['DISPONIVEL', 'PARCIAL_AUTOMATICO', 'PARCIAL_CARGA_MAXIMA'] and not ja_separado:
            exp_str = data_expedicao.strftime('%d/%m') if data_expedicao else 'amanha'
            tipo = 'completa' if decisao['decisao'] == 'DISPONIVEL' else 'parcial'
            comando_separacao = f"--pedido {num_pedido} --expedicao {exp_str} --tipo {tipo}"
            # Parciais usam --apenas-estoque ou --pallets limitado
            if decisao['decisao'] == 'PARCIAL_AUTOMATICO':
                comando_separacao += " --apenas-estoque"
            elif decisao['decisao'] == 'PARCIAL_CARGA_MAXIMA':
                # Limitar a 28 pallets (carga de caminhão)
                comando_separacao += " --pallets 28"

        # VERIFICAR SEPARAÇÕES EXISTENTES - sugerir ajustes se data incorreta
        if ja_separado and dados['data_entrega_pedido']:
            incoterm = dados.get('incoterm')
            resultado_exp_correta = calcular_data_expedicao(dados['data_entrega_pedido'], uf, peso, incoterm=incoterm)
            sep_exp_atual = sep_info.get('expedicao')

            if resultado_exp_correta['automatico']:
                # SP/RED/SC-PR>2000kg: cálculo automático
                data_exp_correta = resultado_exp_correta['data_expedicao']
                # Se separação existe mas com data diferente da correta
                if sep_exp_atual and data_exp_correta and sep_exp_atual != data_exp_correta.isoformat():
                    sugestoes_ajuste.append({
                        'pedido': num_pedido,
                        'cliente': dados['cliente'],
                        'uf': uf,
                        'lote_id': sep_info['lote_id'],
                        'expedicao_atual': sep_exp_atual,
                        'expedicao_correta': data_exp_correta.isoformat(),
                        'data_entrega': dados['data_entrega_pedido'].isoformat(),
                        'regra': resultado_exp_correta['regra'],
                        'motivo': f"Entrega {dados['data_entrega_pedido'].strftime('%d/%m')} → Exp {data_exp_correta.strftime('%d/%m')} ({resultado_exp_correta['regra']})"
                    })
            else:
                # Outras regiões: calcular frete com lead_time
                opcoes_frete_ajuste = calcular_opcoes_frete_com_leadtime(
                    data_entrega=dados['data_entrega_pedido'],
                    codigo_ibge=dados.get('codigo_ibge'),
                    peso=peso,
                    valor=valor_total,
                    uf=uf,
                    cidade=dados['cidade']
                )
                if opcoes_frete_ajuste['sucesso'] and opcoes_frete_ajuste['mais_rapida']:
                    data_exp_correta = opcoes_frete_ajuste['mais_rapida']['data_expedicao']
                    lead_time = opcoes_frete_ajuste['mais_rapida']['lead_time']
                    transportadora = opcoes_frete_ajuste['mais_rapida']['transportadora']
                    regra = f"D-{lead_time} ({transportadora})"

                    # Se separação existe mas com data diferente da correta
                    if sep_exp_atual and data_exp_correta and sep_exp_atual != data_exp_correta.isoformat():
                        sugestoes_ajuste.append({
                            'pedido': num_pedido,
                            'cliente': dados['cliente'],
                            'uf': uf,
                            'lote_id': sep_info['lote_id'],
                            'expedicao_atual': sep_exp_atual,
                            'expedicao_correta': data_exp_correta.isoformat(),
                            'data_entrega': dados['data_entrega_pedido'].isoformat(),
                            'regra': regra,
                            'opcoes_frete': opcoes_frete_ajuste,
                            'motivo': f"Entrega {dados['data_entrega_pedido'].strftime('%d/%m')} → Exp {data_exp_correta.strftime('%d/%m')} ({regra})"
                        })

        # GERAR COMUNICACOES
        if disponibilidade['itens_com_falta'] and not ja_separado:
            # PCP: agrupar por PRODUTO - acumular DEMANDA (não falta individual)
            for item_falta in disponibilidade['itens_com_falta']:
                cod = item_falta['cod_produto']
                comunicacoes_pcp[cod]['nome_produto'] = item_falta['nome_produto']
                # Buscar nome resumido da palletização (ex: "AZ VF - POUCH 150G - CAMPO BELO")
                pal_info = palletizacao_dict.get(cod, {})
                comunicacoes_pcp[cod]['nome_resumido'] = pal_info.get('nome_resumido')
                # CORRIGIDO: acumular DEMANDA, não falta individual
                comunicacoes_pcp[cod]['qtd_demandada'] += item_falta['qtd_necessaria']

                # RUPTURA PREVISTA: verificar dia_ruptura da projeção
                proj_info = projecao_dict.get(cod, {})
                if proj_info.get('dia_ruptura'):
                    comunicacoes_pcp[cod]['dia_ruptura'] = proj_info['dia_ruptura']

                if num_pedido not in comunicacoes_pcp[cod]['pedidos_afetados']:
                    comunicacoes_pcp[cod]['pedidos_afetados'].append(num_pedido)

            # Comercial: se precisa consultar
            if decisao['decisao'] == 'CONSULTAR_COMERCIAL':
                # Usar nome resumido (MP - EMBALAGEM - CATEGORIA) se disponível
                produtos_falta = []
                for i in disponibilidade['itens_com_falta']:
                    pal_info = palletizacao_dict.get(i['cod_produto'], {})
                    nome_exibir = pal_info.get('nome_resumido') or i['nome_produto']
                    produtos_falta.append(f"{nome_exibir} ({i['falta']:.0f} un)")
                comunicacoes_comercial[gestor['nome']].append({
                    'pedido': num_pedido,
                    'cliente': dados['cliente'],
                    'valor': round(valor_total, 2),
                    'produtos_faltantes': produtos_falta,
                    'percentual_falta': disponibilidade['percentual_falta'],
                    'canal': gestor['canal']
                })

        # Preparar opcoes_frete para output (serializar datas)
        opcoes_frete_output = None
        if opcoes_frete and opcoes_frete['sucesso']:
            opcoes_frete_output = {
                'sucesso': True,
                'mais_barata': {
                    'transportadora': opcoes_frete['mais_barata']['transportadora'],
                    'valor_frete': opcoes_frete['mais_barata']['valor_frete'],
                    'lead_time': opcoes_frete['mais_barata']['lead_time'],
                    'data_expedicao': opcoes_frete['mais_barata']['data_expedicao'].isoformat() if opcoes_frete['mais_barata']['data_expedicao'] else None,
                    'destaque': opcoes_frete['mais_barata']['destaque']
                } if opcoes_frete['mais_barata'] else None,
                'mais_rapida': {
                    'transportadora': opcoes_frete['mais_rapida']['transportadora'],
                    'valor_frete': opcoes_frete['mais_rapida']['valor_frete'],
                    'lead_time': opcoes_frete['mais_rapida']['lead_time'],
                    'data_expedicao': opcoes_frete['mais_rapida']['data_expedicao'].isoformat() if opcoes_frete['mais_rapida']['data_expedicao'] else None,
                    'destaque': opcoes_frete['mais_rapida']['destaque']
                } if opcoes_frete['mais_rapida'] else None,
                'total_opcoes': len(opcoes_frete['opcoes'])
            }

        pedidos.append({
            'num_pedido': num_pedido,
            'cnpj_cpf': cnpj,
            'cliente': dados['cliente'],
            'cidade': dados['cidade'],
            'uf': uf,
            'incoterm': dados.get('incoterm'),
            'data_pedido': dados['data_pedido'].isoformat() if dados.get('data_pedido') else None,  # Para ordenar P6
            'data_entrega_pedido': dados['data_entrega_pedido'].isoformat() if dados['data_entrega_pedido'] else None,
            'data_expedicao': data_expedicao.isoformat() if data_expedicao else None,
            'regra_expedicao': regra_expedicao,
            'valor_total': round(valor_total, 2),
            'qtd_itens': len(dados['itens']),
            'peso_total': round(peso, 2),
            'pallets_total': round(pallets, 2),
            'prioridade': prioridade,
            'grupo': grupo,
            'tipo_cliente': tipo_cliente,
            'exige_agenda': exige_agenda,
            'forma_agenda': forma_agenda,
            'ja_separado': ja_separado,
            'separacao_info': sep_info,
            'gestor': gestor,
            'disponibilidade': {
                'percentual_disponivel': disponibilidade['percentual_disponivel'],
                'itens_disponiveis': disponibilidade['qtd_disponiveis'],
                'itens_com_falta': disponibilidade['qtd_com_falta'],
                # Usar nome resumido (MP - EMBALAGEM - CATEGORIA) se disponível
                'produtos_faltantes': [palletizacao_dict.get(i['cod_produto'], {}).get('nome_resumido') or i['nome_produto'] for i in disponibilidade['itens_com_falta']],
                'data_100_disponivel': disponibilidade.get('data_100_disponivel'),
                'dias_para_100': disponibilidade.get('dias_para_100')
            },
            'decisao': decisao,
            'comando_separacao': comando_separacao,
            'opcoes_frete': opcoes_frete_output  # NOVO: opções de frete (para regiões não-SP/RED)
        })

    # Ordenar por prioridade, depois por data_pedido (mais antigo primeiro)
    # Para P6 (resto): data_pedido mais antiga primeiro
    # Para outras prioridades: mantém ordem por valor decrescente como fallback
    pedidos.sort(key=lambda x: (
        x['prioridade'],
        x['data_pedido'] if x['data_pedido'] else '9999-12-31',  # Mais antigo primeiro, None vai pro final
        -x['valor_total']  # Fallback: maior valor primeiro
    ))

    # Limitar
    if limit:
        pedidos = pedidos[:limit]

    # ==========================================================
    # 5. ORGANIZAR RESULTADO
    # ==========================================================
    resultado_por_prioridade = defaultdict(list)

    # PEDIDOS DISPONIVEIS: pedidos que PODEM ser separados (ainda não estão em separação)
    pedidos_disponiveis = []

    # PCP: agrupado por PRODUTO
    pcp_por_produto = []

    # COMERCIAL: agrupado por GESTOR
    comercial_por_gestor = defaultdict(list)

    for ped in pedidos:
        resultado_por_prioridade[ped['prioridade']].append(ped)

        # Pedidos DISPONIVEIS para criar separação (ainda NÃO estão em separação)
        if ped['decisao']['decisao'] in ['DISPONIVEL', 'PARCIAL_AUTOMATICO', 'PARCIAL_CARGA_MAXIMA'] and not ped['ja_separado']:
            # P3 com agenda: calcular sugestão D+3+leadtime
            sugestao_agendamento = None
            if ped['prioridade'] == 3 and ped['exige_agenda']:
                # Buscar lead_time das opções de frete, ou usar default 3
                lead_time = 3
                if ped.get('opcoes_frete') and ped['opcoes_frete'].get('mais_rapida'):
                    lead_time = ped['opcoes_frete']['mais_rapida'].get('lead_time', 3)
                sugestao_agendamento = calcular_sugestao_agendamento(lead_time)

            pedidos_disponiveis.append({
                'pedido': ped['num_pedido'],
                'cliente': ped['cliente'],
                'uf': ped['uf'],
                'prioridade': ped['prioridade'],  # Para identificar P3
                'valor': ped['valor_total'],
                'data_entrega': ped['data_entrega_pedido'],  # Data negociada com cliente
                'expedicao': ped['data_expedicao'],          # Data calculada para expedição
                'regra_expedicao': ped.get('regra_expedicao'),  # Regra aplicada (D-1, D-2, etc)
                'tipo': ped['decisao']['decisao'],           # DISPONIVEL, PARCIAL_AUTOMATICO ou PARCIAL_CARGA_MAXIMA
                'exige_agendamento': ped['exige_agenda'],
                'forma_agendamento': ped['forma_agenda'],
                'sugestao_agendamento': sugestao_agendamento,  # P3 com agenda: D+3+leadtime
                'comando': ped['comando_separacao'],
                'opcoes_frete': ped.get('opcoes_frete')  # Opções de frete (se calculadas)
            })

    # Formatar PCP por PRODUTO - calcular FALTA REAL = demanda - estoque
    for cod_produto, info in comunicacoes_pcp.items():
        # Buscar estoque atual do produto
        estoque_atual = estoque_dict.get(cod_produto, 0)
        qtd_demandada = info['qtd_demandada']
        # CORRIGIDO: falta = max(0, demanda - estoque)
        qtd_faltante = max(0, qtd_demandada - estoque_atual)

        # Só incluir se realmente falta algo
        if qtd_faltante > 0:
            nome_exibir = info.get('nome_resumido') or info['nome_produto']
            dia_ruptura = info.get('dia_ruptura')

            # Montar mensagem com urgência se houver ruptura prevista
            msg = f"Precisamos de {qtd_faltante:.0f} un de {nome_exibir} ({len(info['pedidos_afetados'])} pedidos aguardando)"
            if dia_ruptura:
                msg += f" ⚠️ RUPTURA PREVISTA em {dia_ruptura}"

            pcp_por_produto.append({
                'produto': nome_exibir,
                'produto_completo': info['nome_produto'],
                'cod_produto': cod_produto,
                'qtd_demandada': round(qtd_demandada, 0),
                'estoque_atual': round(estoque_atual, 0),
                'qtd_faltante': round(qtd_faltante, 0),
                'qtd_pedidos': len(info['pedidos_afetados']),
                'pedidos': info['pedidos_afetados'][:10],  # Limitar para não poluir
                'dia_ruptura': dia_ruptura,  # Data em que estoque fica negativo
                'mensagem_pcp': msg
            })

    # Ordenar por quantidade faltante (maior primeiro)
    pcp_por_produto.sort(key=lambda x: -x['qtd_faltante'])

    # Formatar COMERCIAL por GESTOR
    for gestor_nome, pedidos_gestor in comunicacoes_comercial.items():
        canal = pedidos_gestor[0]['canal'] if pedidos_gestor else 'WhatsApp'
        comercial_por_gestor[gestor_nome] = {
            'canal': canal,
            'total_pedidos': len(pedidos_gestor),
            'valor_total': sum(p['valor'] for p in pedidos_gestor),
            'pedidos': [{
                'pedido': p['pedido'],
                'cliente': p['cliente'],
                'valor': p['valor'],
                'percentual_falta': p['percentual_falta'],
                'produtos_faltantes': p['produtos_faltantes']
            } for p in pedidos_gestor]
        }

    total_valor = sum(p['valor_total'] for p in pedidos)

    resumo = {
        'total_pedidos': len(pedidos),
        'total_valor': round(total_valor, 2),
        'ja_separados': len([p for p in pedidos if p['ja_separado']]),
        'disponiveis_para_separar': len(pedidos_disponiveis),
        'consultar_comercial': len([p for p in pedidos if p['decisao']['decisao'] == 'CONSULTAR_COMERCIAL']),
        'aguardar_producao': len([p for p in pedidos if p['decisao']['decisao'] == 'AGUARDAR']),
        'produtos_com_falta': len(pcp_por_produto),
        'por_prioridade': {
            k: {'qtd': len(v), 'valor': round(sum(p['valor_total'] for p in v), 2)}
            for k, v in resultado_por_prioridade.items()
        }
    }

    return {
        'sucesso': True,
        'data_analise': hoje.isoformat(),
        'total_pedidos': len(pedidos),
        'resumo': resumo,

        # 1. PEDIDOS DISPONIVEIS (podem ser separados, ainda não estão em separação)
        'pedidos_disponiveis': pedidos_disponiveis,

        # 2. PCP (agrupado por PRODUTO)
        'pcp': pcp_por_produto,

        # 3. COMERCIAL (agrupado por GESTOR)
        'comercial': dict(comercial_por_gestor),

        # 4. SUGESTÕES DE AJUSTE (separações existentes com data incorreta)
        'sugestoes_ajuste': sugestoes_ajuste,

        # Detalhes por prioridade (opcional, para drill-down)
        'prioridades': {
            '1_data_entrega': resultado_por_prioridade.get(1, []),
            '2_fob': resultado_por_prioridade.get(2, []),
            '3_carga_direta': resultado_por_prioridade.get(3, []),
            '4_atacadao': resultado_por_prioridade.get(4, []),
            '5_assai': resultado_por_prioridade.get(5, []),
            '6_outros': resultado_por_prioridade.get(6, []),
            '7_atacadao_183': resultado_por_prioridade.get(7, [])
        }
    }


def gerar_resumo_executivo(analise: dict) -> str:
    """Gera resumo executivo da analise"""
    resumo = analise['resumo']
    pedidos_disponiveis = analise.get('pedidos_disponiveis', [])
    pcp = analise.get('pcp', [])
    comercial = analise.get('comercial', {})
    sugestoes_ajuste = analise.get('sugestoes_ajuste', [])

    linhas = [
        "=" * 70,
        "RESUMO EXECUTIVO - ANALISE DA CARTEIRA (Clone do Rafael)",
        f"Data: {analise['data_analise']}",
        "=" * 70,
        "",
        f"Total de pedidos: {resumo['total_pedidos']}",
        f"Valor total: R$ {resumo['total_valor']:,.2f}",
        "",
        "STATUS:",
        f"  Ja separados: {resumo['ja_separados']}",
        f"  Disponiveis para separar: {resumo['disponiveis_para_separar']}",
        f"  Consultar comercial: {resumo['consultar_comercial']}",
        f"  Aguardar producao: {resumo['aguardar_producao']}",
        f"  Produtos com falta: {resumo['produtos_com_falta']}",
        "",
        "POR PRIORIDADE:"
    ]

    for prio, dados in sorted(resumo['por_prioridade'].items()):
        linhas.append(f"  P{prio}: {dados['qtd']} pedidos - R$ {dados['valor']:,.2f}")

    # PEDIDOS DISPONIVEIS
    if pedidos_disponiveis:
        linhas.extend(["", "-" * 70, "PEDIDOS DISPONIVEIS PARA SEPARAR:", "-" * 70])
        for ped in pedidos_disponiveis[:25]:
            agenda_str = f" - AGENDA: {ped['forma_agendamento']}" if ped['exige_agendamento'] else ""
            entrega_str = f" - Entrega: {ped['data_entrega']}" if ped.get('data_entrega') else ""
            tipo_str = f" [{ped['tipo']}]" if ped.get('tipo') in ['PARCIAL_AUTOMATICO', 'PARCIAL_CARGA_MAXIMA'] else ""
            regra_str = f" ({ped['regra_expedicao']})" if ped.get('regra_expedicao') else ""
            uf_str = f" [{ped.get('uf', '')}]"
            linhas.append(f"  {ped['pedido']} - {ped['cliente'][:25]}{uf_str} - R$ {ped['valor']:,.0f} - Exp: {ped['expedicao'] or 'definir'}{regra_str}{entrega_str}{agenda_str}{tipo_str}")

            # Se tem opções de frete (região que não é SP/RED/SC-PR>2000kg)
            if ped.get('opcoes_frete') and ped['opcoes_frete'].get('sucesso'):
                frete = ped['opcoes_frete']
                if frete.get('mais_barata') and frete.get('mais_rapida'):
                    mb = frete['mais_barata']
                    mr = frete['mais_rapida']
                    if mb['destaque'] == 'AMBOS':
                        linhas.append(f"    💰🚀 {mb['transportadora']}: R$ {mb['valor_frete']:,.0f} (D-{mb['lead_time']})")
                    else:
                        linhas.append(f"    💰 MAIS BARATA: {mb['transportadora']} R$ {mb['valor_frete']:,.0f} (D-{mb['lead_time']})")
                        if mr['transportadora'] != mb['transportadora']:
                            linhas.append(f"    🚀 MAIS RAPIDA: {mr['transportadora']} R$ {mr['valor_frete']:,.0f} (D-{mr['lead_time']})")

            # P3 com agenda: mostrar sugestão de agendamento D+3+leadtime
            if ped.get('sugestao_agendamento'):
                sug = ped['sugestao_agendamento']
                linhas.append(f"    📅 AGENDAR: {sug['resumo']}")

    # PCP (por produto)
    if pcp:
        linhas.extend(["", "-" * 70, "PCP - PRODUTOS COM FALTA:", "-" * 70])
        for p in pcp[:10]:
            ruptura_str = f" ⚠️ RUPTURA: {p['dia_ruptura']}" if p.get('dia_ruptura') else ""
            linhas.append(f"  {p['produto'][:40]}: {p['qtd_faltante']:.0f} un ({p['qtd_pedidos']} pedidos){ruptura_str}")

    # COMERCIAL (por gestor)
    if comercial:
        linhas.extend(["", "-" * 70, "COMERCIAL - CONSULTAR GESTORES:", "-" * 70])
        for gestor, dados in comercial.items():
            linhas.append(f"\n  [{gestor}] ({dados['canal']}) - {dados['total_pedidos']} pedidos - R$ {dados['valor_total']:,.0f}")
            for ped in dados['pedidos'][:10]:
                prods = ', '.join(p.split(' (')[0][:15] for p in ped['produtos_faltantes'][:5])
                linhas.append(f"    {ped['pedido']} | {ped['cliente'][:20]} | R$ {ped['valor']:,.0f} | falta {ped['percentual_falta']:.0f}% | {prods}")

    # SUGESTÕES DE AJUSTE (separações com data incorreta)
    if sugestoes_ajuste:
        linhas.extend(["", "-" * 70, "⚠️ AJUSTES SUGERIDOS (separações com data incorreta):", "-" * 70])
        for aj in sugestoes_ajuste[:10]:
            uf_str = f" [{aj.get('uf', '')}]" if aj.get('uf') else ""
            linhas.append(f"  {aj['pedido']} - {aj['cliente'][:25]}{uf_str} - Exp: {aj['expedicao_atual']} → {aj['expedicao_correta']}")
            linhas.append(f"    {aj['motivo']}")
            # Se tem opções de frete (região calculada)
            if aj.get('opcoes_frete') and aj['opcoes_frete'].get('sucesso'):
                frete = aj['opcoes_frete']
                if frete.get('mais_barata') and frete.get('mais_rapida'):
                    mb = frete['mais_barata']
                    mr = frete['mais_rapida']
                    if mb.get('destaque') == 'AMBOS':
                        linhas.append(f"    💰🚀 {mb['transportadora']}: R$ {mb['valor_frete']:,.0f} (D-{mb['lead_time']})")
                    else:
                        linhas.append(f"    💰 MAIS BARATA: {mb['transportadora']} R$ {mb['valor_frete']:,.0f} (D-{mb['lead_time']})")
                        if mr['transportadora'] != mb['transportadora']:
                            linhas.append(f"    🚀 MAIS RAPIDA: {mr['transportadora']} R$ {mr['valor_frete']:,.0f} (D-{mr['lead_time']})")

    linhas.append("\n" + "=" * 70)
    return "\n".join(linhas)


def main():
    parser = argparse.ArgumentParser(
        description='Analisa carteira completa seguindo algoritmo do Rafael (Clone)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Prioridades:
  1 = Pedidos com data_entrega_pedido (NAO AVALIAR, EXECUTAR)
  2 = FOB (cliente coleta) - SEMPRE COMPLETO
  3 = Cargas diretas fora de SP (>=26 pallets ou >=20.000kg)
  4 = Atacadao (EXCETO loja 183)
  5 = Assai
  6 = Resto ordenado por data_pedido (mais antigo primeiro)
  7 = Atacadao 183 (por ultimo - evitar ruptura)

Exemplos:
  python analisando_carteira_completa.py                    # Analise completa
  python analisando_carteira_completa.py --resumo           # Apenas resumo executivo
  python analisando_carteira_completa.py --prioridade 1     # Pedidos com data negociada
  python analisando_carteira_completa.py --prioridade 2     # Pedidos FOB
  python analisando_carteira_completa.py --prioridade 4     # Atacadao (exceto 183)
  python analisando_carteira_completa.py --prioridade 7     # Atacadao 183
  python analisando_carteira_completa.py --limit 20         # Limitar a 20 pedidos
        """
    )

    parser.add_argument('--resumo', action='store_true', help='Mostrar apenas resumo executivo')
    parser.add_argument('--prioridade', type=int, choices=[1, 2, 3, 4, 5, 6, 7], help='Filtrar por prioridade (1-7)')
    parser.add_argument('--limit', type=int, default=None, help='Limite de pedidos')
    parser.add_argument('--acoes', action='store_true', help='Mostrar apenas acoes')

    args = parser.parse_args()

    try:
        from app import create_app
        app = create_app()

        with app.app_context():
            resultado = analisar_carteira_completa(
                limit=args.limit,
                prioridade_filtro=args.prioridade
            )

        if args.resumo:
            print(gerar_resumo_executivo(resultado))
        elif args.acoes:
            print(json.dumps(resultado['acoes'], indent=2, default=decimal_default, ensure_ascii=False))
        else:
            print(json.dumps(resultado, indent=2, default=decimal_default, ensure_ascii=False))

    except Exception as e:
        import traceback
        print(json.dumps({
            'sucesso': False,
            'erro': str(e),
            'tipo_erro': type(e).__name__,
            'traceback': traceback.format_exc()
        }, indent=2, ensure_ascii=False))
        sys.exit(1)


if __name__ == '__main__':
    main()

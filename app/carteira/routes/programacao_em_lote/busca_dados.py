"""
Módulo de busca de dados para programação em lote
Move a lógica de busca do preencher_planilha.py para cá
Tornando preencher_planilha.py universal
"""

from typing import Dict, Any, List
from decimal import Decimal
from datetime import date
from sqlalchemy import func, and_, exists
import logging

from app import db
from app.carteira.models import CarteiraPrincipal, SaldoStandby
from app.separacao.models import Separacao
from app.portal.sendas.utils_protocolo import gerar_protocolo_sendas
from app.producao.models import CadastroPalletizacao
from app.odoo.utils.pedido_cliente_utils import buscar_pedido_cliente_odoo
from app.utils.text_utils import truncar_observacao

logger = logging.getLogger(__name__)


def buscar_dados_completos_cnpj(cnpj: str, data_agendamento: date = None,
                                data_expedicao: date = None, protocolo: str = None) -> Dict[str, Any]:
    """
    Busca dados completos de um CNPJ para agendamento Sendas
    Consolida dados de 2 fontes:
    1. CarteiraPrincipal (inclui tudo não faturado - sincronizado_nf=False)
    2. Separacao com nf_cd=True (NFs que voltaram ao CD)

    Args:
        cnpj: CNPJ para buscar dados
        data_agendamento: Data de agendamento
        data_expedicao: Data de expedição (para SP, será D-1 do agendamento)
        protocolo: Protocolo do agendamento (se não fornecido, será gerado)

    Returns:
        Dicionário com estrutura unificada para agendamento
    """
    logger.info(f"📊 Buscando dados completos para CNPJ: {cnpj}")

    # ✅ CORREÇÃO CRÍTICA: SEMPRE usar protocolo fornecido, NUNCA gerar novo
    # Isso evita divergência de horário entre FilaAgendamentoSendas e Separacao
    # O protocolo DEVE ser gerado uma única vez e propagado para todos os lugares
    if not protocolo:
        logger.warning(f"⚠️ ATENÇÃO: buscar_dados_completos_cnpj chamado SEM protocolo para CNPJ {cnpj}. Não será gerado novo protocolo.")
        # NÃO gerar novo protocolo aqui para evitar inconsistências
        # protocolo = gerar_protocolo_sendas(cnpj, data_agendamento) if data_agendamento else None

    dados = {
        'cnpj': cnpj,
        'data_agendamento': data_agendamento,
        'data_expedicao': data_expedicao,
        'protocolo': protocolo,  # Pode ser None se não foi fornecido
        'itens': [],
        'peso_total': Decimal('0'),
        'pallets_total': Decimal('0'),
        'valor_total': Decimal('0')
    }

    # BUSCAR TODAS AS SEPARAÇÕES DE UMA VEZ (sincronizado_nf=False + nf_cd=True)
    # Nota: NÃO buscamos mais em CarteiraPrincipal pois já criamos Separações do saldo
    logger.info("  📋 Buscando todas as Separações (não faturadas + NFs no CD)...")
    itens_separacao = _buscar_todas_separacoes(cnpj, protocolo)
    dados['itens'].extend(itens_separacao)

    # 3. GARANTIR pedido_cliente PARA TODOS OS ITENS
    logger.info("  🔍 Validando pedido_cliente...")
    _garantir_pedido_cliente(dados['itens'])

    # 4. CALCULAR TOTAIS
    for item in dados['itens']:
        dados['peso_total'] += Decimal(str(item.get('peso', 0)))
        dados['pallets_total'] += Decimal(str(item.get('pallets', 0)))
        dados['valor_total'] += Decimal(str(item.get('valor', 0)))

    # 5. ADICIONAR DADOS DE EXPEDIÇÃO
    if data_expedicao:
        for item in dados['itens']:
            item['data_expedicao'] = data_expedicao

    logger.info(f"  ✅ Total: {len(dados['itens'])} itens, Peso: {dados['peso_total']:.2f} kg")

    return dados


def _buscar_todas_separacoes(cnpj: str, protocolo: str = None) -> List[Dict[str, Any]]:
    """
    Busca TODAS as Separações relevantes para agendamento:
    - sincronizado_nf=False (não faturadas, incluindo as criadas do saldo)
    - nf_cd=True (NFs que voltaram ao CD)

    Com o protocolo fornecido, busca apenas as do agendamento atual.
    """
    itens = []

    try:
        # Query unificada: buscar TODAS as separações relevantes
        query = db.session.query(Separacao).filter(
            and_(
                Separacao.cnpj_cpf == cnpj,
                Separacao.qtd_saldo > 0,  # ✅ FILTRO: apenas qtd > 0
                db.or_(
                    Separacao.sincronizado_nf == False,  # Não faturadas
                    Separacao.nf_cd == True              # NFs no CD
                )
            )
        )

        # Se temos protocolo, filtrar apenas as deste agendamento
        if protocolo:
            query = query.filter(Separacao.protocolo == protocolo)

        separacoes = query.all()
        logger.info(f"    Encontradas {len(separacoes)} separações para o CNPJ {cnpj}")

        for sep in separacoes:
            # Buscar nome do produto se não tiver
            nome_produto = sep.nome_produto
            if not nome_produto:
                pallet_cadastro = db.session.query(
                    CadastroPalletizacao.nome_produto
                ).filter(
                    CadastroPalletizacao.cod_produto == sep.cod_produto
                ).first()

                if pallet_cadastro:
                    nome_produto = pallet_cadastro.nome_produto

            # Tipo origem unificado - tudo é Separação agora
            tipo_origem = 'separacao'

            itens.append({
                'id': sep.id,  # Para update posterior
                'tipo_origem': tipo_origem,
                'separacao_lote_id': sep.separacao_lote_id,
                'num_pedido': sep.num_pedido,
                'numero_nf': sep.numero_nf if hasattr(sep, 'numero_nf') else None,
                'pedido_cliente': sep.pedido_cliente,
                'cod_produto': sep.cod_produto,
                'nome_produto': nome_produto or f"Produto {sep.cod_produto}",
                'quantidade': float(sep.qtd_saldo or 0),
                'peso': float(sep.peso or 0),
                'pallets': float(sep.pallet or 0),
                'valor': float(sep.valor_saldo or 0),
                'expedicao': sep.expedicao,
                'agendamento': sep.agendamento,
                'protocolo': sep.protocolo,
                'observacoes': sep.observ_ped_1,
                'status': sep.status,
                'tipo_envio': sep.tipo_envio if hasattr(sep, 'tipo_envio') else None,
                'nf_cd': sep.nf_cd,
                'sincronizado_nf': sep.sincronizado_nf
            })
    except Exception as e:
        logger.error(f"Erro ao buscar separações: {e}")
        db.session.rollback()

    return itens


def _garantir_pedido_cliente(itens: List[Dict[str, Any]]) -> None:
    """
    Garante que todos os itens tenham pedido_cliente preenchido
    Busca do Odoo quando necessário
    """
    # Agrupar por num_pedido para buscar uma vez só
    pedidos_sem_cliente = {}

    for item in itens:
        if not item.get('pedido_cliente') and item.get('num_pedido'):
            pedidos_sem_cliente[item['num_pedido']] = None

    # Buscar do Odoo em lote se houver pedidos sem cliente
    if pedidos_sem_cliente:
        logger.info(f"    📡 Buscando pedido_cliente do Odoo para {len(pedidos_sem_cliente)} pedidos...")

        for num_pedido in pedidos_sem_cliente:
            try:
                pedido_cliente = buscar_pedido_cliente_odoo(num_pedido)
                if pedido_cliente:
                    pedidos_sem_cliente[num_pedido] = pedido_cliente
                    logger.info(f"      ✅ Pedido {num_pedido}: {pedido_cliente}")
                else:
                    logger.warning(f"      ⚠️ Pedido {num_pedido}: não encontrado no Odoo")
            except Exception as e:
                logger.error(f"      ❌ Erro ao buscar pedido {num_pedido}: {e}")

        # Atualizar itens com pedido_cliente do Odoo
        for item in itens:
            if not item.get('pedido_cliente') and item.get('num_pedido'):
                pedido_cliente_odoo = pedidos_sem_cliente.get(item['num_pedido'])
                if pedido_cliente_odoo:
                    item['pedido_cliente'] = pedido_cliente_odoo


def buscar_dados_multiplos_cnpjs(lista_cnpjs_agendamento: List[Dict]) -> List[Dict[str, Any]]:
    """
    Busca dados completos para múltiplos CNPJs

    Args:
        lista_cnpjs_agendamento: Lista de dicts com cnpj, data_agendamento, data_expedicao

    Returns:
        Lista de dicionários com dados completos por CNPJ
    """
    dados_completos = []

    for config in lista_cnpjs_agendamento:
        cnpj = config.get('cnpj')
        data_agendamento = config.get('data_agendamento')
        data_expedicao = config.get('data_expedicao')

        if not cnpj:
            continue

        dados = buscar_dados_completos_cnpj(
            cnpj=cnpj,
            data_agendamento=data_agendamento,
            data_expedicao=data_expedicao
        )

        dados_completos.append(dados)

    return dados_completos


def criar_separacoes_do_saldo(cnpj: str, data_agendamento: date, data_expedicao: date = None,
                              protocolo: str = None) -> int:
    """
    (descontando o que já está em Separacao.sincronizado_nf=False)
    e atualiza Separações existentes com o protocolo do agendamento.

    Args:
        cnpj: CNPJ para criar separações
        data_agendamento: Data de agendamento
        data_expedicao: Data de expedição (para SP, será D-1 do agendamento)
        protocolo: Protocolo único do agendamento (se não fornecido, será gerado)

    Returns:
        Número total de registros criados/atualizados
    """
    from app.separacao.models import Separacao
    from app.utils.lote_utils import gerar_lote_id

    logger.info(f"📦 Criando Separações do saldo para CNPJ: {cnpj}")

    # ✅ CORREÇÃO CRÍTICA: SEMPRE usar protocolo fornecido, NUNCA gerar novo
    # Isso evita divergência de horário entre FilaAgendamentoSendas e Separacao
    if not protocolo:
        logger.error(f"❌ ERRO CRÍTICO: criar_separacoes_do_saldo chamado SEM protocolo para CNPJ {cnpj}!")
        raise ValueError(f"Protocolo é obrigatório para criar_separacoes_do_saldo. CNPJ: {cnpj}")

    contador_criadas = 0
    contador_atualizadas = 0

    try:
        # 1. BUSCAR O QUE JÁ ESTÁ EM SEPARAÇÃO (para descontar do saldo)
        # ✅ CORRIGIDO: Excluir separações do protocolo atual para evitar duplicação
        logger.info("  📊 Calculando saldo líquido...")

        # Agrupar quantidades já em separação por num_pedido e cod_produto
        # ✅ CORREÇÃO: Incluir TODAS as separações não faturadas (de qualquer protocolo)
        # Antes excluía o protocolo atual, causando duplicação na 2ª chamada
        ja_em_separacao = db.session.query(
            Separacao.num_pedido,
            Separacao.cod_produto,
            func.sum(Separacao.qtd_saldo).label('qtd_ja_separada')
        ).filter(
            and_(
                Separacao.cnpj_cpf == cnpj,
                Separacao.sincronizado_nf == False  # Apenas não faturadas
            )
        ).group_by(
            Separacao.num_pedido,
            Separacao.cod_produto
        ).all()

        # Criar dicionário para lookup rápido
        dict_ja_separado = {}
        pedidos_com_separacao = set()  # Para rastrear pedidos que já têm separação
        for sep in ja_em_separacao:
            chave = f"{sep.num_pedido}_{sep.cod_produto}"
            dict_ja_separado[chave] = float(sep.qtd_ja_separada or 0)
            pedidos_com_separacao.add(sep.num_pedido)  # Marcar pedido como tendo separação

        # 2. CRIAR SEPARAÇÕES DO SALDO LÍQUIDO DA CARTEIRA PRINCIPAL
        logger.info("  📋 Buscando saldo em CarteiraPrincipal...")

        # Buscar todos os itens com saldo
        # Subquery: pedidos em standby ativo (excluir da criação de separações)
        standby_ativo = exists().where(
            and_(
                SaldoStandby.num_pedido == CarteiraPrincipal.num_pedido,
                SaldoStandby.status_standby.in_(['ATIVO', 'BLOQ. COML.', 'SALDO'])
            )
        )

        itens_carteira = db.session.query(
            CarteiraPrincipal
        ).filter(
            and_(
                CarteiraPrincipal.cnpj_cpf == cnpj,
                CarteiraPrincipal.ativo == True,
                CarteiraPrincipal.qtd_saldo_produto_pedido > 0,
                ~standby_ativo  # M1: Excluir pedidos em standby
            )
        ).all()

        logger.info(f"    ✅ Encontrados {len(itens_carteira)} itens na CarteiraPrincipal com saldo > 0")

        if len(itens_carteira) == 0:
            logger.warning(f"    ⚠️ ATENÇÃO: Nenhum item encontrado na CarteiraPrincipal para CNPJ {cnpj}")
            logger.warning(f"       Verifique se:")
            logger.warning(f"       1. O CNPJ está correto: {cnpj}")
            logger.warning(f"       2. Existem pedidos com qtd_saldo_produto_pedido > 0")
            logger.warning(f"       3. Os itens estão com ativo=True")

        # Agrupar itens por num_pedido para gerar um separacao_lote_id único por pedido
        pedidos_agrupados = {}
        for item in itens_carteira:
            if item.num_pedido not in pedidos_agrupados:
                pedidos_agrupados[item.num_pedido] = []
            pedidos_agrupados[item.num_pedido].append(item)

        logger.info(f"    Agrupados em {len(pedidos_agrupados)} pedidos diferentes")

        # Processar cada pedido com seu próprio separacao_lote_id
        for num_pedido, itens_do_pedido in pedidos_agrupados.items():
            # Gerar um separacao_lote_id ÚNICO para CADA num_pedido
            separacao_lote_id = gerar_lote_id()
            logger.debug(f"      Pedido {num_pedido}: criando lote {separacao_lote_id}")

            for item in itens_do_pedido:
                # Calcular saldo líquido
                chave_item = f"{item.num_pedido}_{item.cod_produto}"
                qtd_ja_separada = dict_ja_separado.get(chave_item, 0)
                saldo_liquido = float(item.qtd_saldo_produto_pedido) - qtd_ja_separada

                if saldo_liquido <= 0:
                    logger.debug(f"      Item {chave_item} sem saldo líquido (tudo já está em separação)")
                    continue

                # Buscar dados de palletização
                pallet_info = db.session.query(
                    CadastroPalletizacao
                ).filter(
                    CadastroPalletizacao.cod_produto == item.cod_produto
                ).first()

                peso_item = Decimal('0')
                pallets_item = Decimal('0')

                if pallet_info:
                    qtd_decimal = Decimal(str(saldo_liquido))  # Usar saldo líquido
                    peso_item = qtd_decimal * Decimal(str(pallet_info.peso_bruto or 0))
                    if pallet_info.palletizacao and pallet_info.palletizacao > 0:
                        pallets_item = qtd_decimal / Decimal(str(pallet_info.palletizacao))

                # Determinar tipo_envio: 'parcial' se já existe separação, 'total' se não
                tipo_envio = 'parcial' if item.num_pedido in pedidos_com_separacao else 'total'

                # Determinar sub_rota (import lazy para evitar circular import com routes.py)
                from app.carteira.routes.programacao_em_lote.routes import _buscar_sub_rota
                sub_rota = _buscar_sub_rota(item.municipio, item.estado) if item.municipio else None

                nova_separacao = Separacao(
                    separacao_lote_id=separacao_lote_id,
                    status='ABERTO',  # Status para separações criadas para agendamento
                    sincronizado_nf=False,  # Sempre False para aparecer na carteira
                    nf_cd=False,  # Não é NF no CD

                    # Dados do pedido
                    num_pedido=item.num_pedido,
                    data_pedido=item.data_pedido,
                    pedido_cliente=item.pedido_cliente,
                    cod_produto=item.cod_produto,
                    nome_produto=item.nome_produto,
                    qtd_saldo=saldo_liquido,  # SALDO LÍQUIDO!
                    valor_saldo=float(Decimal(str(saldo_liquido)) * Decimal(str(item.preco_produto_pedido or 0))),
                    peso=float(peso_item),
                    pallet=float(pallets_item),

                    # Dados do cliente
                    cnpj_cpf=cnpj,
                    raz_social_red=item.raz_social_red,
                    nome_cidade=item.municipio,
                    cod_uf=item.estado,
                    sub_rota=sub_rota,

                    # Dados do agendamento ✅ CORRIGIDO: preencher com valores fornecidos
                    protocolo=protocolo,
                    agendamento=data_agendamento,  # ✅ Preencher com data fornecida
                    expedicao=data_expedicao,      # ✅ Preencher com data fornecida
                    agendamento_confirmado=False,  # ✅ False para indicar que ainda não foi confirmado no portal

                    # Manter observ_ped_1 original se houver (truncado)
                    observ_ped_1=truncar_observacao(item.observ_ped_1),

                    # Tipo de envio baseado em se já existe separação
                    tipo_envio=tipo_envio
                )

                db.session.add(nova_separacao)
                contador_criadas += 1

                # Após criar, marcar o pedido como tendo separação
                pedidos_com_separacao.add(item.num_pedido)

                logger.debug(f"      Criada Separação para {chave_item}: {saldo_liquido} unidades (tipo: {tipo_envio})")

        # 3. ATUALIZAR SEPARAÇÕES EXISTENTES COM PROTOCOLO, EXPEDIÇÃO E AGENDAMENTO
        # M2: Sobrescrever protocolo em TODAS separações não-faturadas do CNPJ
        # Re-agendamento DEVE atualizar separações com protocolo anterior
        # M3: Excluir pedidos em standby do update de protocolo
        standby_sep = exists().where(
            and_(
                SaldoStandby.num_pedido == Separacao.num_pedido,
                SaldoStandby.status_standby.in_(['ATIVO', 'BLOQ. COML.', 'SALDO'])
            )
        )

        logger.info("  📝 Atualizando TODAS Separações não faturadas do CNPJ (exceto standby)...")
        resultado_nao_fat = Separacao.query.filter(
            and_(
                Separacao.cnpj_cpf == cnpj,
                Separacao.sincronizado_nf == False,
                ~standby_sep  # M3: Excluir pedidos em standby
            )
        ).update({
            'protocolo': protocolo,
            'agendamento': data_agendamento,
            'expedicao': data_expedicao,
            'agendamento_confirmado': False
        }, synchronize_session=False)
        contador_atualizadas += resultado_nao_fat

        logger.info("  📄 Atualizando TODAS NFs no CD do CNPJ (exceto standby)...")
        resultado_nf_cd = Separacao.query.filter(
            and_(
                Separacao.cnpj_cpf == cnpj,
                Separacao.nf_cd == True,
                ~standby_sep  # M3: Excluir pedidos em standby
            )
        ).update({
            'protocolo': protocolo,
            'agendamento': data_agendamento,
            'expedicao': data_expedicao,
            'agendamento_confirmado': False
        }, synchronize_session=False)
        contador_atualizadas += resultado_nf_cd

        # Commit das mudanças
        db.session.commit()

        logger.info(f"  ✅ Total: {contador_criadas} Separações criadas, {contador_atualizadas} atualizadas")
        logger.info(f"  ✅ Protocolo: {protocolo}")

        return contador_criadas + contador_atualizadas

    except Exception as e:
        logger.error(f"❌ Erro ao criar Separações do saldo: {e}")
        db.session.rollback()
        raise
"""
Rotas para programação em lote de Redes SP (Atacadão e Sendas)
"""

from flask import render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from sqlalchemy import func, and_, distinct
from decimal import Decimal
from datetime import date, timedelta, datetime
import logging
import traceback

from app import db
from app.carteira.models import CarteiraPrincipal
from app.separacao.models import Separacao
from app.faturamento.models import FaturamentoProduto
from app.producao.models import CadastroPalletizacao
from app.localidades.models import CadastroSubRota
from app.portal.utils.grupo_empresarial import GrupoEmpresarial
from app.estoque.models import MovimentacaoEstoque
from app.producao.models import ProgramacaoProducao
from app.utils.lote_utils import gerar_lote_id
from app.portal.sendas.utils_protocolo import gerar_protocolo_sendas
from .busca_dados import buscar_dados_completos_cnpj

from . import programacao_em_lote_bp

logger = logging.getLogger(__name__)


@programacao_em_lote_bp.route('/listar/<rede>')
@login_required
def listar(rede):
    """
    Lista pedidos agrupados por CNPJ para uma rede específica (Atacadão ou Sendas) em SP
    """
    try:
        # Validar rede selecionada
        if rede not in ['atacadao', 'sendas']:
            flash('Rede inválida selecionada', 'error')
            return redirect(url_for('carteira.index'))
        
        # Mapear rede para portal
        portal_map = {
            'atacadao': 'atacadao',
            'sendas': 'sendas'  # Assaí usa portal sendas
        }
        portal = portal_map[rede]
        
        # Buscar dados agrupados por CNPJ
        dados_cnpj = _buscar_dados_por_rede(portal)
        
        # Pegar vendedor e equipe do primeiro registro (todos são iguais)
        vendedor = None
        equipe_vendas = None
        if dados_cnpj:
            vendedor = dados_cnpj[0].get('vendedor')
            equipe_vendas = dados_cnpj[0].get('equipe_vendas')
        
        # Preparar dados para o template
        contexto = {
            'rede': rede,
            'portal': portal,
            'dados_cnpj': dados_cnpj,
            'total_cnpjs': len(dados_cnpj),
            'data_atual': date.today(),
            'vendedor': vendedor,
            'equipe_vendas': equipe_vendas
        }
        
        return render_template('carteira/programacao_em_lote.html', **contexto)
        
    except Exception as e:
        logger.error(f"Erro ao listar programação em lote: {str(e)}")
        flash(f'Erro ao carregar dados: {str(e)}', 'error')
        return redirect(url_for('carteira.index'))


def _buscar_sub_rota(nome_cidade, cod_uf):
    """
    Busca a sub-rota de uma cidade no CadastroSubRota
    Normaliza o nome da cidade para lidar com acentos
    """
    if not nome_cidade or not cod_uf:
        return None
    
    from app.utils.string_utils import remover_acentos
    
    # Normaliza o nome da cidade removendo acentos
    nome_cidade_normalizado = remover_acentos(nome_cidade)
    
    # Busca todas as sub-rotas ativas para o UF
    sub_rotas = db.session.query(CadastroSubRota).filter(
        and_(
            CadastroSubRota.cod_uf == cod_uf,
            CadastroSubRota.ativa == True
        )
    ).all()
    
    # Compara com normalização de acentos
    for sub_rota in sub_rotas:
        if sub_rota.nome_cidade and remover_acentos(sub_rota.nome_cidade) == nome_cidade_normalizado:
            return sub_rota.sub_rota
    
    return None


def _buscar_dados_por_rede(portal):
    """
    Busca e organiza dados de pedidos/separações/NFs por CNPJ para um portal específico
    """
    dados_por_cnpj = {}
    
    # 1. Buscar CNPJs na CarteiraPrincipal (pedidos pendentes) com cod_uf='SP' e qtd_saldo > 0
    pedidos_carteira = db.session.query(
        CarteiraPrincipal.cnpj_cpf,
        CarteiraPrincipal.raz_social_red,
        CarteiraPrincipal.nome_cidade,
        CarteiraPrincipal.cod_uf,
        CarteiraPrincipal.vendedor,
        CarteiraPrincipal.equipe_vendas,
        func.count(distinct(CarteiraPrincipal.num_pedido)).label('qtd_pedidos')
    ).filter(
        and_(
            CarteiraPrincipal.cod_uf == 'SP',
            CarteiraPrincipal.ativo == True,  # Filtrar apenas pedidos ativos
            CarteiraPrincipal.qtd_saldo_produto_pedido > 0  # ✅ FILTRAR APENAS COM SALDO > 0
        )
    ).group_by(
        CarteiraPrincipal.cnpj_cpf,
        CarteiraPrincipal.raz_social_red,
        CarteiraPrincipal.nome_cidade,
        CarteiraPrincipal.cod_uf,
        CarteiraPrincipal.vendedor,
        CarteiraPrincipal.equipe_vendas
    ).all()
    
    # Filtrar por portal usando GrupoEmpresarial
    for pedido in pedidos_carteira:
        if pedido.cnpj_cpf and GrupoEmpresarial.identificar_portal(pedido.cnpj_cpf) == portal:
            cnpj_key = pedido.cnpj_cpf
            
            if cnpj_key not in dados_por_cnpj:
                # Buscar sub-rota no CadastroSubRota
                sub_rota = _buscar_sub_rota(pedido.nome_cidade, pedido.cod_uf)
                
                dados_por_cnpj[cnpj_key] = {
                    'cnpj': cnpj_key,
                    'cnpj_formatado': GrupoEmpresarial.formatar_cnpj(cnpj_key),
                    'raz_social': pedido.raz_social_red,
                    'cidade': pedido.nome_cidade,
                    'uf': pedido.cod_uf,
                    'vendedor': pedido.vendedor,
                    'equipe_vendas': pedido.equipe_vendas,
                    'sub_rota': sub_rota,
                    'pedidos': [],
                    'total_valor': Decimal('0'),
                    'total_peso': Decimal('0'),
                    'total_pallets': Decimal('0'),
                    'qtd_pedidos': 0,
                    'qtd_separacoes': 0,
                    'qtd_nf_cd': 0,
                    # Campos para cores condicionais
                    'tem_protocolo': False,
                    'agendamento_confirmado': False,
                    'tem_pendencias': False,
                    'expedicao_sugerida': '',
                    'agendamento_sugerido': '',
                    'protocolo': ''
                }
            
            # Buscar detalhes dos pedidos deste CNPJ
            _adicionar_pedidos_cnpj(dados_por_cnpj[cnpj_key], cnpj_key)
            
            # Analisar status para cores condicionais
            _analisar_status_cnpj(dados_por_cnpj[cnpj_key])
    
    # 2. Buscar CNPJs em Separacao com nf_cd=True (NFs no CD sem pedido na carteira) e cod_uf='SP'
    nfs_cd = db.session.query(
        Separacao.cnpj_cpf,
        Separacao.raz_social_red,
        Separacao.nome_cidade,
        Separacao.cod_uf,
        func.count(distinct(Separacao.numero_nf)).label('qtd_nfs')
    ).filter(
        and_(
            Separacao.sincronizado_nf == True,
            Separacao.nf_cd == True,
            Separacao.cod_uf == 'SP'
        )
    ).group_by(
        Separacao.cnpj_cpf,
        Separacao.raz_social_red,
        Separacao.nome_cidade,
        Separacao.cod_uf
    ).all()
    
    for nf in nfs_cd:
        if nf.cnpj_cpf and GrupoEmpresarial.identificar_portal(nf.cnpj_cpf) == portal:
            cnpj_key = nf.cnpj_cpf
            
            # Verificar se este CNPJ já tem pedidos na carteira COM SALDO > 0
            pedidos_na_carteira = db.session.query(
                distinct(CarteiraPrincipal.num_pedido)
            ).filter(
                and_(
                    CarteiraPrincipal.cnpj_cpf == cnpj_key,
                    CarteiraPrincipal.qtd_saldo_produto_pedido > 0  # ✅ APENAS PEDIDOS COM SALDO > 0
                )
            ).all()
            
            pedidos_na_carteira_set = {p[0] for p in pedidos_na_carteira}
            
            # Buscar NFs que não têm pedido correspondente na carteira
            nfs_sem_carteira = db.session.query(Separacao).filter(
                and_(
                    Separacao.cnpj_cpf == cnpj_key,
                    Separacao.sincronizado_nf == True,
                    Separacao.nf_cd == True,
                    ~Separacao.num_pedido.in_(pedidos_na_carteira_set) if pedidos_na_carteira_set else True
                )
            ).all()
            
            if nfs_sem_carteira:
                if cnpj_key not in dados_por_cnpj:
                    # Buscar sub-rota no CadastroSubRota
                    sub_rota = _buscar_sub_rota(nf.nome_cidade, nf.cod_uf)
                    
                    dados_por_cnpj[cnpj_key] = {
                        'cnpj': cnpj_key,
                        'cnpj_formatado': GrupoEmpresarial.formatar_cnpj(cnpj_key),
                        'raz_social': nf.raz_social_red,
                        'cidade': nf.nome_cidade,
                        'uf': nf.cod_uf,
                        'vendedor': None,
                        'equipe_vendas': None,
                        'sub_rota': sub_rota,
                        'pedidos': [],
                        'total_valor': Decimal('0'),
                        'total_peso': Decimal('0'),
                        'total_pallets': Decimal('0'),
                        'qtd_pedidos': 0,
                        'qtd_separacoes': 0,
                        'qtd_nf_cd': 0,
                        # Campos para cores condicionais
                        'tem_protocolo': False,
                        'agendamento_confirmado': False,
                        'tem_pendencias': False,
                        'expedicao_sugerida': '',
                        'agendamento_sugerido': '',
                        'protocolo': ''
                    }
                
                # Adicionar NFs sem carteira
                _adicionar_nfs_sem_carteira(dados_por_cnpj[cnpj_key], nfs_sem_carteira)
                
                # Analisar status para cores condicionais
                _analisar_status_cnpj(dados_por_cnpj[cnpj_key])
    
    # Converter para lista e ordenar por sub_rota
    # Sub-rota "D" deve ficar por último
    dados_lista = list(dados_por_cnpj.values())
    
    def ordem_subrota(item):
        """
        Função de ordenação customizada:
        - None (sem sub-rota) vai para o início (0)
        - Sub-rota "D" vai para o final (999)
        - Outras sub-rotas ordenadas alfabeticamente
        """
        sub_rota = item.get('sub_rota')
        if sub_rota is None:
            return (0, '')  # Sem sub-rota vai primeiro
        elif sub_rota.upper() == 'D':
            return (999, '')  # Sub-rota D vai por último
        else:
            return (1, sub_rota.upper())  # Outras ordenadas alfabeticamente
    
    dados_lista.sort(key=ordem_subrota)
    
    return dados_lista


def _analisar_status_cnpj(dados_cnpj):
    """
    Analisa os pedidos e separações para determinar status e cores
    Hierarquia de prioridade: Reagendar > Consolidar > Ag. Aprovação > Pronto > Pendente
    
    Status 1 - "Ag. Aprovação": protocolo em todas, agendamento futuro, não confirmado, sem saldo pendente
    Status 2 - "Pronto": protocolo em todas, agendamento futuro, confirmado, sem saldo pendente
    Status 3 - "Reagendar": agendamento passado
    Status 4 - "Consolidar": agendamento futuro + (protocolo parcial OU protocolos diferentes OU saldo parcial)
    Status 5 - "Pendente": sem separação/NF ou sem protocolo algum
    """
    # date já está importado no topo do arquivo

    hoje = date.today()
    
    # Variáveis de análise
    tem_separacao_ou_nf = False
    tem_agendamento_passado = False
    tem_agendamento_futuro = False
    todos_tem_protocolo = False  # Só True se HOUVER separações E todas tiverem protocolo
    algum_tem_protocolo = False
    protocolos_iguais = True
    algum_confirmado = False
    todos_confirmados = False  # Só True se HOUVER separações E todas estiverem confirmadas
    tem_saldo_pendente_sem_separacao = False  # Saldo que não está em Separação
    tem_saldo_pendente_parcial = False  # Saldo pendente mas não é o total do CNPJ
    primeiro_protocolo = None
    
    # Variáveis para capturar datas sugeridas
    data_expedicao_sugerida = None
    data_agendamento_sugerida = None
    
    # Contadores para validação
    total_separacoes_nfs = 0
    separacoes_com_protocolo = 0
    separacoes_confirmadas = 0
    
    # Variáveis para análise de saldo
    total_pedidos_cnpj = 0
    pedidos_com_saldo_pendente = 0
    
    # Analisar todos os pedidos
    for pedido in dados_cnpj['pedidos']:
        total_pedidos_cnpj += 1
        
        # Verificar saldo pendente do pedido
        qtd_pendente = pedido.get('qtd_pendente', 0)
        if qtd_pendente > 0:
            pedidos_com_saldo_pendente += 1
            
            # Verificar se há separações para este pedido
            pedido_tem_separacao = len(pedido.get('separacoes', [])) > 0 or len(pedido.get('nfs_cd', [])) > 0
            
            if not pedido_tem_separacao:
                # Há saldo sem nenhuma separação
                tem_saldo_pendente_sem_separacao = True
            else:
                # Há saldo mas tem algumas separações (parcial)
                tem_saldo_pendente_parcial = True
        
        # Verificar separações
        for sep in pedido.get('separacoes', []):
            tem_separacao_ou_nf = True
            total_separacoes_nfs += 1
            
            # Verificar protocolo
            if sep.get('protocolo'):
                algum_tem_protocolo = True
                separacoes_com_protocolo += 1
                if primeiro_protocolo is None:
                    primeiro_protocolo = sep.get('protocolo')
                elif primeiro_protocolo != sep.get('protocolo'):
                    protocolos_iguais = False
            
            # Verificar confirmação
            if sep.get('agendamento_confirmado'):
                algum_confirmado = True
                separacoes_confirmadas += 1
            
            # Verificar datas de agendamento
            if sep.get('agendamento'):
                data_agenda = sep.get('agendamento')
                if isinstance(data_agenda, str):
                    data_agenda = date.fromisoformat(data_agenda)
                if data_agenda:
                    if data_agenda < hoje:
                        tem_agendamento_passado = True
                    else:
                        tem_agendamento_futuro = True
                        # Capturar primeira data de agendamento futura para sugestão
                        if data_agendamento_sugerida is None:
                            data_agendamento_sugerida = data_agenda
                            # Capturar expedição se disponível
                            if sep.get('expedicao'):
                                data_exp = sep.get('expedicao')
                                if isinstance(data_exp, str):
                                    data_exp = date.fromisoformat(data_exp)
                                data_expedicao_sugerida = data_exp
        
        # Verificar NFs no CD
        for nf in pedido.get('nfs_cd', []):
            tem_separacao_ou_nf = True
            total_separacoes_nfs += 1
            
            # Verificar protocolo
            if nf.get('protocolo'):
                algum_tem_protocolo = True
                separacoes_com_protocolo += 1
                if primeiro_protocolo is None:
                    primeiro_protocolo = nf.get('protocolo')
                elif primeiro_protocolo != nf.get('protocolo'):
                    protocolos_iguais = False
            
            # Verificar confirmação
            if nf.get('agendamento_confirmado'):
                algum_confirmado = True
                separacoes_confirmadas += 1
            
            # Verificar datas de agendamento
            if nf.get('agendamento'):
                data_agenda = nf.get('agendamento')
                if isinstance(data_agenda, str):
                    data_agenda = date.fromisoformat(data_agenda)
                if data_agenda:
                    if data_agenda < hoje:
                        tem_agendamento_passado = True
                    else:
                        tem_agendamento_futuro = True
                        # Capturar primeira data de agendamento futura para sugestão
                        if data_agendamento_sugerida is None:
                            data_agendamento_sugerida = data_agenda
                            # Capturar expedição se disponível
                            if nf.get('expedicao'):
                                data_exp = nf.get('expedicao')
                                if isinstance(data_exp, str):
                                    data_exp = date.fromisoformat(data_exp)
                                data_expedicao_sugerida = data_exp
    
    # Recalcular variáveis booleanas baseado nos contadores
    if total_separacoes_nfs > 0:
        # Só pode ser "todos têm protocolo" se houver separações E todas tiverem
        todos_tem_protocolo = (separacoes_com_protocolo == total_separacoes_nfs)
        # Só pode ser "todos confirmados" se houver separações E todas estiverem confirmadas
        todos_confirmados = (separacoes_confirmadas == total_separacoes_nfs)
    else:
        # Se não há separações, não pode dizer que "todos têm" algo
        todos_tem_protocolo = False
        todos_confirmados = False
    
    # Verificar se é saldo pendente parcial (não é o total do CNPJ)
    # Se todos os pedidos têm saldo pendente, então é total, não parcial
    if pedidos_com_saldo_pendente == total_pedidos_cnpj and pedidos_com_saldo_pendente > 0:
        # Todos os pedidos têm saldo pendente - é total, não parcial
        tem_saldo_pendente_parcial = False
    
    # CORREÇÃO IMPORTANTE: Se não há agendamento passado e há separações/NFs, considerar como "potencial futuro"
    # Isso é necessário para casos onde o agendamento ainda não foi preenchido
    tem_potencial_agendamento_futuro = (not tem_agendamento_passado and tem_separacao_ou_nf)
    
    # Log para debug
    logger.debug(f"CNPJ {dados_cnpj.get('cnpj')} - Análise de status:")
    logger.debug(f"  - tem_separacao_ou_nf: {tem_separacao_ou_nf}")
    logger.debug(f"  - total_separacoes_nfs: {total_separacoes_nfs}")
    logger.debug(f"  - separacoes_com_protocolo: {separacoes_com_protocolo}")
    logger.debug(f"  - todos_tem_protocolo: {todos_tem_protocolo}")
    logger.debug(f"  - algum_tem_protocolo: {algum_tem_protocolo}")
    logger.debug(f"  - todos_confirmados: {todos_confirmados}")
    logger.debug(f"  - tem_saldo_pendente_sem_separacao: {tem_saldo_pendente_sem_separacao}")
    logger.debug(f"  - tem_saldo_pendente_parcial: {tem_saldo_pendente_parcial}")
    logger.debug(f"  - tem_agendamento_passado: {tem_agendamento_passado}")
    logger.debug(f"  - tem_agendamento_futuro: {tem_agendamento_futuro}")
    logger.debug(f"  - tem_potencial_agendamento_futuro: {tem_potencial_agendamento_futuro}")
    
    # Determinar status baseado na hierarquia
    # IMPORTANTE: A ordem de verificação IMPORTA devido à prioridade
    status = 'Pendente'
    cor_linha = ''  # sem cor especial
    icone = 'fa-hourglass-half'  # ícone padrão
    
    # 1. STATUS 3 - REAGENDAR (prioridade máxima)
    # Condição: Caso tenha algum agendamento preenchido < hoje
    if tem_agendamento_passado:
        status = 'Reagendar'
        cor_linha = 'table-danger'  # vermelho
        icone = 'fa-redo'
        logger.info(f"  => CNPJ {dados_cnpj.get('cnpj')}: Status REAGENDAR (agendamento passado)")
    
    # 2. STATUS 4 - CONSOLIDAR 
    # Condição obrigatória: As datas de agendamento que estiverem preenchidas sejam futuras (ou não haver passado)
    # Condições opcionais (qualquer uma dispara): protocolo parcial, protocolos diferentes, saldo pendente parcial
    elif tem_agendamento_futuro or tem_potencial_agendamento_futuro:
        precisa_consolidar = False
        motivo_consolidar = []
        
        # Condição opcional 1: Haja protocolo porém não em todas as Separações/NF no CD
        if algum_tem_protocolo and not todos_tem_protocolo:
            precisa_consolidar = True
            motivo_consolidar.append("protocolo parcial")
        
        # Condição opcional 2: Haja protocolo em todas as separações porém não são iguais
        if todos_tem_protocolo and not protocolos_iguais:
            precisa_consolidar = True
            motivo_consolidar.append("protocolos diferentes")
        
        # Condição opcional 3: Haja saldo pendente sem separação porém que não seja o total do CNPJ
        if tem_saldo_pendente_parcial:
            precisa_consolidar = True
            motivo_consolidar.append("saldo pendente parcial")
        
        if precisa_consolidar:
            status = 'Consolidar'
            cor_linha = 'table-warning'  # amarelo
            icone = 'fa-exclamation-triangle'
            logger.info(f"  => CNPJ {dados_cnpj.get('cnpj')}: Status CONSOLIDAR (motivos: {', '.join(motivo_consolidar)})")
        # Para Ag. Aprovação e Pronto, EXIGIR que tenha agendamento futuro preenchido
        elif tem_agendamento_futuro:
            # Tem agendamento futuro mas não precisa consolidar, vamos verificar os próximos status
            logger.debug(f"  => CNPJ {dados_cnpj.get('cnpj')}: Tem agendamento futuro, verificando Ag. Aprovação/Pronto...")
            
            # 3. STATUS 1 - AG. APROVAÇÃO
            # Condições: protocolo em todas, agendamento futuro, não confirmado, sem saldo pendente sem separação
            if (todos_tem_protocolo and not todos_confirmados and not tem_saldo_pendente_sem_separacao):
                status = 'Ag. Aprovação'
                cor_linha = 'table-info'  # azul
                icone = 'fa-clock'
                logger.info(f"  => CNPJ {dados_cnpj.get('cnpj')}: Status AG. APROVAÇÃO")
            
            # 4. STATUS 2 - PRONTO
            # Condições: protocolo em todas, agendamento futuro, confirmado, sem saldo pendente sem separação
            elif (todos_tem_protocolo and todos_confirmados and not tem_saldo_pendente_sem_separacao):
                status = 'Pronto'
                cor_linha = 'table-success'  # azul (mantendo success para verde/azul)
                icone = 'fa-check-circle'
                logger.info(f"  => CNPJ {dados_cnpj.get('cnpj')}: Status PRONTO")
            else:
                logger.debug(f"  => CNPJ {dados_cnpj.get('cnpj')}: Não atende Ag. Aprovação/Pronto. todos_tem_protocolo={todos_tem_protocolo}, todos_confirmados={todos_confirmados}, tem_saldo_pendente_sem_separacao={tem_saldo_pendente_sem_separacao}")
        else:
            # Tem potencial futuro mas sem agendamento preenchido, fica como pendente
            logger.debug(f"  => CNPJ {dados_cnpj.get('cnpj')}: Sem agendamento preenchido, mantendo como Pendente")
    
    # 5. STATUS 5 - PENDENTE (default)
    # Condições: Não haja Separação e nem NF no CD OU Não haja protocolo em nenhuma Separação ou NF no CD
    else:
        status = 'Pendente'
        cor_linha = ''  # sem cor (linha na cor original)
        icone = 'fa-hourglass-half'
        logger.info(f"  => CNPJ {dados_cnpj.get('cnpj')}: Status PENDENTE (não tem agendamento ou não tem separação/protocolo)")
    
    # Log do status final determinado
    logger.debug(f"  => Status final: {status} (cor: {cor_linha})")
    
    # Atualizar dados do CNPJ com status e indicadores visuais
    dados_cnpj['status'] = status
    dados_cnpj['cor_linha'] = cor_linha
    dados_cnpj['icone_status'] = icone
    dados_cnpj['tem_protocolo'] = algum_tem_protocolo
    dados_cnpj['agendamento_confirmado'] = algum_confirmado
    
    # Preencher datas sugeridas quando status for "Ag. Aprovação" ou "Pronto"
    if status in ['Ag. Aprovação', 'Pronto'] and data_agendamento_sugerida:
        # Formatar as datas para input date HTML (YYYY-MM-DD)
        dados_cnpj['agendamento_sugerido'] = data_agendamento_sugerida.strftime('%Y-%m-%d') if data_agendamento_sugerida else ''
        dados_cnpj['expedicao_sugerida'] = data_expedicao_sugerida.strftime('%Y-%m-%d') if data_expedicao_sugerida else ''
        logger.info(f"  => CNPJ {dados_cnpj.get('cnpj')}: Datas preenchidas - Expedição: {dados_cnpj['expedicao_sugerida']}, Agendamento: {dados_cnpj['agendamento_sugerido']}")
    else:
        dados_cnpj['agendamento_sugerido'] = ''
        dados_cnpj['expedicao_sugerida'] = ''
    
    # Indicador de pendências: reagendamento necessário ou consolidação necessária
    dados_cnpj['tem_pendencias'] = status in ['Reagendar', 'Consolidar']


def _adicionar_pedidos_cnpj(dados_cnpj, cnpj):
    """
    Adiciona informações detalhadas dos pedidos de um CNPJ
    """
    # Buscar pedidos na CarteiraPrincipal - APENAS COM SALDO > 0
    pedidos = db.session.query(
        CarteiraPrincipal.num_pedido,
        CarteiraPrincipal.data_pedido,
        CarteiraPrincipal.pedido_cliente,
        CarteiraPrincipal.observ_ped_1,
        func.sum(CarteiraPrincipal.qtd_saldo_produto_pedido).label('qtd_total'),
        func.sum(CarteiraPrincipal.qtd_saldo_produto_pedido * CarteiraPrincipal.preco_produto_pedido).label('valor_total')
    ).filter(
        and_(
            CarteiraPrincipal.cnpj_cpf == cnpj,
            CarteiraPrincipal.ativo == True,  # Filtrar apenas pedidos ativos
            CarteiraPrincipal.qtd_saldo_produto_pedido > 0  # ✅ FILTRAR APENAS COM SALDO > 0
        )
    ).group_by(
        CarteiraPrincipal.num_pedido,
        CarteiraPrincipal.data_pedido,
        CarteiraPrincipal.pedido_cliente,
        CarteiraPrincipal.observ_ped_1
    ).having(
        func.sum(CarteiraPrincipal.qtd_saldo_produto_pedido) > 0  # ✅ GARANTIR QUE A SOMA DO GRUPO TAMBÉM É > 0
    ).all()
    
    for pedido in pedidos:
        pedido_info = {
            'num_pedido': pedido.num_pedido,
            'data_pedido': pedido.data_pedido,
            'pedido_cliente': pedido.pedido_cliente,
            'observacoes': pedido.observ_ped_1,
            'status': 'PENDENTE',
            'separacoes': [],
            'nfs_cd': [],
            'qtd_pendente': Decimal('0'),
            'valor_pendente': Decimal('0'),
            'peso_pendente': Decimal('0'),
            'pallets_pendente': Decimal('0'),
            'valor_original': Decimal(str(pedido.valor_total)) if pedido.valor_total else Decimal('0')
        }
        
        # Calcular quantidades pendentes (CarteiraPrincipal - Separacao)
        _calcular_pendencias_pedido(pedido_info, pedido.num_pedido)
        
        # Buscar separações do pedido
        _adicionar_separacoes_pedido(pedido_info, pedido.num_pedido)
        
        # Buscar NFs no CD do pedido
        _adicionar_nfs_cd_pedido(pedido_info, pedido.num_pedido)
        
        dados_cnpj['pedidos'].append(pedido_info)
        dados_cnpj['qtd_pedidos'] += 1
        
        # Atualizar totais (agora usando valores originais, sem abater)
        dados_cnpj['total_valor'] += pedido_info.get('valor_original', Decimal('0'))
        dados_cnpj['total_peso'] += pedido_info.get('peso_original', Decimal('0'))
        dados_cnpj['total_pallets'] += pedido_info.get('pallets_original', Decimal('0'))


def _calcular_pendencias_pedido(pedido_info, num_pedido):
    """
    Calcula valores pendentes de um pedido (CarteiraPrincipal - Separacao não sincronizada)
    E também calcula os valores totais originais
    """
    # Buscar itens da carteira - APENAS COM SALDO > 0
    itens_carteira = db.session.query(
        CarteiraPrincipal.cod_produto,
        CarteiraPrincipal.qtd_saldo_produto_pedido,
        CarteiraPrincipal.preco_produto_pedido
    ).filter(
        and_(
            CarteiraPrincipal.num_pedido == num_pedido,
            CarteiraPrincipal.ativo == True,  # Filtrar apenas itens ativos
            CarteiraPrincipal.qtd_saldo_produto_pedido > 0  # ✅ APENAS ITENS COM SALDO > 0
        )
    ).all()
    
    # Inicializar totais originais
    peso_total_original = Decimal('0')
    pallets_total_original = Decimal('0')
    
    for item in itens_carteira:
        # Buscar informações de palletização
        pallet_info = db.session.query(
            CadastroPalletizacao.peso_bruto,
            CadastroPalletizacao.palletizacao
        ).filter(
            CadastroPalletizacao.cod_produto == item.cod_produto
        ).first()
        
        if pallet_info:
            # Calcular totais originais (sem abater separações)
            peso_total_original += Decimal(str(item.qtd_saldo_produto_pedido)) * Decimal(str(pallet_info.peso_bruto or 0))
            if pallet_info.palletizacao and pallet_info.palletizacao > 0:
                pallets_total_original += Decimal(str(item.qtd_saldo_produto_pedido)) / Decimal(str(pallet_info.palletizacao))
        
        # Buscar quantidade já separada (não sincronizada)
        qtd_separada = db.session.query(
            func.sum(Separacao.qtd_saldo)
        ).filter(
            and_(
                Separacao.num_pedido == num_pedido,
                Separacao.cod_produto == item.cod_produto,
                Separacao.sincronizado_nf == False
            )
        ).scalar() or Decimal('0')
        
        qtd_pendente = Decimal(str(item.qtd_saldo_produto_pedido)) - Decimal(str(qtd_separada))
        
        if qtd_pendente > 0:
            # Buscar dados de palletização
            palletizacao = db.session.query(CadastroPalletizacao).filter_by(
                cod_produto=item.cod_produto
            ).first()
            
            valor_pendente = qtd_pendente * Decimal(str(item.preco_produto_pedido or 0))
            peso_pendente = Decimal('0')
            pallets_pendente = Decimal('0')
            
            if palletizacao:
                peso_pendente = qtd_pendente * Decimal(str(palletizacao.peso_bruto))
                if palletizacao.palletizacao > 0:
                    pallets_pendente = qtd_pendente / Decimal(str(palletizacao.palletizacao))
            
            pedido_info['qtd_pendente'] += qtd_pendente
            pedido_info['valor_pendente'] += valor_pendente
            pedido_info['peso_pendente'] += peso_pendente
            pedido_info['pallets_pendente'] += pallets_pendente
    
    # Adicionar totais originais ao pedido_info
    pedido_info['peso_original'] = peso_total_original
    pedido_info['pallets_original'] = pallets_total_original


def _adicionar_separacoes_pedido(pedido_info, num_pedido):
    """
    Adiciona informações das separações de um pedido
    """
    separacoes = db.session.query(
        Separacao.separacao_lote_id,
        Separacao.status,
        Separacao.expedicao,
        Separacao.agendamento,
        Separacao.agendamento_confirmado,
        Separacao.protocolo,
        func.sum(Separacao.valor_saldo).label('valor_total'),
        func.sum(Separacao.peso).label('peso_total'),
        func.sum(Separacao.pallet).label('pallet_total')
    ).filter(
        and_(
            Separacao.num_pedido == num_pedido,
            Separacao.sincronizado_nf == False,
            Separacao.qtd_saldo > 0
        )
    ).group_by(
        Separacao.separacao_lote_id,
        Separacao.status,
        Separacao.expedicao,
        Separacao.agendamento,
        Separacao.agendamento_confirmado,
        Separacao.protocolo
    ).all()
    
    for sep in separacoes:
        pedido_info['separacoes'].append({
            'separacao_lote_id': sep.separacao_lote_id,
            'status': sep.status,
            'expedicao': sep.expedicao,
            'agendamento': sep.agendamento,
            'agendamento_confirmado': sep.agendamento_confirmado,
            'protocolo': sep.protocolo,
            'valor_total': sep.valor_total or Decimal('0'),
            'peso_total': sep.peso_total or Decimal('0'),
            'pallet_total': sep.pallet_total or Decimal('0')
        })


def _adicionar_nfs_cd_pedido(pedido_info, num_pedido):
    """
    Adiciona informações das NFs no CD de um pedido
    """
    nfs = db.session.query(
        Separacao.numero_nf,
        Separacao.status,
        Separacao.expedicao,
        Separacao.agendamento,
        Separacao.agendamento_confirmado,
        Separacao.protocolo,
        func.sum(Separacao.valor_saldo).label('valor_total'),
        func.sum(Separacao.peso).label('peso_total'),
        func.sum(Separacao.pallet).label('pallet_total')
    ).filter(
        and_(
            Separacao.num_pedido == num_pedido,
            Separacao.sincronizado_nf == True,
            Separacao.nf_cd == True,
            Separacao.qtd_saldo > 0
        )
    ).group_by(
        Separacao.numero_nf,
        Separacao.status,
        Separacao.expedicao,
        Separacao.agendamento,
        Separacao.agendamento_confirmado,
        Separacao.protocolo
    ).all()
    
    for nf in nfs:
        pedido_info['nfs_cd'].append({
            'numero_nf': nf.numero_nf,
            'status': nf.status,
            'expedicao': nf.expedicao,
            'agendamento': nf.agendamento,
            'agendamento_confirmado': nf.agendamento_confirmado,
            'protocolo': nf.protocolo,
            'valor': nf.valor_total or Decimal('0'),
            'peso': nf.peso_total or Decimal('0'),
            'pallet': nf.pallet_total or Decimal('0')
        })


def _adicionar_nfs_sem_carteira(dados_cnpj, nfs_sem_carteira):
    """
    Adiciona NFs que estão no CD mas não têm pedido na carteira
    """
    # Agrupar por número de NF
    nfs_agrupadas = {}
    
    for item in nfs_sem_carteira:
        if item.numero_nf not in nfs_agrupadas:
            nfs_agrupadas[item.numero_nf] = {
                'numero_nf': item.numero_nf,
                'num_pedido': item.num_pedido,
                'status': item.status,
                'expedicao': item.expedicao,
                'agendamento': item.agendamento,
                'agendamento_confirmado': item.agendamento_confirmado,
                'protocolo': item.protocolo,
                'valor': Decimal('0'),
                'peso': Decimal('0'),
                'pallets': Decimal('0')
            }
    
    # Para cada NF agrupada, buscar TODOS os produtos do faturamento
    for nf_num in nfs_agrupadas.keys():
        # Buscar todos os produtos faturados desta NF
        produtos_faturados = db.session.query(
            FaturamentoProduto.cod_produto,
            FaturamentoProduto.valor_produto_faturado,
            FaturamentoProduto.qtd_produto_faturado,
            FaturamentoProduto.peso_total
        ).filter(
            FaturamentoProduto.numero_nf == nf_num
        ).all()
        
        valor_total_nf = Decimal('0')
        peso_total_nf = Decimal('0')
        pallets_total_nf = Decimal('0')
        
        for prod_fat in produtos_faturados:
            # Somar valor
            valor_total_nf += Decimal(str(prod_fat.valor_produto_faturado or 0))
            
            # Usar peso_total se disponível, senão calcular
            if prod_fat.peso_total:
                peso_total_nf += Decimal(str(prod_fat.peso_total))
            else:
                # Buscar dados de palletização para calcular peso
                palletizacao = db.session.query(CadastroPalletizacao).filter_by(
                    cod_produto=prod_fat.cod_produto
                ).first()
                
                if palletizacao and prod_fat.qtd_produto_faturado:
                    peso_total_nf += Decimal(str(prod_fat.qtd_produto_faturado)) * Decimal(str(palletizacao.peso_bruto))
            
            # Calcular pallets
            palletizacao = db.session.query(CadastroPalletizacao).filter_by(
                cod_produto=prod_fat.cod_produto
            ).first()
            
            if palletizacao and palletizacao.palletizacao > 0 and prod_fat.qtd_produto_faturado:
                pallets_total_nf += Decimal(str(prod_fat.qtd_produto_faturado)) / Decimal(str(palletizacao.palletizacao))
        
        # Atualizar valores da NF
        nfs_agrupadas[nf_num]['valor'] = valor_total_nf
        nfs_agrupadas[nf_num]['peso'] = peso_total_nf
        nfs_agrupadas[nf_num]['pallets'] = pallets_total_nf
    
    # Adicionar como pedido especial "NF no CD s/ Cart."
    for nf_data in nfs_agrupadas.values():
        pedido_info = {
            'num_pedido': nf_data['num_pedido'],
            'data_pedido': None,
            'pedido_cliente': None,
            'observacoes': 'NF no CD sem pedido na carteira',
            'status': 'NF_CD_SEM_CARTEIRA',
            'separacoes': [],
            'nfs_cd': [nf_data],
            'qtd_pendente': Decimal('0'),
            'valor_pendente': Decimal('0'),
            'peso_pendente': Decimal('0'),
            'pallets_pendente': Decimal('0')
        }
        
        dados_cnpj['pedidos'].append(pedido_info)
        dados_cnpj['qtd_nf_cd'] += 1
        
        # Atualizar totais
        dados_cnpj['total_valor'] += nf_data['valor']
        dados_cnpj['total_peso'] += nf_data['peso']
        dados_cnpj['total_pallets'] += nf_data['pallets']


@programacao_em_lote_bp.route('/api/analisar-estoques/<rede>', methods=['GET'])
@login_required
def analisar_estoques(rede):
    """
    API para análise de estoques dos itens da rede
    Retorna somatória de quantidades, valores e projeção de estoque
    """
    try:
        
        # Mapear rede para portal
        portal_map = {'atacadao': 'atacadao', 'sendas': 'sendas'}
        portal = portal_map.get(rede.lower())
        
        if not portal:
            return jsonify({'success': False, 'error': 'Rede inválida'}), 400
        
        # Buscar CNPJs da rede
        dados_rede = _buscar_dados_por_rede(portal)
        cnpjs_rede = [d['cnpj'] for d in dados_rede]
        
        # Buscar todos os produtos dos pedidos dessa rede
        produtos_rede = db.session.query(
            CarteiraPrincipal.cod_produto,
            CarteiraPrincipal.nome_produto,
            func.sum(CarteiraPrincipal.qtd_saldo_produto_pedido).label('qtd_total'),
            func.sum(CarteiraPrincipal.qtd_saldo_produto_pedido * CarteiraPrincipal.preco_produto_pedido).label('valor_total')
        ).filter(
            CarteiraPrincipal.cnpj_cpf.in_(cnpjs_rede)
        ).group_by(
            CarteiraPrincipal.cod_produto,
            CarteiraPrincipal.nome_produto
        ).all()
        
        resultado = []
        data_hoje = date.today()
        
        for produto in produtos_rede:
            # Buscar estoque atual
            estoque_atual = db.session.query(
                func.sum(MovimentacaoEstoque.qtd_movimentacao)
            ).filter(
                MovimentacaoEstoque.cod_produto == produto.cod_produto,
                MovimentacaoEstoque.ativo == True
            ).scalar() or 0
            
            # Calcular data disponível (simplificado)
            data_disponivel = data_hoje
            saldo_projetado = float(estoque_atual)
            
            # Buscar saídas futuras (excluindo pedidos dessa rede)
            for i in range(15):
                data_projecao = data_hoje + timedelta(days=i)
                
                # Saídas do dia (excluindo CNPJs da rede)
                saidas_dia = db.session.query(
                    func.sum(Separacao.qtd_saldo)
                ).filter(
                    Separacao.cod_produto == produto.cod_produto,
                    Separacao.expedicao == data_projecao,
                    Separacao.sincronizado_nf == False,
                    ~Separacao.cnpj_cpf.in_(cnpjs_rede)
                ).scalar() or 0
                
                # Produções do dia
                producoes_dia = db.session.query(
                    func.sum(ProgramacaoProducao.qtd_programada)
                ).filter(
                    ProgramacaoProducao.cod_produto == produto.cod_produto,
                    ProgramacaoProducao.data_programacao == data_projecao
                ).scalar() or 0
                
                saldo_projetado = saldo_projetado - float(saidas_dia) + float(producoes_dia)
                
                if saldo_projetado >= float(produto.qtd_total) and data_disponivel == data_hoje:
                    data_disponivel = data_projecao
            
            resultado.append({
                'cod_produto': produto.cod_produto,
                'nome_produto': produto.nome_produto,
                'qtd_total': float(produto.qtd_total),
                'valor_total': float(produto.valor_total or 0),
                'estoque_atual': float(estoque_atual),
                'data_disponivel': data_disponivel.strftime('%d/%m/%Y'),
                'projecao_15_dias': saldo_projetado
            })
        
        return jsonify({
            'success': True,
            'data': resultado
        })
        
    except Exception as e:
        logger.error(f"Erro ao analisar estoques: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@programacao_em_lote_bp.route('/api/sugerir-datas/<rede>', methods=['POST'])
@login_required
def sugerir_datas(rede):
    """
    API para sugerir datas de expedição e agendamento com análise de ruptura
    Regras:
    1. Expedição inicia em D+2 úteis
    2. Expedição apenas 2ª a 5ª feira
    3. Agendamento D+1 da expedição
    4. Máximo 30 CNPJs por dia
    5. Considera disponibilidade de estoque para cada CNPJ
    """
    try:
        # timedelta já está importado no topo do arquivo

        dados = request.get_json()
        cnpjs_selecionados = dados.get('cnpjs', [])
        ordem = dados.get('ordem', {})  # Ordem de prioridade
        
        if not cnpjs_selecionados:
            return jsonify({'success': False, 'error': 'Nenhum CNPJ selecionado'}), 400
        
        # Configurações
        MAX_POR_DIA = 30
        DIAS_UTEIS = [0, 1, 2, 3]  # Segunda a Quinta (expedição)
        
        # Primeiro, fazer análise de ruptura para obter datas de disponibilidade
        logger.info(f"Analisando ruptura para {len(cnpjs_selecionados)} CNPJs")
        
        # Análise de ruptura considerando ordem
        resultado_ruptura = {}
        saidas_acumuladas = {}
        
        # Ordenar CNPJs conforme prioridade
        cnpjs_ordenados = sorted(cnpjs_selecionados, key=lambda x: ordem.get(x, 999))
        
        for idx, cnpj in enumerate(cnpjs_ordenados):
            # Buscar pedidos do CNPJ
            pedidos = db.session.query(CarteiraPrincipal).filter_by(
                cnpj_cpf=cnpj
            ).all()
            
            data_completa = date.today()
            tem_ruptura = False
            
            for pedido in pedidos:
                cod_produto = pedido.cod_produto
                qtd_necessaria = float(pedido.qtd_saldo_produto_pedido)
                
                # Incluir saídas acumuladas dos pedidos anteriores
                saida_acumulada = saidas_acumuladas.get(cod_produto, 0)
                qtd_necessaria_total = qtd_necessaria + saida_acumulada
                
                # Buscar estoque atual
                estoque_atual = db.session.query(
                    func.sum(MovimentacaoEstoque.qtd_movimentacao)
                ).filter(
                    MovimentacaoEstoque.cod_produto == cod_produto,
                    MovimentacaoEstoque.ativo == True
                ).scalar() or 0
                
                # Se não tem estoque suficiente, calcular quando terá
                if float(estoque_atual) < qtd_necessaria_total:
                    tem_ruptura = True
                    
                    # Buscar data quando estará disponível
                    for dias in range(1, 60):  # Buscar até 60 dias
                        data_futura = date.today() + timedelta(days=dias)
                        
                        # Projetar estoque com produções até D-1 (não considera produção do dia da expedição)
                        # Exemplo: se expedição é dia 11, considera produções até dia 10
                        # INCLUI produção de hoje se houver
                        data_limite_producao = data_futura - timedelta(days=1)
                        producoes = db.session.query(
                            func.sum(ProgramacaoProducao.qtd_programada)
                        ).filter(
                            ProgramacaoProducao.cod_produto == cod_produto,
                            ProgramacaoProducao.data_programacao >= date.today(),  # A partir de hoje (INCLUI hoje)
                            ProgramacaoProducao.data_programacao <= data_limite_producao  # Até D-1 da expedição
                        ).scalar() or 0
                        
                        # Considerar saídas já programadas até a data futura
                        saidas_programadas = db.session.query(
                            func.sum(Separacao.qtd_saldo)
                        ).filter(
                            Separacao.cod_produto == cod_produto,
                            Separacao.expedicao <= data_futura,
                            Separacao.sincronizado_nf == False,
                            ~Separacao.cnpj_cpf.in_(cnpjs_ordenados)  # Excluir CNPJs da rede
                        ).scalar() or 0
                        
                        # Estoque projetado = Estoque atual + Produções até D-1 - Saídas programadas
                        estoque_projetado = float(estoque_atual) + float(producoes) - float(saidas_programadas)
                        
                        if estoque_projetado >= qtd_necessaria_total:
                            if data_futura > data_completa:
                                data_completa = data_futura
                            break
                
                # Acumular saída para próximos pedidos
                saidas_acumuladas[cod_produto] = saidas_acumuladas.get(cod_produto, 0) + qtd_necessaria
            
            resultado_ruptura[cnpj] = {
                'data_disponivel': data_completa,
                'tem_ruptura': tem_ruptura
            }
        
        # Calcular D+2 úteis a partir de hoje
        data_atual = date.today()
        data_minima_expedicao = data_atual
        dias_uteis_adicionados = 0
        
        # Adicionar 2 dias úteis
        while dias_uteis_adicionados < 2:
            data_minima_expedicao += timedelta(days=1)
            # Considera útil se não for sábado (5) ou domingo (6)
            if data_minima_expedicao.weekday() < 5:
                dias_uteis_adicionados += 1
        
        # Se D+2 úteis não cair em dia permitido (2ª-5ª), ajustar
        while data_minima_expedicao.weekday() not in DIAS_UTEIS:
            data_minima_expedicao += timedelta(days=1)
        
        # Agora sugerir datas baseadas na disponibilidade
        sugestoes = {}
        cnpjs_por_dia = {}
        
        for cnpj in cnpjs_ordenados:
            ruptura_info = resultado_ruptura.get(cnpj, {})
            data_disponivel = ruptura_info.get('data_disponivel', date.today())
            
            # Data de expedição é o maior entre: D+2 úteis ou data disponível
            if data_disponivel > data_minima_expedicao:
                data_expedicao = data_disponivel
            else:
                data_expedicao = data_minima_expedicao
            
            # Ajustar para dia permitido se necessário
            while data_expedicao.weekday() not in DIAS_UTEIS:
                data_expedicao += timedelta(days=1)
            
            # Verificar limite diário (30 CNPJs por dia)
            data_str = data_expedicao.strftime('%Y-%m-%d')
            if data_str not in cnpjs_por_dia:
                cnpjs_por_dia[data_str] = 0
            
            # Se excedeu limite do dia, buscar próximo dia útil disponível
            while cnpjs_por_dia.get(data_expedicao.strftime('%Y-%m-%d'), 0) >= MAX_POR_DIA:
                data_expedicao += timedelta(days=1)
                while data_expedicao.weekday() not in DIAS_UTEIS:
                    data_expedicao += timedelta(days=1)
                data_str = data_expedicao.strftime('%Y-%m-%d')
                if data_str not in cnpjs_por_dia:
                    cnpjs_por_dia[data_str] = 0
            
            # Incrementar contador do dia
            cnpjs_por_dia[data_expedicao.strftime('%Y-%m-%d')] += 1
            
            # Data de agendamento é D+1 da expedição
            data_agendamento = data_expedicao + timedelta(days=1)
            
            sugestoes[cnpj] = {
                'expedicao': data_expedicao.strftime('%Y-%m-%d'),
                'agendamento': data_agendamento.strftime('%Y-%m-%d'),
                'disponibilidade_estoque': data_disponivel.strftime('%Y-%m-%d'),
                'tem_ruptura': ruptura_info.get('tem_ruptura', False)
            }
        
        logger.info(f"Sugestões geradas para {len(sugestoes)} CNPJs")
        
        return jsonify({
            'success': True,
            'sugestoes': sugestoes,
            'data_minima': data_minima_expedicao.strftime('%Y-%m-%d'),
            'distribuicao_dias': cnpjs_por_dia
        })
        
    except Exception as e:
        logger.error(f"Erro ao sugerir datas: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@programacao_em_lote_bp.route('/api/analisar-ruptura-cnpj/<path:cnpj>', methods=['GET'])
@login_required
def analisar_ruptura_cnpj(cnpj):
    """
    API para análise de ruptura de UM CNPJ considerando TODOS os seus pedidos
    Replica a lógica de ruptura_sem_cache mas busca por CNPJ ao invés de pedido
    Retorna formato compatível com o modal de ruptura existente
    """
    try:
        import time
        from sqlalchemy import func, text
        from sqlalchemy.orm import load_only
        from app.estoque.models import UnificacaoCodigos

        inicio_total = time.time()
        logger.info(f"Analisando ruptura para CNPJ {cnpj} - TODOS os pedidos")

        # ===== BUSCAR ITENS DO CNPJ - OPÇÃO 2 =====
        # 1. CarteiraPrincipal (qtd_saldo > 0) - representa tudo não faturado
        # 2. Separacao (sincronizado_nf=True AND nf_cd=True) - NFs voltaram para CD

        produtos_agrupados = {}

        # 1. Buscar de CarteiraPrincipal
        logger.info("  📋 Buscando de CarteiraPrincipal...")
        itens_carteira = db.session.query(CarteiraPrincipal).options(
            load_only(
                CarteiraPrincipal.cod_produto,
                CarteiraPrincipal.nome_produto,
                CarteiraPrincipal.qtd_saldo_produto_pedido,
                CarteiraPrincipal.preco_produto_pedido
            )
        ).filter(
            CarteiraPrincipal.cnpj_cpf == cnpj,
            CarteiraPrincipal.ativo == True,
            CarteiraPrincipal.qtd_saldo_produto_pedido >= 0.001
        ).all()

        for item in itens_carteira:
            cod = item.cod_produto
            if cod not in produtos_agrupados:
                produtos_agrupados[cod] = {
                    'cod_produto': cod,
                    'nome_produto': item.nome_produto,
                    'qtd_saldo': 0,
                    'preco': float(item.preco_produto_pedido or 0)
                }
            produtos_agrupados[cod]['qtd_saldo'] += float(item.qtd_saldo_produto_pedido)

        logger.info(f"  ✅ CarteiraPrincipal: {len(itens_carteira)} itens, {len(produtos_agrupados)} produtos únicos")

        # 2. Buscar NFs no CD (sincronizado_nf=True AND nf_cd=True)
        logger.info("  📄 Buscando NFs no CD...")
        itens_nf_cd = db.session.query(Separacao).options(
            load_only(
                Separacao.cod_produto,
                Separacao.nome_produto,
                Separacao.qtd_saldo,
                Separacao.valor_saldo
            )
        ).filter(
            and_(
                Separacao.cnpj_cpf == cnpj,
                Separacao.sincronizado_nf == True,
                Separacao.nf_cd == True,
                Separacao.qtd_saldo > 0
            )
        ).all()

        for item in itens_nf_cd:
            cod = item.cod_produto
            # Calcular preço médio: valor_saldo / qtd_saldo
            preco_unitario = (float(item.valor_saldo) / float(item.qtd_saldo)) if item.qtd_saldo > 0 else 0

            if cod not in produtos_agrupados:
                produtos_agrupados[cod] = {
                    'cod_produto': cod,
                    'nome_produto': item.nome_produto or f"Produto {cod}",
                    'qtd_saldo': 0,
                    'preco': preco_unitario
                }
            produtos_agrupados[cod]['qtd_saldo'] += float(item.qtd_saldo)

        logger.info(f"  ✅ NFs no CD: {len(itens_nf_cd)} itens adicionados")

        if not produtos_agrupados:
            return jsonify({
                'success': False,
                'message': 'CNPJ não encontrado ou todos os itens já foram faturados'
            }), 404

        logger.info(f"  ✅ TOTAL: {len(produtos_agrupados)} produtos únicos para análise")

        produtos_unicos = list(produtos_agrupados.keys())

        # ===== EXPANDIR CÓDIGOS COM UNIFICAÇÃO =====
        produtos_expandidos = {}
        for produto in produtos_unicos:
            codigos_relacionados = UnificacaoCodigos.get_todos_codigos_relacionados(produto)
            produtos_expandidos[produto] = list(codigos_relacionados)

        # Coletar todos os códigos únicos
        todos_codigos = set()
        for codigos in produtos_expandidos.values():
            todos_codigos.update(codigos)

        # ===== QUERY OTIMIZADA COM CTE (IGUAL ruptura_sem_cache) =====
        inicio_query = time.time()

        query_sql = """
        WITH estoque_atual AS (
            SELECT
                cod_produto,
                COALESCE(SUM(qtd_movimentacao), 0) as estoque
            FROM movimentacao_estoque
            WHERE cod_produto = ANY(:codigos_array)
              AND ativo = true
            GROUP BY cod_produto
        ),
        saidas_previstas AS (
            SELECT
                cod_produto,
                expedicao as data,
                SUM(qtd_saldo) as quantidade
            FROM separacao
            WHERE cod_produto = ANY(:codigos_array)
              AND sincronizado_nf = false
              AND expedicao BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '7 days'
            GROUP BY cod_produto, expedicao
        ),
        producoes_previstas AS (
            SELECT
                cod_produto,
                data_programacao as data,
                SUM(qtd_programada) as quantidade
            FROM programacao_producao
            WHERE cod_produto = ANY(:codigos_array)
              AND data_programacao BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '7 days'
            GROUP BY cod_produto, data_programacao
        ),
        todos_codigos AS (
            SELECT DISTINCT cod_produto FROM (
                SELECT cod_produto FROM estoque_atual
                UNION ALL
                SELECT cod_produto FROM saidas_previstas
                UNION ALL
                SELECT cod_produto FROM producoes_previstas
            ) sub
            WHERE cod_produto IS NOT NULL
        )
        SELECT
            c.cod_produto,
            COALESCE(e.estoque, 0) as estoque_atual,
            COALESCE(json_agg(
                jsonb_build_object(
                    'data', s.data,
                    'tipo', 'saida',
                    'qtd', s.quantidade
                ) ORDER BY s.data
            ) FILTER (WHERE s.data IS NOT NULL), '[]'::json) as saidas,
            COALESCE(json_agg(
                jsonb_build_object(
                    'data', p.data,
                    'tipo', 'producao',
                    'qtd', p.quantidade
                ) ORDER BY p.data
            ) FILTER (WHERE p.data IS NOT NULL), '[]'::json) as producoes
        FROM todos_codigos c
        LEFT JOIN estoque_atual e ON e.cod_produto = c.cod_produto
        LEFT JOIN saidas_previstas s ON s.cod_produto = c.cod_produto
        LEFT JOIN producoes_previstas p ON p.cod_produto = c.cod_produto
        GROUP BY c.cod_produto, e.estoque
        """

        resultado_raw = db.session.execute(text(query_sql), {'codigos_array': list(todos_codigos)}).fetchall()

        # Converter resultado e agregar por produto principal
        dados_por_codigo = {}
        for row in resultado_raw:
            cod_produto = row[0]
            estoque_atual = float(row[1] or 0)
            saidas = row[2] if row[2] else []
            producoes = row[3] if row[3] else []

            dados_por_codigo[cod_produto] = {
                'estoque': estoque_atual,
                'saidas': saidas,
                'producoes': producoes
            }

        # Agregar por produto principal (unificação)
        dados_produtos = {}
        for produto_principal, codigos_relacionados in produtos_expandidos.items():
            estoque_total = 0
            todas_saidas = []
            todas_producoes = []

            for codigo in codigos_relacionados:
                if codigo in dados_por_codigo:
                    estoque_total += dados_por_codigo[codigo]['estoque']
                    todas_saidas.extend(dados_por_codigo[codigo]['saidas'])
                    todas_producoes.extend(dados_por_codigo[codigo]['producoes'])

            # Calcular projeção D+7
            def calcular_projecao(estoque_atual, saidas, producoes):
                data_inicio = date.today()
                estoque_dia = float(estoque_atual)
                menor_estoque = estoque_dia

                saidas_por_data = {s['data']: float(s['qtd']) for s in saidas if s}
                producoes_por_data = {p['data']: float(p['qtd']) for p in producoes if p}

                for dias in range(8):
                    data = data_inicio + timedelta(days=dias)
                    data_str = data.isoformat()

                    saida_dia = saidas_por_data.get(data_str, 0)
                    entrada_dia = producoes_por_data.get(data_str, 0)

                    estoque_dia = estoque_dia - saida_dia + entrada_dia
                    menor_estoque = min(menor_estoque, estoque_dia)

                return {'estoque_atual': estoque_atual, 'menor_estoque_d7': menor_estoque}

            dados_produtos[produto_principal] = calcular_projecao(estoque_total, todas_saidas, todas_producoes)

        tempo_query = (time.time() - inicio_query) * 1000

        # ===== BUSCAR PRODUÇÕES FUTURAS (até D+28 para calcular data disponibilidade) =====
        producoes_futuras = db.session.query(
            ProgramacaoProducao.cod_produto,
            ProgramacaoProducao.data_programacao,
            func.sum(ProgramacaoProducao.qtd_programada).label('qtd_producao')
        ).filter(
            ProgramacaoProducao.cod_produto.in_(list(todos_codigos)),
            ProgramacaoProducao.data_programacao >= datetime.now().date()
        ).group_by(
            ProgramacaoProducao.cod_produto,
            ProgramacaoProducao.data_programacao
        ).order_by(
            ProgramacaoProducao.data_programacao
        ).all()

        # Organizar produções por produto principal
        producoes_por_produto = {}
        producoes_por_codigo = {}

        for prod in producoes_futuras:
            if prod.cod_produto not in producoes_por_codigo:
                producoes_por_codigo[prod.cod_produto] = []
            producoes_por_codigo[prod.cod_produto].append({
                'data': prod.data_programacao,
                'qtd': float(prod.qtd_producao)
            })

        # Agregar por produto principal
        for produto_principal, codigos_relacionados in produtos_expandidos.items():
            todas_producoes = []
            for codigo in codigos_relacionados:
                if codigo in producoes_por_codigo:
                    todas_producoes.extend(producoes_por_codigo[codigo])

            # Agrupar por data e somar
            producoes_agrupadas = {}
            for prod in todas_producoes:
                data_str = prod['data'].isoformat() if hasattr(prod['data'], 'isoformat') else str(prod['data'])
                if data_str not in producoes_agrupadas:
                    producoes_agrupadas[data_str] = {'data': prod['data'], 'qtd': 0}
                producoes_agrupadas[data_str]['qtd'] += prod['qtd']

            producoes_por_produto[produto_principal] = sorted(
                producoes_agrupadas.values(),
                key=lambda x: x['data']
            )

        # ===== ANÁLISE DOS ITENS =====
        itens_com_ruptura = []
        itens_disponiveis_lista = []
        valor_total_pedido = 0
        valor_com_ruptura = 0
        datas_producao_ruptura = []
        tem_item_sem_producao = False

        for cod, info in produtos_agrupados.items():
            qtd_saldo = info['qtd_saldo']
            preco = info['preco']
            valor_item = qtd_saldo * preco
            valor_total_pedido += valor_item

            dados = dados_produtos.get(cod, {})
            estoque_atual = dados.get('estoque_atual', 0)
            estoque_d7 = dados.get('menor_estoque_d7', 0)

            if qtd_saldo > estoque_d7:
                # Item COM RUPTURA
                ruptura = qtd_saldo - estoque_d7
                valor_com_ruptura += valor_item

                producoes = producoes_por_produto.get(cod, [])
                data_disponivel = None
                primeira_producao = None
                qtd_primeira_producao = 0

                if producoes:
                    primeira_producao = producoes[0]
                    qtd_primeira_producao = primeira_producao['qtd']

                    # Calcular quando terá estoque (IGUAL ruptura_sem_cache)
                    qtd_acumulada = estoque_d7
                    for prod in producoes:
                        qtd_acumulada += prod['qtd']
                        if qtd_acumulada >= qtd_saldo:
                            data_disponivel = prod['data']
                            data_disponivel = data_disponivel + timedelta(days=1)  # +1 dia lead time
                            break

                    if data_disponivel:
                        datas_producao_ruptura.append(data_disponivel)
                else:
                    tem_item_sem_producao = True

                itens_com_ruptura.append({
                    'cod_produto': cod,
                    'nome_produto': info['nome_produto'],
                    'qtd_saldo': int(qtd_saldo),
                    'estoque_atual': int(estoque_atual),
                    'estoque_min_d7': int(estoque_d7),
                    'ruptura_qtd': int(ruptura),
                    'data_producao': primeira_producao['data'].isoformat() if primeira_producao else None,
                    'qtd_producao': int(qtd_primeira_producao),
                    'data_disponivel': data_disponivel.isoformat() if data_disponivel else None
                })
            else:
                # Item SEM RUPTURA (disponível)
                itens_disponiveis_lista.append({
                    'cod_produto': cod,
                    'nome_produto': info['nome_produto'],
                    'qtd_saldo': int(qtd_saldo),
                    'estoque_atual': int(estoque_atual),
                    'estoque_min_d7': int(estoque_d7),
                    'preco_unitario': preco,
                    'valor_total': valor_item
                })

        # ===== MONTAR RESULTADO =====
        tempo_total = (time.time() - inicio_total) * 1000

        if not itens_com_ruptura:
            # Todos disponíveis
            resposta = {
                'success': True,
                'cnpj': cnpj,
                'data': {
                    'resumo': {
                        'num_pedido': f"CNPJ {cnpj}",
                        'criticidade': 'BAIXA',
                        'qtd_itens_ruptura': 0,
                        'qtd_itens_disponiveis': len(itens_disponiveis_lista),
                        'total_itens': len(itens_disponiveis_lista),
                        'percentual_disponibilidade': 100.0,
                        'percentual_ruptura': 0.0,
                        'valor_total_pedido': round(valor_total_pedido, 2),
                        'valor_com_ruptura': 0,
                        'data_disponibilidade_total': 'agora'
                    },
                    'itens': [],
                    'itens_disponiveis': itens_disponiveis_lista
                }
            }
            logger.info(f"✅ CNPJ {cnpj} OK em {tempo_total:.2f}ms")
            return jsonify(resposta)

        # Calcular métricas
        percentual_ruptura = (valor_com_ruptura / valor_total_pedido * 100) if valor_total_pedido > 0 else 0
        percentual_disponibilidade = 100 - percentual_ruptura

        # Data disponibilidade total (IGUAL ruptura_sem_cache)
        if tem_item_sem_producao:
            data_disponibilidade_total = None
        elif datas_producao_ruptura:
            data_disponibilidade_total = max(datas_producao_ruptura).isoformat()
        else:
            data_disponibilidade_total = None

        # Criticidade
        qtd_itens_ruptura = len(itens_com_ruptura)
        if qtd_itens_ruptura > 3 and percentual_ruptura > 10:
            criticidade = 'CRITICA'
        elif qtd_itens_ruptura <= 3 and percentual_ruptura <= 10:
            criticidade = 'ALTA'
        elif qtd_itens_ruptura <= 2 and percentual_ruptura <= 5:
            criticidade = 'MEDIA'
        else:
            criticidade = 'BAIXA'

        resposta = {
            'success': True,
            'cnpj': cnpj,
            'data': {
                'resumo': {
                    'num_pedido': f"CNPJ {cnpj}",
                    'criticidade': criticidade,
                    'qtd_itens_ruptura': qtd_itens_ruptura,
                    'qtd_itens_disponiveis': len(itens_disponiveis_lista),
                    'total_itens': len(produtos_agrupados),
                    'percentual_disponibilidade': round(percentual_disponibilidade, 0),
                    'percentual_ruptura': round(percentual_ruptura, 2),
                    'valor_total_pedido': round(valor_total_pedido, 2),
                    'valor_com_ruptura': round(valor_com_ruptura, 2),
                    'data_disponibilidade_total': data_disponibilidade_total
                },
                'itens': itens_com_ruptura,
                'itens_disponiveis': itens_disponiveis_lista
            }
        }

        logger.info(f"⚠️ CNPJ {cnpj} com ruptura em {tempo_total:.2f}ms")
        return jsonify(resposta)

    except Exception as e:
        logger.error(f"Erro ao analisar ruptura do CNPJ {cnpj}: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e),
            'cnpj': cnpj
        }), 500


@programacao_em_lote_bp.route('/api/analisar-ruptura-lote', methods=['POST'])
@login_required
def analisar_ruptura_lote():
    """
    API para análise de ruptura em lote considerando pedidos anteriores
    """
    try:
        
        dados = request.get_json()
        cnpjs = dados.get('cnpjs', [])
        ordem = dados.get('ordem', {})  # Ordem de prioridade dos CNPJs
        
        if not cnpjs:
            return jsonify({'success': False, 'error': 'Nenhum CNPJ fornecido'}), 400
        
        resultado = {}
        saidas_acumuladas = {}  # Acumula saídas dos pedidos anteriores
        
        # Processar na ordem definida
        cnpjs_ordenados = sorted(cnpjs, key=lambda x: ordem.get(x, 999))
        
        for idx, cnpj in enumerate(cnpjs_ordenados):
            # Buscar pedidos do CNPJ
            pedidos = db.session.query(CarteiraPrincipal).filter_by(
                cnpj_cpf=cnpj
            ).all()
            
            disponibilidade = {}
            data_completa = date.today()
            percentual_disponivel = 100.0
            
            for pedido in pedidos:
                cod_produto = pedido.cod_produto
                qtd_necessaria = float(pedido.qtd_saldo_produto_pedido)
                
                # Incluir saídas acumuladas dos pedidos anteriores
                saida_acumulada = saidas_acumuladas.get(cod_produto, 0)
                qtd_necessaria_total = qtd_necessaria + saida_acumulada
                
                # Buscar estoque atual
                estoque_atual = db.session.query(
                    func.sum(MovimentacaoEstoque.qtd_movimentacao)
                ).filter(
                    MovimentacaoEstoque.cod_produto == cod_produto,
                    MovimentacaoEstoque.ativo == True
                ).scalar() or 0
                
                # Verificar disponibilidade
                if float(estoque_atual) >= qtd_necessaria_total:
                    disponibilidade[cod_produto] = {
                        'disponivel': True,
                        'percentual': 100.0
                    }
                else:
                    disponibilidade[cod_produto] = {
                        'disponivel': False,
                        'percentual': (float(estoque_atual) / qtd_necessaria_total * 100) if qtd_necessaria_total > 0 else 0
                    }
                    
                    # Calcular data quando estará disponível
                    for dias in range(1, 30):
                        data_futura = date.today() + timedelta(days=dias)
                        
                        # Projetar estoque futuro
                        producoes = db.session.query(
                            func.sum(ProgramacaoProducao.qtd_programada)
                        ).filter(
                            ProgramacaoProducao.cod_produto == cod_produto,
                            ProgramacaoProducao.data_programacao <= data_futura
                        ).scalar() or 0
                        
                        if float(estoque_atual) + float(producoes) >= qtd_necessaria_total:
                            if data_futura > data_completa:
                                data_completa = data_futura
                            break
                
                # Acumular saída para próximos pedidos
                saidas_acumuladas[cod_produto] = saidas_acumuladas.get(cod_produto, 0) + qtd_necessaria
            
            # Calcular percentual geral
            total_itens = len(disponibilidade)
            itens_disponiveis = sum(1 for d in disponibilidade.values() if d['disponivel'])
            percentual_disponivel = (itens_disponiveis / total_itens * 100) if total_itens > 0 else 0
            
            resultado[cnpj] = {
                'data_completa': data_completa.strftime('%Y-%m-%d'),
                'percentual_disponivel': percentual_disponivel,
                'detalhes': disponibilidade
            }
        
        return jsonify({
            'success': True,
            'analise': resultado
        })
        
    except Exception as e:
        logger.error(f"Erro ao analisar ruptura em lote: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@programacao_em_lote_bp.route('/api/processar-agendamento-sendas-async', methods=['POST'])
@login_required
def processar_agendamento_sendas_async():
    """
    Processa agendamento no portal Sendas de forma ASSÍNCRONA usando Redis Queue.
    Retorna imediatamente com um job_id para acompanhamento.
    """
    try:
        from app.portal.workers import enqueue_job
        from app.portal.workers.sendas_jobs import processar_agendamento_sendas as processar_sendas_job
        from app.portal.models import PortalIntegracao, PortalLog
        
        # Obter dados da requisição
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Nenhum dado fornecido'}), 400
        
        logger.info("🚀 [ASYNC] Iniciando processamento assíncrono Sendas")
        logger.info(f"   Dados recebidos: {len(data.get('cnpjs', []) or data.get('agendamentos', []))} CNPJs")
        
        # Validar dados - aceitar tanto 'cnpjs' quanto 'agendamentos' para compatibilidade
        cnpjs_data = data.get('cnpjs', []) or data.get('agendamentos', [])
        if not cnpjs_data:
            return jsonify({'success': False, 'error': 'Nenhum CNPJ fornecido'}), 400
        
        # Filtrar CNPJs com datas válidas (como na função síncrona)
        cnpjs_validos = []
        cnpjs_ignorados = []
        
        for item in cnpjs_data:
            cnpj = item.get('cnpj')
            data_expedicao = item.get('expedicao')
            data_agendamento = item.get('agendamento')
            
            # Verificar se tem CNPJ e data de expedição (obrigatórios)
            if not all([cnpj, data_expedicao]):
                logger.warning(f"  ⚠️ CNPJ {cnpj} ignorado: falta data de expedição")
                cnpjs_ignorados.append(cnpj)
                continue
            
            # Verificar se tem data de agendamento (OBRIGATÓRIA para Sendas)
            if not data_agendamento:
                logger.warning(f"  ⚠️ CNPJ {cnpj} ignorado: falta data de agendamento (obrigatória para portal Sendas)")
                cnpjs_ignorados.append(cnpj)
                continue
            
            cnpjs_validos.append(item)
            logger.info(f"  ✅ CNPJ {cnpj} - Expedição: {data_expedicao}, Agendamento: {data_agendamento}")
        
        if not cnpjs_validos:
            return jsonify({
                'success': False,
                'error': 'Nenhum CNPJ com data de agendamento válida'
            }), 400
        
        # Preparar lista de agendamentos com conversão de datas
        lista_cnpjs_agendamento = []
        for agendamento in cnpjs_validos:
            cnpj = agendamento.get('cnpj')
            data_agendamento = agendamento.get('agendamento')
            
            # Converter data de string para date se necessário (como na versão síncrona)
            if isinstance(data_agendamento, str) and data_agendamento:
                data_agendamento = datetime.strptime(data_agendamento, '%Y-%m-%d').date()

            # Buscar dados completos para esse CNPJ
            # Calcular data_expedicao para SP (D-1 útil)
            data_expedicao = agendamento.get('expedicao')
            if isinstance(data_expedicao, str) and data_expedicao:
                # datetime já está importado no topo do arquivo
                data_expedicao = datetime.strptime(data_expedicao, '%Y-%m-%d').date()

            # Gerar protocolo único para este CNPJ com nova máscara
            protocolo = gerar_protocolo_sendas(cnpj, data_agendamento)

            # CRIAR SEPARAÇÕES DO SALDO ANTES DO AGENDAMENTO
            from app.carteira.routes.programacao_em_lote.busca_dados import criar_separacoes_do_saldo
            try:
                total_criadas_atualizadas = criar_separacoes_do_saldo(
                    cnpj=cnpj,
                    data_agendamento=data_agendamento,
                    data_expedicao=data_expedicao,
                    protocolo=protocolo
                )
                logger.info(f"  ✅ Separações preparadas para CNPJ {cnpj}: {total_criadas_atualizadas} registros")
            except Exception as e:
                logger.error(f"  ❌ Erro ao criar Separações para CNPJ {cnpj}: {e}")
                # Continuar mesmo se houver erro (as separações existentes ainda podem ser agendadas)

            # Buscar dados completos usando o novo módulo
            # Agora vai buscar TODAS as Separações (incluindo as recém-criadas)
            dados_completos = buscar_dados_completos_cnpj(
                cnpj=cnpj,
                data_agendamento=data_agendamento,
                data_expedicao=data_expedicao,
                protocolo=protocolo  # ✅ CORREÇÃO CRÍTICA: Passar o MESMO protocolo
            )

            # Adicionar tipo_fluxo e protocolo para identificação no retorno
            dados_completos['tipo_fluxo'] = 'programacao_lote'
            dados_completos['protocolo'] = protocolo  # Garantir que o protocolo está presente

            # ✅ COMPARAR COM PLANILHA MODELO E GRAVAR NA FILA
            logger.info(f"  🔍 Comparando {len(dados_completos['itens'])} itens com planilha modelo Sendas...")
            from app.portal.sendas.service_comparacao_sendas import ComparacaoSendasService
            comparacao_service = ComparacaoSendasService()

            # Preparar solicitações para comparação (formato esperado pelo service)
            solicitacoes = []
            for item in dados_completos['itens']:
                solicitacoes.append({
                    'cnpj': cnpj,
                    'num_pedido': item['num_pedido'],
                    'pedido_cliente': item.get('pedido_cliente'),
                    'cod_produto': item['cod_produto'],
                    'nome_produto': item['nome_produto'],
                    'quantidade': item['quantidade'],
                    'data_agendamento': data_agendamento
                })

            # Comparar com planilha modelo (converte códigos, valida disponibilidade, etc)
            resultado_comparacao = comparacao_service.comparar_multiplas_solicitacoes(solicitacoes)

            # Verificar se a comparação foi bem-sucedida
            if cnpj not in resultado_comparacao or not resultado_comparacao[cnpj].get('sucesso'):
                erro_msg = resultado_comparacao.get(cnpj, {}).get('erro', 'Erro desconhecido na comparação')
                logger.error(f"  ❌ Erro na comparação para CNPJ {cnpj}: {erro_msg}")
                # Continuar mesmo com erro (outros CNPJs podem ter sucesso)
                lista_cnpjs_agendamento.append(dados_completos)
                continue

            # Extrair itens confirmados da comparação
            itens_comparados = resultado_comparacao[cnpj].get('itens', [])
            if not itens_comparados:
                logger.warning(f"  ⚠️ Nenhum item encontrado na planilha modelo para CNPJ {cnpj}")
                lista_cnpjs_agendamento.append(dados_completos)
                continue

            logger.info(f"  ✅ {len(itens_comparados)} itens comparados com sucesso")

            # Preparar itens para gravar na fila (usando dados da comparação)
            itens_para_fila = []
            for item_comp in itens_comparados:
                # Dados da planilha modelo já estão em item_comp['encontrado']
                encontrado = item_comp.get('encontrado', {})
                solicitado = item_comp.get('solicitado', {})

                itens_para_fila.append({
                    'cnpj': cnpj,
                    'num_pedido': solicitado.get('num_pedido'),
                    'cod_produto': encontrado.get('codigo_produto_sendas'),  # ✅ CORRIGIDO: usar codigo_produto_sendas
                    'nome_produto': encontrado.get('descricao'),              # ✅ CORRIGIDO: usar descricao
                    'quantidade': solicitado.get('quantidade'),
                    'data_expedicao': data_expedicao,
                    'data_agendamento': data_agendamento,
                    'pedido_cliente': encontrado.get('codigo_pedido_sendas')  # ✅ CORRIGIDO: usar codigo_pedido_sendas
                })

            # Gravar na fila com tipo_origem='lote' e documento_origem=CNPJ
            resultado_fila = comparacao_service.gravar_fila_agendamento(
                itens_confirmados=itens_para_fila,
                tipo_origem='lote',
                documento_origem=cnpj
            )

            if resultado_fila['sucesso']:
                logger.info(f"  ✅ {resultado_fila['total_itens']} itens gravados na fila com protocolo {protocolo}")
            else:
                logger.error(f"  ❌ Erro ao gravar na fila: {resultado_fila.get('erro')}")

            lista_cnpjs_agendamento.append(dados_completos)

        # ✅ PRONTO! Itens gravados na fila com status='pendente'
        # O usuário pode exportar em /portal/sendas/exportacao

        logger.info(f"✅ Processamento concluído: {len(lista_cnpjs_agendamento)} CNPJs agendados")
        logger.info(f"📋 Planilhas disponíveis para exportação em /portal/sendas/exportacao")

        return jsonify({
            'success': True,
            'message': f'{len(lista_cnpjs_agendamento)} CNPJs agendados com sucesso',
            'total_cnpjs': len(lista_cnpjs_agendamento),
            'cnpjs_processados': [item['cnpj'] for item in lista_cnpjs_agendamento],
            'exportacao_url': '/portal/sendas/exportacao'
        })

    except Exception as e:
        logger.error(f"❌ Erro no processamento: {e}")
        logger.error(traceback.format_exc())

        return jsonify({
            'success': False,
            'error': f'Erro ao processar agendamento: {str(e)}'
        }), 500

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


@programacao_em_lote_bp.route('/api/analisar-ruptura-cnpj/<cnpj>', methods=['GET'])
@login_required
def analisar_ruptura_cnpj(cnpj):
    """
    API para análise de ruptura de UM CNPJ considerando TODOS os seus pedidos
    Usa as funções consolidadas de ruptura_utils.py
    Retorna formato compatível com o modal de ruptura existente
    """
    try:
        from .ruptura_utils import analisar_ruptura_lote as analisar_ruptura_funcao
        from app.producao.models import CadastroPalletizacao

        logger.info(f"Analisando ruptura para CNPJ {cnpj} - TODOS os pedidos")

        # Data de agendamento para análise (D+7 para projeção)
        data_agendamento = date.today() + timedelta(days=7)

        # Chamar função que AGREGA todos os produtos do CNPJ
        resultado_ruptura = analisar_ruptura_funcao([cnpj], data_agendamento)

        # Buscar informações adicionais do CNPJ para o resumo
        pedidos_cnpj = db.session.query(CarteiraPrincipal).filter(
            and_(
                CarteiraPrincipal.cnpj_cpf == cnpj,
                CarteiraPrincipal.ativo == True,
                CarteiraPrincipal.qtd_saldo_produto_pedido > 0
            )
        ).all()

        # Calcular valores totais
        valor_total = sum(
            float(p.qtd_saldo_produto_pedido or 0) * float(p.preco_produto_pedido or 0)
            for p in pedidos_cnpj
        )

        # Preparar itens em ruptura com detalhes
        itens_ruptura = []
        itens_disponiveis = []
        valor_com_ruptura = 0.0

        for produto_ruptura in resultado_ruptura.get('produtos_em_ruptura', []):
            # Buscar informações do produto na carteira
            pedido_produto = next(
                (p for p in pedidos_cnpj if p.cod_produto == produto_ruptura['cod_produto']),
                None
            )

            if pedido_produto:
                valor_produto = float(pedido_produto.qtd_saldo_produto_pedido or 0) * float(pedido_produto.preco_produto_pedido or 0)
                valor_com_ruptura += valor_produto

                # Buscar palletização para informações adicionais
                pallet_info = db.session.query(CadastroPalletizacao).filter_by(
                    cod_produto=produto_ruptura['cod_produto']
                ).first()

                itens_ruptura.append({
                    'cod_produto': produto_ruptura['cod_produto'],
                    'nome_produto': pedido_produto.nome_produto,
                    'qtd_saldo': produto_ruptura['quantidade_necessaria'],
                    'estoque_atual': produto_ruptura['estoque_atual'],
                    'estoque_min_d7': produto_ruptura['estoque_projetado'],
                    'data_producao': None,  # TODO: Buscar da programação de produção
                    'qtd_producao': produto_ruptura['entradas_projetadas'],
                    'data_disponivel': None,  # Produto em ruptura não tem data disponível imediata
                    'falta': produto_ruptura.get('falta', 0)
                })

        # Preparar itens disponíveis
        for produto_ok in resultado_ruptura.get('produtos_ok', []):
            pedido_produto = next(
                (p for p in pedidos_cnpj if p.cod_produto == produto_ok['cod_produto']),
                None
            )

            if pedido_produto:
                itens_disponiveis.append({
                    'cod_produto': produto_ok['cod_produto'],
                    'nome_produto': pedido_produto.nome_produto,
                    'qtd_saldo': produto_ok['quantidade_necessaria'],
                    'estoque_atual': produto_ok['estoque_atual'],
                    'estoque_min_d7': produto_ok['estoque_projetado']
                })

        # Calcular percentuais
        total_itens = len(resultado_ruptura.get('produtos_em_ruptura', [])) + \
                     len(resultado_ruptura.get('produtos_ok', [])) + \
                     len(resultado_ruptura.get('produtos_criticos', []))

        qtd_itens_ruptura = len(resultado_ruptura.get('produtos_em_ruptura', []))
        qtd_itens_disponiveis = len(resultado_ruptura.get('produtos_ok', []))

        percentual_disponibilidade = (qtd_itens_disponiveis / total_itens * 100) if total_itens > 0 else 100.0
        percentual_ruptura = (qtd_itens_ruptura / total_itens * 100) if total_itens > 0 else 0.0

        # Determinar criticidade
        if percentual_ruptura >= 50:
            criticidade = 'CRITICA'
        elif percentual_ruptura >= 30:
            criticidade = 'ALTA'
        elif percentual_ruptura >= 10:
            criticidade = 'MEDIA'
        else:
            criticidade = 'BAIXA'

        # Montar resposta no formato esperado pelo modal
        resposta = {
            'success': True,
            'cnpj': cnpj,
            'data': {
                'resumo': {
                    'num_pedido': f"CNPJ {cnpj}",  # Identificação
                    'criticidade': criticidade,
                    'qtd_itens_ruptura': qtd_itens_ruptura,
                    'qtd_itens_disponiveis': qtd_itens_disponiveis,
                    'total_itens': total_itens,
                    'percentual_disponibilidade': round(percentual_disponibilidade, 2),
                    'percentual_ruptura': round(percentual_ruptura, 2),
                    'valor_total_pedido': valor_total,
                    'valor_com_ruptura': valor_com_ruptura,
                    'data_disponibilidade_total': data_agendamento.strftime('%Y-%m-%d') if qtd_itens_ruptura > 0 else None
                },
                'itens': itens_ruptura,
                'itens_disponiveis': itens_disponiveis
            }
        }

        logger.info(f"Ruptura analisada: {qtd_itens_ruptura}/{total_itens} itens em ruptura ({percentual_ruptura:.1f}%)")

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
                data_expedicao=data_expedicao
            )

            # Adicionar tipo_fluxo e protocolo para identificação no retorno
            dados_completos['tipo_fluxo'] = 'programacao_lote'
            dados_completos['protocolo'] = protocolo  # Garantir que o protocolo está presente

            lista_cnpjs_agendamento.append(dados_completos)
        
        # Criar registro de integração no banco
        # Gerar lote_id único usando a função padrão
        lote_id = gerar_lote_id()
        
        # Preparar dados para JSONB - converter dates e estruturas complexas
        lista_cnpjs_json = []
        for item in lista_cnpjs_agendamento:
            # Serializar item para JSON, convertendo dates e Decimals
            item_json = {
                'cnpj': item['cnpj'],
                'data_agendamento': item['data_agendamento'].isoformat() if item.get('data_agendamento') and hasattr(item['data_agendamento'], 'isoformat') else str(item.get('data_agendamento')),
                'data_expedicao': item['data_expedicao'].isoformat() if item.get('data_expedicao') and hasattr(item['data_expedicao'], 'isoformat') else str(item.get('data_expedicao')),
                'protocolo': item.get('protocolo'),
                'peso_total': float(item.get('peso_total', 0)),
                'tipo_fluxo': item.get('tipo_fluxo', 'programacao_lote'),
                'total_itens': len(item.get('itens', []))
            }
            lista_cnpjs_json.append(item_json)
        
        integracao = PortalIntegracao(
            portal='sendas',
            lote_id=lote_id,
            tipo_lote='agendamento_lote',
            status='aguardando',
            dados_enviados={
                'cnpjs': lista_cnpjs_json,  # Dados resumidos para log
                'total': len(lista_cnpjs_json),
                'usuario': current_user.nome if current_user else 'Sistema',
                # Incluir metadados do fluxo nos dados_enviados
                'tipo_fluxo': 'programacao_lote',
                'origem': 'programacao_em_lote'
            }
        )
        db.session.add(integracao)
        db.session.commit()
        
        logger.info(f"📝 Integração criada com ID: {integracao.id}")
        
        # Enfileirar job no Redis Queue
        try:
            job = enqueue_job(
                processar_sendas_job,
                integracao.id,
                lista_cnpjs_agendamento,
                current_user.nome if current_user else 'Sistema',
                queue_name='sendas',  # Usa fila específica do Sendas
                timeout='15m'  # Timeout de 15 minutos
            )
            
            # Salvar job_id na integração
            integracao.job_id = job.id
            db.session.commit()
            
            logger.info(f"✅ Job {job.id} enfileirado na fila 'sendas'")
            
            # Log de enfileiramento
            log = PortalLog(
                integracao_id=integracao.id,
                acao='job_enfileirado',
                sucesso=True,
                mensagem=f'Job {job.id} criado para processar {len(lista_cnpjs_agendamento)} CNPJs',
                dados_contexto={'job_id': job.id, 'queue': 'sendas'}
            )
            db.session.add(log)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Processamento iniciado em background',
                'job_id': job.id,
                'integracao_id': integracao.id,
                'total_cnpjs': len(lista_cnpjs_agendamento),
                'status_url': f'/portal/api/status-job/{job.id}'
            }), 202  # 202 Accepted - processamento assíncrono
            
        except Exception as queue_error:
            logger.error(f"❌ Erro ao enfileirar job: {queue_error}")
            
            # Atualizar status da integração
            integracao.status = 'erro'
            integracao.resposta_portal = {'erro': str(queue_error)}
            db.session.commit()
            
            # Se Redis não estiver disponível, sugerir processamento síncrono
            return jsonify({
                'success': False,
                'error': 'Fila de processamento indisponível. Use o endpoint síncrono ou verifique o Redis.',
                'detalhes': str(queue_error)
            }), 503  # 503 Service Unavailable
            
    except Exception as e:
        logger.error(f"❌ Erro no endpoint assíncrono: {e}")
        logger.error(traceback.format_exc())
        
        return jsonify({
            'success': False,
            'error': f'Erro ao iniciar processamento: {str(e)}'
        }), 500


@programacao_em_lote_bp.route('/api/status-job-sendas/<job_id>', methods=['GET'])
@login_required
def status_job_sendas(job_id):
    """
    Verifica o status de um job Sendas no Redis Queue
    """
    try:
        from rq.job import Job
        from app.portal.workers import get_redis_connection
        
        redis_conn = get_redis_connection()
        job = Job.fetch(job_id, connection=redis_conn)
        
        status = job.get_status()
        result = None
        error = None
        
        if status == 'finished':
            result = job.result
        elif status == 'failed':
            error = str(job.exc_info) if job.exc_info else 'Erro desconhecido'
        
        return jsonify({
            'job_id': job_id,
            'status': status,
            'created_at': job.created_at.isoformat() if job.created_at else None,
            'started_at': job.started_at.isoformat() if job.started_at else None,
            'ended_at': job.ended_at.isoformat() if job.ended_at else None,
            'result': result,
            'error': error,
            'meta': job.meta
        })
        
    except Exception as e:
        logger.error(f"Erro ao verificar status do job {job_id}: {e}")
        return jsonify({
            'job_id': job_id,
            'status': 'not_found',
            'error': str(e)
        }), 404

"""
Rotas para programação em lote de Redes SP (Atacadão e Sendas)
"""

from flask import render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required
from sqlalchemy import func, and_, distinct
from decimal import Decimal
from datetime import date, timedelta
import logging

from app import db
from app.carteira.models import CarteiraPrincipal
from app.separacao.models import Separacao
from app.faturamento.models import FaturamentoProduto
from app.producao.models import CadastroPalletizacao
from app.localidades.models import CadastroSubRota
from app.portal.utils.grupo_empresarial import GrupoEmpresarial
from app.estoque.models import MovimentacaoEstoque
from app.producao.models import ProgramacaoProducao

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
            'rede': rede.title(),
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
    
    # 1. Buscar CNPJs na CarteiraPrincipal (pedidos pendentes) com cod_uf='SP'
    pedidos_carteira = db.session.query(
        CarteiraPrincipal.cnpj_cpf,
        CarteiraPrincipal.raz_social_red,
        CarteiraPrincipal.nome_cidade,
        CarteiraPrincipal.cod_uf,
        CarteiraPrincipal.vendedor,
        CarteiraPrincipal.equipe_vendas,
        func.count(distinct(CarteiraPrincipal.num_pedido)).label('qtd_pedidos')
    ).filter(
        CarteiraPrincipal.cod_uf == 'SP'
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
            
            # Verificar se este CNPJ já tem pedidos na carteira
            pedidos_na_carteira = db.session.query(
                distinct(CarteiraPrincipal.num_pedido)
            ).filter(
                CarteiraPrincipal.cnpj_cpf == cnpj_key
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
    """
    from datetime import date
    
    tem_protocolo = False
    agendamento_confirmado = False
    tem_pendencias = False
    
    # Verificar todas as separações
    for pedido in dados_cnpj['pedidos']:
        # Verificar separações
        for sep in pedido.get('separacoes', []):
            if sep.get('protocolo'):
                tem_protocolo = True
            if sep.get('agendamento_confirmado'):
                agendamento_confirmado = True
            if sep.get('agendamento'):
                # Verificar se agendamento é passado
                data_agenda = sep.get('agendamento')
                if isinstance(data_agenda, str):
                    data_agenda = date.fromisoformat(data_agenda)
                if data_agenda and data_agenda < date.today():
                    tem_pendencias = True
        
        # Verificar NFs no CD
        for nf in pedido.get('nfs_cd', []):
            if not nf.get('protocolo'):
                tem_pendencias = True
    
    # Atualizar dados
    dados_cnpj['tem_protocolo'] = tem_protocolo
    dados_cnpj['agendamento_confirmado'] = agendamento_confirmado
    dados_cnpj['tem_pendencias'] = tem_pendencias


def _adicionar_pedidos_cnpj(dados_cnpj, cnpj):
    """
    Adiciona informações detalhadas dos pedidos de um CNPJ
    """
    # Buscar pedidos na CarteiraPrincipal
    pedidos = db.session.query(
        CarteiraPrincipal.num_pedido,
        CarteiraPrincipal.data_pedido,
        CarteiraPrincipal.pedido_cliente,
        CarteiraPrincipal.observ_ped_1,
        func.sum(CarteiraPrincipal.qtd_saldo_produto_pedido).label('qtd_total'),
        func.sum(CarteiraPrincipal.qtd_saldo_produto_pedido * CarteiraPrincipal.preco_produto_pedido).label('valor_total')
    ).filter(
        CarteiraPrincipal.cnpj_cpf == cnpj
    ).group_by(
        CarteiraPrincipal.num_pedido,
        CarteiraPrincipal.data_pedido,
        CarteiraPrincipal.pedido_cliente,
        CarteiraPrincipal.observ_ped_1
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
            'pallets_pendente': Decimal('0')
        }
        
        # Calcular quantidades pendentes (CarteiraPrincipal - Separacao)
        _calcular_pendencias_pedido(pedido_info, pedido.num_pedido)
        
        # Buscar separações do pedido
        _adicionar_separacoes_pedido(pedido_info, pedido.num_pedido)
        
        # Buscar NFs no CD do pedido
        _adicionar_nfs_cd_pedido(pedido_info, pedido.num_pedido)
        
        dados_cnpj['pedidos'].append(pedido_info)
        dados_cnpj['qtd_pedidos'] += 1
        
        # Atualizar totais
        dados_cnpj['total_valor'] += pedido_info['valor_pendente']
        dados_cnpj['total_peso'] += pedido_info['peso_pendente']
        dados_cnpj['total_pallets'] += pedido_info['pallets_pendente']


def _calcular_pendencias_pedido(pedido_info, num_pedido):
    """
    Calcula valores pendentes de um pedido (CarteiraPrincipal - Separacao não sincronizada)
    """
    # Buscar itens da carteira
    itens_carteira = db.session.query(
        CarteiraPrincipal.cod_produto,
        CarteiraPrincipal.qtd_saldo_produto_pedido,
        CarteiraPrincipal.preco_produto_pedido
    ).filter(
        CarteiraPrincipal.num_pedido == num_pedido
    ).all()
    
    for item in itens_carteira:
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
            Separacao.sincronizado_nf == False
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
            'valor': sep.valor_total or Decimal('0'),
            'peso': sep.peso_total or Decimal('0'),
            'pallets': sep.pallet_total or Decimal('0')
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
            Separacao.nf_cd == True
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
            'pallets': nf.pallet_total or Decimal('0')
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
        from datetime import timedelta
        
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
                        
                        # Projetar estoque com produções futuras
                        producoes = db.session.query(
                            func.sum(ProgramacaoProducao.qtd_programada)
                        ).filter(
                            ProgramacaoProducao.cod_produto == cod_produto,
                            ProgramacaoProducao.data_programacao <= data_futura
                        ).scalar() or 0
                        
                        # Considerar saídas já programadas
                        saidas_programadas = db.session.query(
                            func.sum(Separacao.qtd_saldo)
                        ).filter(
                            Separacao.cod_produto == cod_produto,
                            Separacao.expedicao <= data_futura,
                            Separacao.sincronizado_nf == False,
                            ~Separacao.cnpj_cpf.in_(cnpjs_ordenados)  # Excluir CNPJs da rede
                        ).scalar() or 0
                        
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


@programacao_em_lote_bp.route('/api/processar-lote', methods=['POST'])
@login_required
def processar_lote():
    """
    API para processar agendamento em lote (fase futura)
    """
    try:
        dados = request.get_json()
        
        # TODO: Implementar processamento em lote com Redis/Workers
        
        return jsonify({
            'success': True,
            'message': 'Processamento em lote iniciado'
        })
        
    except Exception as e:
        logger.error(f"Erro ao processar lote: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
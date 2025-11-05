from flask import render_template, request, redirect, url_for, Blueprint, flash, session
from flask_login import login_required, current_user
from app import db
from app.pedidos.models import Pedido
from app.pedidos.forms import FiltroPedidosForm, CotarFreteForm, EditarPedidoForm
from app.separacao.models import Separacao
from app.carteira.models import CarteiraPrincipal
from app.transportadoras.models import Transportadora
from app.veiculos.models import Veiculo
from sqlalchemy import func, distinct
from app.utils.localizacao import LocalizacaoService
from app.cadastros_agendamento.models import ContatoAgendamento
from app.embarques.models import Embarque, EmbarqueItem
from flask import jsonify
from app.utils.lote_utils import gerar_lote_id  # Função padronizada para gerar lotes
from app.utils.embarque_numero import obter_proximo_numero_embarque
from datetime import datetime
from app.utils.tabela_frete_manager import TabelaFreteManager


# routes.py
pedidos_bp = Blueprint('pedidos', __name__, url_prefix='/pedidos')

@pedidos_bp.route('/lista_pedidos', methods=['GET','POST'])
@login_required
def lista_pedidos():
    from datetime import datetime, timedelta
    
    # Form para filtrar:
    filtro_form = FiltroPedidosForm()

    # Carrega opções únicas de Rota e Sub Rota
    rotas = db.session.query(distinct(Pedido.rota)).filter(Pedido.rota.isnot(None)).order_by(Pedido.rota).all()
    sub_rotas = db.session.query(distinct(Pedido.sub_rota)).filter(Pedido.sub_rota.isnot(None)).order_by(Pedido.sub_rota).all()
    
    # Atualiza as choices dos campos
    filtro_form.rota.choices = [('', 'Todas')] + [(r[0], r[0]) for r in rotas if r[0]]
    filtro_form.sub_rota.choices = [('', 'Todas')] + [(sr[0], sr[0]) for sr in sub_rotas if sr[0]]

    # Form para cotar frete (checkbox e botao):
    cotar_form = CotarFreteForm()

    query = Pedido.query

    # ✅ NOVO: Filtros de atalho por GET parameters
    filtro_status = request.args.get('status')
    filtro_data = request.args.get('data')
    
    # ✅ NOVO: Parâmetros de ordenação
    sort_by = request.args.get('sort_by', 'expedicao')  # Default: ordenar por expedição
    sort_order = request.args.get('sort_order', 'asc')  # Default: ascendente
    
    # ✅ NOVO: Contadores para os botões de atalho por data
    hoje = datetime.now().date()
    contadores_data = {}
    for i in range(4):  # D+0, D+1, D+2, D+3
        data_filtro = hoje + timedelta(days=i)
        
        # Conta total de pedidos da data
        total_data = Pedido.query.filter(
            func.date(Pedido.expedicao) == data_filtro
        ).count()
        
        # Conta pedidos ABERTOS da data (APENAS por status='ABERTO' e expedição)
        abertos_data = Pedido.query.filter(
            func.date(Pedido.expedicao) == data_filtro,
            Pedido.status == 'ABERTO'  # ✅ Filtro APENAS por status
        ).count()
        
        contadores_data[f'd{i}'] = {
            'data': data_filtro,
            'total': total_data,
            'abertos': abertos_data
        }
    
    # ✅ NOVO: Contadores para os botões de status
    contadores_status = {
        'todos': Pedido.query.count(),
        'abertos': Pedido.query.filter(
            Pedido.status == 'ABERTO'  # ✅ Filtro APENAS por status
        ).count(),
        'cotados': Pedido.query.filter(
            Pedido.cotacao_id.isnot(None),
            Pedido.data_embarque.is_(None),
            (Pedido.nf.is_(None)) | (Pedido.nf == ""),
            Pedido.nf_cd == False
        ).count(),
        'nf_cd': Pedido.query.filter(Pedido.nf_cd == True).count(),
        # Contador de atrasados (cotados ou abertos com expedição < hoje)
        'atrasados': Pedido.query.filter(
            db.or_(
                db.and_(Pedido.cotacao_id.isnot(None), Pedido.data_embarque.is_(None), (Pedido.nf.is_(None)) | (Pedido.nf == "")),  # COTADO
                db.and_(Pedido.cotacao_id.is_(None), (Pedido.nf.is_(None)) | (Pedido.nf == ""))  # ABERTO
            ),
            Pedido.nf_cd == False,
            Pedido.expedicao < hoje,
            (Pedido.nf.is_(None)) | (Pedido.nf == "")  # Sem NF
        ).count(),
        # Contador de atrasados apenas abertos
        'atrasados_abertos': Pedido.query.filter(
            Pedido.status == 'ABERTO',  # ✅ Filtro APENAS por status
            Pedido.expedicao < hoje
        ).count(),
        # ✅ NOVO: Contador de pedidos sem data de expedição
        'sem_data': Pedido.query.filter(
            Pedido.expedicao.is_(None),
            Pedido.nf_cd == False,
            (Pedido.nf.is_(None)) | (Pedido.nf == ""),
            Pedido.data_embarque.is_(None)
        ).count()
    }
    
    # ✅ NOVO: Contador de pedidos com agendamento pendente
    # Buscar CNPJs que precisam de agendamento
    contatos_agendamento_count = ContatoAgendamento.query.filter(
        ContatoAgendamento.forma is not None,
        ContatoAgendamento.forma != '',
        ContatoAgendamento.forma != 'SEM AGENDAMENTO'
    ).all()
    
    # Criar lista de CNPJs válidos para agendamento
    cnpjs_validos_agendamento = []
    for contato in contatos_agendamento_count:
        if contato.cnpj:
            cnpjs_validos_agendamento.append(contato.cnpj)
    
    # Contar pedidos sem agendamento que deveriam ter
    if cnpjs_validos_agendamento:
        contadores_status['agend_pendente'] = Pedido.query.filter(
            Pedido.cnpj_cpf.in_(cnpjs_validos_agendamento),
            (Pedido.agendamento.is_(None)),  # Sem data de agendamento
            Pedido.nf_cd == False,  # Não está no CD
            (Pedido.nf.is_(None)) | (Pedido.nf == ""),  # Sem NF
            Pedido.data_embarque.is_(None)  # Não embarcado
        ).count()
    else:
        contadores_status['agend_pendente'] = 0

    # ✅ NOVO: Contadores para aguardando pagamento e aguardando item
    # Estes serão calculados corretamente consultando as tabelas diretamente

    # 1. Ag. Item: Contar lotes com falta_item=True na Separacao
    try:
        lotes_falta_item = db.session.query(Separacao.separacao_lote_id).filter(
            Separacao.falta_item == True,
            Separacao.sincronizado_nf == False
        ).distinct().subquery()

        contadores_status['ag_item'] = db.session.query(func.count(distinct(Pedido.separacao_lote_id))).filter(
            Pedido.separacao_lote_id.in_(db.session.query(lotes_falta_item)),
            Pedido.nf_cd == False,
            (Pedido.nf.is_(None)) | (Pedido.nf == "")
        ).scalar() or 0

        lotes_falta_item_ids = [r[0] for r in db.session.query(Separacao.separacao_lote_id).filter(
            Separacao.falta_item == True,
            Separacao.sincronizado_nf == False
        ).distinct().all()]
    except Exception as e:
        print(f"[ERRO Contador ag_item] {e}")
        contadores_status['ag_item'] = 0
        lotes_falta_item_ids = []

    # 2. Ag. Pagamento: Contar pedidos ANTECIPADOS com falta_pagamento=True
    try:
        # Buscar pedidos com ANTECIPADO
        num_pedidos_antecipados = [r[0] for r in db.session.query(
            distinct(CarteiraPrincipal.num_pedido)
        ).filter(
            CarteiraPrincipal.cond_pgto_pedido.ilike('%ANTECIPADO%')
        ).all() if r[0]]

        if num_pedidos_antecipados:
            lotes_falta_pgto = db.session.query(Separacao.separacao_lote_id).filter(
                Separacao.num_pedido.in_(num_pedidos_antecipados),
                Separacao.falta_pagamento == True,
                Separacao.sincronizado_nf == False
            ).distinct().subquery()

            contadores_status['ag_pagamento'] = db.session.query(func.count(distinct(Pedido.separacao_lote_id))).filter(
                Pedido.separacao_lote_id.in_(db.session.query(lotes_falta_pgto)),
                Pedido.nf_cd == False,
                (Pedido.nf.is_(None)) | (Pedido.nf == "")
            ).scalar() or 0

            lotes_falta_pagamento_ids = [r[0] for r in db.session.query(Separacao.separacao_lote_id).filter(
                Separacao.num_pedido.in_(num_pedidos_antecipados),
                Separacao.falta_pagamento == True,
                Separacao.sincronizado_nf == False
            ).distinct().all()]
        else:
            contadores_status['ag_pagamento'] = 0
            lotes_falta_pagamento_ids = []
    except Exception as e:
        print(f"[ERRO Contador ag_pagamento] {e}")
        contadores_status['ag_pagamento'] = 0
        lotes_falta_pagamento_ids = []

    # ✅ APLICAR FILTROS DE ATALHO (botões) - SEMPRE PRIMEIRO
    filtros_botao_aplicados = False
    
    if filtro_status:
        filtros_botao_aplicados = True
        if filtro_status == 'abertos':
            query = query.filter(
                Pedido.status == 'ABERTO'  # ✅ Filtro APENAS por status
            )
        elif filtro_status == 'cotados':
            query = query.filter(
                Pedido.cotacao_id.isnot(None),
                Pedido.data_embarque.is_(None),
                (Pedido.nf.is_(None)) | (Pedido.nf == ""),
                Pedido.nf_cd == False
            )
        elif filtro_status == 'nf_cd':
            query = query.filter(Pedido.nf_cd == True)
        elif filtro_status == 'atrasados':
            # Pedidos cotados ou abertos com expedição < hoje (sem NF)
            query = query.filter(
                db.or_(
                    db.and_(Pedido.cotacao_id.isnot(None), Pedido.data_embarque.is_(None), (Pedido.nf.is_(None)) | (Pedido.nf == "")),  # COTADO
                    db.and_(Pedido.cotacao_id.is_(None), (Pedido.nf.is_(None)) | (Pedido.nf == ""))  # ABERTO
                ),
                Pedido.nf_cd == False,
                Pedido.expedicao < hoje,
                (Pedido.nf.is_(None)) | (Pedido.nf == "")  # Sem NF
            )
        elif filtro_status == 'atrasados_abertos':
            # Apenas abertos com expedição < hoje (sem NF)
            query = query.filter(
                Pedido.cotacao_id.is_(None),
                (Pedido.nf.is_(None)) | (Pedido.nf == ""),
                Pedido.nf_cd == False,
                Pedido.expedicao < hoje
            )
        elif filtro_status == 'agend_pendente':
            # ✅ NOVO: Filtro para pedidos com agendamento pendente
            if cnpjs_validos_agendamento:
                query = query.filter(
                    Pedido.cnpj_cpf.in_(cnpjs_validos_agendamento),
                    (Pedido.agendamento.is_(None)),  # Sem data de agendamento
                    Pedido.nf_cd == False,  # Não está no CD
                    (Pedido.nf.is_(None)) | (Pedido.nf == ""),  # Sem NF
                    Pedido.data_embarque.is_(None)  # Não embarcado
                )
            else:
                # Se não há CNPJs válidos, retorna query vazia
                query = query.filter(Pedido.separacao_lote_id == 'IMPOSSIVEL')
        elif filtro_status == 'sem_data':
            # ✅ NOVO: Filtro para pedidos sem data de expedição
            query = query.filter(
                Pedido.expedicao.is_(None),
                Pedido.nf_cd == False,
                (Pedido.nf.is_(None)) | (Pedido.nf == ""),
                Pedido.data_embarque.is_(None)
            )
        elif filtro_status == 'ag_pagamento':
            # ✅ NOVO: Filtro para pedidos aguardando pagamento
            if lotes_falta_pagamento_ids:
                query = query.filter(
                    Pedido.separacao_lote_id.in_(lotes_falta_pagamento_ids),
                    Pedido.nf_cd == False,
                    (Pedido.nf.is_(None)) | (Pedido.nf == "")
                )
            else:
                query = query.filter(Pedido.separacao_lote_id == 'IMPOSSIVEL')
        elif filtro_status == 'ag_item':
            # ✅ NOVO: Filtro para pedidos aguardando item
            if lotes_falta_item_ids:
                query = query.filter(
                    Pedido.separacao_lote_id.in_(lotes_falta_item_ids),
                    Pedido.nf_cd == False,
                    (Pedido.nf.is_(None)) | (Pedido.nf == "")
                )
            else:
                query = query.filter(Pedido.separacao_lote_id == 'IMPOSSIVEL')
        # 'todos' não aplica filtro
    
    if filtro_data:
        filtros_botao_aplicados = True
        try:
            data_selecionada = datetime.strptime(filtro_data, '%Y-%m-%d').date()
            query = query.filter(func.date(Pedido.expedicao) == data_selecionada)
        except ValueError:
            pass  # Ignora data inválida

    # ✅ PRESERVA filtros GET quando for POST do formulário
    form_preservar_status = filtro_status
    form_preservar_data = filtro_data

    # ✅ CORRIGIDO: SEMPRE aplicar filtros do formulário quando houver dados
    # Os filtros de botão (GET) e formulário (POST/GET) agora trabalham JUNTOS
    aplicar_filtros_formulario = filtro_form.validate_on_submit() or (request.method == 'GET' and any([
        request.args.get('numero_pedido'),
        request.args.get('cnpj_cpf'),
        request.args.get('cliente'),
        request.args.get('status_form'),  # Renomeado para não conflitar com filtro de botão
        request.args.get('uf'),
        request.args.get('rota'),
        request.args.get('sub_rota')
    ]))

    if aplicar_filtros_formulario:
        # Filtros básicos
        if filtro_form.numero_pedido.data:
            query = query.filter(
                Pedido.num_pedido.ilike(f"%{filtro_form.numero_pedido.data}%")
            )
        if filtro_form.cnpj_cpf.data:
            query = query.filter(
                Pedido.cnpj_cpf.ilike(f"%{filtro_form.cnpj_cpf.data}%")
            )
        
        # ✨ NOVO: Filtro por cliente (razão social)
        if filtro_form.cliente.data:
            query = query.filter(
                Pedido.raz_social_red.ilike(f"%{filtro_form.cliente.data}%")
            )
        
        # ✨ NOVO: Filtro por status
        if filtro_form.status.data:
            status_filtro = filtro_form.status.data
            if status_filtro == 'NF no CD':
                # ✅ NOVO: Filtro para pedidos com NF no CD
                query = query.filter(Pedido.nf_cd == True)
            elif status_filtro == 'FATURADO':
                query = query.filter(
                    (Pedido.nf.isnot(None)) & (Pedido.nf != ""),
                    Pedido.nf_cd == False  # ✅ CORRIGIDO: Não deve estar no CD
                )
            elif status_filtro == 'COTADO':
                query = query.filter(
                    Pedido.cotacao_id.isnot(None),
                    Pedido.data_embarque.is_(None),
                    (Pedido.nf.is_(None)) | (Pedido.nf == ""),
                    Pedido.nf_cd == False  # ✅ CORRIGIDO: Não deve estar no CD
                )
            elif status_filtro == 'ABERTO':
                query = query.filter(
                    Pedido.status == 'ABERTO'  # ✅ Filtro APENAS por status
                )
        
        # ✨ NOVO: Filtro para pedidos pendentes de cotação
        if filtro_form.pendente_cotacao.data:
            query = query.filter(
                Pedido.cotacao_id.is_(None)
            )
        
        # Filtros existentes
        if filtro_form.somente_sem_nf.data:
            query = query.filter(
                (Pedido.nf.is_(None)) | (Pedido.nf == "")
            )
        if filtro_form.uf.data:
            if filtro_form.uf.data == 'FOB':
                # ✅ Para FOB, buscar apenas pedidos com rota FOB
                query = query.filter(Pedido.rota == 'FOB')
            elif filtro_form.uf.data == 'SP':
                # ✅ Para SP, incluir UF SP + pedidos com rota RED (excluindo FOB)
                query = query.filter(
                    (Pedido.cod_uf == 'SP') | 
                    (Pedido.rota == 'RED')
                ).filter(Pedido.rota != 'FOB')  # Exclui FOB
            else:
                # ✅ Para outras UFs, filtro normal EXCLUINDO RED e FOB
                query = query.filter(
                    Pedido.cod_uf == filtro_form.uf.data,
                    Pedido.rota != 'RED',
                    Pedido.rota != 'FOB'
                )
        if filtro_form.rota.data:
            query = query.filter(Pedido.rota == filtro_form.rota.data)
        if filtro_form.sub_rota.data:
            query = query.filter(Pedido.sub_rota == filtro_form.sub_rota.data)
        if filtro_form.expedicao_inicio.data:
            query = query.filter(Pedido.expedicao >= filtro_form.expedicao_inicio.data)
        if filtro_form.expedicao_fim.data:
            query = query.filter(Pedido.expedicao <= filtro_form.expedicao_fim.data)

    # ✅ NOVO: Ordenação dinâmica baseada em parâmetros
    # Mapear campos de ordenação para atributos do modelo
    campos_ordenacao = {
        'num_pedido': Pedido.num_pedido,
        'cnpj_cpf': Pedido.cnpj_cpf,
        'raz_social_red': Pedido.raz_social_red,
        'nome_cidade': Pedido.nome_cidade,
        'cod_uf': Pedido.cod_uf,
        'valor_saldo_total': Pedido.valor_saldo_total,
        'peso_total': Pedido.peso_total,
        'rota': Pedido.rota,
        'sub_rota': Pedido.sub_rota,
        'expedicao': Pedido.expedicao,
        'agendamento': Pedido.agendamento,
        'protocolo': Pedido.protocolo,
        'nf': Pedido.nf,
        'data_embarque': Pedido.data_embarque
    }
    
    # ✅ CORRIGIDO: Aplicar SEMPRE a ordenação hierárquica
    # A ordenação hierárquica SEMPRE é aplicada para manter a consistência visual
    # Mesmo quando usuário clica em uma coluna para ordenar, mantemos a hierarquia como critério secundário
    if sort_by in campos_ordenacao and sort_by != 'expedicao':
        # Se usuário ordenou por uma coluna específica, usa como critério primário
        # mas mantém a hierarquia como critérios secundários
        campo_ordenacao = campos_ordenacao[sort_by]
        if sort_order == 'desc':
            query = query.order_by(
                campo_ordenacao.desc(),
                Pedido.rota.asc().nullslast(),
                Pedido.sub_rota.asc().nullslast(),
                Pedido.cnpj_cpf.asc().nullslast(),
                Pedido.expedicao.asc().nullslast()
            )
        else:
            query = query.order_by(
                campo_ordenacao.asc(),
                Pedido.rota.asc().nullslast(),
                Pedido.sub_rota.asc().nullslast(),
                Pedido.cnpj_cpf.asc().nullslast(),
                Pedido.expedicao.asc().nullslast()
            )
    else:
        # Ordenação padrão hierárquica: SEMPRE aplicada
        query = query.order_by(
            Pedido.rota.asc().nullslast(),      # 1º Rota: menor para maior (A-Z)
            Pedido.sub_rota.asc().nullslast(),  # 2º Sub-rota: menor para maior (A-Z)
            Pedido.cnpj_cpf.asc().nullslast(),  # 3º CNPJ: menor para maior (0-9)
            Pedido.expedicao.asc().nullslast(), # 4º Data de expedição
        )

    # Paginação com 50 itens por página
    page = request.args.get('page', 1, type=int)
    per_page = 50
    paginacao = query.paginate(page=page, per_page=per_page, error_out=False)
    pedidos = paginacao.items

    # ✅ NOVO: Busca o último embarque válido para cada pedido

    # Cria um dicionário para mapear lote_id -> último embarque
    embarques_por_lote = {}

    # Busca todos os lotes únicos dos pedidos
    lotes_ids = [p.separacao_lote_id for p in pedidos if p.separacao_lote_id]
    
    if lotes_ids:
        # Busca os itens de embarque ativos para esses lotes
        itens_embarque = (
            db.session.query(EmbarqueItem, Embarque)
            .join(Embarque, EmbarqueItem.embarque_id == Embarque.id)
            .filter(
                EmbarqueItem.separacao_lote_id.in_(lotes_ids),
                EmbarqueItem.status == 'ativo',
                Embarque.status == 'ativo'
            )
            .order_by(Embarque.numero.desc())  # Último embarque primeiro
            .all()
        )
        
        # Mapeia cada lote para seu último embarque
        for item, embarque in itens_embarque:
            if item.separacao_lote_id not in embarques_por_lote:
                embarques_por_lote[item.separacao_lote_id] = embarque
    
    # ✅ NOVO: Busca contatos de agendamento para os CNPJs dos pedidos
    contatos_por_cnpj = {}
    cnpjs_pedidos = [p.cnpj_cpf for p in pedidos if p.cnpj_cpf]
    
    if cnpjs_pedidos:
        contatos_agendamento = ContatoAgendamento.query.filter(
            ContatoAgendamento.cnpj.in_(cnpjs_pedidos)
        ).all()
        
        for contato in contatos_agendamento:
            contatos_por_cnpj[contato.cnpj] = contato
    
    # Adiciona o embarque e contato de agendamento a cada pedido
    for pedido in pedidos:
        pedido.ultimo_embarque = embarques_por_lote.get(pedido.separacao_lote_id)
        pedido.contato_agendamento = contatos_por_cnpj.get(pedido.cnpj_cpf)

    # ✅ NOVO: Buscar informações de pagamento antecipado e falta de item
    info_separacao_por_lote = {}

    if lotes_ids:
        # Buscar na Separacao os flags de falta_item e falta_pagamento
        itens_separacao = Separacao.query.filter(
            Separacao.separacao_lote_id.in_(lotes_ids)
        ).all()

        for item in itens_separacao:
            lote_id = item.separacao_lote_id
            if lote_id not in info_separacao_por_lote:
                info_separacao_por_lote[lote_id] = {
                    'tem_falta_item': False,
                    'tem_falta_pagamento': False,
                    'num_pedido': item.num_pedido,
                    'obs_separacao': item.obs_separacao,  # ✅ NOVO
                    'separacao_impressa': False  # ✅ NOVO
                }

            # Marcar se tem algum item com falta
            if item.falta_item:
                info_separacao_por_lote[lote_id]['tem_falta_item'] = True

            if item.falta_pagamento:
                info_separacao_por_lote[lote_id]['tem_falta_pagamento'] = True

            # Marcar se separação foi impressa
            if item.separacao_impressa:
                info_separacao_por_lote[lote_id]['separacao_impressa'] = True

    # Buscar condição de pagamento da CarteiraPrincipal para verificar ANTECIPADO
    num_pedidos = list(set([info['num_pedido'] for info in info_separacao_por_lote.values() if info.get('num_pedido')]))

    if num_pedidos:
        itens_carteira = CarteiraPrincipal.query.filter(
            CarteiraPrincipal.num_pedido.in_(num_pedidos)
        ).all()

        # Criar dicionário de condições de pagamento por pedido
        cond_pgto_por_pedido = {}
        for item in itens_carteira:
            if item.num_pedido not in cond_pgto_por_pedido:
                cond_pgto_por_pedido[item.num_pedido] = item.cond_pgto_pedido

        # Atualizar info_separacao com informação de pagamento antecipado
        for lote_id, info in info_separacao_por_lote.items():
            num_pedido = info.get('num_pedido')
            if num_pedido:
                cond_pgto = cond_pgto_por_pedido.get(num_pedido, '')
                info['eh_antecipado'] = cond_pgto and 'ANTECIPADO' in cond_pgto.upper()

    # Adicionar flags aos pedidos
    for pedido in pedidos:
        info = info_separacao_por_lote.get(pedido.separacao_lote_id, {})
        pedido.tem_falta_item = info.get('tem_falta_item', False)
        pedido.tem_falta_pagamento = info.get('tem_falta_pagamento', False)
        pedido.eh_pagamento_antecipado = info.get('eh_antecipado', False)
        pedido.obs_separacao = info.get('obs_separacao')  # ✅ NOVO
        pedido.separacao_impressa = info.get('separacao_impressa', False)  # ✅ NOVO

    # ✅ CORRIGIDO: Funções auxiliares para URLs com preservação completa de filtros
    def sort_url(campo):
        """Gera URL para ordenação mantendo TODOS os filtros atuais"""
        from urllib.parse import urlencode
        
        # Captura TODOS os parâmetros atuais (incluindo filtros de formulário)
        params = {}
        
        # Primeiro, pega parâmetros da URL
        for key, value in request.args.items():
            params[key] = value
        
        # Depois, se foi POST com filtros, pega os dados do formulário também
        if request.method == 'POST' and filtro_form.validate():
            if filtro_form.numero_pedido.data:
                params['numero_pedido'] = filtro_form.numero_pedido.data
            if filtro_form.cnpj_cpf.data:
                params['cnpj_cpf'] = filtro_form.cnpj_cpf.data
            if filtro_form.cliente.data:
                params['cliente'] = filtro_form.cliente.data
            if filtro_form.uf.data:
                params['uf'] = filtro_form.uf.data
            if filtro_form.status.data:
                params['status'] = filtro_form.status.data
            if filtro_form.rota.data:
                params['rota'] = filtro_form.rota.data
            if filtro_form.sub_rota.data:
                params['sub_rota'] = filtro_form.sub_rota.data
            if filtro_form.expedicao_inicio.data:
                params['expedicao_inicio'] = filtro_form.expedicao_inicio.data.strftime('%Y-%m-%d')
            if filtro_form.expedicao_fim.data:
                params['expedicao_fim'] = filtro_form.expedicao_fim.data.strftime('%Y-%m-%d')
        
        # Define nova ordem: se já está ordenando por este campo, inverte; senão, usa 'asc'
        nova_ordem = 'asc'
        if params.get('sort_by') == campo and params.get('sort_order') == 'asc':
            nova_ordem = 'desc'
        
        params['sort_by'] = campo
        params['sort_order'] = nova_ordem
        
        return url_for('pedidos.lista_pedidos') + '?' + urlencode(params)
    
    def filtro_url(**kwargs):
        """Gera URL para filtros mantendo TODOS os parâmetros atuais"""
        from urllib.parse import urlencode
        
        # Captura TODOS os parâmetros atuais
        params = {}
        
        # Primeiro, pega parâmetros da URL
        for key, value in request.args.items():
            params[key] = value
        
        # Depois, se foi POST com filtros, preserva os dados do formulário
        if request.method == 'POST' and filtro_form.validate():
            if filtro_form.numero_pedido.data:
                params['numero_pedido'] = filtro_form.numero_pedido.data
            if filtro_form.cnpj_cpf.data:
                params['cnpj_cpf'] = filtro_form.cnpj_cpf.data
            if filtro_form.cliente.data:
                params['cliente'] = filtro_form.cliente.data
            if filtro_form.uf.data:
                params['uf'] = filtro_form.uf.data
            if filtro_form.status.data:
                params['status'] = filtro_form.status.data
            if filtro_form.rota.data:
                params['rota'] = filtro_form.rota.data
            if filtro_form.sub_rota.data:
                params['sub_rota'] = filtro_form.sub_rota.data
            if filtro_form.expedicao_inicio.data:
                params['expedicao_inicio'] = filtro_form.expedicao_inicio.data.strftime('%Y-%m-%d')
            if filtro_form.expedicao_fim.data:
                params['expedicao_fim'] = filtro_form.expedicao_fim.data.strftime('%Y-%m-%d')
        
        # Aplica as mudanças específicas solicitadas
        for chave, valor in kwargs.items():
            if valor is None:
                params.pop(chave, None)  # Remove parâmetro
            else:
                params[chave] = valor  # Define/atualiza parâmetro

        return url_for('pedidos.lista_pedidos') + '?' + urlencode(params)
       
    return render_template(
        'pedidos/lista_pedidos.html',
        filtro_form=filtro_form,
        cotar_form=cotar_form,
        pedidos=pedidos,
        paginacao=paginacao,
        contadores_data=contadores_data,
        contadores_status=contadores_status,
        filtro_status_ativo=filtro_status,
        filtro_data_ativo=filtro_data,
        sort_by=sort_by,
        sort_order=sort_order,
        form_preservar_status=form_preservar_status,
        form_preservar_data=form_preservar_data,
        sort_url=sort_url,
        filtro_url=filtro_url
    )

@pedidos_bp.route('/editar/<string:lote_id>', methods=['GET', 'POST'])
@login_required
def editar_pedido(lote_id):
    """
    Edita campos específicos de um pedido (agenda, protocolo, expedição)
    e sincroniza as alterações com a separação relacionada.
    Permite alterações apenas em pedidos com status "ABERTO".
    Suporta requisições AJAX para pop-up.
    """
    
    pedido = Pedido.query.filter_by(separacao_lote_id=lote_id).first_or_404()

    # ✅ NOVO: Busca primeiro item de Separacao para obter sincronizado_nf e numero_nf
    # (Como todos os itens do lote têm o mesmo numero_nf e sincronizado_nf, pega o primeiro)
    separacao_exemplo = Separacao.query.filter_by(separacao_lote_id=lote_id).first()

    # ✅ NOVO: Busca contato de agendamento para este CNPJ
    contato_agendamento = None
    if pedido.cnpj_cpf:
        contato_agendamento = ContatoAgendamento.query.filter_by(cnpj=pedido.cnpj_cpf).first()

    form = EditarPedidoForm()
    
    if form.validate_on_submit():
        try:
            # ✅ BACKUP dos valores originais para log
            valores_originais = {
                'expedicao': pedido.expedicao,
                'agendamento': pedido.agendamento,
                'protocolo': pedido.protocolo,
                'agendamento_confirmado': pedido.agendamento_confirmado
            }
            
            # ✅ ATUALIZA DIRETAMENTE NA TABELA SEPARACAO
            separacoes_atualizadas = 0
            if pedido.separacao_lote_id:
                # Atualiza todas as separações com este lote
                result = Separacao.query.filter_by(
                    separacao_lote_id=pedido.separacao_lote_id
                ).update({
                    'expedicao': form.expedicao.data,
                    'agendamento': form.agendamento.data,
                    'protocolo': form.protocolo.data,
                    'agendamento_confirmado': form.agendamento_confirmado.data
                })
                separacoes_atualizadas = result
            
            # Se não encontrou por lote, busca por chave composta
            if separacoes_atualizadas == 0:
                result = Separacao.query.filter_by(
                    num_pedido=pedido.num_pedido,
                    expedicao=valores_originais['expedicao'],
                    agendamento=valores_originais['agendamento'],
                    protocolo=valores_originais['protocolo']
                ).update({
                    'expedicao': form.expedicao.data,
                    'agendamento': form.agendamento.data,
                    'protocolo': form.protocolo.data,
                    'agendamento_confirmado': form.agendamento_confirmado.data
                })
                separacoes_atualizadas = result
            
            # ✅ COMMIT das alterações
            db.session.commit()
            
            # ✅ RESPOSTA PARA AJAX
            if request.args.get('ajax') or request.is_json:
                return jsonify({
                    'success': True,
                    'message': f"Pedido {pedido.num_pedido} atualizado com sucesso! {separacoes_atualizadas} item(ns) de separação também foram atualizados."
                })
            
            # ✅ MENSAGEM DE SUCESSO com detalhes
            flash(f"Pedido {pedido.num_pedido} atualizado com sucesso! {separacoes_atualizadas} item(ns) de separação também foram atualizados.", "success")
            
            # ✅ LOG das alterações (opcional)
            print(f"[EDIT] Pedido {pedido.num_pedido} editado:")
            print(f"  - Expedição: {valores_originais['expedicao']} → {form.expedicao.data}")
            print(f"  - Agendamento: {valores_originais['agendamento']} → {form.agendamento.data}")
            print(f"  - Protocolo: {valores_originais['protocolo']} → {form.protocolo.data}")
            print(f"  - Agendamento Confirmado: {valores_originais['agendamento_confirmado']} → {form.agendamento_confirmado.data}")
            print(f"  - Separações atualizadas: {separacoes_atualizadas}")

            # ✅ NOVA FUNCIONALIDADE: Sincronizar agendamento entre todas as tabelas
            from app.pedidos.services.sincronizacao_agendamento_service import SincronizadorAgendamentoService

            try:
                sincronizador = SincronizadorAgendamentoService(usuario=current_user.nome if hasattr(current_user, 'nome') else 'Sistema')

                # Preparar dados
                dados_agendamento = {
                    'agendamento': form.agendamento.data,
                    'protocolo': form.protocolo.data,
                    'agendamento_confirmado': form.agendamento_confirmado.data,
                    'numero_nf': form.numero_nf.data if form.numero_nf.data else None,
                    'nf_cd': form.nf_cd.data if form.nf_cd.data else False
                }

                identificador = {
                    'separacao_lote_id': pedido.separacao_lote_id,
                    'numero_nf': form.numero_nf.data if form.numero_nf.data else None
                }

                # Executar sincronização
                resultado = sincronizador.sincronizar_agendamento(
                    dados_agendamento=dados_agendamento,
                    identificador=identificador
                )

                if resultado['success']:
                    print(f"[SINCRONIZAÇÃO] Tabelas atualizadas: {', '.join(resultado['tabelas_atualizadas'])}")
                    flash(f"Sincronização completa: {', '.join(resultado['tabelas_atualizadas'])}", "info")
                else:
                    print(f"[SINCRONIZAÇÃO] Erro: {resultado['error']}")
                    flash(f"Aviso: Erro na sincronização - {resultado['error']}", "warning")

            except Exception as e:
                print(f"[SINCRONIZAÇÃO] Erro ao sincronizar: {e}")
                flash(f"Aviso: Erro na sincronização - {str(e)}", "warning")
                # Não falhar a edição se sincronização der erro

            return redirect(url_for('pedidos.lista_pedidos'))
            
        except Exception as e:
            db.session.rollback()
            if request.args.get('ajax') or request.is_json:
                return jsonify({
                    'success': False,
                    'message': f"Erro ao atualizar pedido: {str(e)}"
                })
            flash(f"Erro ao atualizar pedido: {str(e)}", "error")
            
    else:
        # ✅ VALIDAÇÃO DE ERROS PARA AJAX
        if request.method == 'POST' and (request.args.get('ajax') or request.is_json):
            return jsonify({
                'success': False,
                'errors': form.errors,
                'message': 'Erros de validação encontrados'
            })
        
        # ✅ PRÉ-PREENCHE o formulário com dados atuais
        form.expedicao.data = pedido.expedicao
        form.agendamento.data = pedido.agendamento
        form.protocolo.data = pedido.protocolo
        form.agendamento_confirmado.data = pedido.agendamento_confirmado

        # ✅ NOVO: Pré-preenche numero_nf e nf_cd de Separacao
        if separacao_exemplo:
            form.numero_nf.data = separacao_exemplo.numero_nf
            form.nf_cd.data = separacao_exemplo.nf_cd or False

    # ✅ RESPOSTA PARA AJAX (apenas o conteúdo do formulário)
    if request.args.get('ajax'):
        return render_template('pedidos/editar_pedido_ajax.html', form=form, pedido=pedido, separacao=separacao_exemplo, contato_agendamento=contato_agendamento)

    return render_template('pedidos/editar_pedido.html', form=form, pedido=pedido, separacao=separacao_exemplo, contato_agendamento=contato_agendamento)

@pedidos_bp.route('/reset_status/<string:lote_id>', methods=['POST'])
@login_required
def reset_status_pedido(lote_id):
    """
    Reset do status do pedido:
    1. Limpa NF e nf_cd
    2. Busca NF em EmbarqueItem ativo
    3. Se encontrar NF, verifica em FaturamentoProduto
    4. Define status baseado nos resultados
    """
    from app.embarques.models import Embarque, EmbarqueItem
    from app.faturamento.models import FaturamentoProduto
    
    try:
        pedido = Pedido.query.filter_by(separacao_lote_id=lote_id).first_or_404()
        
        # Guarda status anterior para log
        status_anterior = pedido.status
        nf_anterior = pedido.nf
        
        # PASSO 1: Limpar NF e nf_cd em Separacao
        if pedido.separacao_lote_id:
            Separacao.query.filter_by(
                separacao_lote_id=pedido.separacao_lote_id
            ).update({
                'numero_nf': None,
                'nf_cd': False,
                'sincronizado_nf': False
            })
        
        # PASSO 2: Buscar em EmbarqueItem
        embarque_item = None
        embarque_ativo = None
        
        if pedido.separacao_lote_id:
            # Busca EmbarqueItem com status ativo e Embarque ativo
            embarque_item = db.session.query(EmbarqueItem).join(
                Embarque, EmbarqueItem.embarque_id == Embarque.id
            ).filter(
                EmbarqueItem.separacao_lote_id == pedido.separacao_lote_id,
                EmbarqueItem.status == 'ativo',
                Embarque.status == 'ativo'
            ).first()
            
            if embarque_item:
                embarque_ativo = embarque_item.embarque
        
        # Processar resultado da busca
        if embarque_item and embarque_item.nota_fiscal:
            # CASO 1-A: Encontrou NF no EmbarqueItem - atualizar em Separacao
            if pedido.separacao_lote_id:
                Separacao.query.filter_by(
                    separacao_lote_id=pedido.separacao_lote_id
                ).update({'numero_nf': embarque_item.nota_fiscal})
            
            # PASSO 3: Verificar em FaturamentoProduto
            faturamento_existe = FaturamentoProduto.query.filter_by(
                numero_nf=embarque_item.nota_fiscal
            ).first()
            
            if faturamento_existe:
                # CASO 2-A: NF existe no faturamento
                if pedido.separacao_lote_id:
                    Separacao.query.filter_by(
                        separacao_lote_id=pedido.separacao_lote_id
                    ).update({
                        'status': 'FATURADO',
                        'sincronizado_nf': True
                    })
            else:
                # CASO 2-B: NF não existe no faturamento (mas existe no embarque)
                if pedido.separacao_lote_id:
                    Separacao.query.filter_by(
                        separacao_lote_id=pedido.separacao_lote_id
                    ).update({'status': 'FATURADO'})
                
        elif embarque_item and embarque_ativo:
            # CASO 1-B: Encontrou EmbarqueItem ativo mas sem NF
            if pedido.separacao_lote_id:
                Separacao.query.filter_by(
                    separacao_lote_id=pedido.separacao_lote_id
                ).update({'status': 'COTADO'})
            
        else:
            # CASO 1-C: Não encontrou EmbarqueItem ativo
            if pedido.separacao_lote_id:
                Separacao.query.filter_by(
                    separacao_lote_id=pedido.separacao_lote_id
                ).update({'status': 'ABERTO'})
        
        # Salvar alterações
        db.session.commit()
        
        # Log da operação
        print(f"[RESET STATUS] Pedido {pedido.num_pedido}:")
        print(f"  - Status: {status_anterior} → {pedido.status}")
        print(f"  - NF: {nf_anterior} → {pedido.nf}")
        print(f"  - Embarque ativo: {'Sim' if embarque_ativo else 'Não'}")
        
        return jsonify({
            'success': True,
            'status_anterior': status_anterior,
            'status_novo': pedido.status,
            'nf': pedido.nf,
            'message': f'Status resetado com sucesso'
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"[ERRO RESET STATUS] {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Erro ao resetar status: {str(e)}'
        }), 500

@pedidos_bp.route('/cancelar_separacao/<string:lote_id>', methods=['POST'])
@login_required
def cancelar_separacao(lote_id):
    """
    Cancela uma separação (Admin Only)
    Remove todos os itens da separação independente do status
    ✅ NOVO: Aceita motivo_exclusao e grava na CarteiraPrincipal
    """
    from flask_login import current_user

    # Verificar se é admin
    if current_user.perfil != 'administrador':
        return jsonify({
            'success': False,
            'message': 'Acesso negado. Apenas administradores podem cancelar separações.'
        }), 403

    try:
        # Buscar todos os itens da separação
        itens_separacao = Separacao.query.filter_by(separacao_lote_id=lote_id).all()

        if not itens_separacao:
            return jsonify({
                'success': False,
                'message': f'Separação {lote_id} não encontrada.'
            }), 404

        # Guardar informações para log
        num_pedido = itens_separacao[0].num_pedido if itens_separacao else 'N/A'
        status_atual = itens_separacao[0].status if itens_separacao else 'N/A'
        qtd_itens = len(itens_separacao)

        # ✅ NOVO: Obter motivo de exclusão do corpo da requisição
        data = request.get_json() or {}
        motivo_exclusao = data.get('motivo_exclusao', '').strip()

        # Validar motivo obrigatório
        if not motivo_exclusao:
            return jsonify({
                'success': False,
                'message': 'O motivo da exclusão é obrigatório.'
            }), 400

        # ✅ NOVO: Atualizar motivo_exclusao na CarteiraPrincipal
        if num_pedido and num_pedido != 'N/A':
            itens_carteira = CarteiraPrincipal.query.filter_by(num_pedido=num_pedido).all()
            for item_carteira in itens_carteira:
                item_carteira.motivo_exclusao = motivo_exclusao
                item_carteira.updated_by = current_user.nome

            if itens_carteira:
                print(f"[CANCELAR SEPARAÇÃO] Motivo gravado em {len(itens_carteira)} item(ns) da carteira")

        # Deletar todos os itens da separação
        for item in itens_separacao:
            db.session.delete(item)

        # Salvar alterações
        db.session.commit()

        # Log da operação
        print(f"[CANCELAR SEPARAÇÃO] Admin {current_user.nome} cancelou:")
        print(f"  - Lote: {lote_id}")
        print(f"  - Pedido: {num_pedido}")
        print(f"  - Status anterior: {status_atual}")
        print(f"  - Itens removidos: {qtd_itens}")
        print(f"  - Motivo: {motivo_exclusao}")

        return jsonify({
            'success': True,
            'message': f'Separação {lote_id} cancelada com sucesso. {qtd_itens} itens removidos.'
        })

    except Exception as e:
        db.session.rollback()
        print(f"[ERRO CANCELAR SEPARAÇÃO] {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Erro ao cancelar separação: {str(e)}'
        }), 500

@pedidos_bp.route('/api/info_separacao/<string:lote_id>', methods=['GET'])
@login_required
def info_separacao(lote_id):
    """
    API para buscar informações detalhadas de uma separação para exibir no modal
    Retorna todos os itens da separação com suas quantidades, valores, e status
    """
    try:
        # Buscar todos os itens da separação
        itens = Separacao.query.filter_by(separacao_lote_id=lote_id).all()

        if not itens:
            return jsonify({
                'success': False,
                'message': f'Separação {lote_id} não encontrada.'
            }), 404

        # Buscar condição de pagamento da CarteiraPrincipal
        num_pedido = itens[0].num_pedido
        carteira_item = CarteiraPrincipal.query.filter_by(num_pedido=num_pedido).first()
        cond_pgto = carteira_item.cond_pgto_pedido if carteira_item else None

        # Verificar se pedido está separado (tem separacao_impressa)
        pedido_separado = any(item.separacao_impressa for item in itens)

        # Calcular totais
        qtd_total = sum(float(item.qtd_saldo or 0) for item in itens)
        valor_total = sum(float(item.valor_saldo or 0) for item in itens)
        peso_total = sum(float(item.peso or 0) for item in itens)
        pallet_total = sum(float(item.pallet or 0) for item in itens)

        # Preparar lista de itens
        itens_list = []
        for item in itens:
            itens_list.append({
                'id': item.id,
                'cod_produto': item.cod_produto,
                'nome_produto': item.nome_produto,
                'qtd_saldo': float(item.qtd_saldo or 0),
                'valor_saldo': float(item.valor_saldo or 0),
                'peso': float(item.peso or 0),
                'pallet': float(item.pallet or 0),
                'falta_item': item.falta_item,
                'obs_separacao': item.obs_separacao
            })

        return jsonify({
            'success': True,
            'lote_id': lote_id,
            'num_pedido': num_pedido,
            'cnpj_cpf': itens[0].cnpj_cpf,
            'raz_social_red': itens[0].raz_social_red,
            'cond_pgto': cond_pgto,
            'pedido_separado': pedido_separado,
            'falta_pagamento': itens[0].falta_pagamento,
            'obs_separacao': itens[0].obs_separacao or '',  # ✅ NOVO: Observação geral do lote
            'totais': {
                'qtd': qtd_total,
                'valor': valor_total,
                'peso': peso_total,
                'pallet': pallet_total
            },
            'itens': itens_list
        })

    except Exception as e:
        print(f"[ERRO INFO SEPARAÇÃO] {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Erro ao buscar informações: {str(e)}'
        }), 500

@pedidos_bp.route('/api/toggle_falta_item/<int:item_id>', methods=['POST'])
@login_required
def toggle_falta_item(item_id):
    """
    API para alternar o status de falta_item de um item da separação
    """
    try:
        item = Separacao.query.get(item_id)

        if not item:
            return jsonify({
                'success': False,
                'message': f'Item {item_id} não encontrado.'
            }), 404

        # Alternar o status
        item.falta_item = not item.falta_item
        db.session.commit()

        return jsonify({
            'success': True,
            'item_id': item_id,
            'falta_item': item.falta_item
        })

    except Exception as e:
        db.session.rollback()
        print(f"[ERRO TOGGLE FALTA ITEM] {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Erro ao atualizar item: {str(e)}'
        }), 500

@pedidos_bp.route('/api/toggle_pagamento/<string:lote_id>', methods=['POST'])
@login_required
def toggle_pagamento(lote_id):
    """
    API para marcar/desmarcar pagamento realizado para todos os itens de uma separação
    """
    try:
        itens = Separacao.query.filter_by(separacao_lote_id=lote_id).all()

        if not itens:
            return jsonify({
                'success': False,
                'message': f'Separação {lote_id} não encontrada.'
            }), 404

        # Obter o novo valor do corpo da requisição
        data = request.get_json()
        falta_pagamento = data.get('falta_pagamento', False)

        # Atualizar todos os itens
        for item in itens:
            item.falta_pagamento = falta_pagamento

        db.session.commit()

        return jsonify({
            'success': True,
            'lote_id': lote_id,
            'falta_pagamento': falta_pagamento
        })

    except Exception as e:
        db.session.rollback()
        print(f"[ERRO TOGGLE PAGAMENTO] {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Erro ao atualizar pagamento: {str(e)}'
        }), 500

@pedidos_bp.route('/api/salvar_obs_separacao/<string:lote_id>', methods=['POST'])
@login_required
def salvar_obs_separacao(lote_id):
    """
    API para salvar observações da separação
    Atualiza todos os itens do lote com a mesma observação
    """
    try:
        data = request.get_json()
        obs_separacao = data.get('obs_separacao', '').strip()

        # Buscar todos os itens da separação
        itens = Separacao.query.filter_by(separacao_lote_id=lote_id).all()

        if not itens:
            return jsonify({
                'success': False,
                'message': f'Separação {lote_id} não encontrada.'
            }), 404

        # Atualizar observação em todos os itens do lote
        for item in itens:
            item.obs_separacao = obs_separacao if obs_separacao else None

        db.session.commit()

        return jsonify({
            'success': True,
            'lote_id': lote_id,
            'obs_separacao': obs_separacao,
            'itens_atualizados': len(itens)
        })

    except Exception as e:
        db.session.rollback()
        print(f"[ERRO SALVAR OBS SEPARAÇÃO] {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Erro ao salvar observações: {str(e)}'
        }), 500

@pedidos_bp.route('/excluir/<string:lote_id>', methods=['POST'])
@login_required
def excluir_pedido(lote_id):
    """
    Exclui um pedido e todas as separações relacionadas.
    Permite exclusão apenas de pedidos com status "ABERTO".
    Limpa automaticamente vínculos órfãos com embarques cancelados.
    """
    # Busca primeira separação do lote para validações
    primeira_separacao = Separacao.query.filter_by(separacao_lote_id=lote_id).first()
    
    if not primeira_separacao:
        flash(f"Pedido com lote {lote_id} não encontrado.", "error")
        return redirect(url_for('pedidos.lista_pedidos'))
    
    # ✅ VALIDAÇÃO: Só permite excluir pedidos com status ABERTO
    if primeira_separacao.status_calculado == 'FATURADO' or primeira_separacao.status_calculado == 'COTADO' or primeira_separacao.status_calculado == 'EMBARCADO':
        flash(f"Não é possível excluir o pedido {primeira_separacao.num_pedido}. Apenas pedidos com status 'ABERTO' podem ser excluídos. Status atual: {primeira_separacao.status_calculado}", "error")
        return redirect(url_for('pedidos.lista_pedidos'))
    
    try:
        # ✅ BACKUP de informações para log
        num_pedido = primeira_separacao.num_pedido
        lote_id_backup = primeira_separacao.separacao_lote_id
        
        # 🔧 NOVA FUNCIONALIDADE: Limpa vínculos órfãos com embarques cancelados
        vinculos_limpos = False
        if primeira_separacao.cotacao_id or primeira_separacao.numero_nf or primeira_separacao.data_embarque:
            
            # Busca se há embarque relacionado
            embarque_relacionado = None
            if lote_id:
                item_embarque = EmbarqueItem.query.filter_by(separacao_lote_id=lote_id).first()
                if item_embarque:
                    embarque_relacionado = Embarque.query.get(item_embarque.embarque_id)
            
            # Se o embarque estiver cancelado, limpa os vínculos órfãos
            if embarque_relacionado and embarque_relacionado.status == 'cancelado':
                print(f"[DEBUG] 🧹 Limpando vínculos órfãos com embarque cancelado #{embarque_relacionado.numero}")
                if lote_id:
                    Separacao.query.filter_by(
                        separacao_lote_id=lote_id
                    ).update({
                        'numero_nf': None,
                        'data_embarque': None,
                        'cotacao_id': None,
                        'nf_cd': False
                    })
                    # transportadora ignorado conforme orientação
                vinculos_limpos = True
        
        # ✅ BUSCA E EXCLUI SEPARAÇÕES RELACIONADAS
        separacoes_excluidas = 0
        
        # Busca por lote
        if lote_id:
            separacoes_relacionadas = Separacao.query.filter_by(
                separacao_lote_id=lote_id
            ).all()
            
            for separacao in separacoes_relacionadas:
                db.session.delete(separacao)
                separacoes_excluidas += 1
        
        # Se não encontrou por lote, busca por chave composta
        if separacoes_excluidas == 0:
            separacoes_relacionadas = Separacao.query.filter_by(
                num_pedido=primeira_separacao.num_pedido,
                expedicao=primeira_separacao.expedicao,
                agendamento=primeira_separacao.agendamento,
                protocolo=primeira_separacao.protocolo
            ).all()
            
            for separacao in separacoes_relacionadas:
                db.session.delete(separacao)
                separacoes_excluidas += 1
        
        # 🔧 NOVA FUNCIONALIDADE: Excluir itens de cotação relacionados
        from app.cotacao.models import CotacaoItem
        itens_cotacao_excluidos = 0
        if lote_id:
            itens_cotacao = CotacaoItem.query.filter_by(separacao_lote_id=lote_id).all()
            for item_cotacao in itens_cotacao:
                db.session.delete(item_cotacao)
                itens_cotacao_excluidos += 1
        
        if itens_cotacao_excluidos > 0:
            print(f"[DEBUG] 🗑️ Removendo {itens_cotacao_excluidos} item(ns) de cotação relacionados")
        
        # ✅ COMMIT das exclusões
        db.session.commit()
        
        # ✅ MENSAGEM DE SUCESSO
        mensagem_base = f"Pedido {num_pedido} excluído com sucesso! {separacoes_excluidas} item(ns) de separação foram removidos."
        if itens_cotacao_excluidos > 0:
            mensagem_base += f" {itens_cotacao_excluidos} item(ns) de cotação também foram removidos."
        if vinculos_limpos:
            mensagem_base += " Vínculos órfãos com embarque cancelado foram automaticamente removidos."
        
        flash(mensagem_base, "success")
        
        # ✅ LOG da exclusão
        print(f"[DELETE] Pedido {num_pedido} excluído:")
        print(f"  - Lote de separação: {lote_id_backup}")
        print(f"  - Separações removidas: {separacoes_excluidas}")
        
    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao excluir pedido: {str(e)}", "error")
    
    return redirect(url_for('pedidos.lista_pedidos'))

# Função gerar_lote_id movida para app.utils.lote_utils para padronização

@pedidos_bp.route('/api/pedido/<string:num_pedido>/endereco-carteira', methods=['GET'])
@login_required
def api_endereco_carteira(num_pedido):
    """
    API para buscar dados de endereço da CarteiraPrincipal
    """
    try:
        from app.carteira.models import CarteiraPrincipal
        
        # Buscar primeiro item da carteira para este pedido
        # (pega apenas um registro pois os dados de endereço são iguais para todo o pedido)
        item_carteira = CarteiraPrincipal.query.filter_by(
            num_pedido=num_pedido
        ).first()
        
        if not item_carteira:
            return jsonify({
                'success': False,
                'error': f'Pedido {num_pedido} não encontrado na carteira'
            }), 404
        
        # Preparar dados do endereço
        dados = {
            # Dados do cliente
            'raz_social': item_carteira.raz_social,
            'raz_social_red': item_carteira.raz_social_red,
            'cnpj_cpf': item_carteira.cnpj_cpf,
            'municipio': item_carteira.municipio,
            'estado': item_carteira.estado,
            'incoterm': item_carteira.incoterm,
            
            # Dados do endereço de entrega
            'empresa_endereco_ent': item_carteira.empresa_endereco_ent,
            'cnpj_endereco_ent': item_carteira.cnpj_endereco_ent,
            'cep_endereco_ent': item_carteira.cep_endereco_ent,
            'nome_cidade': item_carteira.nome_cidade,
            'cod_uf': item_carteira.cod_uf,
            'bairro_endereco_ent': item_carteira.bairro_endereco_ent,
            'rua_endereco_ent': item_carteira.rua_endereco_ent,
            'endereco_ent': item_carteira.endereco_ent,
            'telefone_endereco_ent': item_carteira.telefone_endereco_ent,
            
            # Observações
            'observ_ped_1': item_carteira.observ_ped_1,
            
            # Dados adicionais úteis
            'pedido_cliente': item_carteira.pedido_cliente,
            'vendedor': item_carteira.vendedor,
            'equipe_vendas': item_carteira.equipe_vendas,
            'cliente_nec_agendamento': item_carteira.cliente_nec_agendamento
        }
        
        return jsonify({
            'success': True,
            'dados': dados
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@pedidos_bp.route('/api/pedido/<string:num_pedido>/endereco-receita', methods=['GET'])
@login_required
def api_endereco_receita(num_pedido):
    """
    API fallback para buscar dados de endereço via ReceitaWS quando não encontrar na CarteiraPrincipal
    Também retorna o separacao_lote_id para permitir atualização da cidade
    """
    import requests
    import re

    try:
        from app.separacao.models import Separacao

        # Buscar CNPJ e separacao_lote_id da primeira Separacao deste pedido
        separacao = Separacao.query.filter_by(num_pedido=num_pedido).first()

        if not separacao or not separacao.cnpj_cpf:
            return jsonify({
                'success': False,
                'error': f'Pedido {num_pedido} não encontrado ou sem CNPJ'
            }), 404

        # Limpar CNPJ (apenas números)
        cnpj_limpo = re.sub(r'\D', '', separacao.cnpj_cpf)

        if len(cnpj_limpo) != 14:
            return jsonify({
                'success': False,
                'error': f'CNPJ inválido: {separacao.cnpj_cpf}'
            }), 400

        # Buscar dados na ReceitaWS
        url = f'https://www.receitaws.com.br/v1/cnpj/{cnpj_limpo}'
        response = requests.get(url, timeout=10)

        # Tratamento específico para erro 429 (Too Many Requests)
        if response.status_code == 429:
            return jsonify({
                'success': False,
                'error': 'Limite de consultas à ReceitaWS atingido. Tente novamente após 60 segundos.',
                'error_code': 429
            }), 429

        if response.status_code != 200:
            return jsonify({
                'success': False,
                'error': f'Erro ao consultar ReceitaWS: Status {response.status_code}'
            }), response.status_code

        dados_receita = response.json()

        # Verificar se retornou erro
        if dados_receita.get('status') == 'ERROR':
            return jsonify({
                'success': False,
                'error': dados_receita.get('message', 'Erro desconhecido na ReceitaWS')
            }), 400

        # Preparar dados no formato esperado pelo modal
        dados = {
            # Dados do cliente
            'raz_social': dados_receita.get('nome', '-'),
            'raz_social_red': dados_receita.get('fantasia', dados_receita.get('nome', '-')),
            'cnpj_cpf': dados_receita.get('cnpj', separacao.cnpj_cpf),
            'municipio': dados_receita.get('municipio', '-'),
            'estado': dados_receita.get('uf', '-'),
            'incoterm': separacao.roteirizacao or '-',

            # Dados do endereço de entrega (mesmo endereço do CNPJ)
            'empresa_endereco_ent': dados_receita.get('fantasia', dados_receita.get('nome', '-')),
            'cnpj_endereco_ent': dados_receita.get('cnpj', separacao.cnpj_cpf),
            'cep_endereco_ent': dados_receita.get('cep', '-').replace('.', ''),
            'nome_cidade': dados_receita.get('municipio', '-'),
            'cod_uf': dados_receita.get('uf', '-'),
            'bairro_endereco_ent': dados_receita.get('bairro', '-'),
            'rua_endereco_ent': dados_receita.get('logradouro', '-'),
            'endereco_ent': dados_receita.get('numero', '-'),
            'telefone_endereco_ent': dados_receita.get('telefone', '-'),

            # Observações
            'observ_ped_1': separacao.observ_ped_1 or 'Sem observações',

            # Dados adicionais
            'pedido_cliente': separacao.pedido_cliente or '-',
            'vendedor': '-',
            'equipe_vendas': '-',
            'cliente_nec_agendamento': False,

            # IMPORTANTE: Incluir separacao_lote_id para permitir atualização
            'separacao_lote_id': separacao.separacao_lote_id
        }

        return jsonify({
            'success': True,
            'dados': dados,
            'fonte': 'receita'  # Indica que veio da ReceitaWS
        })

    except requests.Timeout:
        return jsonify({
            'success': False,
            'error': 'Timeout ao consultar ReceitaWS. Tente novamente.'
        }), 504
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@pedidos_bp.route('/api/separacao/<string:lote_id>/atualizar-cidade', methods=['POST'])
@login_required
def api_atualizar_cidade_separacao(lote_id):
    """
    API para atualizar a cidade de TODAS as Separacoes de um lote
    """
    try:
        from app.separacao.models import Separacao

        dados = request.get_json()
        nova_cidade = dados.get('cidade')

        if not nova_cidade:
            return jsonify({
                'success': False,
                'error': 'Cidade não informada'
            }), 400

        # Buscar TODAS as separações deste lote
        separacoes = Separacao.query.filter_by(separacao_lote_id=lote_id).all()

        if not separacoes:
            return jsonify({
                'success': False,
                'error': f'Nenhuma separação encontrada para o lote {lote_id}'
            }), 404

        # Atualizar cidade em TODAS
        for sep in separacoes:
            sep.nome_cidade = nova_cidade

        db.session.commit()

        return jsonify({
            'success': True,
            'atualizados': len(separacoes),
            'message': f'Cidade atualizada em {len(separacoes)} registro(s)'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@pedidos_bp.route('/gerar_resumo', methods=['GET'])
def gerar_resumo():
    print("[DEBUG] 🔄 Iniciando geração de resumo com correção de separações...")
    
    # 1) Agrupar separacao
    resultados = (
        db.session.query(
            Separacao.num_pedido,
            Separacao.expedicao,
            Separacao.agendamento,
            Separacao.protocolo,
            func.min(Separacao.data_pedido).label('data_pedido'),
            func.min(Separacao.cnpj_cpf).label('cnpj_cpf'),
            func.min(Separacao.raz_social_red).label('raz_social_red'),
            func.min(Separacao.nome_cidade).label('nome_cidade'),
            func.min(Separacao.cod_uf).label('cod_uf'),
            func.sum(Separacao.valor_saldo).label('valor_saldo_total'),
            func.sum(Separacao.pallet).label('pallet_total'),
            func.sum(Separacao.peso).label('peso_total'),
            func.min(Separacao.rota).label('rota'),
            func.min(Separacao.sub_rota).label('sub_rota'),
            func.min(Separacao.observ_ped_1).label('observ_ped_1'),
            func.min(Separacao.roteirizacao).label('roteirizacao'),
        )
        .group_by(
            Separacao.num_pedido,
            Separacao.expedicao,
            Separacao.agendamento,
            Separacao.protocolo
        )
        .all()
    )

    # ✅ NOVO: Corrige separações órfãs ANTES de criar/atualizar pedidos
    separacoes_sem_lote = Separacao.query.filter(Separacao.separacao_lote_id.is_(None)).all()
    if separacoes_sem_lote:
        print(f"[DEBUG] 📦 Corrigindo {len(separacoes_sem_lote)} separações órfãs...")
        
        # Agrupa separações por pedido para gerar lotes únicos
        from collections import defaultdict
        separacoes_por_pedido = defaultdict(list)
        for sep in separacoes_sem_lote:
            if sep.num_pedido:
                chave_pedido = f"{sep.num_pedido}_{sep.expedicao}_{sep.agendamento}_{sep.protocolo}"
                separacoes_por_pedido[chave_pedido].append(sep)
        
        # Gera lote único para cada grupo de pedido
        for chave_pedido, separacoes in separacoes_por_pedido.items():
            novo_lote_id = gerar_lote_id()
            print(f"[DEBUG]   ✅ Criando lote {novo_lote_id} para {len(separacoes)} itens do pedido {separacoes[0].num_pedido}")
            
            for sep in separacoes:
                sep.separacao_lote_id = novo_lote_id

    # 2) Para cada group, insere/atualiza em Pedido
    for row in resultados:
        pedido_existente = Pedido.query.filter_by(
            num_pedido=row.num_pedido,
            expedicao=row.expedicao,
            agendamento=row.agendamento,
            protocolo=row.protocolo
        ).first()
        
        # ✅ NOVO: Busca o lote de separação para este pedido
        separacao_exemplo = Separacao.query.filter_by(
            num_pedido=row.num_pedido,
            expedicao=row.expedicao,
            agendamento=row.agendamento,
            protocolo=row.protocolo
        ).first()
        
        lote_id = separacao_exemplo.separacao_lote_id if separacao_exemplo else None
        
        # IMPORTANTE: Após migração, Pedido é uma VIEW
        # Não podemos criar/atualizar registros em Pedido
        # A VIEW agrega automaticamente as Separacoes
        
        # O que podemos fazer é atualizar campos nas Separacoes se necessário
        if lote_id and not pedido_existente:
            # Se não existe pedido na VIEW, significa que as Separacoes precisam de ajustes
            separacoes_do_grupo = Separacao.query.filter_by(
                num_pedido=row.num_pedido,
                expedicao=row.expedicao,
                agendamento=row.agendamento,
                protocolo=row.protocolo
            ).all()
            
            # Normalizar dados nas Separacoes
            for sep in separacoes_do_grupo:
                # Aplicar normalização diretamente nas Separacoes
                if hasattr(sep, 'cidade_normalizada') and not sep.cidade_normalizada:
                    # Normalizar cidade/UF se disponível
                    try:
                        from app.utils.localizacao import LocalizacaoService
                        sep.cidade_normalizada = LocalizacaoService.normalizar_cidade(sep.nome_cidade)
                        sep.uf_normalizada = LocalizacaoService.normalizar_uf(sep.cod_uf)
                        sep.codigo_ibge = LocalizacaoService.obter_codigo_ibge(sep.nome_cidade, sep.cod_uf)
                    except ImportError:
                        # Se o serviço não existir, apenas pular a normalização
                        pass

    db.session.commit()
    
    # ✅ NOVO: Verifica resultado da correção
    separacoes_orfas_restantes = Separacao.query.filter(Separacao.separacao_lote_id.is_(None)).count()
    pedidos_com_separacao = Pedido.query.filter(Pedido.separacao_lote_id.isnot(None)).count()
    
    flash(f"Resumo gerado/atualizado com sucesso! {pedidos_com_separacao} pedidos com separação linkada.", "success")
    
    if separacoes_orfas_restantes == 0:
        flash("✅ Todas as separações foram corretamente linkadas aos pedidos!", "success")
    else:
        flash(f"⚠️ Ainda restam {separacoes_orfas_restantes} separações órfãs para análise.", "warning")

    return redirect(url_for('pedidos.lista_pedidos'))  # hipotético: rotas do blueprint de pedidos

@pedidos_bp.route('/atualizar_status', methods=['GET', 'POST'])
@login_required
def atualizar_status():
    """
    Atualiza todos os status dos pedidos baseado na lógica status_calculado
    """
    try:
        pedidos = Pedido.query.all()
        atualizados = 0
        
        for pedido in pedidos:
            status_correto = pedido.status_calculado
            if pedido.status != status_correto:
                # Atualizar status em Separacao
                if pedido.separacao_lote_id:
                    Separacao.query.filter_by(
                        separacao_lote_id=pedido.separacao_lote_id
                    ).update({'status': status_correto})
                    atualizados += 1
        
        if atualizados > 0:
            db.session.commit()
            flash(f"✅ {atualizados} status de pedidos atualizados com sucesso!", "success")
        else:
            flash("✅ Todos os status já estão corretos!", "info")
            
    except Exception as e:
        db.session.rollback()
        flash(f"❌ Erro ao atualizar status: {str(e)}", "error")
    
    return redirect(url_for('pedidos.lista_pedidos'))

@pedidos_bp.route('/cotacao_manual', methods=['GET', 'POST'])
@login_required
def cotacao_manual():
    """
    Processa a cotação manual dos pedidos selecionados
    """
    if request.method == 'POST':
        # Tenta primeiro por separacao_lote_ids (novo padrão)
        lista_ids_str = request.form.getlist("separacao_lote_ids")
        
        if not lista_ids_str:
            lista_ids_str = request.form.getlist("pedido_ids")
        
        if not lista_ids_str:
            flash("Nenhum pedido selecionado!", "warning")
            return redirect(url_for("pedidos.lista_pedidos"))

        # Não converter para int se forem lotes (strings)
        if lista_ids_str and lista_ids_str[0].startswith('LOTE'):
            lista_ids = lista_ids_str
        else:
            lista_ids = [int(x) for x in lista_ids_str if x.isdigit()]

        # Armazena no session para usar nas rotas subsequentes
        session["cotacao_manual_pedidos"] = lista_ids

        # Se lista_ids contém strings de lote (LOTE_xxx), usar diretamente
        if lista_ids and isinstance(lista_ids[0], str) and lista_ids[0].startswith('LOTE'):
            pedidos = Pedido.query.filter(Pedido.separacao_lote_id.in_(lista_ids)).all()
        else:
            # Se são IDs numéricos, converter para string e buscar por num_pedido
            pedidos = Pedido.query.filter(Pedido.num_pedido.in_([str(id) for id in lista_ids])).all()
        
        if not pedidos:
            flash("Nenhum pedido encontrado!", "warning")
            return redirect(url_for("pedidos.lista_pedidos"))

        # ✅ CORRIGIDO: Não usa LocalizacaoService.normalizar_dados_pedido pois Pedido é VIEW
        # A normalização já deve estar presente na VIEW ou será feita em memória se necessário
        # NOTA: Pedido é uma VIEW, dados de normalização já devem vir da Separacao
        # Se precisar normalizar, fazer diretamente na Separacao usando separacao_lote_id

        # Carrega transportadoras e veículos para os formulários
        transportadoras = Transportadora.query.order_by(Transportadora.razao_social).all()
        veiculos = Veiculo.query.order_by(Veiculo.nome).all()

        return render_template(
            'pedidos/cotacao_manual.html',
            pedidos=pedidos,
            transportadoras=transportadoras,
            veiculos=veiculos
        )
    
    # Se GET, redireciona para lista de pedidos
    return redirect(url_for('pedidos.lista_pedidos'))

@pedidos_bp.route('/processar_cotacao_manual', methods=['POST'])
@login_required
def processar_cotacao_manual():
    """
    Processa os dados da cotação manual e cria o embarque
    """
    try:
        # Recupera pedidos da sessão
        lista_ids = session.get("cotacao_manual_pedidos", [])
        if not lista_ids:
            flash("Sessão expirada. Selecione os pedidos novamente.", "warning")
            return redirect(url_for("pedidos.lista_pedidos"))

        # Dados do formulário
        transportadora_id = request.form.get('transportadora_id')
        modalidade = request.form.get('modalidade')
        valor_frete = request.form.get('valor_frete')

        # Validações básicas
        if not transportadora_id or not modalidade or not valor_frete:
            flash("Todos os campos são obrigatórios!", "error")
            return redirect(url_for("pedidos.cotacao_manual"))

        try:
            transportadora_id = int(transportadora_id)
            valor_frete = float(valor_frete.replace(',', '.'))
        except ValueError:
            flash("Valores inválidos fornecidos!", "error")
            return redirect(url_for("pedidos.cotacao_manual"))

        # Carrega pedidos e transportadora
        # Converter IDs para lotes se necessário
        from app.separacao.models import Separacao
        # Se lista_ids contém strings de lote, usar diretamente
        if lista_ids and isinstance(lista_ids[0], str) and lista_ids[0].startswith('LOTE'):
            pedidos = Pedido.query.filter(Pedido.separacao_lote_id.in_(lista_ids)).all()
        else:
            # Se são IDs numéricos, precisa converter para num_pedido ou buscar lotes
            pedidos = Pedido.query.filter(Pedido.num_pedido.in_([str(id) for id in lista_ids])).all()
        transportadora = Transportadora.query.get(transportadora_id)

        if not pedidos or not transportadora:
            flash("Dados não encontrados!", "error")
            return redirect(url_for("pedidos.cotacao_manual"))

        # ✅ CORRIGIDO: Não usa LocalizacaoService.normalizar_dados_pedido pois Pedido é VIEW
        # A normalização já deve estar presente na VIEW ou será feita em memória se necessário

        # Importa as classes necessárias
        from app.embarques.models import Embarque, EmbarqueItem
        from app.cotacao.models import Cotacao, CotacaoItem
        from app.utils.embarque_numero import obter_proximo_numero_embarque
        from datetime import datetime

        # Calcula totais dos pedidos
        peso_total = sum(p.peso_total or 0 for p in pedidos)
        valor_total = sum(p.valor_saldo_total or 0 for p in pedidos)
        pallet_total = sum(p.pallet_total or 0 for p in pedidos)

        # Cria a cotação manual
        from app.utils.tabela_frete_manager import TabelaFreteManager
        
        # Prepara dados da cotação manual
        dados_cotacao = TabelaFreteManager.preparar_cotacao_manual(valor_frete, modalidade, icms_incluso=True)
        
        cotacao = Cotacao(
            usuario_id=1,  # Ajustar conforme seu sistema de usuários
            transportadora_id=transportadora_id,
            status='Fechado',
            data_criacao=datetime.now(),
            data_fechamento=datetime.now(),
            tipo_carga='DIRETA',  # ✅ CORRIGIDO: DIRETA ao invés de MANUAL
            valor_total=valor_total,
            peso_total=peso_total,
            **dados_cotacao  # Desempacota todos os campos da tabela
        )
        db.session.add(cotacao)
        db.session.flush()  # Para obter o ID da cotação

        # Cria itens da cotação
        for pedido in pedidos:
            cotacao_item = CotacaoItem(
                cotacao_id=cotacao.id,
                separacao_lote_id=pedido.separacao_lote_id,  
                pedido_id_old=pedido.id if hasattr(pedido, 'id') else 0,  # Adiciona pedido_id_old com fallback
                cnpj_cliente=pedido.cnpj_cpf,
                cliente=pedido.raz_social_red,
                peso=pedido.peso_total or 0,
                valor=pedido.valor_saldo_total or 0,
                **dados_cotacao  # Reutiliza os mesmos dados da cotação
            )
            db.session.add(cotacao_item)

        # Cria o embarque
        embarque = Embarque(
            numero=obter_proximo_numero_embarque(),
            transportadora_id=transportadora_id,
            status='ativo',
            tipo_cotacao='Manual',
            valor_total=valor_total,
            pallet_total=pallet_total,
            peso_total=peso_total,
            tipo_carga='DIRETA',  # ✅ CORRIGIDO: DIRETA para seguir lógica de carga direta
            cotacao_id=cotacao.id,
            transportadora_optante=False,
            criado_por='Sistema'
        )
        # Atribui campos da tabela usando TabelaFreteManager
        TabelaFreteManager.atribuir_campos_objeto(embarque, dados_cotacao)
        embarque.icms_destino = 0
        db.session.add(embarque)
        db.session.flush()  # Para obter o ID do embarque

        # Cria itens do embarque
        for pedido in pedidos:
            # ✅ NOVO: Busca cidade correta usando LocalizacaoService (igual ao "Cotar Frete")
            cidade_correta = LocalizacaoService.buscar_cidade_unificada(pedido=pedido)
            
            # ✅ NOVO: Usa nome correto da cidade ou fallback para o nome normalizado
            nome_cidade_correto = cidade_correta.nome if cidade_correta else pedido.cidade_normalizada or pedido.nome_cidade
            uf_correto = cidade_correta.uf if cidade_correta else pedido.uf_normalizada or pedido.cod_uf
            
            # Prepara dados vazios para EmbarqueItem (DIRETA não usa tabela nos itens)
            dados_vazio = TabelaFreteManager.preparar_cotacao_vazia()
            
            embarque_item = EmbarqueItem(
                embarque_id=embarque.id,
                separacao_lote_id=pedido.separacao_lote_id,
                cnpj_cliente=pedido.cnpj_cpf,
                cliente=pedido.raz_social_red,
                pedido=pedido.num_pedido,
                protocolo_agendamento=str(pedido.protocolo) if pedido.protocolo else '',
                data_agenda=pedido.agendamento.strftime('%d/%m/%Y') if pedido.agendamento else '',
                peso=pedido.peso_total or 0,
                valor=pedido.valor_saldo_total or 0,
                pallets=pedido.pallet_total,  # ✅ Adiciona pallets reais do pedido
                uf_destino=uf_correto,
                cidade_destino=nome_cidade_correto,
                cotacao_id=cotacao.id,
                volumes=None  # Deixa volumes em branco para preenchimento manual
                # ✅ CORRIGIDO: Cotação manual é DIRETA - dados da tabela ficam apenas no Embarque
                # EmbarqueItem não precisa dos campos de tabela
            )
            # Atribui campos vazios usando TabelaFreteManager
            TabelaFreteManager.atribuir_campos_objeto(embarque_item, dados_vazio)
            embarque_item.icms_destino = None
            db.session.add(embarque_item)

        # Commit antes de atualizar separações (Embarque e itens já criados)
        db.session.commit()

        # ✅ CORRIGIDO: Atualiza todos os pedidos após criar os itens
        # Usa método Separacao.atualizar_cotacao() que já faz commit internamente
        for pedido in pedidos:
            if pedido.separacao_lote_id:
                # Usa método que dispara event listeners para atualizar status automaticamente
                Separacao.atualizar_cotacao(
                    separacao_lote_id=pedido.separacao_lote_id,
                    cotacao_id=cotacao.id,
                    nf_cd=False
                )
                # Status será calculado automaticamente como COTADO pelo listener

        # Limpa a sessão
        if "cotacao_manual_pedidos" in session:
            del session["cotacao_manual_pedidos"]

        flash(f"Cotação manual criada com sucesso! Embarque #{embarque.numero} gerado.", "success")
        return redirect(url_for('embarques.visualizar_embarque', id=embarque.id))

    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao processar cotação manual: {str(e)}", "error")
        return redirect(url_for("pedidos.cotacao_manual"))

@pedidos_bp.route('/embarque_fob', methods=['POST'])
@login_required
def embarque_fob():
    """
    Processa a criação de embarque FOB
    Valida se todos os pedidos selecionados têm rota "FOB"
    """
    try:
        # Tenta primeiro por separacao_lote_ids (novo padrão)
        lista_ids_str = request.form.getlist("separacao_lote_ids")
        
        # Fallback para pedido_ids (retrocompatibilidade)
        if not lista_ids_str:
            lista_ids_str = request.form.getlist("pedido_ids")
        
        if not lista_ids_str:
            flash("Nenhum pedido selecionado!", "warning")
            return redirect(url_for("pedidos.lista_pedidos"))

        # Não converter para int se forem lotes (strings)
        if lista_ids_str and lista_ids_str[0].startswith('LOTE'):
            lista_ids = lista_ids_str
        else:
            lista_ids = [int(x) for x in lista_ids_str if x.isdigit()]

        # Carrega os pedidos do banco
        from app.separacao.models import Separacao
        
        # Se lista_ids contém strings de lote (LOTE_xxx), usar diretamente
        if lista_ids and isinstance(lista_ids[0], str) and lista_ids[0].startswith('LOTE'):
            pedidos = Pedido.query.filter(Pedido.separacao_lote_id.in_(lista_ids)).all()
        else:
            # Se são IDs numéricos, converter para string e buscar por num_pedido
            pedidos = Pedido.query.filter(Pedido.num_pedido.in_([str(id) for id in lista_ids])).all()
        
        if not pedidos:
            flash("Nenhum pedido encontrado!", "warning")
            return redirect(url_for("pedidos.lista_pedidos"))

        # ✅ VALIDAÇÃO: Verifica se todos os pedidos são FOB
        pedidos_nao_fob = []
        for pedido in pedidos:
            if not pedido.rota or pedido.rota.upper().strip() != 'FOB':
                pedidos_nao_fob.append(f"Pedido {pedido.num_pedido} (rota: {pedido.rota or 'N/A'})")

        if pedidos_nao_fob:
            flash(f"Os seguintes pedidos não são FOB: {', '.join(pedidos_nao_fob)}. Apenas pedidos com rota 'FOB' podem usar este embarque.", "error")
            return redirect(url_for("pedidos.lista_pedidos"))

        # ✅ TODOS SÃO FOB: Procede com criação do embarque

        # ✅ CORRIGIDO: Não usa LocalizacaoService.normalizar_dados_pedido pois Pedido é VIEW
        # A normalização já deve estar presente na VIEW ou será feita em memória se necessário

        # Busca ou cria a transportadora "FOB - COLETA"
        from app.transportadoras.models import Transportadora
        transportadora_fob = Transportadora.query.filter_by(razao_social="FOB - COLETA").first()
        
        if not transportadora_fob:
            # Cria a transportadora FOB - COLETA se não existir
            transportadora_fob = Transportadora(
                razao_social="FOB - COLETA",
                cnpj="00000000000000",  # CNPJ fictício
                cidade="FOB",
                uf="SP",
                optante=False,
                condicao_pgto="FOB"
            )
            db.session.add(transportadora_fob)
            db.session.flush()  # Para obter o ID

        # Importa as classes necessárias

        # Calcula totais dos pedidos
        peso_total = sum(p.peso_total or 0 for p in pedidos)
        valor_total = sum(p.valor_saldo_total or 0 for p in pedidos)
        pallet_total = sum(p.pallet_total or 0 for p in pedidos)

        # ✅ CRIA O EMBARQUE FOB (sem cotação, sem tabela)
        embarque = Embarque(
            numero=obter_proximo_numero_embarque(),
            transportadora_id=transportadora_fob.id,
            status='ativo',
            tipo_cotacao='FOB',  # Tipo especial para FOB
            valor_total=valor_total,
            pallet_total=pallet_total,
            peso_total=peso_total,
            tipo_carga='FOB',  # Tipo especial para FOB
            cotacao_id=None,  # ✅ SEM COTAÇÃO
            modalidade=None,  # ✅ SEM MODALIDADE
            # ✅ SEM DADOS DE TABELA (todos None/0)
            tabela_nome_tabela=None,
            tabela_frete_minimo_valor=None,
            tabela_valor_kg=None,
            tabela_percentual_valor=None,
            tabela_frete_minimo_peso=None,
            tabela_icms=None,
            tabela_percentual_gris=None,
            tabela_pedagio_por_100kg=None,
            tabela_valor_tas=None,
            tabela_percentual_adv=None,
            tabela_percentual_rca=None,
            tabela_valor_despacho=None,
            tabela_valor_cte=None,
            tabela_icms_incluso=None,
            icms_destino=None,
            transportadora_optante=None,
            criado_por='Sistema'
        )
        db.session.add(embarque)
        db.session.flush()  # Para obter o ID do embarque

        # Cria itens do embarque
        for pedido in pedidos:
            # ✅ Busca cidade correta usando LocalizacaoService (igual ao "Cotar Frete")
            cidade_correta = LocalizacaoService.buscar_cidade_unificada(pedido=pedido)
            
            # ✅ Usa nome correto da cidade ou fallback para o nome normalizado
            nome_cidade_correto = cidade_correta.nome if cidade_correta else pedido.cidade_normalizada or pedido.nome_cidade
            uf_correto = cidade_correta.uf if cidade_correta else pedido.uf_normalizada or pedido.cod_uf
            
            # Prepara dados vazios para EmbarqueItem (FOB não usa tabela)
            dados_vazio = TabelaFreteManager.preparar_cotacao_vazia()
            
            embarque_item = EmbarqueItem(
                embarque_id=embarque.id,
                separacao_lote_id=pedido.separacao_lote_id,
                cnpj_cliente=pedido.cnpj_cpf,
                cliente=pedido.raz_social_red,
                pedido=pedido.num_pedido,
                nota_fiscal=pedido.nf,
                protocolo_agendamento=str(pedido.protocolo) if pedido.protocolo else '',
                data_agenda=pedido.agendamento.strftime('%d/%m/%Y') if pedido.agendamento else '',
                peso=pedido.peso_total or 0,
                valor=pedido.valor_saldo_total or 0,
                pallets=pedido.pallet_total,  # ✅ Adiciona pallets reais do pedido
                uf_destino=uf_correto,
                cidade_destino=nome_cidade_correto,
                cotacao_id=None,  # SEM COTAÇÃO para FOB
                volumes=None  # Deixa volumes em branco para preenchimento manual
                # ✅ SEM DADOS DE TABELA (FOB não usa tabelas)
            )
            # Atribui campos vazios usando TabelaFreteManager
            TabelaFreteManager.atribuir_campos_objeto(embarque_item, dados_vazio)
            embarque_item.icms_destino = None
            db.session.add(embarque_item)

        # ✅ CORRIGIDO: Atualiza todos os pedidos após criar os itens FOB
        cotacao_fob = None  # Inicializar variável fora do if
        for pedido in pedidos:
            # FOB não tem cotação, mas precisa de cotacao_id para ficar como COTADO
            # Vamos criar uma cotação fictícia para FOB
            if not pedido.cotacao_id:
                # Cria uma cotação FOB fictícia se não existir
                from app.cotacao.models import Cotacao
                # Prepara dados para cotação FOB
                dados_fob = TabelaFreteManager.preparar_cotacao_fob()
                
                cotacao_fob = Cotacao(
                    usuario_id=1,  # Sistema
                    transportadora_id=transportadora_fob.id,
                    status='Fechado',
                    data_criacao=datetime.now(),
                    data_fechamento=datetime.now(),
                    tipo_carga='FOB',
                    valor_total=sum(p.valor_saldo_total or 0 for p in pedidos),
                    peso_total=sum(p.peso_total or 0 for p in pedidos),
                    **dados_fob  # Desempacota todos os campos FOB
                )
                db.session.add(cotacao_fob)
                db.session.flush()
                
                # Atualiza o embarque com a cotação FOB
                embarque.cotacao_id = cotacao_fob.id
            
        # Commit antes de atualizar separações (Embarque e itens já criados)
        db.session.commit()

        # ✅ NOVO: Atualizar pedidos com cotação FOB
        # Usa método Separacao.atualizar_cotacao() que já faz commit internamente
        for pedido in pedidos:
            if pedido.separacao_lote_id:
                cotacao_id_final = embarque.cotacao_id or (cotacao_fob.id if cotacao_fob else None)

                if cotacao_id_final:
                    # Usa método que dispara event listeners para atualizar status automaticamente
                    Separacao.atualizar_cotacao(
                        separacao_lote_id=pedido.separacao_lote_id,
                        cotacao_id=cotacao_id_final,
                        nf_cd=False
                    )
                    # Status será calculado automaticamente como COTADO pelo listener

        flash(f"Embarque FOB #{embarque.numero} criado com sucesso! Transportadora: FOB - COLETA", "success")
        return redirect(url_for('embarques.visualizar_embarque', id=embarque.id))

    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao criar embarque FOB: {str(e)}", "error")
        return redirect(url_for("pedidos.lista_pedidos"))

@pedidos_bp.route('/detalhes/<string:lote_id>')
@login_required
def detalhes_pedido(lote_id):
    """
    Visualiza detalhes completos de um pedido usando separacao_lote_id
    """
    pedido = Pedido.query.filter_by(separacao_lote_id=lote_id).first_or_404()
    
    # Buscar embarque relacionado se existir
    embarque = None
    if pedido.separacao_lote_id:
        from app.embarques.models import EmbarqueItem, Embarque
        item_embarque = (
            db.session.query(EmbarqueItem, Embarque)
            .join(Embarque, EmbarqueItem.embarque_id == Embarque.id)
            .filter(
                EmbarqueItem.separacao_lote_id == pedido.separacao_lote_id,
                EmbarqueItem.status == 'ativo',
                Embarque.status == 'ativo'
            )
            .order_by(Embarque.numero.desc())
            .first()
        )
        
        if item_embarque:
            embarque = item_embarque[1]
    
    # Buscar contato de agendamento
    contato_agendamento = None
    if pedido.cnpj_cpf:
        contato_agendamento = ContatoAgendamento.query.filter_by(cnpj=pedido.cnpj_cpf).first()
    
    return render_template(
        'pedidos/detalhes_pedido.html',
        pedido=pedido,
        embarque=embarque,
        contato_agendamento=contato_agendamento
    )


@pedidos_bp.route('/sincronizar-items-faturamento/<lote_id>', methods=['POST'])
@login_required
def sincronizar_items_faturamento(lote_id):
    """
    Sincroniza items de Separacao com FaturamentoProduto

    Busca dados reais de qtd, valor, peso e pallets do faturamento
    e atualiza a Separacao com sincronizado_nf=True
    """
    try:
        from app.pedidos.services.sincronizar_items_service import SincronizadorItemsService

        # Executar sincronização
        service = SincronizadorItemsService()
        resultado = service.sincronizar_items_faturamento(
            separacao_lote_id=lote_id,
            usuario=current_user.nome if hasattr(current_user, 'nome') else 'Sistema'
        )

        return jsonify(resultado)

    except Exception as e:
        import logging
        logging.error(f"Erro ao sincronizar items do lote {lote_id}: {e}")
        return jsonify({
            'success': False,
            'separacao_lote_id': lote_id,
            'erro': str(e)
        }), 500

@pedidos_bp.route('/validar_nf/<string:numero_nf>', methods=['GET'])
@login_required
def validar_nf(numero_nf):
    """
    Valida se NF existe em FaturamentoProduto e retorna status

    Query params:
    - lote_id: ID do lote (opcional, para log)

    Response:
    {
        "success": true,
        "existe": true/false,
        "status": "Lançado"|"Cancelado"|"Provisório"|null,
        "sincronizado_nf": true/false
    }
    """
    from app.faturamento.models import FaturamentoProduto

    try:
        lote_id = request.args.get('lote_id', 'N/A')

        # Buscar NF em FaturamentoProduto
        faturamento = FaturamentoProduto.query.filter_by(
            numero_nf=numero_nf
        ).first()

        if faturamento:
            # NF encontrada
            status = faturamento.status_nf or 'Lançado'
            sincronizado = (status != 'Cancelado')

            print(f"[VALIDAR NF] Lote: {lote_id} | NF: {numero_nf} | Status: {status} | Sincronizado: {sincronizado}")

            return jsonify({
                'success': True,
                'existe': True,
                'status': status,
                'sincronizado_nf': sincronizado,
                'message': f'NF encontrada com status: {status}'
            })
        else:
            # NF não encontrada
            print(f"[VALIDAR NF] Lote: {lote_id} | NF: {numero_nf} | Não encontrada")

            return jsonify({
                'success': True,
                'existe': False,
                'status': None,
                'sincronizado_nf': False,
                'message': 'NF não encontrada no faturamento'
            })

    except Exception as e:
        print(f"[ERRO VALIDAR NF] {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Erro ao validar NF: {str(e)}'
        }), 500


@pedidos_bp.route('/gravar_nf/<string:lote_id>', methods=['POST'])
@login_required
def gravar_nf(lote_id):
    """
    Valida NF em FaturamentoProduto E grava em Separacao.numero_nf

    Payload:
    {
        "numero_nf": "12345"
    }

    Response:
    {
        "success": true,
        "existe": true/false,
        "status": "Lançado"|"Cancelado"|null,
        "sincronizado_nf": true/false,
        "itens_atualizados": 3,
        "message": "..."
    }
    """
    from app.faturamento.models import FaturamentoProduto

    try:
        data = request.get_json()
        numero_nf = data.get('numero_nf', '').strip()

        if not numero_nf:
            return jsonify({
                'success': False,
                'message': 'Número da NF não informado'
            }), 400

        # PASSO 1: Validar NF em FaturamentoProduto
        faturamento = FaturamentoProduto.query.filter_by(
            numero_nf=numero_nf
        ).first()

        existe_faturamento = False
        status_nf = None
        sincronizado = False

        if faturamento:
            existe_faturamento = True
            status_nf = faturamento.status_nf or 'Lançado'
            sincronizado = (status_nf != 'Cancelado')

        # PASSO 2: Gravar em Separacao (TODAS as linhas do lote)
        itens_separacao = Separacao.query.filter_by(
            separacao_lote_id=lote_id
        ).all()

        if not itens_separacao:
            return jsonify({
                'success': False,
                'message': f'Nenhum item de separação encontrado para o lote {lote_id}'
            }), 404

        # Atualizar TODOS os itens do lote
        itens_atualizados = 0
        for item in itens_separacao:
            item.numero_nf = numero_nf
            item.sincronizado_nf = sincronizado  # Marca como sincronizado apenas se NF válida

            if sincronizado:
                item.data_sincronizacao = datetime.now()

            itens_atualizados += 1

        db.session.commit()

        # PASSO 3: Log e resposta
        print(f"[GRAVAR NF] Lote: {lote_id} | NF: {numero_nf} | Existe: {existe_faturamento} | Status: {status_nf} | Sincronizado: {sincronizado} | Itens: {itens_atualizados}")

        if existe_faturamento:
            if sincronizado:
                mensagem = f'✅ NF {numero_nf} gravada e sincronizada com sucesso! (Status: {status_nf}) - {itens_atualizados} itens atualizados'
            else:
                mensagem = f'⚠️ NF {numero_nf} está CANCELADA. Não foi marcada como sincronizada. - {itens_atualizados} itens atualizados'
        else:
            mensagem = f'⚠️ NF {numero_nf} NÃO encontrada no faturamento, mas foi gravada para referência. - {itens_atualizados} itens atualizados'

        return jsonify({
            'success': True,
            'existe': existe_faturamento,
            'status': status_nf,
            'sincronizado_nf': sincronizado,
            'itens_atualizados': itens_atualizados,
            'message': mensagem
        })

    except Exception as e:
        db.session.rollback()
        print(f"[ERRO GRAVAR NF] Lote: {lote_id} | Erro: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Erro ao gravar NF: {str(e)}'
        }), 500


@pedidos_bp.route('/verificar_monitoramento', methods=['POST'])
@login_required
def verificar_monitoramento():
    """
    Verifica status de nf_cd em EntregaMonitorada

    Payload:
    {
        "lote_id": "LOTE-123",
        "numero_nf": "12345" (optional)
    }

    Response:
    {
        "success": true,
        "encontrado": true/false,
        "nf_cd": true/false,
        "message": "..."
    }
    """
    from app.monitoramento.models import EntregaMonitorada

    try:
        data = request.get_json()
        lote_id = data.get('lote_id')
        numero_nf = data.get('numero_nf')

        if not lote_id and not numero_nf:
            return jsonify({
                'success': False,
                'message': 'Informe lote_id ou numero_nf'
            }), 400

        # Buscar EntregaMonitorada
        # Prioridade 1: Por separacao_lote_id
        entrega = None
        if lote_id:
            entrega = EntregaMonitorada.query.filter_by(
                separacao_lote_id=lote_id
            ).first()

        # Fallback: Por numero_nf
        if not entrega and numero_nf:
            entrega = EntregaMonitorada.query.filter_by(
                numero_nf=numero_nf
            ).first()

        if entrega:
            # Encontrado
            nf_cd = bool(entrega.nf_cd)

            print(f"[VERIFICAR MONITORAMENTO] Lote: {lote_id} | NF: {numero_nf} | nf_cd: {nf_cd}")

            return jsonify({
                'success': True,
                'encontrado': True,
                'nf_cd': nf_cd,
                'message': f'Entrega encontrada (nf_cd={nf_cd})'
            })
        else:
            # Não encontrado
            print(f"[VERIFICAR MONITORAMENTO] Lote: {lote_id} | NF: {numero_nf} | Não encontrado")

            return jsonify({
                'success': True,
                'encontrado': False,
                'nf_cd': False,
                'message': 'Entrega não encontrada no monitoramento'
            })

    except Exception as e:
        print(f"[ERRO VERIFICAR MONITORAMENTO] {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Erro ao verificar monitoramento: {str(e)}'
        }), 500

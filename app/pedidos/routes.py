from flask import render_template, request, redirect, url_for, Blueprint, flash, session
from flask_login import login_required
from app import db
from app.pedidos.models import Pedido
from app.pedidos.forms import FiltroPedidosForm, CotarFreteForm, EditarPedidoForm
from app.separacao.models import Separacao
from app.transportadoras.models import Transportadora
from app.veiculos.models import Veiculo
from sqlalchemy import func, distinct
from app.utils.localizacao import LocalizacaoService
from app.cadastros_agendamento.models import ContatoAgendamento
from app.embarques.models import Embarque, EmbarqueItem
from flask import jsonify
import uuid  # ✅ ADICIONADO: Para gerar lotes únicos
from app.utils.embarque_numero import obter_proximo_numero_embarque
from datetime import datetime



pedidos_bp = Blueprint('pedidos', __name__, url_prefix='/pedidos')

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
        
        # Conta pedidos ABERTOS da data
        abertos_data = Pedido.query.filter(
            func.date(Pedido.expedicao) == data_filtro,
            Pedido.cotacao_id.is_(None),
            Pedido.nf_cd == False,
            (Pedido.nf.is_(None)) | (Pedido.nf == ""),  # ✅ CORRIGIDO: Exclui pedidos com NF
            Pedido.data_embarque.is_(None)  # ✅ CORRIGIDO: Exclui pedidos embarcados
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
            Pedido.cotacao_id.is_(None),
            Pedido.nf_cd == False,
            (Pedido.nf.is_(None)) | (Pedido.nf == ""),  # ✅ CORRIGIDO: Exclui pedidos com NF
            Pedido.data_embarque.is_(None)  # ✅ CORRIGIDO: Exclui pedidos embarcados
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
            Pedido.cotacao_id.is_(None),
            (Pedido.nf.is_(None)) | (Pedido.nf == ""),
            Pedido.nf_cd == False,
            Pedido.expedicao < hoje
        ).count()
    }
    
    # ✅ NOVO: Contador de pedidos com agendamento pendente
    # Buscar CNPJs que precisam de agendamento
    contatos_agendamento_count = ContatoAgendamento.query.filter(
        ContatoAgendamento.forma != None,
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

    # ✅ APLICAR FILTROS DE ATALHO (botões) - SEMPRE PRIMEIRO
    filtros_botao_aplicados = False
    
    if filtro_status:
        filtros_botao_aplicados = True
        if filtro_status == 'abertos':
            query = query.filter(
                Pedido.cotacao_id.is_(None),
                Pedido.nf_cd == False,
                (Pedido.nf.is_(None)) | (Pedido.nf == ""),  # ✅ CORRIGIDO: Exclui pedidos com NF
                Pedido.data_embarque.is_(None)  # ✅ CORRIGIDO: Exclui pedidos embarcados
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
                query = query.filter(Pedido.id == -1)
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
    
    # ✅ APLICAR FILTROS DO FORMULÁRIO (quando POST) OU PRESERVAR FILTROS DE BOTÃO
    # Se for POST do filtro_form, rodamos 'validate_on_submit' nele.
    # Se há filtros de botão mas não é POST, não aplica filtros do formulário
    aplicar_filtros_formulario = filtro_form.validate_on_submit() or not filtros_botao_aplicados
    
    if aplicar_filtros_formulario and request.method == 'POST':
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
            elif status_filtro == 'EMBARCADO':
                query = query.filter(
                    Pedido.data_embarque.isnot(None),
                    (Pedido.nf.is_(None)) | (Pedido.nf == ""),
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
                    Pedido.cotacao_id.is_(None),
                    Pedido.nf_cd == False  # ✅ CORRIGIDO: Não deve estar no CD
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
    
    # Aplicar ordenação
    if sort_by in campos_ordenacao:
        campo_ordenacao = campos_ordenacao[sort_by]
        if sort_order == 'desc':
            query = query.order_by(campo_ordenacao.desc())
        else:
            query = query.order_by(campo_ordenacao.asc())
    else:
        # Ordenação padrão se campo inválido
        query = query.order_by(
            Pedido.rota.asc(),
            Pedido.cod_uf.asc(),
            Pedido.sub_rota.asc(),
            Pedido.expedicao.asc(),
            Pedido.nome_cidade.asc(),
            Pedido.cnpj_cpf.asc()
        )

    pedidos = query.all()
    
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

@pedidos_bp.route('/editar/<int:pedido_id>', methods=['GET', 'POST'])
@login_required
def editar_pedido(pedido_id):
    """
    Edita campos específicos de um pedido (agenda, protocolo, expedição)
    e sincroniza as alterações com a separação relacionada.
    Permite alterações apenas em pedidos com status "ABERTO".
    Suporta requisições AJAX para pop-up.
    """
    
    pedido = Pedido.query.get_or_404(pedido_id)
    
    # ✅ VALIDAÇÃO: Só permite editar pedidos com status ABERTO
    if pedido.status_calculado != 'ABERTO':
        if request.args.get('ajax'):
            return jsonify({
                'success': False, 
                'message': f"Não é possível editar o pedido {pedido.num_pedido}. Apenas pedidos com status 'ABERTO' podem ser editados."
            })
        flash(f"Não é possível editar o pedido {pedido.num_pedido}. Apenas pedidos com status 'ABERTO' podem ser editados. Status atual: {pedido.status_calculado}", "error")
        return redirect(url_for('pedidos.lista_pedidos'))
    
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
                'protocolo': pedido.protocolo
            }
            
            # ✅ ATUALIZA OS CAMPOS DO PEDIDO
            pedido.expedicao = form.expedicao.data
            pedido.agendamento = form.agendamento.data
            pedido.protocolo = form.protocolo.data
            
            # ✅ SINCRONIZA COM SEPARAÇÃO
            # Busca todas as separações relacionadas ao pedido através do lote
            separacoes_relacionadas = []
            if pedido.separacao_lote_id:
                separacoes_relacionadas = Separacao.query.filter_by(
                    separacao_lote_id=pedido.separacao_lote_id
                ).all()
            
            # Se não encontrou por lote, busca por chave composta
            if not separacoes_relacionadas:
                separacoes_relacionadas = Separacao.query.filter_by(
                    num_pedido=pedido.num_pedido,
                    expedicao=valores_originais['expedicao'],
                    agendamento=valores_originais['agendamento'],
                    protocolo=valores_originais['protocolo']
                ).all()
            
            # Atualiza as separações encontradas
            separacoes_atualizadas = 0
            for separacao in separacoes_relacionadas:
                separacao.expedicao = form.expedicao.data
                separacao.agendamento = form.agendamento.data
                separacao.protocolo = form.protocolo.data
                separacoes_atualizadas += 1
            
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
            print(f"  - Separações atualizadas: {separacoes_atualizadas}")
            
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
    
    # ✅ RESPOSTA PARA AJAX (apenas o conteúdo do formulário)
    if request.args.get('ajax'):
        return render_template('pedidos/editar_pedido_ajax.html', form=form, pedido=pedido, contato_agendamento=contato_agendamento)
    
    return render_template('pedidos/editar_pedido.html', form=form, pedido=pedido, contato_agendamento=contato_agendamento)

@pedidos_bp.route('/excluir/<int:pedido_id>', methods=['POST'])
@login_required
def excluir_pedido(pedido_id):
    """
    Exclui um pedido e todas as separações relacionadas.
    Permite exclusão apenas de pedidos com status "ABERTO".
    Limpa automaticamente vínculos órfãos com embarques cancelados.
    """
    pedido = Pedido.query.get_or_404(pedido_id)
    
    # ✅ VALIDAÇÃO: Só permite excluir pedidos com status ABERTO
    if pedido.status_calculado != 'ABERTO':
        flash(f"Não é possível excluir o pedido {pedido.num_pedido}. Apenas pedidos com status 'ABERTO' podem ser excluídos. Status atual: {pedido.status_calculado}", "error")
        return redirect(url_for('pedidos.lista_pedidos'))
    
    try:
        # ✅ BACKUP de informações para log
        num_pedido = pedido.num_pedido
        lote_id = pedido.separacao_lote_id
        
        # 🔧 NOVA FUNCIONALIDADE: Limpa vínculos órfãos com embarques cancelados
        vinculos_limpos = False
        if pedido.cotacao_id or pedido.transportadora or pedido.nf or pedido.data_embarque:
            from app.embarques.models import Embarque, EmbarqueItem
            
            # Busca se há embarque relacionado
            embarque_relacionado = None
            if lote_id:
                item_embarque = EmbarqueItem.query.filter_by(separacao_lote_id=lote_id).first()
                if item_embarque:
                    embarque_relacionado = Embarque.query.get(item_embarque.embarque_id)
            
            # Se o embarque estiver cancelado, limpa os vínculos órfãos
            if embarque_relacionado and embarque_relacionado.status == 'cancelado':
                print(f"[DEBUG] 🧹 Limpando vínculos órfãos com embarque cancelado #{embarque_relacionado.numero}")
                pedido.nf = None
                pedido.data_embarque = None
                pedido.cotacao_id = None
                pedido.transportadora = None
                pedido.nf_cd = False
                vinculos_limpos = True
        
        # ✅ BUSCA E EXCLUI SEPARAÇÕES RELACIONADAS
        separacoes_excluidas = 0
        
        # Primeiro busca por lote
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
                num_pedido=pedido.num_pedido,
                expedicao=pedido.expedicao,
                agendamento=pedido.agendamento,
                protocolo=pedido.protocolo
            ).all()
            
            for separacao in separacoes_relacionadas:
                db.session.delete(separacao)
                separacoes_excluidas += 1
        
        # 🔧 NOVA FUNCIONALIDADE: Excluir itens de cotação relacionados
        from app.cotacao.models import CotacaoItem
        itens_cotacao_excluidos = 0
        itens_cotacao = CotacaoItem.query.filter_by(pedido_id=pedido.id).all()
        for item_cotacao in itens_cotacao:
            db.session.delete(item_cotacao)
            itens_cotacao_excluidos += 1
        
        if itens_cotacao_excluidos > 0:
            print(f"[DEBUG] 🗑️ Removendo {itens_cotacao_excluidos} item(ns) de cotação relacionados")

        # ✅ EXCLUI O PEDIDO
        db.session.delete(pedido)
        
        # ✅ COMMIT das exclusões
        db.session.commit()
        
        # ✅ MENSAGEM DE SUCESSO
        mensagem_base = f"Pedido {num_pedido} excluído com sucesso! {separacoes_excluidas} item(ns) de separação também foram removidos."
        if itens_cotacao_excluidos > 0:
            mensagem_base += f" {itens_cotacao_excluidos} item(ns) de cotação também foram removidos."
        if vinculos_limpos:
            mensagem_base += " Vínculos órfãos com embarque cancelado foram automaticamente removidos."
        
        flash(mensagem_base, "success")
        
        # ✅ LOG da exclusão
        print(f"[DELETE] Pedido {num_pedido} excluído:")
        print(f"  - Lote de separação: {lote_id}")
        print(f"  - Separações removidas: {separacoes_excluidas}")
        
    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao excluir pedido: {str(e)}", "error")
    
    return redirect(url_for('pedidos.lista_pedidos'))

def gerar_lote_id():
    """Gera um ID único para o lote de separação"""
    return f"LOTE_{uuid.uuid4().hex[:8].upper()}"

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
        
        if pedido_existente:
            pedido_existente.data_pedido = row.data_pedido
            pedido_existente.cnpj_cpf = row.cnpj_cpf
            pedido_existente.raz_social_red = row.raz_social_red
            pedido_existente.nome_cidade = row.nome_cidade
            pedido_existente.cod_uf = row.cod_uf
            pedido_existente.valor_saldo_total = row.valor_saldo_total
            pedido_existente.pallet_total = row.pallet_total
            pedido_existente.peso_total = row.peso_total
            pedido_existente.rota = row.rota
            pedido_existente.sub_rota = row.sub_rota
            pedido_existente.observ_ped_1 = row.observ_ped_1
            pedido_existente.roteirizacao = row.roteirizacao
            pedido_existente.separacao_lote_id = lote_id  # ✅ NOVO: Conecta com separação
            # ✨ Usa o novo serviço de normalização
            LocalizacaoService.normalizar_dados_pedido(pedido_existente)
        else:
            novo = Pedido(
                num_pedido = row.num_pedido,
                data_pedido = row.data_pedido,
                cnpj_cpf = row.cnpj_cpf,
                raz_social_red = row.raz_social_red,
                nome_cidade = row.nome_cidade,
                cod_uf = row.cod_uf,
                valor_saldo_total = row.valor_saldo_total,
                pallet_total = row.pallet_total,
                peso_total = row.peso_total,
                rota = row.rota,
                sub_rota = row.sub_rota,
                observ_ped_1 = row.observ_ped_1,
                roteirizacao = row.roteirizacao,
                expedicao = row.expedicao,
                agendamento = row.agendamento,
                protocolo = row.protocolo,
                separacao_lote_id = lote_id  # ✅ NOVO: Conecta com separação
            )
            # ✨ Usa o novo serviço de normalização
            LocalizacaoService.normalizar_dados_pedido(novo)
            db.session.add(novo)

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
                pedido.status = status_correto
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
        # Recebe os IDs dos pedidos selecionados
        lista_ids_str = request.form.getlist("pedido_ids")
        if not lista_ids_str:
            flash("Nenhum pedido selecionado!", "warning")
            return redirect(url_for("pedidos.lista_pedidos"))

        lista_ids = [int(x) for x in lista_ids_str]

        # Armazena no session para usar nas rotas subsequentes
        session["cotacao_manual_pedidos"] = lista_ids

        # Carrega os pedidos do banco
        pedidos = Pedido.query.filter(Pedido.id.in_(lista_ids)).all()
        
        if not pedidos:
            flash("Nenhum pedido encontrado!", "warning")
            return redirect(url_for("pedidos.lista_pedidos"))

        # ✅ NOVO: Normaliza dados dos pedidos para mostrar nomes corretos das cidades
        for pedido in pedidos:
            LocalizacaoService.normalizar_dados_pedido(pedido)
        
        # Commit para salvar normalizações
        db.session.commit()

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
        pedidos = Pedido.query.filter(Pedido.id.in_(lista_ids)).all()
        transportadora = Transportadora.query.get(transportadora_id)

        if not pedidos or not transportadora:
            flash("Dados não encontrados!", "error")
            return redirect(url_for("pedidos.cotacao_manual"))

        # ✅ NOVO: Normaliza dados dos pedidos usando LocalizacaoService (igual ao "Cotar Frete")
        for pedido in pedidos:
            LocalizacaoService.normalizar_dados_pedido(pedido)
        
        # Commit para salvar normalizações
        db.session.commit()

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
        cotacao = Cotacao(
            usuario_id=1,  # Ajustar conforme seu sistema de usuários
            transportadora_id=transportadora_id,
            status='Fechado',
            data_criacao=datetime.now(),
            data_fechamento=datetime.now(),
            tipo_carga='DIRETA',  # ✅ CORRIGIDO: DIRETA ao invés de MANUAL
            valor_total=valor_total,
            peso_total=peso_total,
            modalidade=modalidade,
            nome_tabela='Cotação Manual',
            frete_minimo_valor=valor_frete,  # Usa o valor manual como frete_minimo_valor
            valor_kg=0,
            percentual_valor=0,
            frete_minimo_peso=0,
            icms=0,
            percentual_gris=0,
            pedagio_por_100kg=0,
            valor_tas=0,
            percentual_adv=0,
            percentual_rca=0,
            valor_despacho=0,
            valor_cte=0,
            icms_incluso=True,  # ✅ CORRIGIDO: True para cotação manual
            icms_destino=0
        )
        db.session.add(cotacao)
        db.session.flush()  # Para obter o ID da cotação

        # Cria itens da cotação
        for pedido in pedidos:
            cotacao_item = CotacaoItem(
                cotacao_id=cotacao.id,
                pedido_id=pedido.id,
                cnpj_cliente=pedido.cnpj_cpf,
                cliente=pedido.raz_social_red,
                peso=pedido.peso_total or 0,
                valor=pedido.valor_saldo_total or 0,
                modalidade=modalidade,
                nome_tabela='Cotação Manual',
                frete_minimo_valor=valor_frete,  # Usa o valor manual
                valor_kg=0,
                percentual_valor=0,
                frete_minimo_peso=0,
                icms=0,
                percentual_gris=0,
                pedagio_por_100kg=0,
                valor_tas=0,
                percentual_adv=0,
                percentual_rca=0,
                valor_despacho=0,
                valor_cte=0,
                icms_incluso=True,  # ✅ CORRIGIDO: True para cotação manual
                icms_destino=0
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
            modalidade=modalidade,
            # ✅ CORRIGIDO: Dados da tabela no nível do Embarque (como carga direta)
            tabela_nome_tabela='Cotação Manual',
            tabela_frete_minimo_valor=valor_frete,  # Apenas este campo preenchido
            tabela_valor_kg=0,
            tabela_percentual_valor=0,
            tabela_frete_minimo_peso=0,
            tabela_icms=0,
            tabela_percentual_gris=0,
            tabela_pedagio_por_100kg=0,
            tabela_valor_tas=0,
            tabela_percentual_adv=0,
            tabela_percentual_rca=0,
            tabela_valor_despacho=0,
            tabela_valor_cte=0,
            tabela_icms_incluso=True,  # ✅ CORRIGIDO: ICMS incluso
            icms_destino=0,
            transportadora_optante=False,
            criado_por='Sistema'
        )
        db.session.add(embarque)
        db.session.flush()  # Para obter o ID do embarque

        # Cria itens do embarque
        for pedido in pedidos:
            # ✅ NOVO: Busca cidade correta usando LocalizacaoService (igual ao "Cotar Frete")
            cidade_correta = LocalizacaoService.buscar_cidade_unificada(pedido=pedido)
            
            # ✅ NOVO: Usa nome correto da cidade ou fallback para o nome normalizado
            nome_cidade_correto = cidade_correta.nome if cidade_correta else pedido.cidade_normalizada or pedido.nome_cidade
            uf_correto = cidade_correta.uf if cidade_correta else pedido.uf_normalizada or pedido.cod_uf
            
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
                uf_destino=uf_correto,
                cidade_destino=nome_cidade_correto,
                cotacao_id=cotacao.id,
                volumes=None,  # Deixa volumes em branco para preenchimento manual
                # ✅ CORRIGIDO: Cotação manual é DIRETA - dados da tabela ficam apenas no Embarque
                # EmbarqueItem não precisa dos campos de tabela
                modalidade=None,
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
                icms_destino=None
                # ✅ REMOVIDO: transportadora_optante (campo não existe em EmbarqueItem)
            )
            db.session.add(embarque_item)

        # ✅ CORRIGIDO: Atualiza todos os pedidos após criar os itens
        for pedido in pedidos:
            pedido.cotacao_id = cotacao.id
            pedido.transportadora = transportadora.razao_social
            pedido.nf_cd = False  # ✅ NOVO: Reseta flag NF no CD ao criar cotação manual
            # Status será calculado automaticamente

        # Commit final
        db.session.commit()

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
        # Recebe os IDs dos pedidos selecionados
        lista_ids_str = request.form.getlist("pedido_ids")
        if not lista_ids_str:
            flash("Nenhum pedido selecionado!", "warning")
            return redirect(url_for("pedidos.lista_pedidos"))

        lista_ids = [int(x) for x in lista_ids_str]

        # Carrega os pedidos do banco
        pedidos = Pedido.query.filter(Pedido.id.in_(lista_ids)).all()
        
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

        # Normaliza dados dos pedidos para usar nomes corretos das cidades
        for pedido in pedidos:
            LocalizacaoService.normalizar_dados_pedido(pedido)
        
        # Commit para salvar normalizações
        db.session.commit()

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
                uf_destino=uf_correto,
                cidade_destino=nome_cidade_correto,
                cotacao_id=None,  # SEM COTAÇÃO para FOB
                volumes=None,  # Deixa volumes em branco para preenchimento manual
                # ✅ SEM DADOS DE TABELA (FOB não usa tabelas)
                modalidade=None,
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
                icms_destino=None
                # ✅ REMOVIDO: transportadora_optante (campo não existe em EmbarqueItem)
            )
            db.session.add(embarque_item)

        # ✅ CORRIGIDO: Atualiza todos os pedidos após criar os itens FOB
        for pedido in pedidos:
            # FOB não tem cotação, mas precisa de cotacao_id para ficar como COTADO
            # Vamos criar uma cotação fictícia para FOB
            if not pedido.cotacao_id:
                # Cria uma cotação FOB fictícia se não existir
                from app.cotacao.models import Cotacao
                cotacao_fob = Cotacao(
                    usuario_id=1,  # Sistema
                    transportadora_id=transportadora_fob.id,
                    status='Fechado',
                    data_criacao=datetime.now(),
                    data_fechamento=datetime.now(),
                    tipo_carga='FOB',
                    valor_total=sum(p.valor_saldo_total or 0 for p in pedidos),
                    peso_total=sum(p.peso_total or 0 for p in pedidos),
                    modalidade='FOB',
                    nome_tabela='FOB - COLETA',
                    frete_minimo_valor=0,
                    valor_kg=0,
                    percentual_valor=0,
                    frete_minimo_peso=0,
                    icms=0,
                    percentual_gris=0,
                    pedagio_por_100kg=0,
                    valor_tas=0,
                    percentual_adv=0,
                    percentual_rca=0,
                    valor_despacho=0,
                    valor_cte=0,
                    icms_incluso=False,
                    icms_destino=0
                )
                db.session.add(cotacao_fob)
                db.session.flush()
                
                # Atualiza o embarque com a cotação FOB
                embarque.cotacao_id = cotacao_fob.id
            
            # Atualiza o pedido
            pedido.cotacao_id = embarque.cotacao_id or cotacao_fob.id
            pedido.transportadora = transportadora_fob.razao_social
            pedido.nf_cd = False  # ✅ NOVO: Reseta flag NF no CD ao criar embarque FOB
            # O status será calculado automaticamente como COTADO pelo trigger

        # Commit final
        db.session.commit()

        flash(f"Embarque FOB #{embarque.numero} criado com sucesso! Transportadora: FOB - COLETA", "success")
        return redirect(url_for('embarques.visualizar_embarque', id=embarque.id))

    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao criar embarque FOB: {str(e)}", "error")
        return redirect(url_for("pedidos.lista_pedidos"))

@pedidos_bp.route('/detalhes/<int:id>')
@login_required
def detalhes_pedido(id):
    """
    Visualiza detalhes completos de um pedido
    """
    pedido = Pedido.query.get_or_404(id)
    
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
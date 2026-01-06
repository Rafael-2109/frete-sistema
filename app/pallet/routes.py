from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from app import db
from app.estoque.models import MovimentacaoEstoque
from app.embarques.models import Embarque, EmbarqueItem
from app.transportadoras.models import Transportadora
from app.cadastros_agendamento.models import ContatoAgendamento
from app.pallet.models import ValePallet
from app.pallet.utils import (
    normalizar_cnpj, raiz_cnpj, buscar_tipo_destinatario,
    calcular_prazo_cobranca, PRAZO_COBRANCA_SP_RED, PRAZO_COBRANCA_OUTROS
)
from sqlalchemy import func, or_

pallet_bp = Blueprint('pallet', __name__, url_prefix='/pallet')

# Codigo do produto PALLET
COD_PRODUTO_PALLET = '208000012'
NOME_PRODUTO_PALLET = 'PALLET'


def obter_uf_destinatario(cnpj: str) -> str:
    """
    Busca a UF do destinatario pelo CNPJ.
    Prioridade: Transportadora > ContatoAgendamento

    Args:
        cnpj: CNPJ do destinatario (pode estar formatado)

    Returns:
        UF do destinatario ou '' se nao encontrado
    """
    if not cnpj:
        return ''

    raiz = raiz_cnpj(cnpj)
    if not raiz:
        return ''

    # 1. Buscar em Transportadora (tem campo UF)
    for transp in Transportadora.query.filter(Transportadora.ativo == True).all():
        if raiz_cnpj(transp.cnpj) == raiz:
            return transp.uf or ''

    # 2. ContatoAgendamento nao tem UF, retorna vazio
    # Poderiamos buscar no Embarque se tiver referencia
    return ''


def calcular_prazo_remessa(remessa) -> int:
    """
    Calcula o prazo de cobranca para uma remessa de pallet.

    Regras:
    - UF=SP ou Rota=RED: 7 dias
    - Demais: 30 dias

    Args:
        remessa: MovimentacaoEstoque do tipo REMESSA

    Returns:
        Prazo em dias
    """
    # Tentar obter UF do destinatario
    uf = obter_uf_destinatario(remessa.cnpj_destinatario)

    # Se tiver referencia ao embarque, buscar rota
    rota = None
    if remessa.codigo_embarque:
        try:
            embarque = Embarque.query.get(remessa.codigo_embarque)
            if embarque and embarque.itens_ativos:
                # Usar a rota do primeiro item (geralmente todos tem a mesma)
                for item in embarque.itens_ativos:
                    if hasattr(item, 'rota') and item.rota:
                        rota = item.rota
                        break
        except Exception:
            pass

    return calcular_prazo_cobranca(uf, rota)


@pallet_bp.route('/')
@login_required
def index():
    """Dashboard de gestao de pallet"""
    # Estatisticas gerais - incluindo REMESSA
    total_em_terceiros = db.session.query(
        func.coalesce(func.sum(MovimentacaoEstoque.qtd_movimentacao), 0)
    ).filter(
        MovimentacaoEstoque.local_movimentacao == 'PALLET',
        MovimentacaoEstoque.tipo_movimentacao.in_(['SAIDA', 'REMESSA']),
        MovimentacaoEstoque.baixado == False,
        MovimentacaoEstoque.ativo == True
    ).scalar() or 0

    # Saldos por destinatario
    saldos = MovimentacaoEstoque.listar_saldos_pallet_pendentes()

    # Ultimos movimentos
    ultimos_movimentos = MovimentacaoEstoque.query.filter(
        MovimentacaoEstoque.local_movimentacao == 'PALLET',
        MovimentacaoEstoque.ativo == True
    ).order_by(MovimentacaoEstoque.criado_em.desc()).limit(10).all()

    # ====== ALERTAS DE PRAZO DIFERENCIADO ======
    # Regras: SP/RED = 7 dias, Outros = 30 dias
    hoje = date.today()

    # Buscar todas as remessas pendentes e calcular prazo individualmente
    todas_remessas_pendentes = MovimentacaoEstoque.query.filter(
        MovimentacaoEstoque.local_movimentacao == 'PALLET',
        MovimentacaoEstoque.tipo_movimentacao == 'REMESSA',
        MovimentacaoEstoque.baixado == False,
        MovimentacaoEstoque.ativo == True
    ).order_by(MovimentacaoEstoque.data_movimentacao.asc()).all()

    remessas_vencidas = []
    remessas_prestes_vencer = []

    for remessa in todas_remessas_pendentes:
        prazo_dias = calcular_prazo_remessa(remessa)
        data_vencimento = remessa.data_movimentacao + timedelta(days=prazo_dias)
        dias_ate_vencimento = (data_vencimento - hoje).days

        # Adicionar prazo calculado como atributo para uso no template
        remessa.prazo_dias = prazo_dias
        remessa.data_vencimento = data_vencimento
        remessa.dias_ate_vencimento = dias_ate_vencimento

        if dias_ate_vencimento < 0:
            # Vencida
            remessas_vencidas.append(remessa)
        elif dias_ate_vencimento <= 5:
            # Prestes a vencer (5 dias antes do prazo)
            remessas_prestes_vencer.append(remessa)

    # Vendas pendentes de vinculo (SAIDA sem movimento_baixado_id)
    vendas_pendentes_vinculo = MovimentacaoEstoque.query.filter(
        MovimentacaoEstoque.local_movimentacao == 'PALLET',
        MovimentacaoEstoque.tipo_movimentacao == 'SAIDA',
        MovimentacaoEstoque.movimento_baixado_id == None,
        MovimentacaoEstoque.ativo == True
    ).order_by(MovimentacaoEstoque.data_movimentacao.desc()).all()

    # Vale pallets pendentes
    vales_pendentes = ValePallet.query.filter(
        ValePallet.ativo == True,
        ValePallet.resolvido == False
    ).count()

    vales_vencidos = ValePallet.query.filter(
        ValePallet.ativo == True,
        ValePallet.resolvido == False,
        ValePallet.data_validade < hoje
    ).count()

    return render_template('pallet/index.html',
                           total_em_terceiros=int(total_em_terceiros),
                           saldos=saldos,
                           ultimos_movimentos=ultimos_movimentos,
                           remessas_vencidas=remessas_vencidas,
                           remessas_prestes_vencer=remessas_prestes_vencer,
                           vendas_pendentes_vinculo=vendas_pendentes_vinculo,
                           vales_pendentes=vales_pendentes,
                           vales_vencidos=vales_vencidos,
                           prazo_sp_red=PRAZO_COBRANCA_SP_RED,
                           prazo_outros=PRAZO_COBRANCA_OUTROS)


@pallet_bp.route('/movimentos')
@login_required
def listar_movimentos():
    """Lista todos os movimentos de pallet"""
    page = request.args.get('page', 1, type=int)
    filtro_tipo = request.args.get('tipo', '')
    filtro_baixado = request.args.get('baixado', '')
    filtro_destinatario = request.args.get('destinatario', '')

    query = MovimentacaoEstoque.query.filter(
        MovimentacaoEstoque.local_movimentacao == 'PALLET',
        MovimentacaoEstoque.ativo == True
    )

    if filtro_tipo:
        query = query.filter(MovimentacaoEstoque.tipo_movimentacao == filtro_tipo)
    if filtro_baixado == 'sim':
        query = query.filter(MovimentacaoEstoque.baixado == True)
    elif filtro_baixado == 'nao':
        query = query.filter(MovimentacaoEstoque.baixado == False)
    if filtro_destinatario:
        query = query.filter(MovimentacaoEstoque.tipo_destinatario == filtro_destinatario)

    movimentos = query.order_by(MovimentacaoEstoque.criado_em.desc()).paginate(
        page=page, per_page=50, error_out=False
    )

    return render_template('pallet/movimentos.html',
                           movimentos=movimentos,
                           filtro_tipo=filtro_tipo,
                           filtro_baixado=filtro_baixado,
                           filtro_destinatario=filtro_destinatario)


@pallet_bp.route('/registrar-saida', methods=['GET', 'POST'])
@login_required
def registrar_saida():
    """Registra uma saida de pallet (emissao de NF)"""
    if request.method == 'POST':
        try:
            embarque_id = request.form.get('embarque_id')
            embarque_item_id = request.form.get('embarque_item_id')

            movimento = MovimentacaoEstoque(
                cod_produto=COD_PRODUTO_PALLET,
                nome_produto=NOME_PRODUTO_PALLET,
                data_movimentacao=date.today(),
                tipo_movimentacao='SAIDA',
                local_movimentacao='PALLET',
                qtd_movimentacao=int(request.form.get('quantidade', 0)),
                tipo_destinatario=request.form.get('tipo_destinatario'),
                cnpj_destinatario=request.form.get('cnpj_destinatario', '').replace('.', '').replace('-', '').replace('/', ''),
                nome_destinatario=request.form.get('nome_destinatario'),
                numero_nf=request.form.get('numero_nf'),
                codigo_embarque=int(embarque_id) if embarque_id else None,
                embarque_item_id=int(embarque_item_id) if embarque_item_id else None,
                observacao=request.form.get('observacao'),
                tipo_origem='MANUAL',
                baixado=False,
                criado_por=current_user.nome if hasattr(current_user, 'nome') else str(current_user.id)
            )
            db.session.add(movimento)
            db.session.commit()
            flash(f'Saida de {movimento.qtd_movimentacao} pallets registrada com sucesso!', 'success')
            return redirect(url_for('pallet.listar_movimentos'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao registrar saida: {str(e)}', 'danger')

    embarques = Embarque.query.filter_by(status='ativo').order_by(Embarque.numero.desc()).limit(100).all()
    return render_template('pallet/registrar_saida.html', embarques=embarques)


@pallet_bp.route('/registrar-retorno', methods=['GET', 'POST'])
@login_required
def registrar_retorno():
    """Registra um retorno de pallet"""
    if request.method == 'POST':
        try:
            movimento = MovimentacaoEstoque(
                cod_produto=COD_PRODUTO_PALLET,
                nome_produto=NOME_PRODUTO_PALLET,
                data_movimentacao=date.today(),
                tipo_movimentacao='ENTRADA',
                local_movimentacao='PALLET',
                qtd_movimentacao=int(request.form.get('quantidade', 0)),
                tipo_destinatario=request.form.get('tipo_destinatario'),
                cnpj_destinatario=request.form.get('cnpj_destinatario', '').replace('.', '').replace('-', '').replace('/', ''),
                nome_destinatario=request.form.get('nome_destinatario'),
                numero_nf=request.form.get('numero_nf'),
                observacao=request.form.get('observacao'),
                tipo_origem='MANUAL',
                criado_por=current_user.nome if hasattr(current_user, 'nome') else str(current_user.id)
            )
            db.session.add(movimento)
            db.session.commit()
            flash(f'Retorno de {movimento.qtd_movimentacao} pallets registrado com sucesso!', 'success')
            return redirect(url_for('pallet.listar_movimentos'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao registrar retorno: {str(e)}', 'danger')

    # Listar destinatarios com saldo pendente para facilitar selecao
    saldos_pendentes = MovimentacaoEstoque.listar_saldos_pallet_pendentes()

    return render_template('pallet/registrar_retorno.html', saldos_pendentes=saldos_pendentes)


@pallet_bp.route('/baixar/<int:movimento_id>', methods=['GET', 'POST'])
@login_required
def baixar_movimento(movimento_id):
    """Baixa um movimento de saida"""
    saida = MovimentacaoEstoque.query.get_or_404(movimento_id)

    if saida.tipo_movimentacao != 'SAIDA' or saida.local_movimentacao != 'PALLET':
        flash('Apenas movimentos de SAIDA de pallet podem ser baixados!', 'warning')
        return redirect(url_for('pallet.listar_movimentos'))

    if saida.baixado:
        flash('Este movimento ja foi baixado!', 'warning')
        return redirect(url_for('pallet.listar_movimentos'))

    if request.method == 'POST':
        try:
            # Marcar como baixado
            saida.baixado = True
            saida.baixado_em = datetime.utcnow()
            saida.baixado_por = current_user.nome if hasattr(current_user, 'nome') else str(current_user.id)

            # Se foi informado um movimento de retorno, vincular
            retorno_id = request.form.get('retorno_id')
            if retorno_id:
                saida.movimento_baixado_id = int(retorno_id)

            # Observacao adicional
            obs_baixa = request.form.get('observacao_baixa')
            if obs_baixa:
                saida.observacao = (saida.observacao or '') + f'\n[BAIXA] {obs_baixa}'

            db.session.commit()
            flash('Movimento baixado com sucesso!', 'success')
            return redirect(url_for('pallet.listar_movimentos'))

        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao baixar movimento: {str(e)}', 'danger')

    # Buscar retornos disponiveis para vincular
    retornos_disponiveis = MovimentacaoEstoque.query.filter(
        MovimentacaoEstoque.local_movimentacao == 'PALLET',
        MovimentacaoEstoque.tipo_movimentacao == 'ENTRADA',
        MovimentacaoEstoque.ativo == True
    ).order_by(MovimentacaoEstoque.criado_em.desc()).limit(20).all()

    return render_template('pallet/baixar_movimento.html',
                           saida=saida,
                           retornos_disponiveis=retornos_disponiveis)


# ========== APIs ==========

@pallet_bp.route('/api/saldo/<cnpj>')
@login_required
def api_saldo_cnpj(cnpj):
    """Retorna saldo de pallet de um CNPJ"""
    cnpj_limpo = cnpj.replace('.', '').replace('-', '').replace('/', '')
    saldo = MovimentacaoEstoque.saldo_pallet_por_destinatario(cnpj_limpo)
    return jsonify({'cnpj': cnpj, 'saldo': int(saldo)})


@pallet_bp.route('/api/buscar-destinatario')
@login_required
def api_buscar_destinatario():
    """Busca cliente ou transportadora por CNPJ/nome"""
    termo = request.args.get('q', '')
    tipo = request.args.get('tipo', 'CLIENTE')

    resultados = []

    if tipo == 'CLIENTE':
        # Buscar em ContatoAgendamento
        contatos = ContatoAgendamento.query.filter(
            or_(
                ContatoAgendamento.cnpj.ilike(f'%{termo}%'),
                ContatoAgendamento.contato.ilike(f'%{termo}%')
            )
        ).limit(10).all()
        for c in contatos:
            resultados.append({
                'cnpj': c.cnpj,
                'nome': c.contato or c.cnpj,
                'aceita_nf_pallet': not c.nao_aceita_nf_pallet
            })
    else:
        # Buscar em Transportadora
        transportadoras = Transportadora.query.filter(
            or_(
                Transportadora.cnpj.ilike(f'%{termo}%'),
                Transportadora.razao_social.ilike(f'%{termo}%')
            )
        ).limit(10).all()
        for t in transportadoras:
            resultados.append({
                'cnpj': t.cnpj,
                'nome': t.razao_social,
                'aceita_nf_pallet': not t.nao_aceita_nf_pallet
            })

    return jsonify(resultados)


@pallet_bp.route('/api/embarque/<int:embarque_id>/itens')
@login_required
def api_embarque_itens(embarque_id):
    """Retorna itens de um embarque para selecao"""
    embarque = Embarque.query.get_or_404(embarque_id)
    itens = []
    for item in embarque.itens_ativos:
        itens.append({
            'id': item.id,
            'cliente': item.cliente,
            'cnpj': item.cnpj_cliente,
            'pedido': item.pedido,
            'aceita_nf_pallet': item.cliente_aceita_nf_pallet
        })
    return jsonify(itens)


@pallet_bp.route('/api/dashboard')
@login_required
def api_dashboard():
    """Retorna dados do dashboard em JSON"""
    total_em_terceiros = db.session.query(
        func.coalesce(func.sum(MovimentacaoEstoque.qtd_movimentacao), 0)
    ).filter(
        MovimentacaoEstoque.local_movimentacao == 'PALLET',
        MovimentacaoEstoque.tipo_movimentacao == 'SAIDA',
        MovimentacaoEstoque.baixado == False,
        MovimentacaoEstoque.ativo == True
    ).scalar() or 0

    saldos = MovimentacaoEstoque.listar_saldos_pallet_pendentes()
    saldos_json = [
        {
            'tipo': s.tipo_destinatario,
            'cnpj': s.cnpj_destinatario,
            'nome': s.nome_destinatario,
            'saldo': int(s.saldo)
        }
        for s in saldos
    ]

    return jsonify({
        'total_em_terceiros': int(total_em_terceiros),
        'saldos': saldos_json
    })


# ========== VALE PALLETS CRUD ==========


@pallet_bp.route('/vales')
@login_required
def listar_vales():
    """Lista todos os vale pallets"""
    page = request.args.get('page', 1, type=int)
    filtro_status = request.args.get('status', '')
    filtro_transportadora = request.args.get('transportadora', '')
    filtro_cliente = request.args.get('cliente', '')

    query = ValePallet.query.filter(ValePallet.ativo == True)

    # Filtros
    if filtro_status:
        if filtro_status == 'PENDENTE':
            query = query.filter(ValePallet.resolvido == False, ValePallet.recebido == False)
        elif filtro_status == 'RECEBIDO':
            query = query.filter(ValePallet.recebido == True, ValePallet.resolvido == False)
        elif filtro_status == 'RESOLVIDO':
            query = query.filter(ValePallet.resolvido == True)
        elif filtro_status == 'VENCIDO':
            query = query.filter(ValePallet.resolvido == False, ValePallet.data_validade < date.today())
        elif filtro_status == 'A_VENCER':
            limite = date.today() + timedelta(days=PRAZO_COBRANCA_OUTROS)
            query = query.filter(
                ValePallet.resolvido == False,
                ValePallet.data_validade >= date.today(),
                ValePallet.data_validade <= limite
            )

    if filtro_transportadora:
        query = query.filter(ValePallet.cnpj_transportadora.ilike(f'%{filtro_transportadora}%'))

    if filtro_cliente:
        query = query.filter(
            or_(
                ValePallet.cnpj_cliente.ilike(f'%{filtro_cliente}%'),
                ValePallet.nome_cliente.ilike(f'%{filtro_cliente}%')
            )
        )

    # Ordenar por data de validade (mais urgentes primeiro)
    vales = query.order_by(ValePallet.data_validade.asc()).paginate(
        page=page, per_page=50, error_out=False
    )

    # Estatisticas
    stats = {
        'total': ValePallet.query.filter(ValePallet.ativo == True, ValePallet.resolvido == False).count(),
        'pendentes': ValePallet.query.filter(
            ValePallet.ativo == True,
            ValePallet.resolvido == False,
            ValePallet.recebido == False
        ).count(),
        'recebidos': ValePallet.query.filter(
            ValePallet.ativo == True,
            ValePallet.recebido == True,
            ValePallet.resolvido == False
        ).count(),
        'vencidos': ValePallet.query.filter(
            ValePallet.ativo == True,
            ValePallet.resolvido == False,
            ValePallet.data_validade < date.today()
        ).count(),
        'a_vencer': ValePallet.query.filter(
            ValePallet.ativo == True,
            ValePallet.resolvido == False,
            ValePallet.data_validade >= date.today(),
            ValePallet.data_validade <= date.today() + timedelta(days=PRAZO_COBRANCA_OUTROS)
        ).count()
    }

    return render_template('pallet/vale_pallets.html',
                           vales=vales,
                           stats=stats,
                           filtro_status=filtro_status,
                           filtro_transportadora=filtro_transportadora,
                           filtro_cliente=filtro_cliente)


def baixar_nf_remessa_automaticamente(numero_nf: str, usuario: str) -> dict:
    """
    Verifica se a NF de remessa deve ser baixada com base nos vales vinculados.

    Regra: Se a soma das quantidades dos vales ativos >= quantidade da remessa,
    marca a remessa como baixada.

    Args:
        numero_nf: Numero da NF de remessa
        usuario: Nome do usuario que esta realizando a operacao

    Returns:
        dict com status da operacao
    """
    if not numero_nf:
        return {'baixada': False, 'motivo': 'NF nao informada'}

    # Buscar a NF de remessa
    remessa = MovimentacaoEstoque.query.filter(
        MovimentacaoEstoque.numero_nf == numero_nf,
        MovimentacaoEstoque.tipo_movimentacao == 'REMESSA',
        MovimentacaoEstoque.local_movimentacao == 'PALLET',
        MovimentacaoEstoque.ativo == True
    ).first()

    if not remessa:
        return {'baixada': False, 'motivo': 'NF de remessa nao encontrada'}

    if remessa.baixado:
        return {'baixada': True, 'motivo': 'NF ja estava baixada'}

    # Somar quantidade de todos os vales ativos vinculados a esta NF
    total_vales = db.session.query(
        func.coalesce(func.sum(ValePallet.quantidade), 0)
    ).filter(
        ValePallet.nf_pallet == numero_nf,
        ValePallet.ativo == True
    ).scalar() or 0

    # Se soma dos vales >= quantidade da remessa, baixar
    if total_vales >= remessa.qtd_movimentacao:
        remessa.baixado = True
        remessa.baixado_em = datetime.utcnow()
        remessa.baixado_por = usuario
        remessa.observacao = (remessa.observacao or '') + f'\n[BAIXA AUTOMATICA] Vales totalizam {total_vales} pallets'
        return {
            'baixada': True,
            'motivo': f'NF baixada automaticamente (vales: {total_vales}, remessa: {int(remessa.qtd_movimentacao)})'
        }

    return {
        'baixada': False,
        'motivo': f'Vales ({total_vales}) ainda nao cobrem remessa ({int(remessa.qtd_movimentacao)})',
        'pendente': int(remessa.qtd_movimentacao) - int(total_vales)
    }


@pallet_bp.route('/vales/novo', methods=['GET', 'POST'])
@login_required
def criar_vale():
    """Cria um novo vale pallet"""
    if request.method == 'POST':
        try:
            # Calcular data de validade (30 dias a partir da emissao)
            data_emissao_str = request.form.get('data_emissao')
            data_emissao = datetime.strptime(data_emissao_str, '%Y-%m-%d').date() if data_emissao_str else date.today()
            data_validade_str = request.form.get('data_validade')
            if data_validade_str:
                data_validade = datetime.strptime(data_validade_str, '%Y-%m-%d').date()
            else:
                data_validade = data_emissao + timedelta(days=PRAZO_COBRANCA_OUTROS)

            # Obter tipo_vale do formulario (novo campo)
            tipo_vale = request.form.get('tipo_vale', 'CANHOTO_ASSINADO')

            vale = ValePallet(
                nf_pallet=request.form.get('nf_pallet'),
                data_emissao=data_emissao,
                data_validade=data_validade,
                quantidade=int(request.form.get('quantidade', 0)),
                tipo_vale=tipo_vale,
                cnpj_cliente=request.form.get('cnpj_cliente', '').replace('.', '').replace('-', '').replace('/', ''),
                nome_cliente=request.form.get('nome_cliente'),
                cnpj_transportadora=request.form.get('cnpj_transportadora', '').replace('.', '').replace('-', '').replace('/', ''),
                nome_transportadora=request.form.get('nome_transportadora'),
                posse_atual=request.form.get('posse_atual', 'TRANSPORTADORA'),
                cnpj_posse=request.form.get('cnpj_posse', '').replace('.', '').replace('-', '').replace('/', ''),
                nome_posse=request.form.get('nome_posse'),
                pasta_arquivo=request.form.get('pasta_arquivo'),
                aba_arquivo=request.form.get('aba_arquivo'),
                observacao=request.form.get('observacao'),
                criado_por=current_user.nome if hasattr(current_user, 'nome') else str(current_user.id)
            )
            db.session.add(vale)
            db.session.flush()  # Obter ID do vale antes do commit

            # Baixar automaticamente a NF de remessa se aplicavel
            usuario = current_user.nome if hasattr(current_user, 'nome') else str(current_user.id)
            resultado_baixa = baixar_nf_remessa_automaticamente(vale.nf_pallet, usuario)

            db.session.commit()

            # Montar mensagem de sucesso
            msg = f'Vale pallet #{vale.id} criado com sucesso!'
            if resultado_baixa.get('baixada'):
                msg += f' {resultado_baixa.get("motivo")}'
            elif resultado_baixa.get('pendente'):
                msg += f' (Faltam {resultado_baixa.get("pendente")} pallets para baixar a NF)'

            flash(msg, 'success')
            return redirect(url_for('pallet.listar_vales'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao criar vale pallet: {str(e)}', 'danger')

    # Listar transportadoras para o select
    transportadoras = Transportadora.query.filter(
        Transportadora.ativo == True
    ).order_by(Transportadora.razao_social).all()

    return render_template('pallet/vale_pallet_form.html',
                           vale=None,
                           transportadoras=transportadoras,
                           prazo_dias=PRAZO_COBRANCA_OUTROS)


@pallet_bp.route('/vales/<int:vale_id>', methods=['GET', 'POST'])
@login_required
def editar_vale(vale_id):
    """Edita um vale pallet"""
    vale = ValePallet.query.get_or_404(vale_id)

    if request.method == 'POST':
        try:
            vale.nf_pallet = request.form.get('nf_pallet')
            data_emissao_str = request.form.get('data_emissao')
            if data_emissao_str:
                vale.data_emissao = datetime.strptime(data_emissao_str, '%Y-%m-%d').date()
            data_validade_str = request.form.get('data_validade')
            if data_validade_str:
                vale.data_validade = datetime.strptime(data_validade_str, '%Y-%m-%d').date()
            vale.quantidade = int(request.form.get('quantidade', 0))
            vale.tipo_vale = request.form.get('tipo_vale', 'CANHOTO_ASSINADO')
            vale.cnpj_cliente = request.form.get('cnpj_cliente', '').replace('.', '').replace('-', '').replace('/', '')
            vale.nome_cliente = request.form.get('nome_cliente')
            vale.cnpj_transportadora = request.form.get('cnpj_transportadora', '').replace('.', '').replace('-', '').replace('/', '')
            vale.nome_transportadora = request.form.get('nome_transportadora')
            vale.posse_atual = request.form.get('posse_atual', 'TRANSPORTADORA')
            vale.cnpj_posse = request.form.get('cnpj_posse', '').replace('.', '').replace('-', '').replace('/', '')
            vale.nome_posse = request.form.get('nome_posse')
            vale.pasta_arquivo = request.form.get('pasta_arquivo')
            vale.aba_arquivo = request.form.get('aba_arquivo')
            vale.observacao = request.form.get('observacao')
            vale.atualizado_por = current_user.nome if hasattr(current_user, 'nome') else str(current_user.id)
            vale.atualizado_em = datetime.utcnow()

            db.session.commit()
            flash('Vale pallet atualizado com sucesso!', 'success')
            return redirect(url_for('pallet.listar_vales'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar vale pallet: {str(e)}', 'danger')

    transportadoras = Transportadora.query.filter(
        Transportadora.ativo == True
    ).order_by(Transportadora.razao_social).all()

    return render_template('pallet/vale_pallet_form.html',
                           vale=vale,
                           transportadoras=transportadoras,
                           prazo_dias=PRAZO_COBRANCA_OUTROS)


@pallet_bp.route('/vales/<int:vale_id>/receber', methods=['POST'])
@login_required
def receber_vale(vale_id):
    """Marca um vale pallet como recebido pela Nacom"""
    vale = ValePallet.query.get_or_404(vale_id)

    if vale.recebido:
        flash('Este vale ja foi recebido!', 'warning')
        return redirect(url_for('pallet.listar_vales'))

    try:
        vale.recebido = True
        vale.recebido_em = datetime.utcnow()
        vale.recebido_por = current_user.nome if hasattr(current_user, 'nome') else str(current_user.id)
        vale.posse_atual = 'NACOM'
        vale.cnpj_posse = None
        vale.nome_posse = 'NACOM GOYA'
        vale.atualizado_em = datetime.utcnow()
        vale.atualizado_por = current_user.nome if hasattr(current_user, 'nome') else str(current_user.id)

        db.session.commit()
        flash('Vale pallet marcado como recebido!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao receber vale: {str(e)}', 'danger')

    return redirect(url_for('pallet.listar_vales'))


@pallet_bp.route('/vales/<int:vale_id>/enviar-resolucao', methods=['GET', 'POST'])
@login_required
def enviar_resolucao(vale_id):
    """Envia vale para coleta ou venda"""
    vale = ValePallet.query.get_or_404(vale_id)

    if vale.resolvido:
        flash('Este vale ja foi resolvido!', 'warning')
        return redirect(url_for('pallet.listar_vales'))

    if request.method == 'POST':
        try:
            vale.tipo_resolucao = request.form.get('tipo_resolucao', 'COLETA')
            vale.responsavel_resolucao = request.form.get('responsavel_resolucao')
            vale.cnpj_resolucao = request.form.get('cnpj_resolucao', '').replace('.', '').replace('-', '').replace('/', '')
            valor = request.form.get('valor_resolucao')
            if valor:
                vale.valor_resolucao = float(valor.replace(',', '.'))
            vale.enviado_coleta = True
            vale.enviado_coleta_em = datetime.utcnow()
            vale.enviado_coleta_por = current_user.nome if hasattr(current_user, 'nome') else str(current_user.id)
            vale.atualizado_em = datetime.utcnow()
            vale.atualizado_por = current_user.nome if hasattr(current_user, 'nome') else str(current_user.id)

            db.session.commit()
            flash(f'Vale enviado para {vale.tipo_resolucao}!', 'success')
            return redirect(url_for('pallet.listar_vales'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao enviar vale: {str(e)}', 'danger')

    return render_template('pallet/enviar_resolucao.html', vale=vale)


@pallet_bp.route('/vales/<int:vale_id>/resolver', methods=['GET', 'POST'])
@login_required
def resolver_vale(vale_id):
    """Marca vale pallet como resolvido"""
    vale = ValePallet.query.get_or_404(vale_id)

    if vale.resolvido:
        flash('Este vale ja foi resolvido!', 'warning')
        return redirect(url_for('pallet.listar_vales'))

    if request.method == 'POST':
        try:
            vale.nf_resolucao = request.form.get('nf_resolucao')
            valor = request.form.get('valor_resolucao')
            if valor:
                vale.valor_resolucao = float(valor.replace(',', '.'))
            vale.resolvido = True
            vale.resolvido_em = datetime.utcnow()
            vale.resolvido_por = current_user.nome if hasattr(current_user, 'nome') else str(current_user.id)
            vale.atualizado_em = datetime.utcnow()
            vale.atualizado_por = current_user.nome if hasattr(current_user, 'nome') else str(current_user.id)

            # Adicionar observacao
            obs = request.form.get('observacao')
            if obs:
                vale.observacao = (vale.observacao or '') + f'\n[RESOLVIDO] {obs}'

            db.session.commit()
            flash('Vale pallet resolvido com sucesso!', 'success')
            return redirect(url_for('pallet.listar_vales'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao resolver vale: {str(e)}', 'danger')

    return render_template('pallet/resolver_vale.html', vale=vale)


@pallet_bp.route('/vales/<int:vale_id>/excluir', methods=['POST'])
@login_required
def excluir_vale(vale_id):
    """Exclui (soft delete) um vale pallet"""
    vale = ValePallet.query.get_or_404(vale_id)

    try:
        vale.ativo = False
        vale.atualizado_em = datetime.utcnow()
        vale.atualizado_por = current_user.nome if hasattr(current_user, 'nome') else str(current_user.id)
        db.session.commit()
        flash('Vale pallet excluido com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir vale: {str(e)}', 'danger')

    return redirect(url_for('pallet.listar_vales'))


# ========== SINCRONIZACAO ODOO ==========

@pallet_bp.route('/sync', methods=['GET', 'POST'])
@login_required
def sincronizar_odoo():
    """Sincroniza movimentacoes de pallet com Odoo"""
    if request.method == 'POST':
        try:
            from app.odoo.utils.connection import get_odoo_connection
            from app.pallet.services import PalletSyncService

            dias = int(request.form.get('dias', 30))
            tipo_sync = request.form.get('tipo', 'tudo')

            odoo = get_odoo_connection()
            service = PalletSyncService(odoo)

            if tipo_sync == 'remessas':
                resumo = service.sincronizar_remessas(dias)
                flash(f'Remessas sincronizadas: {resumo.get("novos", 0)} novas', 'success')
            elif tipo_sync == 'vendas':
                resumo = service.sincronizar_vendas_pallet(dias)
                flash(f'Vendas sincronizadas: {resumo.get("novos", 0)} novas', 'success')
            elif tipo_sync == 'devolucoes':
                resumo = service.sincronizar_devolucoes(dias)
                msg = f'Devolucoes sincronizadas: {resumo.get("novos", 0)} novas'
                if resumo.get('baixas_realizadas', 0) > 0:
                    msg += f', {resumo.get("baixas_realizadas")} baixas automaticas'
                flash(msg, 'success')
            elif tipo_sync == 'recusas':
                resumo = service.sincronizar_recusas(dias)
                msg = f'Recusas sincronizadas: {resumo.get("novos", 0)} novas'
                if resumo.get('baixas_realizadas', 0) > 0:
                    msg += f', {resumo.get("baixas_realizadas")} baixas automaticas'
                flash(msg, 'success')
            else:
                resumo = service.sincronizar_tudo(dias)
                msg = f'Sincronizacao completa: {resumo.get("total_novos", 0)} novos registros'
                if resumo.get('total_baixas', 0) > 0:
                    msg += f', {resumo.get("total_baixas")} baixas automaticas'
                flash(msg, 'success')

            return redirect(url_for('pallet.listar_movimentos'))

        except Exception as e:
            flash(f'Erro na sincronizacao: {str(e)}', 'danger')
            return redirect(url_for('pallet.sincronizar_odoo'))

    return render_template('pallet/sincronizar.html')


@pallet_bp.route('/vincular-venda/<int:movimento_id>', methods=['GET', 'POST'])
@login_required
def vincular_venda(movimento_id):
    """Vincula uma venda de pallet a uma remessa pendente"""
    venda = MovimentacaoEstoque.query.get_or_404(movimento_id)

    if venda.tipo_movimentacao != 'SAIDA' or venda.local_movimentacao != 'PALLET':
        flash('Este movimento nao e uma venda de pallet!', 'warning')
        return redirect(url_for('pallet.listar_movimentos'))

    if venda.movimento_baixado_id:
        flash('Esta venda ja esta vinculada a uma remessa!', 'warning')
        return redirect(url_for('pallet.listar_movimentos'))

    if request.method == 'POST':
        try:
            remessa_id = int(request.form.get('remessa_id'))
            remessa = MovimentacaoEstoque.query.get_or_404(remessa_id)

            if remessa.tipo_movimentacao != 'REMESSA' or remessa.local_movimentacao != 'PALLET':
                flash('O movimento selecionado nao e uma remessa de pallet!', 'warning')
                return redirect(url_for('pallet.vincular_venda', movimento_id=movimento_id))

            # Vincular venda a remessa
            venda.movimento_baixado_id = remessa.id
            venda.baixado = True
            venda.baixado_em = datetime.utcnow()
            venda.baixado_por = current_user.nome if hasattr(current_user, 'nome') else str(current_user.id)

            # Marcar remessa como baixada (parcial ou total)
            remessa.baixado = True
            remessa.baixado_em = datetime.utcnow()
            remessa.baixado_por = current_user.nome if hasattr(current_user, 'nome') else str(current_user.id)

            # Adicionar observacao
            obs = f'Vinculado a venda NF {venda.numero_nf}'
            remessa.observacao = (remessa.observacao or '') + f'\n[BAIXA] {obs}'

            db.session.commit()
            flash('Venda vinculada a remessa com sucesso!', 'success')
            return redirect(url_for('pallet.listar_movimentos'))

        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao vincular: {str(e)}', 'danger')

    # Buscar remessas pendentes do mesmo destinatario
    remessas = MovimentacaoEstoque.query.filter(
        MovimentacaoEstoque.local_movimentacao == 'PALLET',
        MovimentacaoEstoque.tipo_movimentacao == 'REMESSA',
        MovimentacaoEstoque.baixado == False,
        MovimentacaoEstoque.ativo == True
    ).order_by(MovimentacaoEstoque.data_movimentacao.desc()).all()

    return render_template('pallet/vincular_venda.html',
                           venda=venda,
                           remessas=remessas)

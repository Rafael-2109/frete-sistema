from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from app import db
from app.utils.valores_brasileiros import converter_valor_brasileiro
from app.estoque.models import MovimentacaoEstoque
from app.embarques.models import Embarque
from app.transportadoras.models import Transportadora
from app.cadastros_agendamento.models import ContatoAgendamento
from app.pallet.models import ValePallet
from app.pallet.utils import (
    raiz_cnpj, 
    calcular_prazo_cobranca, PRAZO_COBRANCA_SP_RED, PRAZO_COBRANCA_OUTROS
)
from sqlalchemy import func, or_
from sqlalchemy.orm import joinedload

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


def calcular_qtd_substituida(numero_nf_original: str) -> float:
    """
    Calcula a quantidade total já substituída de uma NF original.

    Soma todas as substituições ativas criadas a partir da NF original.

    Args:
        numero_nf_original: Número da NF original (remessa para transportadora)

    Returns:
        float: Quantidade total já substituída
    """
    if not numero_nf_original:
        return 0.0

    substituicoes = MovimentacaoEstoque.query.filter(
        MovimentacaoEstoque.nf_remessa_origem == numero_nf_original,
        MovimentacaoEstoque.tipo_origem == 'SUBSTITUICAO',
        MovimentacaoEstoque.ativo == True
    ).all()

    return sum(float(s.qtd_movimentacao or 0) for s in substituicoes)


def obter_substituicoes_por_nf(numeros_nf: list) -> dict:
    """
    Busca todas as substituições para uma lista de NFs originais.

    Args:
        numeros_nf: Lista de números de NF originais

    Returns:
        dict: {nf_original: {'items': [substituicoes], 'total': qtd_total}}
    """
    if not numeros_nf:
        return {}

    substituicoes = MovimentacaoEstoque.query.filter(
        MovimentacaoEstoque.nf_remessa_origem.in_(numeros_nf),
        MovimentacaoEstoque.tipo_origem == 'SUBSTITUICAO',
        MovimentacaoEstoque.ativo == True
    ).all()

    resultado = {}
    for sub in substituicoes:
        nf_orig = sub.nf_remessa_origem
        if nf_orig not in resultado:
            resultado[nf_orig] = {'items': [], 'total': 0}
        resultado[nf_orig]['items'].append({
            'id': sub.id,
            'numero_nf': sub.numero_nf,
            'qtd': float(sub.qtd_movimentacao or 0),
            'cliente': sub.nome_destinatario,
            'data': sub.data_movimentacao
        })
        resultado[nf_orig]['total'] += float(sub.qtd_movimentacao or 0)

    return resultado


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
            embarque = db.session.get(Embarque,remessa.codigo_embarque) if remessa.codigo_embarque else None
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
    """Dashboard de gestao de pallet - 3 abas: NF Remessa / Vale Pallet / Retornos"""
    hoje = date.today()

    # ====== ESTATISTICAS GERAIS ======
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

    # ====== ABA 1: NF REMESSA ======
    # Todas as remessas pendentes com prazo calculado
    todas_remessas_pendentes = MovimentacaoEstoque.query.filter(
        MovimentacaoEstoque.local_movimentacao == 'PALLET',
        MovimentacaoEstoque.tipo_movimentacao == 'REMESSA',
        MovimentacaoEstoque.baixado == False,
        MovimentacaoEstoque.ativo == True
    ).order_by(MovimentacaoEstoque.data_movimentacao.asc()).all()

    remessas_vencidas = []
    remessas_prestes_vencer = []
    remessas_ok = []

    for remessa in todas_remessas_pendentes:
        prazo_dias = calcular_prazo_remessa(remessa)
        data_vencimento = remessa.data_movimentacao + timedelta(days=prazo_dias)
        dias_ate_vencimento = (data_vencimento - hoje).days

        # Adicionar prazo calculado como atributo
        remessa.prazo_dias = prazo_dias
        remessa.data_vencimento = data_vencimento
        remessa.dias_ate_vencimento = dias_ate_vencimento

        if dias_ate_vencimento < 0:
            remessas_vencidas.append(remessa)
        elif dias_ate_vencimento <= 5:
            remessas_prestes_vencer.append(remessa)
        else:
            remessas_ok.append(remessa)

    # Vendas pendentes de vinculo (SAIDA sem movimento_baixado_id)
    vendas_pendentes_vinculo = MovimentacaoEstoque.query.filter(
        MovimentacaoEstoque.local_movimentacao == 'PALLET',
        MovimentacaoEstoque.tipo_movimentacao == 'SAIDA',
        MovimentacaoEstoque.movimento_baixado_id is None,
        MovimentacaoEstoque.ativo == True
    ).order_by(MovimentacaoEstoque.data_movimentacao.desc()).all()

    # Stats da aba NF Remessa
    stats_remessa = {
        'total_pendentes': len(todas_remessas_pendentes),
        'vencidas': len(remessas_vencidas),
        'prestes_vencer': len(remessas_prestes_vencer),
        'ok': len(remessas_ok),
        'vendas_sem_vinculo': len(vendas_pendentes_vinculo)
    }

    # ====== ABA 2: VALE PALLET ======
    # Vales ativos ordenados por urgencia
    vales_lista = ValePallet.query.filter(
        ValePallet.ativo == True,
        ValePallet.resolvido == False
    ).order_by(ValePallet.data_validade.asc()).limit(50).all()

    # Stats da aba Vale Pallet
    stats_vales = {
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
            ValePallet.data_validade < hoje
        ).count(),
        'a_vencer': ValePallet.query.filter(
            ValePallet.ativo == True,
            ValePallet.resolvido == False,
            ValePallet.data_validade >= hoje,
            ValePallet.data_validade <= hoje + timedelta(days=5)
        ).count()
    }

    # ====== ABA 3: RETORNOS/DEVOLUCOES ======
    # Movimentos de entrada (retorno, devolucao, recusa)
    retornos_devolucoes = MovimentacaoEstoque.query.filter(
        MovimentacaoEstoque.local_movimentacao == 'PALLET',
        MovimentacaoEstoque.tipo_movimentacao.in_(['ENTRADA', 'DEVOLUCAO', 'RECUSA']),
        MovimentacaoEstoque.ativo == True
    ).order_by(MovimentacaoEstoque.data_movimentacao.desc()).limit(50).all()

    # Stats da aba Retornos
    inicio_mes = hoje.replace(day=1)
    stats_retornos = {
        'entradas_mes': MovimentacaoEstoque.query.filter(
            MovimentacaoEstoque.local_movimentacao == 'PALLET',
            MovimentacaoEstoque.tipo_movimentacao == 'ENTRADA',
            MovimentacaoEstoque.data_movimentacao >= inicio_mes,
            MovimentacaoEstoque.ativo == True
        ).count(),
        'devolucoes_mes': MovimentacaoEstoque.query.filter(
            MovimentacaoEstoque.local_movimentacao == 'PALLET',
            MovimentacaoEstoque.tipo_movimentacao == 'DEVOLUCAO',
            MovimentacaoEstoque.data_movimentacao >= inicio_mes,
            MovimentacaoEstoque.ativo == True
        ).count(),
        'recusas_mes': MovimentacaoEstoque.query.filter(
            MovimentacaoEstoque.local_movimentacao == 'PALLET',
            MovimentacaoEstoque.tipo_movimentacao == 'RECUSA',
            MovimentacaoEstoque.data_movimentacao >= inicio_mes,
            MovimentacaoEstoque.ativo == True
        ).count(),
        'total_retornado_mes': db.session.query(
            func.coalesce(func.sum(MovimentacaoEstoque.qtd_movimentacao), 0)
        ).filter(
            MovimentacaoEstoque.local_movimentacao == 'PALLET',
            MovimentacaoEstoque.tipo_movimentacao.in_(['ENTRADA', 'DEVOLUCAO', 'RECUSA']),
            MovimentacaoEstoque.data_movimentacao >= inicio_mes,
            MovimentacaoEstoque.ativo == True
        ).scalar() or 0
    }

    return render_template('pallet/index.html',
                           # Gerais
                           total_em_terceiros=int(total_em_terceiros),
                           saldos=saldos,
                           prazo_sp_red=PRAZO_COBRANCA_SP_RED,
                           prazo_outros=PRAZO_COBRANCA_OUTROS,
                           # Aba NF Remessa
                           todas_remessas_pendentes=todas_remessas_pendentes,
                           remessas_vencidas=remessas_vencidas,
                           remessas_prestes_vencer=remessas_prestes_vencer,
                           remessas_ok=remessas_ok,
                           vendas_pendentes_vinculo=vendas_pendentes_vinculo,
                           stats_remessa=stats_remessa,
                           # Aba Vale Pallet
                           vales_lista=vales_lista,
                           stats_vales=stats_vales,
                           # Aba Retornos
                           retornos_devolucoes=retornos_devolucoes,
                           stats_retornos=stats_retornos)


@pallet_bp.route('/movimentos')
@login_required
def listar_movimentos():
    """Lista todos os movimentos de pallet"""
    page = request.args.get('page', 1, type=int)
    filtro_tipo = request.args.get('tipo', '')
    filtro_baixado = request.args.get('baixado', '')
    filtro_destinatario = request.args.get('destinatario', '')
    # Novos filtros avancados
    filtro_nf_pallet = request.args.get('nf_pallet', '').strip()
    filtro_data_de = request.args.get('data_de', '')
    filtro_data_ate = request.args.get('data_ate', '')
    filtro_transportadora = request.args.get('transportadora', '').strip()

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

    # Filtros avancados
    if filtro_nf_pallet:
        query = query.filter(MovimentacaoEstoque.numero_nf.ilike(f'%{filtro_nf_pallet}%'))

    if filtro_data_de:
        try:
            data_de = datetime.strptime(filtro_data_de, '%Y-%m-%d').date()
            query = query.filter(MovimentacaoEstoque.data_movimentacao >= data_de)
        except ValueError:
            pass

    if filtro_data_ate:
        try:
            data_ate = datetime.strptime(filtro_data_ate, '%Y-%m-%d').date()
            query = query.filter(MovimentacaoEstoque.data_movimentacao <= data_ate)
        except ValueError:
            pass

    if filtro_transportadora:
        # Buscar por CNPJ responsavel ou nome da transportadora
        cnpj_limpo = filtro_transportadora.replace('.', '').replace('-', '').replace('/', '')
        query = query.filter(
            or_(
                MovimentacaoEstoque.cnpj_responsavel.ilike(f'%{cnpj_limpo}%'),
                MovimentacaoEstoque.nome_responsavel.ilike(f'%{filtro_transportadora}%'),
                MovimentacaoEstoque.cnpj_destinatario.ilike(f'%{cnpj_limpo}%'),
                MovimentacaoEstoque.nome_destinatario.ilike(f'%{filtro_transportadora}%')
            )
        )

    movimentos = query.order_by(MovimentacaoEstoque.criado_em.desc()).paginate(
        page=page, per_page=50, error_out=False
    )

    # Buscar informacoes de vales para cada NF de remessa
    # Retorna: {nf: {'count': N, 'qtd_total': X, 'qtd_pendente': Y, 'qtd_resolvido': Z}}
    vales_por_nf = {}
    nfs_remessa = [m.numero_nf for m in movimentos.items if m.numero_nf and m.tipo_movimentacao == 'REMESSA']
    if nfs_remessa:
        vales = ValePallet.query.filter(
            ValePallet.nf_pallet.in_(nfs_remessa),
            ValePallet.ativo == True
        ).all()

        for vale in vales:
            nf = vale.nf_pallet
            if nf not in vales_por_nf:
                vales_por_nf[nf] = {'count': 0, 'qtd_total': 0, 'qtd_pendente': 0, 'qtd_resolvido': 0}
            vales_por_nf[nf]['count'] += 1
            vales_por_nf[nf]['qtd_total'] += vale.quantidade or 0
            if vale.resolvido:
                vales_por_nf[nf]['qtd_resolvido'] += vale.quantidade or 0
            else:
                vales_por_nf[nf]['qtd_pendente'] += vale.quantidade or 0

    # Buscar transportadoras dos embarques associados
    # Retorna: {embarque_id: {'nome': X, 'cnpj': Y}}
    transportadoras_por_embarque = {}
    embarque_ids = [m.codigo_embarque for m in movimentos.items if m.codigo_embarque]
    if embarque_ids:
        embarques = Embarque.query.options(
            joinedload(Embarque.transportadora)
        ).filter(Embarque.id.in_(embarque_ids)).all()

        for emb in embarques:
            if emb.transportadora:
                transportadoras_por_embarque[emb.id] = {
                    'nome': emb.transportadora.razao_social,
                    'cnpj': emb.transportadora.cnpj
                }

    # Calcular prazo de vencimento para cada REMESSA pendente
    hoje = date.today()
    for mov in movimentos.items:
        if mov.tipo_movimentacao == 'REMESSA' and not mov.baixado and mov.data_movimentacao:
            prazo_dias = calcular_prazo_remessa(mov)
            mov.data_vencimento = mov.data_movimentacao + timedelta(days=prazo_dias)
            mov.dias_ate_vencimento = (mov.data_vencimento - hoje).days
        else:
            mov.data_vencimento = None
            mov.dias_ate_vencimento = None

    # Buscar substituições por NF original (apenas para remessas de TRANSPORTADORA)
    # Retorna: {nf_original: {'items': [...], 'total': X}}
    nfs_transportadora = [
        m.numero_nf for m in movimentos.items
        if m.numero_nf and m.tipo_movimentacao == 'REMESSA' and m.tipo_destinatario == 'TRANSPORTADORA'
    ]
    substituicoes_por_nf = obter_substituicoes_por_nf(nfs_transportadora)

    return render_template('pallet/movimentos.html',
                           movimentos=movimentos,
                           filtro_tipo=filtro_tipo,
                           filtro_baixado=filtro_baixado,
                           filtro_destinatario=filtro_destinatario,
                           filtro_nf_pallet=filtro_nf_pallet,
                           filtro_data_de=filtro_data_de,
                           filtro_data_ate=filtro_data_ate,
                           filtro_transportadora=filtro_transportadora,
                           vales_por_nf=vales_por_nf,
                           transportadoras_por_embarque=transportadoras_por_embarque,
                           substituicoes_por_nf=substituicoes_por_nf)


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
    """Registra um retorno de pallet com baixa automatica das remessas"""
    if request.method == 'POST':
        try:
            cnpj = request.form.get('cnpj_destinatario', '').replace('.', '').replace('-', '').replace('/', '')
            quantidade_retorno = int(request.form.get('quantidade', 0))
            usuario = current_user.nome if hasattr(current_user, 'nome') else str(current_user.id)

            movimento = MovimentacaoEstoque(
                cod_produto=COD_PRODUTO_PALLET,
                nome_produto=NOME_PRODUTO_PALLET,
                data_movimentacao=date.today(),
                tipo_movimentacao='ENTRADA',
                local_movimentacao='PALLET',
                qtd_movimentacao=quantidade_retorno,
                tipo_destinatario=request.form.get('tipo_destinatario'),
                cnpj_destinatario=cnpj,
                nome_destinatario=request.form.get('nome_destinatario'),
                numero_nf=request.form.get('numero_nf'),
                observacao=request.form.get('observacao'),
                tipo_origem='MANUAL',
                criado_por=usuario
            )
            db.session.add(movimento)
            db.session.flush()  # Para obter o ID do movimento

            # =====================================================================
            # BAIXA AUTOMATICA: Buscar remessas pendentes do mesmo CNPJ e baixar
            # =====================================================================
            baixas_realizadas = 0
            quantidade_restante = quantidade_retorno

            if cnpj and quantidade_restante > 0:
                # Buscar remessas pendentes para o mesmo CNPJ (FIFO - mais antigas primeiro)
                remessas_pendentes = MovimentacaoEstoque.query.filter(
                    MovimentacaoEstoque.local_movimentacao == 'PALLET',
                    MovimentacaoEstoque.tipo_movimentacao == 'REMESSA',
                    MovimentacaoEstoque.baixado == False,
                    MovimentacaoEstoque.ativo == True,
                    MovimentacaoEstoque.cnpj_destinatario == cnpj
                ).order_by(MovimentacaoEstoque.data_movimentacao.asc()).all()

                for remessa in remessas_pendentes:
                    if quantidade_restante <= 0:
                        break

                    qtd_remessa = int(remessa.qtd_movimentacao or 0)

                    if qtd_remessa <= quantidade_restante:
                        # Baixa total da remessa
                        remessa.baixado = True
                        remessa.baixado_em = datetime.utcnow()
                        remessa.baixado_por = usuario
                        remessa.movimento_baixado_id = movimento.id
                        remessa.observacao = (remessa.observacao or '') + f'\n[BAIXA AUTOMATICA] Retorno registrado - {quantidade_retorno} pallets'
                        quantidade_restante -= qtd_remessa
                        baixas_realizadas += 1

            db.session.commit()

            # Mensagem de sucesso com detalhes da baixa
            if baixas_realizadas > 0:
                flash(f'Retorno de {quantidade_retorno} pallets registrado com sucesso! {baixas_realizadas} remessa(s) baixada(s) automaticamente.', 'success')
            else:
                flash(f'Retorno de {quantidade_retorno} pallets registrado com sucesso!', 'success')

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


@pallet_bp.route('/desfazer-baixa/<int:movimento_id>', methods=['POST'])
@login_required
def desfazer_baixa(movimento_id):
    """Desfaz a baixa de um movimento de pallet"""
    movimento = MovimentacaoEstoque.query.get_or_404(movimento_id)

    if movimento.local_movimentacao != 'PALLET':
        flash('Este movimento nao e de pallet!', 'warning')
        return redirect(url_for('pallet.listar_movimentos'))

    if not movimento.baixado:
        flash('Este movimento nao esta baixado!', 'warning')
        return redirect(url_for('pallet.listar_movimentos'))

    # Bloquear desfazer baixa se houver vales vinculados (REMESSA)
    if movimento.tipo_movimentacao == 'REMESSA' and movimento.numero_nf:
        vales_vinculados = ValePallet.query.filter(
            ValePallet.nf_pallet == movimento.numero_nf,
            ValePallet.ativo == True
        ).count()
        if vales_vinculados > 0:
            flash(f'Nao e possivel desfazer a baixa: existem {vales_vinculados} vale(s) vinculado(s) a esta NF! '
                  f'Para desfazer, primeiro exclua ou desvincule os vales.', 'danger')
            return redirect(url_for('pallet.listar_movimentos'))

    try:
        # Registrar quem e quando desfez
        usuario = current_user.nome if hasattr(current_user, 'nome') else str(current_user.id)
        obs_desfazer = f'\n[BAIXA DESFEITA em {datetime.utcnow().strftime("%d/%m/%Y %H:%M")} por {usuario}]'

        # Guardar info anterior na observacao
        if movimento.baixado_em:
            obs_desfazer += f' (estava baixado desde {movimento.baixado_em.strftime("%d/%m/%Y")} por {movimento.baixado_por})'

        movimento.observacao = (movimento.observacao or '') + obs_desfazer

        # Limpar campos de baixa
        movimento.baixado = False
        movimento.baixado_em = None
        movimento.baixado_por = None
        movimento.movimento_baixado_id = None

        db.session.commit()
        flash(f'Baixa do movimento #{movimento.id} desfeita com sucesso!', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao desfazer baixa: {str(e)}', 'danger')

    return redirect(url_for('pallet.listar_movimentos'))


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


@pallet_bp.route('/api/nfs-pendentes')
@login_required
def api_nfs_pendentes():
    """Busca NFs de remessa pendentes para criar vale pallet"""
    termo = request.args.get('q', '')

    # Buscar remessas (tipo REMESSA) não baixadas
    query = MovimentacaoEstoque.query.filter(
        MovimentacaoEstoque.local_movimentacao == 'PALLET',
        MovimentacaoEstoque.tipo_movimentacao == 'REMESSA',
        MovimentacaoEstoque.baixado == False,
        MovimentacaoEstoque.ativo == True,
        MovimentacaoEstoque.numero_nf.isnot(None),
        MovimentacaoEstoque.numero_nf != ''
    )

    # Filtrar por número da NF se informado
    if termo:
        query = query.filter(MovimentacaoEstoque.numero_nf.ilike(f'%{termo}%'))

    # Ordenar por data mais recente
    query = query.order_by(MovimentacaoEstoque.data_movimentacao.desc())
    remessas = query.limit(20).all()

    resultados = []
    for r in remessas:
        # Calcular saldo (quantidade - abatida)
        saldo = int(r.qtd_movimentacao or 0) - int(r.qtd_abatida or 0)
        if saldo <= 0:
            continue

        resultados.append({
            'numero_nf': r.numero_nf,
            'destinatario': r.nome_destinatario or r.cnpj_destinatario or '-',
            'data': r.data_movimentacao.strftime('%d/%m/%Y') if r.data_movimentacao else '-',
            'saldo': saldo,
            'cnpj_transportadora': r.cnpj_destinatario if r.tipo_destinatario == 'TRANSPORTADORA' else None,
            'nome_transportadora': r.nome_destinatario if r.tipo_destinatario == 'TRANSPORTADORA' else None
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
                vale.valor_resolucao = converter_valor_brasileiro(valor)
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
                vale.valor_resolucao = converter_valor_brasileiro(valor)
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


# ========== SUBSTITUICAO DE NF ==========

@pallet_bp.route('/substituicao', methods=['GET'])
@login_required
def listar_substituicoes():
    """Lista remessas disponiveis para substituicao (com saldo disponível)"""
    # Buscar remessas pendentes de transportadoras
    remessas_raw = MovimentacaoEstoque.query.filter(
        MovimentacaoEstoque.local_movimentacao == 'PALLET',
        MovimentacaoEstoque.tipo_movimentacao == 'REMESSA',
        MovimentacaoEstoque.tipo_destinatario == 'TRANSPORTADORA',
        MovimentacaoEstoque.baixado == False,
        MovimentacaoEstoque.ativo == True
    ).order_by(MovimentacaoEstoque.data_movimentacao.desc()).all()

    # Calcular saldo disponível para cada remessa e filtrar totalmente substituídas
    remessas = []
    for rem in remessas_raw:
        qtd_substituida = calcular_qtd_substituida(rem.numero_nf)
        saldo_disponivel = float(rem.qtd_movimentacao or 0) - qtd_substituida

        # Só incluir se ainda houver saldo disponível
        if saldo_disponivel > 0:
            # Adicionar atributos temporários para o template
            rem.qtd_substituida = qtd_substituida
            rem.saldo_disponivel = saldo_disponivel
            remessas.append(rem)

    return render_template('pallet/substituicao_lista.html', remessas=remessas)


@pallet_bp.route('/substituicao/<int:remessa_id>', methods=['GET', 'POST'])
@login_required
def registrar_substituicao(remessa_id):
    """
    Registra uma substituicao de NF de pallet.

    Substituicao: NF emitida para transportadora, mas cliente precisa de NF especifica.
    A nova NF do cliente "consome" parte da NF da transportadora.
    A responsabilidade PERMANECE com a transportadora.
    """
    remessa_origem = MovimentacaoEstoque.query.get_or_404(remessa_id)

    # Validar que e uma remessa de transportadora pendente
    if remessa_origem.tipo_movimentacao != 'REMESSA' or remessa_origem.local_movimentacao != 'PALLET':
        flash('Este movimento nao e uma remessa de pallet!', 'warning')
        return redirect(url_for('pallet.listar_substituicoes'))

    if remessa_origem.tipo_destinatario != 'TRANSPORTADORA':
        flash('Substituicao so se aplica a remessas para transportadora!', 'warning')
        return redirect(url_for('pallet.listar_substituicoes'))

    if remessa_origem.baixado:
        flash('Esta remessa ja foi baixada!', 'warning')
        return redirect(url_for('pallet.listar_substituicoes'))

    # Calcular saldo disponível para substituição
    qtd_ja_substituida = calcular_qtd_substituida(remessa_origem.numero_nf)
    saldo_disponivel = float(remessa_origem.qtd_movimentacao or 0) - qtd_ja_substituida

    # Validar se ainda há saldo disponível
    if saldo_disponivel <= 0:
        flash('Esta remessa já foi totalmente substituída!', 'warning')
        return redirect(url_for('pallet.listar_substituicoes'))

    if request.method == 'POST':
        try:
            quantidade = int(request.form.get('quantidade', 0))

            # Validar quantidade
            if quantidade <= 0:
                flash('Quantidade deve ser maior que zero!', 'warning')
                return redirect(url_for('pallet.registrar_substituicao', remessa_id=remessa_id))

            # Validar contra o SALDO DISPONÍVEL (não a quantidade original)
            if quantidade > saldo_disponivel:
                flash(f'Saldo disponível para substituição: {int(saldo_disponivel)} pallets (de {int(remessa_origem.qtd_movimentacao)} originais, {int(qtd_ja_substituida)} já substituídos)', 'warning')
                return redirect(url_for('pallet.registrar_substituicao', remessa_id=remessa_id))

            # Criar nova remessa para o CLIENTE
            # nf_remessa_origem = NF original da transportadora
            # cnpj_responsavel = CNPJ da transportadora (mantem responsabilidade)
            nova_remessa = MovimentacaoEstoque(
                cod_produto=COD_PRODUTO_PALLET,
                nome_produto=NOME_PRODUTO_PALLET,
                data_movimentacao=date.today(),
                tipo_movimentacao='REMESSA',
                local_movimentacao='PALLET',
                qtd_movimentacao=quantidade,
                tipo_destinatario='CLIENTE',
                cnpj_destinatario=request.form.get('cnpj_cliente', '').replace('.', '').replace('-', '').replace('/', ''),
                nome_destinatario=request.form.get('nome_cliente'),
                numero_nf=request.form.get('numero_nf'),
                # Campos de substituicao
                nf_remessa_origem=remessa_origem.numero_nf,
                cnpj_responsavel=remessa_origem.cnpj_destinatario,  # Transportadora continua responsavel
                nome_responsavel=remessa_origem.nome_destinatario,
                codigo_embarque=remessa_origem.codigo_embarque,
                observacao=f'Substituicao da NF {remessa_origem.numero_nf} (Transp: {remessa_origem.nome_destinatario})',
                tipo_origem='SUBSTITUICAO',
                baixado=False,
                criado_por=current_user.nome if hasattr(current_user, 'nome') else str(current_user.id)
            )
            db.session.add(nova_remessa)

            # Verificar se após esta substituição o saldo ficará zerado
            # saldo_disponivel já foi calculado antes do POST
            saldo_apos_substituicao = saldo_disponivel - quantidade

            if saldo_apos_substituicao <= 0:
                # Substituição total: baixar a remessa original
                remessa_origem.baixado = True
                remessa_origem.baixado_em = datetime.utcnow()
                remessa_origem.baixado_por = current_user.nome if hasattr(current_user, 'nome') else str(current_user.id)
                remessa_origem.observacao = (remessa_origem.observacao or '') + f'\n[SUBSTITUICAO TOTAL] NF cliente: {request.form.get("numero_nf")}'
            else:
                # Substituição parcial - ainda há saldo disponível
                remessa_origem.observacao = (remessa_origem.observacao or '') + f'\n[SUBSTITUICAO PARCIAL] {quantidade} pallets -> NF cliente: {request.form.get("numero_nf")} (saldo restante: {int(saldo_apos_substituicao)})'

            db.session.commit()

            flash(f'Substituicao registrada! NF {request.form.get("numero_nf")} para cliente vinculada a NF {remessa_origem.numero_nf} da transportadora.', 'success')
            return redirect(url_for('pallet.listar_movimentos'))

        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao registrar substituicao: {str(e)}', 'danger')

    # Passar saldo para o template
    return render_template('pallet/substituicao.html',
                          remessa=remessa_origem,
                          qtd_ja_substituida=qtd_ja_substituida,
                          saldo_disponivel=saldo_disponivel)


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

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, send_from_directory, send_file, jsonify, current_app
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from app.utils.timezone import agora_utc_naive
import os
import time
import tempfile
from itertools import chain
from sqlalchemy import func
from sqlalchemy.orm import joinedload
import logging


import re

from app import db

# 🔒 Importar decoradores de permissão
from app.utils.auth_decorators import require_monitoramento_geral, allow_vendedor_own_data, check_vendedor_permission, get_vendedor_filter_query

from app.separacao.models import Separacao
from app.monitoramento.models import (
    EntregaMonitorada,
    EventoEntrega,
    CustoExtraEntrega,
    RegistroLogEntrega,
    AgendamentoEntrega,
    ComentarioNF,
    ArquivoEntrega
)
from app.monitoramento.forms import (
    LogEntregaForm,
    EventoEntregaForm,
    CustoExtraForm,
    AgendamentoEntregaForm,
    FormComentarioNF,
    ExportarMonitoramentoForm
)

from app.financeiro.models import PendenciaFinanceiraNF
from app.faturamento.models import RelatorioFaturamentoImportado, FaturamentoProduto
from app.carteira.models import CarteiraPrincipal
from app.embarques.models import Embarque, EmbarqueItem

from app.cadastros_agendamento.models import ContatoAgendamento

# Devolucoes - para exibir links no monitoramento
from app.devolucao.models import NFDevolucao, OcorrenciaDevolucao

from app.utils.sincronizar_todas_entregas import sincronizar_todas_entregas
from app.pedidos.models import Pedido  # ✅ ADICIONADO: Para controle de status NF no CD

# 🌐 Importar sistema de arquivos S3
from app.utils.file_storage import get_file_storage

logger = logging.getLogger(__name__)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, '..', '..', 'uploads', 'entregas')
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ------------------------------------
# Cache de contatos de agendamento (TTL 60s)
# Evita ContatoAgendamento.query.all() (~4000 regs) em cada request
# ------------------------------------
_contatos_cache = None
_contatos_cache_ts = 0
_CONTATOS_TTL = 60


def _get_contatos_agendamento():
    """Retorna dict {cnpj: {forma, contato, observacao}} com CNPJs originais e limpos. Cache 60s.

    IMPORTANTE: Armazena dicts simples (não instâncias ORM) para evitar
    DetachedInstanceError quando o cache sobrevive ao request que o populou.
    """
    global _contatos_cache, _contatos_cache_ts
    if _contatos_cache is not None and (time.time() - _contatos_cache_ts) < _CONTATOS_TTL:
        return _contatos_cache
    contatos = {}
    for c in ContatoAgendamento.query.all():
        dados = {
            'forma': c.forma,
            'contato': c.contato,
            'observacao': c.observacao,
            'nao_aceita_nf_pallet': c.nao_aceita_nf_pallet,
            'horario_recebimento_de': c.horario_recebimento_de.strftime('%H:%M') if c.horario_recebimento_de else None,
            'horario_recebimento_ate': c.horario_recebimento_ate.strftime('%H:%M') if c.horario_recebimento_ate else None,
            'observacoes_recebimento': c.observacoes_recebimento,
        }
        contatos[c.cnpj] = dados
        if c.cnpj:
            cnpj_limpo = c.cnpj.replace('.', '').replace('-', '').replace('/', '')
            contatos[cnpj_limpo] = dados
    _contatos_cache = contatos
    _contatos_cache_ts = time.time()
    return contatos


def _get_cnpjs_que_precisam_agendamento():
    """Retorna set de CNPJs (original + limpo) que precisam de agendamento. Derivado do cache."""
    contatos = _get_contatos_agendamento()
    cnpjs = set()
    for cnpj, contato in contatos.items():
        forma = contato.get('forma', '')
        if forma and forma != 'SEM AGENDAMENTO':
            cnpjs.add(cnpj)
    return cnpjs


def get_file_icon(filename):
    """Retorna ícone baseado na extensão do arquivo"""
    ext = filename.split('.')[-1].lower() if '.' in filename else ''
    if ext in ['pdf']:
        return '📄'
    elif ext in ['jpg', 'jpeg', 'png']:
        return '🖼️'
    elif ext in ['doc', 'docx']:
        return '📝'
    elif ext in ['xls', 'xlsx']:
        return '📊'
    else:
        return '📁'

# Função de migração removida - não há arquivos locais para migrar

monitoramento_bp = Blueprint('monitoramento', __name__, url_prefix='/monitoramento')

def processar_nf_cd_pedido(entrega_id):
    """
    ✅ FUNÇÃO ULTRA SIMPLIFICADA: Processa quando uma NF volta para o CD
    
    Implementa o item 2-d do processo_completo.md:
    - Busca o pedido diretamente pela NF (coluna "nf" na tabela pedidos)
    - Reseta o pedido para permitir nova cotação
    """
    try:
        entrega = db.session.get(EntregaMonitorada,entrega_id) if entrega_id else None
        if not entrega:
            return False, "Entrega não encontrada"
        
        print(f"[DEBUG] 🔍 Processando NF no CD para NF {entrega.numero_nf}")
        
        # ✅ MÉTODO ULTRA SIMPLIFICADO: Busca pedido diretamente pela NF
        pedido = db.session.query(Pedido).filter_by(nf=entrega.numero_nf).first()
        
        if not pedido:
            msg_erro = f"Pedido não encontrado para NF {entrega.numero_nf}"
            print(f"[DEBUG] ❌ {msg_erro}")
            return True, msg_erro
        
        # ✅ PEDIDO ENCONTRADO: Marca como "NF no CD" sem apagar a NF
        print(f"[DEBUG] ✅ Pedido {pedido.num_pedido} encontrado diretamente pela NF {entrega.numero_nf}")
        print(f"[DEBUG] 📦 Marcando pedido {pedido.num_pedido} como 'NF no CD'...")
        
        # ✅ NOVO: Marca como NF no CD sem apagar a NF (preserva histórico)
        if pedido.separacao_lote_id:
            update_data = {
                'nf_cd': True,
                'data_embarque': None,
                # ✅ CORREÇÃO: NÃO apagar expedição - manter data planejada
                # 'expedicao': None  # ❌ REMOVIDO
            }

            if entrega.data_agenda:
                update_data['agendamento'] = entrega.data_agenda

            # ✅ CORREÇÃO: Buscar protocolo em AgendamentoEntrega mais recente
            from app.monitoramento.models import AgendamentoEntrega
            agendamento_recente = AgendamentoEntrega.query.filter_by(
                entrega_id=entrega.id
            ).order_by(AgendamentoEntrega.criado_em.desc()).first()

            if agendamento_recente:
                update_data['protocolo'] = agendamento_recente.protocolo_agendamento
                update_data['agendamento_confirmado'] = (agendamento_recente.status == 'confirmado')

            Separacao.query.filter_by(
                separacao_lote_id=pedido.separacao_lote_id
            ).update(update_data)

        # NF é preservada para manter histórico
        # Status será recalculado automaticamente pelo trigger como "NF no CD"
        
        db.session.commit()
        
        sucesso_msg = f"Pedido {pedido.num_pedido} marcado como 'NF no CD' (NF: {entrega.numero_nf} preservada)"
        print(f"[DEBUG] ✅ {sucesso_msg}")
        return True, sucesso_msg
        
    except Exception as e:
        db.session.rollback()
        error_msg = f"Erro ao processar NF no CD: {str(e)}"
        print(f"[DEBUG] ❌ {error_msg}")
        return False, error_msg

@monitoramento_bp.route('/<int:id>', methods=['GET'])
@login_required
@allow_vendedor_own_data()  # 🔒 VENDEDORES: Apenas dados próprios
def visualizar_entrega(id):
    entrega = EntregaMonitorada.query.get_or_404(id)
    
    # 🔒 VERIFICAÇÃO ESPECÍFICA PARA VENDEDORES
    if current_user.perfil == 'vendedor':
        if not check_vendedor_permission(vendedor_nome=entrega.vendedor, numero_nf=entrega.numero_nf):
            flash('Acesso negado. Você só pode visualizar entregas dos seus clientes.', 'danger')
            return redirect(url_for('monitoramento.listar_entregas'))

    # Instancie os forms só para renderizar na página:
    form_log = LogEntregaForm()
    form_evento = EventoEntregaForm()
    form_custo = CustoExtraForm()
    form_agendamento = AgendamentoEntregaForm()
    form_comentario = FormComentarioNF()  # para comentários

    # Preencher defaults no form de agendamento (se houver contato prévio):
    contato_prev = ContatoAgendamento.query.filter_by(cnpj=entrega.cnpj_cliente).first()
    if contato_prev:
        form_agendamento.forma_agendamento.data = contato_prev.forma
        form_agendamento.contato_agendamento.data = contato_prev.contato
        form_agendamento.observacao.data = contato_prev.observacao

    # Buscar comentários (sem resposta)
    comentarios = entrega.comentarios \
                         .filter_by(resposta_a_id=None) \
                         .order_by(ComentarioNF.criado_em.desc()) \
                         .all()

    feedback = session.pop('feedback', None)

    # Buscar ocorrências de devolução vinculadas a esta entrega
    ocorrencias_devolucao = []
    if entrega.teve_devolucao:
        # Buscar NFDs vinculadas a esta entrega de duas formas:
        # 1. Por entrega_monitorada_id (vinculação direta)
        # 2. Por numero_nf_venda (vinculação por número da NF)
        nfds = NFDevolucao.query.filter(
            db.or_(
                NFDevolucao.entrega_monitorada_id == entrega.id,
                NFDevolucao.numero_nf_venda == entrega.numero_nf
            )
        ).all()

        for nfd in nfds:
            # Buscar ocorrência vinculada à NFD
            ocorrencia = OcorrenciaDevolucao.query.filter_by(
                nf_devolucao_id=nfd.id,
                ativo=True
            ).first()

            if ocorrencia:
                ocorrencias_devolucao.append({
                    'id': ocorrencia.id,
                    'numero_ocorrencia': ocorrencia.numero_ocorrencia,
                    'numero_nfd': nfd.numero_nfd,
                    'status': ocorrencia.status,
                    'motivo': nfd.motivo,
                    'destino': ocorrencia.destino
                })

    # Lookup CarVia (apenas para usuarios com acesso CarVia)
    # Carrega CarviaFrete vinculado por numero_nf (match exato CSV) e
    # CEs existentes para exibicao readonly na aba Custos.
    tem_frete_carvia = False
    frete_carvia = None
    custos_entrega_carvia = []

    if getattr(current_user, 'sistema_carvia', False):
        try:
            from app.carvia.models import CarviaFrete, CarviaCustoEntrega

            frete_carvia = (
                CarviaFrete.query
                .filter(
                    db.or_(
                        CarviaFrete.numeros_nfs == entrega.numero_nf,
                        CarviaFrete.numeros_nfs.like(f"{entrega.numero_nf},%"),
                        CarviaFrete.numeros_nfs.like(f"%,{entrega.numero_nf},%"),
                        CarviaFrete.numeros_nfs.like(f"%,{entrega.numero_nf}"),
                    ),
                    CarviaFrete.status != 'CANCELADO',
                )
                .order_by(CarviaFrete.criado_em.desc())
                .first()
            )
            tem_frete_carvia = frete_carvia is not None

            if frete_carvia:
                custos_entrega_carvia = (
                    CarviaCustoEntrega.query
                    .filter_by(frete_id=frete_carvia.id)
                    .filter(CarviaCustoEntrega.status != 'CANCELADO')
                    .order_by(CarviaCustoEntrega.data_custo.desc())
                    .all()
                )
        except Exception as e_carvia:
            print(f"[AVISO] Lookup CarVia visualizar_entrega falhou: {e_carvia}")

    return render_template(
        'monitoramento/visualizar_entrega.html',
        entrega=entrega,
        form_log=form_log,
        form_evento=form_evento,
        form_custo=form_custo,
        form_agendamento=form_agendamento,
        form=form_comentario,
        comentarios=comentarios,
        feedback=feedback,
        ocorrencias_devolucao=ocorrencias_devolucao,
        contato_agendamento=contato_prev,
        tem_frete_carvia=tem_frete_carvia,
        frete_carvia=frete_carvia,
        custos_entrega_carvia=custos_entrega_carvia,
    )

@monitoramento_bp.route('/<int:id>/adicionar_log', methods=['POST'])
@login_required
@require_monitoramento_geral()  # 🔒 BLOQUEADO para vendedores
def adicionar_log(id):
    entrega = EntregaMonitorada.query.get_or_404(id)
    form_log = LogEntregaForm()

    if form_log.validate_on_submit():
        log = RegistroLogEntrega(
            entrega_id=entrega.id,
            autor=current_user.nome,
            descricao=form_log.descricao.data,
            tipo=form_log.tipo.data,
            lembrete_para=form_log.lembrete_para.data,
            data_hora=agora_utc_naive(),
        )
        db.session.add(log)
        db.session.commit()
        session['feedback'] = 'log'


    else:
        print("DEBUG form_log.errors =", form_log.errors)  # <---
        flash('Erro ao validar Log. Verifique o preenchimento.', 'danger')


    return redirect(url_for('monitoramento.visualizar_entrega', id=entrega.id))

@monitoramento_bp.route('/<int:id>/adicionar_evento', methods=['POST'])
@login_required
@require_monitoramento_geral()  # 🔒 BLOQUEADO para vendedores
def adicionar_evento(id):
    entrega = EntregaMonitorada.query.get_or_404(id)
    form_evento = EventoEntregaForm()

    if form_evento.validate_on_submit():
        # Monta datetime de chegada/saida se existirem
        chegada = None
        saida = None
        if form_evento.data_hora_chegada.data and form_evento.hora_chegada.data:
            chegada = datetime.combine(form_evento.data_hora_chegada.data, form_evento.hora_chegada.data)
        if form_evento.data_hora_saida.data and form_evento.hora_saida.data:
            saida = datetime.combine(form_evento.data_hora_saida.data, form_evento.hora_saida.data)

        # Cria o evento normalmente
        evento = EventoEntrega(
            entrega_id=entrega.id,
            data_hora_chegada=chegada,
            data_hora_saida=saida,
            motorista=form_evento.motorista.data,
            tipo_evento=form_evento.tipo_evento.data,
            observacao=form_evento.observacao.data,
            autor=current_user.nome,
            criado_em=agora_utc_naive(),
        )
        db.session.add(evento)

        # ✅ IMPLEMENTAÇÃO APRIMORADA DO ITEM 2-d: NF no CD
        if form_evento.tipo_evento.data == "NF no CD":
            entrega.nf_cd = True
            entrega.entregue = False
            entrega.status_finalizacao = None
            entrega.data_embarque = None
            entrega.data_entrega_prevista = None
            # ✅ CORREÇÃO: NÃO apagar data_agenda - manter agendamento quando NF volta ao CD
            # entrega.data_agenda = None  # ❌ REMOVIDO
            entrega.data_hora_entrega_realizada = None
            entrega.finalizado_por = None
            entrega.finalizado_em = None

            # ✅ NOVA FUNCIONALIDADE: Atualiza status do pedido correspondente
            try:
                sucesso, resultado = processar_nf_cd_pedido(entrega.id)
                if sucesso:
                    flash(f"📦 {resultado}", "info")
                else:
                    flash(f"⚠️ Erro ao processar pedido: {resultado}", "warning")
            except Exception as e:
                print(f"Erro ao processar NF no CD: {e}")

        db.session.commit()
        session['feedback'] = 'evento'
    else:
        flash('Erro ao validar Evento. Verifique o preenchimento.', 'danger')

    return redirect(url_for('monitoramento.visualizar_entrega', id=entrega.id))


@monitoramento_bp.route('/<int:id>/adicionar_custo', methods=['POST'])
@login_required
def adicionar_custo(id):
    entrega = EntregaMonitorada.query.get_or_404(id)
    form_custo = CustoExtraForm()

    if form_custo.validate_on_submit():
        custo = CustoExtraEntrega(
            entrega_id=entrega.id,
            tipo=form_custo.tipo.data,
            valor=form_custo.valor.data,
            motivo=form_custo.motivo.data,
            autor=current_user.nome,
            criado_em=agora_utc_naive(),
        )
        db.session.add(custo)
        db.session.commit()
        session['feedback'] = 'custo'
    else:
        flash('Erro ao validar Custo Extra.', 'danger')

    return redirect(url_for('monitoramento.visualizar_entrega', id=entrega.id))

@monitoramento_bp.route('/<int:id>/adicionar_agendamento', methods=['POST'])
@login_required
def adicionar_agendamento(id):
    entrega = EntregaMonitorada.query.get_or_404(id)
    form_agendamento = AgendamentoEntregaForm()

    if form_agendamento.validate_on_submit():
        # ✅ VALIDAÇÃO SIMPLIFICADA: Apenas campos obrigatórios
        forma_agendamento = form_agendamento.forma_agendamento.data
        data_agendada = form_agendamento.data_agendada.data
        
        # ✅ BLOQUEIO SIMPLES: Forma de agendamento obrigatória
        if not forma_agendamento or forma_agendamento.strip() == '':
            flash('⚠️ É obrigatório informar a forma de agendamento!', 'danger')
            return redirect(url_for('monitoramento.visualizar_entrega', id=entrega.id))
        
        # ✅ BLOQUEIO SIMPLES: Data obrigatória
        if not data_agendada:
            flash('⚠️ É obrigatório informar a data do agendamento!', 'danger')
            return redirect(url_for('monitoramento.visualizar_entrega', id=entrega.id))
        
        # ✅ Determina o status baseado no checkbox
        status = 'confirmado' if form_agendamento.criar_confirmado.data else 'aguardando'
        
        # ✅ CRIAR AGENDAMENTO (protocolo é opcional)
        ag = AgendamentoEntrega(
            entrega_id=entrega.id,
            data_agendada=data_agendada,
            hora_agendada=form_agendamento.hora_agendada.data,
            forma_agendamento=forma_agendamento,
            contato_agendamento=form_agendamento.contato_agendamento.data,
            protocolo_agendamento=form_agendamento.protocolo_agendamento.data,  # Opcional
            motivo=form_agendamento.motivo.data,
            observacao=form_agendamento.observacao.data,
            autor=current_user.nome,
            status=status
        )
        
        # Se criado já confirmado, preenche campos de confirmação
        if status == 'confirmado':
            ag.confirmado_por = current_user.nome
            ag.confirmado_em = agora_utc_naive()
        
        db.session.add(ag)

        # ✅ Atualiza campos da entrega
        entrega.data_agenda = data_agendada
        entrega.data_entrega_prevista = data_agendada
        db.session.commit()

        # ✅ SINCRONIZAÇÃO BIDIRECIONAL: Propagar para Separacao e EmbarqueItem
        from app.pedidos.services.sincronizacao_agendamento_service import SincronizadorAgendamentoService

        try:
            sincronizador = SincronizadorAgendamentoService(usuario=current_user.nome)
            resultado_sync = sincronizador.sincronizar_desde_agendamento_entrega(
                entrega_id=entrega.id,
                agendamento_id=ag.id
            )

            if resultado_sync['success']:
                tabelas = ', '.join(resultado_sync.get('tabelas_atualizadas', []))
                if tabelas:
                    flash(f"✅ Agendamento criado e sincronizado com: {tabelas}", 'success')
                else:
                    flash('✅ Agendamento criado com sucesso!', 'success')
            else:
                flash(f"✅ Agendamento criado. Aviso na sincronização: {resultado_sync.get('error', '')}", 'warning')
        except Exception as e:
            flash(f"✅ Agendamento criado. Erro na sincronização: {str(e)}", 'warning')
        
        session['feedback'] = 'agendamento'
    else:
        flash('❌ Erro ao validar agendamento. Verifique os campos obrigatórios.', 'danger')

    return redirect(url_for('monitoramento.visualizar_entrega', id=entrega.id))


@monitoramento_bp.route('/confirmar_agendamento/<int:agendamento_id>', methods=['POST'])
@login_required
def confirmar_agendamento(agendamento_id):
    agendamento = AgendamentoEntrega.query.get_or_404(agendamento_id)
    
    # Só pode confirmar se estiver aguardando
    if agendamento.status != 'aguardando':
        flash('Este agendamento já foi confirmado.', 'warning')
        return redirect(request.referrer or url_for('monitoramento.listar_entregas'))
    
    # Atualiza para confirmado
    agendamento.status = 'confirmado'
    agendamento.confirmado_por = current_user.nome
    agendamento.confirmado_em = agora_utc_naive()

    # Pega observações do POST se houver
    observacoes = request.form.get('observacoes_confirmacao', '').strip()
    if observacoes:
        agendamento.observacoes_confirmacao = observacoes

    db.session.commit()

    # ✅ SINCRONIZAÇÃO BIDIRECIONAL: Propagar confirmação para Separacao e EmbarqueItem
    from app.pedidos.services.sincronizacao_agendamento_service import SincronizadorAgendamentoService

    try:
        sincronizador = SincronizadorAgendamentoService(usuario=current_user.nome)
        resultado_sync = sincronizador.sincronizar_desde_agendamento_entrega(
            entrega_id=agendamento.entrega_id,
            agendamento_id=agendamento.id
        )

        if resultado_sync['success']:
            tabelas = ', '.join(resultado_sync.get('tabelas_atualizadas', []))
            if tabelas:
                flash(f'✅ Agendamento confirmado e sincronizado com: {tabelas}', 'success')
            else:
                flash('✅ Agendamento confirmado com sucesso!', 'success')
        else:
            flash(f"✅ Agendamento confirmado. Aviso na sincronização: {resultado_sync.get('error', '')}", 'warning')
    except Exception as e:
        flash(f'✅ Agendamento confirmado. Erro na sincronização: {str(e)}', 'warning')

    return redirect(request.referrer or url_for('monitoramento.listar_entregas'))


@monitoramento_bp.route('/<int:id>/historico_agendamentos')
@login_required
def historico_agendamentos(id):
    entrega = EntregaMonitorada.query.get_or_404(id)
    agendamentos = AgendamentoEntrega.query.filter_by(entrega_id=id).order_by(AgendamentoEntrega.criado_em.desc()).all()
    
    agendamentos_data = []
    for ag in agendamentos:
        agendamentos_data.append({
            'id': ag.id,
            'data_agendada': ag.data_agendada.strftime('%d/%m/%Y') if ag.data_agendada else '',
            'hora_agendada': ag.hora_agendada.strftime('%H:%M') if ag.hora_agendada else '',
            'forma_agendamento': ag.forma_agendamento or '',
            'protocolo_agendamento': ag.protocolo_agendamento or '',
            'motivo': ag.motivo or '',
            'observacao': ag.observacao or '',
            'status': ag.status or 'aguardando',
            'autor': ag.autor or '',
            'criado_em': ag.criado_em.strftime('%d/%m/%Y %H:%M') if ag.criado_em else '',
            'confirmado_por': ag.confirmado_por or '',
            'confirmado_em': ag.confirmado_em.strftime('%d/%m/%Y %H:%M') if ag.confirmado_em else '',
            'observacoes_confirmacao': ag.observacoes_confirmacao or ''
        })
    
    return jsonify({'agendamentos': agendamentos_data})


@monitoramento_bp.route('/<int:id>/finalizar', methods=['POST'])
@login_required
def finalizar_entrega(id):
    entrega = EntregaMonitorada.query.get_or_404(id)

    data_str = request.form.get('data_hora_entrega')
    status_finalizacao = request.form.get('status_finalizacao')
    nova_nf = request.form.get('nova_nf')

    # Validação clara para não aceitar entrega sem data se não houver status especial
    if not status_finalizacao and not data_str:
        flash('Data e hora obrigatórias para finalizar entrega!', 'danger')
        return redirect(url_for('monitoramento.visualizar_entrega', id=id))

    # Cancelando qualquer status anterior antes de aplicar um novo
    entrega.status_finalizacao = None
    entrega.entregue = False
    entrega.data_hora_entrega_realizada = None
    entrega.nova_nf = None

    # ✅ CORREÇÃO: Resetar nf_cd ao finalizar entrega
    # Se a entrega está sendo finalizada, ela não está mais "no CD"
    if entrega.nf_cd:
        entrega.nf_cd = False
        # Sincronizar com Separacao
        if entrega.separacao_lote_id:
            Separacao.query.filter_by(
                separacao_lote_id=entrega.separacao_lote_id
            ).update({'nf_cd': False})
            print(f"[FINALIZAR] 🔄 Separacao nf_cd=False para lote {entrega.separacao_lote_id}")
        elif entrega.numero_nf:
            Separacao.query.filter_by(
                numero_nf=entrega.numero_nf
            ).update({'nf_cd': False})
            print(f"[FINALIZAR] 🔄 Separacao nf_cd=False para NF {entrega.numero_nf}")

    descricao_log = ""

    if status_finalizacao in ["Troca de NF", "Cancelada", "Devolvida", "Sinistro"]:
        entrega.status_finalizacao = status_finalizacao
        descricao_log = f"Entrega finalizada com status: {status_finalizacao}"

        if status_finalizacao == "Troca de NF":
            if not nova_nf:
                flash('Nova NF obrigatória para Troca de NF!', 'danger')
                return redirect(url_for('monitoramento.visualizar_entrega', id=id))

            entrega.nova_nf = nova_nf
            nova_entrega = EntregaMonitorada.query.filter_by(numero_nf=nova_nf).first()
            if nova_entrega:
                nova_entrega.substituida_por_nf = entrega
                
                # ✅ NOVA FUNCIONALIDADE: Transferir separacao_lote_id
                nova_entrega.separacao_lote_id = entrega.separacao_lote_id

                if entrega.agendamentos:
                    ag = max(entrega.agendamentos, key=lambda a: a.criado_em)
                    novo_ag = AgendamentoEntrega(
                        entrega_id=nova_entrega.id,
                        data_agendada=ag.data_agendada,
                        hora_agendada=ag.hora_agendada,
                        protocolo_agendamento=ag.protocolo_agendamento,
                        observacao=ag.observacao,
                        motivo=ag.motivo,
                        autor=current_user.nome,
                        forma_agendamento=ag.forma_agendamento
                    )
                    db.session.add(novo_ag)

                nova_entrega.data_embarque = entrega.data_embarque
                nova_entrega.data_agenda = entrega.data_agenda
                nova_entrega.data_entrega_prevista = entrega.data_entrega_prevista

                evento = EventoEntrega(
                    entrega_id=nova_entrega.id,
                    autor=current_user.nome,
                    observacao=f"Troca da NF <a href='{url_for('monitoramento.visualizar_entrega', id=entrega.id, _external=True)}'>{entrega.numero_nf}</a>",
                    tipo_evento="Troca NF"
                )
                db.session.add(evento)

                descricao_log += f" para nova NF: {nova_nf}"

    else:  # Se não houver um status especial selecionado, considera Entrega realizada obrigatoriamente com data
        entrega.status_finalizacao = "Entregue"
        entrega.entregue = True
        entrega.data_hora_entrega_realizada = datetime.strptime(data_str, "%Y-%m-%dT%H:%M")
        descricao_log = "Entrega realizada"

    entrega.finalizado_em = agora_utc_naive()
    entrega.finalizado_por = current_user.nome

    db.session.commit()

    flash('Entrega atualizada com sucesso.', 'success')
    return redirect(url_for('monitoramento.visualizar_entrega', id=id))





@monitoramento_bp.route('/<int:id>/resolver-pendencia', methods=['POST'])
@login_required
def resolver_pendencia(id):
    entrega = EntregaMonitorada.query.get_or_404(id)
    entrega.pendencia_financeira = False
    entrega.resposta_financeiro = f"Resolvido por {current_user.nome} em {agora_utc_naive().strftime('%d/%m/%Y %H:%M')}"
    db.session.commit()
    return redirect(url_for('monitoramento.listar_entregas', **request.args))

def _enriquecer_entregas_batch(entregas):
    """
    Enriquece lista de EntregaMonitorada com dados de faturamento, carteira e embarque.
    Usa batch pre-fetch com IN() para evitar N+1 queries.
    """
    if not entregas:
        return

    # Coletar NFs unicas
    nfs = list({e.numero_nf for e in entregas if e.numero_nf})

    if not nfs:
        # Sem NFs — inicializar defaults
        for entrega in entregas:
            entrega.num_pedido = None
            entrega.incoterm = None
            entrega.observ_ped_1 = None
            entrega.pedido_cliente = None
            entrega.nf_cancelada = False
            entrega.modalidade = None
            entrega.rastreamento_id = None
        return

    # Batch 1: RelatorioFaturamentoImportado (num_pedido, incoterm, valor)
    fat_imp_map = {}
    for f in RelatorioFaturamentoImportado.query.filter(
        RelatorioFaturamentoImportado.numero_nf.in_(nfs)
    ).all():
        if f.numero_nf not in fat_imp_map:
            fat_imp_map[f.numero_nf] = f

    # Batch 2: FaturamentoProduto (status NF cancelada)
    fat_prod_map = {}
    for f in FaturamentoProduto.query.filter(
        FaturamentoProduto.numero_nf.in_(nfs)
    ).all():
        if f.numero_nf not in fat_prod_map:
            fat_prod_map[f.numero_nf] = f

    # Batch 3: EmbarqueItem com joinedload do embarque e rastreamento
    emb_itens_map = {}
    emb_itens_raw = EmbarqueItem.query.options(
        joinedload(EmbarqueItem.embarque).joinedload(Embarque.rastreamento)
    ).filter(EmbarqueItem.nota_fiscal.in_(nfs)).all()
    for ei in emb_itens_raw:
        if ei.nota_fiscal not in emb_itens_map:
            emb_itens_map[ei.nota_fiscal] = ei

    # Coletar num_pedido para batch CarteiraPrincipal
    pedidos_set = set()
    for entrega in entregas:
        fat = fat_imp_map.get(entrega.numero_nf)
        if fat and fat.origem:
            pedidos_set.add(fat.origem)
    pedidos_list = list(pedidos_set)

    # Batch 4: CarteiraPrincipal (observ_ped_1, pedido_cliente)
    carteira_map = {}
    if pedidos_list:
        for c in CarteiraPrincipal.query.filter(
            CarteiraPrincipal.num_pedido.in_(pedidos_list)
        ).all():
            if c.num_pedido not in carteira_map:
                carteira_map[c.num_pedido] = c

    # Enriquecer cada entrega via lookup O(1)
    for entrega in entregas:
        faturamento = fat_imp_map.get(entrega.numero_nf)
        entrega.num_pedido = faturamento.origem if faturamento else None

        if not entrega.valor_nf and faturamento:
            entrega.valor_nf = faturamento.valor_total

        entrega.incoterm = faturamento.incoterm if faturamento else None

        # CarteiraPrincipal
        if entrega.num_pedido:
            carteira_item = carteira_map.get(entrega.num_pedido)
            entrega.observ_ped_1 = carteira_item.observ_ped_1 if carteira_item else None
            entrega.pedido_cliente = getattr(carteira_item, 'pedido_cliente', None)
        else:
            entrega.observ_ped_1 = None
            entrega.pedido_cliente = None

        # NF cancelada
        faturamento_produto = fat_prod_map.get(entrega.numero_nf)
        entrega.nf_cancelada = (faturamento_produto and faturamento_produto.status_nf == 'Cancelado')

        # Embarque / modalidade / rastreamento
        embarque_item = emb_itens_map.get(entrega.numero_nf)
        if embarque_item:
            if embarque_item.modalidade:
                entrega.modalidade = embarque_item.modalidade
            elif embarque_item.embarque:
                entrega.modalidade = embarque_item.embarque.modalidade
            else:
                entrega.modalidade = None

            if embarque_item.embarque and hasattr(embarque_item.embarque, 'rastreamento'):
                rastreamento = embarque_item.embarque.rastreamento
                if rastreamento and rastreamento.aceite_lgpd:
                    entrega.rastreamento_id = rastreamento.id
                    entrega.rastreamento_status = rastreamento.status
                    entrega.embarque_numero = embarque_item.embarque.numero
                else:
                    entrega.rastreamento_id = None
            else:
                entrega.rastreamento_id = None
        else:
            entrega.modalidade = None
            entrega.rastreamento_id = None


@monitoramento_bp.route('/listar_entregas')
@login_required
@allow_vendedor_own_data()  # 🔒 VENDEDORES: Apenas dados próprios
def listar_entregas():
    
    query = EntregaMonitorada.query
    
    # 🔒 FILTRO PARA VENDEDORES - Só vê seus dados
    vendedor_filtro = get_vendedor_filter_query()
    if vendedor_filtro == "ACESSO_NEGADO":
        flash('Acesso negado. Perfil sem permissão para monitoramento.', 'danger')
        return redirect(url_for('main.dashboard'))
    elif vendedor_filtro is not None:  # Vendedor específico
        query = query.filter(EntregaMonitorada.vendedor.ilike(f'%{vendedor_filtro}%'))

    status = request.args.get('status')
    if status == 'entregue':
        query = query.filter(EntregaMonitorada.status_finalizacao == 'Entregue')
    elif status == 'atrasada':
        query = query.filter(
            EntregaMonitorada.status_finalizacao.is_(None),
            EntregaMonitorada.data_entrega_prevista.isnot(None),
            EntregaMonitorada.data_entrega_prevista < date.today()
        )
    elif status == 'no_prazo':
        query = query.filter(
            EntregaMonitorada.status_finalizacao.is_(None),
            EntregaMonitorada.data_entrega_prevista.isnot(None),
            EntregaMonitorada.data_entrega_prevista >= date.today()
        )
    elif status == 'sem_previsao':
        # ✅ CORRIGIDO: Excluir finalizados do filtro "Sem Previsão"
        query = query.filter(
            EntregaMonitorada.data_entrega_prevista.is_(None),
            EntregaMonitorada.status_finalizacao.is_(None)
        )

    if status == 'reagendar':
        query = query.filter(
            EntregaMonitorada.reagendar == True,
            EntregaMonitorada.status_finalizacao.is_(None)
        )
    if status == 'pendencia_financeira':
        query = query.join(PendenciaFinanceiraNF, PendenciaFinanceiraNF.entrega_id == EntregaMonitorada.id)
        # Pendências não respondidas OU com resposta apagada
        query = query.filter(
            db.or_(
                PendenciaFinanceiraNF.respondida_em.is_(None),
                PendenciaFinanceiraNF.resposta_excluida_em.isnot(None)
            )
        )
    # ✅ NOVOS FILTROS DE STATUS ESPECÍFICOS
    if status == 'troca_nf':
        query = query.filter(EntregaMonitorada.status_finalizacao == 'Troca de NF')
    elif status == 'cancelada':
        query = query.filter(EntregaMonitorada.status_finalizacao == 'Cancelada')
    elif status == 'devolvida':
        query = query.filter(EntregaMonitorada.status_finalizacao == 'Devolvida')
    elif status == 'sinistro':
        query = query.filter(EntregaMonitorada.status_finalizacao == 'Sinistro')
    if status == 'nf_cd':
        query = query.filter(EntregaMonitorada.nf_cd == True)
    
    # ✅ NOVO FILTRO: Aguardando Aprovação de Agendamento (apenas o último agendamento)
    if status == 'ag_aprovacao':
        # Subquery para pegar a data/hora do último agendamento de cada entrega
        # Isso garante que só verificamos o status do agendamento mais recente
        subquery_ultimo_agend = db.session.query(
            AgendamentoEntrega.entrega_id,
            func.max(AgendamentoEntrega.criado_em).label('max_criado_em')
        ).group_by(AgendamentoEntrega.entrega_id).subquery()
        
        # Buscar entregas onde o ÚLTIMO agendamento tem status "aguardando"
        query = query.join(
            AgendamentoEntrega, 
            AgendamentoEntrega.entrega_id == EntregaMonitorada.id
        ).join(
            subquery_ultimo_agend,
            db.and_(
                AgendamentoEntrega.entrega_id == subquery_ultimo_agend.c.entrega_id,
                AgendamentoEntrega.criado_em == subquery_ultimo_agend.c.max_criado_em
            )
        ).filter(
            AgendamentoEntrega.status == 'aguardando',
            EntregaMonitorada.status_finalizacao.is_(None)  # Não finalizada
        )

    # Filtro por origem (NACOM / CARVIA / Todas)
    # Permite segregar NFs do fluxo principal das do subsistema CarVia
    origem_filtro = (request.args.get('origem') or '').strip().upper()
    if origem_filtro in ('NACOM', 'CARVIA'):
        query = query.filter(EntregaMonitorada.origem == origem_filtro)

    # Filtro sem_agendamento — usa cache de contatos e IN() ao invés de OR-explosion
    if status == 'sem_agendamento':
        cnpjs_validos = _get_cnpjs_que_precisam_agendamento()

        if cnpjs_validos:
            query = query.filter(
                EntregaMonitorada.cnpj_cliente.in_(cnpjs_validos),
                EntregaMonitorada.data_agenda.is_(None),
                EntregaMonitorada.status_finalizacao.is_(None)
            )
        else:
            query = query.filter(db.text('1=0'))

    if numero_nf := request.args.get('numero_nf'):
        query = query.filter(EntregaMonitorada.numero_nf.ilike(f"%{numero_nf}%"))

    transportadora = request.args.get('transportadora', '')
    transportadora_id = request.args.get('transportadora_id', type=int)
    if transportadora or transportadora_id:
        from app.transportadoras.filter_utils import expandir_filtro_texto
        filtro = expandir_filtro_texto(
            [EntregaMonitorada.transportadora],
            transportadora_id=transportadora_id,
            texto_busca=transportadora
        )
        if filtro is not None:
            query = query.filter(filtro)

    if cliente := request.args.get('cliente'):
        query = query.filter(EntregaMonitorada.cliente.ilike(f"%{cliente}%"))

    if cnpj := request.args.get('cnpj_cliente'):
        query = query.filter(EntregaMonitorada.cnpj_cliente.ilike(f"%{cnpj}%"))

    if status == 'com_comentarios':
        query = query.join(ComentarioNF).group_by(EntregaMonitorada.id)

    # ✅ NOVO FILTRO: Vendedor
    if vendedor := request.args.get('vendedor'):
        query = query.filter(EntregaMonitorada.vendedor.ilike(f"%{vendedor}%"))

    if uf := request.args.get('uf'):
        query = query.filter(EntregaMonitorada.uf.ilike(f"%{uf}%"))

    if protocolo := request.args.get('protocolo'):
        query = query.filter(
            EntregaMonitorada.agendamentos.any(
                AgendamentoEntrega.protocolo_agendamento.ilike(f"%{protocolo}%")
            )
        )

    # ✅ CORRIGINDO FILTROS DE DATA - formato YYYY-MM-DD (padrão HTML date input)
    if data_emissao := request.args.get('data_emissao'):
        try:
            # Tenta formato YYYY-MM-DD primeiro (HTML date input)
            dt = datetime.strptime(data_emissao, "%Y-%m-%d").date()
            query = query.filter(EntregaMonitorada.data_faturamento == dt)
        except ValueError:
            try:
                # Fallback para formato brasileiro DD-MM-YYYY
                dt = datetime.strptime(data_emissao, "%d-%m-%Y").date()
                query = query.filter(EntregaMonitorada.data_faturamento == dt)
            except ValueError:
                pass

    if data_embarque := request.args.get('data_embarque'):
        try:
            # Tenta formato YYYY-MM-DD primeiro (HTML date input)
            dt = datetime.strptime(data_embarque, "%Y-%m-%d").date()
            query = query.filter(EntregaMonitorada.data_embarque == dt)
        except ValueError:
            try:
                # Fallback para formato brasileiro DD-MM-YYYY  
                dt = datetime.strptime(data_embarque, "%d-%m-%Y").date()
                query = query.filter(EntregaMonitorada.data_embarque == dt)
            except ValueError:
                pass

    # ✅ NOVO FILTRO: Data Entrega Prevista
    if data_entrega_prevista := request.args.get('data_entrega_prevista'):
        try:
            # Tenta formato YYYY-MM-DD primeiro (HTML date input)
            dt = datetime.strptime(data_entrega_prevista, "%Y-%m-%d").date()
            query = query.filter(EntregaMonitorada.data_entrega_prevista == dt)
        except ValueError:
            try:
                # Fallback para formato brasileiro DD-MM-YYYY
                dt = datetime.strptime(data_entrega_prevista, "%d-%m-%Y").date()
                query = query.filter(EntregaMonitorada.data_entrega_prevista == dt)
            except ValueError:
                pass

    if data_entrega := request.args.get('data_entrega'):
        try:
            # Tenta formato YYYY-MM-DD primeiro (HTML date input)
            dt = datetime.strptime(data_entrega, "%Y-%m-%d").date()
            query = query.filter(func.date(EntregaMonitorada.data_hora_entrega_realizada) == dt)
        except ValueError:
            try:
                # Fallback para formato brasileiro DD-MM-YYYY
                dt = datetime.strptime(data_entrega, "%d-%m-%Y").date()
                query = query.filter(func.date(EntregaMonitorada.data_hora_entrega_realizada) == dt)
            except ValueError:
                pass

    # Faz join para poder ordenar / filtrar por esse valor, se necessário
    # (Se não for filtrar explicitamente, o "outerjoin" nem sempre é necessário)
    # query = query.outerjoin(...)   # Em muitos casos, basta a subquery correlacionada.

    # 1) Descobre a coluna e direção de ordenação
    sort = request.args.get('sort')
    direction = request.args.get('direction', 'asc')

    # 2) Defina as colunas "ordenáveis"
    sortable_columns = {
        'numero_nf': EntregaMonitorada.numero_nf,
        'cnpj_cliente': EntregaMonitorada.cnpj_cliente,
        'cliente': EntregaMonitorada.cliente,
        'transportadora': EntregaMonitorada.transportadora,
        'municipio': EntregaMonitorada.municipio,
        'uf':EntregaMonitorada.uf,
        'data_faturamento': EntregaMonitorada.data_faturamento,
        'data_embarque': EntregaMonitorada.data_embarque,
        'data_agenda': EntregaMonitorada.data_agenda,
        'data_entrega_prevista': EntregaMonitorada.data_entrega_prevista,
    }

    # 3) Ordena pela coluna correspondente, se existir
    if sort in sortable_columns:
        column = sortable_columns[sort]
        if direction == 'desc':
            query = query.order_by(column.desc())
        else:
            query = query.order_by(column.asc())
    else:
        # Ordenação padrão
        query = query.order_by(EntregaMonitorada.criado_em.desc())

    # Contatos de agendamento (cache 60s — evita query em cada request)
    contatos_agendamento = _get_contatos_agendamento()

    # ✅ CALCULANDO CONTADORES DOS FILTROS
    contadores = {}
    
    # Base query para aplicar filtro de vendedor aos contadores
    base_count_query = EntregaMonitorada.query
    if vendedor_filtro is not None and vendedor_filtro != "ACESSO_NEGADO":
        base_count_query = base_count_query.filter(EntregaMonitorada.vendedor.ilike(f'%{vendedor_filtro}%'))
    
    # Contador Atrasadas
    contadores['atrasadas'] = base_count_query.filter(
        EntregaMonitorada.status_finalizacao.is_(None),
        EntregaMonitorada.data_entrega_prevista.isnot(None),
        EntregaMonitorada.data_entrega_prevista < date.today()
    ).count()
    
    # Contador Sem Previsão  
    contadores['sem_previsao'] = base_count_query.filter(
        EntregaMonitorada.data_entrega_prevista.is_(None),
        EntregaMonitorada.status_finalizacao.is_(None)
    ).count()
    
    # Contador Reagendar
    contadores['reagendar'] = base_count_query.filter(
        EntregaMonitorada.reagendar == True,
        EntregaMonitorada.status_finalizacao.is_(None)
    ).count()
    
    # Contador sem_agendamento — reutiliza cache de CNPJs (IN ao invés de OR-explosion)
    cnpjs_agendamento = _get_cnpjs_que_precisam_agendamento()
    if cnpjs_agendamento:
        contadores['sem_agendamento'] = base_count_query.filter(
            EntregaMonitorada.cnpj_cliente.in_(cnpjs_agendamento),
            EntregaMonitorada.data_agenda.is_(None),
            EntregaMonitorada.status_finalizacao.is_(None)
        ).count()
    else:
        contadores['sem_agendamento'] = 0
    
    # Contador NF no CD
    contadores['nf_cd'] = base_count_query.filter(
        EntregaMonitorada.nf_cd == True
    ).count()
    
    # ✅ NOVO CONTADOR: Aguardando Aprovação de Agendamento (apenas o último agendamento)
    # Subquery para pegar o último agendamento de cada entrega
    subquery_ultimo_contador = db.session.query(
        AgendamentoEntrega.entrega_id,
        func.max(AgendamentoEntrega.criado_em).label('max_criado_em')
    ).group_by(AgendamentoEntrega.entrega_id).subquery()
    
    count_query_ag_aprov = base_count_query.join(
        AgendamentoEntrega,
        AgendamentoEntrega.entrega_id == EntregaMonitorada.id
    ).join(
        subquery_ultimo_contador,
        db.and_(
            AgendamentoEntrega.entrega_id == subquery_ultimo_contador.c.entrega_id,
            AgendamentoEntrega.criado_em == subquery_ultimo_contador.c.max_criado_em
        )
    ).filter(
        AgendamentoEntrega.status == 'aguardando',
        EntregaMonitorada.status_finalizacao.is_(None)
    )
    contadores['ag_aprovacao'] = count_query_ag_aprov.count()

    page = request.args.get('page', 1, type=int)
    per_page = 20
    paginacao = query.paginate(page=page, per_page=per_page)

    # ✅ BUSCAR VENDEDORES ÚNICOS para dropdown
    vendedores_unicos = db.session.query(RelatorioFaturamentoImportado.vendedor)\
        .filter(RelatorioFaturamentoImportado.vendedor.isnot(None), RelatorioFaturamentoImportado.vendedor != '')\
        .distinct().order_by(RelatorioFaturamentoImportado.vendedor).all()
    vendedores_unicos = [v[0] for v in vendedores_unicos]

    # Batch pre-fetch: enriquecer entregas paginadas de uma vez
    _enriquecer_entregas_batch(paginacao.items)

    # R18: batch — mapear NF venda (origem=CARVIA) -> NF transferencia
    # vinculada, para exibir "NF Transf: ####" na coluna Embarque.
    num_nf_transf_por_nf = {}
    nfs_carvia = [
        e.numero_nf for e in paginacao.items
        if getattr(e, 'origem', None) == 'CARVIA' and e.numero_nf
    ]
    if nfs_carvia:
        try:
            from app.carvia.models import CarviaNf
            from app.carvia.models.documentos import (
                CarviaNfVinculoTransferencia,
            )
            NfVenda = db.aliased(CarviaNf, name='nf_venda')
            NfTransf = db.aliased(CarviaNf, name='nf_transf')
            # Limitacao conhecida: carvia_nfs.numero_nf nao e unique. Filtramos
            # por NfVenda.status='ATIVA' para alinhar com o criterio de sync
            # que so cria EntregaMonitorada de NFs ATIVAs. Em caso raro de
            # duas NFs ATIVAS com mesmo numero, o dict pega a ultima (last-wins).
            rows = db.session.query(
                NfVenda.numero_nf, NfTransf.numero_nf,
            ).select_from(
                CarviaNfVinculoTransferencia,
            ).join(
                NfVenda, NfVenda.id == CarviaNfVinculoTransferencia.nf_venda_id,
            ).join(
                NfTransf, NfTransf.id == CarviaNfVinculoTransferencia.nf_transferencia_id,
            ).filter(
                NfVenda.numero_nf.in_(nfs_carvia),
                NfVenda.status == 'ATIVA',
            ).all()
            num_nf_transf_por_nf = {
                num_venda: num_transf for num_venda, num_transf in rows if num_venda
            }
        except Exception:
            # Nao-bloqueante: erro aqui nao quebra a tela
            import logging as _lg
            _lg.getLogger(__name__).exception(
                'Erro ao carregar num_nf_transf_por_nf (R18)'
            )

    return render_template(
        'monitoramento/listar_entregas.html',
        paginacao=paginacao,
        entregas=paginacao.items,
        current_date=date.today(),
        contatos_agendamento=contatos_agendamento,
        current_user=current_user,
        contadores=contadores,
        vendedores_unicos=vendedores_unicos,
        num_nf_transf_por_nf=num_nf_transf_por_nf,
    )

@monitoramento_bp.route('/sincronizar-todas-entregas', methods=['POST'])
@login_required  
def sincronizar_todas_entregas_manual():
    """
    ✅ NOVA ROTA: Permite sincronização manual de todas as entregas
    
    Útil para:
    - Corrigir inconsistências no monitoramento
    - Atualizar dados após importação de faturamento
    - Manutenção preventiva do sistema
    """
    try:
        # Executa a sincronização completa
        sincronizar_todas_entregas()
        
        flash("✅ Sincronização de todas as entregas concluída com sucesso!", "success")
        print("[DEBUG] 🔄 Sincronização manual de entregas executada")
        
    except Exception as e:
        flash(f"❌ Erro na sincronização: {str(e)}", "error")
        print(f"[DEBUG] ❌ Erro na sincronização manual: {e}")
    
    return redirect(url_for('monitoramento.listar_entregas'))

@monitoramento_bp.route('/diagnosticar-monitoramento')
@login_required
def diagnosticar_monitoramento():
    """
    ✅ NOVA ROTA: Diagnóstico completo do módulo de monitoramento
    
    Analisa:
    - Entregas órfãs (sem embarque)
    - NFs no CD que precisam de reprocessamento  
    - Inconsistências de data
    - Problemas de sincronização
    """
    try:
        from app.embarques.models import EmbarqueItem
        from app.faturamento.models import RelatorioFaturamentoImportado
        
        diagnosticos = {}
        
        # 1. Entregas sem embarque correspondente
        entregas_sem_embarque = db.session.query(EntregaMonitorada.numero_nf).outerjoin(
            EmbarqueItem, EmbarqueItem.nota_fiscal == EntregaMonitorada.numero_nf
        ).filter(EmbarqueItem.nota_fiscal.is_(None)).all()
        
        diagnosticos['entregas_sem_embarque'] = len(entregas_sem_embarque)
        
        # 2. NFs no CD que precisam reprocessamento
        nfs_cd_ativo = EntregaMonitorada.query.filter_by(nf_cd=True).count()
        diagnosticos['nfs_cd_ativo'] = nfs_cd_ativo
        
        # 3. Entregas sem data de embarque
        entregas_sem_data_embarque = EntregaMonitorada.query.filter_by(data_embarque=None).count()
        diagnosticos['entregas_sem_data_embarque'] = entregas_sem_data_embarque
        
        # 4. Entregas com NF não importada no faturamento (anti-join, 1 query)
        subquery_nfs_fat = db.session.query(
            RelatorioFaturamentoImportado.numero_nf
        ).filter(
            RelatorioFaturamentoImportado.numero_nf.isnot(None)
        ).subquery()

        nfs_nao_importadas = db.session.query(
            db.func.count(EntregaMonitorada.id)
        ).filter(
            ~EntregaMonitorada.numero_nf.in_(
                db.session.query(subquery_nfs_fat.c.numero_nf)
            )
        ).scalar() or 0

        diagnosticos['nfs_nao_importadas'] = nfs_nao_importadas
        
        # 5. Total de entregas
        diagnosticos['total_entregas'] = EntregaMonitorada.query.count()
        
        flash(f"📊 Diagnóstico concluído: {diagnosticos['total_entregas']} entregas analisadas", "info")
        
        return render_template('monitoramento/diagnostico.html', diagnosticos=diagnosticos)
        
    except Exception as e:
        flash(f"❌ Erro no diagnóstico: {str(e)}", "error")
        return redirect(url_for('monitoramento.listar_entregas'))

@monitoramento_bp.route('/<int:id>/historico', methods=['GET'])
@login_required
def visualizar_historico(id):
    entrega = EntregaMonitorada.query.get_or_404(id)
    logs = RegistroLogEntrega.query.filter_by(entrega_id=id).all()
    eventos = EventoEntrega.query.filter_by(entrega_id=id).all()
    custos = CustoExtraEntrega.query.filter_by(entrega_id=id).all()
    agendamentos = AgendamentoEntrega.query.filter_by(entrega_id=id).all()
    
    historico_completo = sorted(
        chain(
            ((log.data_hora, 'Log', log.autor, f"{log.tipo}: {log.descricao}") for log in logs),
            ((evento.criado_em, 'Evento', evento.autor, f"{evento.tipo_evento}: {evento.observacao} - Chegada: {evento.data_hora_chegada.strftime('%d/%m/%Y %H:%M') if evento.data_hora_chegada else 'Sem registro'}") for evento in eventos),
            ((custo.criado_em, 'Custo', custo.autor, f"{custo.tipo}: R$ {custo.valor:.2f} - {custo.motivo}") for custo in custos),
            ((ag.criado_em, 'Agendamento', ag.autor, f"Agendado por: {ag.forma_agendamento} Data: {ag.data_agendada.strftime('%d/%m/%Y')} - {ag.hora_agendada.strftime('%H:%M') if ag.hora_agendada else 'Sem horário'} - Protocolo {ag.protocolo_agendamento}- Motivo: {ag.motivo}") for ag in agendamentos),
            [(entrega.finalizado_em, 'Finalização', entrega.finalizado_por, f"Entrega finalizada em: {entrega.data_hora_entrega_realizada.strftime('%d/%m/%Y-%H:%M') if entrega.data_hora_entrega_realizada else 'Data não informada'}")] if entrega.finalizado_em else [],
            [(entrega.data_hora_entrega_realizada, 'Entrega', entrega.finalizado_por, f"Entrega realizada em: {entrega.data_hora_entrega_realizada.strftime('%d/%m/%Y-%H:%M') if entrega.data_hora_entrega_realizada else 'Data não informada'}")] if entrega.data_hora_entrega_realizada else [],
        ),
        key=lambda x: x[0], reverse=True
    )

    return render_template('monitoramento/historico.html', entrega=entrega, historico=historico_completo)



@monitoramento_bp.route('/<int:id>/arquivos', methods=['GET', 'POST'])
@login_required
def visualizar_arquivos(id):
    entrega = EntregaMonitorada.query.get_or_404(id)
    
    # 🆕 Usar sistema S3
    storage = get_file_storage()
    
    if request.method == 'POST':
        if 'arquivo' not in request.files:
            flash("Nenhum arquivo enviado.", 'warning')
            return redirect(request.url)
        
        file = request.files['arquivo']
        if file and file.filename:
            try:
                # 📏 Obter informações do arquivo ANTES de salvar
                file.seek(0, 2)  # Move para o final
                tamanho_arquivo = file.tell()
                file.seek(0)  # Volta para o início
                
                current_app.logger.info(f"🔄 Iniciando upload: {file.filename} ({tamanho_arquivo} bytes) para entrega {entrega.id}")
                
                # 🌐 Salvar no storage usando o novo sistema
                file_path = storage.save_file(
                    file=file,
                    folder=f'entregas/{entrega.id}',
                    allowed_extensions=['pdf', 'jpg', 'jpeg', 'jfif', 'png', 'xlsx', 'docx', 'txt']
                )
                
                if file_path:
                    current_app.logger.info(f"✅ Arquivo salvo no storage: {file_path}")
                    
                    # 📝 Registrar arquivo na tabela
                    arquivo_entrega = ArquivoEntrega(
                        entrega_id=entrega.id,
                        nome_original=file.filename,
                        nome_arquivo=os.path.basename(file_path),
                        caminho_arquivo=file_path,
                        tipo_storage='s3' if storage.use_s3 else 'local',
                        tamanho_bytes=tamanho_arquivo,
                        content_type=file.content_type or 'application/octet-stream',
                        criado_por=current_user.nome
                    )
                    
                    db.session.add(arquivo_entrega)
                    db.session.commit()
                    
                    current_app.logger.info(f"✅ Arquivo registrado no banco: ID {arquivo_entrega.id}")
                    flash("✅ Arquivo salvo com sucesso no sistema!", 'success')
                else:
                    current_app.logger.error(f"❌ Falha ao salvar arquivo no storage: {file.filename}")
                    flash("❌ Erro ao salvar arquivo.", 'danger')
                    
            except Exception as e:
                current_app.logger.error(f"❌ ERRO DETALHADO no upload: {str(e)}", exc_info=True)
                flash(f"❌ Erro ao salvar arquivo: {str(e)}", 'danger')
            
            return redirect(request.url)

    # 📁 Listar arquivos (novos do banco + antigos da pasta local)
    arquivos = []
    
    # ✅ Arquivos novos (rastreados no banco)
    arquivos_banco = ArquivoEntrega.query.filter_by(entrega_id=entrega.id).order_by(ArquivoEntrega.criado_em.desc()).all()
    current_app.logger.info(f"📂 Listando arquivos da entrega {entrega.id}: {len(arquivos_banco)} arquivos no banco")
    
    for arquivo_db in arquivos_banco:
        current_app.logger.info(f"📄 Arquivo no banco: {arquivo_db.nome_original} (ID: {arquivo_db.id}, Tipo: {arquivo_db.tipo_storage})")
        arquivos.append({
            'id': arquivo_db.id,
            'nome': arquivo_db.nome_original,
            'tipo': arquivo_db.tipo_storage,
            'icone': arquivo_db.icone,
            'tamanho': arquivo_db.tamanho_bytes,
            'criado_em': arquivo_db.criado_em,
            'criado_por': arquivo_db.criado_por,
            'url': url_for('monitoramento.download_arquivo_entrega', arquivo_id=arquivo_db.id)
        })
    
    # 📂 Arquivos antigos (pasta local - compatibilidade)
    pasta_local = os.path.join(UPLOAD_DIR, str(entrega.id))
    if os.path.exists(pasta_local):
        for arquivo in os.listdir(pasta_local):
            # Evita duplicatas se o arquivo já está no banco
            if not any(a['nome'] == arquivo for a in arquivos):
                arquivos.append({
                    'id': None,
                    'nome': arquivo,
                    'tipo': 'local_antigo',
                    'icone': get_file_icon(arquivo),
                    'tamanho': None,
                    'criado_em': None,
                    'criado_por': 'Sistema Antigo',
                    'url': url_for('monitoramento.get_arquivo_entrega', entrega_id=entrega.id, filename=arquivo)
                })
    
    return render_template('monitoramento/arquivos.html', entrega=entrega, arquivos=arquivos)

@monitoramento_bp.route('/<int:id>/toggle-reagendar', methods=['POST'])
@login_required
def toggle_reagendar(id):
    entrega = EntregaMonitorada.query.get_or_404(id)
    entrega.reagendar = not entrega.reagendar
    db.session.commit()
    return redirect(url_for('monitoramento.listar_entregas',**request.args))

@monitoramento_bp.route('/uploads/entregas/<int:entrega_id>/<filename>')
@login_required
def get_arquivo_entrega(entrega_id, filename):
    """Serve arquivos antigos (compatibilidade)"""
    pasta = os.path.join(UPLOAD_DIR, str(entrega_id))
    return send_from_directory(pasta, filename)

@monitoramento_bp.route('/arquivo/<int:arquivo_id>/download')
@login_required
def download_arquivo_entrega(arquivo_id):
    """Serve arquivos novos (rastreados no banco)"""
    arquivo = ArquivoEntrega.query.get_or_404(arquivo_id)
    
    # 🔒 Verificar acesso à entrega (mesmo controle de visualizar_entrega)
    if current_user.perfil == 'vendedor':
        if not check_vendedor_permission(vendedor_nome=arquivo.entrega.vendedor, numero_nf=arquivo.entrega.numero_nf):
            flash('Acesso negado. Você só pode baixar arquivos das entregas dos seus clientes.', 'danger')
            return redirect(url_for('monitoramento.listar_entregas'))
    
    try:
        storage = get_file_storage()
        
        if arquivo.tipo_storage == 's3':
            # Para arquivos S3, gera URL assinada e redireciona
            url = storage.get_file_url(arquivo.caminho_arquivo)
            if url:
                return redirect(url)
            else:
                flash("❌ Erro ao gerar link do arquivo.", 'danger')
                return redirect(request.referrer)
        else:
            # Para arquivos locais, serve diretamente
            pasta = os.path.dirname(arquivo.caminho_arquivo)
            nome_arquivo = os.path.basename(arquivo.caminho_arquivo)
            return send_from_directory(pasta, nome_arquivo)
            
    except Exception as e:
        flash(f"❌ Erro ao baixar arquivo: {str(e)}", 'danger')
        return redirect(request.referrer)

@monitoramento_bp.route('/log/<int:log_id>/excluir', methods=['POST'])
@login_required
def excluir_log(log_id):
    log = RegistroLogEntrega.query.get_or_404(log_id)

    db.session.delete(log)
    db.session.commit()

    flash('Log excluído com sucesso e alterações revertidas.', 'success')
    return redirect(request.referrer)


@monitoramento_bp.route('/evento/<int:evento_id>/excluir', methods=['POST'])
@login_required
def excluir_evento(evento_id):
    evento = EventoEntrega.query.get_or_404(evento_id)
    entrega = evento.entrega  # referência à entrega associada

    # Verifique se é evento de troca de NF
    if evento.tipo_evento == "Troca NF":
        nf_substituida = re.search(r"numero_nf=(\d+)", evento.observacao)
        if nf_substituida:
            nf_substituida_num = nf_substituida.group(1)
            entrega_original = EntregaMonitorada.query.filter_by(numero_nf=nf_substituida_num).first()

            # Se for a "nova" entrega
            entrega_nova = evento.entrega
            if entrega_nova:
                # Remove vínculo com a entrega original
                entrega_nova.substituida_por_nf = None
                # Apaga status finalização e nova_nf da entrega original
                entrega_original.status_finalizacao = None
                entrega_original.nova_nf = None

    # Verifique se é evento "NF no CD"
    if evento.tipo_evento == "NF no CD":
        # "desativar" o nf_cd, se houver entrega associada
        if entrega:
            entrega.nf_cd = False

            # ✅ CORREÇÃO: Sincronizar nf_cd com Separacao
            # Ao excluir evento "NF no CD", também resetar flag em Separacao
            if entrega.separacao_lote_id:
                Separacao.query.filter_by(
                    separacao_lote_id=entrega.separacao_lote_id
                ).update({'nf_cd': False})
                print(f"[SYNC] 🔄 Separacao nf_cd=False para lote {entrega.separacao_lote_id}")
            elif entrega.numero_nf:
                # Fallback: buscar por NF
                Separacao.query.filter_by(
                    numero_nf=entrega.numero_nf
                ).update({'nf_cd': False})
                print(f"[SYNC] 🔄 Separacao nf_cd=False para NF {entrega.numero_nf}")

    db.session.delete(evento)
    db.session.commit()

    flash('Evento excluído com sucesso.', 'success')
    return redirect(request.referrer)



@monitoramento_bp.route('/custo/<int:custo_id>/excluir', methods=['POST'])
@login_required
def excluir_custo(custo_id):
    custo = CustoExtraEntrega.query.get_or_404(custo_id)
    db.session.delete(custo)
    db.session.commit()
    flash('Custo excluído com sucesso.', 'success')
    return redirect(request.referrer)

@monitoramento_bp.route('/agendamento/<int:agendamento_id>/excluir', methods=['POST'])
@login_required
def excluir_agendamento(agendamento_id):
    agendamento = AgendamentoEntrega.query.get_or_404(agendamento_id)
    entrega = agendamento.entrega

    db.session.delete(agendamento)
    db.session.commit()

    entrega.data_agenda = None
    entrega.data_entrega_prevista = None
    db.session.commit()

    flash('Agendamento excluído com sucesso.', 'success')
    return redirect(request.referrer)

@monitoramento_bp.route('/<int:id>/remover_finalizacao', methods=['POST'])
@login_required
def remover_finalizacao(id):
    entrega = EntregaMonitorada.query.get_or_404(id)

    # Reset completo da finalização/status
    entrega.data_hora_entrega_realizada = None
    entrega.finalizado_por = None
    entrega.finalizado_em = None
    entrega.status_finalizacao = None
    entrega.entregue = False
    entrega.nova_nf = None

    # Revertendo relações, se existirem
    substituicao = EntregaMonitorada.query.filter_by(substituida_por_nf_id=entrega.id).first()
    if substituicao:
        substituicao.substituida_por_nf = None
        evento_relacionado = EventoEntrega.query.filter_by(
            entrega_id=substituicao.id,
            tipo_evento="Troca NF"
        ).first()
        if evento_relacionado:
            db.session.delete(evento_relacionado)

    db.session.commit()

    flash('Finalização removida com sucesso.', 'success')
    return redirect(url_for('monitoramento.visualizar_entrega', id=id))


@monitoramento_bp.route('/<int:id>/adicionar_comentario', methods=['POST'])
@login_required
@allow_vendedor_own_data()  # 🔒 PERMITIDO para vendedores (apenas seus dados)
def adicionar_comentario(id):
    entrega = EntregaMonitorada.query.get_or_404(id)
    
    # 🔒 VERIFICAÇÃO ESPECÍFICA PARA VENDEDORES
    if current_user.perfil == 'vendedor':
        if not check_vendedor_permission(vendedor_nome=entrega.vendedor, numero_nf=entrega.numero_nf):
            flash('Acesso negado. Você só pode comentar nas entregas dos seus clientes.', 'danger')
            return redirect(url_for('monitoramento.listar_entregas'))
    
    form = FormComentarioNF()

    if form.validate_on_submit():
        arquivo_path = None
        if form.arquivo.data:
            try:
                # 🌐 Usar sistema S3 para comentários
                storage = get_file_storage()
                arquivo_path = storage.save_file(
                    file=form.arquivo.data,
                    folder=f'comentarios_nf',
                    allowed_extensions=['pdf', 'jpg', 'jpeg', 'jfif', 'png', 'xlsx', 'docx', 'txt']
                )
                
                if not arquivo_path:
                    flash("❌ Erro ao salvar arquivo do comentário.", 'danger')
                    return redirect(url_for('monitoramento.visualizar_entrega', id=id))
                    
            except Exception as e:
                flash(f"❌ Erro ao salvar arquivo: {str(e)}", 'danger')
                return redirect(url_for('monitoramento.visualizar_entrega', id=id))

        comentario = ComentarioNF(
            entrega_id=id,
            autor=current_user.nome,
            texto=form.texto.data,
            arquivo=arquivo_path,  # 🆕 Agora salva o caminho S3
            resposta_a_id=form.resposta_a_id.data or None
        )
        db.session.add(comentario)
        db.session.commit()

        flash('✅ Comentário adicionado com sucesso!', 'success')
    
    return redirect(url_for('monitoramento.visualizar_entrega', id=id))

@monitoramento_bp.route('/comentarios_nf/<path:filename>')
@login_required
def baixar_arquivo_comentario(filename):
    """Serve arquivos de comentários"""
    try:
        # 🌐 Para arquivos S3, usar o sistema de URLs
        storage = get_file_storage()
        
        # Se for um caminho S3 (começa com s3://)
        if filename.startswith('s3://') or filename.startswith('comentarios_nf/'):
            url = storage.get_file_url(filename)
            if url:
                return redirect(url)
        
        # Fallback para arquivos antigos (pasta local)
        pasta_comentarios = os.path.join(UPLOAD_DIR, "comentarios_nf")
        return send_from_directory(pasta_comentarios, filename)
        
    except Exception as e:
        flash(f"❌ Erro ao acessar arquivo: {str(e)}", 'danger')
        return redirect(request.referrer)

@monitoramento_bp.route('/<int:id>/adicionar_pendencia', methods=['POST'])
@login_required
def adicionar_pendencia(id):
    entrega = EntregaMonitorada.query.get_or_404(id)
    observacao = request.form.get('observacao')
    
    if observacao and observacao.strip():
        from app.financeiro.models import PendenciaFinanceiraNF
        
        pendencia = PendenciaFinanceiraNF(
            numero_nf=entrega.numero_nf,
            entrega_id=entrega.id,
            observacao=observacao.strip(),
            criado_por=current_user.nome
        )
        
        # Marca a entrega como tendo pendência financeira
        entrega.pendencia_financeira = True
        
        db.session.add(pendencia)
        db.session.commit()
        
        flash('✔️ Pendência financeira registrada com sucesso.', 'success')
        session['feedback'] = 'pendencia'
    else:
        flash('❌ Observação da pendência é obrigatória.', 'danger')
    
    return redirect(url_for('monitoramento.visualizar_entrega', id=entrega.id))

@monitoramento_bp.route('/<int:id>/responder_pendencia', methods=['POST'])
@login_required
def responder_pendencia(id):
    entrega = EntregaMonitorada.query.get_or_404(id)
    pendencia_id = request.form.get('pendencia_id')
    resposta_logistica = request.form.get('resposta_logistica')
    
    if pendencia_id and resposta_logistica and resposta_logistica.strip():
        from app.financeiro.models import PendenciaFinanceiraNF
        
        pendencia = PendenciaFinanceiraNF.query.get_or_404(pendencia_id)
        
        if pendencia.entrega_id == entrega.id:
            pendencia.resposta_logistica = resposta_logistica.strip()
            pendencia.respondida_em = agora_utc_naive()
            pendencia.respondida_por = current_user.nome
            
            # Verifica se ainda há pendências não respondidas (pendência nunca é excluída)
            pendencias_abertas = PendenciaFinanceiraNF.query.filter_by(
                entrega_id=entrega.id,
                respondida_em=None
            ).count()
            
            if pendencias_abertas == 0:
                entrega.pendencia_financeira = False
            
            db.session.commit()
            
            flash('✔️ Resposta à pendência financeira registrada com sucesso.', 'success')
            session['feedback'] = 'pendencia'
        else:
            flash('❌ Pendência não pertence a esta entrega.', 'danger')
    else:
        flash('❌ Resposta da logística é obrigatória.', 'danger')
    
    return redirect(url_for('monitoramento.visualizar_entrega', id=entrega.id))

@monitoramento_bp.route('/pendencia/<int:pendencia_id>/apagar_resposta', methods=['POST'])
@login_required
def apagar_resposta_pendencia(pendencia_id):
    from app.financeiro.models import PendenciaFinanceiraNF
    
    pendencia = PendenciaFinanceiraNF.query.get_or_404(pendencia_id)
    entrega = pendencia.entrega
    
    if not pendencia.respondida_em:
        flash('❌ Não há resposta para apagar nesta pendência.', 'warning')
        return redirect(request.referrer)
    
    # Soft delete da resposta - mantém histórico
    pendencia.resposta_excluida_em = agora_utc_naive()
    pendencia.resposta_excluida_por = current_user.nome
    
    # A pendência volta a ser "não respondida" para efeitos de contagem
    # mas mantém o histórico da resposta original
    
    # Verifica se ainda há pendências sem resposta válida
    pendencias_abertas = PendenciaFinanceiraNF.query.filter_by(
        entrega_id=entrega.id,
        respondida_em=None
    ).count()
    
    # Soma as que têm resposta excluída (voltam a contar como abertas)
    pendencias_resposta_excluida = PendenciaFinanceiraNF.query.filter(
        PendenciaFinanceiraNF.entrega_id == entrega.id,
        PendenciaFinanceiraNF.respondida_em.isnot(None),
        PendenciaFinanceiraNF.resposta_excluida_em.isnot(None)
    ).count()
    
    total_pendencias_abertas = pendencias_abertas + pendencias_resposta_excluida
    
    entrega.pendencia_financeira = total_pendencias_abertas > 0
    
    db.session.commit()
    
    flash('✔️ Resposta à pendência apagada com sucesso. (Histórico da resposta mantido)', 'success')
    return redirect(request.referrer)

@monitoramento_bp.route('/<int:id>/alterar_data_prevista', methods=['POST'])
@login_required
def alterar_data_prevista(id):
    entrega = EntregaMonitorada.query.get_or_404(id)
    nova_data_str = request.form.get('nova_data_prevista')
    motivo_alteracao = request.form.get('motivo_alteracao')
    
    if not nova_data_str or not motivo_alteracao:
        flash('❌ Data e motivo são obrigatórios.', 'danger')
        return redirect(request.referrer)
    
    try:
        from datetime import datetime
        nova_data = datetime.strptime(nova_data_str, '%Y-%m-%d').date()
        
        # Registra histórico
        from app.monitoramento.models import HistoricoDataPrevista
        
        historico = HistoricoDataPrevista(
            entrega_id=entrega.id,
            data_anterior=entrega.data_entrega_prevista,
            data_nova=nova_data,
            motivo_alteracao=motivo_alteracao,
            alterado_por=current_user.nome
            # alterado_em usa o default do modelo (agora_utc_naive)
        )
        
        # Atualiza a data na entrega
        entrega.data_entrega_prevista = nova_data
        
        db.session.add(historico)
        db.session.commit()
        
        flash('✅ Data de entrega prevista alterada com sucesso!', 'success')
        
    except ValueError:
        flash('❌ Formato de data inválido.', 'danger')
    except Exception as e:
        db.session.rollback()
        flash(f'❌ Erro ao alterar data: {str(e)}', 'danger')
    
    return redirect(request.referrer)

@monitoramento_bp.route('/<int:id>/atualizar_observacao_rapida', methods=['POST'])
@login_required
def atualizar_observacao_rapida(id):
    """
    Atualiza a observação operacional de uma entrega via AJAX.
    Usado pelo campo de observação rápida na listagem de entregas.
    """
    entrega = EntregaMonitorada.query.get_or_404(id)

    # Verificar permissão de vendedor
    if current_user.perfil == 'vendedor':
        if not check_vendedor_permission(vendedor_nome=entrega.vendedor, numero_nf=entrega.numero_nf):
            return jsonify({'success': False, 'message': 'Acesso negado'}), 403

    try:
        data = request.get_json()
        observacao = data.get('observacao', '').strip() if data else ''

        # Atualiza o campo (permite string vazia para limpar)
        entrega.observacao_operacional = observacao if observacao else None
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Observação salva',
            'observacao': entrega.observacao_operacional or ''
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@monitoramento_bp.route('/<int:id>/historico_data_prevista')
@login_required
def historico_data_prevista(id):
    entrega = EntregaMonitorada.query.get_or_404(id)
    
    from app.monitoramento.models import HistoricoDataPrevista
    from app.utils.timezone import formatar_data_hora_brasil
    
    historicos = HistoricoDataPrevista.query.filter_by(entrega_id=entrega.id).order_by(HistoricoDataPrevista.alterado_em.desc()).all()
    
    historico_data = []
    for h in historicos:
        # Verifica se alterado_em é datetime antes de formatar
        if hasattr(h.alterado_em, 'strftime'):
            data_alteracao = formatar_data_hora_brasil(h.alterado_em)
        else:
            # Se for string ou outro formato, usar como está
            data_alteracao = str(h.alterado_em) if h.alterado_em else ''
            
        historico_data.append({
            'data_alteracao': data_alteracao,
            'data_anterior': h.data_anterior.strftime('%d/%m/%Y') if h.data_anterior else None,
            'data_nova': h.data_nova.strftime('%d/%m/%Y'),
            'motivo': h.motivo_alteracao,
            'alterado_por': h.alterado_por,
        })
    
    return jsonify({'historico': historico_data})

# ============================================================================
# EXPORTAÇÃO PARA EXCEL
# ============================================================================

def aplicar_filtros_exportacao(query, filtros):
    """Aplica filtros à query de EntregaMonitorada para exportação"""
    
    # Filtro por período de faturamento
    if filtros.get('data_faturamento_inicio'):
        query = query.filter(EntregaMonitorada.data_faturamento >= filtros['data_faturamento_inicio'])
    
    if filtros.get('data_faturamento_fim'):
        query = query.filter(EntregaMonitorada.data_faturamento <= filtros['data_faturamento_fim'])
    
    # Filtro por período de embarque
    if filtros.get('data_embarque_inicio'):
        query = query.filter(EntregaMonitorada.data_embarque >= filtros['data_embarque_inicio'])
    
    if filtros.get('data_embarque_fim'):
        query = query.filter(EntregaMonitorada.data_embarque <= filtros['data_embarque_fim'])
    
    # Filtro por cliente
    if filtros.get('cliente'):
        query = query.filter(EntregaMonitorada.cliente.ilike(f'%{filtros["cliente"]}%'))
    
    # Filtro por CNPJ
    if filtros.get('cnpj'):
        cnpj = filtros['cnpj'].replace('.', '').replace('/', '').replace('-', '')
        query = query.filter(EntregaMonitorada.cnpj_cliente.like(f'%{cnpj}%'))
    
    # Filtro por UF
    if filtros.get('uf'):
        query = query.filter(EntregaMonitorada.uf == filtros['uf'].upper())
    
    # Filtro por município
    if filtros.get('municipio'):
        query = query.filter(EntregaMonitorada.municipio.ilike(f'%{filtros["municipio"]}%'))
    
    # Filtro por transportadora
    if filtros.get('transportadora'):
        query = query.filter(EntregaMonitorada.transportadora.ilike(f'%{filtros["transportadora"]}%'))
    
    # Filtro por vendedor
    if filtros.get('vendedor'):
        query = query.filter(EntregaMonitorada.vendedor.ilike(f'%{filtros["vendedor"]}%'))
    
    # Filtro por número NF
    if filtros.get('numero_nf'):
        query = query.filter(EntregaMonitorada.numero_nf.ilike(f'%{filtros["numero_nf"]}%'))
    
    # Filtro por status de entrega
    if filtros.get('entregue') is not None:
        if filtros['entregue']:
            query = query.filter(EntregaMonitorada.status_finalizacao == 'Entregue')
        else:
            query = query.filter(EntregaMonitorada.status_finalizacao != 'Entregue')
    
    # Filtro por pendência financeira
    if filtros.get('pendencia_financeira') is not None:
        query = query.filter(EntregaMonitorada.pendencia_financeira == filtros['pendencia_financeira'])
    
    # Filtro por status de finalização
    if filtros.get('status_finalizacao'):
        if filtros['status_finalizacao'] == 'nao_finalizado':
            query = query.filter(EntregaMonitorada.status_finalizacao.is_(None))
        else:
            query = query.filter(EntregaMonitorada.status_finalizacao == filtros['status_finalizacao'])
    
    # Filtro por NF no CD
    if filtros.get('nf_cd') is not None:
        query = query.filter(EntregaMonitorada.nf_cd == filtros['nf_cd'])
    
    return query

def gerar_excel_monitoramento(entregas, formato='multiplas_abas'):
    """Gera arquivo Excel com dados do monitoramento - sempre formato completo"""
    import pandas as pd  # Lazy import (~150 MB) — só carregado quando gera Excel

    # Cache para conversões de timezone (evita conversões repetidas)
    timezone_cache = {}
    
    def limpar_timezone(dt):
        """Remove timezone de datetime para compatibilidade com Excel - VERSÃO CACHE"""
        if dt is None:
            return None
        if dt in timezone_cache:
            return timezone_cache[dt]
        
        resultado = dt
        if hasattr(dt, 'replace') and hasattr(dt, 'tzinfo') and dt.tzinfo is not None:
            resultado = dt.replace(tzinfo=None)
        
        timezone_cache[dt] = resultado
        return resultado
    
    print(f"🔥 INICIANDO GERAÇÃO EXCEL para {len(entregas)} entregas...")
    
    # Prepara dados principais
    dados_principais = []
    dados_agendamentos = []
    dados_eventos = []
    dados_custos = []
    dados_logs = []
    dados_comentarios = []
    
    for i, entrega in enumerate(entregas):
        if i % 1000 == 0 and i > 0:
            print(f"📊 Processando entrega {i}/{len(entregas)}...")
        
        # Agendamento mais recente
        agendamento_recente = None
        if entrega.agendamentos:
            agendamento_recente = max(entrega.agendamentos, key=lambda x: x.criado_em)
        
        # Último log
        ultimo_log = None
        if entrega.logs:
            ultimo_log = max(entrega.logs, key=lambda x: x.data_hora)
        
        # Custo total extra
        custo_total = sum(custo.valor for custo in entrega.custos_extras if custo.valor)
        
        # Conta eventos, comentários
        qtd_eventos = len(entrega.eventos)
        # Usar comentários pré-carregados se disponíveis, senão fazer query
        if hasattr(entrega, '_comentarios_carregados'):
            qtd_comentarios = len(entrega._comentarios_carregados)
        else:
            qtd_comentarios = len([c for c in entrega.comentarios if c.resposta_a_id is None])
        
        # Formatar data de faturamento para dd/mm/aaaa
        data_faturamento_formatada = ''
        if entrega.data_faturamento:
            data_faturamento_formatada = entrega.data_faturamento.strftime('%d/%m/%Y')
        
        # finalizado_em já está em horário Brasil (armazenado naive)
        finalizado_em_brasil = entrega.finalizado_em if entrega.finalizado_em else None
        
        dados_principais.append({
            # 1ª coluna: Data de faturamento formatada
            'data_faturamento': data_faturamento_formatada,
            'numero_nf': entrega.numero_nf,
            'cliente': entrega.cliente,
            'cnpj_cliente': entrega.cnpj_cliente,
            'municipio': entrega.municipio,
            'uf': entrega.uf,
            'transportadora': entrega.transportadora,
            'vendedor': entrega.vendedor,
            'valor_nf': entrega.valor_nf,
            'data_embarque': limpar_timezone(entrega.data_embarque),
            'data_entrega_prevista': limpar_timezone(entrega.data_entrega_prevista),
            'data_agenda': limpar_timezone(entrega.data_agenda),
            'data_hora_entrega_realizada': limpar_timezone(entrega.data_hora_entrega_realizada),
            # Substituir 'entregue' por 'status_finalizacao'
            'status_finalizacao': entrega.status_finalizacao,
            # Adicionar finalizado_em e finalizado_por após status_finalizacao
            'finalizado_em': limpar_timezone(finalizado_em_brasil),
            'finalizado_por': entrega.finalizado_por,
            'lead_time': entrega.lead_time,
            'reagendar': entrega.reagendar,
            'motivo_reagendamento': entrega.motivo_reagendamento,
            'pendencia_financeira': entrega.pendencia_financeira,
            'nf_cd': entrega.nf_cd,
            'nova_nf': entrega.nova_nf,
            'observacao_operacional': entrega.observacao_operacional,
            'resposta_financeiro': entrega.resposta_financeiro,
            'criado_em': limpar_timezone(entrega.criado_em),
            'criado_por': entrega.criado_por,
            'qtd_agendamentos': len(entrega.agendamentos),
            'data_ultimo_agendamento': limpar_timezone(agendamento_recente.data_agendada if agendamento_recente else None),
            'protocolo_ultimo_agendamento': agendamento_recente.protocolo_agendamento if agendamento_recente else None,
            'qtd_eventos': qtd_eventos,
            'qtd_logs': len(entrega.logs),
            'ultimo_log_descricao': ultimo_log.descricao if ultimo_log else None,
            'ultimo_log_data': limpar_timezone(ultimo_log.data_hora if ultimo_log else None),
            'qtd_custos_extras': len(entrega.custos_extras),
            'valor_total_custos_extras': custo_total,
            'qtd_comentarios': qtd_comentarios,
            'possui_comentarios': entrega.possui_comentarios
        })
        
        # Agendamentos
        for ag in entrega.agendamentos:
            dados_agendamentos.append({
                'numero_nf': entrega.numero_nf,
                'cliente': entrega.cliente,
                'data_agendada': limpar_timezone(ag.data_agendada),
                'hora_agendada': ag.hora_agendada,
                'forma_agendamento': ag.forma_agendamento,
                'contato_agendamento': ag.contato_agendamento,
                'protocolo_agendamento': ag.protocolo_agendamento,
                'motivo': ag.motivo,
                'observacao': ag.observacao,
                'autor': ag.autor,
                'criado_em': limpar_timezone(ag.criado_em),
                'confirmado_em': limpar_timezone(ag.confirmado_em),
                'confirmado_por': ag.confirmado_por
            })
        
        # Eventos
        for ev in entrega.eventos:
            dados_eventos.append({
                'numero_nf': entrega.numero_nf,
                'cliente': entrega.cliente,
                'data_hora_chegada': limpar_timezone(ev.data_hora_chegada),
                'data_hora_saida': limpar_timezone(ev.data_hora_saida),
                'motorista': ev.motorista,
                'tipo_evento': ev.tipo_evento,
                'observacao': ev.observacao,
                'autor': ev.autor,
                'criado_em': limpar_timezone(ev.criado_em),
            })
        
        # Custos extras
        for custo in entrega.custos_extras:
            dados_custos.append({
                'numero_nf': entrega.numero_nf,
                'cliente': entrega.cliente,
                'tipo': custo.tipo,
                'valor': custo.valor,
                'motivo': custo.motivo,
                'autor': custo.autor,
                'criado_em': limpar_timezone(custo.criado_em),
            })
        
        # Logs
        for log in entrega.logs:
            dados_logs.append({
                'numero_nf': entrega.numero_nf,
                'cliente': entrega.cliente,
                'autor': log.autor,
                'data_hora': limpar_timezone(log.data_hora),
                'tipo': log.tipo,
                'descricao': log.descricao,
                'lembrete_para': log.lembrete_para,
            })
        
        # Comentários
        # Usar comentários pré-carregados se disponíveis
        comentarios_lista = []
        if hasattr(entrega, '_comentarios_carregados'):
            comentarios_lista = entrega._comentarios_carregados
        else:
            comentarios_lista = [c for c in entrega.comentarios if c.resposta_a_id is None]
            
        for comentario in comentarios_lista:
            qtd_respostas = len(comentario.respostas)
            dados_comentarios.append({
                'numero_nf': entrega.numero_nf,
                'cliente': entrega.cliente,
                'autor': comentario.autor,
                'texto': comentario.texto,
                'arquivo': comentario.arquivo,
                'criado_em': limpar_timezone(comentario.criado_em),
                'qtd_respostas': qtd_respostas
            })
    
    # Cria DataFrame principal
    df_principal = pd.DataFrame(dados_principais)
    
    # Cria arquivo temporário - sempre formato completo com múltiplas abas
    with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
        with pd.ExcelWriter(tmp_file.name) as writer:
            # Aba principal
            df_principal.to_excel(writer, sheet_name='Entregas', index=False)
            
            # Abas relacionadas
            if dados_agendamentos:
                df_agendamentos = pd.DataFrame(dados_agendamentos)
                df_agendamentos.to_excel(writer, sheet_name='Agendamentos', index=False)
            
            if dados_eventos:
                df_eventos = pd.DataFrame(dados_eventos)
                df_eventos.to_excel(writer, sheet_name='Eventos', index=False)
            
            if dados_custos:
                df_custos = pd.DataFrame(dados_custos)
                df_custos.to_excel(writer, sheet_name='Custos Extras', index=False)
            
            if dados_logs:
                df_logs = pd.DataFrame(dados_logs)
                df_logs.to_excel(writer, sheet_name='Logs', index=False)
            
            if dados_comentarios:
                df_comentarios = pd.DataFrame(dados_comentarios)
                df_comentarios.to_excel(writer, sheet_name='Comentários', index=False)
            
            # Aba de estatísticas
            estatisticas = {
                'Total de Entregas': len(entregas),
                'Entregas Finalizadas': len([e for e in entregas if e.status_finalizacao]),
                'Entregas Entregues': len([e for e in entregas if e.status_finalizacao == 'Entregue']),
                'Entregas Canceladas': len([e for e in entregas if e.status_finalizacao == 'Cancelada']),
                'Entregas Devolvidas': len([e for e in entregas if e.status_finalizacao == 'Devolvida']),
                'Entregas Sinistradas': len([e for e in entregas if e.status_finalizacao == 'Sinistro']),
                'Pendências Financeiras': len([e for e in entregas if e.pendencia_financeira]),
                'NFs no CD': len([e for e in entregas if e.nf_cd]),
                'Total Agendamentos': len(dados_agendamentos),
                'Total Eventos': len(dados_eventos),
                'Total Custos Extras': len(dados_custos),
                'Valor Total Custos': sum(custo['valor'] for custo in dados_custos if custo['valor']),
                'Total Logs': len(dados_logs),
                'Total Comentários': len(dados_comentarios)
            }
            
            df_stats = pd.DataFrame(list(estatisticas.items()), columns=['Métrica', 'Valor'])
            df_stats.to_excel(writer, sheet_name='Estatísticas', index=False)
        
        print(f"🎉 EXCEL GERADO em {timezone_cache.__len__()} conversões cache utilizadas")
        
        return tmp_file.name

@monitoramento_bp.route('/exportar', methods=['GET', 'POST'])
@login_required
@allow_vendedor_own_data()  # 🔒 PERMITIDO para vendedores (apenas seus dados)
def exportar_entregas():
    """Página para configurar e executar exportação"""
    form = ExportarMonitoramentoForm()
    
    if form.validate_on_submit():
        try:
            # Monta filtros baseado no formulário
            filtros = {}
            
            # Filtros predefinidos têm prioridade
            if form.mes_atual.data:
                hoje = date.today()
                primeiro_dia_mes = date(hoje.year, hoje.month, 1)
                filtros['data_faturamento_inicio'] = primeiro_dia_mes
                filtros['data_faturamento_fim'] = hoje
            elif form.ultimo_mes.data:
                hoje = date.today()
                if hoje.month == 1:
                    primeiro_dia_mes_passado = date(hoje.year - 1, 12, 1)
                    ultimo_dia_mes_passado = date(hoje.year, 1, 1) - timedelta(days=1)
                else:
                    primeiro_dia_mes_passado = date(hoje.year, hoje.month - 1, 1)
                    ultimo_dia_mes_passado = date(hoje.year, hoje.month, 1) - timedelta(days=1)
                filtros['data_faturamento_inicio'] = primeiro_dia_mes_passado
                filtros['data_faturamento_fim'] = ultimo_dia_mes_passado
            else:
                # Filtros de período manuais
                if form.data_faturamento_inicio.data:
                    filtros['data_faturamento_inicio'] = form.data_faturamento_inicio.data
                if form.data_faturamento_fim.data:
                    filtros['data_faturamento_fim'] = form.data_faturamento_fim.data
                if form.data_embarque_inicio.data:
                    filtros['data_embarque_inicio'] = form.data_embarque_inicio.data
                if form.data_embarque_fim.data:
                    filtros['data_embarque_fim'] = form.data_embarque_fim.data
            
            # Filtros de dados
            for campo in ['cliente', 'cnpj', 'uf', 'municipio', 'transportadora', 'vendedor', 'numero_nf']:
                valor = getattr(form, campo).data
                if valor and valor.strip():
                    filtros[campo] = valor.strip()
            
            # Filtros de status
            if form.entregue.data:
                filtros['entregue'] = form.entregue.data == 'true'
            if form.pendencia_financeira.data:
                filtros['pendencia_financeira'] = form.pendencia_financeira.data == 'true'
            if form.nf_cd.data:
                filtros['nf_cd'] = form.nf_cd.data == 'true'
            if form.status_finalizacao.data:
                filtros['status_finalizacao'] = form.status_finalizacao.data
            
            # Filtro pendentes
            if form.pendentes.data:
                filtros['status_finalizacao'] = 'nao_finalizado'
            
            # Query base
            query = EntregaMonitorada.query
            
            # 🔒 FILTRO PARA VENDEDORES NA EXPORTAÇÃO - Só exportam seus dados
            vendedor_filtro = get_vendedor_filter_query()
            if vendedor_filtro == "ACESSO_NEGADO":
                flash('Acesso negado. Perfil sem permissão para exportação.', 'danger')
                return redirect(url_for('main.dashboard'))
            elif vendedor_filtro is not None:  # Vendedor específico
                query = query.filter(EntregaMonitorada.vendedor.ilike(f'%{vendedor_filtro}%'))
                # Para vendedores, também aplica filtro por NF através do faturamento
                if current_user.perfil == 'vendedor':
                    from app.faturamento.models import RelatorioFaturamentoImportado
                    nfs_vendedor = db.session.query(RelatorioFaturamentoImportado.numero_nf).filter(
                        RelatorioFaturamentoImportado.vendedor.ilike(f'%{vendedor_filtro}%')
                    ).subquery()
                    query = query.filter(
                        db.or_(
                            EntregaMonitorada.vendedor.ilike(f'%{vendedor_filtro}%'),
                            EntregaMonitorada.numero_nf.in_(db.select([nfs_vendedor.c.numero_nf]))
                        )
                    )
            
            # Aplica filtros
            query = aplicar_filtros_exportacao(query, filtros)

            # 🚀 BUSCA OTIMIZADA - Carrega relacionamentos em uma query
            # 🚀 QUERY OTIMIZADA: Carrega todos os relacionamentos de uma vez
            from sqlalchemy.orm import joinedload
            entregas = query.options(
                joinedload(EntregaMonitorada.agendamentos),
                joinedload(EntregaMonitorada.logs),
                joinedload(EntregaMonitorada.eventos),
                joinedload(EntregaMonitorada.custos_extras)
                # Removido joinedload(EntregaMonitorada.comentarios) devido a lazy='dynamic'
            ).order_by(EntregaMonitorada.numero_nf).all()

            # 🚀 OTIMIZAÇÃO: Carregar TODOS os comentários em UMA ÚNICA QUERY
            # Antes: N queries (uma por entrega) - LENTO para 2000-3000 entregas
            # Depois: 1 query apenas - RÁPIDO!
            if entregas:
                entrega_ids = [e.id for e in entregas]
                comentarios_dict = {}

                # Busca todos os comentários principais (sem resposta_a_id) de uma vez
                comentarios = ComentarioNF.query.filter(
                    ComentarioNF.entrega_id.in_(entrega_ids),
                    ComentarioNF.resposta_a_id.is_(None)
                ).all()

                # Agrupa comentários por entrega_id
                for comentario in comentarios:
                    if comentario.entrega_id not in comentarios_dict:
                        comentarios_dict[comentario.entrega_id] = []
                    comentarios_dict[comentario.entrega_id].append(comentario)

                # Atribui comentários pré-carregados a cada entrega
                for entrega in entregas:
                    entrega._comentarios_carregados = comentarios_dict.get(entrega.id, [])
            
            if not entregas:
                flash('❌ Nenhuma entrega encontrada com os filtros especificados', 'warning')
                return render_template('monitoramento/exportar_entregas.html', form=form)
            
            # 🚀 LOG DE PERFORMANCE
            import time
            start_time = time.time()
            print(f"📊 INICIANDO EXPORTAÇÃO: {len(entregas)} entregas")
            
            # Gera arquivo Excel - sempre formato completo
            arquivo_path = gerar_excel_monitoramento(entregas, 'multiplas_abas')
            
            # Nome do arquivo para download
            nome_arquivo = form.nome_arquivo.data
            if not nome_arquivo.endswith('.xlsx'):
                nome_arquivo += '.xlsx' # type: ignore
            
            # 🔒 Adiciona informação do vendedor no nome do arquivo se for vendedor
            if current_user.perfil == 'vendedor':
                nome_base = nome_arquivo.replace('.xlsx', '')
                nome_arquivo = f'{nome_base}_vendedor_{current_user.vendedor_vinculado or current_user.nome.replace(" ", "_")}.xlsx'
            
            # 🚀 LOG FINAL DE PERFORMANCE
            total_time = time.time() - start_time
            print(f"🎉 EXPORTAÇÃO CONCLUÍDA em {total_time:.2f}s")
            
            flash(f'✅ Exportação concluída! {len(entregas)} entregas exportadas em {total_time:.2f}s.', 'success')
            
            # Envia arquivo para download
            def cleanup_file(): # type: ignore
                try:
                    os.unlink(arquivo_path)
                except Exception as e:
                    logger.error(f"Erro ao excluir arquivo: {e}")
                    pass
            
            return send_file(
                arquivo_path,
                as_attachment=True,
                download_name=nome_arquivo,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            
        except Exception as e:
            flash(f'❌ Erro ao gerar exportação: {str(e)}', 'danger')
            return render_template('monitoramento/exportar_entregas.html', form=form)
    
    return render_template('monitoramento/exportar_entregas.html', form=form)

# Rota administrativa de migração removida - não necessária

# ============================================================================
# CANHOTOS DE ENTREGA
# ============================================================================

@monitoramento_bp.route('/<int:id>/upload_canhoto', methods=['POST'])
@login_required
@allow_vendedor_own_data()  # 🔒 PERMITIDO para vendedores (apenas seus dados)
def upload_canhoto(id):
    """Upload individual de canhoto para uma entrega"""
    entrega = EntregaMonitorada.query.get_or_404(id)
    
    # 🔒 VERIFICAÇÃO ESPECÍFICA PARA VENDEDORES
    if current_user.perfil == 'vendedor':
        if not check_vendedor_permission(vendedor_nome=entrega.vendedor, numero_nf=entrega.numero_nf):
            return jsonify({'success': False, 'message': 'Acesso negado'})
    
    if 'canhoto' not in request.files:
        return jsonify({'success': False, 'message': 'Nenhum arquivo enviado'})
    
    file = request.files['canhoto']
    if not file or not file.filename:
        return jsonify({'success': False, 'message': 'Arquivo inválido'})
    
    # Validar extensão
    extensao = file.filename.split('.')[-1].lower()
    if extensao not in ['jpg', 'jpeg', 'jfif', 'png', 'pdf']:
        return jsonify({'success': False, 'message': 'Apenas arquivos JPG, JFIF, PNG ou PDF são permitidos'})
    
    try:
        # 🌐 Salvar no S3
        from app.utils.file_storage import get_file_storage
        storage = get_file_storage()
        file_path = storage.save_file(
            file=file,
            folder='canhotos',
            allowed_extensions=['jpg', 'jpeg', 'jfif', 'png', 'pdf']
        )

        if file_path:
            # Remove canhoto anterior se existir
            if entrega.canhoto_arquivo:
                try:
                    # TODO: Implementar exclusão do arquivo anterior no S3 se necessário
                    pass
                except Exception as e:
                    logger.error(f"Erro ao excluir arquivo: {e}")
                    pass

            entrega.canhoto_arquivo = file_path
            db.session.commit()

            return jsonify({
                'success': True,
                'message': f'Canhoto anexado com sucesso para NF {entrega.numero_nf}!'
            })
        else:
            return jsonify({'success': False, 'message': 'Erro ao salvar arquivo'})
            
    except Exception as e:
        current_app.logger.error(f"Erro ao fazer upload do canhoto: {str(e)}")
        return jsonify({'success': False, 'message': f'Erro interno: {str(e)}'})

@monitoramento_bp.route('/upload_canhotos_lote', methods=['GET', 'POST'])
@login_required
@require_monitoramento_geral()  # 🔒 BLOQUEADO para vendedores (apenas staff)
def upload_canhotos_lote():
    """Upload em lote de canhotos identificados pelo nome do arquivo"""
    if request.method == 'POST':
        if 'canhotos' not in request.files:
            flash('Nenhum arquivo enviado.', 'warning')
            return redirect(request.url)
        
        files = request.files.getlist('canhotos')
        
        resultados = {
            'sucesso': [],
            'erro': [],
            'nao_encontrado': []
        }
        
        for file in files:
            if not file or not file.filename:
                continue
            
            try:
                # Extrair número da NF do nome do arquivo (ex: 133526.jpeg -> 133526)
                nome_arquivo = file.filename.split('.')[0]
                numero_nf = ''.join(filter(str.isdigit, nome_arquivo))
                
                if not numero_nf:
                    resultados['erro'].append(f'{file.filename}: Nome inválido (deve conter número da NF)')
                    continue
                
                # Buscar entrega pela NF
                entrega = EntregaMonitorada.query.filter_by(numero_nf=numero_nf).first()
                
                if not entrega:
                    resultados['nao_encontrado'].append(f'{file.filename}: NF {numero_nf} não encontrada')
                    continue
                
                # Validar extensão
                extensao = file.filename.split('.')[-1].lower()
                if extensao not in ['jpg', 'jpeg', 'jfif', 'png', 'pdf']:
                    resultados['erro'].append(f'{file.filename}: Extensão não permitida')
                    continue
                
                # Salvar arquivo
                from app.utils.file_storage import get_file_storage
                storage = get_file_storage()
                file_path = storage.save_file(
                    file=file,
                    folder='canhotos',
                    allowed_extensions=['jpg', 'jpeg', 'jfif', 'png', 'pdf']
                )
                
                if file_path:
                    # Remove canhoto anterior se existir
                    if entrega.canhoto_arquivo:
                        try:
                            # TODO: Implementar exclusão do arquivo anterior no S3 se necessário
                            pass
                        except Exception as e:
                            logger.error(f"Erro ao excluir arquivo: {e}")
                            pass
                    
                    entrega.canhoto_arquivo = file_path
                    resultados['sucesso'].append(f'NF {numero_nf}: {file.filename}')
                else:
                    resultados['erro'].append(f'{file.filename}: Erro ao salvar')
                    
            except Exception as e:
                current_app.logger.error(f"Erro ao processar {file.filename}: {str(e)}")
                resultados['erro'].append(f'{file.filename}: {str(e)}')
        
        # Salvar todas as alterações
        db.session.commit()
        
        # Exibir resultados
        if resultados['sucesso']:
            flash(f"✅ {len(resultados['sucesso'])} canhoto(s) anexado(s) com sucesso!", 'success')
        
        if resultados['erro']:
            for erro in resultados['erro']:
                flash(f"❌ {erro}", 'danger')
        
        if resultados['nao_encontrado']:
            for nao_encontrado in resultados['nao_encontrado']:
                flash(f"⚠️ {nao_encontrado}", 'warning')
        
        return redirect(request.url)
    
    return render_template('monitoramento/upload_canhotos_lote.html')

@monitoramento_bp.route('/<int:id>/visualizar_canhoto')
@login_required
@allow_vendedor_own_data()  # 🔒 PERMITIDO para vendedores (apenas seus dados)
def visualizar_canhoto(id):
    """Visualizar/baixar canhoto de uma entrega"""
    entrega = EntregaMonitorada.query.get_or_404(id)
    
    # 🔒 VERIFICAÇÃO ESPECÍFICA PARA VENDEDORES
    if current_user.perfil == 'vendedor':
        if not check_vendedor_permission(vendedor_nome=entrega.vendedor, numero_nf=entrega.numero_nf):
            flash('Acesso negado. Você só pode visualizar entregas dos seus clientes.', 'danger')
            return redirect(url_for('monitoramento.listar_entregas'))
    
    if not entrega.canhoto_arquivo:
        flash('Esta entrega não possui canhoto anexado.', 'warning')
        return redirect(request.referrer or url_for('monitoramento.listar_entregas'))
    
    try:
        from app.utils.file_storage import get_file_storage
        storage = get_file_storage()
        
        # Para arquivos S3 (novos)
        if not entrega.canhoto_arquivo.startswith('uploads/'):
            url = storage.get_file_url(entrega.canhoto_arquivo)
            if url:
                return redirect(url)
            else:
                flash('Erro ao gerar URL do arquivo.', 'danger')
                return redirect(request.referrer or url_for('monitoramento.listar_entregas'))
        else:
            # Para arquivos locais (antigos) - compatibilidade
            from flask import send_from_directory
            import os
            return send_from_directory(
                os.path.join(current_app.root_path, 'static'), 
                entrega.canhoto_arquivo
            )
            
    except Exception as e:
        current_app.logger.error(f"Erro ao acessar canhoto: {str(e)}")
        flash('Erro ao acessar o arquivo.', 'danger')
        return redirect(request.referrer or url_for('monitoramento.listar_entregas'))

def sincronizar_agendamento_pedido(entrega):
    """
    Sincroniza agendamento de entrega com nf_cd=True para o pedido correspondente
    """
    try:
        if not entrega.nf_cd:
            return True, "Entrega não está marcada como NF no CD"
        
        # Buscar pedido pela NF
        pedido = Pedido.query.filter_by(nf=entrega.numero_nf).first()
        if not pedido:
            return False, f"Pedido não encontrado para NF {entrega.numero_nf}"
        
        # Buscar último agendamento
        ultimo_agendamento = AgendamentoEntrega.query.filter_by(entrega_id=entrega.id)\
            .order_by(AgendamentoEntrega.criado_em.desc()).first()
        
        if ultimo_agendamento:
            # Transferir dados do agendamento para as Separações (não para VIEW Pedido)
            Separacao.query.filter_by(
                separacao_lote_id=pedido.separacao_lote_id,
                num_pedido=pedido.num_pedido
            ).update({
                'agendamento': ultimo_agendamento.data_agendada,
                'protocolo': ultimo_agendamento.protocolo_agendamento
            })

            # ✅ NÃO limpar expedição aqui - apenas no evento "NF no CD"

            db.session.commit()
            return True, f"Pedido {pedido.num_pedido} atualizado com agendamento"
        else:
            return True, "Nenhum agendamento encontrado para sincronizar"
            
    except Exception as e:
        db.session.rollback()
        return False, f"Erro ao sincronizar agendamento: {str(e)}"

# ===========================
# API Routes
# ===========================

@monitoramento_bp.route('/api/entrega/<int:entrega_id>')
@login_required
@allow_vendedor_own_data()
def api_get_entrega(entrega_id):
    """
    Retorna dados de uma entrega específica
    """
    entrega = EntregaMonitorada.query.get_or_404(entrega_id)
    
    # Verificar se vendedor tem acesso
    vendedor_filtro = get_vendedor_filter_query()
    if vendedor_filtro and vendedor_filtro != "ACESSO_NEGADO":
        if not (entrega.vendedor and vendedor_filtro.lower() in entrega.vendedor.lower()):
            return jsonify({'error': 'Acesso negado'}), 403
    
    # Buscar contato de agendamento para enriquecer resposta
    contatos_cache = _get_contatos_agendamento()
    contato_dados = contatos_cache.get(entrega.cnpj_cliente, {})

    return jsonify({
        'entrega': {
            'id': entrega.id,
            'numero_nf': entrega.numero_nf,
            'cliente': entrega.cliente,
            'cnpj_cliente': entrega.cnpj_cliente,
            'transportadora': entrega.transportadora,
            'municipio': entrega.municipio,
            'uf': entrega.uf,
            'vendedor': entrega.vendedor,
            'valor_nf': entrega.valor_nf,
            'data_faturamento': entrega.data_faturamento.strftime('%Y-%m-%d') if entrega.data_faturamento else None,
            'data_embarque': entrega.data_embarque.strftime('%Y-%m-%d') if entrega.data_embarque else None,
            'data_entrega_prevista': entrega.data_entrega_prevista.strftime('%Y-%m-%d') if entrega.data_entrega_prevista else None,
            'data_agenda': entrega.data_agenda.strftime('%Y-%m-%d') if entrega.data_agenda else None,
            'entregue': entrega.entregue,
            'reagendar': entrega.reagendar,
            'motivo_reagendamento': entrega.motivo_reagendamento,
            'observacao_operacional': entrega.observacao_operacional,
            'pendencia_financeira': entrega.pendencia_financeira,
            'resposta_financeiro': entrega.resposta_financeiro,
        },
        'contato_agendamento': {
            'forma': contato_dados.get('forma'),
            'contato': contato_dados.get('contato'),
            'observacao': contato_dados.get('observacao'),
            'horario_de': contato_dados.get('horario_recebimento_de'),
            'horario_ate': contato_dados.get('horario_recebimento_ate'),
            'obs_recebimento': contato_dados.get('observacoes_recebimento'),
            'nao_aceita_nf_pallet': contato_dados.get('nao_aceita_nf_pallet', False),
        } if contato_dados else None
    })

@monitoramento_bp.route('/api/entrega/<int:entrega_id>/dados')
@login_required
def api_get_entrega_dados(entrega_id):
    """
    Retorna dados completos de uma entrega incluindo separacao_lote_id
    """
    entrega = EntregaMonitorada.query.get_or_404(entrega_id)

    return jsonify({
        'id': entrega.id,
        'numero_nf': entrega.numero_nf,
        'cliente': entrega.cliente,
        'cnpj_cliente': entrega.cnpj_cliente,
        'separacao_lote_id': entrega.separacao_lote_id,
        'data_agenda': entrega.data_agenda.isoformat() if entrega.data_agenda else None,
        'municipio': entrega.municipio,
        'uf': entrega.uf,
        'transportadora': entrega.transportadora,
        'vendedor': entrega.vendedor
    })


# ============================================================================
# 📄 DOWNLOAD PDF/XML DE NF DO ODOO
# ============================================================================

@monitoramento_bp.route('/nf/<numero_nf>/pdf')
@login_required
def download_nf_pdf(numero_nf):
    """
    Faz download do PDF (DANFE) da NF direto do Odoo.
    Busca o account.move pelo número da NF e retorna o PDF em base64 decodificado.
    Campo Odoo: l10n_br_pdf_aut_nfe (DANFE NF-e)
    """
    import base64
    from io import BytesIO

    try:
        from app.odoo.utils.connection import get_odoo_connection

        connection = get_odoo_connection()
        if not connection.authenticate():
            flash('Erro ao conectar com Odoo', 'danger')
            return redirect(request.referrer or url_for('monitoramento.listar_entregas'))

        # Buscar a NF no Odoo pelo número
        # O campo l10n_br_numero_nota_fiscal contém o número da NF
        nfs = connection.search_read(
            'account.move',
            [
                ('l10n_br_numero_nota_fiscal', '=', numero_nf),
                ('move_type', '=', 'out_invoice')  # Apenas NF de venda
            ],
            ['id', 'name', 'l10n_br_pdf_aut_nfe']
        )

        if not nfs:
            flash(f'NF {numero_nf} não encontrada no Odoo', 'warning')
            return redirect(request.referrer or url_for('monitoramento.listar_entregas'))

        nf = nfs[0]
        pdf_base64 = nf.get('l10n_br_pdf_aut_nfe')

        if not pdf_base64:
            flash(f'DANFE da NF {numero_nf} não disponível no Odoo', 'warning')
            return redirect(request.referrer or url_for('monitoramento.listar_entregas'))

        # Decodificar o PDF
        pdf_bytes = base64.b64decode(pdf_base64)

        # Nome do arquivo
        filename = f'DANFE_NF_{numero_nf}.pdf'

        return send_file(
            BytesIO(pdf_bytes),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        current_app.logger.error(f"Erro ao baixar PDF da NF {numero_nf}: {e}")
        flash(f'Erro ao baixar PDF: {str(e)}', 'danger')
        return redirect(request.referrer or url_for('monitoramento.listar_entregas'))


@monitoramento_bp.route('/nf/<numero_nf>/xml')
@login_required
def download_nf_xml(numero_nf):
    """
    Faz download do XML da NF direto do Odoo.
    Busca o account.move pelo número da NF e retorna o XML em base64 decodificado.
    Campo Odoo: l10n_br_xml_aut_nfe (XML NF-e)
    """
    import base64
    from io import BytesIO

    try:
        from app.odoo.utils.connection import get_odoo_connection

        connection = get_odoo_connection()
        if not connection.authenticate():
            flash('Erro ao conectar com Odoo', 'danger')
            return redirect(request.referrer or url_for('monitoramento.listar_entregas'))

        # Buscar a NF no Odoo pelo número
        nfs = connection.search_read(
            'account.move',
            [
                ('l10n_br_numero_nota_fiscal', '=', numero_nf),
                ('move_type', '=', 'out_invoice')  # Apenas NF de venda
            ],
            ['id', 'name', 'l10n_br_xml_aut_nfe']
        )

        if not nfs:
            flash(f'NF {numero_nf} não encontrada no Odoo', 'warning')
            return redirect(request.referrer or url_for('monitoramento.listar_entregas'))

        nf = nfs[0]
        xml_base64 = nf.get('l10n_br_xml_aut_nfe')

        if not xml_base64:
            flash(f'XML da NF {numero_nf} não disponível no Odoo', 'warning')
            return redirect(request.referrer or url_for('monitoramento.listar_entregas'))

        # Decodificar o XML
        xml_bytes = base64.b64decode(xml_base64)

        # Nome do arquivo
        filename = f'XML_NF_{numero_nf}.xml'

        return send_file(
            BytesIO(xml_bytes),
            mimetype='application/xml',
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        current_app.logger.error(f"Erro ao baixar XML da NF {numero_nf}: {e}")
        flash(f'Erro ao baixar XML: {str(e)}', 'danger')
        return redirect(request.referrer or url_for('monitoramento.listar_entregas'))

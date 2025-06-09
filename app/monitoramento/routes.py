from flask import Blueprint, render_template, request, redirect, url_for, flash, session, send_from_directory
from flask_login import login_required, current_user
from datetime import datetime, date
import os
from werkzeug.utils import secure_filename
from sqlalchemy import func
from sqlalchemy.orm import aliased

from collections import defaultdict

import re

from app import db
from app.monitoramento.models import (
    EntregaMonitorada,
    EventoEntrega,
    CustoExtraEntrega,
    RegistroLogEntrega,
    AgendamentoEntrega,
    ComentarioNF
)
from app.monitoramento.forms import (
    LogEntregaForm,
    EventoEntregaForm,
    CustoExtraForm,
    AgendamentoEntregaForm,
    FormComentarioNF
)

from app.financeiro.models import PendenciaFinanceiraNF

from app.cadastros_agendamento.models import ContatoAgendamento

from app.utils.sincronizar_todas_entregas import sincronizar_todas_entregas
from app.pedidos.models import Pedido  # ✅ ADICIONADO: Para controle de status NF no CD

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, '..', '..', 'uploads', 'entregas')
os.makedirs(UPLOAD_DIR, exist_ok=True)

monitoramento_bp = Blueprint('monitoramento', __name__, url_prefix='/monitoramento')

def processar_nf_cd_pedido(entrega_id):
    """
    ✅ FUNÇÃO ULTRA SIMPLIFICADA: Processa quando uma NF volta para o CD
    
    Implementa o item 2-d do processo_completo.md:
    - Busca o pedido diretamente pela NF (coluna "nf" na tabela pedidos)
    - Reseta o pedido para permitir nova cotação
    """
    try:
        entrega = EntregaMonitorada.query.get(entrega_id)
        if not entrega:
            return False, "Entrega não encontrada"
        
        print(f"[DEBUG] 🔍 Processando NF no CD para NF {entrega.numero_nf}")
        
        # ✅ MÉTODO ULTRA SIMPLIFICADO: Busca pedido diretamente pela NF
        pedido = Pedido.query.filter_by(nf=entrega.numero_nf).first()
        
        if not pedido:
            msg_erro = f"Pedido não encontrado para NF {entrega.numero_nf}"
            print(f"[DEBUG] ❌ {msg_erro}")
            return True, msg_erro
        
        # ✅ PEDIDO ENCONTRADO: Marca como "NF no CD" sem apagar a NF
        print(f"[DEBUG] ✅ Pedido {pedido.num_pedido} encontrado diretamente pela NF {entrega.numero_nf}")
        print(f"[DEBUG] 📦 Marcando pedido {pedido.num_pedido} como 'NF no CD'...")
        
        # ✅ NOVO: Marca como NF no CD sem apagar a NF (preserva histórico)
        pedido.nf_cd = True
        pedido.data_embarque = None
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
def visualizar_entrega(id):
    entrega = EntregaMonitorada.query.get_or_404(id)

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

    return render_template(
        'monitoramento/visualizar_entrega.html',
        entrega=entrega,
        form_log=form_log,
        form_evento=form_evento,
        form_custo=form_custo,
        form_agendamento=form_agendamento,
        form=form_comentario,
        comentarios=comentarios,
        feedback=feedback
    )

@monitoramento_bp.route('/<int:id>/adicionar_log', methods=['POST'])
@login_required
def adicionar_log(id):
    entrega = EntregaMonitorada.query.get_or_404(id)
    form_log = LogEntregaForm()

    if form_log.validate_on_submit():
        log = RegistroLogEntrega(
            entrega_id=entrega.id,
            autor=current_user.nome,
            descricao=form_log.descricao.data,
            tipo=form_log.tipo.data,
            lembrete_para=form_log.lembrete_para.data
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
            criado_em=datetime.utcnow() 
        )
        db.session.add(evento)

        # ✅ IMPLEMENTAÇÃO APRIMORADA DO ITEM 2-d: NF no CD
        if form_evento.tipo_evento.data == "NF no CD":
            entrega.nf_cd = True
            entrega.entregue = False
            entrega.data_embarque = None
            entrega.data_entrega_prevista = None
            entrega.data_agenda = None
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
            autor=current_user.nome
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
        ag = AgendamentoEntrega(
            entrega_id=entrega.id,
            data_agendada=form_agendamento.data_agendada.data,
            hora_agendada=form_agendamento.hora_agendada.data,
            forma_agendamento=form_agendamento.forma_agendamento.data,
            contato_agendamento=form_agendamento.contato_agendamento.data,
            protocolo_agendamento=form_agendamento.protocolo_agendamento.data,
            motivo=form_agendamento.motivo.data,
            observacao=form_agendamento.observacao.data,
            autor=current_user.nome
        )
        db.session.add(ag)

        entrega.data_agenda = form_agendamento.data_agendada.data
        entrega.data_entrega_prevista = form_agendamento.data_agendada.data
        db.session.commit()

        session['feedback'] = 'agendamento'
    else:
        flash('Erro ao validar Agendamento.', 'danger')

    return redirect(url_for('monitoramento.visualizar_entrega', id=entrega.id))

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

    descricao_log = ""

    if status_finalizacao in ["Troca de NF", "Cancelada", "Devolvida"]:
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

    entrega.finalizado_em = datetime.utcnow()
    entrega.finalizado_por = current_user.nome

    db.session.commit()

    flash('Entrega atualizada com sucesso.', 'success')
    return redirect(url_for('monitoramento.visualizar_entrega', id=id))





@monitoramento_bp.route('/<int:id>/resolver-pendencia', methods=['POST'])
@login_required
def resolver_pendencia(id):
    entrega = EntregaMonitorada.query.get_or_404(id)
    entrega.pendencia_financeira = False
    entrega.resposta_financeiro = f"Resolvido por {current_user.nome} em {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    db.session.commit()
    return redirect(url_for('monitoramento.listar_entregas', **request.args))

@monitoramento_bp.route('/listar_entregas')
@login_required
def listar_entregas():
    query = EntregaMonitorada.query

    status = request.args.get('status')
    if status == 'pendente':
        query = query.filter(EntregaMonitorada.entregue == False)
    elif status == 'entregue':
        query = query.filter(EntregaMonitorada.entregue == True)
    elif status == 'atrasada':
        query = query.filter(
            EntregaMonitorada.entregue == False,
            EntregaMonitorada.data_entrega_prevista != None,
            EntregaMonitorada.data_entrega_prevista < date.today()
        )
    elif status == 'sem_previsao':
        query = query.filter(EntregaMonitorada.data_entrega_prevista == None)
    elif status == 'sem_agendamento':
        subquery = db.session.query(AgendamentoEntrega.entrega_id).distinct()
        query = query.filter(
            EntregaMonitorada.cnpj_cliente.in_(
                db.session.query(ContatoAgendamento.cnpj)
            ),
            ~EntregaMonitorada.id.in_(subquery)
        )
    elif status == 'reagendar':
        query = query.filter(EntregaMonitorada.reagendar == True)
    elif status == 'pendencia_financeira':
        query = query.join(PendenciaFinanceiraNF, PendenciaFinanceiraNF.entrega_id == EntregaMonitorada.id)
        query = query.filter(PendenciaFinanceiraNF.respondida_em == None)

    if numero_nf := request.args.get('numero_nf'):
        query = query.filter(EntregaMonitorada.numero_nf.ilike(f"%{numero_nf}%"))

    if transportadora := request.args.get('transportadora'):
        query = query.filter(EntregaMonitorada.transportadora.ilike(f"%{transportadora}%"))

    if cliente := request.args.get('cliente'):
        query = query.filter(EntregaMonitorada.cliente.ilike(f"%{cliente}%"))

    if cnpj := request.args.get('cnpj_cliente'):
        query = query.filter(EntregaMonitorada.cnpj_cliente.ilike(f"%{cnpj}%"))

    if status == 'com_comentarios':
        query = query.join(ComentarioNF).group_by(EntregaMonitorada.id)

    if uf := request.args.get('uf'):
        query = query.filter(EntregaMonitorada.uf.ilike(f"%{uf}%"))

    if protocolo := request.args.get('protocolo'):
        query = query.join(EntregaMonitorada.agendamentos).filter(
            EntregaMonitorada.agendamentos.any(
                AgendamentoEntrega.protocolo_agendamento.ilike(f"%{protocolo}%")
            )
        )

    if data_emissao := request.args.get('data_emissao'):
        try:
            dt = datetime.strptime(data_emissao, "%d-%m-%Y").date()
            query = query.filter(EntregaMonitorada.data_faturamento == dt)
        except ValueError:
            pass

    if data_embarque := request.args.get('data_embarque'):
        try:
            dt = datetime.strptime(data_embarque, "%d-%m-%Y").date()
            query = query.filter(EntregaMonitorada.data_embarque == dt)
        except ValueError:
            pass

    if data_entrega := request.args.get('data_entrega'):
        try:
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

    entregas = query.all()

    # ------------------------------
    # Montagem do dicionário cnpjs
    cnpjs_com_agendamento = {c.cnpj for c in ContatoAgendamento.query.all()}

    agrupar = request.args.get('agrupar') == 'status'
    entregas_agrupadas = defaultdict(list)

    if agrupar:
        entregas_agrupadas = {
            '🔴 Atrasadas': [],
            '⚠️ Sem Agendamento': [],
            '🔁 Reagendar': [],
            '⚪ Sem Previsão': [],
            '🟡 Pendentes': [],
            '✅ Entregues': []
        }

        for e in entregas:
            if e.entregue:
                entregas_agrupadas['✅ Entregues'].append(e)
            elif e.reagendar:
                entregas_agrupadas['🔁 Reagendar'].append(e)
            elif e.cnpj_cliente in cnpjs_com_agendamento and len(e.agendamentos) == 0:
                entregas_agrupadas['⚠️ Sem Agendamento'].append(e)
            elif e.data_entrega_prevista and e.data_entrega_prevista < date.today():
                entregas_agrupadas['🔴 Atrasadas'].append(e)
            elif not e.data_entrega_prevista:
                entregas_agrupadas['⚪ Sem Previsão'].append(e)
            else:
                entregas_agrupadas['🟡 Pendentes'].append(e)

        # Remove grupos vazios
        entregas_agrupadas = {k: v for k, v in entregas_agrupadas.items() if v}

    page = request.args.get('page', 1, type=int)
    per_page = 20
    paginacao = query.paginate(page=page, per_page=per_page)

    return render_template(
        'monitoramento/listar_entregas.html',
        paginacao=paginacao,
        entregas=paginacao.items,
        entregas_agrupadas=entregas_agrupadas,
        agrupar=agrupar,
        current_date=date.today(),
        contatos_agendamento=cnpjs_com_agendamento,
        current_user=current_user
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
        
        # 4. Entregas com NF não importada no faturamento
        todas_entregas = EntregaMonitorada.query.all()
        nfs_nao_importadas = 0
        
        for entrega in todas_entregas:
            nf_fat = RelatorioFaturamentoImportado.query.filter_by(numero_nf=entrega.numero_nf).first()
            if not nf_fat:
                nfs_nao_importadas += 1
        
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
        [
            *((log.data_hora, 'Log', log.autor, f"{log.tipo}: {log.descricao}") for log in logs),
            *((evento.criado_em, 'Evento', evento.autor, 
               f"{evento.tipo_evento}: {evento.observacao} - Chegada: {evento.data_hora_chegada.strftime('%d/%m/%Y %H:%M') if evento.data_hora_chegada else 'Sem registro'}") for evento in eventos),
            *((custo.criado_em, 'Custo', custo.autor, f"{custo.tipo}: R$ {custo.valor:.2f} - {custo.motivo}") for custo in custos),
            *((ag.criado_em, 'Agendamento', ag.autor, f"Agendado por: {ag.forma_agendamento} Data: {ag.data_agendada.strftime('%d/%m/%Y')} - {ag.hora_agendada.strftime('%H:%M') if ag.hora_agendada else 'Sem horário'} - Protocolo {ag.protocolo_agendamento}- Motivo: {ag.motivo}") for ag in agendamentos),
            *( [(entrega.finalizado_em, 'Finalização', entrega.finalizado_por, f"Entrega finalizada em: {entrega.data_hora_entrega_realizada.strftime('%d/%m/%Y-%H:%M') if entrega.data_hora_entrega_realizada else 'Data não informada'}"
)] if entrega.finalizado_em else [] ),
        ],
        key=lambda x: x[0], reverse=True
    )

    return render_template('monitoramento/historico.html', entrega=entrega, historico=historico_completo)



@monitoramento_bp.route('/<int:id>/arquivos', methods=['GET', 'POST'])
@login_required
def visualizar_arquivos(id):
    entrega = EntregaMonitorada.query.get_or_404(id)
    pasta = os.path.join(UPLOAD_DIR, str(entrega.id))
    os.makedirs(pasta, exist_ok=True)

    if request.method == 'POST':
        if 'arquivo' not in request.files:
            flash("Nenhum arquivo enviado.", 'warning')
            return redirect(request.url)
        file = request.files['arquivo']
        if file and file.filename:
            filename = secure_filename(file.filename)
            file.save(os.path.join(pasta, filename))
            flash("Arquivo salvo com sucesso.", 'success')
            return redirect(request.url)

    arquivos = os.listdir(pasta)
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
    pasta = os.path.join(UPLOAD_DIR, str(entrega_id))
    return send_from_directory(pasta, filename)

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
def adicionar_comentario(id):
    form = FormComentarioNF()

    if form.validate_on_submit():
        arquivo_nome = None
        if form.arquivo.data:
            arquivo_nome = secure_filename(form.arquivo.data.filename)
            pasta_comentarios = os.path.join(UPLOAD_DIR, "comentarios_nf")
            os.makedirs(pasta_comentarios, exist_ok=True)
            form.arquivo.data.save(os.path.join(pasta_comentarios, arquivo_nome))

        comentario = ComentarioNF(
            entrega_id=id,
            autor=current_user.nome,
            texto=form.texto.data,
            arquivo=arquivo_nome,
            resposta_a_id=form.resposta_a_id.data or None
        )
        db.session.add(comentario)
        db.session.commit()

        flash('Comentário adicionado com sucesso.', 'success')
    
    return redirect(url_for('monitoramento.visualizar_entrega', id=id))

@monitoramento_bp.route('/comentarios_nf/<filename>')
@login_required
def baixar_arquivo_comentario(filename):
    pasta_comentarios = os.path.join(UPLOAD_DIR, "comentarios_nf")
    return send_from_directory(pasta_comentarios, filename)


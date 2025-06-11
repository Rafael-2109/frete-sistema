from flask import request, flash, url_for, redirect, render_template, Blueprint

from sqlalchemy import or_, cast, String

from flask_login import login_required, current_user

from app import db

from app.embarques.forms import EmbarqueForm, EmbarqueItemForm

from app.transportadoras.models import Transportadora

from app.embarques.models import Embarque, EmbarqueItem

from app.utils.sincronizar_entregas import sincronizar_entrega_por_nf, sincronizar_nova_entrega_por_nf
from app.monitoramento.models import EntregaMonitorada

from app.localidades.models import Cidade

from datetime import datetime

from app.pedidos.models import Pedido

embarques_bp = Blueprint('embarques', __name__,url_prefix='/embarques')

def obter_proximo_numero_embarque():
    """
    Obtém o próximo número de embarque de forma simples
    """
    # Busca o maior número existente
    ultimo = db.session.query(db.func.max(Embarque.numero)).scalar()
    proximo = (ultimo or 0) + 1
    return proximo

@embarques_bp.route('/<int:id>', methods=['GET', 'POST'])
@login_required
def visualizar_embarque(id):
    embarque = Embarque.query.get_or_404(id)

    if request.method == 'POST':
        form = EmbarqueForm(request.form)
        # Preenche transportadora.choices
        transportadoras = [(t.id, t.razao_social) for t in Transportadora.query.all()]
        form.transportadora.choices = transportadoras

        # Para cada item do FieldList, montar uf/cidade
        for item_form in form.itens:
            uf_sel = item_form.uf_destino.data
            if uf_sel:
                # Carregar cidades da UF do DB
                cidades_uf = Cidade.query.filter_by(uf=uf_sel).order_by(Cidade.nome).all()
                city_choices = [(c.nome, c.nome) for c in cidades_uf]
                item_form.cidade_destino.choices = [('', '--Selecione--')] + city_choices
            else:
                item_form.cidade_destino.choices = [('', '--Selecione--')]

        action = request.form.get('action')

        if action == 'add_line':
            # Não validamos, só adicionamos 1 item em branco
            form.itens.append_entry({})
            dados_portaria = obter_dados_portaria_embarque(embarque.id)
            return render_template('embarques/visualizar_embarque.html', form=form, embarque=embarque, dados_portaria=dados_portaria)

        elif action and action.startswith('remove_line_'):
            # Excluir a linha i
            line_idx = int(action.split('_')[-1])
            if line_idx < len(form.itens.entries):
                del form.itens.entries[line_idx]
            dados_portaria = obter_dados_portaria_embarque(embarque.id)
            return render_template('embarques/visualizar_embarque.html', form=form, embarque=embarque, dados_portaria=dados_portaria)

        elif action == 'save':

            
            # Agora sim, validar
            if form.validate_on_submit():
                # Salvar cabeçalho no DB
                if form.data_embarque.data:
                    embarque.data_embarque = datetime.strptime(form.data_embarque.data, '%d/%m/%Y').date()
                else:
                    embarque.data_embarque = None

                # ✅ READONLY: Transportadora não é mais editável - mantém valor existente
                embarque.observacoes = form.observacoes.data
                embarque.placa_veiculo = form.placa_veiculo.data
                embarque.paletizado = form.paletizado.data
                embarque.laudo_anexado = form.laudo_anexado.data
                embarque.embalagem_aprovada = form.embalagem_aprovada.data
                embarque.transporte_aprovado = form.transporte_aprovado.data
                embarque.horario_carregamento = form.horario_carregamento.data
                embarque.responsavel_carregamento = form.responsavel_carregamento.data
                embarque.nome_motorista = form.nome_motorista.data
                embarque.cpf_motorista = form.cpf_motorista.data
                embarque.qtd_pallets = int(form.qtd_pallets.data or 0)

                # ✅ CORREÇÃO FINAL: Dados da tabela NÃO precisam ser alterados - já estão corretos da cotação!
                # Atualizar APENAS campos básicos editáveis pelo usuário:

                # ✅ NOVA ESTRATÉGIA: Mapear por POSIÇÃO ao invés de ID (WTForms gera IDs automáticos)
                # Mapear itens do formulário com itens do banco por POSIÇÃO
                for i, item_form in enumerate(form.itens):
                    # ✅ PROTEÇÃO: Verificar se existe item correspondente no banco
                    if i < len(embarque.itens):
                        item_existente = embarque.itens[i]
                        
                        # ✅ ATUALIZA apenas campos editáveis pelo usuário
                        item_existente.nota_fiscal = item_form.nota_fiscal.data.strip() if item_form.nota_fiscal.data else None
                        item_existente.volumes = int(item_form.volumes.data or 0)
                        item_existente.protocolo_agendamento = item_form.protocolo_agendamento.data.strip() if item_form.protocolo_agendamento.data else None
                        item_existente.data_agenda = item_form.data_agenda.data.strip() if item_form.data_agenda.data else None
                        
                        # ✅ PRESERVA todos os dados importantes: CNPJ, peso, valor, tabelas, separação
                        # Estes dados SÓ vêm da cotação e NUNCA devem ser alterados manualmente
                        
                        # Validar NF do cliente
                        try:
                            sucesso, erro = validar_nf_cliente(item_existente)
                            if not sucesso:
                                flash(f"⚠️ {erro}", "warning")
                        except Exception as e:
                            pass
                
                # ✅ NOVA LÓGICA: Remove apenas itens que foram realmente removidos do formulário
                # (não implementado por enquanto - manter todos os itens existentes)
                
                # ✅ CORREÇÃO CRÍTICA: ANTES do commit, execute todas as operações em uma única transação
                messages_sync = []
                messages_validacao = []
                messages_fretes = []
                messages_entregas = []

                # ✅ NOVA FUNCIONALIDADE: Sincronizar NFs com pedidos
                try:
                    sucesso_sync, resultado_sync = sincronizar_nf_embarque_pedido(embarque.id)
                    if sucesso_sync:
                        messages_sync.append(f"🔄 {resultado_sync}")
                    else:
                        messages_sync.append(f"⚠️ Erro na sincronização: {resultado_sync}")
                except Exception as e:
                    print(f"Erro na sincronização de NFs: {e}")
                    messages_sync.append(f"⚠️ Erro na sincronização de NFs: {e}")

                # Validação de CNPJ entre embarque e faturamento
                try:
                    from app.fretes.routes import validar_cnpj_embarque_faturamento
                    sucesso_validacao, resultado_validacao = validar_cnpj_embarque_faturamento(embarque.id)
                    if not sucesso_validacao:
                        messages_validacao.append(f"⚠️ {resultado_validacao}")
                except Exception as e:
                    print(f"Erro na validação de CNPJ: {e}")
                    messages_validacao.append(f"⚠️ Erro na validação de CNPJ: {e}")

                # Lançamento automático de fretes após salvar embarque
                try:
                    from app.fretes.routes import processar_lancamento_automatico_fretes
                    sucesso, resultado = processar_lancamento_automatico_fretes(
                        embarque_id=embarque.id,
                        usuario=current_user.nome if current_user.is_authenticated else 'Sistema'
                    )
                    if sucesso and "lançado(s) automaticamente" in resultado:
                        messages_fretes.append(f"✅ {resultado}")
                except Exception as e:
                    print(f"Erro no lançamento automático de fretes: {e}")
                    messages_fretes.append(f"⚠️ Erro no lançamento de fretes: {e}")

                # Sincronização de entregas
                for item in embarque.itens:
                    if not item.nota_fiscal:
                        continue

                    try:
                        # Recupera a entrega pra verificar se está com nf_cd=True
                        entrega = EntregaMonitorada.query.filter_by(numero_nf=item.nota_fiscal).first()

                        if entrega and entrega.nf_cd:
                            # ✅ IMPLEMENTAÇÃO DO ITEM 2-d: NF no CD
                            # Atualiza status do pedido quando NF volta para CD
                            # ✅ CORREÇÃO: Passa separacao_lote_id para maior precisão
                            sucesso_cd, resultado_cd = atualizar_status_pedido_nf_cd(
                                numero_pedido=item.pedido,
                                separacao_lote_id=item.separacao_lote_id
                            )
                            if sucesso_cd:
                                messages_entregas.append(f"📦 {resultado_cd}")
                            
                            # Se nf_cd=True, chamamos o script especial
                            sincronizar_nova_entrega_por_nf(
                                numero_nf=item.nota_fiscal,
                                embarque=embarque,
                                item_embarque=item
                            )
                        else:
                            # Caso contrário, script normal
                            sincronizar_entrega_por_nf(item.nota_fiscal)
                    except Exception as e:
                        print(f"Erro na sincronização de entrega {item.nota_fiscal}: {e}")
                        messages_entregas.append(f"⚠️ Erro na entrega {item.nota_fiscal}: {e}")

                # ✅ CORREÇÃO: Commit ÚNICO após TODAS as operações
                db.session.commit()

                # Exibir todas as mensagens acumuladas
                for msg in messages_sync + messages_validacao + messages_fretes + messages_entregas:
                    if "⚠️" in msg or "❌" in msg:
                        flash(msg, "warning")
                    else:
                        flash(msg, "info" if "🔄" in msg or "📦" in msg else "success")

                flash("✅ Embarque atualizado com sucesso!", "success")
                return redirect(url_for('embarques.visualizar_embarque', id=embarque.id))
            else:
                flash("Erros na validação do formulário.", "danger")
                # Log form.errors se quiser
            dados_portaria = obter_dados_portaria_embarque(embarque.id)
            return render_template('embarques/visualizar_embarque.html', form=form, embarque=embarque, dados_portaria=dados_portaria)

        # Se chegou aqui e nao match action => exibe a página
        dados_portaria = obter_dados_portaria_embarque(embarque.id)
        return render_template('embarques/visualizar_embarque.html', form=form, embarque=embarque, dados_portaria=dados_portaria)

    else:
        # GET
        form = EmbarqueForm()

        # Popular cabeçalho - ✅ READONLY: string com nome ao invés de ID
        form.data_embarque.data = (
            embarque.data_embarque.strftime('%d/%m/%Y') if embarque.data_embarque else ''
        )
        form.transportadora.data = (
            embarque.transportadora.razao_social if embarque.transportadora else ''
        )
        form.observacoes.data = embarque.observacoes
        form.placa_veiculo.data = embarque.placa_veiculo
        form.paletizado.data = embarque.paletizado
        form.laudo_anexado.data = embarque.laudo_anexado
        form.embalagem_aprovada.data = embarque.embalagem_aprovada
        form.transporte_aprovado.data = embarque.transporte_aprovado
        form.horario_carregamento.data = embarque.horario_carregamento
        form.responsavel_carregamento.data = embarque.responsavel_carregamento
        form.nome_motorista.data = embarque.nome_motorista
        form.cpf_motorista.data = embarque.cpf_motorista
        form.qtd_pallets.data = embarque.qtd_pallets
        
        # ✅ SIMPLIFICAÇÃO: Campos ocultos removidos - dados preservados automaticamente no banco

        # ✅ CORREÇÃO DEFINITIVA: Limpar form.itens e adicionar APENAS os existentes
        form.itens.entries = []  # ⚡ Limpa tudo primeiro
        
        if embarque.itens:
            for i, it in enumerate(embarque.itens):
                entry_data = {
                    'id': str(it.id),
                    'cliente': it.cliente,
                    'pedido': it.pedido,
                    'protocolo_agendamento': it.protocolo_agendamento or '',
                    'data_agenda': it.data_agenda or '',
                    'nota_fiscal': it.nota_fiscal or '',
                    'volumes': str(it.volumes) if it.volumes is not None else '',
                    'uf_destino': it.uf_destino,
                    'cidade_destino': it.cidade_destino,
                }
                form.itens.append_entry(entry_data)
        else:
            # Se não há itens, adicionar um vazio
            form.itens.append_entry()
        
        # ✅ TENTATIVA: Forçar IDs após append_entry usando process() 
        try:
            # Processa os dados do request para popular os campos corretamente
            for i, it in enumerate(embarque.itens):
                if i < len(form.itens.entries):
                    entry = form.itens.entries[i]
                    if hasattr(entry, 'id') and hasattr(entry.id, 'process'):
                        entry.id.process(formdata=None, data=str(it.id))
        except Exception as e:
            pass

        # ✅ READONLY: UF e cidade são StringField readonly, não precisam mais de choices

        # Buscar dados da portaria para este embarque
        dados_portaria = obter_dados_portaria_embarque(embarque.id)
        
        return render_template('embarques/visualizar_embarque.html', form=form, embarque=embarque, dados_portaria=dados_portaria)
  
@embarques_bp.route('/listar_embarques')
def listar_embarques():
    from app.embarques.forms import FiltrosEmbarqueExpandidoForm
    
    # Apagar os rascunhos sem uso
    rascunhos = Embarque.query.filter_by(status='draft').all()
    for r in rascunhos:
        if len(r.itens) == 0:
            db.session.delete(r)
    db.session.commit()

    # Criar formulário de filtros expandido
    form_filtros = FiltrosEmbarqueExpandidoForm()
    
    # Popular choices de transportadoras
    transportadoras = Transportadora.query.all()
    form_filtros.transportadora_id.choices = [('', 'Todas as transportadoras')] + [(t.id, t.razao_social) for t in transportadoras]

    # Query base
    query = Embarque.query.options(db.joinedload(Embarque.transportadora))
    query = query.outerjoin(EmbarqueItem).outerjoin(Transportadora)

    # Aplicar filtros
    filtros_aplicados = False
    
    # Filtro por data de início
    data_inicio = request.args.get('data_inicio', '').strip()
    if data_inicio:
        try:
            data_inicio_obj = datetime.strptime(data_inicio, '%d/%m/%Y').date()
            query = query.filter(Embarque.data_embarque >= data_inicio_obj)
            form_filtros.data_inicio.data = data_inicio
            filtros_aplicados = True
        except ValueError:
            flash('Data de início inválida. Use o formato DD/MM/AAAA', 'warning')

    # Filtro por data fim
    data_fim = request.args.get('data_fim', '').strip()
    if data_fim:
        try:
            data_fim_obj = datetime.strptime(data_fim, '%d/%m/%Y').date()
            query = query.filter(Embarque.data_embarque <= data_fim_obj)
            form_filtros.data_fim.data = data_fim
            filtros_aplicados = True
        except ValueError:
            flash('Data de fim inválida. Use o formato DD/MM/AAAA', 'warning')

    # Filtro por nota fiscal
    nota_fiscal = request.args.get('nota_fiscal', '').strip()
    if nota_fiscal:
        query = query.filter(EmbarqueItem.nota_fiscal.ilike(f'%{nota_fiscal}%'))
        form_filtros.nota_fiscal.data = nota_fiscal
        filtros_aplicados = True

    # Filtro por pedido
    pedido = request.args.get('pedido', '').strip()
    if pedido:
        query = query.filter(EmbarqueItem.pedido.ilike(f'%{pedido}%'))
        form_filtros.pedido.data = pedido
        filtros_aplicados = True

    # Filtro por transportadora
    transportadora_id = request.args.get('transportadora_id', '').strip()
    if transportadora_id and transportadora_id != '':
        try:
            transportadora_id = int(transportadora_id)
            query = query.filter(Embarque.transportadora_id == transportadora_id)
            form_filtros.transportadora_id.data = transportadora_id
            filtros_aplicados = True
        except ValueError:
            pass

    # Filtro por status do embarque
    status = request.args.get('status', '').strip()
    if status and status != '':
        query = query.filter(Embarque.status == status)
        form_filtros.status.data = status
        filtros_aplicados = True

    # Filtro por status da portaria
    status_portaria = request.args.get('status_portaria', '').strip()
    if status_portaria and status_portaria != '':
        from app.portaria.models import ControlePortaria
        
        if status_portaria == 'Sem Registro':
            # Embarques que NÃO têm registro na portaria
            embarques_com_registro = db.session.query(ControlePortaria.embarque_id).filter(
                ControlePortaria.embarque_id.isnot(None)
            ).distinct()
            query = query.filter(~Embarque.id.in_(embarques_com_registro))
        else:
            # Embarques que têm registro com status específico
            # Busca o último registro de cada embarque e filtra pelo status
            from sqlalchemy import and_, func
            
            # Subquery para pegar o último registro de cada embarque (apenas com embarque_id válido)
            ultimo_registro_subquery = db.session.query(
                ControlePortaria.embarque_id,
                func.max(ControlePortaria.id).label('ultimo_id')
            ).filter(
                ControlePortaria.embarque_id.isnot(None)
            ).group_by(ControlePortaria.embarque_id).subquery()
            
            # Join para pegar os dados do último registro
            query = query.join(
                ultimo_registro_subquery,
                Embarque.id == ultimo_registro_subquery.c.embarque_id
            ).join(
                ControlePortaria,
                ControlePortaria.id == ultimo_registro_subquery.c.ultimo_id
            )
            
            # Filtra pelo status calculado dinamicamente
            if status_portaria == 'SAIU':
                query = query.filter(
                    and_(
                        ControlePortaria.data_saida.isnot(None),
                        ControlePortaria.hora_saida.isnot(None)
                    )
                )
            elif status_portaria == 'DENTRO':
                query = query.filter(
                    and_(
                        ControlePortaria.data_entrada.isnot(None),
                        ControlePortaria.hora_entrada.isnot(None),
                        ControlePortaria.data_saida.is_(None)
                    )
                )
            elif status_portaria == 'AGUARDANDO':
                query = query.filter(
                    and_(
                        ControlePortaria.data_chegada.isnot(None),
                        ControlePortaria.hora_chegada.isnot(None),
                        ControlePortaria.data_entrada.is_(None)
                    )
                )
            elif status_portaria == 'PENDENTE':
                query = query.filter(
                    ControlePortaria.data_chegada.is_(None)
                )
        
        form_filtros.status_portaria.data = status_portaria
        filtros_aplicados = True

    # Filtro por status das NFs
    status_nfs = request.args.get('status_nfs', '').strip()
    if status_nfs and status_nfs != '':
        # Como status_nfs é uma propriedade calculada, precisamos filtrar após a query
        # Vamos manter a referência para filtrar depois
        form_filtros.status_nfs.data = status_nfs
        filtros_aplicados = True
    
    # Filtro por status dos fretes
    status_fretes = request.args.get('status_fretes', '').strip()
    if status_fretes and status_fretes != '':
        # Como status_fretes é uma propriedade calculada, precisamos filtrar após a query
        # Vamos manter a referência para filtrar depois
        form_filtros.status_fretes.data = status_fretes
        filtros_aplicados = True

    # Busca geral (mantém funcionalidade original)
    buscar_texto = request.args.get('buscar_texto', '').strip()
    if buscar_texto:
        busca = f"%{buscar_texto}%"
        query = query.filter(
            or_(
                cast(Embarque.numero, String).ilike(busca),
                EmbarqueItem.cliente.ilike(busca),
                EmbarqueItem.pedido.ilike(busca),
                EmbarqueItem.nota_fiscal.ilike(busca),
                Transportadora.razao_social.ilike(busca),
            )
        )
        form_filtros.buscar_texto.data = buscar_texto
        filtros_aplicados = True

    # Ordenação padrão (mais recente primeiro)
    query = query.order_by(Embarque.numero.desc())

    # Remover duplicados caso o embarque tenha vários itens que casam com a busca
    query = query.distinct()

    # Executa a query
    embarques = query.all()
    
    # Aplica filtros baseados nas propriedades calculadas (status_nfs e status_fretes)
    if status_nfs and status_nfs != '':
        embarques = [e for e in embarques if e.status_nfs == status_nfs]
    
    if status_fretes and status_fretes != '':
        embarques = [e for e in embarques if e.status_fretes == status_fretes]

    return render_template(
        'embarques/listar_embarques.html', 
        embarques=embarques, 
        form_filtros=form_filtros,
        filtros_aplicados=filtros_aplicados
    )

@embarques_bp.route('/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar_embarque(id):
    embarque = Embarque.query.get_or_404(id)

    # Define número de itens no formulário (somando +1 ao existente)
    if request.method == 'GET':
        qtd_itens = int(request.args.get('itens', len(embarque.itens) + 1))
        form = EmbarqueForm()

        # ✅ READONLY: Preencher campos como string
        form.data_embarque.data = embarque.data_embarque.strftime('%d/%m/%Y') if embarque.data_embarque else ''
        form.transportadora.data = embarque.transportadora.razao_social if embarque.transportadora else ''
        form.observacoes.data = embarque.observacoes
        form.placa_veiculo.data = embarque.placa_veiculo
        form.paletizado.data = embarque.paletizado
        form.laudo_anexado.data = embarque.laudo_anexado
        form.embalagem_aprovada.data = embarque.embalagem_aprovada
        form.transporte_aprovado.data = embarque.transporte_aprovado
        form.horario_carregamento.data = embarque.horario_carregamento
        form.responsavel_carregamento.data = embarque.responsavel_carregamento
        form.nome_motorista.data = embarque.nome_motorista
        form.cpf_motorista.data = embarque.cpf_motorista
        form.qtd_pallets.data = embarque.qtd_pallets

        # ✅ CORREÇÃO DEFINITIVA: Limpar form.itens e adicionar itens conforme necessário
        form.itens.entries = []  # ⚡ Limpa tudo primeiro
        
        # Adicionar itens existentes
        for i, it in enumerate(embarque.itens):
            entry_data = {
                'id': str(it.id),
                'cliente': it.cliente,
                'pedido': it.pedido,
                'protocolo_agendamento': it.protocolo_agendamento or '',
                'data_agenda': it.data_agenda or '',
                'nota_fiscal': it.nota_fiscal or '',
                'volumes': str(it.volumes) if it.volumes is not None else '',
                'uf_destino': it.uf_destino,
                'cidade_destino': it.cidade_destino,
            }
            form.itens.append_entry(entry_data)
            
        # Adicionar itens vazios extras conforme solicitado via qtd_itens
        for i in range(len(embarque.itens), qtd_itens):
            form.itens.append_entry()
        
        # ✅ TENTATIVA: Forçar IDs após append_entry usando process() 
        try:
            for i, it in enumerate(embarque.itens):
                if i < len(form.itens.entries):
                    entry = form.itens.entries[i]
                    if hasattr(entry, 'id') and hasattr(entry.id, 'process'):
                        entry.id.process(formdata=None, data=str(it.id))
        except Exception as e:
            pass



        return render_template('embarques/visualizar_embarque.html', embarque=embarque, form=form)

    flash("Erro inesperado", "danger")
    return redirect(url_for("embarques.visualizar_embarque", id=embarque.id))


@embarques_bp.route('/<int:id>/cancelar', methods=['GET', 'POST'])
@login_required
def cancelar_embarque(id):
    from app.embarques.forms import CancelamentoEmbarqueForm
    
    embarque = Embarque.query.get_or_404(id)
    
    # Verifica se já está cancelado
    if embarque.status == 'cancelado':
        flash("Este embarque já está cancelado.", "warning")
        return redirect(url_for('embarques.visualizar_embarque', id=id))
    
    form = CancelamentoEmbarqueForm()
    
    if form.validate_on_submit():
        # Marca como cancelado em vez de excluir
        embarque.status = 'cancelado'
        embarque.motivo_cancelamento = form.motivo_cancelamento.data
        embarque.cancelado_em = datetime.now()
        embarque.cancelado_por = current_user.nome if current_user.is_authenticated else 'Sistema'
        
        # ✅ NOVO: Resetar pedidos para status "Aberto" usando lote_separacao
        try:
            from app.pedidos.models import Pedido
            
            # Busca todos os lotes de separação vinculados aos itens deste embarque
            lotes_vinculados = set()
            for item in embarque.itens:
                if hasattr(item, 'separacao_lote_id') and item.separacao_lote_id:
                    lotes_vinculados.add(item.separacao_lote_id)
            
            # Reseta os pedidos para status "Aberto" usando os lotes
            pedidos_atualizados = 0
            for lote_id in lotes_vinculados:
                pedidos_lote = Pedido.query.filter_by(separacao_lote_id=lote_id).all()
                for pedido in pedidos_lote:
                    # Remove vinculação com cotação (volta ao estado inicial)
                    pedido.cotacao_id = None
                    pedido.transportadora = None
                    pedido.nf_cd = False
                    # Status será calculado automaticamente como "Aberto"
                    pedidos_atualizados += 1
            
            if pedidos_atualizados > 0:
                flash(f"✅ {pedidos_atualizados} pedidos retornaram ao status 'Aberto'", "info")
                
        except Exception as e:
            flash(f"⚠️ Erro ao resetar pedidos: {str(e)}", "warning")
        
        db.session.commit()
        
        flash(f"Embarque #{embarque.numero} cancelado com sucesso!", "success")
        return redirect(url_for('embarques.listar_embarques'))
    
    return render_template('embarques/cancelar_embarque.html', 
                         embarque=embarque, 
                         form=form)

@embarques_bp.route('/<int:id>/motivo_cancelamento')
@login_required
def motivo_cancelamento(id):
    embarque = Embarque.query.get_or_404(id)
    
    if embarque.status != 'cancelado':
        flash("Este embarque não está cancelado.", "warning")
        return redirect(url_for('embarques.visualizar_embarque', id=id))
    
    return render_template('embarques/motivo_cancelamento.html', embarque=embarque)




@embarques_bp.route('/excluir_item/<int:item_id>', methods=['POST'])
@login_required
def excluir_item_embarque(item_id):
    item = EmbarqueItem.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    return "", 204


@embarques_bp.route('/<int:embarque_id>/novo_item', methods=['GET', 'POST'])
@login_required
def novo_item(embarque_id):
    embarque = Embarque.query.get_or_404(embarque_id)
    form = EmbarqueItemForm()  # <-- seu form para UM item

    if request.method == 'POST':
        if form.validate_on_submit():
            novo_item = EmbarqueItem(
                embarque_id=embarque.id,
                cliente=form.cliente.data,
                pedido=form.pedido.data,
                nota_fiscal=form.nota_fiscal.data,
                volumes=int(form.volumes.data) if form.volumes.data else 0,
                uf_destino=form.uf_destino.data,
                cidade_destino=form.cidade_destino.data,
                protocolo_agendamento=form.protocolo_agendamento.data,
                data_agenda=form.data_agenda.data
            )
            db.session.add(novo_item)
            db.session.commit()
            flash("Item adicionado com sucesso!", "success")
            return redirect(url_for('embarques.visualizar_embarque', id=embarque.id))

    return render_template("embarques/novo_item.html", form=form, embarque=embarque)

@embarques_bp.route('/novo', methods=['GET'])
@login_required
def novo_rascunho():
    # Cria um embarque rascunho
    novo = Embarque(status='draft')
    db.session.add(novo)
    db.session.flush()

    # Gera número sequencial para o embarque
    novo.numero = obter_proximo_numero_embarque()

    db.session.commit()

    # Redireciona para a página "interativa" com HTMX
    return redirect(url_for('embarques.novo_interativo', embarque_id=novo.id))

@embarques_bp.route('/novo/<int:embarque_id>', methods=['GET','POST'])
@login_required
def novo_interativo(embarque_id):
    """Cria/edita o Embarque em modo 'draft' usando FieldList. 
       Ao final, clica em 'finalizar' e salva tudo no DB.
    """
    embarque = Embarque.query.get_or_404(embarque_id)
    if embarque.status != 'draft':
        flash("Embarque não está em status draft!", "warning")
        return redirect(url_for('embarques.visualizar_embarque', id=embarque.id))

            # Monta o form (recriando no POST c/ request.form)
    if request.method == 'POST':
        form = EmbarqueForm(request.form)
        # ✅ READONLY: Transportadora é string com nome ao invés de SelectField
        # Não precisa mais de choices
        # ✅ READONLY: UF e cidade são StringField readonly, não precisam mais de choices
    else:
        # GET
        # Inicia form vazio
        form = EmbarqueForm()

        # Preenche cabeçalho - ✅ READONLY: string com nome ao invés de ID
        form.data_embarque.data = (
            embarque.data_embarque.strftime('%d/%m/%Y') if embarque.data_embarque else ''
        )
        form.transportadora.data = (
            embarque.transportadora.razao_social if embarque.transportadora else ''
        )
        form.observacoes.data = embarque.observacoes
        form.placa_veiculo.data = embarque.placa_veiculo
        form.paletizado.data = embarque.paletizado
        form.laudo_anexado.data = embarque.laudo_anexado
        form.embalagem_aprovada.data = embarque.embalagem_aprovada
        form.transporte_aprovado.data = embarque.transporte_aprovado
        form.horario_carregamento.data = embarque.horario_carregamento
        form.responsavel_carregamento.data = embarque.responsavel_carregamento
        form.nome_motorista.data = embarque.nome_motorista
        form.cpf_motorista.data = embarque.cpf_motorista
        form.qtd_pallets.data = embarque.qtd_pallets if embarque.qtd_pallets else ''

        # ✅ CORREÇÃO DEFINITIVA: Limpar form.itens e adicionar APENAS os existentes
        form.itens.entries = []  # ⚡ Limpa tudo primeiro
        
        if len(embarque.itens) > 0:
            for i, item in enumerate(embarque.itens):
                entry_data = {
                    'id': str(item.id),
                    'cliente': item.cliente,
                    'pedido': item.pedido,
                    'protocolo_agendamento': item.protocolo_agendamento or '',
                    'data_agenda': item.data_agenda or '',
                    'nota_fiscal': item.nota_fiscal or '',
                    'volumes': str(item.volumes) if item.volumes is not None else '',
                    'uf_destino': item.uf_destino,
                    'cidade_destino': item.cidade_destino,
                }
                form.itens.append_entry(entry_data)
        else:
            # Se não há itens, criar um vazio
            form.itens.append_entry()
        
        # ✅ TENTATIVA: Forçar IDs após append_entry usando process() 
        try:
            for i, item in enumerate(embarque.itens):
                if i < len(form.itens.entries):
                    entry = form.itens.entries[i]
                    if hasattr(entry, 'id') and hasattr(entry.id, 'process'):
                        entry.id.process(formdata=None, data=str(item.id))
        except Exception as e:
            pass

        # ✅ READONLY: UF e cidade são StringField readonly, não precisam mais de choices

    # Se POST, verificamos qual "action"
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add_line':
            # Adiciona nova entrada no FieldList (vazia)
            form.itens.append_entry()
            return render_template('embarques/novo_interativo.html', form=form, embarque=embarque)

        elif action and action.startswith('remove_line_'):
            # Excluir a linha i
            line_str = action.split('_')[-1]
            line_idx = int(line_str)
            if line_idx < len(form.itens.entries):
                del form.itens.entries[line_idx]
            return render_template('embarques/novo_interativo.html', form=form, embarque=embarque)

        elif action == 'finalizar':
            
            # Agora sim rodamos validate_on_submit
            if form.validate_on_submit():
                # Salvar cabeçalho
                if form.data_embarque.data:
                    embarque.data_embarque = datetime.strptime(form.data_embarque.data, '%d/%m/%Y').date()
                else:
                    embarque.data_embarque = None

                # ✅ READONLY: Transportadora não é mais editável - mantém valor existente
                embarque.observacoes = form.observacoes.data
                embarque.placa_veiculo = form.placa_veiculo.data
                embarque.paletizado = form.paletizado.data
                embarque.laudo_anexado = form.laudo_anexado.data
                embarque.embalagem_aprovada = form.embalagem_aprovada.data
                embarque.transporte_aprovado = form.transporte_aprovado.data
                embarque.horario_carregamento = form.horario_carregamento.data
                embarque.responsavel_carregamento = form.responsavel_carregamento.data
                embarque.nome_motorista = form.nome_motorista.data
                embarque.cpf_motorista = form.cpf_motorista.data
                embarque.qtd_pallets = int(form.qtd_pallets.data or 0)

                # Gera numero e finaliza
                embarque.numero = obter_proximo_numero_embarque()
                embarque.status = 'ativo'
                
                # ✅ CORREÇÃO FINAL: Dados da tabela NÃO precisam ser alterados - já estão corretos da cotação!

                # ✅ CORREÇÃO DEFINITIVA: NÃO deleta/recria itens - apenas ATUALIZA os que mudaram
                # Cria mapa de itens existentes por ID para atualização eficiente
                itens_existentes = {item.id: item for item in embarque.itens}
                
                # Itens que foram processados no formulário
                ids_processados = set()
                
                # Atualiza apenas os campos que o usuário pode modificar
                for i, item_form in enumerate(form.itens):
                    # ✅ PROTEÇÃO: Verifica se id é um campo com atributo 'data' ou é string/valor direto
                    item_id_value = item_form.id.data if hasattr(item_form.id, 'data') else item_form.id
                    if item_id_value and str(item_id_value).strip():
                        try:
                            item_id = int(item_id_value)
                            item_existente = itens_existentes.get(item_id)
                            
                            if item_existente:
                                # ✅ CORREÇÃO SIMPLIFICADA: Atualizar SEMPRE campos editáveis
                                # Nota Fiscal
                                item_existente.nota_fiscal = item_form.nota_fiscal.data or None
                                
                                # Volumes
                                if item_form.volumes.data:
                                    try:
                                        item_existente.volumes = int(item_form.volumes.data)
                                    except (ValueError, TypeError):
                                        pass  # Mantém valor existente se conversão falhar
                                else:
                                    item_existente.volumes = 0
                                
                                # Protocolo
                                item_existente.protocolo_agendamento = item_form.protocolo_agendamento.data or None
                                
                                # Data Agenda
                                item_existente.data_agenda = item_form.data_agenda.data or None
                                
                                # ✅ PRESERVA todos os dados importantes: CNPJ, peso, valor, tabelas, separação
                                # Estes dados SÓ vêm da cotação e NUNCA devem ser alterados manualmente
                                
                                ids_processados.add(item_id)
                                
                                # Validar NF do cliente
                                sucesso, erro = validar_nf_cliente(item_existente)
                                if not sucesso:
                                    flash(f"⚠️ {erro}", "warning")
                        except (ValueError, TypeError):
                            pass
                
                # ✅ NOVA LÓGICA: Remove apenas itens que foram realmente removidos do formulário
                # (não implementado por enquanto - manter todos os itens existentes)

                # ✅ CORREÇÃO CRÍTICA: ANTES do commit, execute todas as operações em uma única transação
                messages_validacao = []
                messages_fretes = []
                messages_entregas = []

                # Validação de CNPJ entre embarque e faturamento
                try:
                    from app.fretes.routes import validar_cnpj_embarque_faturamento
                    sucesso_validacao, resultado_validacao = validar_cnpj_embarque_faturamento(embarque.id)
                    if not sucesso_validacao:
                        messages_validacao.append(f"⚠️ {resultado_validacao}")
                except Exception as e:
                    print(f"Erro na validação de CNPJ: {e}")
                    messages_validacao.append(f"⚠️ Erro na validação de CNPJ: {e}")

                # Lançamento automático de fretes após finalizar embarque
                try:
                    from app.fretes.routes import processar_lancamento_automatico_fretes
                    sucesso, resultado = processar_lancamento_automatico_fretes(
                        embarque_id=embarque.id,
                        usuario=current_user.nome if current_user.is_authenticated else 'Sistema'
                    )
                    if sucesso and "lançado(s) automaticamente" in resultado:
                        messages_fretes.append(f"✅ {resultado}")
                except Exception as e:
                    print(f"Erro no lançamento automático de fretes: {e}")
                    messages_fretes.append(f"⚠️ Erro no lançamento de fretes: {e}")

                # Sincronização de entregas
                for it in embarque.itens:
                    if it.nota_fiscal:
                        try:
                            entrega = EntregaMonitorada.query.filter_by(numero_nf=it.nota_fiscal).first()

                            if entrega and entrega.nf_cd:
                                # Chama a função nova, passando todos os parâmetros
                                sincronizar_nova_entrega_por_nf(
                                    numero_nf=it.nota_fiscal,
                                    embarque=embarque,
                                    item_embarque=it
                                )
                            else:
                                sincronizar_entrega_por_nf(it.nota_fiscal)
                        except Exception as e:
                            print(f"Erro na sincronização de entrega {it.nota_fiscal}: {e}")
                            messages_entregas.append(f"⚠️ Erro na entrega {it.nota_fiscal}: {e}")

                # ✅ CORREÇÃO: Commit ÚNICO após TODAS as operações
                db.session.commit()

                # Exibir todas as mensagens acumuladas
                for msg in messages_validacao + messages_fretes + messages_entregas:
                    if "⚠️" in msg or "❌" in msg:
                        flash(msg, "warning")
                    else:
                        flash(msg, "info" if "🔄" in msg or "📦" in msg else "success")

                flash("✅ Embarque atualizado (ou finalizado) com sucesso!", "success")
                return redirect(url_for('embarques.visualizar_embarque', id=embarque.id))

            else:
                if not form.validate_on_submit():
                    print("FORM ERRORS:", form.errors)
                    for i, item_form in enumerate(form.itens):
                        print(f"Item {i} errors:", item_form.errors)
                    flash("Erros na validação do formulário.", "danger")
            return render_template('embarques/novo_interativo.html', form=form, embarque=embarque)

    return render_template('embarques/novo_interativo.html', form=form, embarque=embarque)

@embarques_bp.route('/<int:id>/dados_tabela')
@login_required
def dados_tabela_embarque(id):
    """
    Exibe os dados da tabela de frete do embarque
    """
    embarque = Embarque.query.get_or_404(id)
    
    # Carrega os itens do embarque
    itens = EmbarqueItem.query.filter_by(embarque_id=embarque.id).all()
    
    return render_template('embarques/dados_tabela.html', embarque=embarque, itens=itens)

def obter_dados_portaria_embarque(embarque_id):
    """
    Busca informações da portaria vinculadas ao embarque
    """
    from app.portaria.models import ControlePortaria
    
    # Busca registros da portaria vinculados a este embarque
    registros = ControlePortaria.query.filter_by(embarque_id=embarque_id).all()
    
    if not registros:
        return None
    
    # Retorna informações do primeiro/último registro (pode ter vários)
    registro = registros[-1]  # Pega o mais recente
    
    return {
        'motorista_nome': registro.motorista_obj.nome_completo if registro.motorista_obj else 'N/A',
        'placa': registro.placa,
        'tipo_veiculo': registro.tipo_veiculo.nome if registro.tipo_veiculo else 'N/A',
        'data_chegada': registro.data_chegada,
        'hora_chegada': registro.hora_chegada,
        'data_entrada': registro.data_entrada,
        'hora_entrada': registro.hora_entrada,
        'data_saida': registro.data_saida,
        'hora_saida': registro.hora_saida,
        'status': registro.status,
        'registro_id': registro.id
    }

@embarques_bp.route('/<int:embarque_id>/separacao/<separacao_lote_id>')
@login_required
def acessar_separacao(embarque_id, separacao_lote_id):
    """
    Exibe os dados detalhados da separação vinculada ao embarque
    """
    from app.separacao.models import Separacao
    
    embarque = Embarque.query.get_or_404(embarque_id)
    
    # Busca todos os itens da separação com este lote_id
    itens_separacao = Separacao.query.filter_by(separacao_lote_id=separacao_lote_id).all()
    
    if not itens_separacao:
        flash('Dados de separação não encontrados para este embarque.', 'warning')
        return redirect(url_for('embarques.visualizar_embarque', id=embarque_id))
    
    # Agrupa informações da separação
    resumo_separacao = {
        'lote_id': separacao_lote_id,
        'num_pedido': itens_separacao[0].num_pedido,
        'data_pedido': itens_separacao[0].data_pedido,
        'cliente': itens_separacao[0].raz_social_red,
        'cnpj_cpf': itens_separacao[0].cnpj_cpf,
        'cidade_destino': itens_separacao[0].nome_cidade,
        'uf_destino': itens_separacao[0].cod_uf,
        'total_produtos': len(itens_separacao),
        'peso_total': sum(item.peso or 0 for item in itens_separacao),
        'valor_total': sum(item.valor_saldo or 0 for item in itens_separacao),
        'pallet_total': sum(item.pallet or 0 for item in itens_separacao),
        'qtd_total': sum(item.qtd_saldo or 0 for item in itens_separacao),
    }
    
    return render_template(
        'embarques/acessar_separacao.html', 
        embarque=embarque,
        itens_separacao=itens_separacao,
        resumo_separacao=resumo_separacao
    )

@embarques_bp.route('/<int:embarque_id>/separacao/<separacao_lote_id>/imprimir')
@login_required 
def imprimir_separacao(embarque_id, separacao_lote_id):
    """
    Gera relatório de impressão da separação
    """
    from app.separacao.models import Separacao
    from flask import make_response
    
    embarque = Embarque.query.get_or_404(embarque_id)
    
    # Busca todos os itens da separação com este lote_id
    itens_separacao = Separacao.query.filter_by(separacao_lote_id=separacao_lote_id).all()
    
    if not itens_separacao:
        flash('Dados de separação não encontrados para este embarque.', 'warning')
        return redirect(url_for('embarques.visualizar_embarque', id=embarque_id))
    
    # Agrupa informações da separação para impressão
    resumo_separacao = {
        'lote_id': separacao_lote_id,
        'num_pedido': itens_separacao[0].num_pedido,
        'data_pedido': itens_separacao[0].data_pedido,
        'cliente': itens_separacao[0].raz_social_red,
        'cnpj_cpf': itens_separacao[0].cnpj_cpf,
        'cidade_destino': itens_separacao[0].nome_cidade,
        'uf_destino': itens_separacao[0].cod_uf,
        'total_produtos': len(itens_separacao),
        'peso_total': sum(item.peso or 0 for item in itens_separacao),
        'valor_total': sum(item.valor_saldo or 0 for item in itens_separacao),
        'pallet_total': sum(item.pallet or 0 for item in itens_separacao),
        'qtd_total': sum(item.qtd_saldo or 0 for item in itens_separacao),
    }
    
    # Renderiza template específico para impressão
    html = render_template(
        'embarques/imprimir_separacao.html',
        embarque=embarque,
        itens_separacao=itens_separacao,
        resumo_separacao=resumo_separacao,
        data_impressao=datetime.now(),
        current_user=current_user
    )
    
    response = make_response(html)
    response.headers['Content-Type'] = 'text/html; charset=utf-8'
    return response

@embarques_bp.route('/<int:embarque_id>/imprimir_embarque')
@login_required 
def imprimir_embarque(embarque_id):
    """
    Gera relatório de impressão apenas do embarque individual (sem separações)
    """
    from flask import make_response
    
    embarque = Embarque.query.get_or_404(embarque_id)
    
    # Renderiza template específico para impressão do embarque
    html = render_template(
        'embarques/imprimir_embarque.html',
        embarque=embarque,
        data_impressao=datetime.now(),
        current_user=current_user
    )
    
    response = make_response(html)
    response.headers['Content-Type'] = 'text/html; charset=utf-8'
    return response

@embarques_bp.route('/<int:embarque_id>/imprimir_completo')
@login_required 
def imprimir_embarque_completo(embarque_id):
    """
    Gera relatório completo: embarque + todas as separações individuais
    """
    from app.separacao.models import Separacao
    from flask import make_response
    
    embarque = Embarque.query.get_or_404(embarque_id)
    
    # Busca todos os lotes únicos de separação vinculados a este embarque
    lotes_separacao = db.session.query(EmbarqueItem.separacao_lote_id).filter(
        EmbarqueItem.embarque_id == embarque_id,
        EmbarqueItem.separacao_lote_id.isnot(None)
    ).distinct().all()
    
    # Prepara dados de cada separação
    separacoes_data = []
    for (lote_id,) in lotes_separacao:
        # Busca itens da separação
        itens_separacao = Separacao.query.filter_by(separacao_lote_id=lote_id).all()
        
        if itens_separacao:
            # Agrupa informações da separação
            resumo_separacao = {
                'lote_id': lote_id,
                'num_pedido': itens_separacao[0].num_pedido,
                'data_pedido': itens_separacao[0].data_pedido,
                'cliente': itens_separacao[0].raz_social_red,
                'cnpj_cpf': itens_separacao[0].cnpj_cpf,
                'cidade_destino': itens_separacao[0].nome_cidade,
                'uf_destino': itens_separacao[0].cod_uf,
                'total_produtos': len(itens_separacao),
                'data_agendamento': itens_separacao[0].agendamento,
                'peso_total': sum(item.peso or 0 for item in itens_separacao),
                'valor_total': sum(item.valor_saldo or 0 for item in itens_separacao),
                'pallet_total': sum(item.pallet or 0 for item in itens_separacao),
                'qtd_total': sum(item.qtd_saldo or 0 for item in itens_separacao),
            }
            
            separacoes_data.append({
                'resumo': resumo_separacao,
                'itens': itens_separacao
            })
    
    # Renderiza template específico para impressão completa
    html = render_template(
        'embarques/imprimir_completo.html',
        embarque=embarque,
        separacoes_data=separacoes_data,
        data_impressao=datetime.now(),
        current_user=current_user
    )
    
    response = make_response(html)
    response.headers['Content-Type'] = 'text/html; charset=utf-8'
    return response

@embarques_bp.route('/<int:embarque_id>/corrigir_cnpj', methods=['POST'])
@login_required
def corrigir_cnpj_embarque(embarque_id):
    """
    Permite ao usuário corrigir manualmente os CNPJs divergentes
    """
    try:
        embarque = Embarque.query.get_or_404(embarque_id)
        
        # Busca itens com erro de CNPJ
        itens_com_erro = [item for item in embarque.itens if item.erro_validacao and 'CNPJ_DIFERENTE' in item.erro_validacao]
        
        if not itens_com_erro:
            flash('Não há erros de CNPJ para corrigir neste embarque.', 'info')
            return redirect(url_for('embarques.visualizar_embarque', id=embarque_id))
        
        # Para cada item com erro, atualiza com o CNPJ do faturamento
        from app.faturamento.models import RelatorioFaturamentoImportado
        itens_corrigidos = 0
        
        for item in itens_com_erro:
            if item.nota_fiscal:
                nf_faturamento = RelatorioFaturamentoImportado.query.filter_by(
                    numero_nf=item.nota_fiscal
                ).first()
                
                if nf_faturamento:
                    item.cnpj_cliente = nf_faturamento.cnpj_cliente
                    item.erro_validacao = None
                    itens_corrigidos += 1
        
        db.session.commit()
        
        if itens_corrigidos > 0:
            flash(f'✅ {itens_corrigidos} item(ns) corrigido(s) com sucesso! CNPJs atualizados conforme faturamento.', 'success')
            
            # Tenta lançar fretes automaticamente após correção
            try:
                from app.fretes.routes import processar_lancamento_automatico_fretes
                sucesso, resultado = processar_lancamento_automatico_fretes(
                    embarque_id=embarque.id,
                    usuario=current_user.nome if current_user.is_authenticated else 'Sistema'
                )
                if sucesso and "lançado(s) automaticamente" in resultado:
                    flash(f"✅ {resultado}", "success")
            except Exception as e:
                print(f"Erro no lançamento automático após correção: {e}")
        else:
            flash('Nenhum item foi corrigido.', 'warning')
            
    except Exception as e:
        flash(f'Erro ao corrigir CNPJs: {str(e)}', 'error')
    
    return redirect(url_for('embarques.visualizar_embarque', id=embarque_id))

def validar_nf_cliente(item_embarque):
    """
    Valida se a NF do item pertence ao cliente correto.
    
    REGRA RIGOROSA: NÃO atualiza dados do embarque, apenas valida!
    
    ✅ PERMITE:
    - NF não preenchida (opcional)
    - NF não encontrada no faturamento (pode ser preenchida antes da importação)
    - NF pertence ao cliente correto
    
    ❌ BLOQUEIA:
    - NF pertence a outro cliente (CNPJ divergente)
    
    Retorna (sucesso, mensagem_erro)
    """
    from app.faturamento.models import RelatorioFaturamentoImportado
    
    if not item_embarque.nota_fiscal:
        return True, None
        
    # Busca a NF no faturamento
    nf_faturamento = RelatorioFaturamentoImportado.query.filter_by(
        numero_nf=item_embarque.nota_fiscal
    ).first()
    
    if not nf_faturamento:
        # NF não encontrada - PERMITE (pode ser preenchida antes da importação)
        item_embarque.erro_validacao = "NF_PENDENTE_FATURAMENTO"
        return True, f"NF {item_embarque.nota_fiscal} ainda não importada no faturamento (será validada após importação)"
    
    # ✅ CORREÇÃO PRINCIPAL: Se o item TEM cliente definido, verifica se a NF pertence a esse cliente
    if item_embarque.cnpj_cliente:
        if item_embarque.cnpj_cliente != nf_faturamento.cnpj_cliente:
            # ✅ CORREÇÃO: NF não pertence ao cliente - APAGA APENAS a NF, mantém todos os outros dados
            nf_original = item_embarque.nota_fiscal
            item_embarque.erro_validacao = f"NF_DIVERGENTE: NF {nf_original} pertence ao CNPJ {nf_faturamento.cnpj_cliente}, não a {item_embarque.cnpj_cliente}"
            item_embarque.nota_fiscal = None  # ✅ APAGA APENAS a NF divergente
            
            # ✅ MANTÉM todos os outros dados: CNPJ, peso, valor, tabelas, separação, etc.
            # NÃO toca em nada além da NF e do erro_validacao
            
            return False, f"❌ BLOQUEADO: NF {nf_original} não pertence ao cliente {item_embarque.cnpj_cliente} (pertence a {nf_faturamento.cnpj_cliente})"
        else:
            # ✅ NF pertence ao cliente correto - Atualiza peso e valor da NF
            item_embarque.peso = float(nf_faturamento.peso_bruto or 0)
            item_embarque.valor = float(nf_faturamento.valor_total or 0)
            item_embarque.erro_validacao = None
            return True, None
    
    # ✅ CORREÇÃO: Item sem cliente não pode ter NF preenchida  
    # Mantém a NF para posterior validação quando o cliente for definido
    if not item_embarque.cnpj_cliente:
        item_embarque.erro_validacao = f"CLIENTE_NAO_DEFINIDO: Defina o cliente antes de preencher a NF"
        
        # ✅ MANTÉM a NF para validação posterior (quando cliente for definido)
        # NÃO apaga a NF - apenas marca como pendente de definição de cliente
        # Se o usuário informar o CNPJ depois, a validação será refeita
        
        return False, f"❌ BLOQUEADO: Defina o cliente antes de preencher a NF {item_embarque.nota_fiscal}"
    
    # Limpa erro se havia (caso padrão de sucesso)
    item_embarque.erro_validacao = None
    return True, None

def sincronizar_nf_embarque_pedido(embarque_id):
    """
    ✅ FUNÇÃO CORRIGIDA: Sincroniza as NFs do embarque com os pedidos correspondentes
    
    Para cada item do embarque:
    1. Se tem NF preenchida E separacao_lote_id, busca o pedido correspondente
    2. Usa separacao_lote_id para garantir precisão (evita problemas com embarques parciais)
    3. Atualiza o campo 'nf' do pedido
    4. Atualiza o status do pedido automaticamente (via trigger)
    
    Esta função resolve o problema de pedidos ficarem "EMBARCADO" 
    quando deveriam estar "FATURADO" após preenchimento da NF.
    """
    try:
        embarque = Embarque.query.get(embarque_id)
        if not embarque:
            return False, "Embarque não encontrado"
        
        itens_sincronizados = 0
        itens_sem_lote = 0
        erros = []
        
        for item in embarque.itens:
            # Se o item tem NF preenchida, sincroniza com o pedido
            if item.nota_fiscal and item.nota_fiscal.strip():
                
                # ✅ CORREÇÃO: Usar separacao_lote_id para busca precisa
                if item.separacao_lote_id:
                    # Busca o pedido pelo lote de separação (mais seguro)
                    pedido = Pedido.query.filter_by(separacao_lote_id=item.separacao_lote_id).first()
                    
                    if pedido:
                        # Atualiza a NF no pedido
                        pedido.nf = item.nota_fiscal
                        # O status será atualizado automaticamente pelo trigger
                        itens_sincronizados += 1
                        print(f"[DEBUG] 🔄 Pedido {pedido.num_pedido} (Lote: {item.separacao_lote_id}): NF atualizada para {item.nota_fiscal}")
                    else:
                        erros.append(f"Pedido com lote {item.separacao_lote_id} não encontrado na base de dados")
                else:
                    # Fallback: Se não tem lote, tenta buscar por num_pedido (menos seguro)
                    itens_sem_lote += 1
                    pedido = Pedido.query.filter_by(num_pedido=item.pedido).first()
                    
                    if pedido:
                        pedido.nf = item.nota_fiscal
                        itens_sincronizados += 1
                        print(f"[DEBUG] ⚠️ Pedido {pedido.num_pedido} (SEM LOTE): NF atualizada para {item.nota_fiscal}")
                    else:
                        erros.append(f"Pedido {item.pedido} não encontrado na base de dados")
        
        db.session.commit()
        
        resultado_msg = f"✅ {itens_sincronizados} pedido(s) sincronizado(s) com suas NFs"
        
        if itens_sem_lote > 0:
            resultado_msg += f" ({itens_sem_lote} sem lote de separação - menos seguro)"
        
        if erros:
            resultado_msg += f" | ⚠️ {len(erros)} erro(s): {'; '.join(erros[:2])}"
        
        if itens_sincronizados > 0:
            print(f"[DEBUG] ✅ {itens_sincronizados} pedidos sincronizados com NFs")
            return True, resultado_msg
        else:
            return True, "Nenhuma NF para sincronizar"
            
    except Exception as e:
        db.session.rollback()
        error_msg = f"Erro ao sincronizar NFs com pedidos: {str(e)}"
        print(f"[DEBUG] ❌ {error_msg}")
        return False, error_msg

def atualizar_status_pedido_nf_cd(numero_pedido, separacao_lote_id=None):
    """
    ✅ FUNÇÃO CORRIGIDA: Atualiza status do pedido para "NF no CD"
    
    Implementa o item 2-d do processo_completo.md:
    - Quando uma NF volta para o CD, altera o status do pedido
    - Remove data de embarque para permitir nova cotação
    - Usa separacao_lote_id quando disponível para maior precisão
    """
    try:
        pedido = None
        
        # ✅ CORREÇÃO: Priorizar busca por separacao_lote_id quando disponível
        if separacao_lote_id:
            pedido = Pedido.query.filter_by(separacao_lote_id=separacao_lote_id).first()
            print(f"[DEBUG] 🔍 Busca por lote {separacao_lote_id}: {'Encontrado' if pedido else 'Não encontrado'}")
        
        # Fallback: Se não encontrou por lote, busca por número do pedido
        if not pedido and numero_pedido:
            pedido = Pedido.query.filter_by(num_pedido=numero_pedido).first()
            print(f"[DEBUG] 🔍 Busca por num_pedido {numero_pedido}: {'Encontrado' if pedido else 'Não encontrado'}")
        
        if pedido:
            # Remove dados de embarque para permitir nova cotação
            pedido.data_embarque = None
            pedido.nf = None  # Remove NF para voltar ao status anterior
            # Status será recalculado automaticamente pelo trigger
            
            db.session.commit()
            print(f"[DEBUG] 📦 Pedido {pedido.num_pedido} (Lote: {pedido.separacao_lote_id}): Status atualizado para 'NF no CD'")
            return True, f"Pedido {pedido.num_pedido} atualizado para 'NF no CD'"
        else:
            return False, f"Pedido não encontrado (num_pedido: {numero_pedido}, lote: {separacao_lote_id})"
            
    except Exception as e:
        db.session.rollback()
        return False, f"Erro ao atualizar pedido: {str(e)}"


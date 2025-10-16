from flask import request, flash, url_for, redirect, render_template, Blueprint, jsonify, session
from sqlalchemy import or_, cast, String
from flask_login import login_required, current_user
from app import db
from app.utils.auth_decorators import require_embarques
from app.embarques.forms import EmbarqueForm, EmbarqueItemForm
from app.transportadoras.models import Transportadora
from app.embarques.models import Embarque, EmbarqueItem
from app.utils.sincronizar_entregas import sincronizar_entrega_por_nf, sincronizar_nova_entrega_por_nf
from app.monitoramento.models import EntregaMonitorada
from app.localidades.models import Cidade
from datetime import datetime
from app.pedidos.models import Pedido
from app.separacao.models import Separacao
from app.cotacao.models import Cotacao
from app.utils.embarque_numero import obter_proximo_numero_embarque
from app.rastreamento.services.qrcode_service import QRCodeService  # 🚚 QR Code rastreamento
import logging

logger = logging.getLogger(__name__)


embarques_bp = Blueprint('embarques', __name__,url_prefix='/embarques')

# Importa a função centralizada

def apagar_fretes_sem_cte_embarque(embarque_id):
    """
    🔧 NOVA FUNÇÃO: Apaga fretes existentes do embarque que não possuem CTe preenchido
    
    Esta função resolve o problema de sincronização entre embarques e fretes:
    - Busca todos os fretes do embarque
    - Remove apenas os fretes que NÃO têm CTe preenchido
    - Preserva fretes que já têm CTe (para não perder dados já processados)
    - Retorna informações sobre a operação
    """
    try:
        from app.fretes.models import Frete
        
        # Busca fretes do embarque sem CTe preenchido
        fretes_sem_cte = Frete.query.filter(
            Frete.embarque_id == embarque_id,
            Frete.status != 'CANCELADO',
            db.or_(
                Frete.numero_cte.is_(None),
                Frete.numero_cte == '',
                Frete.valor_cte.is_(None)
            )
        ).all()
        
        if not fretes_sem_cte:
            return True, "Nenhum frete sem CTe encontrado"
        
        # Remove os fretes sem CTe
        fretes_removidos = []
        for frete in fretes_sem_cte:
            fretes_removidos.append(f"Frete #{frete.id} (CNPJ: {frete.cnpj_cliente})")
            db.session.delete(frete)
        
        # Não faz commit aqui - será feito junto com o salvamento do embarque
        
        return True, f"✅ {len(fretes_removidos)} frete(s) sem CTe removido(s) antes do salvamento"
        
    except Exception as e:
        return False, f"Erro ao apagar fretes sem CTe: {str(e)}"

@embarques_bp.route('/<int:id>', methods=['GET', 'POST'])
@login_required
@require_embarques()  # 🔒 VENDEDORES: Apenas com dados próprios
def visualizar_embarque(id):
    embarque = Embarque.query.get_or_404(id)
    
    # 🔒 VERIFICAÇÃO ESPECÍFICA PARA VENDEDORES
    if current_user.perfil == 'vendedor':
        # Verifica se o vendedor tem permissão para ver este embarque
        tem_permissao = False
        from app.utils.auth_decorators import check_vendedor_permission
        for item in embarque.itens:
            if check_vendedor_permission(numero_nf=item.nota_fiscal):
                tem_permissao = True
                break
        
        if not tem_permissao:
            flash('Acesso negado. Você só pode visualizar embarques dos seus clientes.', 'danger')
            return redirect(url_for('embarques.listar_embarques'))

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
        
        if action == 'add_item':
            # Código para adicionar item
            dados_portaria = obter_dados_portaria_embarque(embarque.id)
            
            # Buscar dados de impressão
            from app.pedidos.models import Pedido
            pedidos_impressos = {}
            for item in embarque.itens:
                if item.separacao_lote_id:
                    pedido = Pedido.query.filter_by(separacao_lote_id=item.separacao_lote_id).first()
                    if pedido:
                        pedidos_impressos[item.separacao_lote_id] = {
                            'impresso': pedido.separacao_impressa,
                            'impresso_em': pedido.separacao_impressa_em,
                            'impresso_por': pedido.separacao_impressa_por
                        }
            
            return render_template('embarques/visualizar_embarque.html', 
                                 form=form, 
                                 embarque=embarque, 
                                 dados_portaria=dados_portaria,
                                 pedidos_impressos=pedidos_impressos)

        elif action == 'save':
            # 🔧 NOVA LÓGICA: Antes de salvar, remove fretes sem CTe
            try:
                sucesso_limpeza, resultado_limpeza = apagar_fretes_sem_cte_embarque(embarque.id)
                if sucesso_limpeza:
                    flash(f"🔄 {resultado_limpeza}", "info")
                else:
                    flash(f"⚠️ {resultado_limpeza}", "warning")
            except Exception as e:
                flash(f"⚠️ Erro na limpeza de fretes: {str(e)}", "warning")
            
            # Agora sim, validar
            if form.validate_on_submit():
                # Salvar cabeçalho no DB
                if form.data_embarque.data:
                    embarque.data_embarque = datetime.strptime(form.data_embarque.data, '%d/%m/%Y').date()
                else:
                    embarque.data_embarque = None

                # Adicionar campo data_prevista_embarque
                if form.data_prevista_embarque.data:
                    embarque.data_prevista_embarque = datetime.strptime(form.data_prevista_embarque.data, '%d/%m/%Y').date()
                else:
                    embarque.data_prevista_embarque = None

                # ✅ READONLY: Transportadora não é mais editável - mantém valor existente
                embarque.observacoes = form.observacoes.data
                embarque.paletizado = form.paletizado.data
                embarque.laudo_anexado = form.laudo_anexado.data
                embarque.embalagem_aprovada = form.embalagem_aprovada.data
                embarque.transporte_aprovado = form.transporte_aprovado.data
                embarque.horario_carregamento = form.horario_carregamento.data
                embarque.responsavel_carregamento = form.responsavel_carregamento.data
                embarque.nome_motorista = form.nome_motorista.data
                embarque.cpf_motorista = form.cpf_motorista.data
                form.qtd_pallets.data = int(form.qtd_pallets.data or 0)

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

                        # ✅ SINCRONIZAÇÃO: Propagar alterações para outras tabelas
                        from app.pedidos.services.sincronizacao_agendamento_service import SincronizadorAgendamentoService

                        try:
                            sincronizador = SincronizadorAgendamentoService(usuario=current_user.nome if hasattr(current_user, 'nome') else 'Sistema')

                            # Converter data_agenda (String DD/MM/YYYY) para Date
                            data_agendamento = None
                            if item_existente.data_agenda:
                                try:
                                    data_agendamento = datetime.strptime(item_existente.data_agenda, '%d/%m/%Y').date()
                                except Exception as e:
                                    print(f"[SINCRONIZAÇÃO EMBARQUE_ITEM] Erro ao converter data_agenda: {e}")
                                    pass

                            dados_agendamento = {
                                'agendamento': data_agendamento,
                                'protocolo': item_existente.protocolo_agendamento,
                                'agendamento_confirmado': getattr(item_existente, 'agendamento_confirmado', False),
                                'numero_nf': item_existente.nota_fiscal
                            }

                            identificador = {
                                'separacao_lote_id': item_existente.separacao_lote_id,
                                'numero_nf': item_existente.nota_fiscal
                            }

                            resultado = sincronizador.sincronizar_agendamento(dados_agendamento, identificador)

                            if resultado['success'] and resultado['tabelas_atualizadas']:
                                print(f"[SINCRONIZAÇÃO EMBARQUE_ITEM] Lote {item_existente.separacao_lote_id}: {', '.join(resultado['tabelas_atualizadas'])}")

                        except Exception as e:
                            print(f"[SINCRONIZAÇÃO EMBARQUE_ITEM] Erro: {e}")

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

                # ✅ SINCRONIZAÇÃO SEMPRE: Executa toda vez que salvar o embarque
                try:
                    sucesso_sync, resultado_sync = sincronizar_nf_embarque_pedido_completa(embarque.id)
                    if sucesso_sync:
                        messages_sync.append(f"🔄 {resultado_sync}")
                    else:
                        messages_sync.append(f"⚠️ Erro na sincronização: {resultado_sync}")
                except Exception as e:
                    print(f"Erro na sincronização de NFs: {e}")
                    messages_sync.append(f"⚠️ Erro na sincronização de NFs: {e}")

                # Validação de CNPJ sempre executa
                try:
                    from app.fretes.routes import validar_cnpj_embarque_faturamento
                    sucesso_validacao, resultado_validacao = validar_cnpj_embarque_faturamento(embarque.id)
                    if not sucesso_validacao:
                        messages_validacao.append(f"⚠️ {resultado_validacao}")
                except Exception as e:
                    print(f"Erro na validação de CNPJ: {e}")
                    messages_validacao.append(f"⚠️ Erro na validação de CNPJ: {e}")

                # Lançamento automático de fretes sempre executa
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

                # Sincronização de entregas sempre executa
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

                # ✅ SINCRONIZAÇÃO: Atualizar expedição nas Separacoes quando data_prevista_embarque mudar
                if embarque.data_prevista_embarque:
                    from app.separacao.models import Separacao

                    count_total = 0
                    for item in embarque.itens_ativos:
                        if item.separacao_lote_id:
                            count = Separacao.query.filter_by(
                                separacao_lote_id=item.separacao_lote_id
                            ).update({'expedicao': embarque.data_prevista_embarque})
                            count_total += count

                    if count_total > 0:
                        print(f"[SINCRONIZAÇÃO EMBARQUE] {count_total} separações atualizadas com expedição {embarque.data_prevista_embarque}")
                        messages_sync.append(f"📅 {count_total} pedidos atualizados com nova data de expedição")

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
        # Tratamento seguro para datas que podem vir como string ou date
        if embarque.data_embarque:
            if hasattr(embarque.data_embarque, 'strftime'):
                form.data_embarque.data = embarque.data_embarque.strftime('%d/%m/%Y')
            else:
                # Se já é string, usa como está
                form.data_embarque.data = str(embarque.data_embarque)
        else:
            form.data_embarque.data = ''
            
        if embarque.data_prevista_embarque:
            if hasattr(embarque.data_prevista_embarque, 'strftime'):
                form.data_prevista_embarque.data = embarque.data_prevista_embarque.strftime('%d/%m/%Y')
            else:
                # Se já é string, usa como está
                form.data_prevista_embarque.data = str(embarque.data_prevista_embarque)
        else:
            form.data_prevista_embarque.data = ''
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
        
        # Buscar dados de impressão dos pedidos
        from app.pedidos.models import Pedido
        pedidos_impressos = {}
        for item in embarque.itens:
            if item.separacao_lote_id:
                pedido = Pedido.query.filter_by(separacao_lote_id=item.separacao_lote_id).first()
                if pedido:
                    pedidos_impressos[item.separacao_lote_id] = {
                        'impresso': pedido.separacao_impressa,
                        'impresso_em': pedido.separacao_impressa_em,
                        'impresso_por': pedido.separacao_impressa_por
                    }
        
        return render_template('embarques/visualizar_embarque.html', 
                             form=form, 
                             embarque=embarque, 
                             dados_portaria=dados_portaria,
                             pedidos_impressos=pedidos_impressos)
  
@embarques_bp.route('/listar_embarques')
@require_embarques()  # 🔒 VENDEDORES: Apenas com dados próprios
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

    # ✅ NOVO: Pré-filtro - Mostra apenas embarques ativos sem data de embarque (por padrão)
    mostrar_todos = request.args.get('mostrar_todos', '').lower() == 'true'
    
    # Query base
    query = Embarque.query.options(db.joinedload(Embarque.transportadora))
    query = query.outerjoin(EmbarqueItem).outerjoin(Transportadora)
    
    # ✅ APLICAR PRÉ-FILTRO (apenas se não foi solicitado "mostrar todos")
    if not mostrar_todos:
        query = query.filter(
            Embarque.status == 'ativo',
            Embarque.data_embarque.is_(None)
        )

    # Aplicar filtros
    filtros_aplicados = not mostrar_todos  # Se não está mostrando todos, filtro está aplicado
    
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

    # Filtro por data prevista início
    data_prevista_inicio = request.args.get('data_prevista_inicio', '').strip()
    if data_prevista_inicio:
        try:
            data_prevista_inicio_obj = datetime.strptime(data_prevista_inicio, '%d/%m/%Y').date()
            query = query.filter(Embarque.data_prevista_embarque >= data_prevista_inicio_obj)
            form_filtros.data_prevista_inicio.data = data_prevista_inicio
            filtros_aplicados = True
        except ValueError:
            flash('Data prevista de início inválida. Use o formato DD/MM/AAAA', 'warning')

    # Filtro por data prevista fim
    data_prevista_fim = request.args.get('data_prevista_fim', '').strip()
    if data_prevista_fim:
        try:
            data_prevista_fim_obj = datetime.strptime(data_prevista_fim, '%d/%m/%Y').date()
            query = query.filter(Embarque.data_prevista_embarque <= data_prevista_fim_obj)
            form_filtros.data_prevista_fim.data = data_prevista_fim
            filtros_aplicados = True
        except ValueError:
            flash('Data prevista de fim inválida. Use o formato DD/MM/AAAA', 'warning')

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

    # ✅ CORREÇÃO: Se há filtros de propriedades calculadas, buscar TODOS antes de paginar
    if (status_nfs and status_nfs != '') or (status_fretes and status_fretes != ''):
        # Buscar todos os embarques (sem paginação)
        embarques_todos = query.all()

        # Aplicar filtros de propriedades calculadas
        if status_nfs and status_nfs != '':
            embarques_todos = [e for e in embarques_todos if e.status_nfs == status_nfs]

        if status_fretes and status_fretes != '':
            embarques_todos = [e for e in embarques_todos if e.status_fretes == status_fretes]

        # Criar paginação MANUAL após filtros
        page = request.args.get('page', 1, type=int)
        per_page = 100
        total_filtrado = len(embarques_todos)
        total_pages = (total_filtrado + per_page - 1) // per_page  # Ceiling division

        # Calcular índices de slice para paginação
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        embarques = embarques_todos[start_idx:end_idx]

        # Criar objeto paginacao manual compatível com template
        class PaginacaoManual:
            def __init__(self, items, page, per_page, total):
                self.items = items
                self.page = page
                self.per_page = per_page
                self.total = total
                self.pages = (total + per_page - 1) // per_page
                self.has_prev = page > 1
                self.has_next = page < self.pages
                self.prev_num = page - 1 if self.has_prev else None
                self.next_num = page + 1 if self.has_next else None

            def iter_pages(self, left_edge=2, left_current=2, right_current=3, right_edge=2):
                """Gera números de página para navegação (compatível com Flask-SQLAlchemy)"""
                last = 0
                for num in range(1, self.pages + 1):
                    if (num <= left_edge or
                    (num > self.page - left_current - 1 and num < self.page + right_current) or num > self.pages - right_edge): 
                        if last + 1 != num:
                            yield None
                        yield num
                        last = num

        paginacao = PaginacaoManual(embarques, page, per_page, total_filtrado)
    else:
        # Paginação normal (sem filtros de propriedades calculadas)
        page = request.args.get('page', 1, type=int)
        per_page = 100
        paginacao = query.paginate(page=page, per_page=per_page, error_out=False)
        embarques = paginacao.items

    return render_template(
        'embarques/listar_embarques.html',
        embarques=embarques,
        paginacao=paginacao,
        form_filtros=form_filtros,
        filtros_aplicados=filtros_aplicados,
        mostrar_todos=mostrar_todos
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
        form.data_prevista_embarque.data = (
            embarque.data_prevista_embarque.strftime('%d/%m/%Y') if embarque.data_prevista_embarque else ''
        )
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
        
        # ✅ ATUALIZADO: Remover NFs dos itens e sincronizar com pedidos
        try:
            # 1. Remove as NFs de todos os itens do embarque que tinham NF
            nfs_removidas = 0
            for item in embarque.itens:
                if item.nota_fiscal and item.nota_fiscal.strip():
                    print(f"[CANCEL] Removendo NF {item.nota_fiscal} do item {item.pedido}")
                    item.nota_fiscal = None  # Remove a NF
                    nfs_removidas += 1
            
            # 2. Cancela todos os itens do embarque e reverte campos nas Separações
            from app.separacao.models import Separacao
            lotes_revertidos = set()
            
            for item in embarque.itens:
                item.status = 'cancelado'
                
                # ✅ REVERTER campos nas Separações quando cancela embarque completo
                if item.separacao_lote_id and item.separacao_lote_id not in lotes_revertidos:
                    lotes_revertidos.add(item.separacao_lote_id)
                    
                    # Atualizar TODAS as linhas do lote
                    separacoes = Separacao.query.filter_by(
                        separacao_lote_id=item.separacao_lote_id
                    ).all()
                    
                    for sep in separacoes:
                        mudancas = []
                        
                        # Limpar data_embarque se corresponder
                        if embarque.data_embarque and sep.data_embarque == embarque.data_embarque:
                            sep.data_embarque = None
                            mudancas.append('data_embarque')
                        
                        # Limpar cotacao_id se corresponder
                        if embarque.cotacao_id and sep.cotacao_id == embarque.cotacao_id:
                            sep.cotacao_id = None
                            mudancas.append('cotacao_id')
                        
                        if mudancas:
                            print(f"[CANCEL] Lote {item.separacao_lote_id}, produto {sep.cod_produto}: {', '.join(mudancas)} limpos")
            
            if lotes_revertidos:
                print(f"[CANCEL] Total de {len(lotes_revertidos)} lotes revertidos do embarque #{embarque.numero}")
            
            # 3. ✅ USAR SINCRONIZAÇÃO COMPLETA: Sincroniza as mudanças com os pedidos
            print(f"[CANCEL] 🔄 Iniciando sincronização para embarque #{embarque.numero}")
            sucesso_sync, resultado_sync = sincronizar_nf_embarque_pedido_completa(embarque.id)
            print(f"[CANCEL] 📊 Resultado da sincronização: {sucesso_sync} - {resultado_sync}")
            
            if nfs_removidas > 0:
                flash(f"✅ {nfs_removidas} NF(s) removida(s) dos itens do embarque", "info")
            
            if sucesso_sync:
                flash(f"✅ Sincronização com pedidos: {resultado_sync}", "info")
            else:
                flash(f"⚠️ Erro na sincronização com pedidos: {resultado_sync}", "warning")
                
        except Exception as e:
            flash(f"⚠️ Erro ao remover NFs e sincronizar: {str(e)}", "warning")
        
        # ✅ NOVO: Cancelar fretes vinculados ao embarque
        try:
            from app.fretes.routes import cancelar_frete_por_embarque
            
            sucesso, mensagem = cancelar_frete_por_embarque(
                embarque_id=embarque.id,
                usuario=current_user.nome if current_user.is_authenticated else 'Sistema'
            )
            
            if sucesso:
                flash(f"✅ Fretes cancelados: {mensagem}", "info")
            else:
                flash(f"⚠️ Erro ao cancelar fretes: {mensagem}", "warning")
                
        except Exception as e:
            flash(f"⚠️ Erro ao cancelar fretes: {str(e)}", "warning")
        
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


@embarques_bp.route('/<int:id>/dados_tabela')
@login_required
def dados_tabela_embarque(id):
    """
    Exibe os dados da tabela de frete do embarque
    """
    embarque = Embarque.query.get_or_404(id)
    
    # Carrega apenas os itens ativos do embarque
    itens = EmbarqueItem.query.filter_by(embarque_id=embarque.id, status='ativo').all()
    
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
    from app.pedidos.models import Pedido
    from flask import make_response
    
    embarque = Embarque.query.get_or_404(embarque_id)
    
    # Marcar separação como impressa diretamente em Separacao
    pedido = Pedido.query.filter_by(separacao_lote_id=separacao_lote_id).first()
    if pedido and not pedido.separacao_impressa:
        Separacao.query.filter_by(
            separacao_lote_id=separacao_lote_id
        ).update({
            'separacao_impressa': True,
            'separacao_impressa_em': datetime.now(),
            'separacao_impressa_por': current_user.nome if hasattr(current_user, 'nome') else current_user.email
        })
        db.session.commit()
    
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

    # 🚚 Gerar QR Code para rastreamento
    qrcode_base64 = None
    if hasattr(embarque, 'rastreamento') and embarque.rastreamento:
        url_rastreamento = embarque.rastreamento.url_rastreamento
        qrcode_base64 = QRCodeService.gerar_qrcode(url_rastreamento, tamanho=8, borda=1)

    # Renderiza template específico para impressão do embarque
    html = render_template(
        'embarques/imprimir_embarque.html',
        embarque=embarque,
        data_impressao=datetime.now(),
        current_user=current_user,
        qrcode_base64=qrcode_base64  # 🚚 QR Code
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
    from app.pedidos.models import Pedido
    from flask import make_response
    
    embarque = Embarque.query.get_or_404(embarque_id)
    
    # Verificar se a data prevista de embarque está preenchida
    if not embarque.data_prevista_embarque:
        flash('⚠️ A Data Prevista de Embarque deve ser preenchida antes de imprimir o relatório completo.', 'warning')
        return redirect(url_for('embarques.visualizar_embarque', id=embarque_id))
    
    # Marcar todos os pedidos dos itens ativos como impressos
    for item in embarque.itens:
        if item.status == 'ativo' and item.separacao_lote_id:
            pedido = Pedido.query.filter_by(separacao_lote_id=item.separacao_lote_id).first()
            if pedido and not pedido.separacao_impressa:
                Separacao.query.filter_by(
                    separacao_lote_id=item.separacao_lote_id
                ).update({
                    'separacao_impressa': True,
                    'separacao_impressa_em': datetime.now(),
                    'separacao_impressa_por': current_user.nome if hasattr(current_user, 'nome') else current_user.email
                })
    db.session.commit()
    
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
    
    # 🚚 Gerar QR Code para rastreamento
    qrcode_base64 = None
    if hasattr(embarque, 'rastreamento') and embarque.rastreamento:
        url_rastreamento = embarque.rastreamento.url_rastreamento
        qrcode_base64 = QRCodeService.gerar_qrcode(url_rastreamento, tamanho=8, borda=1)

    # Renderiza template específico para impressão completa
    html = render_template(
        'embarques/imprimir_completo.html',
        embarque=embarque,
        separacoes_data=separacoes_data,
        data_impressao=datetime.now(),
        current_user=current_user,
        qrcode_base64=qrcode_base64  # 🚚 QR Code
    )
    
    response = make_response(html)
    response.headers['Content-Type'] = 'text/html; charset=utf-8'
    return response

@embarques_bp.route('/<int:embarque_id>/registrar_impressao', methods=['POST'])
@login_required
def registrar_impressao(embarque_id):
    """
    Registra que o embarque foi impresso
    """

    embarque = Embarque.query.get_or_404(embarque_id)
    
    # Verificar se a data prevista de embarque está preenchida
    if not embarque.data_prevista_embarque:
        return jsonify({'success': False, 'message': 'A Data Prevista de Embarque deve ser preenchida antes de imprimir.'})
    
    # Registrar a impressão (você pode criar uma tabela específica para isso ou usar um campo no embarque)
    # Por enquanto, vamos apenas retornar os dados para exibir
    usuario_nome = current_user.nome if current_user.is_authenticated and hasattr(current_user, 'nome') and current_user.nome else (current_user.email if current_user.is_authenticated else 'Sistema')
    data_impressao = datetime.now()
    
    return jsonify({
        'success': True, 
        'usuario': usuario_nome,
        'data_impressao': data_impressao.strftime('%d/%m/%Y às %H:%M:%S')
    })

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
    from app.utils.cnpj_utils import normalizar_cnpj
    
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
        # 🔧 NORMALIZAR CNPJs para comparação (remove formatação)
        cnpj_embarque_normalizado = normalizar_cnpj(item_embarque.cnpj_cliente)
        cnpj_faturamento_normalizado = normalizar_cnpj(nf_faturamento.cnpj_cliente)
        
        if cnpj_embarque_normalizado != cnpj_faturamento_normalizado:
            # 🔧 FALLBACK INTELIGENTE: Verifica se o CNPJ da NF começa com 0
            # Se sim, tenta adicionar 0 no início do CNPJ do embarque
            if cnpj_faturamento_normalizado and cnpj_faturamento_normalizado[0] == '0':
                # O CNPJ da NF começa com 0, vamos tentar adicionar 0 no CNPJ do embarque
                cnpj_embarque_com_zero = '0' + cnpj_embarque_normalizado
                
                # Verifica se agora os CNPJs batem
                if cnpj_embarque_com_zero == cnpj_faturamento_normalizado:
                    # ✅ SUCESSO! O problema era o zero faltando
                    print(f"[INFO] ✅ CNPJ corrigido: {cnpj_embarque_normalizado} -> {cnpj_embarque_com_zero}")
                    
                    # Atualiza o CNPJ do item_embarque com o zero na frente
                    item_embarque.cnpj_cliente = cnpj_embarque_com_zero
                    
                    # Atualiza peso e valor da NF
                    item_embarque.peso = float(nf_faturamento.peso_bruto or 0)
                    item_embarque.valor = float(nf_faturamento.valor_total or 0)
                    item_embarque.erro_validacao = None
                    
                    # Log da correção
                    print(f"[INFO] ✅ NF {item_embarque.nota_fiscal} validada após correção do CNPJ")
                    
                    return True, None
            
            # Se não conseguiu corrigir com o fallback, mantém o erro original
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
    
    # ✅ CORREÇÃO FINAL: Se não há CNPJ, é erro de dados - não deveria acontecer
    # Todo pedido tem CNPJ obrigatório, então se chegou aqui sem CNPJ é bug do sistema
    if not item_embarque.cnpj_cliente:
        print(f"[DEBUG] ⚠️ AVISO: Item sem CNPJ detectado - isso não deveria acontecer!")
        print(f"[DEBUG]   Item: {item_embarque.pedido} - Cliente: {item_embarque.cliente}")
        # NÃO bloqueia nem marca erro - apenas permite continuar
        return True, None
    
    # Limpa erro se havia (caso padrão de sucesso)
    item_embarque.erro_validacao = None
    return True, None

def sincronizar_nf_embarque_pedido_completa(embarque_id):
    """
    ✅ FUNÇÃO OTIMIZADA: Sincronização bidirecional entre embarque e pedidos
    
    1. ADICIONA NF no pedido quando preenchida no embarque
    2. REMOVE NF do pedido quando apagada no embarque  
    3. ATUALIZA status do pedido conforme situação
    4. TRATAMENTO ESPECIAL para embarques FOB
    
    Versão otimizada com menos logs e melhor performance.
    """
    
    try:
        embarque = Embarque.query.get(embarque_id)
        if not embarque:
            return False, "Embarque não encontrado"
        
        # Detectar se é embarque FOB
        is_embarque_fob = (
            embarque.tipo_carga == 'FOB' or 
            (embarque.transportadora and embarque.transportadora.razao_social == "FOB - COLETA")
        )
        
        # Buscar transportadora e cotação FOB se necessário
        transportadora_fob = None
        cotacao_fob = None
        
        if is_embarque_fob:
            transportadora_fob = Transportadora.query.filter_by(razao_social="FOB - COLETA").first()
            
            if transportadora_fob:
                # Busca ou cria cotação FOB global
                cotacao_fob = Cotacao.query.filter_by(
                    transportadora_id=transportadora_fob.id,
                    tipo_carga='FOB'
                ).first()
                
                if not cotacao_fob:
                    cotacao_fob = Cotacao(
                        usuario_id=1,
                        transportadora_id=transportadora_fob.id,
                        status='Fechado',
                        data_criacao=datetime.now(),
                        data_fechamento=datetime.now(),
                        tipo_carga='FOB',
                        valor_total=0,
                        peso_total=0,
                        pallet_total=0,
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
                    print(f"[SYNC] Cotação FOB criada com ID {cotacao_fob.id}")
        
        # Contadores de operações
        itens_sincronizados = 0
        itens_removidos = 0
        itens_cancelados = 0
        erros = []
        
        # Processar cada item do embarque
        for item in embarque.itens:
            # Buscar pedido (otimizado) - usando VIEW para leitura
            pedido = None
            
            if item.separacao_lote_id:
                pedido = Pedido.query.filter_by(separacao_lote_id=item.separacao_lote_id).first()
                # Atualiza flag nf_cd diretamente em Separacao
                if pedido and pedido.nf_cd == True:
                    Separacao.query.filter_by(
                        separacao_lote_id=item.separacao_lote_id
                    ).update({'nf_cd': False})                   
            
            if not pedido and item.pedido:
                pedido = Pedido.query.filter_by(num_pedido=item.pedido).first()
            
            if not pedido:
                erros.append(f"Pedido {item.pedido} não encontrado")
                continue
            
            # PROCESSAMENTO POR TIPO DE OPERAÇÃO
            
            if item.status == 'cancelado':
                # ✅ ITEM CANCELADO: Aplicar lógica consolidada
                print(f"[SYNC] 🔄 Item cancelado - Pedido {pedido.num_pedido} (Lote: {item.separacao_lote_id})")
                
                # ✅ VERIFICAR OUTROS EMBARQUES ATIVOS
                outros_embarques_ativos = EmbarqueItem.query.join(Embarque).filter(
                    EmbarqueItem.separacao_lote_id == item.separacao_lote_id,
                    EmbarqueItem.status == 'ativo',
                    Embarque.status == 'ativo',
                ).first()
                
                # ✅ VERIFICAR ENTREGAS MONITORADAS VINCULADAS
                entregas_vinculadas = EntregaMonitorada.query.filter_by(
                    separacao_lote_id=item.separacao_lote_id
                ).all()
                
                # 🔧 CORREÇÃO: Se não encontrou por lote, buscar por NF (95% dos casos!)
                if not entregas_vinculadas and item.nota_fiscal:
                    entregas_vinculadas = EntregaMonitorada.query.filter_by(
                        numero_nf=item.nota_fiscal
                    ).all()
                    if entregas_vinculadas:
                        print(f"[SYNC] 🔍 Encontrada entrega pela NF {item.nota_fiscal} (fallback)")
                
                tem_entrega_no_cd = any(e.nf_cd for e in entregas_vinculadas)
                
                # ✅ LOGS DETALHADOS PARA AUDITORIA
                print(f"[SYNC] 📊 Análise cancelamento:")
                print(f"[SYNC]    Separação: {item.separacao_lote_id}")
                print(f"[SYNC]    Outros embarques ativos: {bool(outros_embarques_ativos)}")
                print(f"[SYNC]    Entregas vinculadas: {len(entregas_vinculadas)}")
                print(f"[SYNC]    Alguma entrega no CD: {tem_entrega_no_cd}")
                
                # ✅ LÓGICA CONSOLIDADA
                if not outros_embarques_ativos:
                    # NÃO HÁ OUTROS EMBARQUES ATIVOS
                    
                    if entregas_vinculadas:
                        # ✅ HÁ ENTREGAS VINCULADAS → NF voltou para CD
                        Separacao.query.filter_by(
                            separacao_lote_id=item.separacao_lote_id
                        ).update({'nf_cd': True})
                        # MANTÉM numero_nf (não apaga)
                        print(f"[SYNC] 📦 NF {pedido.nf} voltou para o CD (nf_cd=True)")
                        
                    else:
                        # ✅ NÃO HÁ ENTREGAS VINCULADAS → Reset completo
                        Separacao.query.filter_by(
                            separacao_lote_id=item.separacao_lote_id
                        ).update({
                            'numero_nf': None,
                            'data_embarque': None,
                            'cotacao_id': None,
                            'nf_cd': False
                        })
                        # transportadora ignorado conforme orientação
                        print(f"[SYNC] 🔄 Pedido {pedido.num_pedido} resetado para 'Aberto'")
                        
                else:
                    # HÁ OUTROS EMBARQUES ATIVOS
                    
                    if entregas_vinculadas:
                        # ✅ SINCRONIZAR ESTADO COM ENTREGAS MONITORADAS
                        Separacao.query.filter_by(
                            separacao_lote_id=item.separacao_lote_id
                        ).update({'nf_cd': tem_entrega_no_cd})
                        print(f"[SYNC] 🔗 Estado sincronizado: nf_cd={tem_entrega_no_cd}")
                        
                    else:
                        # ✅ NÃO MEXE NO PEDIDO
                        print(f"[SYNC] 🤷 Outros embarques ativos - mantendo status do pedido")
                
                itens_cancelados += 1
                
            elif item.nota_fiscal and item.nota_fiscal.strip():
                # ✅ ITEM COM NF: Sincronizar NF em Separacao
                Separacao.query.filter_by(
                    separacao_lote_id=item.separacao_lote_id
                ).update({'numero_nf': item.nota_fiscal})
                
                # Configuração especial FOB
                if is_embarque_fob and transportadora_fob and cotacao_fob:
                    # Transportadora ignorado conforme orientação
                    if not pedido.cotacao_id:
                        Separacao.query.filter_by(
                            separacao_lote_id=item.separacao_lote_id
                        ).update({'cotacao_id': cotacao_fob.id})
                
                itens_sincronizados += 1
                
            else:
                # ✅ ITEM SEM NF: Remover NF de Separacao se existir
                if pedido.nf:
                    Separacao.query.filter_by(
                        separacao_lote_id=item.separacao_lote_id
                    ).update({'numero_nf': None})
                    itens_removidos += 1
        
        # Salvar todas as alterações
        db.session.commit()
        
        # ✅ VERIFICAÇÃO PÓS-COMMIT: Confirma se as alterações foram persistidas
        if itens_cancelados > 0:
            print(f"[SYNC] 🔍 Verificação pós-commit - Confirmando alterações nos pedidos:")
            for item in embarque.itens:
                if item.status == 'cancelado':
                    # Recarrega o pedido do banco após commit
                    pedido_verificacao = None
                    if item.separacao_lote_id:
                        pedido_verificacao = Pedido.query.filter_by(separacao_lote_id=item.separacao_lote_id).first()
                    elif item.pedido:
                        pedido_verificacao = Pedido.query.filter_by(num_pedido=item.pedido).first()
                    
                    if pedido_verificacao:
                        print(f"[SYNC] 📊 Pedido {pedido_verificacao.num_pedido}:")
                        print(f"[SYNC]    NF: '{pedido_verificacao.nf}'")
                        print(f"[SYNC]    Status: '{pedido_verificacao.status_calculado}'")
                        print(f"[SYNC]    Cotação ID: {pedido_verificacao.cotacao_id}")
        
        # Montar mensagem de resultado
        resultado_parts = []
        if itens_sincronizados > 0:
            resultado_parts.append(f"{itens_sincronizados} NF(s) sincronizada(s)")
        if itens_removidos > 0:
            resultado_parts.append(f"{itens_removidos} NF(s) removida(s)")
        if itens_cancelados > 0:
            resultado_parts.append(f"{itens_cancelados} item(ns) processado(s)")
        
        if is_embarque_fob and itens_sincronizados > 0:
            resultado_parts.append("embarque FOB configurado")
        
        resultado_msg = "✅ " + ", ".join(resultado_parts) if resultado_parts else "Nenhuma alteração necessária"
        
        if erros:
            resultado_msg += f" | ⚠️ {len(erros)} erro(s)"
        
        # Log resumido apenas se houve alterações significativas
        if itens_sincronizados > 0 or itens_removidos > 0 or itens_cancelados > 0:
            print(f"[SYNC] Embarque #{embarque.numero}: {resultado_msg}")
        
        return True, resultado_msg
            
    except Exception as e:
        db.session.rollback()
        error_msg = f"Erro na sincronização: {str(e)}"
        print(f"[SYNC] ❌ {error_msg}")
        return False, error_msg

def atualizar_status_pedido_nf_cd(numero_pedido, separacao_lote_id=None):
    """
    ✅ FUNÇÃO CORRIGIDA: Atualiza status dos itens de separação para "NF no CD"
    
    Implementa o item 2-d do processo_completo.md:
    - Quando uma NF volta para o CD, altera o status dos itens de separação
    - Remove data de embarque e marca nf_cd=True para permitir nova cotação
    - Atualiza diretamente na tabela Separacao (não na VIEW Pedido)
    """
    try:
        # Atualiza diretamente na tabela Separacao
        update_data = {
            'nf_cd': True,
            'data_embarque': None,
            'status': 'NF no CD'
        }
        
        # Constrói a query baseada nos parâmetros disponíveis
        if separacao_lote_id:
            # Atualização por lote completo
            result = Separacao.query.filter_by(
                separacao_lote_id=separacao_lote_id
            ).update(update_data)
            
            identificador = f"Lote: {separacao_lote_id}"
                        
        else:
            return False, "Nenhum parâmetro de busca fornecido"
        
        # Confirma as alterações
        db.session.commit()
        
        # Verifica quantas linhas foram afetadas
        if result > 0:
            msg = f"Status atualizado para 'NF no CD': {result} item(ns) de separação ({identificador})"
            print(f"[DEBUG] 📦 {msg}")
            return True, msg
        else:
            return False, f"Nenhum item de separação encontrado ({identificador})"
            
    except Exception as e:
        db.session.rollback()
        return False, f"Erro ao atualizar pedido: {str(e)}"

@embarques_bp.route('/item/<int:item_id>/cancelar', methods=['POST'])
@login_required
def cancelar_item_embarque(item_id):
    """
    Cancela um item do embarque (exclusão lógica)
    """
    
    item = EmbarqueItem.query.get_or_404(item_id)
    embarque = item.embarque
    
    # Verificar se o embarque não está cancelado
    if embarque.status == 'cancelado':
        flash('❌ Não é possível remover itens de um embarque cancelado.', 'danger')
        return redirect(url_for('embarques.visualizar_embarque', id=embarque.id))
    
    try:
        # Cancelar o item (exclusão lógica)
        item.status = 'cancelado'
        
        # ✅ REVERSÃO SIMPLIFICADA: Como 1 lote = 1 NF = 1 unidade, podemos reverter com segurança
        if item.separacao_lote_id:
            
            # Buscar TODAS as separações do lote (todos os produtos)
            # Não precisa filtrar por num_pedido pois 1 lote = 1 pedido
            separacoes = Separacao.query.filter_by(
                separacao_lote_id=item.separacao_lote_id
            ).all()
            
            campos_revertidos = []
            
            # Para cada linha do lote (cada produto)
            for sep in separacoes:
                mudancas = []
                
                # 1. REVERTER DATA_EMBARQUE se corresponder a este embarque
                if embarque.data_embarque and sep.data_embarque == embarque.data_embarque:
                    sep.data_embarque = None
                    mudancas.append('data_embarque')
                
                # 2. REVERTER COTACAO_ID se corresponder a cotação deste embarque
                # Como o lote inteiro sai do embarque, podemos limpar a cotação
                if embarque.cotacao_id and sep.cotacao_id == embarque.cotacao_id:
                    # Verificar se não há OUTRO embarque ativo com este mesmo lote
                    outro_embarque = EmbarqueItem.query.join(Embarque).filter(
                        EmbarqueItem.separacao_lote_id == item.separacao_lote_id,
                        EmbarqueItem.status == 'ativo',
                        Embarque.status == 'ativo',
                        Embarque.id != embarque.id
                    ).first()
                    
                    if not outro_embarque:
                        # Seguro limpar - este lote não está em outro embarque
                        sep.cotacao_id = None
                        mudancas.append('cotacao_id')
                    else:
                        print(f"[AVISO] Lote {item.separacao_lote_id} está em outro embarque, mantendo cotacao_id")
                
                if mudancas:
                    campos_revertidos.extend(mudancas)
                    print(f"[REVERSÃO] Separação {sep.id} (produto {sep.cod_produto}): {', '.join(mudancas)} limpos")
            
            if campos_revertidos:
                print(f"[RESUMO] Lote {item.separacao_lote_id} removido do embarque #{embarque.numero}")
                print(f"         Total de reversões: {len(set(campos_revertidos))} campos únicos")
                # O status será recalculado automaticamente pelo event listener para todas as linhas
        
        db.session.commit()
        
        # ✅ USAR NOVA SINCRONIZAÇÃO COMPLETA
        sucesso, resultado = sincronizar_nf_embarque_pedido_completa(embarque.id)
        if sucesso:
            flash(f'✅ Pedido {item.pedido} removido do embarque com sucesso! {resultado}', 'success')
        else:
            flash(f'✅ Pedido {item.pedido} removido do embarque, mas houve erro na sincronização: {resultado}', 'warning')
        
    except Exception as e:
        db.session.rollback()
        flash(f'❌ Erro ao remover pedido do embarque: {str(e)}', 'danger')
    
    return redirect(url_for('embarques.visualizar_embarque', id=embarque.id))

@embarques_bp.route('/<int:embarque_id>/alterar_cotacao')
@login_required
@require_embarques()
def alterar_cotacao(embarque_id):
    """
    Permite alterar a cotação de um embarque existente.
    
    Só permite se a data do embarque não estiver preenchida.
    Extrai os pedidos do embarque e redireciona para a tela de cotação.
    """
    try:
        embarque = Embarque.query.get_or_404(embarque_id)
        
        # 🔒 VERIFICAÇÃO ESPECÍFICA PARA VENDEDORES
        if current_user.perfil == 'vendedor':
            # Verifica se o vendedor tem permissão para ver este embarque
            tem_permissao = False
            from app.utils.auth_decorators import check_vendedor_permission
            for item in embarque.itens:
                if check_vendedor_permission(numero_nf=item.nota_fiscal):
                    tem_permissao = True
                    break
            
            if not tem_permissao:
                flash('Acesso negado. Você só pode alterar cotação de embarques dos seus clientes.', 'danger')
                return redirect(url_for('embarques.listar_embarques'))
        
        # Verificar se a data do embarque não está preenchida
        if embarque.data_embarque:
            flash('❌ Não é possível alterar a cotação de um embarque que já foi embarcado (data de embarque preenchida).', 'danger')
            return redirect(url_for('embarques.visualizar_embarque', id=embarque_id))
        
        # Verificar se há itens ativos no embarque
        itens_ativos = [item for item in embarque.itens if item.status == 'ativo']
        if not itens_ativos:
            flash('❌ Este embarque não possui itens ativos para cotar.', 'warning')
            return redirect(url_for('embarques.visualizar_embarque', id=embarque_id))
        
        # Extrair os lotes únicos dos itens do embarque agregando por separacao_lote_id
        from app.separacao.models import Separacao
        from sqlalchemy import func
        
        # Coletar lotes únicos dos itens ativos
        lotes_unicos = set()
        for item in itens_ativos:
            if item.separacao_lote_id:
                lotes_unicos.add(item.separacao_lote_id)
        
        if not lotes_unicos:
            flash('❌ Nenhum lote de separação encontrado nos itens do embarque.', 'danger')
            return redirect(url_for('embarques.visualizar_embarque', id=embarque_id))
        
        # Buscar dados agregados de Separacao por lote
        # Criar estrutura similar à VIEW pedidos mas buscando direto de Separacao
        pedidos_data = []
        
        for lote_id in lotes_unicos:
            # Buscar dados agregados do lote na tabela Separacao
            agregacao = db.session.query(
                Separacao.separacao_lote_id,
                func.min(Separacao.num_pedido).label('num_pedido'),
                func.min(Separacao.data_pedido).label('data_pedido'),
                func.min(Separacao.cnpj_cpf).label('cnpj_cpf'),
                func.min(Separacao.raz_social_red).label('raz_social_red'),
                func.min(Separacao.nome_cidade).label('nome_cidade'),
                func.min(Separacao.cod_uf).label('cod_uf'),
                func.coalesce(func.sum(Separacao.valor_saldo), 0).label('valor_saldo_total'),
                func.coalesce(func.sum(Separacao.pallet), 0).label('pallet_total'),
                func.coalesce(func.sum(Separacao.peso), 0).label('peso_total'),
                func.min(Separacao.rota).label('rota'),
                func.min(Separacao.cidade_normalizada).label('cidade_normalizada'),
                func.min(Separacao.uf_normalizada).label('uf_normalizada'),
                func.min(Separacao.codigo_ibge).label('codigo_ibge'),
                func.min(Separacao.sub_rota).label('sub_rota'),
                func.min(Separacao.expedicao).label('expedicao'),
                func.min(Separacao.agendamento).label('agendamento'),
                func.min(Separacao.protocolo).label('protocolo')
            ).filter(
                Separacao.separacao_lote_id == lote_id
            ).group_by(
                Separacao.separacao_lote_id
            ).first()
            
            if agregacao:
                # Criar um objeto similar ao Pedido para compatibilidade
                pedido_obj = type('PedidoTemp', (), {
                    'id': hash(lote_id) % 1000000,  # ID temporário único baseado no lote
                    'separacao_lote_id': agregacao.separacao_lote_id,
                    'num_pedido': agregacao.num_pedido,
                    'data_pedido': agregacao.data_pedido,
                    'cnpj_cpf': agregacao.cnpj_cpf,
                    'raz_social_red': agregacao.raz_social_red,
                    'nome_cidade': agregacao.nome_cidade,
                    'cod_uf': agregacao.cod_uf,
                    'cidade_normalizada': agregacao.cidade_normalizada,
                    'uf_normalizada': agregacao.uf_normalizada,
                    'codigo_ibge': agregacao.codigo_ibge,
                    'valor_saldo_total': float(agregacao.valor_saldo_total or 0),
                    'pallet_total': float(agregacao.pallet_total or 0),
                    'peso_total': float(agregacao.peso_total or 0),
                    'rota': agregacao.rota,
                    'sub_rota': agregacao.sub_rota,
                    'expedicao': agregacao.expedicao,
                    'agendamento': agregacao.agendamento,
                    'protocolo': agregacao.protocolo
                })()
                pedidos_data.append(pedido_obj)
            else:
                flash(f'⚠️ Lote {lote_id} não encontrado na base de dados.', 'warning')
        
        if not pedidos_data:
            flash('❌ Nenhum dado válido encontrado para alterar a cotação.', 'danger')
            return redirect(url_for('embarques.visualizar_embarque', id=embarque_id))
        
        # Armazenar os dados completos dos pedidos na sessão para uso na cotação
        # Em vez de apenas IDs, vamos armazenar os dados completos serializados
        pedidos_serializados = []
        for p in pedidos_data:
            pedidos_serializados.append({
                'id': p.separacao_lote_id,
                'separacao_lote_id': p.separacao_lote_id,
                'num_pedido': p.num_pedido,
                'data_pedido': p.data_pedido.isoformat() if p.data_pedido else None,
                'cnpj_cpf': p.cnpj_cpf,
                'raz_social_red': p.raz_social_red,
                'nome_cidade': p.nome_cidade,
                'cod_uf': p.cod_uf,
                'cidade_normalizada': p.cidade_normalizada,
                'uf_normalizada': p.uf_normalizada,
                'codigo_ibge': p.codigo_ibge,
                'valor_saldo_total': p.valor_saldo_total,
                'pallet_total': p.pallet_total,
                'peso_total': p.peso_total,
                'rota': p.rota,
                'sub_rota': p.sub_rota,
                'expedicao': p.expedicao.isoformat() if p.expedicao else None,
                'agendamento': p.agendamento.isoformat() if p.agendamento else None,
                'protocolo': p.protocolo
            })
        
        # Armazenar informações na sessão
        session['cotacao_pedidos_data'] = pedidos_serializados  # Dados completos
        session['cotacao_pedidos'] = [p['id'] for p in pedidos_serializados]  # IDs para compatibilidade
        session['alterando_embarque'] = {
            'embarque_id': embarque_id,
            'numero_embarque': embarque.numero,
            'transportadora_anterior': embarque.transportadora.razao_social if embarque.transportadora else None,
            'tipo_carga_anterior': embarque.tipo_carga
        }
        
        flash(f'🔄 Iniciando alteração da cotação do embarque #{embarque.numero}. {len(pedidos_serializados)} pedido(s) selecionado(s).', 'info')
        
        # Redirecionar para a tela de cotação com parâmetro indicando alteração
        return redirect(url_for('cotacao.tela_cotacao', alterando_embarque=embarque_id))
        
    except Exception as e:
        flash(f'❌ Erro ao iniciar alteração de cotação: {str(e)}', 'danger')
        return redirect(url_for('embarques.listar_embarques'))

@embarques_bp.route('/admin/desvincular-pedido/<string:lote_id>', methods=['POST'])
@login_required
def desvincular_pedido(lote_id):
    """
    Desvincula um pedido de embarques cancelados.
    Remove vínculos órfãos (cotação, NF, data embarque) de pedidos que estão
    vinculados a embarques cancelados, permitindo que voltem ao status ABERTO.
    
    Apenas para administradores.
    """
    # Verifica se o usuário é administrador
    if not hasattr(current_user, 'perfil') or current_user.perfil != 'administrador':
        flash("Acesso negado. Esta função é restrita a administradores.", "error")
        return redirect(url_for('pedidos.lista_pedidos'))
    
    try:
        # Busca separações do lote
        separacoes = Separacao.query.filter_by(separacao_lote_id=lote_id).all()
        
        if not separacoes:
            flash(f"Pedido com lote {lote_id} não encontrado.", "error")
            return redirect(url_for('pedidos.lista_pedidos'))
        
        primeira_separacao = separacoes[0]
        num_pedido = primeira_separacao.num_pedido
        
        # Verifica se há embarque relacionado
        embarque_relacionado = None
        embarque_cancelado = False
        
        if lote_id:
            item_embarque = EmbarqueItem.query.filter_by(separacao_lote_id=lote_id).first()
            if item_embarque:
                embarque_relacionado = Embarque.query.get(item_embarque.embarque_id)
                if embarque_relacionado:
                    embarque_cancelado = embarque_relacionado.status == 'cancelado'
        
        # Se não há embarque ou o embarque não está cancelado, verifica se pode desvincular mesmo assim
        if not embarque_cancelado:
            # Permite desvinculação se o pedido tem vínculos mas está em status que permite
            status_atual = primeira_separacao.status_calculado
            if status_atual not in ['ABERTO', 'COTADO', 'EMBARCADO']:
                flash(f"Pedido {num_pedido} não pode ser desvinculado. Status: {status_atual}", "warning")
                return redirect(url_for('pedidos.lista_pedidos'))
        
        # Realiza a desvinculação
        vinculos_removidos = []
        
        # Remove vínculos de todas as separações do lote
        update_data = {}
        
        if primeira_separacao.cotacao_id:
            update_data['cotacao_id'] = None
            vinculos_removidos.append("cotação")
            
        if primeira_separacao.numero_nf:
            update_data['numero_nf'] = None
            update_data['sincronizado_nf'] = False
            vinculos_removidos.append("nota fiscal")
            
        if primeira_separacao.data_embarque:
            update_data['data_embarque'] = None
            vinculos_removidos.append("data de embarque")
            
        if primeira_separacao.nf_cd:
            update_data['nf_cd'] = False
            vinculos_removidos.append("flag NF no CD")
        
        # Atualiza status para ABERTO
        update_data['status'] = 'ABERTO'
        
        if update_data:
            Separacao.query.filter_by(
                separacao_lote_id=lote_id
            ).update(update_data)
            
            # Remove item de embarque se existir e o embarque estiver cancelado
            if embarque_cancelado and item_embarque:
                db.session.delete(item_embarque)
                vinculos_removidos.append(f"item do embarque #{embarque_relacionado.numero}")
            
            db.session.commit()
            
            # Mensagem de sucesso
            if vinculos_removidos:
                vinculos_texto = ", ".join(vinculos_removidos)
                flash(f"✅ Pedido {num_pedido} desvinculado com sucesso! Removidos: {vinculos_texto}", "success")
            else:
                flash(f"✅ Pedido {num_pedido} já estava sem vínculos órfãos.", "info")
                
            # Log da operação
            print(f"[DESVINCULAR] Pedido {num_pedido}:")
            print(f"  - Lote: {lote_id}")
            print(f"  - Embarque cancelado: {'Sim' if embarque_cancelado else 'Não'}")
            print(f"  - Vínculos removidos: {vinculos_removidos}")
        else:
            flash(f"Pedido {num_pedido} não possui vínculos para remover.", "info")
            
    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao desvincular pedido: {str(e)}", "error")
        print(f"[ERRO DESVINCULAR] {str(e)}")
    
    return redirect(url_for('pedidos.lista_pedidos'))


@embarques_bp.route('/item/<int:item_id>/confirmar_agendamento', methods=['POST'])
@login_required
def confirmar_agendamento_item(item_id):
    """
    Confirma/atualiza agendamento de um EmbarqueItem

    Payload:
    {
        "data_agenda": "DD/MM/AAAA",
        "agendamento_confirmado": true/false
    }

    Response:
    {
        "success": true,
        "message": "...",
        "item_id": 123,
        "data_agenda": "01/01/2025",
        "agendamento_confirmado": true
    }
    """
    try:
        # Buscar EmbarqueItem
        item = EmbarqueItem.query.get_or_404(item_id)

        # Obter dados do payload
        data = request.get_json()
        data_agenda = data.get('data_agenda', '').strip()
        agendamento_confirmado = data.get('agendamento_confirmado', False)

        # Validar data
        if not data_agenda:
            return jsonify({
                'success': False,
                'message': 'Data de agendamento é obrigatória'
            }), 400

        # Atualizar EmbarqueItem
        item.data_agenda = data_agenda
        item.agendamento_confirmado = agendamento_confirmado

        # ✅ SINCRONIZAÇÃO: Propagar para outras tabelas
        from app.pedidos.services.sincronizacao_agendamento_service import SincronizadorAgendamentoService

        try:
            sincronizador = SincronizadorAgendamentoService(
                usuario=current_user.nome if hasattr(current_user, 'nome') else 'Sistema'
            )

            # Converter data_agenda (String DD/MM/YYYY) para Date
            data_agendamento_obj = None
            if data_agenda:
                try:
                    data_agendamento_obj = datetime.strptime(data_agenda, '%d/%m/%Y').date()
                except Exception as e:
                    print(f"[CONFIRMAÇÃO AGENDAMENTO] Erro ao converter data: {e}")
                    pass

            dados_agendamento = {
                'agendamento': data_agendamento_obj,
                'protocolo': item.protocolo_agendamento,
                'agendamento_confirmado': agendamento_confirmado,
                'numero_nf': item.nota_fiscal
            }

            identificador = {
                'separacao_lote_id': item.separacao_lote_id,
                'numero_nf': item.nota_fiscal
            }

            resultado = sincronizador.sincronizar_agendamento(dados_agendamento, identificador)

            if resultado['success']:
                print(f"[CONFIRMAÇÃO AGENDAMENTO] Item {item_id}: {', '.join(resultado['tabelas_atualizadas'])}")
            else:
                print(f"[CONFIRMAÇÃO AGENDAMENTO] Erro na sincronização: {resultado['error']}")

        except Exception as e:
            print(f"[CONFIRMAÇÃO AGENDAMENTO] Erro ao sincronizar: {e}")
            # Não falhar a atualização se sincronização der erro

        # Salvar alterações
        db.session.commit()

        print(f"[CONFIRMAÇÃO AGENDAMENTO] Item {item_id} atualizado: data={data_agenda}, confirmado={agendamento_confirmado}")

        return jsonify({
            'success': True,
            'message': 'Agendamento atualizado com sucesso',
            'item_id': item_id,
            'data_agenda': data_agenda,
            'agendamento_confirmado': agendamento_confirmado
        })

    except Exception as e:
        db.session.rollback()
        print(f"[ERRO CONFIRMAÇÃO AGENDAMENTO] {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Erro ao atualizar agendamento: {str(e)}'
        }), 500


@embarques_bp.route('/item/<int:item_id>/sincronizar_faturamento', methods=['POST'])
@login_required
def sincronizar_item_faturamento(item_id):
    """
    Sincroniza valor e peso de um EmbarqueItem com o total da NF em FaturamentoProduto

    Busca todos os produtos da NF e soma:
    - valor_produto_faturado (para atualizar item.valor)
    - peso_total (para atualizar item.peso)

    Response:
    {
        "success": true,
        "message": "...",
        "valor_anterior": 1000.00,
        "valor_novo": 1050.00,
        "peso_anterior": 500.0,
        "peso_novo": 520.5
    }
    """
    try:
        # Buscar EmbarqueItem
        item = EmbarqueItem.query.get_or_404(item_id)

        # Validar se tem NF
        if not item.nota_fiscal or item.nota_fiscal.strip() == '':
            return jsonify({
                'success': False,
                'message': 'Item não possui Nota Fiscal para sincronizar'
            }), 400

        # Buscar produtos da NF em FaturamentoProduto
        from app.faturamento.models import FaturamentoProduto

        produtos_nf = FaturamentoProduto.query.filter_by(
            numero_nf=item.nota_fiscal
        ).all()

        if not produtos_nf:
            return jsonify({
                'success': False,
                'message': f'NF {item.nota_fiscal} não encontrada em FaturamentoProduto. Importação pendente?'
            }), 404

        # Calcular totais da NF
        valor_nf_total = sum(float(p.valor_produto_faturado or 0) for p in produtos_nf)
        peso_nf_total = sum(float(p.peso_total or 0) for p in produtos_nf)

        # Guardar valores anteriores
        valor_anterior = float(item.valor or 0)
        peso_anterior = float(item.peso or 0)

        # Atualizar EmbarqueItem
        item.valor = valor_nf_total
        item.peso = peso_nf_total

        db.session.commit()

        print(f"[SINCRONIZAÇÃO FATURAMENTO] Item {item_id} | NF {item.nota_fiscal} | Valor: {valor_anterior} → {valor_nf_total} | Peso: {peso_anterior} → {peso_nf_total}")

        return jsonify({
            'success': True,
            'message': f'Sincronizado com sucesso! NF: {item.nota_fiscal}',
            'numero_nf': item.nota_fiscal,
            'qtd_produtos_nf': len(produtos_nf),
            'valor_anterior': round(valor_anterior, 2),
            'valor_novo': round(valor_nf_total, 2),
            'peso_anterior': round(peso_anterior, 2),
            'peso_novo': round(peso_nf_total, 2)
        })

    except Exception as e:
        db.session.rollback()
        print(f"[ERRO SINCRONIZAÇÃO FATURAMENTO] {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Erro ao sincronizar: {str(e)}'
        }), 500


@embarques_bp.route('/api/gerar-pdf-protocolo-atacadao/<int:item_id>', methods=['POST'])
@login_required
def gerar_pdf_protocolo_atacadao_route(item_id):
    """
    API para gerar PDF do protocolo do Atacadão via Playwright (headless)

    Fluxo:
    1. Verifica se é Atacadão
    2. Abre navegador headless com Playwright
    3. Clica em "Imprimir Senha" e abre modal
    4. Captura modal como PDF
    5. Salva PDF em /tmp e retorna caminho para download
    """
    try:
        from app.portal.utils.grupo_empresarial import GrupoEmpresarial
        from app.portal.atacadao.impressao_protocolo import gerar_pdf_protocolo_atacadao
        import logging

        logger = logging.getLogger(__name__)

        # Buscar EmbarqueItem
        item = EmbarqueItem.query.get_or_404(item_id)

        # Verificar se tem protocolo
        if not item.protocolo_agendamento:
            return jsonify({
                'success': False,
                'message': 'Item sem protocolo de agendamento'
            })

        # Verificar se tem CNPJ
        if not item.cnpj_cliente:
            return jsonify({
                'success': False,
                'message': 'Item sem CNPJ associado'
            })

        # Verificar se é Atacadão
        eh_atacadao = GrupoEmpresarial.eh_cliente_atacadao(item.cnpj_cliente)

        if not eh_atacadao:
            return jsonify({
                'success': False,
                'message': 'Cliente não é Atacadão'
            })

        # Gerar PDF via Playwright (headless)
        logger.info(f"Gerando PDF do protocolo {item.protocolo_agendamento} via Playwright")

        resultado = gerar_pdf_protocolo_atacadao(item.protocolo_agendamento)

        return jsonify(resultado)

    except Exception as e:
        logger.error(f"Erro ao gerar PDF: {e}")
        return jsonify({
            'success': False,
            'message': f'Erro ao processar PDF: {str(e)}'
        }), 500


@embarques_bp.route('/api/download-pdf-protocolo/<protocolo>/<filename>', methods=['GET'])
@login_required
def download_pdf_protocolo(protocolo, filename):
    """
    Endpoint para download do PDF gerado

    Args:
        protocolo: Número do protocolo
        filename: Nome do arquivo PDF
    """
    try:
        from flask import send_file
        from pathlib import Path

        # Validar filename para segurança
        if not filename.startswith(f'protocolo_{protocolo}_') or not filename.endswith('.pdf'):
            return jsonify({
                'success': False,
                'message': 'Nome de arquivo inválido'
            }), 400

        # Caminho do PDF
        pdf_path = Path(f"/tmp/protocolos_atacadao/{filename}")

        if not pdf_path.exists():
            return jsonify({
                'success': False,
                'message': 'PDF não encontrado. Talvez tenha expirado.'
            }), 404

        # Retornar arquivo para download
        return send_file(
            pdf_path,
            as_attachment=False,  # Abre no navegador ao invés de baixar
            download_name=filename,
            mimetype='application/pdf'
        )

    except Exception as e:
        logger.error(f"Erro ao fazer download do PDF: {e}")
        return jsonify({
            'success': False,
            'message': f'Erro ao baixar PDF: {str(e)}'
        }), 500

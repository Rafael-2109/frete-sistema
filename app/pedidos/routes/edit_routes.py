"""Routes de edicao, reset, cancelamento e exclusao de pedidos."""
from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user

from app import db
from app.pedidos.models import Pedido
from app.pedidos.forms import EditarPedidoForm
from app.separacao.models import Separacao
from app.carteira.models import CarteiraPrincipal
from app.embarques.models import Embarque, EmbarqueItem
from app.cadastros_agendamento.models import ContatoAgendamento

def register_edit_routes(bp):

    @bp.route('/editar/<string:lote_id>', methods=['GET', 'POST']) # type: ignore
    @login_required
    def editar_pedido(lote_id): # type: ignore
        """
        Edita campos específicos de um pedido (agenda, protocolo, expedição)
        e sincroniza as alterações com a separação relacionada.
        Suporta Nacom (Separacao) e CarVia (CarviaCotacao).
        """
        # ===== CarVia: rota polimórfica =====
        if str(lote_id).startswith('CARVIA-'):
            return _editar_pedido_carvia(lote_id)

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

                # ✅ Invalidar cache de contadores (expedição pode ter mudado)
                from app.pedidos.services.counter_service import PedidosCounterService
                PedidosCounterService.invalidar_cache()

                # ✅ LOG das alterações
                print(f"[EDIT] Pedido {pedido.num_pedido} editado:")
                print(f"  - Expedição: {valores_originais['expedicao']} → {form.expedicao.data}")
                print(f"  - Agendamento: {valores_originais['agendamento']} → {form.agendamento.data}")
                print(f"  - Protocolo: {valores_originais['protocolo']} → {form.protocolo.data}")
                print(f"  - Agendamento Confirmado: {valores_originais['agendamento_confirmado']} → {form.agendamento_confirmado.data}")
                print(f"  - Separações atualizadas: {separacoes_atualizadas}")

                # ✅ SINCRONIZAR AGENDAMENTO ENTRE TODAS AS TABELAS (EmbarqueItem, EntregaMonitorada, AgendamentoEntrega)
                # IMPORTANTE: Esta sincronização DEVE ocorrer ANTES do return para garantir que seja executada
                from app.pedidos.services.sincronizacao_agendamento_service import SincronizadorAgendamentoService

                tabelas_sincronizadas = []
                erro_sincronizacao = None

                try:
                    sincronizador = SincronizadorAgendamentoService(usuario=current_user.nome if hasattr(current_user, 'nome') else 'Sistema')

                    # Executar sincronização usando o método que busca dados da Separacao já commitada
                    if pedido.separacao_lote_id:
                        resultado_sync = sincronizador.sincronizar_desde_separacao(
                            separacao_lote_id=pedido.separacao_lote_id,
                            criar_agendamento=True
                        )

                        if resultado_sync['success']:
                            tabelas_sincronizadas = resultado_sync.get('tabelas_atualizadas', [])
                            print(f"[SINCRONIZAÇÃO] Tabelas atualizadas: {', '.join(tabelas_sincronizadas)}")
                        else:
                            erro_sincronizacao = resultado_sync.get('error', 'Erro desconhecido')
                            print(f"[SINCRONIZAÇÃO] Erro: {erro_sincronizacao}")

                except Exception as e:
                    erro_sincronizacao = str(e)
                    print(f"[SINCRONIZAÇÃO] Erro ao sincronizar: {e}")
                    # Não falhar a edição se sincronização der erro

                # ✅ RESPOSTA PARA AJAX (APÓS sincronização)
                if request.args.get('ajax') or request.is_json:
                    response_data = {
                        'success': True,
                        'message': f"Pedido {pedido.num_pedido} atualizado com sucesso! {separacoes_atualizadas} item(ns) de separação também foram atualizados."
                    }
                    if tabelas_sincronizadas:
                        response_data['tabelas_sincronizadas'] = tabelas_sincronizadas
                        response_data['message'] += f" Sincronizado: {', '.join(tabelas_sincronizadas)}."
                    if erro_sincronizacao:
                        response_data['aviso_sincronizacao'] = erro_sincronizacao
                    return jsonify(response_data)

                # ✅ MENSAGEM DE SUCESSO com detalhes (para requisições não-AJAX)
                flash(f"Pedido {pedido.num_pedido} atualizado com sucesso! {separacoes_atualizadas} item(ns) de separação também foram atualizados.", "success")
                if tabelas_sincronizadas:
                    flash(f"Sincronização completa: {', '.join(tabelas_sincronizadas)}", "info")
                if erro_sincronizacao:
                    flash(f"Aviso: Erro na sincronização - {erro_sincronizacao}", "warning")

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
            return render_template('pedidos/editar_pedido_ajax.html', form=form, pedido=pedido, separacao=separacao_exemplo, contato_agendamento=contato_agendamento, eh_carvia=False)

        return render_template('pedidos/editar_pedido.html', form=form, pedido=pedido, separacao=separacao_exemplo, contato_agendamento=contato_agendamento, eh_carvia=False)


    @bp.route('/reset_status/<string:lote_id>', methods=['POST']) # type: ignore
    @login_required
    def reset_status_pedido(lote_id): # type: ignore
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


    @bp.route('/cancelar_separacao/<string:lote_id>', methods=['POST']) # type: ignore
    @login_required
    def cancelar_separacao(lote_id): # type: ignore
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


    @bp.route('/excluir/<string:lote_id>', methods=['POST']) # type: ignore
    @login_required
    def excluir_pedido(lote_id): # type: ignore
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
                        embarque_relacionado = db.session.get(Embarque,item_embarque.embarque_id) if item_embarque.embarque_id else None
            
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

    def _editar_pedido_carvia(lote_id):
        """Editar datas (expedição/agenda) de cotação CarVia."""
        from app.carvia.models import CarviaCotacao, CarviaPedido
        from datetime import date

        # Resolver cotação
        if str(lote_id).startswith('CARVIA-PED-'):
            ped_id = int(str(lote_id).replace('CARVIA-PED-', ''))
            pedido_cv = db.session.get(CarviaPedido, ped_id)
            if not pedido_cv:
                if request.args.get('ajax'):
                    return jsonify({'success': False, 'message': 'Pedido CarVia não encontrado'}), 404
                flash('Pedido CarVia não encontrado', 'error')
                return redirect(url_for('pedidos.lista_pedidos'))
            cot = pedido_cv.cotacao
        else:
            cot_id = int(str(lote_id).replace('CARVIA-', ''))
            cot = db.session.get(CarviaCotacao, cot_id)

        if not cot:
            if request.args.get('ajax'):
                return jsonify({'success': False, 'message': 'Cotação CarVia não encontrada'}), 404
            flash('Cotação CarVia não encontrada', 'error')
            return redirect(url_for('pedidos.lista_pedidos'))

        # Buscar pedido da VIEW para exibição
        pedido = Pedido.query.filter_by(separacao_lote_id=lote_id).first()

        if request.method == 'POST':
            try:
                if request.is_json:
                    data = request.get_json()
                else:
                    data = request.form

                # Atualizar datas na cotação CarVia
                expedicao_str = data.get('expedicao', '')
                agendamento_str = data.get('agendamento', '')
                agendamento_confirmado = data.get('agendamento_confirmado')

                if expedicao_str:
                    cot.data_expedicao = date.fromisoformat(expedicao_str)
                else:
                    cot.data_expedicao = None

                if agendamento_str:
                    cot.data_agenda = date.fromisoformat(agendamento_str)
                else:
                    cot.data_agenda = None

                if agendamento_confirmado is not None:
                    cot.agendamento_confirmado = agendamento_confirmado in (True, 'True', 'true', 'on', '1', 'y')

                db.session.commit()

                if request.args.get('ajax') or request.is_json:
                    return jsonify({
                        'success': True,
                        'message': f'Cotação CarVia {cot.numero_cotacao} atualizada com sucesso!'
                    })

                flash(f'Cotação CarVia {cot.numero_cotacao} atualizada com sucesso!', 'success')
                return redirect(url_for('pedidos.lista_pedidos'))

            except Exception as e:
                db.session.rollback()
                if request.args.get('ajax') or request.is_json:
                    return jsonify({'success': False, 'message': f'Erro: {str(e)}'})
                flash(f'Erro ao atualizar: {str(e)}', 'error')

        # GET: preencher form com dados atuais
        form = EditarPedidoForm()
        form.expedicao.data = cot.data_expedicao
        form.agendamento.data = cot.data_agenda
        form.protocolo.data = None
        form.agendamento_confirmado.data = cot.agendamento_confirmado

        if request.args.get('ajax'):
            return render_template(
                'pedidos/editar_pedido_ajax.html',
                form=form,
                pedido=pedido,
                separacao=None,
                contato_agendamento=None,
                eh_carvia=True
            )

        return render_template(
            'pedidos/editar_pedido.html',
            form=form,
            pedido=pedido,
            separacao=None,
            contato_agendamento=None,
            eh_carvia=True
        )

    # Função gerar_lote_id movida para app.utils.lote_utils para padronização

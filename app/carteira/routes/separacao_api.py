"""
API para gerar separação de pedidos completos na carteira agrupada
Versão unificada com suporte a parciais HTML e JSON
MIGRADO: PreSeparacaoItem → Separacao (status='ABERTO')
"""
from flask import jsonify, request, render_template
from flask_login import login_required, current_user
from datetime import datetime
from app import db
from app.carteira.models import CarteiraPrincipal
from app.separacao.models import Separacao
from app.utils.timezone import agora_brasil
from app.carteira.utils.separacao_utils import (
    calcular_peso_pallet_produto,
    buscar_rota_por_uf,
    buscar_sub_rota_por_uf_cidade,
)
from app.utils.lote_utils import gerar_lote_id as gerar_novo_lote_id  # Função padronizada
import logging

from . import carteira_bp

logger = logging.getLogger(__name__)


@carteira_bp.route("/api/pedido/<num_pedido>/gerar-separacao-completa", methods=["POST"])
@login_required
def gerar_separacao_completa_pedido(num_pedido):
    """
    API para gerar separação de TODOS os produtos do pedido

    Usado pelo botão "Gerar Separação" na carteira agrupada
    Aplica mesma data de expedição, agendamento e protocolo para todos os produtos

    Payload esperado:
    {
        "expedicao": "2025-01-25",
        "agendamento": "2025-01-26", // opcional
        "protocolo": "PROT123" // opcional
    }
    """
    try:
        # PROTEÇÃO CONTRA RACE CONDITION: Dupla verificação com lock
        from sqlalchemy import text
        
        # LOCK no nível do pedido primeiro (advisory lock do PostgreSQL)
        # Isso garante que apenas uma transação processe este pedido por vez
        lock_query = text("SELECT pg_advisory_xact_lock(:lock_id)")
        lock_id = hash(f"pedido_{num_pedido}") % 2147483647  # Converter para int positivo
        db.session.execute(lock_query, {"lock_id": lock_id})
        
        # Verificar se já existe separação para este pedido
        separacao_existente = Separacao.query.filter(
            Separacao.num_pedido == num_pedido,
            Separacao.sincronizado_nf == False
        ).first()
        
        if separacao_existente:
            logger.warning(f"Pedido {num_pedido} já possui separação com lote {separacao_existente.separacao_lote_id}")
            return jsonify({
                "success": False,
                "error": "Este pedido já possui separação gerada",
                "lote_existente": separacao_existente.separacao_lote_id
            }), 400

        # Obter dados do request
        data = request.get_json()
        data_expedicao = data.get("expedicao")
        data_agendamento = data.get("agendamento")
        protocolo = data.get("protocolo")
        agendamento_confirmado = data.get("agendamento_confirmado", False)

        if not data_expedicao:
            return jsonify({"success": False, "error": "Data de expedição é obrigatória"}), 400

        # Converter datas
        try:
            data_expedicao_obj = datetime.strptime(data_expedicao, "%Y-%m-%d").date()
            data_agendamento_obj = None
            if data_agendamento:
                data_agendamento_obj = datetime.strptime(data_agendamento, "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"success": False, "error": "Formato de data inválido"}), 400

        # Buscar todos os produtos ativos do pedido na carteira COM SALDO > 0
        # IMPORTANTE: Filtrar qtd_saldo_produto_pedido >= 0.001 para evitar processar itens já faturados
        itens_carteira = CarteiraPrincipal.query.filter(
            CarteiraPrincipal.num_pedido == num_pedido,
            CarteiraPrincipal.ativo == True,
            CarteiraPrincipal.qtd_saldo_produto_pedido >= 0.001  # Evita floats zerados
        ).all()

        if not itens_carteira:
            return jsonify({"success": False, "error": "Nenhum produto com saldo disponível encontrado para este pedido"}), 404

        # Gerar ID único para o lote
        separacao_lote_id = gerar_novo_lote_id()

        # Criar separações para cada produto
        separacoes_criadas = []
        valor_total = 0
        peso_total = 0
        pallet_total = 0

        for item in itens_carteira:
            # Usar qtd_saldo_produto_pedido como quantidade
            quantidade = float(item.qtd_saldo_produto_pedido)

            # Calcular valores
            valor_unitario = float(item.preco_produto_pedido or 0)
            valor_separacao = quantidade * valor_unitario

            # Calcular peso e pallet usando a função utilitária
            peso_calculado, pallet_calculado = calcular_peso_pallet_produto(item.cod_produto, quantidade)

            # Calcular rota e sub-rota
            # Se incoterm for RED ou FOB, usar ele como rota
            if item.incoterm in ["RED", "FOB"]:
                rota_calculada = item.incoterm
            else:
                rota_calculada = buscar_rota_por_uf(item.cod_uf or "SP")
            sub_rota_calculada = buscar_sub_rota_por_uf_cidade(item.cod_uf or "", item.nome_cidade or "")

            # Criar separação com status ABERTO (separação completa vai direto)
            separacao = Separacao(
                separacao_lote_id=separacao_lote_id,
                num_pedido=num_pedido,
                data_pedido=item.data_pedido,
                cnpj_cpf=item.cnpj_cpf,
                raz_social_red=item.raz_social_red,
                nome_cidade=item.nome_cidade,
                cod_uf=item.cod_uf,
                cod_produto=item.cod_produto,
                nome_produto=item.nome_produto,
                qtd_saldo=quantidade,
                valor_saldo=valor_separacao,
                peso=peso_calculado,
                pallet=pallet_calculado,
                rota=rota_calculada,
                sub_rota=sub_rota_calculada,
                observ_ped_1=item.observ_ped_1,
                roteirizacao=None,  # Será preenchido depois
                expedicao=data_expedicao_obj,
                agendamento=data_agendamento_obj,
                protocolo=protocolo,
                agendamento_confirmado=agendamento_confirmado,
                pedido_cliente=item.pedido_cliente,
                tipo_envio="total",  # SEMPRE total quando vem de gerar_separacao_completa
                status='ABERTO',  # CORRIGIDO: Cria como ABERTO primeiro
                sincronizado_nf=False,  # IMPORTANTE: Sempre criar com False (não NULL)
                # vendedor=item.vendedor,  # REMOVIDO: campo não existe em Separacao
                criado_em=agora_brasil(),
            )

            db.session.add(separacao)
            separacoes_criadas.append(separacao)

            # Acumular totais
            valor_total += valor_separacao
            peso_total += peso_calculado
            pallet_total += pallet_calculado

        # IMPORTANTE: Após migração para VIEW, Pedido é gerado automaticamente
        # A VIEW agrega as Separacoes com mesmo separacao_lote_id
        
        # Log para debug
        logger.info(f"✅ {len(separacoes_criadas)} separações criadas para pedido {num_pedido} com lote {separacao_lote_id}")

        # Commit das mudanças
        db.session.commit()

        # Verificar se cliente quer resposta com parciais HTML
        accept_html = request.headers.get('Accept', '').find('text/html') != -1 or request.args.get('format') == 'html'
        
        if accept_html:
            # Retornar parciais HTML
            pedido_atualizado = _get_pedido_completo(num_pedido)
            contadores = _calcular_contadores_globais()
            
            return jsonify({
                "ok": True,
                "success": True,
                "message": f"Separação gerada com sucesso! {len(separacoes_criadas)} produtos processados.",
                "targets": {
                    f"#resumo-{num_pedido}": render_template('carteira/partials/_resumo_pedido.html', 
                                                            pedido=pedido_atualizado),
                    f"#separacoes-{num_pedido}": render_template('carteira/partials/_separacoes_pedido.html', 
                                                                pedido=pedido_atualizado),
                    f"#botoes-{num_pedido}": render_template('carteira/partials/_botoes_pedido.html', 
                                                            pedido=pedido_atualizado)
                },
                "contadores": contadores,
                "lote_id": separacao_lote_id,
                "total_produtos": len(separacoes_criadas),
                "valor_total": valor_total,
                "peso_total": peso_total,
                "pallet_total": pallet_total,
                "status_criado": "ABERTO",  # Indicar que foi criado como ABERTO
                "pode_enviar_separacao": True  # Flag para frontend mostrar checkbox
            })
        else:
            # Resposta JSON padrão
            return jsonify({
                "success": True,
                "message": f"Separação gerada com sucesso para o pedido {num_pedido}",
                "lote_id": separacao_lote_id,
                "total_produtos": len(separacoes_criadas),
                "valor_total": valor_total,
                "peso_total": peso_total,
                "pallet_total": pallet_total,
                "status_criado": "ABERTO",  # Indicar que foi criado como ABERTO
                "pode_enviar_separacao": True  # Flag para frontend mostrar checkbox
            })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao gerar separação completa do pedido {num_pedido}: {e}")
        return jsonify({"success": False, "error": f"Erro interno: {str(e)}"}), 500




# Funções auxiliares para buscar dados
def _buscar_pre_separacoes(num_pedido):
    """Busca pré-separações agrupadas por lote"""
    # MIGRADO: Buscar Separacao com status='PREVISAO'
    pre_separacoes_raw = Separacao.query.filter_by(
        num_pedido=num_pedido,
        status='PREVISAO'  # MIGRADO: Status único para pré-separação
    ).all()
    
    # Agrupar por lote
    pre_separacoes = {}
    for item in pre_separacoes_raw:
        lote_id = item.separacao_lote_id or 'sem_lote'
        if lote_id not in pre_separacoes:
            pre_separacoes[lote_id] = []
        pre_separacoes[lote_id].append({
            'cod_produto': item.cod_produto,
            'nome_produto': item.nome_produto,
            'quantidade': float(item.qtd_saldo),  # MIGRADO: qtd_selecionada_usuario → qtd_saldo
            'valor': float(item.valor_saldo or 0),  # MIGRADO: valor_original_item → valor_saldo
            'data_expedicao': item.expedicao.strftime('%d/%m/%Y') if item.expedicao else None,  # MIGRADO
            'tipo_envio': item.tipo_envio or 'total'
        })
    
    return pre_separacoes


def _calcular_contadores_globais():
    """Calcula contadores globais para o dashboard"""
    from app.pedidos.models import Pedido
    
    total_separacoes = Separacao.query.count()
    total_pre_separacoes = Separacao.query.filter_by(status='PREVISAO').count()  # MIGRADO
    # Usar status COMPLETO ao invés de SEPARADO para consistência
    pedidos_completos = db.session.query(Pedido).filter_by(status='COMPLETO').count()
    
    return {
        'total_separacoes': total_separacoes,
        'total_pre_separacoes': total_pre_separacoes,
        'pedidos_completos': pedidos_completos
    }


def _get_pedido_completo(num_pedido):
    """Busca dados completos do pedido incluindo separações e pré-separações"""
    from app.pedidos.models import Pedido
    
    # Buscar pedido
    pedido = Pedido.query.filter_by(num_pedido=num_pedido).first()
    
    if pedido:
        # Adicionar separações relacionadas
        pedido.separacoes = Separacao.query.filter_by(
            num_pedido=num_pedido,
            status='ABERTO'  # Apenas separações confirmadas
        ).all()
        
        # Adicionar pré-separações
        pedido.pre_separacoes = _buscar_pre_separacoes(num_pedido)
    
    return pedido


# =============================================================================
# APIs GENÉRICAS PARA SEPARAÇÃO (drag & drop, edição individual)
# =============================================================================

@carteira_bp.route("/api/separacao/salvar", methods=["POST"])
@login_required
def salvar_separacao_generic():
    """
    API genérica para salvar separação (drag & drop individual)
    Cria ou atualiza uma linha de Separacao
    Por padrão cria com status='ABERTO'
    """
    try:
        data = request.get_json()
        num_pedido = data.get("num_pedido")
        cod_produto = data.get("cod_produto")
        separacao_lote_id = data.get("lote_id") or data.get("separacao_lote_id")
        qtd_selecionada = data.get("qtd_selecionada_usuario") or data.get("qtd_saldo")
        data_expedicao = data.get("data_expedicao_editada") or data.get("expedicao")
        status = data.get("status", "ABERTO")  # Por padrão cria como ABERTO

        # Se não foi fornecido separacao_lote_id, gerar um novo
        if not separacao_lote_id:
            separacao_lote_id = gerar_novo_lote_id()

        if not all([num_pedido, cod_produto, qtd_selecionada, data_expedicao]):
            return jsonify({
                "success": False,
                "error": "Dados obrigatórios: num_pedido, cod_produto, quantidade, data_expedicao"
            }), 400

        # Buscar item da carteira para dados base
        item_carteira = CarteiraPrincipal.query.filter(
            CarteiraPrincipal.num_pedido == num_pedido,
            CarteiraPrincipal.cod_produto == cod_produto,
            CarteiraPrincipal.ativo == True
        ).first()

        if not item_carteira:
            return jsonify({
                "success": False,
                "error": f"Item não encontrado: {num_pedido} - {cod_produto}"
            }), 404

        # Converter data
        if isinstance(data_expedicao, str):
            data_expedicao_obj = datetime.strptime(data_expedicao, "%Y-%m-%d").date()
        else:
            data_expedicao_obj = data_expedicao

        # Verificar se já existe separação para este produto no mesmo lote
        separacao_existente = Separacao.query.filter(
            Separacao.num_pedido == num_pedido,
            Separacao.cod_produto == cod_produto,
            Separacao.separacao_lote_id == separacao_lote_id
        ).first()

        if separacao_existente:
            # Verificar se está sincronizada
            if separacao_existente.sincronizado_nf:
                return jsonify({
                    "success": False,
                    "error": "Não é possível alterar uma separação já sincronizada com NF"
                }), 400
            
            # Atualizar quantidade existente (somar)
            nova_quantidade = float(separacao_existente.qtd_saldo or 0) + float(qtd_selecionada)
            
            # Verificar se não excede o saldo disponível
            if nova_quantidade > float(item_carteira.qtd_saldo_produto_pedido):
                return jsonify({
                    "success": False,
                    "error": f"Quantidade total ({nova_quantidade}) excede o saldo disponível ({item_carteira.qtd_saldo_produto_pedido})"
                }), 400
            
            separacao_existente.qtd_saldo = nova_quantidade
            separacao_existente.expedicao = data_expedicao_obj
            
            # Recalcular peso e pallet
            peso_calculado, pallet_calculado = calcular_peso_pallet_produto(cod_produto, nova_quantidade)
            separacao_existente.peso = peso_calculado
            separacao_existente.pallet = pallet_calculado
            separacao_existente.valor_saldo = float(item_carteira.preco_produto_pedido or 0) * nova_quantidade
            
            db.session.commit()
            
            logger.info(f"Separação atualizada: {num_pedido}/{cod_produto} - Qtd: {nova_quantidade}")
            
            return jsonify({
                "success": True,
                "message": "Quantidade atualizada com sucesso",
                "lote_id": separacao_lote_id,
                "qtd_total": nova_quantidade
            })
        else:
            # Criar nova separação
            # Calcular peso e pallet
            peso_calculado, pallet_calculado = calcular_peso_pallet_produto(cod_produto, qtd_selecionada)
            
            # Buscar informações de rota
            rota = buscar_rota_por_uf(item_carteira.cod_uf or item_carteira.estado)
            sub_rota = buscar_sub_rota_por_uf_cidade(
                item_carteira.cod_uf or item_carteira.estado,
                item_carteira.nome_cidade or item_carteira.municipio
            )
            
            nova_separacao = Separacao(
                separacao_lote_id=separacao_lote_id,
                num_pedido=num_pedido,
                cod_produto=cod_produto,
                qtd_saldo=qtd_selecionada,
                valor_saldo=float(item_carteira.preco_produto_pedido or 0) * float(qtd_selecionada),
                peso=peso_calculado,
                pallet=pallet_calculado,
                cnpj_cpf=item_carteira.cnpj_cpf,
                raz_social_red=item_carteira.raz_social_red,
                nome_produto=item_carteira.nome_produto,
                nome_cidade=item_carteira.nome_cidade or item_carteira.municipio,
                cod_uf=item_carteira.cod_uf or item_carteira.estado,
                data_pedido=item_carteira.data_pedido,
                expedicao=data_expedicao_obj,
                agendamento=data.get("agendamento"),
                protocolo=data.get("protocolo"),
                tipo_envio=data.get("tipo_envio", "parcial"),  # Por padrão parcial no drag & drop
                observ_ped_1=item_carteira.observ_ped_1,
                pedido_cliente=item_carteira.pedido_cliente,
                # vendedor=item_carteira.vendedor,  # REMOVIDO: campo não existe em Separacao
                # equipe_vendas=item_carteira.equipe_vendas,  # REMOVIDO: campo não existe em Separacao
                rota=rota,
                sub_rota=sub_rota,
                status=status,
                sincronizado_nf=False,  # Sempre cria como não sincronizado
                criado_em=agora_brasil()
            )
            
            db.session.add(nova_separacao)
            db.session.commit()
            
            logger.info(f"Separação criada: {num_pedido}/{cod_produto} - Status: {status}")
            
            return jsonify({
                "success": True,
                "message": f"Separação criada com sucesso (status: {status})",
                "lote_id": separacao_lote_id,
                "separacao_id": nova_separacao.id
            })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao salvar separação: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@carteira_bp.route("/api/separacao/<int:separacao_id>/remover", methods=["DELETE"])
@login_required
def remover_separacao_generic(separacao_id):
    """
    API genérica para remover uma separação individual
    Não permite remover se sincronizado_nf=True
    """
    try:
        
        separacao = Separacao.query.get_or_404(separacao_id)
        
        # Verificar se está sincronizada
        if separacao.sincronizado_nf:
            return jsonify({
                "success": False,
                "error": "Não é possível remover uma separação já sincronizada com NF"
            }), 400
        
        # Guardar informações para resposta
        num_pedido = separacao.num_pedido
        cod_produto = separacao.cod_produto
        lote_id = separacao.separacao_lote_id
        
        db.session.delete(separacao)
        db.session.commit()
        
        logger.info(f"Separação {separacao_id} removida por {current_user.nome if hasattr(current_user, 'nome') else 'usuário'}")
        
        return jsonify({
            "success": True,
            "message": "Separação removida com sucesso",
            "num_pedido": num_pedido,
            "cod_produto": cod_produto,
            "lote_id": lote_id
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao remover separação {separacao_id}: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@carteira_bp.route("/api/separacao/<string:lote_id>/atualizar-datas", methods=["POST"])
@login_required
def atualizar_datas_separacao_generic(lote_id):
    """
    API genérica para atualizar datas de todas as separações de um lote
    Funciona para qualquer status (PREVISAO, ABERTO, etc.)
    Não permite alterar se alguma estiver com sincronizado_nf=True
    """
    try:
        data = request.get_json()
        
        # Buscar todas as separações do lote que NÃO estão sincronizadas
        separacoes = Separacao.query.filter(
            Separacao.separacao_lote_id == lote_id,
            Separacao.sincronizado_nf == False  # Explicitamente != True para incluir NULL
        ).all()
        
        if not separacoes:
            # Verificar se existem mas estão sincronizadas
            sincronizadas = Separacao.query.filter(
                Separacao.separacao_lote_id == lote_id,
                Separacao.sincronizado_nf == True
            ).count()
            
            if sincronizadas > 0:
                return jsonify({
                    "success": False,
                    "error": f"Lote {lote_id} possui {sincronizadas} itens sincronizados com NF que não podem ser alterados"
                }), 400
            else:
                return jsonify({
                    "success": False,
                    "error": f"Nenhuma separação encontrada para o lote {lote_id}"
                }), 404
        
        # Atualizar campos se fornecidos
        contador = 0
        for sep in separacoes:
            if "expedicao" in data and data["expedicao"]:
                sep.expedicao = datetime.strptime(data["expedicao"], "%Y-%m-%d").date()
            if "agendamento" in data:
                sep.agendamento = datetime.strptime(data["agendamento"], "%Y-%m-%d").date() if data["agendamento"] else None
            if "protocolo" in data:
                sep.protocolo = data["protocolo"]
            if "agendamento_confirmado" in data:
                sep.agendamento_confirmado = data["agendamento_confirmado"]
            contador += 1
        
        db.session.commit()
        
        logger.info(f"Datas atualizadas para lote {lote_id} ({contador} itens) por {current_user.nome if hasattr(current_user, 'nome') else 'usuário'}")
        
        return jsonify({
            "success": True,
            "message": f"Datas atualizadas para {contador} itens",
            "lote_id": lote_id
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao atualizar datas do lote {lote_id}: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@carteira_bp.route("/api/separacao/<string:lote_id>/alterar-status", methods=["POST"])
@login_required
def alterar_status_separacao(lote_id):
    """
    API para alterar status de separações de um lote
    Usado principalmente para ABERTO → PREVISAO
    """
    try:
        data = request.get_json()
        novo_status = data.get("status")
        
        if not novo_status:
            return jsonify({
                "success": False,
                "error": "Status é obrigatório"
            }), 400
        
        # Buscar todas as separações do lote que NÃO estão sincronizadas
        separacoes = Separacao.query.filter(
            Separacao.separacao_lote_id == lote_id,
            Separacao.sincronizado_nf == False
        ).all()
        
        if not separacoes:
            # Verificar se existem mas estão sincronizadas
            sincronizadas = Separacao.query.filter(
                Separacao.separacao_lote_id == lote_id,
                Separacao.sincronizado_nf == True
            ).count()
            
            if sincronizadas > 0:
                return jsonify({
                    "success": False,
                    "error": f"Lote possui {sincronizadas} itens sincronizados com NF que não podem ser alterados"
                }), 400
            else:
                return jsonify({
                    "success": False,
                    "error": f"Nenhuma separação encontrada para o lote {lote_id}"
                }), 404
        
        # Validar transição de status
        status_atual = separacoes[0].status if separacoes else None
        
        # Regras de transição permitidas
        transicoes_validas = {
            'ABERTO': ['PREVISAO'],  # Pode voltar para PREVISAO
            'PREVISAO': ['ABERTO'],  # Pode avançar para ABERTO
        }
        
        if status_atual and novo_status not in transicoes_validas.get(status_atual, []):
            return jsonify({
                "success": False,
                "error": f"Transição inválida: {status_atual} → {novo_status}"
            }), 400
        
        # Atualizar status de todas as separações do lote
        contador = 0
        for sep in separacoes:
            sep.status = novo_status
            contador += 1
        
        db.session.commit()
        
        logger.info(f"Status alterado para {novo_status} no lote {lote_id} ({contador} itens)")
        
        return jsonify({
            "success": True,
            "message": f"Status alterado para {novo_status}",
            "lote_id": lote_id,
            "itens_atualizados": contador,
            "novo_status": novo_status
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao alterar status do lote {lote_id}: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@carteira_bp.route("/api/separacao/<string:lote_id>/excluir", methods=["DELETE"])
@login_required
def excluir_lote_separacao(lote_id):
    """
    API para excluir todas as separações de um lote
    Só permite excluir se status for PREVISAO ou ABERTO
    """
    try:
        # Buscar todas as separações do lote
        separacoes = Separacao.query.filter(
            Separacao.separacao_lote_id == lote_id
        ).all()
        
        if not separacoes:
            return jsonify({
                "success": False,
                "error": f"Nenhuma separação encontrada para o lote {lote_id}"
            }), 404
        
        # Verificar se todas as separações podem ser excluídas
        status_permitidos = ['PREVISAO', 'ABERTO']
        nao_permitidas = []
        
        for sep in separacoes:
            # Não pode excluir se sincronizada com NF
            if sep.sincronizado_nf:
                nao_permitidas.append(f"{sep.cod_produto} (sincronizada com NF)")
            # Não pode excluir se status não permitido
            elif sep.status not in status_permitidos:
                nao_permitidas.append(f"{sep.cod_produto} (status: {sep.status})")
        
        if nao_permitidas:
            return jsonify({
                "success": False,
                "error": f"Não é possível excluir. Itens com restrição: {', '.join(nao_permitidas)}"
            }), 400
        
        # Guardar informações para log
        num_pedido = separacoes[0].num_pedido if separacoes else None
        contador = len(separacoes)
        
        # Excluir todas as separações
        for sep in separacoes:
            db.session.delete(sep)
        
        db.session.commit()
        
        logger.info(f"Lote {lote_id} excluído ({contador} itens) do pedido {num_pedido}")
        
        return jsonify({
            "success": True,
            "message": f"Lote excluído com sucesso ({contador} itens)",
            "lote_id": lote_id,
            "num_pedido": num_pedido,
            "itens_excluidos": contador
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao excluir lote {lote_id}: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
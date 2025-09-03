"""
APIs para gerenciamento de pré-separações usando ADAPTER
Sistema de persistência para drag & drop do workspace
Data: 2025-01-29

VERSÃO COM ADAPTER: Usa Separacao com status='PREVISAO' ao invés de PreSeparacaoItem
"""

from flask import jsonify, request, current_app
from flask_login import login_required
from datetime import datetime
from app import db
from app.carteira.models import CarteiraPrincipal
from app.separacao.models import Separacao
from app.utils.timezone import agora_brasil
from app.carteira.utils.separacao_utils import calcular_peso_pallet_produto
from app.utils.lote_utils import gerar_lote_id as gerar_novo_lote_id
import logging

from . import carteira_bp

logger = logging.getLogger(__name__)


@carteira_bp.route("/api/pre-separacao-v2/salvar", methods=["POST"])
@login_required
def salvar_pre_separacao_v2():
    """
    API para salvar pré-separação no drag & drop usando Separacao com status='PREVISAO'
    Cada drag & drop cria/atualiza uma Separacao
    """
    try:
        data = request.get_json()
        num_pedido = data.get("num_pedido")
        cod_produto = data.get("cod_produto")
        separacao_lote_id = data.get("lote_id")  # Pode vir como 'lote_id' do frontend
        qtd_selecionada = data.get("qtd_selecionada_usuario")
        data_expedicao = data.get("data_expedicao_editada")

        # Se não foi fornecido separacao_lote_id, gerar um novo
        if not separacao_lote_id:
            separacao_lote_id = gerar_novo_lote_id()

        if not all([num_pedido, cod_produto, qtd_selecionada, data_expedicao]):
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Dados obrigatórios: num_pedido, cod_produto, qtd_selecionada_usuario, data_expedicao_editada",
                    }
                ),
                400,
            )

        # Buscar item da carteira para dados base
        item_carteira = (
            db.session.query(CarteiraPrincipal)
            .filter(
                CarteiraPrincipal.num_pedido == num_pedido,
                CarteiraPrincipal.cod_produto == cod_produto,
                CarteiraPrincipal.ativo == True,
            )
            .first()
        )

        if not item_carteira:
            return jsonify({"success": False, "error": f"Item não encontrado: {num_pedido} - {cod_produto}"}), 404

        # Converter data
        try:
            data_expedicao_obj = datetime.strptime(data_expedicao, "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"success": False, "error": "Formato de data inválido"}), 400

        # Verificar se já existe pré-separação (Separacao com status='PREVISAO') para este produto no mesmo lote
        pre_separacao_existente = Separacao.query.filter(
            Separacao.num_pedido == num_pedido,
            Separacao.cod_produto == cod_produto,
            Separacao.separacao_lote_id == separacao_lote_id,
            Separacao.status == 'PREVISAO'  # ✅ Usar status PREVISAO
        ).first()

        if pre_separacao_existente:
            # Somar quantidade à existente
            nova_quantidade = float(pre_separacao_existente.qtd_saldo) + float(qtd_selecionada)

            # Verificar se não excede o saldo disponível
            if nova_quantidade > float(item_carteira.qtd_saldo_produto_pedido):
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": f"Quantidade total ({nova_quantidade}) excede o saldo disponível ({item_carteira.qtd_saldo_produto_pedido})",
                        }
                    ),
                    400,
                )

            # Atualizar quantidade existente (somar)
            pre_separacao_existente.qtd_saldo = nova_quantidade
            # Recalcular valor total
            pre_separacao_existente.valor_saldo = (
                float(item_carteira.preco_produto_pedido or 0) * nova_quantidade
            )
            # Recalcular peso e pallet
            peso_calculado, pallet_calculado = calcular_peso_pallet_produto(cod_produto, nova_quantidade)
            pre_separacao_existente.peso = peso_calculado
            pre_separacao_existente.pallet = pallet_calculado
            
            pre_separacao = pre_separacao_existente
            acao = "atualizada (quantidade somada)"
        else:
            # Calcular peso e pallet
            peso_calculado, pallet_calculado = calcular_peso_pallet_produto(
                cod_produto, float(qtd_selecionada)
            )
            
            # Criar nova pré-separação como Separacao com status='PREVISAO'
            pre_separacao = Separacao(
                # Identificação
                separacao_lote_id=separacao_lote_id,
                num_pedido=num_pedido,
                cod_produto=cod_produto,
                nome_produto=item_carteira.nome_produto,
                
                # Cliente
                cnpj_cpf=item_carteira.cnpj_cpf,
                raz_social_red=item_carteira.raz_social_red,
                nome_cidade=item_carteira.nome_cidade,
                cod_uf=item_carteira.cod_uf,
                
                # Quantidades e valores
                qtd_saldo=float(qtd_selecionada),
                valor_saldo=float(item_carteira.preco_produto_pedido or 0) * float(qtd_selecionada),
                peso=peso_calculado,
                pallet=pallet_calculado,
                
                # Datas
                data_pedido=item_carteira.data_pedido,
                expedicao=data_expedicao_obj,
                agendamento=None,  # Pode ser preenchido depois
                protocolo=data.get("protocolo_editado"),
                
                # Observações
                observ_ped_1=data.get("observacoes_usuario"),
                
                # Status e controle
                status='PREVISAO',  # ✅ Status PREVISAO para pré-separação
                tipo_envio=(
                    "parcial" if float(qtd_selecionada) < float(item_carteira.qtd_saldo_produto_pedido) else "total"
                ),
                criado_em=agora_brasil(),
                
                # Campos opcionais
                rota=item_carteira.rota if hasattr(item_carteira, 'rota') else None,
                sub_rota=item_carteira.sub_rota if hasattr(item_carteira, 'sub_rota') else None,
                roteirizacao=item_carteira.roteirizacao if hasattr(item_carteira, 'roteirizacao') else None,
                pedido_cliente=item_carteira.pedido_cliente if hasattr(item_carteira, 'pedido_cliente') else None,
            )
            db.session.add(pre_separacao)
            acao = "criada"

        db.session.commit()

        # Calcular valores para resposta
        quantidade_final = float(pre_separacao.qtd_saldo)

        return jsonify(
            {
                "success": True,
                "message": f"Pré-separação {acao} com sucesso",
                "pre_separacao_id": pre_separacao.id,
                "lote_id": separacao_lote_id,
                "dados": {
                    "cod_produto": cod_produto,
                    "quantidade": quantidade_final,
                    "valor": float(pre_separacao.valor_saldo or 0),
                    "peso": float(pre_separacao.peso or 0),
                    "pallet": float(pre_separacao.pallet or 0),
                    "status": "CRIADO",  # Manter compatibilidade com frontend
                    "tipo": "pre_separacao",
                },
            }
        )

    except Exception as e:
        # Verificar se a sessão está em estado válido antes do rollback
        try:
            if db.session.is_active:
                db.session.rollback()
        except Exception:
            # Se não conseguir fazer rollback, criar nova sessão
            db.session.remove()
            db.session = db.create_scoped_session()

        logger.error(f"Erro ao salvar pré-separação: {e}")
        return jsonify({"success": False, "error": f"Erro interno: {str(e)}"}), 500


@carteira_bp.route("/api/pedido/<num_pedido>/pre-separacoes-v2")
@login_required
def listar_pre_separacoes_v2(num_pedido):
    """
    API para listar pré-separações existentes de um pedido
    Usa Separacao com status='PREVISAO'
    """
    try:
        # Buscar Separacao com status='PREVISAO'
        pre_separacoes = (
            db.session.query(Separacao)
            .filter(
                Separacao.num_pedido == num_pedido, 
                Separacao.status == 'PREVISAO'  # ✅ Buscar status PREVISAO
            )
            .all()
        )

        # Agrupar por separacao_lote_id
        lotes = {}
        for pre_sep in pre_separacoes:
            lote_key = pre_sep.separacao_lote_id

            if lote_key not in lotes:
                lotes[lote_key] = {
                    "lote_id": lote_key,
                    "data_expedicao": (
                        pre_sep.expedicao.strftime('%Y-%m-%d') if pre_sep.expedicao else None
                    ),
                    "data_agendamento": (
                        pre_sep.agendamento.strftime('%Y-%m-%d') if pre_sep.agendamento else None
                    ),
                    "agendamento_confirmado": pre_sep.agendamento_confirmado if hasattr(pre_sep, 'agendamento_confirmado') else False,
                    "protocolo": pre_sep.protocolo,
                    "status": "pre_separacao",
                    "produtos": [],
                    "totais": {"valor": 0, "peso": 0, "pallet": 0},
                    "pre_separacao_id": pre_sep.id,
                }

            produto_data = {
                "pre_separacao_id": pre_sep.id,
                "cod_produto": pre_sep.cod_produto,
                "nome_produto": pre_sep.nome_produto,
                "quantidade": float(pre_sep.qtd_saldo),
                "valor": float(pre_sep.valor_saldo or 0),
                "peso": float(pre_sep.peso or 0),
                "pallet": float(pre_sep.pallet or 0),
            }

            lotes[lote_key]["produtos"].append(produto_data)
            lotes[lote_key]["totais"]["valor"] += produto_data["valor"]
            lotes[lote_key]["totais"]["peso"] += produto_data["peso"]
            lotes[lote_key]["totais"]["pallet"] += produto_data["pallet"]

        return jsonify(
            {"success": True, "num_pedido": num_pedido, "lotes": list(lotes.values()), "total_lotes": len(lotes)}
        )

    except Exception as e:
        logger.error(f"Erro ao listar pré-separações do pedido {num_pedido}: {e}")
        return jsonify({"success": False, "error": f"Erro interno: {str(e)}"}), 500


@carteira_bp.route("/api/pre-separacao-v2/<int:pre_separacao_id>/remover", methods=["DELETE"])
@login_required
def remover_pre_separacao_v2(pre_separacao_id):
    """
    API para remover pré-separação (quando remove produto do lote)
    Remove Separacao com status='PREVISAO'
    """
    try:
        # Buscar Separacao com status='PREVISAO'
        pre_separacao = Separacao.query.filter(
            Separacao.id == pre_separacao_id,
            Separacao.status == 'PREVISAO'
        ).first()

        if not pre_separacao:
            return jsonify({"success": False, "error": "Pré-separação não encontrada"}), 404

        # Dados para resposta antes de deletar
        dados_removidos = {
            "cod_produto": pre_separacao.cod_produto,
            "quantidade": float(pre_separacao.qtd_saldo),
            "valor": float(pre_separacao.valor_saldo or 0),
        }

        db.session.delete(pre_separacao)
        db.session.commit()

        return jsonify(
            {"success": True, "message": "Pré-separação removida com sucesso", "dados_removidos": dados_removidos}
        )

    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao remover pré-separação {pre_separacao_id}: {e}")
        return jsonify({"success": False, "error": f"Erro interno: {str(e)}"}), 500


@carteira_bp.route("/api/pre-separacao-v2/<lote_id>/atualizar-datas", methods=["POST"])
@login_required
def atualizar_datas_pre_separacao_v2(lote_id):
    """
    Atualiza datas de expedição, agendamento e protocolo de uma pré-separação
    Atualiza Separacao com status='PREVISAO'
    """
    try:
        data = request.get_json()
        data_expedicao = data.get("expedicao")
        data_agendamento = data.get("agendamento")
        protocolo = data.get("protocolo")
        agendamento_confirmado = data.get("agendamento_confirmado", False)

        if not data_expedicao:
            return jsonify({"success": False, "error": "Data de expedição é obrigatória"}), 400

        # Buscar todas as Separacao com status='PREVISAO' do lote
        pre_separacoes = Separacao.query.filter(
            Separacao.separacao_lote_id == lote_id, 
            Separacao.status == 'PREVISAO'
        ).all()

        if not pre_separacoes:
            return jsonify({"success": False, "error": "Pré-separação não encontrada ou já processada"}), 404

        # Converter datas
        from datetime import datetime

        data_expedicao_obj = datetime.strptime(data_expedicao, "%Y-%m-%d").date()
        data_agendamento_obj = None
        if data_agendamento:
            data_agendamento_obj = datetime.strptime(data_agendamento, "%Y-%m-%d").date()

        # Atualizar todas as pré-separações do lote
        for pre_sep in pre_separacoes:
            pre_sep.expedicao = data_expedicao_obj
            pre_sep.agendamento = data_agendamento_obj
            pre_sep.protocolo = protocolo
            if hasattr(pre_sep, 'agendamento_confirmado'):
                pre_sep.agendamento_confirmado = agendamento_confirmado

        db.session.commit()

        return jsonify(
            {
                "success": True,
                "message": f"{len(pre_separacoes)} itens atualizados com sucesso",
                "itens_atualizados": len(pre_separacoes),
            }
        )

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao atualizar datas da pré-separação: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@carteira_bp.route("/api/lote-v2/<lote_id>/transformar-separacao", methods=["POST"])
@login_required
def transformar_lote_em_separacao_v2(lote_id):
    """
    API para transformar pré-separação em separação definitiva
    Converte Separacao de status='PREVISAO' para status='ABERTO'
    """
    try:
        logger.info(f"Transformando lote {lote_id} de PREVISAO para ABERTO")
        
        # Buscar Separacoes com status='PREVISAO'
        pre_separacoes = Separacao.query.filter(
            Separacao.separacao_lote_id == lote_id, 
            Separacao.status == 'PREVISAO'
        ).all()

        if not pre_separacoes:
            logger.warning(f"Nenhuma pré-separação encontrada para lote {lote_id}")
            return jsonify({"success": False, "error": "Nenhuma pré-separação encontrada para este lote"}), 404

        # Verificar se é lote completo (todos os produtos do pedido)
        num_pedido = pre_separacoes[0].num_pedido

        # IMPORTANTE: Apenas atualizar status de PREVISAO para ABERTO
        # NÃO criar novas separações, apenas mudar o status!
        separacoes_atualizadas = 0
        valor_total = 0
        peso_total = 0
        pallet_total = 0

        for pre_sep in pre_separacoes:
            # Apenas mudar o status
            pre_sep.status = 'ABERTO'
            separacoes_atualizadas += 1
            
            # Acumular totais
            valor_total += float(pre_sep.valor_saldo or 0)
            peso_total += float(pre_sep.peso or 0)
            pallet_total += float(pre_sep.pallet or 0)

        if separacoes_atualizadas == 0:
            return jsonify({"success": False, "error": "Nenhuma separação foi atualizada"}), 400

        # IMPORTANTE: Após migração, Pedido é uma VIEW que se atualiza automaticamente
        # Não precisamos (e não podemos) criar registros em Pedido
        # A VIEW agregará automaticamente as Separacoes com mesmo separacao_lote_id
        
        # Commit das mudanças (apenas atualização de status das Separacoes)
        db.session.commit()

        return jsonify(
            {
                "success": True,
                "message": f"Lote transformado em separação com sucesso! {separacoes_atualizadas} produtos processados.",
                "lote_id": lote_id,
                "tipo_envio": pre_separacoes[0].tipo_envio,
                "separacoes_atualizadas": separacoes_atualizadas,
                "totais": {
                    "valor": valor_total,
                    "peso": peso_total,
                    "pallet": pallet_total,
                },
            }
        )

    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao transformar lote {lote_id}: {e}")
        return jsonify({"success": False, "error": f"Erro interno: {str(e)}"}), 500


# NOTA: Esta é uma versão com ADAPTER que usa Separacao com status='PREVISAO'
# Para ativar estas rotas, remova o sufixo -v2 e substitua as rotas originais
# Ou configure um switch para escolher entre versão original e versão com adapter
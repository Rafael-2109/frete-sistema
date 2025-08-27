"""
API para gerar separação de pedidos completos na carteira agrupada
Versão unificada com suporte a parciais HTML e JSON
"""

from flask import jsonify, request, render_template
from flask_login import login_required, current_user
from datetime import datetime
from app import db
from app.carteira.models import CarteiraPrincipal
from app.separacao.models import Separacao
from app.pedidos.models import Pedido
from app.utils.timezone import agora_brasil
from app.carteira.utils.separacao_utils import (
    calcular_peso_pallet_produto,
    buscar_rota_por_uf,
    buscar_sub_rota_por_uf_cidade,
    gerar_novo_lote_id,
)
import logging

from . import carteira_bp
from app.carteira.models import PreSeparacaoItem

logger = logging.getLogger(__name__)


@carteira_bp.route("/api/pedido/<num_pedido>/verificar-lote", methods=["GET"])
@login_required
def verificar_lote_pedido(num_pedido):
    """
    API para verificar se existe pré-separação para o pedido

    Retorna:
    {
        "lote_completo_com_expedicao": true/false,
        "lote_parcial_existe": true/false,
        "lote_id": "LOTE-ID" (se existir lote completo)
    }
    """
    try:
        # Buscar pré-separações do pedido
        pre_separacoes = PreSeparacaoItem.query.filter(
            PreSeparacaoItem.num_pedido == num_pedido, PreSeparacaoItem.status.in_(["CRIADO", "RECOMPOSTO"])
        ).all()

        if not pre_separacoes:
            return jsonify({"lote_completo_com_expedicao": False, "lote_parcial_existe": False, "lote_id": None})

        # Agrupar por separacao_lote_id e verificar tipo_envio
        lotes_info = {}
        for item in pre_separacoes:
            # Usar separacao_lote_id que é o campo correto
            lote_id = getattr(item, "separacao_lote_id", None) or "sem_lote"
            if lote_id not in lotes_info:
                lotes_info[lote_id] = {
                    "tipo_envio": getattr(item, "tipo_envio", "total"),
                    "data_expedicao": getattr(item, "data_expedicao_editada", None),
                    "itens": [],
                }
            lotes_info[lote_id]["itens"].append(item)

        # Verificar se existe lote completo com expedição
        for lote_id, info in lotes_info.items():
            if info["tipo_envio"] == "total" and info["data_expedicao"] is not None:
                return jsonify({"lote_completo_com_expedicao": True, "lote_parcial_existe": False, "lote_id": lote_id})

        # Verificar se existe lote parcial
        tem_parcial = any(info["tipo_envio"] == "parcial" for info in lotes_info.values())

        return jsonify({"lote_completo_com_expedicao": False, "lote_parcial_existe": tem_parcial, "lote_id": None})

    except Exception as e:
        logger.error(f"Erro ao verificar lote do pedido {num_pedido}: {e}")
        return jsonify({"success": False, "error": f"Erro interno: {str(e)}"}), 500


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
        from app.separacao.models import Separacao
        from app.pedidos.models import Pedido
        from sqlalchemy import text
        
        # LOCK no nível do pedido primeiro (advisory lock do PostgreSQL)
        # Isso garante que apenas uma transação processe este pedido por vez
        db.session.execute(text(f"SELECT pg_advisory_xact_lock(hashtext(:pedido))"), {'pedido': num_pedido})
        
        # Agora verificar novamente com a garantia do lock
        separacao_existente = Separacao.query.filter_by(
            num_pedido=num_pedido,
            tipo_envio='total'
        ).first()
        
        if separacao_existente:
            db.session.rollback()  # Liberar o lock
            return jsonify({
                "success": False, 
                "error": f"Pedido já possui separação completa (Lote: {separacao_existente.separacao_lote_id})"
            }), 400
        
        data = request.get_json()
        expedicao = data.get("expedicao")
        agendamento = data.get("agendamento")
        protocolo = data.get("protocolo")
        agendamento_confirmado = data.get("agendamento_confirmado", False)

        if not expedicao:
            return jsonify({"success": False, "error": "Data de expedição é obrigatória"}), 400

        # Buscar todos os produtos do pedido
        produtos_pedido = (
            db.session.query(CarteiraPrincipal)
            .filter(CarteiraPrincipal.num_pedido == num_pedido, CarteiraPrincipal.ativo == True)
            .all()
        )

        if not produtos_pedido:
            return jsonify({"success": False, "error": f"Nenhum produto encontrado para o pedido {num_pedido}"}), 404

        # Converter datas
        try:
            expedicao_obj = datetime.strptime(expedicao, "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"success": False, "error": "Formato de data de expedição inválido"}), 400

        agendamento_obj = None
        if agendamento:
            try:
                agendamento_obj = datetime.strptime(agendamento, "%Y-%m-%d").date()
            except ValueError:
                pass

        # Gerar ID único para o lote
        lote_id = gerar_novo_lote_id()

        # Criar separações para todos os produtos
        separacoes_criadas = []
        valor_total_separacao = 0
        peso_total_separacao = 0
        pallet_total_separacao = 0

        # Tipo de envio é sempre 'total' pois está separando todos os produtos
        tipo_envio = "total"

        for item in produtos_pedido:
            quantidade = float(item.qtd_saldo_produto_pedido or 0)

            if quantidade <= 0:
                continue

            # Calcular valores proporcionais
            preco_unitario = float(item.preco_produto_pedido or 0)
            valor_separacao = quantidade * preco_unitario

            # Calcular peso e pallet
            peso_calculado, pallet_calculado = calcular_peso_pallet_produto(item.cod_produto, quantidade)

            # Buscar rota e sub-rota
            # Se incoterm for RED ou FOB, usar ele como rota
            if item.incoterm in ["RED", "FOB"]:
                rota_calculada = item.incoterm
            else:
                rota_calculada = buscar_rota_por_uf(item.cod_uf or "SP")
            sub_rota_calculada = buscar_sub_rota_por_uf_cidade(item.cod_uf or "", item.nome_cidade or "")

            # Criar separação
            separacao = Separacao(
                separacao_lote_id=lote_id,
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
                roteirizacao=None,
                expedicao=expedicao_obj,
                agendamento=agendamento_obj,
                protocolo=protocolo,
                agendamento_confirmado=agendamento_confirmado,
                pedido_cliente=item.pedido_cliente,  # 🆕 Incluir pedido_cliente diretamente da CarteiraPrincipal
                tipo_envio=tipo_envio,
                criado_em=agora_brasil(),
            )

            db.session.add(separacao)
            separacoes_criadas.append(separacao)

            # Acumular totais
            valor_total_separacao += valor_separacao
            peso_total_separacao += peso_calculado
            pallet_total_separacao += pallet_calculado

        if not separacoes_criadas:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Nenhuma separação foi criada. Verifique se há produtos com quantidade válida.",
                    }
                ),
                400,
            )

        # SEMPRE criar um novo pedido para este lote de separação
        # Buscar dados do primeiro item para popular o pedido
        primeiro_item = separacoes_criadas[0]

        # Verificar se já existe um pedido com este lote (não deveria)
        pedido_existente = Pedido.query.filter_by(separacao_lote_id=lote_id).first()

        if pedido_existente:
            # Se por algum motivo já existe, remover
            db.session.delete(pedido_existente)

        # Buscar pedido_cliente da CarteiraPrincipal usando apenas num_pedido
        item_carteira = CarteiraPrincipal.query.filter_by(
            num_pedido=num_pedido,
            ativo=True
        ).first()
        pedido_cliente = item_carteira.pedido_cliente if item_carteira else None
        
        # Criar novo pedido
        novo_pedido = Pedido(
            separacao_lote_id=lote_id,
            num_pedido=num_pedido,
            data_pedido=primeiro_item.data_pedido,
            cnpj_cpf=primeiro_item.cnpj_cpf,
            raz_social_red=primeiro_item.raz_social_red,
            nome_cidade=primeiro_item.nome_cidade,
            cod_uf=primeiro_item.cod_uf,
            valor_saldo_total=valor_total_separacao,
            pallet_total=pallet_total_separacao,
            peso_total=peso_total_separacao,
            rota=primeiro_item.rota,
            sub_rota=primeiro_item.sub_rota,
            observ_ped_1=primeiro_item.observ_ped_1,
            expedicao=expedicao_obj,
            agendamento=agendamento_obj,
            protocolo=protocolo,
            pedido_cliente=pedido_cliente,  # ✅ NOVO: Incluir pedido_cliente
            status="ABERTO",  # Sempre começa como ABERTO
        )

        db.session.add(novo_pedido)

        # Commit das mudanças
        db.session.commit()

        # Verificar se cliente quer resposta com parciais HTML
        accept_html = request.headers.get('Accept', '').find('text/html') != -1 or request.args.get('format') == 'html'
        
        if accept_html:
            # Retornar parciais HTML para atualização sem reload
            pedido_atualizado = _get_pedido_completo(num_pedido)
            contadores = _calcular_contadores_globais()
            
            return jsonify({
                "ok": True,
                "success": True,
                "message": f"Separação completa gerada com sucesso! {len(separacoes_criadas)} produtos separados.",
                "targets": {
                    f"#resumo-{num_pedido}": render_template('carteira/partials/_resumo_pedido.html', 
                                                            pedido=pedido_atualizado),
                    f"#separacoes-{num_pedido}": render_template('carteira/partials/_separacoes_pedido.html', 
                                                                pedido=pedido_atualizado),
                    f"#botoes-{num_pedido}": render_template('carteira/partials/_botoes_pedido.html', 
                                                            pedido=pedido_atualizado)
                },
                "contadores": contadores,
                "lote_id": lote_id,
                "separacoes_criadas": len(separacoes_criadas)
            })
        else:
            # Resposta JSON tradicional para compatibilidade
            return jsonify(
                {
                    "success": True,
                    "message": f"Separação completa gerada com sucesso! {len(separacoes_criadas)} produtos separados.",
                    "lote_id": lote_id,
                    "tipo_envio": tipo_envio,
                    "separacoes_criadas": len(separacoes_criadas),
                    "totais": {
                        "valor": valor_total_separacao,
                        "peso": peso_total_separacao,
                        "pallet": pallet_total_separacao,
                    },
                    "datas": {"expedicao": expedicao, "agendamento": agendamento, "protocolo": protocolo},
                }
            )

    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao gerar separação completa do pedido {num_pedido}: {e}")
        return jsonify({"success": False, "error": f"Erro interno: {str(e)}"}), 500


@carteira_bp.route("/api/lote/<lote_id>/transformar-separacao", methods=["POST"])
@login_required
def transformar_lote_em_separacao(lote_id):
    """
    API para transformar pré-separação em separação definitiva
    Usado pelo botão "Transformar em Separação" no workspace
    """
    try:
        # Log para debug
        logger.info(f"Tentando transformar lote {lote_id} em separação")
        
        # Buscar pré-separações pelo separacao_lote_id
        pre_separacoes = PreSeparacaoItem.query.filter(
            PreSeparacaoItem.separacao_lote_id == lote_id, 
            PreSeparacaoItem.status.in_(["CRIADO", "RECOMPOSTO"])
        ).all()
        
        # Debug: verificar se existem pré-separações com outro status
        todas_pre_sep = PreSeparacaoItem.query.filter(
            PreSeparacaoItem.separacao_lote_id == lote_id
        ).all()
        
        if todas_pre_sep and not pre_separacoes:
            status_encontrados = [ps.status for ps in todas_pre_sep]
            logger.warning(f"Lote {lote_id} tem pré-separações mas com status: {status_encontrados}")
            return jsonify({
                "success": False, 
                "error": f"Pré-separações encontradas mas com status inadequado: {set(status_encontrados)}"
            }), 400

        if not pre_separacoes:
            logger.warning(f"Nenhuma pré-separação encontrada para lote {lote_id}")
            return jsonify({"success": False, "error": "Nenhuma pré-separação encontrada para este lote"}), 404

        # Verificar se é lote completo (todos os produtos do pedido)
        num_pedido = pre_separacoes[0].num_pedido

        # MANTER O MESMO lote_id da pré-separação
        # NÃO gerar novo, para manter rastreabilidade
        separacao_lote_id = lote_id  # Usar o mesmo ID

        # Criar separações
        separacoes_criadas = []
        valor_total = 0
        peso_total = 0
        pallet_total = 0

        for pre_sep in pre_separacoes:
            quantidade = float(pre_sep.qtd_selecionada_usuario)

            # Buscar item da carteira para dados adicionais
            item_carteira = CarteiraPrincipal.query.filter_by(
                num_pedido=num_pedido, cod_produto=pre_sep.cod_produto
            ).first()

            if not item_carteira:
                continue

            # Calcular valores
            valor_unitario = float(item_carteira.preco_produto_pedido or 0)
            valor_separacao = quantidade * valor_unitario

            # Calcular peso e pallet usando a função utilitária
            peso_calculado, pallet_calculado = calcular_peso_pallet_produto(pre_sep.cod_produto, quantidade)

            # Calcular rota e sub-rota
            # Se incoterm for RED ou FOB, usar ele como rota
            if item_carteira.incoterm in ["RED", "FOB"]:
                rota_calculada = item_carteira.incoterm
            else:
                rota_calculada = buscar_rota_por_uf(item_carteira.cod_uf or "SP")
            sub_rota_calculada = buscar_sub_rota_por_uf_cidade(
                item_carteira.cod_uf or "", item_carteira.nome_cidade or ""
            )

            # Criar separação
            separacao = Separacao(
                separacao_lote_id=separacao_lote_id,
                num_pedido=pre_sep.num_pedido,
                data_pedido=item_carteira.data_pedido,
                cnpj_cpf=item_carteira.cnpj_cpf,
                raz_social_red=item_carteira.raz_social_red,
                nome_cidade=item_carteira.nome_cidade,
                cod_uf=item_carteira.cod_uf,
                cod_produto=pre_sep.cod_produto,
                nome_produto=pre_sep.nome_produto,
                qtd_saldo=quantidade,
                valor_saldo=valor_separacao,
                peso=peso_calculado,
                pallet=pallet_calculado,
                rota=rota_calculada,
                sub_rota=sub_rota_calculada,
                observ_ped_1=item_carteira.observ_ped_1,
                roteirizacao=None,
                expedicao=pre_sep.data_expedicao_editada,
                agendamento=pre_sep.data_agendamento_editada,
                protocolo=pre_sep.protocolo_editado,
                agendamento_confirmado=pre_sep.agendamento_confirmado if hasattr(pre_sep, 'agendamento_confirmado') else False,
                pedido_cliente=item_carteira.pedido_cliente,  # 🆕 Incluir pedido_cliente diretamente da CarteiraPrincipal
                tipo_envio=pre_sep.tipo_envio,
                criado_em=agora_brasil(),
            )

            db.session.add(separacao)
            separacoes_criadas.append(separacao)

            # Acumular totais
            valor_total += valor_separacao
            peso_total += peso_calculado
            pallet_total += pallet_calculado

            # Marcar pré-separação como processada
            pre_sep.status = "ENVIADO_SEPARACAO"

        if not separacoes_criadas:
            return jsonify({"success": False, "error": "Nenhuma separação foi criada"}), 400

        # SEMPRE criar um novo pedido para este lote de separação
        # Buscar dados do primeiro item para popular o pedido
        primeiro_item = separacoes_criadas[0]

        # Verificar se já existe um pedido com este lote (não deveria)
        pedido_existente = Pedido.query.filter_by(separacao_lote_id=separacao_lote_id).first()

        if pedido_existente:
            # Se por algum motivo já existe, remover
            db.session.delete(pedido_existente)

        # Buscar pedido_cliente da CarteiraPrincipal usando apenas num_pedido
        item_carteira = CarteiraPrincipal.query.filter_by(
            num_pedido=num_pedido,
            ativo=True
        ).first()
        pedido_cliente = item_carteira.pedido_cliente if item_carteira else None

        # Criar novo pedido
        novo_pedido = Pedido(
            separacao_lote_id=separacao_lote_id,
            num_pedido=num_pedido,
            data_pedido=primeiro_item.data_pedido,
            cnpj_cpf=primeiro_item.cnpj_cpf,
            raz_social_red=primeiro_item.raz_social_red,
            nome_cidade=primeiro_item.nome_cidade,
            cod_uf=primeiro_item.cod_uf,
            valor_saldo_total=valor_total,
            pallet_total=pallet_total,
            peso_total=peso_total,
            rota=primeiro_item.rota,
            sub_rota=primeiro_item.sub_rota,
            observ_ped_1=primeiro_item.observ_ped_1,
            expedicao=pre_separacoes[0].data_expedicao_editada,
            agendamento=pre_separacoes[0].data_agendamento_editada,
            protocolo=pre_separacoes[0].protocolo_editado,
            pedido_cliente=pedido_cliente,  # ✅ NOVO: Incluir pedido_cliente
            status="ABERTO",  # Sempre começa como ABERTO
        )

        db.session.add(novo_pedido)

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
                "message": f"Lote transformado em separação com sucesso! {len(separacoes_criadas)} produtos processados.",
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
                "separacoes_criadas": len(separacoes_criadas)
            })
        else:
            # Resposta JSON tradicional
            return jsonify(
                {
                    "success": True,
                    "message": f"Lote transformado em separação com sucesso! {len(separacoes_criadas)} produtos processados.",
                    "lote_id": separacao_lote_id,
                    "separacoes_criadas": len(separacoes_criadas),
                    "pre_separacoes_processadas": len(pre_separacoes),
                    "totais": {"valor": valor_total, "peso": peso_total, "pallet": pallet_total},
                }
            )

    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao transformar lote {lote_id} em separação: {e}")
        return jsonify({"success": False, "error": f"Erro interno: {str(e)}"}), 500


# ============================================================================
# FUNÇÕES AUXILIARES PARA PARCIAIS HTML
# ============================================================================

def _get_pedido_completo(num_pedido):
    """
    Busca dados completos do pedido para renderizar parciais
    """
    from app.pedidos.models import Pedido
    
    pedido = Pedido.query.filter_by(num_pedido=num_pedido).first()
    
    # Se não existe pedido, criar objeto mock
    if not pedido:
        pedido = type('obj', (object,), {
            'num_pedido': num_pedido,
            'status': 'ABERTO',
            'cliente_nome': '',
            'itens_separados': 0,
            'total_itens': 0,
            'valor_saldo': 0
        })()
    
    # Adicionar dados calculados
    separacoes_raw = Separacao.query.filter_by(num_pedido=num_pedido).all()
    
    # Agrupar separações por lote e adicionar informações extras
    from collections import defaultdict
    lotes_sep = defaultdict(list)
    for sep in separacoes_raw:
        lotes_sep[sep.separacao_lote_id].append(sep)
    
    # Criar objetos de lote para separações
    pedido.separacoes = []
    for lote_id, itens in lotes_sep.items():
        lote_obj = type('obj', (object,), {
            'separacao_lote_id': lote_id,
            'qtd_itens': len(itens),
            'tipo_envio': itens[0].tipo_envio if itens else 'total',
            'expedicao': itens[0].expedicao if itens else None,
            'agendamento': itens[0].agendamento if itens else None,
            'protocolo': itens[0].protocolo if itens else None,
            'itens': itens,
            # ID da primeira separação para exclusão
            'id': itens[0].id if itens else None
        })()
        pedido.separacoes.append(lote_obj)
    
    # Buscar pré-separações agrupadas por lote
    pre_separacoes_raw = PreSeparacaoItem.query.filter_by(
        num_pedido=num_pedido,
        status='CRIADO'
    ).all()
    
    # Agrupar pré-separações por lote
    lotes_pre_sep = defaultdict(list)
    for ps in pre_separacoes_raw:
        lotes_pre_sep[ps.separacao_lote_id].append(ps)
    
    # Criar objetos de lote para o template
    pedido.pre_separacoes = []
    for lote_id, itens in lotes_pre_sep.items():
        lote_obj = type('obj', (object,), {
            'separacao_lote_id': lote_id,
            'qtd_itens': len(itens),
            'tipo_envio': itens[0].tipo_envio if itens else 'total',
            'itens': itens
        })()
        pedido.pre_separacoes.append(lote_obj)
    
    # Buscar dados da carteira
    carteira_itens = CarteiraPrincipal.query.filter_by(
        num_pedido=num_pedido,
        ativo=True
    ).all()
    
    # Calcular totais - CORRIGIDO: considerar apenas itens com saldo
    itens_com_saldo = [item for item in carteira_itens if (item.qtd_saldo_produto_pedido or 0) > 0]
    pedido.total_itens = len(itens_com_saldo)  # Total de itens COM SALDO
    pedido.itens_separados = len(pedido.separacoes)
    
    # Calcular valor saldo
    pedido.valor_saldo = sum(float(item.qtd_saldo_produto_pedido or 0) * float(item.preco_produto_pedido or 0) 
                            for item in itens_com_saldo)
    
    # Buscar nome do cliente
    if carteira_itens:
        pedido.cliente_nome = carteira_itens[0].raz_social_red or carteira_itens[0].raz_social or ''
    
    # CORREÇÃO: Calcular saldo real comparando quantidades
    # Buscar quantidades já separadas por produto
    produtos_separados = {}
    for lote_sep in pedido.separacoes:
        # lote_sep é um objeto com atributo 'itens' que contém as separações reais
        for item_sep in lote_sep.itens:
            cod_produto = item_sep.cod_produto
            if cod_produto:
                qtd_separada = float(item_sep.qtd_saldo or 0)
                produtos_separados[cod_produto] = produtos_separados.get(cod_produto, 0) + qtd_separada
    
    # Verificar se ainda há saldo disponível
    tem_saldo_disponivel = False
    for item in itens_com_saldo:
        qtd_disponivel = float(item.qtd_saldo_produto_pedido or 0)
        qtd_separada = produtos_separados.get(item.cod_produto, 0)
        saldo_restante = qtd_disponivel - qtd_separada
        
        if saldo_restante > 0.01:  # Margem de 1 centésimo
            tem_saldo_disponivel = True
            break
    
    # Determinar status e cores baseado em SALDO REAL
    if not tem_saldo_disponivel and pedido.total_itens > 0:
        pedido.status = 'COMPLETO'
        pedido.status_cor = 'success'
        pedido.pode_gerar_separacao = False
    elif pedido.itens_separados > 0:
        pedido.status = 'PARCIAL'
        pedido.status_cor = 'warning'
        pedido.pode_gerar_separacao = tem_saldo_disponivel  # Só pode gerar se tem saldo
    else:
        pedido.status = 'PENDENTE'
        pedido.status_cor = 'secondary'
        pedido.pode_gerar_separacao = tem_saldo_disponivel  # Só pode gerar se tem saldo
    
    return pedido


def _calcular_contadores_globais():
    """
    Calcula contadores globais para atualizar no frontend
    """
    from app.pedidos.models import Pedido
    
    total_separacoes = Separacao.query.count()
    total_pre_separacoes = PreSeparacaoItem.query.filter_by(status='CRIADO').count()
    # Usar status COMPLETO ao invés de SEPARADO para consistência
    pedidos_completos = db.session.query(Pedido).filter_by(status='COMPLETO').count()
    
    # Contar pedidos únicos com separação
    pedidos_com_separacao = db.session.query(Separacao.num_pedido).distinct().count()
    
    return {
        'contador-total-separacoes': total_separacoes,
        'contador-pre-separacoes': total_pre_separacoes,
        'contador-pedidos-completos': pedidos_completos,
        'contador-pedidos-separados': pedidos_com_separacao
    }


@carteira_bp.route("/api/contadores", methods=["GET"])
@login_required
def get_contadores():
    """
    Rota para buscar contadores globais atualizados
    """
    try:
        contadores = _calcular_contadores_globais()
        return jsonify({
            'ok': True,
            'contadores': contadores
        })
    except Exception as e:
        logger.error(f"Erro ao buscar contadores: {str(e)}")
        return jsonify({
            'ok': False,
            'error': str(e)
        }), 500


@carteira_bp.route("/api/separacao/<int:separacao_id>/excluir", methods=["DELETE"])
@login_required
def excluir_separacao(separacao_id):
    """
    Exclui separação e retorna parciais HTML atualizados
    """
    try:
        separacao = Separacao.query.get(separacao_id)
        if not separacao:
            return jsonify({
                'ok': False,
                'success': False,
                'error': 'Separação não encontrada'
            }), 404
        
        num_pedido = separacao.num_pedido
        
        # Excluir separação
        db.session.delete(separacao)
        db.session.commit()
        
        # Verificar se cliente quer parciais HTML
        accept_html = request.headers.get('Accept', '').find('text/html') != -1
        
        if accept_html:
            pedido_atualizado = _get_pedido_completo(num_pedido)
            contadores = _calcular_contadores_globais()
            
            return jsonify({
                'ok': True,
                'success': True,
                'message': 'Separação excluída com sucesso',
                'targets': {
                    f'#resumo-{num_pedido}': render_template('carteira/partials/_resumo_pedido.html', 
                                                            pedido=pedido_atualizado),
                    f'#separacoes-{num_pedido}': render_template('carteira/partials/_separacoes_pedido.html', 
                                                                pedido=pedido_atualizado),
                    f'#botoes-{num_pedido}': render_template('carteira/partials/_botoes_pedido.html', 
                                                            pedido=pedido_atualizado)
                },
                'contadores': contadores
            })
        else:
            return jsonify({
                'success': True,
                'message': 'Separação excluída com sucesso'
            })
        
    except Exception as e:
        logger.error(f"Erro ao excluir separação: {str(e)}")
        db.session.rollback()
        return jsonify({
            'ok': False,
            'success': False,
            'error': str(e)
        }), 500


@carteira_bp.route("/api/pre-separacao/<lote_id>/excluir", methods=["DELETE"])
@login_required
def excluir_pre_separacao(lote_id):
    """
    Exclui pré-separação e retorna parciais HTML atualizados
    """
    try:
        pre_separacoes = PreSeparacaoItem.query.filter_by(
            separacao_lote_id=lote_id,
            status='CRIADO'
        ).all()
        
        if not pre_separacoes:
            return jsonify({
                'ok': False,
                'success': False,
                'error': 'Pré-separação não encontrada'
            }), 404
        
        num_pedido = pre_separacoes[0].num_pedido if pre_separacoes else None
        
        # Excluir todas as pré-separações do lote
        for pre_sep in pre_separacoes:
            db.session.delete(pre_sep)
        
        db.session.commit()
        
        # Verificar se cliente quer parciais HTML
        accept_html = request.headers.get('Accept', '').find('text/html') != -1
        
        if accept_html and num_pedido:
            pedido_atualizado = _get_pedido_completo(num_pedido)
            contadores = _calcular_contadores_globais()
            
            return jsonify({
                'ok': True,
                'success': True,
                'message': 'Pré-separação excluída com sucesso',
                'targets': {
                    f'#resumo-{num_pedido}': render_template('carteira/partials/_resumo_pedido.html', 
                                                            pedido=pedido_atualizado),
                    f'#separacoes-{num_pedido}': render_template('carteira/partials/_separacoes_pedido.html', 
                                                                pedido=pedido_atualizado),
                    f'#botoes-{num_pedido}': render_template('carteira/partials/_botoes_pedido.html', 
                                                            pedido=pedido_atualizado)
                },
                'contadores': contadores
            })
        else:
            return jsonify({
                'success': True,
                'message': f'Pré-separação {lote_id} excluída com sucesso'
            })
        
    except Exception as e:
        logger.error(f"Erro ao excluir pré-separação: {str(e)}")
        db.session.rollback()
        return jsonify({
            'ok': False,
            'success': False,
            'error': str(e)
        }), 500


@carteira_bp.route("/api/separacao/<lote_id>/reverter", methods=["POST"])
@login_required
def reverter_separacao(lote_id):
    """
    API para reverter separação com status ABERTO para pré-separação
    """
    try:
        # Buscar o pedido associado a este lote
        pedido = Pedido.query.filter_by(separacao_lote_id=lote_id).first()

        if not pedido:
            return jsonify({"success": False, "error": "Pedido não encontrado para este lote"}), 404

        # Verificar se o status é ABERTO
        if pedido.status != "ABERTO":
            return (
                jsonify(
                    {
                        "success": False,
                        "error": f"Apenas separações com status ABERTO podem ser revertidas. Status atual: {pedido.status}",
                    }
                ),
                400,
            )

        # Buscar separações com este lote_id
        separacoes = Separacao.query.filter(Separacao.separacao_lote_id == lote_id).all()

        if not separacoes:
            return jsonify({"success": False, "error": "Separações não encontradas"}), 404

        # Buscar pré-separações correspondentes (podem existir de fluxos anteriores)
        pre_separacoes_existentes = PreSeparacaoItem.query.filter(
            PreSeparacaoItem.separacao_lote_id == lote_id, PreSeparacaoItem.status.in_(["ENVIADO_SEPARACAO", "CRIADO"])
        ).all()

        # 1) Deletar as separações primeiro e dar flush para acionar triggers de DELETE
        for sep in separacoes:
            db.session.delete(sep)
        logger.info(f"Removendo {len(separacoes)} separações do lote {lote_id}")

        # Flush para garantir que os triggers de DELETE ajustem MovimentacaoPrevista
        db.session.flush()

        # 2) Criar (ou reativar) pré-separações após remover as separações
        from datetime import datetime

        pre_separacoes_criadas = []
        if not pre_separacoes_existentes or len(pre_separacoes_existentes) == 0:
            logger.info(f"Pré-separações não encontradas para lote {lote_id}, criando novas...")

            # Reconstituir as pré-separações a partir dos dados anteriormente carregados
            for sep in separacoes:
                nova_pre_sep = PreSeparacaoItem(
                    separacao_lote_id=lote_id,
                    num_pedido=sep.num_pedido,
                    cod_produto=sep.cod_produto,
                    nome_produto=sep.nome_produto,
                    cnpj_cliente=sep.cnpj_cpf,
                    qtd_original_carteira=sep.qtd_saldo,
                    qtd_selecionada_usuario=sep.qtd_saldo,
                    qtd_restante_calculada=0,
                    valor_original_item=sep.valor_saldo,
                    peso_original_item=sep.peso,
                    data_expedicao_editada=pedido.expedicao if pedido.expedicao else datetime.now().date(),
                    data_agendamento_editada=pedido.agendamento,
                    protocolo_editado=pedido.protocolo,
                    agendamento_confirmado=sep.agendamento_confirmado if hasattr(sep, 'agendamento_confirmado') else False,
                    tipo_envio=sep.tipo_envio or "total",
                    status="CRIADO",
                    data_criacao=agora_brasil(),
                    criado_por=current_user.nome if current_user.is_authenticated else "Sistema",
                )
                db.session.add(nova_pre_sep)
                pre_separacoes_criadas.append(nova_pre_sep)

            logger.info(f"Criadas {len(pre_separacoes_criadas)} novas pré-separações")
        else:
            # Reverter status das pré-separações existentes
            for pre_sep in pre_separacoes_existentes:
                pre_sep.status = "CRIADO"

        # 3) Remover pedido (cancelar)
        db.session.delete(pedido)
        logger.info(f"Removendo pedido {pedido.num_pedido} com lote {lote_id}")

        db.session.commit()

        # Calcular total de pré-separações de forma correta
        # Se criamos novas pré-separações (separação sem PreSeparacaoItem prévia)
        if pre_separacoes_criadas:
            total_pre = len(pre_separacoes_criadas)
        # Se revertemos pré-separações existentes (status ENVIADO_SEPARACAO → CRIADO)
        elif pre_separacoes_existentes:
            total_pre = len(pre_separacoes_existentes)
        # Fallback: usar quantidade de separações removidas
        else:
            total_pre = len(separacoes)
        
        # Verificar se cliente quer resposta com parciais HTML
        accept_html = request.headers.get('Accept', '').find('text/html') != -1
        num_pedido = separacoes[0].num_pedido if separacoes else None
        
        if accept_html and num_pedido:
            pedido_atualizado = _get_pedido_completo(num_pedido)
            contadores = _calcular_contadores_globais()
            
            return jsonify({
                "ok": True,
                "success": True,
                "message": f"Separação revertida com sucesso! {total_pre} itens voltaram para pré-separação.",
                "targets": {
                    f"#resumo-{num_pedido}": render_template('carteira/partials/_resumo_pedido.html', 
                                                            pedido=pedido_atualizado),
                    f"#separacoes-{num_pedido}": render_template('carteira/partials/_separacoes_pedido.html', 
                                                                pedido=pedido_atualizado),
                    f"#botoes-{num_pedido}": render_template('carteira/partials/_botoes_pedido.html', 
                                                            pedido=pedido_atualizado)
                },
                "contadores": contadores,
                "pre_separacoes_revertidas": total_pre,
                "separacoes_removidas": len(separacoes)
            })
        else:
            return jsonify(
                {
                    "success": True,
                    "message": f"Separação revertida com sucesso! {total_pre} itens voltaram para pré-separação.",
                    "pre_separacoes_revertidas": total_pre,
                    "separacoes_removidas": len(separacoes),
                }
            )

    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao reverter separação {lote_id}: {e}")
        return jsonify({"success": False, "error": f"Erro interno: {str(e)}"}), 500


@carteira_bp.route("/api/separacao/<lote_id>/atualizar-datas", methods=["POST"])
@login_required
def atualizar_datas_separacao(lote_id):
    """
    Atualiza datas de expedição, agendamento e protocolo de uma separação com status ABERTO
    """
    try:
        data = request.get_json()
        data_expedicao = data.get("expedicao")
        data_agendamento = data.get("agendamento")
        protocolo = data.get("protocolo")
        agendamento_confirmado = data.get("agendamento_confirmado", False)

        if not data_expedicao:
            return jsonify({"success": False, "error": "Data de expedição é obrigatória"}), 400

        # Buscar todas as separações do lote PRIMEIRO
        separacoes = Separacao.query.filter(Separacao.separacao_lote_id == lote_id).all()

        if not separacoes:
            return jsonify({"success": False, "error": "Separações não encontradas"}), 404

        # Buscar o pedido associado
        pedido = Pedido.query.filter_by(separacao_lote_id=lote_id).first()

        # Se não existe pedido, criar um baseado nas separações
        if not pedido:
            logger.warning(f"Pedido não encontrado para lote {lote_id}. Criando novo pedido.")

            # Usar primeira separação para dados base
            primeira_sep = separacoes[0]

            # Calcular totais
            valor_total = sum(float(s.valor_saldo or 0) for s in separacoes)
            peso_total = sum(float(s.peso or 0) for s in separacoes)
            pallet_total = sum(float(s.pallet or 0) for s in separacoes)

            # Se rota/sub_rota estão vazias na separação, recalcular
            rota = primeira_sep.rota
            sub_rota = primeira_sep.sub_rota

            if not rota:
                rota = buscar_rota_por_uf(primeira_sep.cod_uf or "")
            if not sub_rota:
                sub_rota = buscar_sub_rota_por_uf_cidade(primeira_sep.cod_uf or "", primeira_sep.nome_cidade or "")

            # Criar novo pedido
            pedido = Pedido(
                separacao_lote_id=lote_id,
                num_pedido=primeira_sep.num_pedido,
                data_pedido=primeira_sep.data_pedido,
                cnpj_cpf=primeira_sep.cnpj_cpf,
                raz_social_red=primeira_sep.raz_social_red,
                nome_cidade=primeira_sep.nome_cidade,
                cod_uf=primeira_sep.cod_uf,
                valor_saldo_total=valor_total,
                pallet_total=pallet_total,
                peso_total=peso_total,
                rota=rota,
                sub_rota=sub_rota,
                observ_ped_1=primeira_sep.observ_ped_1,
                expedicao=primeira_sep.expedicao,
                agendamento=primeira_sep.agendamento,
                protocolo=primeira_sep.protocolo,
                status="ABERTO",
            )
            db.session.add(pedido)

        # Verificar se o status é ABERTO
        if pedido.status != "ABERTO":
            return (
                jsonify(
                    {
                        "success": False,
                        "error": f"Apenas separações com status ABERTO podem ser editadas. Status atual: {pedido.status}",
                    }
                ),
                400,
            )

        # Converter datas
        from datetime import datetime

        data_expedicao_obj = datetime.strptime(data_expedicao, "%Y-%m-%d").date()
        data_agendamento_obj = None
        if data_agendamento:
            data_agendamento_obj = datetime.strptime(data_agendamento, "%Y-%m-%d").date()

        # Atualizar todas as separações do lote
        for sep in separacoes:
            sep.expedicao = data_expedicao_obj
            sep.agendamento = data_agendamento_obj
            sep.protocolo = protocolo
            if hasattr(sep, 'agendamento_confirmado'):
                sep.agendamento_confirmado = agendamento_confirmado

        # Atualizar também o pedido
        pedido.expedicao = data_expedicao_obj
        pedido.agendamento = data_agendamento_obj
        pedido.protocolo = protocolo
        if hasattr(pedido, 'agendamento_confirmado'):
            pedido.agendamento_confirmado = agendamento_confirmado

        db.session.commit()

        # Verificar se cliente quer resposta com parciais HTML
        accept_html = request.headers.get('Accept', '').find('text/html') != -1
        num_pedido = separacoes[0].num_pedido if separacoes else None
        
        if accept_html and num_pedido:
            pedido_atualizado = _get_pedido_completo(num_pedido)
            contadores = _calcular_contadores_globais()
            
            return jsonify({
                "ok": True,
                "success": True,
                "message": f"{len(separacoes)} itens atualizados com sucesso",
                "targets": {
                    f"#resumo-{num_pedido}": render_template('carteira/partials/_resumo_pedido.html', 
                                                            pedido=pedido_atualizado),
                    f"#separacoes-{num_pedido}": render_template('carteira/partials/_separacoes_pedido.html', 
                                                                pedido=pedido_atualizado),
                    f"#botoes-{num_pedido}": render_template('carteira/partials/_botoes_pedido.html', 
                                                            pedido=pedido_atualizado)
                },
                "contadores": contadores,
                "itens_atualizados": len(separacoes)
            })
        else:
            return jsonify(
                {
                    "success": True,
                    "message": f"{len(separacoes)} itens atualizados com sucesso",
                    "itens_atualizados": len(separacoes),
                }
            )

    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao atualizar datas da separação: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

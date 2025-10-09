"""
Rotas para solicitação de agendamento - Etapa 2
Fluxos: Lote, Separação e NF/Monitoramento
"""

from flask import Blueprint, request, jsonify, render_template, send_file
from flask_login import login_required, current_user
from app import db
from app.portal.sendas.service_comparacao_sendas import ComparacaoSendasService
from app.portal.sendas.service_exportacao_sendas import ExportacaoSendasService
from app.portal.sendas.service_verificacao_sendas import VerificacaoSendasService
from app.portal.sendas.models import FilialDeParaSendas, ProdutoDeParaSendas
from app.portal.sendas.models_planilha import PlanilhaModeloSendas
from app.separacao.models import Separacao
from app.monitoramento.models import EntregaMonitorada, AgendamentoEntrega
from datetime import datetime
import logging
from app.faturamento.models import FaturamentoProduto
from sqlalchemy import and_


logger = logging.getLogger(__name__)

bp_solicitacao_sendas = Blueprint('solicitacao_sendas', __name__, url_prefix='/portal/sendas')

# Instância dos services
comparacao_service = ComparacaoSendasService()
exportacao_service = ExportacaoSendasService()
verificacao_service = VerificacaoSendasService()


# =====================================================
# PÁGINAS DE TESTE
# =====================================================

@bp_solicitacao_sendas.route('/teste-etapa2')
@login_required
def teste_etapa2():
    """Página de teste da Etapa 2"""
    return render_template('portal/sendas/teste_etapa2.html')


# =====================================================
# APIs DE STATUS
# =====================================================

@bp_solicitacao_sendas.route('/api/status-planilha')
@login_required
def status_planilha():
    """Retorna status da planilha modelo"""
    total = PlanilhaModeloSendas.query.count()
    ultima = PlanilhaModeloSendas.query.order_by(PlanilhaModeloSendas.created_at.desc()).first()

    return jsonify({
        'total': total,
        'ultima_importacao': ultima.created_at.strftime('%d/%m/%Y %H:%M') if ultima else None
    })


@bp_solicitacao_sendas.route('/api/status-depara-filial')
@login_required
def status_depara_filial():
    """Retorna status do DE-PARA de filiais"""
    total = FilialDeParaSendas.query.count()
    return jsonify({'total': total})


@bp_solicitacao_sendas.route('/api/status-depara-produto')
@login_required
def status_depara_produto():
    """Retorna status do DE-PARA de produtos"""
    total = ProdutoDeParaSendas.query.count()
    return jsonify({'total': total})


# =====================================================
# FLUXO 1 - AGENDAMENTO EM LOTE
# =====================================================

@bp_solicitacao_sendas.route('/solicitar/lote/preparar', methods=['POST'])
@login_required
def preparar_lote_sendas():
    """
    Prepara dados para comparação criando separações do saldo da carteira
    e buscando todas as separações relevantes (não faturadas + NF CD)
    """
    try:
        from app.carteira.routes.programacao_em_lote.busca_dados import (
            criar_separacoes_do_saldo,
            buscar_dados_completos_cnpj
        )
        from app.portal.sendas.utils_protocolo import gerar_protocolo_sendas

        data = request.get_json()
        cnpjs = data.get('cnpjs', [])

        if not cnpjs:
            return jsonify({'sucesso': False, 'erro': 'Nenhum CNPJ selecionado'}), 400

        resultado = {'solicitacoes': []}

        for cnpj_info in cnpjs:
            # ✅ CORREÇÃO: cnpj_info pode ser string ou dict com {cnpj, data_agendamento, data_expedicao}
            if isinstance(cnpj_info, str):
                cnpj = cnpj_info
                # Se não tem datas, usar padrão (D+1 para agendamento, D+0 para expedição)
                data_agendamento = datetime.now().date()
                data_agendamento = data_agendamento.replace(day=data_agendamento.day + 1)
                data_expedicao = datetime.now().date()
            else:
                cnpj = cnpj_info.get('cnpj')
                # ✅ PEGAR DATAS DO FRONTEND (programação em lote)
                data_agendamento = cnpj_info.get('data_agendamento')
                data_expedicao = cnpj_info.get('data_expedicao')

                # Converter strings para date se necessário
                if isinstance(data_agendamento, str):
                    data_agendamento = datetime.strptime(data_agendamento, '%Y-%m-%d').date()
                if isinstance(data_expedicao, str):
                    data_expedicao = datetime.strptime(data_expedicao, '%Y-%m-%d').date()

            if not cnpj:
                continue

            # 1. Gerar protocolo único para este CNPJ
            protocolo = gerar_protocolo_sendas(cnpj, data_agendamento)

            # 2. ✅ CORREÇÃO: Criar separações do saldo COM data_expedicao
            logger.info(f"Criando separações do saldo para CNPJ {cnpj}")
            criar_separacoes_do_saldo(
                cnpj=cnpj,
                data_agendamento=data_agendamento,
                data_expedicao=data_expedicao,  # ✅ ADICIONADO
                protocolo=protocolo
            )

            # 3. ✅ CORREÇÃO: Buscar todos os dados COM data_expedicao e protocolo
            dados = buscar_dados_completos_cnpj(
                cnpj=cnpj,
                data_agendamento=data_agendamento,
                data_expedicao=data_expedicao,  # ✅ ADICIONADO
                protocolo=protocolo  # ✅ ADICIONADO para filtrar apenas as deste agendamento
            )

            # 4. ✅ CORREÇÃO: Converter para formato esperado incluindo separacao_lote_id
            for item in dados['itens']:
                resultado['solicitacoes'].append({
                    'cnpj': cnpj,
                    'pedido_cliente': item.get('pedido_cliente'),
                    'cod_produto': item['cod_produto'],
                    'nome_produto': item.get('nome_produto'),
                    'quantidade': item['quantidade'],
                    'num_pedido': item.get('num_pedido'),
                    'separacao_lote_id': item.get('separacao_lote_id'),  # ✅ ADICIONADO
                    'data_agendamento': str(data_agendamento),
                    'data_expedicao': str(data_expedicao)  # ✅ ADICIONADO
                })

        return jsonify({
            'sucesso': True,
            'solicitacoes': resultado['solicitacoes'],
            'total_itens': len(resultado['solicitacoes'])
        })

    except Exception as e:
        logger.error(f"Erro ao preparar lote Sendas: {e}")
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


@bp_solicitacao_sendas.route('/solicitar/lote/comparar', methods=['POST'])
@login_required
def comparar_lote():
    """
    Compara múltiplas solicitações de agendamento (Fluxo 1 - Lote)
    Usado na programação em lote
    """
    try:
        data = request.get_json()

        if not data or 'solicitacoes' not in data:
            return jsonify({'sucesso': False, 'erro': 'Dados inválidos'}), 400

        # Comparar todas as solicitações
        resultados = comparacao_service.comparar_multiplas_solicitacoes(
            data['solicitacoes']
        )

        return jsonify({
            'sucesso': True,
            'resultados_por_cnpj': resultados
        })

    except Exception as e:
        logger.error(f"Erro ao comparar lote: {e}")
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


@bp_solicitacao_sendas.route('/solicitar/lote/confirmar', methods=['POST'])
@login_required
def confirmar_lote():
    """
    Confirma agendamento em lote após aprovação do usuário
    Grava em FilaAgendamentoSendas e propaga protocolos
    """
    try:
        data = request.get_json()

        if not data or 'itens_confirmados' not in data:
            return jsonify({'sucesso': False, 'erro': 'Dados inválidos'}), 400

        # Agrupar por CNPJ para gerar 1 protocolo por CNPJ
        itens_por_cnpj = {}
        for item in data['itens_confirmados']:
            cnpj = item['cnpj']
            if cnpj not in itens_por_cnpj:
                itens_por_cnpj[cnpj] = []
            itens_por_cnpj[cnpj].append(item)

        protocolos_gerados = {}

        # Processar cada CNPJ
        for cnpj, itens in itens_por_cnpj.items():
            # ✅ VALIDAÇÃO: Verificar se a filial tem dados na planilha modelo

            filial_sendas = FilialDeParaSendas.cnpj_to_filial(cnpj)
            if not filial_sendas:
                logger.warning(f"CNPJ {cnpj} não encontrado no DE-PARA, pulando...")
                continue

            planilha_existe = PlanilhaModeloSendas.query.filter_by(
                unidade_destino=filial_sendas
            ).first()

            if not planilha_existe:
                logger.warning(f"Filial {filial_sendas} não tem dados na planilha modelo, pulando CNPJ {cnpj}...")
                continue

            # Gravar na fila (1 protocolo por CNPJ)
            resultado = comparacao_service.gravar_fila_agendamento(
                itens_confirmados=itens,
                tipo_origem='lote',
                documento_origem=cnpj
            )

            if resultado['sucesso']:
                protocolo = resultado['protocolos'][cnpj]
                protocolos_gerados[cnpj] = protocolo

                # ✅ CORREÇÃO: Agrupar itens por separacao_lote_id para atualizar em lote
                lotes_para_atualizar = {}
                for item in itens:
                    lote_id = item.get('separacao_lote_id')
                    if lote_id:
                        if lote_id not in lotes_para_atualizar:
                            lotes_para_atualizar[lote_id] = item  # Guardar qualquer item do lote para pegar datas
                    else:
                        logger.warning(f"Item sem separacao_lote_id: {item.get('num_pedido')} - {item.get('cod_produto')}")

                # ✅ CORREÇÃO: Atualizar TODAS as separações de cada lote com protocolo e datas
                for lote_id, item_referencia in lotes_para_atualizar.items():
                    # Converter datas de string para date se necessário
                    data_agendamento = item_referencia.get('data_agendamento')
                    data_expedicao = item_referencia.get('data_expedicao')

                    if isinstance(data_agendamento, str):
                        from datetime import datetime as dt
                        data_agendamento = dt.strptime(data_agendamento, '%Y-%m-%d').date()
                    if isinstance(data_expedicao, str):
                        from datetime import datetime as dt
                        data_expedicao = dt.strptime(data_expedicao, '%Y-%m-%d').date()

                    Separacao.query.filter_by(
                        separacao_lote_id=lote_id
                    ).update({
                        'protocolo': protocolo,
                        'agendamento': data_agendamento,  # ✅ PREENCHER com valor real
                        'expedicao': data_expedicao,      # ✅ PREENCHER com valor real
                        'agendamento_confirmado': False   # ✅ False até confirmação do portal
                    })



        db.session.commit()

        return jsonify({
            'sucesso': True,
            'protocolos': protocolos_gerados,
            'mensagem': f'{len(protocolos_gerados)} CNPJ(s) agendado(s) com sucesso'
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao confirmar lote: {e}")
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


# =====================================================
# FLUXO 2 - AGENDAMENTO POR SEPARAÇÃO
# =====================================================

@bp_solicitacao_sendas.route('/solicitar/separacao/comparar', methods=['POST'])
@login_required
def comparar_separacao():
    """
    Compara TODOS os itens de uma separação (Fluxo 2)
    SEMPRE compara múltiplos produtos do mesmo lote
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({'sucesso': False, 'erro': 'Dados inválidos'}), 400

        solicitacoes = []

        # Se fornecido separacao_lote_id, buscar TODOS os itens do lote
        if 'separacao_lote_id' in data:
            # Buscar TODOS os itens da separação com mesmo lote_id
            separacoes = Separacao.query.filter(
                and_(
                    Separacao.separacao_lote_id == data['separacao_lote_id'],
                    Separacao.qtd_saldo > 0  # ✅ FILTRO: apenas qtd > 0
                )
            ).all()

            if not separacoes:
                return jsonify({'sucesso': False, 'erro': 'Separação não encontrada'}), 404

            logger.info(f"Encontrados {len(separacoes)} itens no lote {data['separacao_lote_id']}")

            # Montar lista com TODOS os itens
            for sep in separacoes:
                solicitacoes.append({
                    'cnpj': sep.cnpj_cpf,
                    'pedido_cliente': sep.pedido_cliente,
                    'num_pedido': sep.num_pedido,  # ✅ ADICIONADO: num_pedido obrigatório
                    'cod_produto': sep.cod_produto,
                    'quantidade': float(sep.qtd_saldo) if sep.qtd_saldo else 0,
                    'data_agendamento': data.get('data_agendamento') or (
                        sep.agendamento.strftime('%Y-%m-%d') if sep.agendamento else None
                    )
                })

        # Se fornecidos itens diretamente (para teste ou outros casos)
        elif 'itens' in data:
            solicitacoes = data['itens']

        # Se fornecido apenas um item (converter para lista)
        else:
            solicitacoes = [{
                'cnpj': data.get('cnpj'),
                'pedido_cliente': data.get('pedido_cliente'),
                'cod_produto': data.get('cod_produto'),
                'quantidade': data.get('quantidade'),
                'data_agendamento': data.get('data_agendamento')
            }]

        # Comparar TODOS os itens usando múltiplas solicitações
        resultados = comparacao_service.comparar_multiplas_solicitacoes(solicitacoes)

        # Adicionar separacao_lote_id ao resultado
        if 'separacao_lote_id' in data:
            for cnpj in resultados:
                resultados[cnpj]['separacao_lote_id'] = data['separacao_lote_id']

        return jsonify({
            'sucesso': True,
            'separacao_lote_id': data.get('separacao_lote_id'),
            'resultados_por_cnpj': resultados
        })

    except Exception as e:
        logger.error(f"Erro ao comparar separação: {e}")
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


@bp_solicitacao_sendas.route('/solicitar/separacao/confirmar', methods=['POST'])
@login_required
def confirmar_separacao():
    """
    Confirma agendamento de TODOS os itens de uma separação
    Gera 1 protocolo por separacao_lote_id
    """
    try:
        data = request.get_json()

        if not data or 'itens_confirmados' not in data:
            return jsonify({'sucesso': False, 'erro': 'Dados inválidos - esperando itens_confirmados'}), 400

        itens = data['itens_confirmados']
        separacao_lote_id = data.get('separacao_lote_id')

        if not separacao_lote_id and itens:
            # Tentar pegar o separacao_lote_id do primeiro item
            separacao_lote_id = itens[0].get('separacao_lote_id', 'MANUAL')

        # Gravar na fila - 1 protocolo por separacao_lote_id
        resultado = comparacao_service.gravar_fila_agendamento(
            itens_confirmados=itens,
            tipo_origem='separacao',
            documento_origem=separacao_lote_id
        )

        if resultado['sucesso']:
            # Protocolo único para todo o lote
            protocolo = resultado['protocolos'].get(separacao_lote_id)

            # Propagar protocolo para TODAS as separações do lote
            if separacao_lote_id and separacao_lote_id != 'MANUAL':
                Separacao.query.filter_by(
                    separacao_lote_id=separacao_lote_id
                ).update({
                    'protocolo': protocolo,
                    'agendamento': itens[0]['data_agendamento'] if itens else None
                })
                db.session.commit()

            return jsonify({
                'sucesso': True,
                'protocolo': protocolo,
                'separacao_lote_id': separacao_lote_id,
                'total_itens': len(itens),
                'mensagem': f'Agendamento confirmado para {len(itens)} itens com protocolo {protocolo}'
            })

        return jsonify(resultado)

    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao confirmar separação: {e}")
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


# =====================================================
# FLUXO 3 - AGENDAMENTO POR NF (MONITORAMENTO)
# =====================================================

@bp_solicitacao_sendas.route('/solicitar/nf/comparar', methods=['POST'])
@login_required
def comparar_nf():
    """
    Compara TODOS os produtos de uma NF (Fluxo 3)
    SEMPRE compara múltiplos produtos da mesma NF
    """
    try:
        data = request.get_json()

        if not data or 'numero_nf' not in data:
            return jsonify({'sucesso': False, 'erro': 'Número da NF é obrigatório'}), 400

        numero_nf = data['numero_nf']
        solicitacoes = []

        # Buscar entrega monitorada
        entrega = EntregaMonitorada.query.filter_by(
            numero_nf=numero_nf
        ).first()
        produtos_nf = FaturamentoProduto.query.filter_by(
            numero_nf=numero_nf
        ).all()

        # ========== BUSCAR PEDIDO_CLIENTE COM FALLBACK ==========
        # 1. Primeiro: buscar em Separacao via numero_nf
        pedido_cliente = None
        num_pedido_fallback = None

        separacao_com_nf = Separacao.query.filter_by(
            numero_nf=numero_nf
        ).first()

        if separacao_com_nf and separacao_com_nf.pedido_cliente:
            pedido_cliente = separacao_com_nf.pedido_cliente
            logger.info(f"✅ pedido_cliente encontrado em Separacao para NF {numero_nf}: {pedido_cliente}")
        else:
            # 2. Fallback: usar FaturamentoProduto.origem e buscar no Odoo
            if produtos_nf and produtos_nf[0].origem:
                num_pedido_fallback = produtos_nf[0].origem
                logger.info(f"🔍 Buscando pedido_cliente no Odoo para pedido {num_pedido_fallback}")

                from app.odoo.utils.pedido_cliente_utils import buscar_pedido_cliente_odoo
                pedido_cliente = buscar_pedido_cliente_odoo(num_pedido_fallback)

                if pedido_cliente:
                    logger.info(f"✅ pedido_cliente encontrado no Odoo: {pedido_cliente}")
                else:
                    logger.warning(f"⚠️ pedido_cliente não encontrado no Odoo para {num_pedido_fallback}")
        # ==========================================================

        if not entrega:
            # Se não encontrou no monitoramento, tentar buscar no faturamento

            if not produtos_nf:
                return jsonify({'sucesso': False, 'erro': 'NF não encontrada'}), 404

            # Montar lista com todos os produtos da NF
            cnpj_cliente = produtos_nf[0].cnpj_cliente if produtos_nf else None
            for produto in produtos_nf:
                # ✅ FILTRO: apenas produtos com quantidade > 0
                if produto.qtd_produto_faturado and produto.qtd_produto_faturado > 0:
                    solicitacoes.append({
                        'cnpj': produto.cnpj_cliente,
                        'pedido_cliente': pedido_cliente,  # ✅ Usando pedido_cliente encontrado
                        'num_pedido': produto.origem,  # ✅ ADICIONADO: usando origem como num_pedido
                        'cod_produto': produto.cod_produto,
                        'quantidade': float(produto.qtd_produto_faturado),
                        'data_agendamento': data.get('data_agendamento')
                    })
        else:
            # Usar dados da entrega monitorada
            # Buscar produtos detalhados da NF se disponível
            if produtos_nf:
                cnpj_cliente = entrega.cnpj_cliente
                for produto in produtos_nf:
                    # ✅ FILTRO: apenas produtos com quantidade > 0
                    if produto.qtd_produto_faturado and produto.qtd_produto_faturado > 0:
                        solicitacoes.append({
                            'cnpj': cnpj_cliente,
                            'pedido_cliente': pedido_cliente,  # ✅ Usando pedido_cliente encontrado
                            'num_pedido': produto.origem,  # ✅ ADICIONADO: usando origem como num_pedido
                            'cod_produto': produto.cod_produto,
                            'quantidade': float(produto.qtd_produto_faturado),
                            'data_agendamento': data.get('data_agendamento')
                        })
            else:
                # Se não tem produtos detalhados, criar solicitação genérica
                solicitacoes.append({
                    'cnpj': entrega.cnpj_cliente,
                    'pedido_cliente': pedido_cliente,  # ✅ Usando pedido_cliente encontrado
                    'num_pedido': num_pedido_fallback,  # ✅ Usando fallback se disponível
                    'cod_produto': data.get('cod_produto'),
                    'quantidade': float(entrega.peso) if entrega.peso else 0,
                    'data_agendamento': data.get('data_agendamento')
                })
                cnpj_cliente = entrega.cnpj_cliente

        # Se ainda temos produtos fornecidos diretamente (override manual)
        if 'produtos' in data:
            solicitacoes = []
            for prod in data['produtos']:
                solicitacoes.append({
                    'cnpj': cnpj_cliente,
                    'pedido_cliente': prod.get('pedido_cliente') or pedido_cliente,
                    'num_pedido': prod.get('num_pedido') or num_pedido_fallback,
                    'cod_produto': prod.get('cod_produto'),
                    'quantidade': prod.get('quantidade', 0),
                    'data_agendamento': data.get('data_agendamento')
                })

        # Comparar TODOS os produtos usando múltiplas solicitações
        resultados = comparacao_service.comparar_multiplas_solicitacoes(solicitacoes)

        # Adicionar dados da NF ao resultado
        for cnpj in resultados:
            resultados[cnpj]['numero_nf'] = numero_nf
            if entrega:
                resultados[cnpj]['entrega_id'] = entrega.id

        return jsonify({
            'sucesso': True,
            'numero_nf': numero_nf,
            'resultados_por_cnpj': resultados
        })

    except Exception as e:
        logger.error(f"Erro ao comparar NF: {e}")
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


@bp_solicitacao_sendas.route('/solicitar/nf/confirmar', methods=['POST'])
@login_required
def confirmar_nf():
    """
    Confirma agendamento de TODOS os produtos de uma NF
    Gera 1 protocolo por NF
    """
    try:
        data = request.get_json()

        if not data or 'itens_confirmados' not in data:
            return jsonify({'sucesso': False, 'erro': 'Dados inválidos - esperando itens_confirmados'}), 400

        itens = data['itens_confirmados']
        numero_nf = data.get('numero_nf')

        if not numero_nf and itens:
            # Tentar pegar o numero_nf do primeiro item
            numero_nf = itens[0].get('numero_nf')

        if not numero_nf:
            return jsonify({'sucesso': False, 'erro': 'Número da NF é obrigatório'}), 400

        # Gravar na fila - 1 protocolo por NF
        resultado = comparacao_service.gravar_fila_agendamento(
            itens_confirmados=itens,
            tipo_origem='nf',
            documento_origem=numero_nf
        )

        if resultado['sucesso']:
            # Protocolo único para toda a NF
            protocolo = resultado['protocolos'].get(numero_nf)

            # Criar AgendamentoEntrega se tiver entrega_id
            entrega_id = data.get('entrega_id') or (itens[0].get('entrega_id') if itens else None)
            if entrega_id:
                # Converter string de data para objeto date se necessário
                data_agendamento = itens[0]['data_agendamento'] if itens else None
                if isinstance(data_agendamento, str):
                    from datetime import datetime
                    data_agendamento = datetime.strptime(data_agendamento, '%Y-%m-%d').date()

                novo_agendamento = AgendamentoEntrega(
                    entrega_id=entrega_id,
                    data_agendada=data_agendamento,  # ✅ CORRIGIDO: campo correto
                    protocolo_agendamento=protocolo,
                    status='confirmado',
                    forma_agendamento='Portal',  # ✅ ADICIONADO: forma de agendamento
                    contato_agendamento='Sistema Sendas',  # ✅ ADICIONADO: contato
                    motivo='Agendamento via integração Portal Sendas',  # ✅ ADICIONADO: motivo
                    autor=current_user.nome if hasattr(current_user, 'nome') else 'Sistema'  # ✅ CORRIGIDO: campo correto
                )
                db.session.add(novo_agendamento)
                db.session.commit()

            return jsonify({
                'sucesso': True,
                'protocolo': protocolo,
                'numero_nf': numero_nf,
                'total_itens': len(itens),
                'mensagem': f'Agendamento da NF {numero_nf} confirmado com protocolo {protocolo}'
            })

        return jsonify(resultado)

    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao confirmar NF: {e}")
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


# =====================================================
# ROTA AUXILIAR - BUSCAR ALTERNATIVAS DE FILIAL
# =====================================================

@bp_solicitacao_sendas.route('/solicitar/buscar-alternativas-filial', methods=['POST'])
@login_required
def buscar_alternativas_filial():
    """
    Busca todas as opções disponíveis de uma filial
    Usado quando o pedido solicitado não existe mas a filial tem outros produtos
    """
    try:
        data = request.get_json()

        if not data or 'cnpj' not in data:
            return jsonify({'sucesso': False, 'erro': 'CNPJ é obrigatório'}), 400

        # Converter CNPJ para unidade destino
        from app.portal.sendas.models import FilialDeParaSendas
        unidade_destino = FilialDeParaSendas.cnpj_to_filial(data['cnpj'])

        if not unidade_destino:
            return jsonify({'sucesso': False, 'erro': 'CNPJ não encontrado no DE-PARA'}), 404

        # Buscar todos os itens da filial
        from app.portal.sendas.models_planilha import PlanilhaModeloSendas
        itens = PlanilhaModeloSendas.query.filter_by(
            unidade_destino=unidade_destino
        ).filter(
            PlanilhaModeloSendas.saldo_disponivel > 0
        ).all()

        # Agrupar por pedido
        pedidos = {}
        for item in itens:
            pedido = item.codigo_pedido_cliente.split('-')[0]
            if pedido not in pedidos:
                pedidos[pedido] = []

            pedidos[pedido].append({
                'codigo_produto': item.codigo_produto_cliente,
                'descricao': item.descricao_item,
                'saldo': float(item.saldo_disponivel),
                'unidade': item.unidade_medida
            })

        return jsonify({
            'sucesso': True,
            'unidade_destino': unidade_destino,
            'total_pedidos': len(pedidos),
            'pedidos': pedidos
        })

    except Exception as e:
        logger.error(f"Erro ao buscar alternativas: {e}")
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


# =====================================================
# ETAPA 3 - EXPORTAÇÃO DE PLANILHA
# =====================================================

@bp_solicitacao_sendas.route('/exportacao')
@login_required
def listar_exportacoes():
    """Página para listar e exportar planilhas"""
    return render_template('portal/sendas/exportacao.html')


@bp_solicitacao_sendas.route('/api/exportacoes/listar')
@login_required
def api_listar_exportacoes():
    """API para listar exportações disponíveis"""
    try:
        exportacoes = exportacao_service.listar_exportacoes_disponiveis()
        return jsonify({
            'sucesso': True,
            'exportacoes': exportacoes,
            'total': len(exportacoes)
        })
    except Exception as e:
        logger.error(f"Erro ao listar exportações: {e}")
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


@bp_solicitacao_sendas.route('/api/exportacao/baixar/<protocolo>')
@login_required
def baixar_exportacao(protocolo):
    """Baixa planilha Excel para um protocolo específico"""
    try:
        import io

        # Exportar planilha
        sucesso, mensagem, arquivo_bytes = exportacao_service.exportar_planilha(
            protocolo=protocolo
        )

        if not sucesso:
            return jsonify({'sucesso': False, 'erro': mensagem}), 400

        # Criar nome do arquivo
        data_hora = datetime.now().strftime('%Y%m%d_%H%M%S')
        nome_arquivo = f'agendamento_sendas_{protocolo}_{data_hora}.xlsx'

        # Enviar arquivo
        return send_file(
            io.BytesIO(arquivo_bytes),
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=nome_arquivo
        )

    except Exception as e:
        logger.error(f"Erro ao baixar exportação: {e}")
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


@bp_solicitacao_sendas.route('/api/exportacao/baixar-todos')
@login_required
def baixar_todas_exportacoes():
    """
    ✅ CORREÇÃO PROBLEMA 4: Baixa planilha Excel com TODOS os agendamentos pendentes
    Acumula todos os protocolos pendentes em uma única planilha
    """
    try:
        import io

        # Exportar TODOS os protocolos pendentes
        sucesso, mensagem, arquivo_bytes = exportacao_service.exportar_planilha(
            protocolo=None  # None = exportar todos
        )

        if not sucesso:
            return jsonify({'sucesso': False, 'erro': mensagem}), 400

        # Criar nome do arquivo
        data_hora = datetime.now().strftime('%Y%m%d_%H%M%S')
        nome_arquivo = f'agendamento_sendas_TODOS_{data_hora}.xlsx'

        # Enviar arquivo
        return send_file(
            io.BytesIO(arquivo_bytes),
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=nome_arquivo
        )

    except Exception as e:
        logger.error(f"Erro ao baixar todas as exportações: {e}")
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


@bp_solicitacao_sendas.route('/api/exportacao/reprocessar', methods=['POST'])
@login_required
def reprocessar_exportacao():
    """Reprocessa uma exportação marcando como pendente novamente"""
    try:
        data = request.get_json()

        if not data or 'protocolo' not in data:
            return jsonify({'sucesso': False, 'erro': 'Protocolo é obrigatório'}), 400

        sucesso = exportacao_service.reprocessar_exportacao(data['protocolo'])

        if sucesso:
            return jsonify({
                'sucesso': True,
                'mensagem': f"Protocolo {data['protocolo']} marcado para reprocessamento"
            })
        else:
            return jsonify({
                'sucesso': False,
                'erro': 'Erro ao reprocessar exportação'
            }), 500

    except Exception as e:
        logger.error(f"Erro ao reprocessar: {e}")
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


# =====================================================
# ETAPA 4 - VERIFICAÇÃO DE AGENDAMENTOS
# =====================================================

@bp_solicitacao_sendas.route('/verificacao')
@login_required
def verificacao_agendamentos():
    """Página para verificação de agendamentos"""
    return render_template('portal/sendas/verificacao.html')


@bp_solicitacao_sendas.route('/api/verificacao/processar', methods=['POST'])
@login_required
def processar_verificacao():
    """Processa planilha de verificação do Portal Sendas"""
    try:
        # Verificar se arquivo foi enviado
        if 'file' not in request.files:
            return jsonify({'sucesso': False, 'erro': 'Nenhum arquivo enviado'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'sucesso': False, 'erro': 'Arquivo vazio'}), 400

        # Verificar extensão
        if not file.filename.lower().endswith(('.xlsx', '.xls')):
            return jsonify({'sucesso': False, 'erro': 'Arquivo deve ser Excel (.xlsx ou .xls)'}), 400

        # Processar arquivo
        arquivo_bytes = file.read()
        resultado = verificacao_service.processar_planilha_verificacao(arquivo_bytes)

        return jsonify(resultado)

    except Exception as e:
        logger.error(f"Erro ao processar verificação: {e}")
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


@bp_solicitacao_sendas.route('/api/verificacao/reenviar', methods=['POST'])
@login_required
def reenviar_nao_encontrados():
    """Reenviar agendamentos não encontrados para fila"""
    try:
        data = request.get_json()

        if not data or 'protocolos' not in data:
            return jsonify({'sucesso': False, 'erro': 'Lista de protocolos é obrigatória'}), 400

        resultado = verificacao_service.reenviar_nao_encontrados(data['protocolos'])
        return jsonify(resultado)

    except Exception as e:
        logger.error(f"Erro ao reenviar agendamentos: {e}")
        return jsonify({'sucesso': False, 'erro': str(e)}), 500


@bp_solicitacao_sendas.route('/api/verificacao/atualizar-datas', methods=['POST'])
@login_required
def atualizar_datas_divergentes():
    """Atualiza datas divergentes após confirmação do usuário"""
    try:
        data = request.get_json()

        if not data or 'atualizacoes' not in data:
            return jsonify({'sucesso': False, 'erro': 'Lista de atualizações é obrigatória'}), 400

        resultado = verificacao_service.atualizar_datas_divergentes(data['atualizacoes'])
        return jsonify(resultado)

    except Exception as e:
        logger.error(f"Erro ao atualizar datas: {e}")
        return jsonify({'sucesso': False, 'erro': str(e)}), 500
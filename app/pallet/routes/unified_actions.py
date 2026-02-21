"""
Routes POST da Tela Unificada de Pallets V3 — Acoes

Todos os endpoints recebem JSON e retornam JSON padronizado:
{
    "sucesso": bool,
    "mensagem": str,
    "dados": {...}
}

Cada endpoint e um wrapper fino que delega para services existentes.
NENHUM service existente foi modificado — reutilizacao 100%.
"""
import logging
from datetime import datetime

from flask import Blueprint, request, jsonify

from app.pallet.services.credito_service import CreditoService
from app.pallet.services.nf_service import NFService
from app.pallet.services.solucao_pallet_service import SolucaoPalletService
from app.pallet.services.match_service import MatchService
from app.pallet.services.sync_odoo_service import PalletSyncService

logger = logging.getLogger(__name__)

unified_actions_bp = Blueprint('unified_actions', __name__, url_prefix='/api/acoes')


def _get_usuario():
    """Obtem usuario da sessao Flask (ou 'SISTEMA' como fallback)."""
    from flask import session
    return session.get('usuario', session.get('user_name', 'SISTEMA'))


def _parse_date(date_str):
    """Converte string de data (YYYY-MM-DD) para date ou None."""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return None


# =========================================================================
# DOMINIO A: SOLUCOES DE CREDITO
# =========================================================================

@unified_actions_bp.route('/baixa', methods=['POST'])
def acao_baixa():
    """
    Registra baixa (descarte) de pallets.

    JSON esperado:
    {
        "credito_id": int,
        "quantidade": int,
        "motivo": str,
        "confirmado_cliente": bool,
        "observacao": str (opcional)
    }
    """
    dados = request.get_json(silent=True)
    if not dados:
        return jsonify({'sucesso': False, 'mensagem': 'JSON invalido'}), 400

    credito_id = dados.get('credito_id')
    quantidade = dados.get('quantidade')
    motivo = dados.get('motivo', '').strip()
    confirmado = dados.get('confirmado_cliente', False)
    observacao = dados.get('observacao')
    usuario = _get_usuario()

    if not credito_id or not quantidade or not motivo:
        return jsonify({
            'sucesso': False,
            'mensagem': 'Campos obrigatorios: credito_id, quantidade, motivo'
        }), 400

    try:
        solucao, credito = SolucaoPalletService.registrar_baixa(
            credito_id=credito_id,
            quantidade=quantidade,
            motivo=motivo,
            usuario=usuario,
            confirmado_cliente=confirmado,
            observacao=observacao
        )

        return jsonify({
            'sucesso': True,
            'mensagem': f'Baixa de {quantidade} pallet(s) registrada',
            'dados': {
                'solucao_id': solucao.id,
                'credito_id': credito.id,
                'novo_saldo': credito.qtd_saldo,
                'novo_status': credito.status,
                'nf_remessa_id': credito.nf_remessa_id,
            }
        })

    except ValueError as e:
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 400
    except Exception as e:
        logger.error(f"Erro ao registrar baixa: {e}")
        return jsonify({'sucesso': False, 'mensagem': 'Erro interno ao registrar baixa'}), 500


@unified_actions_bp.route('/venda', methods=['POST'])
def acao_venda():
    """
    Registra venda de pallets (N creditos → 1 NF venda).

    JSON esperado:
    {
        "nf_venda": str,
        "creditos": [{"credito_id": int, "quantidade": int}, ...],
        "data_venda": "YYYY-MM-DD",
        "valor_unitario": float,
        "cnpj_comprador": str,
        "nome_comprador": str,
        "chave_nfe": str (opcional),
        "observacao": str (opcional)
    }
    """
    dados = request.get_json(silent=True)
    if not dados:
        return jsonify({'sucesso': False, 'mensagem': 'JSON invalido'}), 400

    nf_venda = dados.get('nf_venda', '').strip()
    creditos = dados.get('creditos', [])
    data_venda = _parse_date(dados.get('data_venda'))
    valor_unitario = dados.get('valor_unitario', 0)
    cnpj_comprador = dados.get('cnpj_comprador', '').strip()
    nome_comprador = dados.get('nome_comprador', '').strip()
    chave_nfe = dados.get('chave_nfe')
    observacao = dados.get('observacao')
    usuario = _get_usuario()

    if not nf_venda or not creditos or not cnpj_comprador:
        return jsonify({
            'sucesso': False,
            'mensagem': 'Campos obrigatorios: nf_venda, creditos, cnpj_comprador'
        }), 400

    try:
        resultado = SolucaoPalletService.registrar_venda(
            nf_venda=nf_venda,
            creditos_quantidades=creditos,
            data_venda=data_venda,
            valor_unitario=valor_unitario,
            cnpj_comprador=cnpj_comprador,
            nome_comprador=nome_comprador,
            usuario=usuario,
            chave_nfe=chave_nfe,
            observacao=observacao
        )

        return jsonify({
            'sucesso': True,
            'mensagem': f'Venda NF {nf_venda} registrada ({resultado["quantidade_total"]} pallets)',
            'dados': resultado
        })

    except ValueError as e:
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 400
    except Exception as e:
        logger.error(f"Erro ao registrar venda: {e}")
        return jsonify({'sucesso': False, 'mensagem': 'Erro interno ao registrar venda'}), 500


@unified_actions_bp.route('/recebimento', methods=['POST'])
def acao_recebimento():
    """
    Registra recebimento fisico de pallets (coleta).

    JSON esperado:
    {
        "credito_id": int,
        "quantidade": int,
        "data_recebimento": "YYYY-MM-DD",
        "local_recebimento": str,
        "recebido_de": str (opcional),
        "cnpj_entregador": str (opcional),
        "observacao": str (opcional)
    }
    """
    dados = request.get_json(silent=True)
    if not dados:
        return jsonify({'sucesso': False, 'mensagem': 'JSON invalido'}), 400

    credito_id = dados.get('credito_id')
    quantidade = dados.get('quantidade')
    data_recebimento = _parse_date(dados.get('data_recebimento'))
    local = dados.get('local_recebimento', '').strip()
    recebido_de = dados.get('recebido_de', '')
    cnpj_entregador = dados.get('cnpj_entregador', '')
    observacao = dados.get('observacao')
    usuario = _get_usuario()

    if not credito_id or not quantidade or not local:
        return jsonify({
            'sucesso': False,
            'mensagem': 'Campos obrigatorios: credito_id, quantidade, local_recebimento'
        }), 400

    try:
        solucao, credito = SolucaoPalletService.registrar_recebimento(
            credito_id=credito_id,
            quantidade=quantidade,
            data_recebimento=data_recebimento,
            local_recebimento=local,
            recebido_de=recebido_de,
            cnpj_entregador=cnpj_entregador,
            usuario=usuario,
            observacao=observacao
        )

        return jsonify({
            'sucesso': True,
            'mensagem': f'Recebimento de {quantidade} pallet(s) registrado',
            'dados': {
                'solucao_id': solucao.id,
                'credito_id': credito.id,
                'novo_saldo': credito.qtd_saldo,
                'novo_status': credito.status,
                'nf_remessa_id': credito.nf_remessa_id,
            }
        })

    except ValueError as e:
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 400
    except Exception as e:
        logger.error(f"Erro ao registrar recebimento: {e}")
        return jsonify({'sucesso': False, 'mensagem': 'Erro interno ao registrar recebimento'}), 500


@unified_actions_bp.route('/substituicao', methods=['POST'])
def acao_substituicao():
    """
    Registra substituicao de responsabilidade.

    JSON esperado:
    {
        "credito_origem_id": int,
        "credito_destino_id": int,
        "quantidade": int,
        "motivo": str,
        "nf_destino": str (opcional),
        "observacao": str (opcional)
    }
    """
    dados = request.get_json(silent=True)
    if not dados:
        return jsonify({'sucesso': False, 'mensagem': 'JSON invalido'}), 400

    credito_origem_id = dados.get('credito_origem_id')
    credito_destino_id = dados.get('credito_destino_id')
    quantidade = dados.get('quantidade')
    motivo = dados.get('motivo', '').strip()
    nf_destino = dados.get('nf_destino')
    observacao = dados.get('observacao')
    usuario = _get_usuario()

    if not credito_origem_id or not credito_destino_id or not quantidade or not motivo:
        return jsonify({
            'sucesso': False,
            'mensagem': 'Campos obrigatorios: credito_origem_id, credito_destino_id, quantidade, motivo'
        }), 400

    try:
        resultado = SolucaoPalletService.registrar_substituicao(
            credito_origem_id=credito_origem_id,
            credito_destino_id=credito_destino_id,
            quantidade=quantidade,
            motivo=motivo,
            usuario=usuario,
            nf_destino=nf_destino,
            observacao=observacao
        )

        return jsonify({
            'sucesso': True,
            'mensagem': f'Substituicao de {quantidade} pallet(s) registrada',
            'dados': resultado
        })

    except ValueError as e:
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 400
    except Exception as e:
        logger.error(f"Erro ao registrar substituicao: {e}")
        return jsonify({'sucesso': False, 'mensagem': 'Erro interno ao registrar substituicao'}), 500


# =========================================================================
# DOCUMENTOS
# =========================================================================

@unified_actions_bp.route('/documento', methods=['POST'])
def acao_documento():
    """
    Registra documento que enriquece credito (canhoto ou vale pallet).

    JSON esperado:
    {
        "credito_id": int,
        "tipo": "CANHOTO" | "VALE_PALLET",
        "quantidade": int,
        "numero_documento": str (opcional),
        "data_emissao": "YYYY-MM-DD" (opcional),
        "data_validade": "YYYY-MM-DD" (opcional),
        "cnpj_emissor": str (opcional),
        "nome_emissor": str (opcional),
        "observacao": str (opcional)
    }
    """
    dados = request.get_json(silent=True)
    if not dados:
        return jsonify({'sucesso': False, 'mensagem': 'JSON invalido'}), 400

    credito_id = dados.get('credito_id')
    tipo = dados.get('tipo', '').strip().upper()
    quantidade = dados.get('quantidade')
    usuario = _get_usuario()

    if not credito_id or not tipo or not quantidade:
        return jsonify({
            'sucesso': False,
            'mensagem': 'Campos obrigatorios: credito_id, tipo, quantidade'
        }), 400

    try:
        documento = CreditoService.registrar_documento(
            credito_id=credito_id,
            tipo=tipo,
            quantidade=quantidade,
            usuario=usuario,
            numero_documento=dados.get('numero_documento'),
            data_emissao=_parse_date(dados.get('data_emissao')),
            data_validade=_parse_date(dados.get('data_validade')),
            cnpj_emissor=dados.get('cnpj_emissor'),
            nome_emissor=dados.get('nome_emissor'),
            observacao=dados.get('observacao')
        )

        return jsonify({
            'sucesso': True,
            'mensagem': f'Documento {tipo} registrado com sucesso',
            'dados': {
                'documento_id': documento.id,
                'credito_id': credito_id,
            }
        })

    except ValueError as e:
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 400
    except Exception as e:
        logger.error(f"Erro ao registrar documento: {e}")
        return jsonify({'sucesso': False, 'mensagem': 'Erro interno ao registrar documento'}), 500


@unified_actions_bp.route('/documento/<int:documento_id>/receber', methods=['POST'])
def acao_receber_documento(documento_id):
    """
    Marca documento como recebido pela Nacom (acao inline, 1 click).

    JSON esperado (opcional):
    {
        "pasta_arquivo": str (opcional),
        "aba_arquivo": str (opcional)
    }
    """
    dados = request.get_json(silent=True) or {}
    usuario = _get_usuario()

    try:
        documento = CreditoService.registrar_recebimento_documento(
            documento_id=documento_id,
            usuario=usuario,
            pasta_arquivo=dados.get('pasta_arquivo'),
            aba_arquivo=dados.get('aba_arquivo')
        )

        return jsonify({
            'sucesso': True,
            'mensagem': f'Documento #{documento_id} marcado como recebido',
            'dados': {
                'documento_id': documento.id,
                'credito_id': documento.credito_id,
            }
        })

    except ValueError as e:
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 400
    except Exception as e:
        logger.error(f"Erro ao receber documento #{documento_id}: {e}")
        return jsonify({'sucesso': False, 'mensagem': 'Erro interno ao receber documento'}), 500


# =========================================================================
# DOMINIO B: TRATATIVA NF
# =========================================================================

@unified_actions_bp.route('/vincular-devolucao', methods=['POST'])
def acao_vincular_devolucao():
    """
    Vincula NF de devolucao a multiplas NFs de remessa (1:N).

    JSON esperado:
    {
        "nf_devolucao": {
            "numero_nf": str,
            "serie": str (opcional),
            "chave_nfe": str (opcional),
            "data_nf": "YYYY-MM-DD",
            "cnpj_emitente": str,
            "nome_emitente": str,
            "quantidade": int
        },
        "vinculacoes": {
            "<nf_remessa_id>": <quantidade>,
            ...
        }
    }
    """
    dados = request.get_json(silent=True)
    if not dados:
        return jsonify({'sucesso': False, 'mensagem': 'JSON invalido'}), 400

    nf_devolucao = dados.get('nf_devolucao', {})
    vinculacoes = dados.get('vinculacoes', {})
    usuario = _get_usuario()

    if not nf_devolucao or not vinculacoes:
        return jsonify({
            'sucesso': False,
            'mensagem': 'Campos obrigatorios: nf_devolucao, vinculacoes'
        }), 400

    try:
        # Converter chaves de vinculacoes para int
        quantidades = {int(k): int(v) for k, v in vinculacoes.items()}
        nf_remessa_ids = list(quantidades.keys())

        # Converter data
        if nf_devolucao.get('data_nf'):
            nf_devolucao['data_nf'] = _parse_date(nf_devolucao['data_nf'])

        match_service = MatchService()
        solucoes = match_service.vincular_devolucao_manual_multiplas(
            nf_remessa_ids=nf_remessa_ids,
            nf_devolucao=nf_devolucao,
            quantidades=quantidades,
            usuario=usuario
        )

        return jsonify({
            'sucesso': True,
            'mensagem': f'Devolucao vinculada a {len(solucoes)} NF(s) de remessa',
            'dados': {
                'solucoes_criadas': len(solucoes),
                'nf_remessa_ids': nf_remessa_ids,
            }
        })

    except ValueError as e:
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 400
    except Exception as e:
        logger.error(f"Erro ao vincular devolucao: {e}")
        return jsonify({'sucesso': False, 'mensagem': 'Erro interno ao vincular devolucao'}), 500


@unified_actions_bp.route('/registrar-recusa', methods=['POST'])
def acao_registrar_recusa():
    """
    Registra recusa de NF de remessa.

    JSON esperado:
    {
        "nf_remessa_id": int,
        "quantidade": int,
        "motivo_recusa": str,
        "observacao": str (opcional)
    }
    """
    dados = request.get_json(silent=True)
    if not dados:
        return jsonify({'sucesso': False, 'mensagem': 'JSON invalido'}), 400

    nf_remessa_id = dados.get('nf_remessa_id')
    quantidade = dados.get('quantidade')
    motivo = dados.get('motivo_recusa', '').strip()
    observacao = dados.get('observacao')
    usuario = _get_usuario()

    if not nf_remessa_id or not quantidade or not motivo:
        return jsonify({
            'sucesso': False,
            'mensagem': 'Campos obrigatorios: nf_remessa_id, quantidade, motivo_recusa'
        }), 400

    try:
        solucao = NFService.registrar_solucao_nf(
            nf_remessa_id=nf_remessa_id,
            tipo='RECUSA',
            quantidade=quantidade,
            dados={
                'motivo_recusa': motivo,
                'observacao': observacao
            },
            usuario=usuario
        )

        return jsonify({
            'sucesso': True,
            'mensagem': f'Recusa de {quantidade} pallet(s) registrada',
            'dados': {
                'solucao_id': solucao.id,
                'nf_remessa_id': nf_remessa_id,
            }
        })

    except ValueError as e:
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 400
    except Exception as e:
        logger.error(f"Erro ao registrar recusa: {e}")
        return jsonify({'sucesso': False, 'mensagem': 'Erro interno ao registrar recusa'}), 500


# =========================================================================
# SUGESTOES (CONFIRMAR / REJEITAR)
# =========================================================================

@unified_actions_bp.route('/confirmar-sugestao/<int:solucao_id>', methods=['POST'])
def acao_confirmar_sugestao(solucao_id):
    """Confirma uma sugestao de vinculacao (acao inline, 1 click)."""
    usuario = _get_usuario()

    try:
        solucao = NFService.confirmar_sugestao(
            nf_solucao_id=solucao_id,
            usuario=usuario
        )

        return jsonify({
            'sucesso': True,
            'mensagem': f'Sugestao #{solucao_id} confirmada',
            'dados': {
                'solucao_id': solucao.id,
                'nf_remessa_id': solucao.nf_remessa_id,
            }
        })

    except ValueError as e:
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 400
    except Exception as e:
        logger.error(f"Erro ao confirmar sugestao #{solucao_id}: {e}")
        return jsonify({'sucesso': False, 'mensagem': 'Erro interno ao confirmar sugestao'}), 500


@unified_actions_bp.route('/rejeitar-sugestao/<int:solucao_id>', methods=['POST'])
def acao_rejeitar_sugestao(solucao_id):
    """
    Rejeita uma sugestao de vinculacao.

    JSON esperado:
    {
        "motivo": str
    }
    """
    dados = request.get_json(silent=True)
    if not dados:
        return jsonify({'sucesso': False, 'mensagem': 'JSON invalido'}), 400

    motivo = dados.get('motivo', '').strip()
    usuario = _get_usuario()

    if not motivo:
        return jsonify({
            'sucesso': False,
            'mensagem': 'Motivo da rejeicao e obrigatorio'
        }), 400

    try:
        solucao = NFService.rejeitar_sugestao(
            nf_solucao_id=solucao_id,
            motivo=motivo,
            usuario=usuario
        )

        return jsonify({
            'sucesso': True,
            'mensagem': f'Sugestao #{solucao_id} rejeitada',
            'dados': {
                'solucao_id': solucao.id,
                'nf_remessa_id': solucao.nf_remessa_id,
            }
        })

    except ValueError as e:
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 400
    except Exception as e:
        logger.error(f"Erro ao rejeitar sugestao #{solucao_id}: {e}")
        return jsonify({'sucesso': False, 'mensagem': 'Erro interno ao rejeitar sugestao'}), 500


# =========================================================================
# CANCELAR NF
# =========================================================================

@unified_actions_bp.route('/cancelar-nf/<int:nf_id>', methods=['POST'])
def acao_cancelar_nf(nf_id):
    """
    Cancela uma NF de remessa (acao destrutiva).

    JSON esperado:
    {
        "motivo": str
    }
    """
    dados = request.get_json(silent=True)
    if not dados:
        return jsonify({'sucesso': False, 'mensagem': 'JSON invalido'}), 400

    motivo = dados.get('motivo', '').strip()
    usuario = _get_usuario()

    if not motivo:
        return jsonify({
            'sucesso': False,
            'mensagem': 'Motivo do cancelamento e obrigatorio'
        }), 400

    try:
        nf = NFService.cancelar_nf(
            nf_remessa_id=nf_id,
            motivo=motivo,
            usuario=usuario
        )

        return jsonify({
            'sucesso': True,
            'mensagem': f'NF #{nf_id} cancelada com sucesso',
            'dados': {
                'nf_remessa_id': nf.id,
                'novo_status': nf.status,
            }
        })

    except ValueError as e:
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 400
    except Exception as e:
        logger.error(f"Erro ao cancelar NF #{nf_id}: {e}")
        return jsonify({'sucesso': False, 'mensagem': 'Erro interno ao cancelar NF'}), 500


# =========================================================================
# SINCRONIZACAO ODOO + PROCESSAR DFe
# =========================================================================

@unified_actions_bp.route('/sync-odoo', methods=['POST'])
def acao_sync_odoo():
    """
    Sincroniza NFs de remessa do Odoo.

    JSON esperado (opcional):
    {
        "dias_retroativos": int (default 30)
    }
    """
    dados = request.get_json(silent=True) or {}
    dias = dados.get('dias_retroativos', 30)

    try:
        sync_service = PalletSyncService()
        resultado = sync_service.sincronizar_remessas(dias_retroativos=dias)

        return jsonify({
            'sucesso': True,
            'mensagem': f'Sincronizacao concluida: {resultado.get("importadas", 0)} importada(s)',
            'dados': resultado
        })

    except Exception as e:
        logger.error(f"Erro ao sincronizar Odoo: {e}")
        return jsonify({'sucesso': False, 'mensagem': f'Erro ao sincronizar: {str(e)}'}), 500


@unified_actions_bp.route('/processar-dfe', methods=['POST'])
def acao_processar_dfe():
    """
    Processa NFs de devolucao pendentes do DFe.

    JSON esperado (opcional):
    {
        "criar_sugestoes": bool (default true)
    }
    """
    dados = request.get_json(silent=True) or {}
    criar_sugestoes = dados.get('criar_sugestoes', True)

    try:
        match_service = MatchService()
        resultado = match_service.processar_devolucoes_pendentes(
            criar_sugestoes=criar_sugestoes
        )

        processadas = resultado.get('processadas', 0)
        sugestoes = resultado.get('sugestoes_criadas', 0)

        return jsonify({
            'sucesso': True,
            'mensagem': f'DFe processado: {processadas} NF(s), {sugestoes} sugestao(oes)',
            'dados': resultado
        })

    except Exception as e:
        logger.error(f"Erro ao processar DFe: {e}")
        return jsonify({'sucesso': False, 'mensagem': f'Erro ao processar DFe: {str(e)}'}), 500

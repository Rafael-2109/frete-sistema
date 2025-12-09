"""
Jobs assíncronos para lançamento de CTes e Despesas no Odoo
============================================================

Executados via Redis Queue na fila 'odoo_lancamento'

Fluxo:
1. Usuário solicita lançamento via interface
2. Job enfileirado na fila 'odoo_lancamento'
3. Worker processa: executa as 16 etapas
4. Resultado armazenado e banco atualizado

Timeout: 600 segundos (10 minutos) por lançamento individual
Timeout Lote: 1800 segundos (30 minutos) para lotes

TRATAMENTO DE ERROS:
- CTe/Despesa já lançada: Retorna sucesso com aviso (skip)
- CTe não encontrado: Retorna erro específico
- DFe com status diferente: Retorna erro com status atual
- Erro de conexão: Retorna erro com retry sugerido
"""

import json
import logging
import traceback
from datetime import datetime, date
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

# Timeout para conexão com Odoo (10 minutos por lançamento)
TIMEOUT_LANCAMENTO = 600

# Status que indicam que já foi processado
STATUS_JA_LANCADO = ['LANCADO_ODOO']
STATUS_DFE_VALIDO = '04'  # Status PO no Odoo

# Mapeamento de status DFe para descrição
STATUS_DFE_MAP = {
    '01': 'Rascunho',
    '02': 'Sincronizado',
    '03': 'Ciência/Confirmado',
    '04': 'PO (Pronto)',
    '05': 'Rateio',
    '06': 'Concluído',
    '07': 'Rejeitado'
}

# ========================================
# PROGRESSO DE LOTE EM TEMPO REAL
# ========================================


def _get_redis_connection():
    """Obtém conexão Redis do RQ"""
    try:
        from app.portal.workers import get_redis_connection
        return get_redis_connection()
    except Exception:
        return None


def _atualizar_progresso_lote(fatura_id: int, progresso: dict):
    """
    Atualiza progresso do lote no Redis para acompanhamento em tempo real.

    Estrutura do progresso:
    {
        'fatura_id': int,
        'status': 'processando' | 'concluido' | 'erro',
        'total_fretes': int,
        'total_despesas': int,
        'fretes_processados': int,
        'despesas_processadas': int,
        'fretes_sucesso': int,
        'despesas_sucesso': int,
        'fretes_erro': int,
        'despesas_erro': int,
        'item_atual': str,  # "Frete #123 (1/4)" ou "Despesa #456 (2/3)"
        'item_atual_etapa': str,  # "Etapa 6/16"
        'ultimo_update': str,  # ISO timestamp
        'detalhes': [...]  # Lista de resultados de cada item
    }
    """
    try:
        redis_conn = _get_redis_connection()
        if redis_conn:
            progresso['ultimo_update'] = datetime.now().isoformat()
            key = f'lote_progresso:{fatura_id}'
            redis_conn.setex(key, 3600, json.dumps(progresso))  # Expira em 1 hora
            logger.debug(f"📊 [Lote] Progresso atualizado: {progresso.get('item_atual', 'N/A')}")
    except Exception as e:
        logger.warning(f"⚠️ Erro ao atualizar progresso do lote: {e}")


def _obter_progresso_lote(fatura_id: int) -> Optional[dict]:
    """Obtém progresso do lote do Redis"""
    try:
        redis_conn = _get_redis_connection()
        if redis_conn:
            key = f'lote_progresso:{fatura_id}'
            data = redis_conn.get(key)
            if data:
                return json.loads(data)
    except Exception as e:
        logger.warning(f"⚠️ Erro ao obter progresso do lote: {e}")
    return None


def _limpar_progresso_lote(fatura_id: int):
    """Remove progresso do lote do Redis após conclusão"""
    try:
        redis_conn = _get_redis_connection()
        if redis_conn:
            key = f'lote_progresso:{fatura_id}'
            redis_conn.delete(key)
    except Exception as e:
        logger.warning(f"⚠️ Erro ao limpar progresso do lote: {e}")


def _criar_app_context():
    """Cria contexto do Flask para execução no worker"""
    import sys
    import os
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

    from app import create_app
    app = create_app()
    return app


def lancar_frete_job(
    frete_id: int,
    cte_chave: str,
    usuario_nome: str,
    usuario_ip: str = None,
    data_vencimento: str = None
) -> Dict[str, Any]:
    """
    Job para lançar frete no Odoo (16 etapas)

    Args:
        frete_id: ID do frete no sistema
        cte_chave: Chave de acesso do CTe (44 dígitos)
        usuario_nome: Nome do usuário que solicitou
        usuario_ip: IP do usuário (opcional)
        data_vencimento: Data de vencimento YYYY-MM-DD (opcional)

    Returns:
        dict: Resultado do processamento
            - success: bool
            - frete_id: int
            - message: str
            - dfe_id: int (se sucesso)
            - purchase_order_id: int (se sucesso)
            - invoice_id: int (se sucesso)
            - etapas_concluidas: int
            - error: str (se erro)
            - error_type: str (tipo do erro para tratamento)
            - skipped: bool (se foi pulado por já estar lançado)
    """
    inicio = datetime.now()
    logger.info(f"🚀 [Job Frete] Iniciando lançamento frete #{frete_id}")

    resultado = {
        'success': False,
        'frete_id': frete_id,
        'cte_chave': cte_chave,
        'message': '',
        'dfe_id': None,
        'purchase_order_id': None,
        'invoice_id': None,
        'etapas_concluidas': 0,
        'error': None,
        'error_type': None,
        'skipped': False,
        'tempo_segundos': 0
    }

    try:
        app = _criar_app_context()

        with app.app_context():
            from app.fretes.models import Frete, ConhecimentoTransporte
            from app.fretes.services import LancamentoOdooService

            # ========================================
            # VALIDAÇÃO 1: Frete existe?
            # ========================================
            frete = Frete.query.get(frete_id)
            if not frete:
                resultado['error'] = f"Frete ID {frete_id} não encontrado"
                resultado['error_type'] = 'FRETE_NAO_ENCONTRADO'
                resultado['message'] = resultado['error']
                logger.error(f"❌ [Job Frete] {resultado['error']}")
                return resultado

            # ========================================
            # VALIDAÇÃO 2: Já foi lançado?
            # ========================================
            if frete.status in STATUS_JA_LANCADO:
                resultado['success'] = True
                resultado['skipped'] = True
                resultado['message'] = f"Frete #{frete_id} já está lançado no Odoo"
                resultado['dfe_id'] = frete.odoo_dfe_id
                resultado['purchase_order_id'] = frete.odoo_purchase_order_id
                resultado['invoice_id'] = frete.odoo_invoice_id
                logger.info(f"⏭️ [Job Frete] {resultado['message']}")
                return resultado

            # ========================================
            # VALIDAÇÃO 3: Tem CTe?
            # ========================================
            if not cte_chave:
                resultado['error'] = "Chave CTe não informada"
                resultado['error_type'] = 'CTE_NAO_INFORMADO'
                resultado['message'] = resultado['error']
                logger.error(f"❌ [Job Frete] {resultado['error']}")
                return resultado

            # ========================================
            # VALIDAÇÃO 4: CTe existe no sistema?
            # ========================================
            cte = ConhecimentoTransporte.query.filter_by(chave_acesso=cte_chave).first()
            if not cte:
                resultado['error'] = f"CTe com chave {cte_chave[:20]}... não encontrado no sistema"
                resultado['error_type'] = 'CTE_NAO_ENCONTRADO'
                resultado['message'] = resultado['error']
                logger.error(f"❌ [Job Frete] {resultado['error']}")
                return resultado

            # ========================================
            # EXECUTAR LANÇAMENTO
            # ========================================
            logger.info(f"📋 [Job Frete] Iniciando 16 etapas para frete #{frete_id}")

            # Converter data_vencimento se string
            vencimento = None
            if data_vencimento:
                if isinstance(data_vencimento, str):
                    vencimento = datetime.strptime(data_vencimento, '%Y-%m-%d').date()
                else:
                    vencimento = data_vencimento

            service = LancamentoOdooService(
                usuario_nome=usuario_nome,
                usuario_ip=usuario_ip
            )

            result = service.lancar_frete_odoo(
                frete_id=frete_id,
                cte_chave=cte_chave,
                data_vencimento=vencimento
            )

            # Mapear resultado
            tempo_total = (datetime.now() - inicio).total_seconds()
            resultado['tempo_segundos'] = tempo_total
            resultado['success'] = result.get('sucesso', False)
            resultado['message'] = result.get('mensagem', '')
            resultado['dfe_id'] = result.get('dfe_id')
            resultado['purchase_order_id'] = result.get('purchase_order_id')
            resultado['invoice_id'] = result.get('invoice_id')
            resultado['etapas_concluidas'] = result.get('etapas_concluidas', 0)

            if not resultado['success']:
                resultado['error'] = result.get('erro', 'Erro desconhecido')
                resultado['error_type'] = _classificar_erro(resultado['error'])

            if resultado['success']:
                logger.info(f"✅ [Job Frete] Frete #{frete_id} lançado em {tempo_total:.1f}s")
            else:
                logger.error(f"❌ [Job Frete] Frete #{frete_id} falhou: {resultado['error']}")

            return resultado

    except Exception as e:
        tempo_total = (datetime.now() - inicio).total_seconds()
        resultado['tempo_segundos'] = tempo_total
        resultado['error'] = str(e)
        resultado['error_type'] = 'ERRO_INESPERADO'
        resultado['message'] = f'Erro inesperado: {str(e)}'
        logger.error(f"💥 [Job Frete] Erro inesperado frete #{frete_id}: {e}")
        logger.error(traceback.format_exc())
        return resultado


def lancar_despesa_job(
    despesa_id: int,
    usuario_nome: str,
    usuario_ip: str = None,
    data_vencimento: str = None
) -> Dict[str, Any]:
    """
    Job para lançar despesa extra no Odoo (16 etapas)

    Args:
        despesa_id: ID da despesa extra no sistema
        usuario_nome: Nome do usuário que solicitou
        usuario_ip: IP do usuário (opcional)
        data_vencimento: Data de vencimento YYYY-MM-DD (opcional)

    Returns:
        dict: Resultado do processamento (mesma estrutura de lancar_frete_job)
    """
    inicio = datetime.now()
    logger.info(f"🚀 [Job Despesa] Iniciando lançamento despesa #{despesa_id}")

    resultado = {
        'success': False,
        'despesa_id': despesa_id,
        'message': '',
        'dfe_id': None,
        'purchase_order_id': None,
        'invoice_id': None,
        'etapas_concluidas': 0,
        'error': None,
        'error_type': None,
        'skipped': False,
        'tempo_segundos': 0
    }

    try:
        app = _criar_app_context()

        with app.app_context():
            from app.fretes.models import DespesaExtra
            from app.fretes.services.lancamento_despesa_odoo_service import LancamentoDespesaOdooService

            # ========================================
            # VALIDAÇÃO 1: Despesa existe?
            # ========================================
            despesa = DespesaExtra.query.get(despesa_id)
            if not despesa:
                resultado['error'] = f"Despesa Extra ID {despesa_id} não encontrada"
                resultado['error_type'] = 'DESPESA_NAO_ENCONTRADA'
                resultado['message'] = resultado['error']
                logger.error(f"❌ [Job Despesa] {resultado['error']}")
                return resultado

            # ========================================
            # VALIDAÇÃO 2: Já foi lançada?
            # ========================================
            if despesa.status in STATUS_JA_LANCADO:
                resultado['success'] = True
                resultado['skipped'] = True
                resultado['message'] = f"Despesa #{despesa_id} já está lançada no Odoo"
                resultado['dfe_id'] = despesa.odoo_dfe_id
                resultado['purchase_order_id'] = despesa.odoo_purchase_order_id
                resultado['invoice_id'] = despesa.odoo_invoice_id
                logger.info(f"⏭️ [Job Despesa] {resultado['message']}")
                return resultado

            # ========================================
            # VALIDAÇÃO 3: Tem CTe vinculado?
            # ========================================
            if not despesa.despesa_cte_id:
                resultado['error'] = "Despesa não possui CTe Complementar vinculado"
                resultado['error_type'] = 'CTE_NAO_VINCULADO'
                resultado['message'] = resultado['error']
                logger.error(f"❌ [Job Despesa] {resultado['error']}")
                return resultado

            # ========================================
            # VALIDAÇÃO 4: Tipo documento é CTe?
            # ========================================
            if not despesa.tipo_documento or despesa.tipo_documento.upper() != 'CTE':
                resultado['error'] = f"Tipo de documento '{despesa.tipo_documento}' não suportado para lançamento Odoo"
                resultado['error_type'] = 'TIPO_DOCUMENTO_INVALIDO'
                resultado['message'] = resultado['error']
                logger.error(f"❌ [Job Despesa] {resultado['error']}")
                return resultado

            # ========================================
            # VALIDAÇÃO 5: Status permite lançamento?
            # ========================================
            if despesa.status != 'VINCULADO_CTE':
                resultado['error'] = f"Status '{despesa.status}' não permite lançamento. Esperado: VINCULADO_CTE"
                resultado['error_type'] = 'STATUS_INVALIDO'
                resultado['message'] = resultado['error']
                logger.error(f"❌ [Job Despesa] {resultado['error']}")
                return resultado

            # ========================================
            # EXECUTAR LANÇAMENTO
            # ========================================
            logger.info(f"📋 [Job Despesa] Iniciando 16 etapas para despesa #{despesa_id}")

            # Converter data_vencimento se string
            vencimento = None
            if data_vencimento:
                if isinstance(data_vencimento, str):
                    vencimento = datetime.strptime(data_vencimento, '%Y-%m-%d').date()
                else:
                    vencimento = data_vencimento

            service = LancamentoDespesaOdooService(
                usuario_nome=usuario_nome,
                usuario_ip=usuario_ip
            )

            result = service.lancar_despesa_odoo(
                despesa_id=despesa_id,
                data_vencimento=vencimento
            )

            # Mapear resultado
            tempo_total = (datetime.now() - inicio).total_seconds()
            resultado['tempo_segundos'] = tempo_total
            resultado['success'] = result.get('sucesso', False)
            resultado['message'] = result.get('mensagem', '')
            resultado['dfe_id'] = result.get('dfe_id')
            resultado['purchase_order_id'] = result.get('purchase_order_id')
            resultado['invoice_id'] = result.get('invoice_id')
            resultado['etapas_concluidas'] = result.get('etapas_concluidas', 0)

            if not resultado['success']:
                resultado['error'] = result.get('erro', 'Erro desconhecido')
                resultado['error_type'] = _classificar_erro(resultado['error'])

            if resultado['success']:
                logger.info(f"✅ [Job Despesa] Despesa #{despesa_id} lançada em {tempo_total:.1f}s")
            else:
                logger.error(f"❌ [Job Despesa] Despesa #{despesa_id} falhou: {resultado['error']}")

            return resultado

    except Exception as e:
        tempo_total = (datetime.now() - inicio).total_seconds()
        resultado['tempo_segundos'] = tempo_total
        resultado['error'] = str(e)
        resultado['error_type'] = 'ERRO_INESPERADO'
        resultado['message'] = f'Erro inesperado: {str(e)}'
        logger.error(f"💥 [Job Despesa] Erro inesperado despesa #{despesa_id}: {e}")
        logger.error(traceback.format_exc())
        return resultado


def lancar_lote_job(
    fatura_frete_id: int,
    usuario_nome: str,
    usuario_ip: str = None,
    data_vencimento_fatura: str = None
) -> Dict[str, Any]:
    """
    Job para lançar todos os fretes e despesas de uma fatura no Odoo

    Args:
        fatura_frete_id: ID da fatura de frete
        usuario_nome: Nome do usuário que solicitou
        usuario_ip: IP do usuário (opcional)
        data_vencimento_fatura: Data de vencimento da fatura (YYYY-MM-DD)
            Será usado para TODOS os documentos da fatura (fretes e despesas)

    Returns:
        dict: Resultado do processamento em lote
            - success: bool (True se TODOS foram lançados)
            - fatura_frete_id: int
            - message: str
            - total_fretes: int
            - total_despesas: int
            - fretes_sucesso: int
            - despesas_sucesso: int
            - fretes_erro: int
            - despesas_erro: int
            - fretes_skip: int (já lançados)
            - despesas_skip: int (já lançados)
            - detalhes_fretes: List[Dict]
            - detalhes_despesas: List[Dict]
            - tempo_total_segundos: float
    """
    inicio = datetime.now()
    logger.info(f"🚀 [Job Lote] Iniciando lançamento em lote - Fatura #{fatura_frete_id}")

    resultado = {
        'success': False,
        'fatura_frete_id': fatura_frete_id,
        'message': '',
        'total_fretes': 0,
        'total_despesas': 0,
        'fretes_sucesso': 0,
        'despesas_sucesso': 0,
        'fretes_erro': 0,
        'despesas_erro': 0,
        'fretes_skip': 0,
        'despesas_skip': 0,
        'detalhes_fretes': [],
        'detalhes_despesas': [],
        'tempo_total_segundos': 0
    }

    try:
        app = _criar_app_context()

        with app.app_context():
            from app import db
            from app.fretes.models import FaturaFrete, Frete, DespesaExtra, ConhecimentoTransporte

            # ========================================
            # VALIDAÇÃO: Fatura existe?
            # ========================================
            fatura = FaturaFrete.query.get(fatura_frete_id)
            if not fatura:
                resultado['error'] = f"Fatura de Frete ID {fatura_frete_id} não encontrada"
                resultado['error_type'] = 'FATURA_NAO_ENCONTRADA'
                resultado['message'] = resultado['error']
                logger.error(f"❌ [Job Lote] {resultado['error']}")
                return resultado

            # ========================================
            # BUSCAR FRETES DA FATURA
            # ========================================
            fretes = Frete.query.filter_by(fatura_frete_id=fatura_frete_id).all()
            resultado['total_fretes'] = len(fretes)
            logger.info(f"📦 [Job Lote] Encontrados {len(fretes)} fretes na fatura")

            # ========================================
            # BUSCAR DESPESAS DA FATURA
            # ========================================
            despesas = DespesaExtra.query.filter_by(fatura_frete_id=fatura_frete_id).all()
            resultado['total_despesas'] = len(despesas)
            logger.info(f"📦 [Job Lote] Encontradas {len(despesas)} despesas na fatura")

            # ========================================
            # INICIALIZAR PROGRESSO EM TEMPO REAL
            # ========================================
            progresso = {
                'fatura_id': fatura_frete_id,
                'fatura_numero': fatura.numero_fatura,
                'transportadora': fatura.transportadora.nome_curto if fatura.transportadora else 'N/A',
                'status': 'processando',
                'total_fretes': len(fretes),
                'total_despesas': len(despesas),
                'fretes_processados': 0,
                'despesas_processadas': 0,
                'fretes_sucesso': 0,
                'despesas_sucesso': 0,
                'fretes_erro': 0,
                'despesas_erro': 0,
                'fretes_skip': 0,
                'despesas_skip': 0,
                'item_atual': 'Iniciando...',
                'item_atual_id': None,
                'item_atual_etapa': '',
                'detalhes': [],
                'inicio': datetime.now().isoformat()
            }
            _atualizar_progresso_lote(fatura_frete_id, progresso)

            # ========================================
            # PROCESSAR FRETES
            # ========================================
            for idx, frete in enumerate(fretes):
                # 🔧 RECONEXÃO: Garantir conexão válida antes de cada frete
                # Isso evita erros de "SSL connection has been closed unexpectedly"
                # que ocorrem quando o lançamento anterior demora muito
                try:
                    db.session.execute(db.text('SELECT 1'))
                except Exception as e:
                    logger.warning(f"⚠️ [Lote] Conexão perdida, reconectando... ({e})")
                    db.session.rollback()
                    db.session.remove()

                logger.info(f"📋 [Job Lote] Processando frete #{frete.id} ({idx + 1}/{len(fretes)})")

                # 📊 Atualizar progresso: iniciando frete
                progresso['item_atual'] = f"Frete #{frete.id} ({idx + 1}/{len(fretes)})"
                progresso['item_atual_id'] = frete.id
                progresso['item_atual_tipo'] = 'frete'
                progresso['item_atual_etapa'] = 'Buscando CTe...'
                _atualizar_progresso_lote(fatura_frete_id, progresso)

                # ========================================
                # BUSCAR CTe - PRIORIZA SEMPRE O CTe VINCULADO
                # ========================================
                cte = None
                cte_chave = None

                # PRIORIDADE 1: Vínculo explícito (frete_cte_id) - SEMPRE priorizar
                if frete.frete_cte_id:
                    # Tentar pelo relationship primeiro
                    cte = frete.cte

                    # Se relationship falhar, buscar explicitamente pelo ID
                    if not cte:
                        cte = ConhecimentoTransporte.query.get(frete.frete_cte_id)

                    if cte:
                        cte_chave = cte.chave_acesso
                        logger.info(f"✅ [Lote] Frete #{frete.id}: Usando CTe VINCULADO: {cte.numero_cte} (ID {cte.id})")
                    else:
                        # CTe vinculado não existe mais - erro
                        logger.warning(f"⚠️ [Lote] Frete #{frete.id}: CTe vinculado ID {frete.frete_cte_id} não encontrado!")

                # FALLBACK: Busca automática por NFs + CNPJ (SOMENTE se não houver CTe vinculado)
                if not cte:
                    logger.info(f"🔍 [Lote] Frete #{frete.id}: Buscando CTe por NFs em comum + CNPJ...")

                    # 🔧 RETRY: Em caso de erro de conexão, tenta reconectar e buscar novamente
                    ctes_relacionados = None
                    for tentativa in range(3):
                        try:
                            ctes_relacionados = frete.buscar_ctes_relacionados()
                            break
                        except Exception as e:
                            if 'SSL connection' in str(e) or 'connection' in str(e).lower():
                                logger.warning(f"⚠️ [Lote] Tentativa {tentativa + 1}/3 falhou: {e}")
                                db.session.rollback()
                                db.session.remove()
                                if tentativa == 2:
                                    raise  # Re-lança na última tentativa
                            else:
                                raise  # Outros erros são lançados imediatamente

                    if not ctes_relacionados:
                        detalhe = {
                            'frete_id': frete.id,
                            'success': False,
                            'skipped': False,
                            'error': 'Nenhum CTe relacionado encontrado. Vincule um CTe manualmente.',
                            'error_type': 'CTE_NAO_ENCONTRADO'
                        }
                        resultado['detalhes_fretes'].append(detalhe)
                        resultado['fretes_erro'] += 1
                        continue

                    if len(ctes_relacionados) > 1:
                        # Listar CTes sugeridos na mensagem de erro
                        ctes_info = ', '.join([f"CTe {c.numero_cte}" for c in ctes_relacionados[:5]])
                        if len(ctes_relacionados) > 5:
                            ctes_info += f" e mais {len(ctes_relacionados) - 5}..."

                        detalhe = {
                            'frete_id': frete.id,
                            'success': False,
                            'skipped': False,
                            'error': f'Múltiplos CTes sugeridos ({len(ctes_relacionados)}): {ctes_info}. Vincule manualmente o CTe correto antes de lançar.',
                            'error_type': 'MULTIPLOS_CTES'
                        }
                        resultado['detalhes_fretes'].append(detalhe)
                        resultado['fretes_erro'] += 1
                        continue

                    cte = ctes_relacionados[0]
                    cte_chave = cte.chave_acesso
                    logger.info(f"✅ [Lote] Frete #{frete.id}: CTe encontrado automaticamente: {cte.numero_cte}")

                # Validar chave (igual ao individual)
                if not cte_chave or len(cte_chave) != 44:
                    detalhe = {
                        'frete_id': frete.id,
                        'success': False,
                        'skipped': False,
                        'error': f'Chave do CTe inválida ({len(cte_chave) if cte_chave else 0} caracteres, esperado 44)',
                        'error_type': 'CTE_CHAVE_INVALIDA'
                    }
                    resultado['detalhes_fretes'].append(detalhe)
                    resultado['fretes_erro'] += 1
                    continue

                # ========================================
                # VENCIMENTO: Usa da FATURA (prioridade)
                # Todos os documentos usam o mesmo vencimento da fatura
                # ========================================

                # 📊 Atualizar progresso: executando lançamento
                progresso['item_atual_etapa'] = 'Lançando no Odoo (16 etapas)...'
                _atualizar_progresso_lote(fatura_frete_id, progresso)

                # Executar lançamento com vencimento da fatura
                result_frete = lancar_frete_job(
                    frete_id=frete.id,
                    cte_chave=cte_chave,
                    usuario_nome=usuario_nome,
                    usuario_ip=usuario_ip,
                    data_vencimento=data_vencimento_fatura  # Vencimento da fatura
                )

                resultado['detalhes_fretes'].append(result_frete)

                # 📊 Atualizar progresso: frete concluído
                progresso['fretes_processados'] = idx + 1
                if result_frete.get('skipped'):
                    resultado['fretes_skip'] += 1
                    progresso['fretes_skip'] += 1
                    progresso['item_atual_etapa'] = '⏭️ Já lançado (skip)'
                elif result_frete.get('success'):
                    resultado['fretes_sucesso'] += 1
                    progresso['fretes_sucesso'] += 1
                    progresso['item_atual_etapa'] = f"✅ Concluído ({result_frete.get('etapas_concluidas', 16)}/16)"
                else:
                    resultado['fretes_erro'] += 1
                    progresso['fretes_erro'] += 1
                    progresso['item_atual_etapa'] = f"❌ Erro: {result_frete.get('error', 'Desconhecido')[:50]}"

                # Adicionar ao detalhes do progresso
                progresso['detalhes'].append({
                    'tipo': 'frete',
                    'id': frete.id,
                    'success': result_frete.get('success', False),
                    'skipped': result_frete.get('skipped', False),
                    'message': result_frete.get('message', result_frete.get('error', ''))[:100]
                })
                _atualizar_progresso_lote(fatura_frete_id, progresso)

            # ========================================
            # PROCESSAR DESPESAS
            # ========================================
            for idx, despesa in enumerate(despesas):
                # 🔧 RECONEXÃO: Garantir conexão válida antes de cada despesa
                try:
                    db.session.execute(db.text('SELECT 1'))
                except Exception as e:
                    logger.warning(f"⚠️ [Lote] Conexão perdida antes de despesa, reconectando... ({e})")
                    db.session.rollback()
                    db.session.remove()

                logger.info(f"📋 [Job Lote] Processando despesa #{despesa.id} ({idx + 1}/{len(despesas)})")

                # 📊 Atualizar progresso: iniciando despesa
                progresso['item_atual'] = f"Despesa #{despesa.id} ({idx + 1}/{len(despesas)})"
                progresso['item_atual_id'] = despesa.id
                progresso['item_atual_tipo'] = 'despesa'
                progresso['item_atual_etapa'] = 'Lançando no Odoo (16 etapas)...'
                _atualizar_progresso_lote(fatura_frete_id, progresso)

                # Executar lançamento com vencimento da FATURA
                result_despesa = lancar_despesa_job(
                    despesa_id=despesa.id,
                    usuario_nome=usuario_nome,
                    usuario_ip=usuario_ip,
                    data_vencimento=data_vencimento_fatura  # Vencimento da fatura
                )

                resultado['detalhes_despesas'].append(result_despesa)

                # 📊 Atualizar progresso: despesa concluída
                progresso['despesas_processadas'] = idx + 1

                if result_despesa.get('skipped'):
                    resultado['despesas_skip'] += 1
                    progresso['despesas_skip'] += 1
                    progresso['item_atual_etapa'] = '⏭️ Já lançada (skip)'
                elif result_despesa.get('success'):
                    resultado['despesas_sucesso'] += 1
                    progresso['despesas_sucesso'] += 1
                    progresso['item_atual_etapa'] = f"✅ Concluída ({result_despesa.get('etapas_concluidas', 16)}/16)"
                else:
                    resultado['despesas_erro'] += 1
                    progresso['despesas_erro'] += 1
                    progresso['item_atual_etapa'] = f"❌ Erro: {result_despesa.get('error', 'Desconhecido')[:50]}"

                # Adicionar ao detalhes do progresso
                progresso['detalhes'].append({
                    'tipo': 'despesa',
                    'id': despesa.id,
                    'success': result_despesa.get('success', False),
                    'skipped': result_despesa.get('skipped', False),
                    'message': result_despesa.get('message', result_despesa.get('error', ''))[:100]
                })
                _atualizar_progresso_lote(fatura_frete_id, progresso)

            # ========================================
            # RESUMO FINAL
            # ========================================
            tempo_total = (datetime.now() - inicio).total_seconds()
            resultado['tempo_total_segundos'] = tempo_total

            # Sucesso se não houver erros (skip não conta como erro)
            total_erros = resultado['fretes_erro'] + resultado['despesas_erro']
            total_sucesso = resultado['fretes_sucesso'] + resultado['despesas_sucesso']
            total_skip = resultado['fretes_skip'] + resultado['despesas_skip']
            total_itens = resultado['total_fretes'] + resultado['total_despesas']

            resultado['success'] = (total_erros == 0)

            if total_erros == 0:
                resultado['message'] = (
                    f"Lote processado com sucesso em {tempo_total:.1f}s! "
                    f"{total_sucesso} lançados, {total_skip} já lançados anteriormente"
                )
                logger.info(f"✅ [Job Lote] {resultado['message']}")
            else:
                resultado['message'] = (
                    f"Lote processado com {total_erros} erros em {tempo_total:.1f}s. "
                    f"{total_sucesso} lançados, {total_skip} já lançados, {total_erros} com erro"
                )
                logger.warning(f"⚠️ [Job Lote] {resultado['message']}")

            # 📊 Finalizar progresso
            progresso['status'] = 'concluido' if total_erros == 0 else 'erro'
            progresso['item_atual'] = 'Concluído!'
            progresso['item_atual_etapa'] = resultado['message']
            progresso['fim'] = datetime.now().isoformat()
            progresso['tempo_total_segundos'] = tempo_total
            _atualizar_progresso_lote(fatura_frete_id, progresso)

            return resultado

    except Exception as e:
        tempo_total = (datetime.now() - inicio).total_seconds()
        resultado['tempo_total_segundos'] = tempo_total
        resultado['error'] = str(e)
        resultado['error_type'] = 'ERRO_INESPERADO'
        resultado['message'] = f'Erro inesperado no lote: {str(e)}'
        logger.error(f"💥 [Job Lote] Erro inesperado fatura #{fatura_frete_id}: {e}")
        logger.error(traceback.format_exc())
        return resultado


def _classificar_erro(erro_msg: str) -> str:
    """
    Classifica o tipo de erro baseado na mensagem para facilitar tratamento

    Returns:
        Código do tipo de erro
    """
    erro_lower = erro_msg.lower() if erro_msg else ''

    if 'não encontrado' in erro_lower or 'not found' in erro_lower:
        if 'cte' in erro_lower or 'chave' in erro_lower:
            return 'CTE_NAO_ENCONTRADO'
        if 'dfe' in erro_lower:
            return 'DFE_NAO_ENCONTRADO'
        return 'REGISTRO_NAO_ENCONTRADO'

    if 'status' in erro_lower:
        if 'rascunho' in erro_lower or '01' in erro_lower:
            return 'DFE_STATUS_RASCUNHO'
        if 'confirmado' in erro_lower or 'ciência' in erro_lower or '03' in erro_lower:
            return 'DFE_STATUS_CONFIRMADO'
        if 'concluído' in erro_lower or '06' in erro_lower:
            return 'DFE_STATUS_CONCLUIDO'
        return 'DFE_STATUS_INVALIDO'

    if 'autenticação' in erro_lower or 'auth' in erro_lower:
        return 'ERRO_AUTENTICACAO'

    if 'timeout' in erro_lower or 'timed out' in erro_lower:
        return 'ERRO_TIMEOUT'

    if 'conexão' in erro_lower or 'connection' in erro_lower:
        return 'ERRO_CONEXAO'

    if 'permissão' in erro_lower or 'permission' in erro_lower or 'access' in erro_lower:
        return 'ERRO_PERMISSAO'

    if 'já lançado' in erro_lower or 'já está' in erro_lower:
        return 'JA_LANCADO'

    return 'ERRO_DESCONHECIDO'


def get_job_status(job_id: str) -> Dict[str, Any]:
    """
    Obtém status de um job pelo ID

    Args:
        job_id: ID do job no Redis Queue

    Returns:
        dict com status do job
    """
    from rq.job import Job
    from app.portal.workers import get_redis_connection

    try:
        conn = get_redis_connection()
        job = Job.fetch(job_id, connection=conn)

        status_map = {
            'queued': 'Na fila',
            'started': 'Em processamento',
            'finished': 'Concluído',
            'failed': 'Falhou',
            'deferred': 'Adiado',
            'scheduled': 'Agendado',
            'stopped': 'Parado',
            'canceled': 'Cancelado'
        }

        result = {
            'job_id': job_id,
            'status': job.get_status(),
            'status_display': status_map.get(job.get_status(), job.get_status()),
            'created_at': job.created_at.isoformat() if job.created_at else None,
            'started_at': job.started_at.isoformat() if job.started_at else None,
            'ended_at': job.ended_at.isoformat() if job.ended_at else None,
            'result': job.result if job.is_finished else None,
            'error': str(job.exc_info) if job.is_failed else None,
            'meta': job.meta
        }

        # Calcular tempo de execução se disponível
        if job.started_at and job.ended_at:
            result['duracao_segundos'] = (job.ended_at - job.started_at).total_seconds()
        elif job.started_at:
            result['duracao_segundos'] = (datetime.now(job.started_at.tzinfo) - job.started_at).total_seconds()

        return result

    except Exception as e:
        return {
            'job_id': job_id,
            'status': 'not_found',
            'status_display': 'Não encontrado',
            'error': str(e)
        }

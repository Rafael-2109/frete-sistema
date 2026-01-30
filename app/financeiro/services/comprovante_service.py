# -*- coding: utf-8 -*-
"""
Service de Comprovantes de Pagamento de Boleto
===============================================

Processa PDFs de comprovantes SICOOB, extrai dados via OCR
e persiste no banco de dados com tratamento de duplicatas.

Proteções:
- Retry em erros de SSL/conexão (OperationalError)
- Commit isolado por comprovante (falha em 1 não afeta outros)
- Logging estruturado
"""

import os
import re
import time
import logging
from datetime import date
from decimal import Decimal, InvalidOperation

from sqlalchemy.exc import OperationalError, IntegrityError

from app import db
from app.financeiro.models_comprovante import ComprovantePagamentoBoleto

logger = logging.getLogger(__name__)

# Máximo de tentativas em operações de banco (SSL/conexão)
MAX_RETRY = 3
RETRY_BACKOFF_BASE = 1  # segundos (1, 2, 3...)


# =============================================================================
# FUNÇÕES DE RETRY PARA BANCO
# =============================================================================

def _is_retryable_error(erro: Exception) -> bool:
    """Verifica se o erro de banco é retryable (SSL, conexão, timeout)."""
    erro_str = str(erro).lower()
    keywords = ['ssl', 'connection', 'timeout', 'broken pipe', 'closed',
                'could not connect', 'server closed', 'terminating connection',
                'connection reset', 'network']
    return any(k in erro_str for k in keywords)


def _commit_com_retry(max_tentativas: int = MAX_RETRY) -> bool:
    """
    Executa db.session.commit() com retry em erros de conexão/SSL.

    Returns:
        True se commit bem-sucedido

    Raises:
        OperationalError: se todas as tentativas falharem
        Exception: para erros não-retryable
    """
    for tentativa in range(max_tentativas):
        try:
            db.session.commit()
            return True
        except OperationalError as e:
            db.session.rollback()
            if _is_retryable_error(e) and tentativa < max_tentativas - 1:
                wait = RETRY_BACKOFF_BASE * (tentativa + 1)
                logger.warning(
                    f"[Comprovante] Erro de conexão no commit (tentativa {tentativa + 1}/{max_tentativas}), "
                    f"retry em {wait}s: {e}"
                )
                time.sleep(wait)
                continue
            raise
    return False


def _query_com_retry(query_fn, max_tentativas: int = MAX_RETRY):
    """
    Executa uma query com retry em erros de conexão/SSL.

    Args:
        query_fn: função callable que executa a query
        max_tentativas: número máximo de tentativas

    Returns:
        Resultado da query
    """
    for tentativa in range(max_tentativas):
        try:
            return query_fn()
        except OperationalError as e:
            if _is_retryable_error(e) and tentativa < max_tentativas - 1:
                wait = RETRY_BACKOFF_BASE * (tentativa + 1)
                logger.warning(
                    f"[Comprovante] Erro de conexão na query (tentativa {tentativa + 1}/{max_tentativas}), "
                    f"retry em {wait}s: {e}"
                )
                time.sleep(wait)
                continue
            raise
    return None


# =============================================================================
# CONVERSORES DE DADOS
# =============================================================================

def _converter_data_br(data_str: str | None) -> date | None:
    """
    Converte data no formato brasileiro para date.

    Exemplos:
        '02/01/2026' → date(2026, 1, 2)
        '02/01/2026 às 17:08:48' → date(2026, 1, 2) (ignora hora)
        None → None
    """
    if not data_str:
        return None

    # Extrair apenas a parte da data (DD/MM/YYYY)
    match = re.match(r'(\d{2})/(\d{2})/(\d{4})', data_str.strip())
    if not match:
        return None

    try:
        dia, mes, ano = int(match.group(1)), int(match.group(2)), int(match.group(3))
        return date(ano, mes, dia)
    except ValueError:
        logger.warning(f"Data inválida: {data_str}")
        return None


def _converter_valor_br(valor_str: str | None) -> Decimal | None:
    """
    Converte valor monetário brasileiro para Decimal.

    Exemplos:
        'R$ 51,55' → Decimal('51.55')
        'R$ 1.234,56' → Decimal('1234.56')
        'R$ 0,00' → Decimal('0.00')
        None → None
    """
    if not valor_str:
        return None

    # Remover 'R$' e espaços
    limpo = valor_str.replace('R$', '').strip()

    # Formato BR: '1.234,56' → '1234.56'
    limpo = limpo.replace('.', '').replace(',', '.')

    try:
        return Decimal(limpo)
    except (InvalidOperation, ValueError):
        logger.warning(f"Valor inválido: {valor_str}")
        return None


# =============================================================================
# PROTEÇÃO CONTRA DADOS LONGOS (OCR)
# =============================================================================

def _truncar_campos_seguros(comp) -> None:
    """
    Trunca campos do comprovante OCR que podem exceder o limite do banco.

    Proteção defensiva: mesmo com campos ampliados no modelo, o OCR pode
    gerar valores absurdamente longos. Trunca com warning no log.
    """
    LIMITES = {
        'beneficiario_cnpj_cpf': 50,
        'pagador_cnpj_cpf': 50,
        'nosso_numero': 100,
        'instituicao_emissora': 100,
        'tipo_documento': 100,
        'situacao': 50,
        'autenticacao': 255,
        'conta': 50,
        'numero_agendamento': 50,
        'numero_documento': 100,
        'cooperativa': 255,
        'cliente': 255,
        'linha_digitavel': 255,
        'beneficiario_razao_social': 255,
        'beneficiario_nome_fantasia': 255,
        'pagador_razao_social': 255,
        'pagador_nome_fantasia': 255,
        'data_realizado': 50,
    }
    for campo, limite in LIMITES.items():
        valor = getattr(comp, campo, None)
        if valor and len(valor) > limite:
            logger.warning(
                f"[Comprovante] Truncando {campo}: '{valor[:30]}...' ({len(valor)} → {limite})"
            )
            setattr(comp, campo, valor[:limite])


# =============================================================================
# PROCESSAMENTO PRINCIPAL
# =============================================================================

def processar_pdf_comprovantes(
    arquivo_bytes: bytes,
    nome_arquivo: str,
    usuario: str,
    arquivo_s3_path: str = None,
) -> dict:
    """
    Processa um PDF de comprovantes e persiste os dados no banco.

    Cada comprovante é commitado isoladamente — falha em um não afeta outros.
    Operações de banco têm retry automático para erros de SSL/conexão.

    Args:
        arquivo_bytes: Conteúdo binário do PDF
        nome_arquivo: Nome original do arquivo
        usuario: Nome do usuário que fez o upload

    Returns:
        dict com resumo:
            - novos: quantidade de comprovantes novos inseridos
            - duplicados: quantidade de duplicatas ignoradas
            - erros: quantidade de erros
            - detalhes: lista de dicts {pagina, status, mensagem, numero_agendamento}
    """
    # Importar o extrator (lazy import para não carregar tesserocr no boot do app)
    # Configurar TESSDATA
    tessdata_dir = os.environ.get('TESSDATA_PREFIX', os.path.expanduser('~/tessdata'))
    os.environ['TESSDATA_PREFIX'] = tessdata_dir

    from scripts.leitor_comprovantes_sicoob import extrair_comprovantes_from_bytes

    resultado = {
        'novos': 0,
        'duplicados': 0,
        'erros': 0,
        'detalhes': [],
    }

    # Extrair comprovantes do PDF
    try:
        comprovantes = extrair_comprovantes_from_bytes(arquivo_bytes)
    except Exception as e:
        logger.error(f"Erro ao processar PDF {nome_arquivo}: {e}")
        resultado['erros'] = 1
        resultado['detalhes'].append({
            'pagina': 0,
            'status': 'erro',
            'mensagem': f'Erro ao processar PDF: {str(e)}',
            'numero_agendamento': None,
        })
        return resultado

    # Persistir cada comprovante com commit isolado
    for comp in comprovantes:
        detalhe = {
            'pagina': comp.pagina,
            'numero_agendamento': comp.numero_agendamento,
            'beneficiario': comp.beneficiario_razao_social,
            'valor_pago': comp.valor_pago,
        }

        # Validar chave única
        if not comp.numero_agendamento:
            detalhe['status'] = 'erro'
            detalhe['mensagem'] = 'Sem número de agendamento'
            resultado['erros'] += 1
            resultado['detalhes'].append(detalhe)
            continue

        # Validar que numero_agendamento é numérico (proteção OCR — campo desalinhado)
        if not re.match(r'^\d+$', comp.numero_agendamento):
            detalhe['status'] = 'erro'
            detalhe['mensagem'] = f'OCR inconsistente: numero_agendamento="{comp.numero_agendamento}"'
            resultado['erros'] += 1
            resultado['detalhes'].append(detalhe)
            continue

        # Verificar duplicata (com retry)
        try:
            existente = _query_com_retry(
                lambda: ComprovantePagamentoBoleto.query.filter_by(
                    numero_agendamento=comp.numero_agendamento
                ).first()
            )
        except Exception as e:
            logger.error(f"Erro ao verificar duplicata {comp.numero_agendamento}: {e}")
            detalhe['status'] = 'erro'
            detalhe['mensagem'] = f'Erro de conexão ao verificar duplicata: {str(e)}'
            resultado['erros'] += 1
            resultado['detalhes'].append(detalhe)
            continue

        if existente:
            detalhe['status'] = 'duplicado'
            detalhe['mensagem'] = f'Já importado em {existente.importado_em.strftime("%d/%m/%Y %H:%M") if existente.importado_em else "?"}'
            resultado['duplicados'] += 1
            resultado['detalhes'].append(detalhe)
            continue

        # Truncar campos longos antes do insert (proteção OCR)
        _truncar_campos_seguros(comp)

        # Criar registro e commit isolado
        try:
            registro = ComprovantePagamentoBoleto(
                numero_agendamento=comp.numero_agendamento,
                data_comprovante=_converter_data_br(comp.data_comprovante),
                cooperativa=comp.cooperativa,
                conta=comp.conta,
                cliente=comp.cliente,
                linha_digitavel=comp.linha_digitavel,
                numero_documento=comp.numero_documento,
                nosso_numero=comp.nosso_numero,
                instituicao_emissora=comp.instituicao_emissora,
                tipo_documento=comp.tipo_documento,
                beneficiario_razao_social=comp.beneficiario_razao_social,
                beneficiario_nome_fantasia=comp.beneficiario_nome_fantasia,
                beneficiario_cnpj_cpf=comp.beneficiario_cnpj_cpf,
                pagador_razao_social=comp.pagador_razao_social,
                pagador_nome_fantasia=comp.pagador_nome_fantasia,
                pagador_cnpj_cpf=comp.pagador_cnpj_cpf,
                data_realizado=comp.data_realizado,
                data_pagamento=_converter_data_br(comp.data_pagamento),
                data_vencimento=_converter_data_br(comp.data_vencimento),
                valor_documento=_converter_valor_br(comp.valor_documento),
                valor_desconto_abatimento=_converter_valor_br(comp.valor_desconto_abatimento),
                valor_juros_multa=_converter_valor_br(comp.valor_juros_multa),
                valor_pago=_converter_valor_br(comp.valor_pago),
                situacao=comp.situacao,
                autenticacao=comp.autenticacao,
                arquivo_origem=nome_arquivo,
                pagina_origem=comp.pagina,
                importado_por=usuario,
                arquivo_s3_path=arquivo_s3_path,
            )
            db.session.add(registro)

            # Commit isolado por comprovante (com retry SSL)
            _commit_com_retry()

            detalhe['status'] = 'novo'
            detalhe['mensagem'] = 'Importado com sucesso'
            resultado['novos'] += 1

        except IntegrityError:
            # Duplicata detectada pelo banco (race condition — outro worker inseriu primeiro)
            db.session.rollback()
            detalhe['status'] = 'duplicado'
            detalhe['mensagem'] = 'Duplicata detectada (inserção concorrente)'
            resultado['duplicados'] += 1

        except OperationalError as e:
            db.session.rollback()
            logger.error(f"Erro de conexão ao salvar comprovante {comp.numero_agendamento}: {e}")
            detalhe['status'] = 'erro'
            detalhe['mensagem'] = f'Erro de conexão: {str(e)}'
            resultado['erros'] += 1

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao salvar comprovante {comp.numero_agendamento}: {e}")
            detalhe['status'] = 'erro'
            detalhe['mensagem'] = str(e)
            resultado['erros'] += 1

        resultado['detalhes'].append(detalhe)

    return resultado

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

import hashlib
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
            db.session.rollback()  # Limpar transação inválida antes do retry
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
# CHAVE SUBSTITUTA PARA COMPROVANTES SEM AGENDAMENTO
# =============================================================================

def _gerar_chave_surrogate(comp) -> str | None:
    """
    Gera chave substituta para comprovantes sem numero_agendamento.

    Quando o OCR não consegue extrair o numero_agendamento (desalinhamento
    no Formato A causado por valores "--" que o Tesseract perde/mescla),
    usa a autenticacao (UUID bancário, único por transação) como chave.

    Prefixo SA- distingue de chaves reais numéricas e evita colisão
    com CHECKNUMs do OFX (que são sempre numéricos).

    Returns:
        Chave substituta prefixada com 'SA-' ou None se sem dados.
    """
    # Estratégia 1: autenticacao (UUID bancário, mais confiável)
    if comp.autenticacao:
        auth_clean = re.sub(r'\s+', '', comp.autenticacao.strip())
        return f'SA-{auth_clean}'

    # Estratégia 2: hash determinístico de campos identificadores
    parts = [
        comp.beneficiario_cnpj_cpf or '',
        comp.valor_pago or '',
        comp.data_pagamento or comp.data_comprovante or '',
        comp.linha_digitavel or '',
    ]
    combined = '|'.join(parts)
    if not any(parts):
        return None

    hash_val = hashlib.md5(combined.encode()).hexdigest()[:16]
    return f'SA-{hash_val}'


# =============================================================================
# PROCESSAMENTO PRINCIPAL
# =============================================================================

def _bulk_check_duplicatas(chaves: list[str]) -> set[str]:
    """
    Verifica duplicatas em bulk usando uma única query IN(...).

    Substitui N queries individuais por 1 query, reduzindo latência
    significativamente para PDFs com muitos comprovantes.

    Args:
        chaves: Lista de numero_agendamento a verificar.

    Returns:
        Set de numero_agendamento que já existem no banco.
    """
    if not chaves:
        return set()

    try:
        rows = _query_com_retry(
            lambda: ComprovantePagamentoBoleto.query.filter(
                ComprovantePagamentoBoleto.numero_agendamento.in_(chaves)
            ).with_entities(
                ComprovantePagamentoBoleto.numero_agendamento
            ).all()
        )
        return {r[0] for r in rows} if rows else set()
    except Exception as e:
        logger.error(f"[Comprovante] Erro no bulk check de duplicatas: {e}")
        db.session.rollback()
        return set()


def processar_pdf_comprovantes(
    arquivo_bytes: bytes,
    nome_arquivo: str,
    usuario: str,
    arquivo_s3_path: str = None,
) -> dict:
    """
    Processa um PDF de comprovantes e persiste os dados no banco.

    Otimizações:
    - Bulk check de duplicatas: 1 query IN(...) em vez de N queries individuais.
    - Savepoint commits: 1 commit real no final com savepoints por comprovante.
      Se o commit final falhar, faz fallback para commits individuais.

    Args:
        arquivo_bytes: Conteúdo binário do PDF
        nome_arquivo: Nome original do arquivo
        usuario: Nome do usuário que fez o upload
        arquivo_s3_path: Caminho do PDF no S3 (opcional)

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

    from app.financeiro.leitor_comprovantes_sicoob import extrair_comprovantes_from_bytes

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

    if not comprovantes:
        return resultado

    # ── FASE 1: Pré-computar chaves e validar ──
    # Gerar surrogates e validar ANTES do loop de persistência
    comprovantes_validos = []
    for comp in comprovantes:
        detalhe = {
            'pagina': comp.pagina,
            'numero_agendamento': comp.numero_agendamento,
            'beneficiario': comp.beneficiario_razao_social,
            'valor_pago': comp.valor_pago,
        }

        # Gerar chave substituta se necessário
        if not comp.numero_agendamento:
            chave = _gerar_chave_surrogate(comp)
            if not chave:
                detalhe['status'] = 'erro'
                detalhe['mensagem'] = 'Sem número de agendamento e sem dados para identificação única'
                resultado['erros'] += 1
                resultado['detalhes'].append(detalhe)
                continue
            comp.numero_agendamento = chave
            detalhe['numero_agendamento'] = chave
            logger.info(f"[Comprovante] p.{comp.pagina}: Gerada chave surrogate: {chave}")

        # Validar que numero_agendamento é numérico (proteção OCR)
        # Chaves surrogate (prefixo SA-) são permitidas
        if not comp.numero_agendamento.startswith('SA-') and not re.match(r'^\d+$', comp.numero_agendamento):
            detalhe['status'] = 'erro'
            detalhe['mensagem'] = f'OCR inconsistente: numero_agendamento="{comp.numero_agendamento}"'
            resultado['erros'] += 1
            resultado['detalhes'].append(detalhe)
            continue

        comprovantes_validos.append((comp, detalhe))

    if not comprovantes_validos:
        return resultado

    # ── FASE 2: Bulk check de duplicatas (1 query em vez de N) ──
    todas_chaves = [comp.numero_agendamento for comp, _ in comprovantes_validos]
    existentes_db = _bulk_check_duplicatas(todas_chaves)

    # ── FASE 3: Persistir com savepoints (1 commit real no final) ──
    novos_detalhes = []  # Detalhes dos que tentamos inserir (para fallback)

    for comp, detalhe in comprovantes_validos:
        # Check duplicata via set em memória (O(1))
        if comp.numero_agendamento in existentes_db:
            detalhe['status'] = 'duplicado'
            detalhe['mensagem'] = 'Já importado anteriormente'
            resultado['duplicados'] += 1
            resultado['detalhes'].append(detalhe)
            continue

        # Truncar campos longos antes do insert (proteção OCR)
        _truncar_campos_seguros(comp)

        # Inserir com savepoint (rollback granular sem perder outros registros)
        try:
            savepoint = db.session.begin_nested()
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
            savepoint.commit()

            detalhe['status'] = 'novo'
            detalhe['mensagem'] = 'Importado com sucesso'
            resultado['novos'] += 1
            # Marcar no set para dedup intra-PDF
            existentes_db.add(comp.numero_agendamento)

        except IntegrityError:
            # Duplicata detectada pelo banco (race condition — outro worker inseriu primeiro)
            savepoint.rollback()
            detalhe['status'] = 'duplicado'
            detalhe['mensagem'] = 'Duplicata detectada (inserção concorrente)'
            resultado['duplicados'] += 1

        except OperationalError as e:
            savepoint.rollback()
            logger.error(f"Erro de conexão ao salvar comprovante {comp.numero_agendamento}: {e}")
            detalhe['status'] = 'erro'
            detalhe['mensagem'] = f'Erro de conexão: {str(e)}'
            resultado['erros'] += 1

        except Exception as e:
            savepoint.rollback()
            logger.error(f"Erro ao salvar comprovante {comp.numero_agendamento}: {e}")
            detalhe['status'] = 'erro'
            detalhe['mensagem'] = str(e)
            resultado['erros'] += 1

        novos_detalhes.append(detalhe)
        resultado['detalhes'].append(detalhe)

    # ── FASE 4: Commit final (1 commit real para todos os savepoints) ──
    if resultado['novos'] > 0:
        try:
            _commit_com_retry()
            logger.info(
                f"[Comprovante] {nome_arquivo}: {resultado['novos']} novo(s) commitados em batch"
            )
        except (OperationalError, Exception) as e:
            # Commit final falhou — todos os inserts são perdidos
            db.session.rollback()
            logger.error(
                f"[Comprovante] Commit final falhou para {nome_arquivo}: {e}. "
                f"Tentando fallback com commits individuais..."
            )
            # Fallback: re-tentar cada comprovante com commit individual
            _fallback_commit_individual(
                comprovantes_validos, nome_arquivo, usuario,
                arquivo_s3_path, resultado, novos_detalhes,
            )

    return resultado


def _fallback_commit_individual(
    comprovantes_validos, nome_arquivo, usuario,
    arquivo_s3_path, resultado, novos_detalhes,
):
    """
    Fallback: re-insere comprovantes com commit individual quando o commit batch falha.

    Chamado apenas quando _commit_com_retry() final falha (ex: conexão SSL caiu).
    Re-tenta cada comprovante que tinha status='novo' com commit isolado.
    """
    # Zerar contadores dos que estavam como 'novo' (o rollback perdeu tudo)
    novos_perdidos = 0
    for detalhe in novos_detalhes:
        if detalhe['status'] == 'novo':
            novos_perdidos += 1
            detalhe['status'] = 'erro'
            detalhe['mensagem'] = 'Commit batch falhou — tentando individual...'

    resultado['novos'] -= novos_perdidos
    resultado['erros'] += novos_perdidos

    # Re-tentar cada comprovante com commit individual
    for comp, detalhe in comprovantes_validos:
        if detalhe['status'] != 'erro' or 'Commit batch' not in detalhe.get('mensagem', ''):
            continue

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
            _commit_com_retry()

            detalhe['status'] = 'novo'
            detalhe['mensagem'] = 'Importado com sucesso (fallback individual)'
            resultado['novos'] += 1
            resultado['erros'] -= 1

        except IntegrityError:
            db.session.rollback()
            detalhe['status'] = 'duplicado'
            detalhe['mensagem'] = 'Duplicata detectada (fallback individual)'
            resultado['duplicados'] += 1
            resultado['erros'] -= 1

        except Exception as e:
            db.session.rollback()
            detalhe['status'] = 'erro'
            detalhe['mensagem'] = f'Erro no fallback individual: {str(e)}'
            logger.error(f"[Comprovante] Fallback falhou para {comp.numero_agendamento}: {e}")

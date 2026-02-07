# -*- coding: utf-8 -*-
"""
Service de Comprovantes de Pagamento PIX
=========================================

Processa comprovantes PIX (já parseados) e persiste no banco de dados.
Reutiliza a mesma tabela `comprovante_pagamento_boleto` com tipo='pix'.

Mapeamento ComprovantePix → ComprovantePagamentoBoleto:
    id_transacao          → numero_agendamento (CHAVE ÚNICA — EndToEndId)
    destinatario_nome     → beneficiario_razao_social
    destinatario_cnpj_cpf → beneficiario_cnpj_cpf
    destinatario_inst.    → instituicao_emissora
    pagador_nome          → pagador_razao_social
    pagador_cnpj_cpf      → pagador_cnpj_cpf
    pagador_instituicao   → cooperativa
    data_pagamento        → data_pagamento + data_realizado
    valor                 → valor_pago
    tipo_pagamento        → tipo_documento
    situacao              → situacao
"""

import logging
import re
from datetime import date
from decimal import Decimal, InvalidOperation

from sqlalchemy.exc import OperationalError, IntegrityError

from app import db
from app.financeiro.models_comprovante import ComprovantePagamentoBoleto
from app.financeiro.parsers.models import ComprovantePix
from app.financeiro.services.comprovante_service import (
    _commit_com_retry,
    _bulk_check_duplicatas,
)

logger = logging.getLogger(__name__)


# =============================================================================
# CONVERSORES DE DADOS (formato PIX)
# =============================================================================

def _converter_data_br_pix(data_str: str | None) -> date | None:
    """
    Converte data do comprovante PIX para date.

    Formatos aceitos:
        '29/12/2025' → date(2025, 12, 29)
        '29/12/2025 11:31:03' → date(2025, 12, 29) (ignora hora)
    """
    if not data_str:
        return None

    match = re.match(r'(\d{2})/(\d{2})/(\d{4})', data_str.strip())
    if not match:
        return None

    try:
        dia, mes, ano = int(match.group(1)), int(match.group(2)), int(match.group(3))
        return date(ano, mes, dia)
    except ValueError:
        logger.warning(f"[PIX Service] Data inválida: {data_str}")
        return None


def _converter_valor_br_pix(valor_str: str | None) -> Decimal | None:
    """
    Converte valor monetário PIX (formato BR) para Decimal.

    Formatos aceitos:
        '200,41' → Decimal('200.41')
        '1.234,56' → Decimal('1234.56')
        'R$ 200,41' → Decimal('200.41')
    """
    if not valor_str:
        return None

    limpo = valor_str.replace('R$', '').strip()
    limpo = limpo.replace('.', '').replace(',', '.')

    try:
        return Decimal(limpo)
    except (InvalidOperation, ValueError):
        logger.warning(f"[PIX Service] Valor inválido: {valor_str}")
        return None


# =============================================================================
# PROCESSAMENTO PRINCIPAL
# =============================================================================

def processar_comprovantes_pix(
    comprovantes: list[ComprovantePix],
    nome_arquivo: str,
    usuario: str,
    arquivo_s3_path: str = None,
) -> dict:
    """
    Persiste comprovantes PIX no banco (mesma tabela de boletos, tipo='pix').

    Lógica de dedup: EndToEndId (id_transacao) como `numero_agendamento` UNIQUE.

    Args:
        comprovantes: Lista de ComprovantePix já parseados.
        nome_arquivo: Nome original do arquivo PDF.
        usuario: Nome do usuário que fez o upload.
        arquivo_s3_path: Caminho do PDF no S3 (opcional).

    Returns:
        dict com resumo:
            - novos: quantidade inseridos
            - duplicados: quantidade duplicatas
            - erros: quantidade de erros
            - detalhes: lista de dicts {pagina, status, mensagem, numero_agendamento}
    """
    resultado = {
        'novos': 0,
        'duplicados': 0,
        'erros': 0,
        'detalhes': [],
    }

    if not comprovantes:
        return resultado

    # ── FASE 1: Validar e preparar chaves ──
    comprovantes_validos = []
    for comp in comprovantes:
        detalhe = {
            'pagina': comp.pagina,
            'numero_agendamento': comp.id_transacao,
            'beneficiario': comp.destinatario_nome,
            'valor_pago': comp.valor,
        }

        # PIX PRECISA do EndToEndId como chave única
        if not comp.id_transacao:
            detalhe['status'] = 'erro'
            detalhe['mensagem'] = 'Sem ID Transação (EndToEndId) — não pode ser deduplicado'
            resultado['erros'] += 1
            resultado['detalhes'].append(detalhe)
            continue

        comprovantes_validos.append((comp, detalhe))

    if not comprovantes_validos:
        return resultado

    # ── FASE 2: Bulk check de duplicatas (1 query) ──
    todas_chaves = [comp.id_transacao for comp, _ in comprovantes_validos]
    existentes_db = _bulk_check_duplicatas(todas_chaves)

    # ── FASE 3: Persistir com savepoints ──
    novos_detalhes = []

    for comp, detalhe in comprovantes_validos:
        # Check duplicata via set em memória (O(1))
        if comp.id_transacao in existentes_db:
            detalhe['status'] = 'duplicado'
            detalhe['mensagem'] = 'Já importado anteriormente (EndToEndId duplicado)'
            resultado['duplicados'] += 1
            resultado['detalhes'].append(detalhe)
            continue

        try:
            savepoint = db.session.begin_nested()
            registro = ComprovantePagamentoBoleto(
                tipo='pix',
                numero_agendamento=comp.id_transacao,
                data_comprovante=_converter_data_br_pix(comp.data_comprovante),
                # Mapeamento PIX → Model
                beneficiario_razao_social=comp.destinatario_nome,
                beneficiario_cnpj_cpf=comp.destinatario_cnpj_cpf,
                instituicao_emissora=comp.destinatario_instituicao,
                pagador_razao_social=comp.pagador_nome,
                pagador_cnpj_cpf=comp.pagador_cnpj_cpf,
                cooperativa=comp.pagador_instituicao,
                data_realizado=comp.data_pagamento,
                data_pagamento=_converter_data_br_pix(comp.data_pagamento),
                valor_pago=_converter_valor_br_pix(comp.valor),
                tipo_documento=comp.tipo_pagamento,
                situacao=comp.situacao,
                # Metadados
                arquivo_origem=nome_arquivo,
                pagina_origem=comp.pagina,
                importado_por=usuario,
                arquivo_s3_path=arquivo_s3_path,
            )
            db.session.add(registro)
            savepoint.commit()

            detalhe['status'] = 'novo'
            detalhe['mensagem'] = 'Importado com sucesso (PIX)'
            resultado['novos'] += 1
            # Marcar no set para dedup intra-PDF
            existentes_db.add(comp.id_transacao)

        except IntegrityError:
            savepoint.rollback()
            detalhe['status'] = 'duplicado'
            detalhe['mensagem'] = 'Duplicata detectada (inserção concorrente)'
            resultado['duplicados'] += 1

        except OperationalError as e:
            savepoint.rollback()
            logger.error(f"[PIX Service] Erro de conexão ao salvar {comp.id_transacao}: {e}")
            detalhe['status'] = 'erro'
            detalhe['mensagem'] = f'Erro de conexão: {str(e)}'
            resultado['erros'] += 1

        except Exception as e:
            savepoint.rollback()
            logger.error(f"[PIX Service] Erro ao salvar {comp.id_transacao}: {e}")
            detalhe['status'] = 'erro'
            detalhe['mensagem'] = str(e)
            resultado['erros'] += 1

        novos_detalhes.append(detalhe)
        resultado['detalhes'].append(detalhe)

    # ── FASE 4: Commit final ──
    if resultado['novos'] > 0:
        try:
            _commit_com_retry()
            logger.info(
                f"[PIX Service] {nome_arquivo}: {resultado['novos']} novo(s) commitados"
            )
        except (OperationalError, Exception) as e:
            db.session.rollback()
            logger.error(
                f"[PIX Service] Commit final falhou para {nome_arquivo}: {e}"
            )
            # Zerar contadores dos que estavam como 'novo'
            for detalhe in novos_detalhes:
                if detalhe['status'] == 'novo':
                    detalhe['status'] = 'erro'
                    detalhe['mensagem'] = f'Commit falhou: {str(e)}'
                    resultado['novos'] -= 1
                    resultado['erros'] += 1

    return resultado


def processar_pdf_comprovantes_pix(
    arquivo_bytes: bytes,
    nome_arquivo: str,
    usuario: str,
    arquivo_s3_path: str = None,
) -> dict:
    """
    Pipeline completo: extrai comprovantes PIX do PDF e persiste.

    Args:
        arquivo_bytes: Conteúdo binário do PDF.
        nome_arquivo: Nome original do arquivo.
        usuario: Nome do usuário que fez o upload.
        arquivo_s3_path: Caminho do PDF no S3 (opcional).

    Returns:
        dict com resumo (novos, duplicados, erros, detalhes).
    """
    from app.financeiro.parsers.dispatcher import extrair_comprovantes_pix

    resultado = {
        'novos': 0,
        'duplicados': 0,
        'erros': 0,
        'detalhes': [],
    }

    # Extrair comprovantes do PDF
    try:
        comprovantes = extrair_comprovantes_pix(arquivo_bytes)
    except Exception as e:
        logger.error(f"[PIX Service] Erro ao parsear PDF PIX {nome_arquivo}: {e}")
        resultado['erros'] = 1
        resultado['detalhes'].append({
            'pagina': 0,
            'status': 'erro',
            'mensagem': f'Erro ao parsear PDF PIX: {str(e)}',
            'numero_agendamento': None,
        })
        return resultado

    if not comprovantes:
        return resultado

    return processar_comprovantes_pix(
        comprovantes=comprovantes,
        nome_arquivo=nome_arquivo,
        usuario=usuario,
        arquivo_s3_path=arquivo_s3_path,
    )

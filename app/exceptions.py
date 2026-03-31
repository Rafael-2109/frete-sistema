"""
Hierarquia de excecoes do Sistema de Fretes
============================================

Base para tratamento de erros especificos de dominio.
Substitui bare `except Exception` por catches tipados com contexto.

Hierarquia:
    AppError (base)
    +-- ValidationError (input/validacao)
    +-- FaturamentoError (faturamento/NFs)
    +-- EmbarqueError (embarques)
    +-- FreteError (fretes/cotacao)
    +-- CotacaoError (cotacoes)
    +-- SyncError (sincronizacao Odoo/sistemas externos)
    +-- CusteioError (calculo de custo)
    +-- ReconciliacaoError (reconciliacao NF x separacao)

Uso:
    from app.exceptions import FaturamentoError

    try:
        processar_nf(numero_nf)
    except FaturamentoError as e:
        logger.error(f"Erro faturamento NF {numero_nf}: {e}", extra={'code': e.code})
    except Exception as e:
        logger.exception("Erro inesperado")

Convencoes:
    - SEMPRE usar `raise XError("msg") from e` para preservar traceback
    - SEMPRE manter um `except Exception` final como safety net com logger.exception()
    - Cada catch especifico deve logar COM contexto (entity_id, operation)
"""


class AppError(Exception):
    """Base exception for all application errors.

    Args:
        message: Human-readable error description.
        code: Machine-readable error code (e.g. 'NF_NAO_ENCONTRADA').
        details: Dict with additional context (entity ids, operation, etc).
    """

    def __init__(self, message: str, code: str = None, details: dict = None):
        super().__init__(message)
        self.code = code
        self.details = details or {}


class ValidationError(AppError):
    """Input validation failed (missing fields, invalid format, etc)."""

    pass


class FaturamentoError(AppError):
    """Errors in invoicing/billing operations (NFs, produtos, processamento)."""

    pass


class EmbarqueError(AppError):
    """Errors in shipment operations (embarques, items, validacao)."""

    pass


class FreteError(AppError):
    """Errors in freight operations (calculo, tabela, transportadora)."""

    pass


class CotacaoError(AppError):
    """Errors in quote operations (cotacao, simulacao)."""

    pass


class SyncError(AppError):
    """Errors in data synchronization (Odoo, SSW, external systems)."""

    pass


class CusteioError(AppError):
    """Errors in cost calculation (margem, custeio, markup)."""

    pass


class ReconciliacaoError(AppError):
    """Errors in reconciliation between NF and separacao."""

    pass

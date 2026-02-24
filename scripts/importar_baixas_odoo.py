#!/usr/bin/env python3
"""
DEPRECADO — Script de Importação de Baixas/Reconciliações do Odoo
=================================================================

Este script foi substituído pelo SincronizacaoBaixasService
(app/financeiro/services/sincronizacao_baixas_service.py).

Os modelos que este script utilizava (ContasAReceberPagamento,
ContasAReceberDocumento, ContasAReceberLinhaCredito) foram removidos.

NÃO EXECUTAR — sai com código 1.
"""

import sys

print("=" * 80)
print("ERRO: Este script está DEPRECADO.")
print()
print("Os modelos ContasAReceberPagamento, ContasAReceberDocumento e")
print("ContasAReceberLinhaCredito foram removidos do sistema.")
print()
print("Use o SincronizacaoBaixasService em seu lugar:")
print("  from app.financeiro.services.sincronizacao_baixas_service import SincronizacaoBaixasService")
print("=" * 80)

sys.exit(1)

"""
Modelos do módulo de Pallet v2

Este pacote contém os modelos para a gestão de pallets,
estruturados em dois domínios independentes:

DOMÍNIO A - Controle dos Pallets:
- PalletCredito: Créditos de pallet a receber
- PalletDocumento: Documentos que enriquecem créditos (canhotos, vales)
- PalletSolucao: Soluções de créditos (baixa, venda, recebimento, substituição)

DOMÍNIO B - Tratativa das NFs:
- PalletNFRemessa: NFs de remessa de pallet emitidas
- PalletNFSolucao: Soluções documentais (devolução, retorno, cancelamento)

LEGADO:
- ValePallet: Modelo original (manter para compatibilidade durante transição)

Spec: .claude/ralph-loop/specs/prd-reestruturacao-modulo-pallets.md
"""

# Modelo Legado (manter para compatibilidade)
from app.pallet.models.vale_pallet import ValePallet

# Domínio B - NF de Remessa (deve ser importado primeiro por ser FK de outros)
from app.pallet.models.nf_remessa import PalletNFRemessa

# Domínio A - Créditos
from app.pallet.models.credito import PalletCredito
from app.pallet.models.documento import PalletDocumento
from app.pallet.models.solucao import PalletSolucao

# Domínio B - Soluções de NF
from app.pallet.models.nf_solucao import PalletNFSolucao

# Exportar todos os modelos
__all__ = [
    # Modelo legado
    'ValePallet',
    # Novos modelos v2
    'PalletNFRemessa',
    'PalletCredito',
    'PalletDocumento',
    'PalletSolucao',
    'PalletNFSolucao',
]

"""
Fix: NFs importadas já canceladas que criaram movimentações ativas indevidamente.

NFs afetadas: 140886 e 145463
Causa: Bug no INSERT path de faturamento_service.py que adicionava NFs canceladas
       a nfs_reprocessar, gerando MovimentacaoEstoque com status_nf='FATURADO' e ativo=true
       para NFs que já estavam canceladas no Odoo.

Uso:
    source .venv/bin/activate
    python scripts/migrations/fix_movimentacoes_nf_cancelada_importada.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db
from app.estoque.models import MovimentacaoEstoque
from app.utils.timezone import agora_utc_naive


NFS_AFETADAS = ['140886', '145463']
MOTIVO = 'Fix - NF importada cancelada sem processar cancelamento'


def main():
    app = create_app()
    with app.app_context():
        # Verificação ANTES
        movimentacoes = MovimentacaoEstoque.query.filter(
            MovimentacaoEstoque.numero_nf.in_(NFS_AFETADAS),
            MovimentacaoEstoque.status_nf == 'FATURADO',
            MovimentacaoEstoque.ativo == True,
        ).all()

        if not movimentacoes:
            print("Nenhuma movimentação ativa encontrada para as NFs afetadas.")
            print("Fix já foi aplicado ou dados não existem.")
            return

        print(f"Encontradas {len(movimentacoes)} movimentações para corrigir:")
        for mov in movimentacoes:
            print(f"  ID={mov.id} | NF={mov.numero_nf} | Produto={mov.cod_produto} "
                  f"| Qtd={mov.quantidade} | Status={mov.status_nf} | Ativo={mov.ativo}")

        # Aplicar correção
        agora = agora_utc_naive()
        for mov in movimentacoes:
            mov.status_nf = 'CANCELADO'
            mov.ativo = False
            mov.atualizado_em = agora
            mov.atualizado_por = MOTIVO

        db.session.commit()

        # Verificação DEPOIS
        restantes = MovimentacaoEstoque.query.filter(
            MovimentacaoEstoque.numero_nf.in_(NFS_AFETADAS),
            MovimentacaoEstoque.status_nf == 'FATURADO',
            MovimentacaoEstoque.ativo == True,
        ).count()

        print(f"\nFix aplicado com sucesso!")
        print(f"  Movimentações corrigidas: {len(movimentacoes)}")
        print(f"  Restantes ativas (deve ser 0): {restantes}")

        if restantes > 0:
            print("AVISO: Ainda existem movimentações ativas! Verifique manualmente.")


if __name__ == '__main__':
    main()

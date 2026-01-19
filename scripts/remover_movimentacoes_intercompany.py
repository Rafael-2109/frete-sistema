"""
Script para remover movimentacoes de pallet intercompany (Nacom/La Famiglia)

Essas movimentacoes nao devem ser controladas pois sao transferencias internas do grupo.

Para executar:
    python scripts/remover_movimentacoes_intercompany.py

No Render Shell (SQL direto):
    -- Ver movimentacoes intercompany
    SELECT id, numero_nf, tipo_movimentacao, cnpj_destinatario, nome_destinatario, qtd_movimentacao
    FROM movimentacao_estoque
    WHERE local_movimentacao = 'PALLET'
      AND ativo = true
      AND (cnpj_destinatario LIKE '61724241%' OR cnpj_destinatario LIKE '18467441%');

    -- Soft delete das movimentacoes intercompany
    UPDATE movimentacao_estoque
    SET ativo = false,
        observacao = COALESCE(observacao, '') || E'\\n[REMOVIDO] Movimentacao intercompany - nao deve ser controlada'
    WHERE local_movimentacao = 'PALLET'
      AND ativo = true
      AND (cnpj_destinatario LIKE '61724241%' OR cnpj_destinatario LIKE '18467441%');
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.estoque.models import MovimentacaoEstoque
from sqlalchemy import or_

# CNPJs intercompany (prefixos - 8 primeiros digitos)
CNPJS_INTERCOMPANY_PREFIXOS = ['61724241', '18467441']


def listar_movimentacoes_intercompany():
    """Lista movimentacoes de pallet para CNPJs do grupo"""
    print("\n" + "=" * 70)
    print("MOVIMENTACOES DE PALLET INTERCOMPANY (Nacom/La Famiglia)")
    print("=" * 70)

    movimentacoes = MovimentacaoEstoque.query.filter(
        MovimentacaoEstoque.local_movimentacao == 'PALLET',
        MovimentacaoEstoque.ativo == True,
        or_(
            MovimentacaoEstoque.cnpj_destinatario.like('61724241%'),
            MovimentacaoEstoque.cnpj_destinatario.like('18467441%')
        )
    ).order_by(MovimentacaoEstoque.data_movimentacao.desc()).all()

    if not movimentacoes:
        print("\n✅ Nenhuma movimentacao intercompany encontrada!")
        return []

    print(f"\n⚠️ Encontradas {len(movimentacoes)} movimentacoes:\n")
    print(f"{'ID':>6} | {'NF':>10} | {'Tipo':>12} | {'CNPJ':>18} | {'Destinatario':<30} | {'Qtd':>4}")
    print("-" * 100)

    for m in movimentacoes:
        print(f"{m.id:>6} | {(m.numero_nf or '-'):>10} | {m.tipo_movimentacao:>12} | {(m.cnpj_destinatario or '-'):>18} | {(m.nome_destinatario or '-'):<30} | {int(m.qtd_movimentacao or 0):>4}")

    return movimentacoes


def remover_movimentacoes_intercompany(confirmar=False):
    """Remove (soft delete) movimentacoes intercompany"""
    movimentacoes = MovimentacaoEstoque.query.filter(
        MovimentacaoEstoque.local_movimentacao == 'PALLET',
        MovimentacaoEstoque.ativo == True,
        or_(
            MovimentacaoEstoque.cnpj_destinatario.like('61724241%'),
            MovimentacaoEstoque.cnpj_destinatario.like('18467441%')
        )
    ).all()

    if not movimentacoes:
        print("\n✅ Nenhuma movimentacao intercompany para remover!")
        return 0

    if not confirmar:
        print(f"\n⚠️ {len(movimentacoes)} movimentacoes serao marcadas como inativas.")
        print("   Execute com --confirmar para efetivar a remocao.")
        return 0

    count = 0
    for m in movimentacoes:
        m.ativo = False
        m.observacao = (m.observacao or '') + '\n[REMOVIDO] Movimentacao intercompany - nao deve ser controlada'
        count += 1

    db.session.commit()
    print(f"\n✅ {count} movimentacoes marcadas como inativas!")
    return count


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        # Listar primeiro
        movimentacoes = listar_movimentacoes_intercompany()

        if movimentacoes:
            # Verificar se deve confirmar
            confirmar = '--confirmar' in sys.argv

            if not confirmar:
                print("\n" + "-" * 70)
                print("Para remover, execute:")
                print("  python scripts/remover_movimentacoes_intercompany.py --confirmar")
                print("-" * 70)

            remover_movimentacoes_intercompany(confirmar=confirmar)

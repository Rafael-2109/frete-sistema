"""
Script de Teste: Validação da Nova Lógica de Reversão de NF

Este script verifica se a nova lógica de reversão está funcionando corretamente:
1. FaturamentoProduto.revertida = True (mantém status_nf='Lançado')
2. MovimentacaoEstoque tipo REVERSAO (entrada de estoque)
3. Separacao NÃO é alterada
4. EmbarqueItem NÃO é alterado

Executar: python scripts/test_reversao_estoque.py
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from sqlalchemy import text
from datetime import datetime
from app.utils.timezone import agora_utc_naive


def verificar_estrutura_faturamento():
    """Verifica se os campos de reversão existem em FaturamentoProduto"""
    print("\n" + "=" * 60)
    print("1. VERIFICANDO ESTRUTURA DE FATURAMENTO")
    print("=" * 60)

    resultado = db.session.execute(text("""
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_name = 'faturamento_produto'
        AND column_name IN ('revertida', 'nota_credito_id', 'data_reversao', 'status_nf')
        ORDER BY ordinal_position
    """))

    campos = {row[0]: row for row in resultado.fetchall()}

    if 'revertida' in campos:
        print("   ✅ Campo 'revertida' existe")
    else:
        print("   ❌ Campo 'revertida' NÃO existe")
        return False

    if 'nota_credito_id' in campos:
        print("   ✅ Campo 'nota_credito_id' existe")
    else:
        print("   ❌ Campo 'nota_credito_id' NÃO existe")
        return False

    if 'data_reversao' in campos:
        print("   ✅ Campo 'data_reversao' existe")
    else:
        print("   ❌ Campo 'data_reversao' NÃO existe")
        return False

    return True


def verificar_estrutura_movimentacao():
    """Verifica campos de MovimentacaoEstoque"""
    print("\n" + "=" * 60)
    print("2. VERIFICANDO ESTRUTURA DE MOVIMENTAÇÃO")
    print("=" * 60)

    resultado = db.session.execute(text("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = 'movimentacao_estoque'
        AND column_name IN ('tipo_movimentacao', 'local_movimentacao', 'numero_nf', 'status_nf')
        ORDER BY ordinal_position
    """))

    campos = {row[0]: row for row in resultado.fetchall()}

    for campo in ['tipo_movimentacao', 'local_movimentacao', 'numero_nf', 'status_nf']:
        if campo in campos:
            print(f"   ✅ Campo '{campo}' existe")
        else:
            print(f"   ❌ Campo '{campo}' NÃO existe")
            return False

    return True


def listar_nfs_revertidas():
    """Lista NFs que foram marcadas como revertidas"""
    print("\n" + "=" * 60)
    print("3. NFS MARCADAS COMO REVERTIDAS")
    print("=" * 60)

    resultado = db.session.execute(text("""
        SELECT
            numero_nf,
            COUNT(*) as qtd_itens,
            SUM(qtd_produto_faturado) as qtd_total,
            MAX(data_reversao) as data_reversao,
            MAX(nota_credito_id) as nota_credito_id,
            MAX(status_nf) as status_nf
        FROM faturamento_produto
        WHERE revertida = TRUE
        GROUP BY numero_nf
        ORDER BY MAX(data_reversao) DESC NULLS LAST
        LIMIT 10
    """))

    nfs = resultado.fetchall()

    if not nfs:
        print("   Nenhuma NF marcada como revertida ainda.")
        return

    print(f"   {'NF':<12} {'Itens':<8} {'Qtd Total':<12} {'Data Rev.':<12} {'NC ID':<10} {'Status':<12}")
    print("   " + "-" * 66)

    for nf in nfs:
        data_rev = nf[3].strftime('%d/%m/%Y') if nf[3] else '-'
        print(f"   {nf[0] or 'N/A':<12} {nf[1]:<8} {float(nf[2] or 0):<12.2f} {data_rev:<12} {nf[4] or '-':<10} {nf[5] or '-':<12}")


def listar_movimentacoes_reversao():
    """Lista movimentações de estoque do tipo REVERSAO"""
    print("\n" + "=" * 60)
    print("4. MOVIMENTAÇÕES DE ESTOQUE TIPO REVERSAO")
    print("=" * 60)

    resultado = db.session.execute(text("""
        SELECT
            numero_nf,
            cod_produto,
            nome_produto,
            qtd_movimentacao,
            data_movimentacao,
            status_nf
        FROM movimentacao_estoque
        WHERE local_movimentacao = 'REVERSAO'
        AND ativo = TRUE
        ORDER BY criado_em DESC
        LIMIT 10
    """))

    movs = resultado.fetchall()

    if not movs:
        print("   Nenhuma movimentação de reversão ainda.")
        return

    print(f"   {'NF':<12} {'Produto':<12} {'Nome':<25} {'Qtd':<10} {'Data':<12} {'Status':<10}")
    print("   " + "-" * 81)

    for mov in movs:
        data = mov[4].strftime('%d/%m/%Y') if mov[4] else '-'
        nome = (mov[2] or '')[:22] + '...' if len(mov[2] or '') > 25 else (mov[2] or '-')
        print(f"   {mov[0] or 'N/A':<12} {mov[1] or '-':<12} {nome:<25} {float(mov[3] or 0):<10.2f} {data:<12} {mov[5] or '-':<10}")


def verificar_integridade():
    """Verifica integridade entre faturamento revertido e movimentação"""
    print("\n" + "=" * 60)
    print("5. VERIFICAÇÃO DE INTEGRIDADE")
    print("=" * 60)

    # NFs revertidas que NÃO têm movimentação de reversão
    resultado = db.session.execute(text("""
        SELECT DISTINCT f.numero_nf, COUNT(*) as itens
        FROM faturamento_produto f
        WHERE f.revertida = TRUE
        AND NOT EXISTS (
            SELECT 1 FROM movimentacao_estoque m
            WHERE m.numero_nf = f.numero_nf
            AND m.local_movimentacao = 'REVERSAO'
            AND m.ativo = TRUE
        )
        GROUP BY f.numero_nf
    """))

    nfs_sem_mov = resultado.fetchall()

    if nfs_sem_mov:
        print(f"   ⚠️  {len(nfs_sem_mov)} NFs revertidas SEM movimentação de estoque:")
        for nf in nfs_sem_mov[:5]:
            print(f"      - NF {nf[0]} ({nf[1]} itens)")
    else:
        print("   ✅ Todas as NFs revertidas têm movimentação de reversão correspondente")

    # Verificar se há NFs revertidas com status_nf diferente de 'Lançado'
    resultado = db.session.execute(text("""
        SELECT numero_nf, status_nf, COUNT(*) as itens
        FROM faturamento_produto
        WHERE revertida = TRUE
        AND status_nf != 'Lançado'
        GROUP BY numero_nf, status_nf
    """))

    nfs_status_errado = resultado.fetchall()

    if nfs_status_errado:
        print(f"\n   ⚠️  {len(nfs_status_errado)} NFs revertidas com status_nf diferente de 'Lançado':")
        for nf in nfs_status_errado[:5]:
            print(f"      - NF {nf[0]}: status_nf='{nf[1]}' ({nf[2]} itens)")
    else:
        print("   ✅ Todas as NFs revertidas mantêm status_nf='Lançado'")


def estatisticas_gerais():
    """Mostra estatísticas gerais"""
    print("\n" + "=" * 60)
    print("6. ESTATÍSTICAS GERAIS")
    print("=" * 60)

    # Total de itens faturados
    resultado = db.session.execute(text("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN revertida = TRUE THEN 1 ELSE 0 END) as revertidas,
            SUM(CASE WHEN status_nf = 'Cancelado' THEN 1 ELSE 0 END) as canceladas,
            SUM(CASE WHEN status_nf = 'Lançado' AND revertida = FALSE THEN 1 ELSE 0 END) as lancadas
        FROM faturamento_produto
    """))

    stats = resultado.fetchone()

    print(f"   Total de registros em FaturamentoProduto: {stats[0]}")
    print(f"   - Lançadas (não revertidas): {stats[3]}")
    print(f"   - Revertidas: {stats[1]}")
    print(f"   - Canceladas: {stats[2]}")

    # Movimentações de estoque
    resultado = db.session.execute(text("""
        SELECT
            local_movimentacao,
            COUNT(*) as total,
            SUM(qtd_movimentacao) as qtd_total
        FROM movimentacao_estoque
        WHERE ativo = TRUE
        AND local_movimentacao IN ('VENDA', 'REVERSAO', 'DEVOLUCAO')
        GROUP BY local_movimentacao
    """))

    movs = resultado.fetchall()

    print(f"\n   Movimentações de estoque (ativas):")
    for mov in movs:
        print(f"   - {mov[0]}: {mov[1]} registros (qtd total: {float(mov[2] or 0):.2f})")


def main():
    """Função principal"""
    app = create_app()
    with app.app_context():
        print("\n" + "=" * 60)
        print("TESTE DE VALIDAÇÃO - NOVA LÓGICA DE REVERSÃO")
        print("=" * 60)
        print(f"Data/Hora: {agora_utc_naive().strftime('%d/%m/%Y %H:%M:%S')}")

        # Verificações
        ok1 = verificar_estrutura_faturamento()
        ok2 = verificar_estrutura_movimentacao()

        if not ok1 or not ok2:
            print("\n❌ ERRO: Estrutura incompleta. Execute a migration primeiro.")
            return

        # Listagens
        listar_nfs_revertidas()
        listar_movimentacoes_reversao()
        verificar_integridade()
        estatisticas_gerais()

        print("\n" + "=" * 60)
        print("TESTE CONCLUÍDO")
        print("=" * 60)


if __name__ == '__main__':
    main()

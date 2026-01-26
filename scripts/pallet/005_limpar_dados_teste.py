#!/usr/bin/env python
"""
Script de limpeza de dados de teste das tabelas Pallet V2.

Remove TODOS os registros das tabelas v2 para permitir migração limpa
dos dados reais de MovimentacaoEstoque.

Tabelas afetadas (ordem de DELETE respeitando FKs):
1. pallet_nf_solucoes → FK para pallet_solucoes e pallet_nf_remessa
2. pallet_solucoes → FK para pallet_creditos
3. pallet_documentos → FK para pallet_creditos
4. pallet_creditos → FK para pallet_nf_remessa
5. pallet_nf_remessa → tabela base

Uso:
    cd /home/rafaelnascimento/projetos/frete_sistema
    source .venv/bin/activate
    python scripts/pallet/005_limpar_dados_teste.py

    # Para dry-run (não executa, apenas mostra o que faria):
    python scripts/pallet/005_limpar_dados_teste.py --dry-run
"""
import sys
import os
import argparse

# Adicionar o diretório raiz ao path para imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


# Ordem de limpeza respeitando Foreign Keys
# (tabelas filhas primeiro, depois tabelas pai)
TABELAS_ORDEM_DELETE = [
    'pallet_nf_solucoes',  # FK: pallet_solucoes, pallet_nf_remessa
    'pallet_solucoes',     # FK: pallet_creditos
    'pallet_documentos',   # FK: pallet_creditos
    'pallet_creditos',     # FK: pallet_nf_remessa
    'pallet_nf_remessa',   # Tabela base
]


def verificar_tabelas_existem():
    """Verifica se as tabelas existem"""
    print("\n📋 Verificando tabelas...")

    tabelas_existentes = []

    for tabela in TABELAS_ORDEM_DELETE:
        result = db.session.execute(text(f"""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = '{tabela}'
            )
        """)).scalar()

        if result:
            tabelas_existentes.append(tabela)
            print(f"  ✅ {tabela} existe")
        else:
            print(f"  ⚠️  {tabela} NÃO existe (pulando)")

    return tabelas_existentes


def contar_registros(tabela):
    """Conta registros em uma tabela"""
    result = db.session.execute(text(f"SELECT COUNT(*) FROM {tabela}")).scalar()
    return result or 0


def listar_criadores(tabela):
    """Lista criadores únicos de uma tabela (se tiver coluna criado_por)"""
    try:
        result = db.session.execute(text(f"""
            SELECT criado_por, COUNT(*) as qtd
            FROM {tabela}
            GROUP BY criado_por
            ORDER BY qtd DESC
        """)).fetchall()
        return result
    except Exception:
        return []


def limpar_tabela(tabela, dry_run=False):
    """Limpa todos os registros de uma tabela"""
    count = contar_registros(tabela)

    if count == 0:
        print(f"  ℹ️  {tabela}: já vazia")
        return 0

    if dry_run:
        print(f"  🔍 DRY-RUN: {tabela}: deletaria {count} registros")
        return count

    db.session.execute(text(f"DELETE FROM {tabela}"))
    print(f"  🗑️  {tabela}: deletados {count} registros")
    return count


def executar_limpeza(dry_run=False):
    """Executa a limpeza completa"""
    print("=" * 70)
    print("  LIMPEZA DE DADOS DE TESTE - PALLET V2")
    print("=" * 70)

    if dry_run:
        print("\n⚠️  MODO DRY-RUN: Nenhuma alteração será feita no banco\n")

    # 1. Verificar tabelas
    tabelas = verificar_tabelas_existem()

    if not tabelas:
        print("\n⚠️  Nenhuma tabela v2 encontrada!")
        return False

    # 2. Mostrar estatísticas antes
    print("\n📊 Estatísticas ANTES da limpeza:")
    total_registros = 0

    for tabela in tabelas:
        count = contar_registros(tabela)
        total_registros += count
        criadores = listar_criadores(tabela)

        print(f"\n  {tabela}: {count} registros")
        for criador in criadores[:3]:  # Top 3 criadores
            print(f"    - {criador.criado_por}: {criador.qtd}")

    if total_registros == 0:
        print("\n✅ Tabelas já estão vazias. Nada a fazer.")
        return True

    # 3. Executar limpeza
    print("\n🔄 Iniciando limpeza...")

    deletados = 0
    for tabela in tabelas:
        deletados += limpar_tabela(tabela, dry_run=dry_run)

    # 4. Commit
    if not dry_run:
        db.session.commit()

    # 5. Relatório final
    print("\n" + "=" * 70)
    print("  RELATÓRIO DE LIMPEZA")
    print("=" * 70)
    print(f"  Total de registros deletados: {deletados}")

    if not dry_run:
        print("\n📊 Estatísticas APÓS a limpeza:")
        for tabela in tabelas:
            count = contar_registros(tabela)
            print(f"  {tabela}: {count} registros")

    print("=" * 70)

    return True


def main():
    """Função principal"""
    parser = argparse.ArgumentParser(
        description='Limpa dados de teste das tabelas Pallet V2'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Executa em modo dry-run (não altera o banco)'
    )

    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        try:
            sucesso = executar_limpeza(dry_run=args.dry_run)

            if sucesso:
                print("\n✅ Limpeza concluída com sucesso!")
                print("\n💡 Próximo passo:")
                print("   python scripts/pallet/002_migrar_movimentacao_para_nf_remessa.py\n")
                sys.exit(0)
            else:
                print("\n❌ Limpeza falhou. Verifique os erros acima.\n")
                sys.exit(1)

        except Exception as e:
            print(f"\n❌ Erro fatal: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)


if __name__ == '__main__':
    main()

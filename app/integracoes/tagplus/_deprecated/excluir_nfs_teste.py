#!/usr/bin/env python3
"""
Script para excluir NFs de teste (3753 até 3771) de FaturamentoProduto e NFPendenteTagPlus
Permite realizar testes de importação com essas NFs novamente

Uso:
    python app/integracoes/tagplus/excluir_nfs_teste.py
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# Adiciona o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parents[3]))

from app import create_app, db
from app.faturamento.models import FaturamentoProduto
from app.integracoes.tagplus.models import NFPendenteTagPlus

def excluir_nfs_teste(dry_run=False):
    """
    Exclui NFs de teste das tabelas FaturamentoProduto e NFPendenteTagPlus

    Args:
        dry_run (bool): Se True, apenas mostra o que seria excluído sem executar
    """
    # Lista de NFs para excluir
    nfs_para_excluir = [str(i) for i in range(3753, 3772)]  # 3753 até 3771

    print("\n" + "="*70)
    print("EXCLUIR NFs DE TESTE")
    print("="*70)
    print(f"NFs para excluir: {', '.join(nfs_para_excluir)}")
    print(f"Modo: {'DRY RUN (simulação)' if dry_run else 'EXECUÇÃO REAL'}")
    print("-"*70)

    total_faturamento = 0
    total_pendentes = 0

    try:
        # 1. Buscar e excluir de FaturamentoProduto
        print("\n📋 Verificando FaturamentoProduto...")

        for nf_num in nfs_para_excluir:
            itens_faturamento = FaturamentoProduto.query.filter_by(numero_nf=nf_num).all()

            if itens_faturamento:
                print(f"\n  NF {nf_num}:")
                print(f"    - {len(itens_faturamento)} itens encontrados")

                # Mostra detalhes dos itens
                for item in itens_faturamento:
                    print(f"      • {item.cod_produto} - {item.nome_produto[:40]} - Qtd: {item.qtd_produto_faturado}")

                if not dry_run:
                    for item in itens_faturamento:
                        db.session.delete(item)
                    print(f"    ✅ Excluídos {len(itens_faturamento)} itens")
                else:
                    print(f"    ⚠️  [DRY RUN] Seriam excluídos {len(itens_faturamento)} itens")

                total_faturamento += len(itens_faturamento)

        # 2. Buscar e excluir de NFPendenteTagPlus
        print("\n📋 Verificando NFPendenteTagPlus...")

        for nf_num in nfs_para_excluir:
            itens_pendentes = NFPendenteTagPlus.query.filter_by(numero_nf=nf_num).all()

            if itens_pendentes:
                print(f"\n  NF {nf_num}:")
                print(f"    - {len(itens_pendentes)} itens pendentes encontrados")
                print(f"    - Resolvido: {any(item.resolvido for item in itens_pendentes)}")
                print(f"    - Importado: {any(item.importado for item in itens_pendentes)}")

                # Mostra detalhes
                for item in itens_pendentes:
                    status = []
                    if item.resolvido:
                        status.append("✓ Resolvido")
                    if item.importado:
                        status.append("✓ Importado")
                    if item.origem:
                        status.append(f"Pedido: {item.origem}")

                    status_str = " | ".join(status) if status else "❌ Pendente"
                    print(f"      • {item.cod_produto} - {item.nome_produto[:30]} - {status_str}")

                if not dry_run:
                    for item in itens_pendentes:
                        db.session.delete(item)
                    print(f"    ✅ Excluídos {len(itens_pendentes)} itens pendentes")
                else:
                    print(f"    ⚠️  [DRY RUN] Seriam excluídos {len(itens_pendentes)} itens pendentes")

                total_pendentes += len(itens_pendentes)

        # Commit das exclusões
        if not dry_run:
            db.session.commit()
            print("\n✅ Alterações salvas no banco de dados")

        # Resumo final
        print("\n" + "="*70)
        print("RESUMO DA OPERAÇÃO")
        print("="*70)

        if dry_run:
            print("🔍 MODO DRY RUN - Nenhuma exclusão foi realizada")
            print(f"   - FaturamentoProduto: {total_faturamento} itens seriam excluídos")
            print(f"   - NFPendenteTagPlus: {total_pendentes} itens seriam excluídos")
            print(f"   - Total: {total_faturamento + total_pendentes} itens seriam excluídos")
            print("\nPara executar de verdade, use: --execute")
        else:
            print("✅ EXCLUSÃO CONCLUÍDA COM SUCESSO")
            print(f"   - FaturamentoProduto: {total_faturamento} itens excluídos")
            print(f"   - NFPendenteTagPlus: {total_pendentes} itens excluídos")
            print(f"   - Total: {total_faturamento + total_pendentes} itens excluídos")

        print("="*70 + "\n")

    except Exception as e:
        db.session.rollback()
        print(f"\n❌ Erro ao excluir NFs: {e}")
        raise

def main():
    """Função principal"""
    # Verifica argumentos
    dry_run = '--execute' not in sys.argv

    # Cria aplicação Flask
    app = create_app()

    with app.app_context():
        # Confirmação do usuário se for execução real
        if not dry_run:
            print("\n⚠️  ATENÇÃO: Você está prestes a EXCLUIR dados do banco de dados!")
            print("   NFs que serão excluídas: 3753 até 3771")
            print("   Tabelas afetadas: FaturamentoProduto e NFPendenteTagPlus")
            resposta = input("\n   Tem certeza que deseja continuar? (sim/não): ").lower()

            if resposta not in ['sim', 's', 'yes', 'y']:
                print("\n❌ Operação cancelada pelo usuário")
                return

        # Executa exclusão
        excluir_nfs_teste(dry_run=dry_run)

if __name__ == "__main__":
    main()
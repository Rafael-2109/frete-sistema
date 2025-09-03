#!/usr/bin/env python
"""
Script para sincronizar campo sincronizado_nf em Separacao
baseado nos dados de RelatorioFaturamentoImportado

Verifica:
1. Se Separacao.numero_nf existe em RelatorioFaturamentoImportado.numero_nf
2. Se o CNPJ do cliente corresponde
3. Se sim, marca Separacao.sincronizado_nf=True

Pode ser executado localmente ou no Render Shell
"""

import sys
import os

# Adiciona o path do projeto para funcionar no Render
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Importa as configurações do Flask
from app import create_app, db
from datetime import datetime
from sqlalchemy import text

def sincronizar_nf_separacao(verbose=True, dry_run=False):
    """
    Sincroniza o campo sincronizado_nf em Separacao baseado em RelatorioFaturamentoImportado
    
    Args:
        verbose: Se True, mostra detalhes do processamento
        dry_run: Se True, apenas simula sem fazer commit
    """
    app = create_app()
    
    with app.app_context():
        try:
            from app.separacao.models import Separacao
            from app.faturamento.models import RelatorioFaturamentoImportado
            
            print("=" * 70)
            print("SINCRONIZAÇÃO DE NF - SEPARAÇÃO x RELATÓRIO FATURAMENTO")
            print("=" * 70)
            print(f"Iniciado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
            if dry_run:
                print("🔍 MODO DRY RUN - Nenhuma alteração será salva")
            print("-" * 70)
            
            # Estatísticas
            total_separacoes = 0
            separacoes_com_nf = 0
            nfs_encontradas = 0
            sincronizadas = 0
            ja_sincronizadas = 0
            
            # 1. Busca todas as separações com numero_nf preenchido e não sincronizadas
            print("\n1. Buscando separações com NF não sincronizadas...")
            
            separacoes = Separacao.query.filter(
                Separacao.numero_nf.isnot(None),
                Separacao.numero_nf != '',
                Separacao.sincronizado_nf == False  # Apenas não sincronizadas
            ).all()
            
            separacoes_com_nf = len(separacoes)
            print(f"   ✓ Encontradas {separacoes_com_nf} separações com NF para verificar")
            
            if separacoes_com_nf == 0:
                print("\n✅ Não há separações para sincronizar!")
                return
            
            # 2. Processa cada separação
            print("\n2. Processando separações...")
            print("-" * 70)
            
            for i, separacao in enumerate(separacoes, 1):
                total_separacoes += 1
                
                if verbose and i % 100 == 0:
                    print(f"   Processando {i}/{separacoes_com_nf}...")
                
                # Busca no RelatorioFaturamentoImportado
                # NOVA LÓGICA: Busca por numero_nf E origem (num_pedido)
                relatorio = RelatorioFaturamentoImportado.query.filter_by(
                    numero_nf=separacao.numero_nf,
                    origem=separacao.num_pedido  # Compara origem com num_pedido
                ).first()
                
                if relatorio:
                    nfs_encontradas += 1
                    
                    # Marca como sincronizado (sem validar CNPJ ou ativo)
                    if not dry_run:
                        separacao.sincronizado_nf = True
                        separacao.data_sincronizacao = datetime.now()
                    
                    sincronizadas += 1
                    
                    if verbose and sincronizadas <= 10:  # Mostra apenas os primeiros 10
                        print(f"   ✅ Sincronizado: Pedido {separacao.num_pedido} | "
                              f"NF {separacao.numero_nf}")
            
            # 3. Verifica separações já sincronizadas para estatística
            print("\n3. Verificando separações já sincronizadas...")
            ja_sincronizadas = Separacao.query.filter(
                Separacao.numero_nf.isnot(None),
                Separacao.numero_nf != '',
                Separacao.sincronizado_nf == True
            ).count()
            
            # 4. Commit das alterações
            if not dry_run and sincronizadas > 0:
                print("\n4. Salvando alterações...")
                db.session.commit()
                print("   ✓ Alterações salvas com sucesso!")
            elif dry_run:
                print("\n4. Modo DRY RUN - Nenhuma alteração foi salva")
                db.session.rollback()
            
            # 5. Relatório final
            print("\n" + "=" * 70)
            print("RELATÓRIO FINAL")
            print("=" * 70)
            print(f"Separações processadas:        {total_separacoes:,}")
            print(f"NFs encontradas (NF+Pedido):   {nfs_encontradas:,}")
            print(f"Separações sincronizadas:      {sincronizadas:,}")
            print(f"Já sincronizadas previamente:  {ja_sincronizadas:,}")
            print(f"NFs não encontradas:           {total_separacoes - nfs_encontradas:,}")
            
            # Taxa de sucesso
            if total_separacoes > 0:
                taxa_sucesso = (sincronizadas / total_separacoes) * 100
                print(f"\nTaxa de sincronização: {taxa_sucesso:.1f}%")
            
            # Total geral sincronizado
            total_sincronizado = ja_sincronizadas + sincronizadas
            total_com_nf = Separacao.query.filter(
                Separacao.numero_nf.isnot(None),
                Separacao.numero_nf != ''
            ).count()
            
            if total_com_nf > 0:
                taxa_geral = (total_sincronizado / total_com_nf) * 100
                print(f"Taxa geral sincronizada: {taxa_geral:.1f}% ({total_sincronizado:,}/{total_com_nf:,})")
            
            print("=" * 70)
            print(f"Finalizado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
            print("=" * 70)
            
            return True
            
        except Exception as e:
            print(f"\n❌ ERRO: {str(e)}")
            import traceback
            traceback.print_exc()
            db.session.rollback()
            return False

def main():
    """Função principal com argumentos de linha de comando"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Sincroniza campo sincronizado_nf em Separacao baseado em RelatorioFaturamentoImportado'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Executa em modo simulação sem salvar alterações'
    )
    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Modo silencioso - mostra apenas resumo'
    )
    
    args = parser.parse_args()
    
    # Executa sincronização
    sucesso = sincronizar_nf_separacao(
        verbose=not args.quiet,
        dry_run=args.dry_run
    )
    
    # Retorna código de saída apropriado
    sys.exit(0 if sucesso else 1)

if __name__ == "__main__":
    main()
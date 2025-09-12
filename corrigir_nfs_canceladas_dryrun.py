#!/usr/bin/env python3
"""
Script de correção de NFs canceladas com modo DRY RUN
Permite simular as alterações sem aplicá-las no banco

Uso:
    python corrigir_nfs_canceladas_dryrun.py           # Modo dry-run (padrão)
    python corrigir_nfs_canceladas_dryrun.py --execute  # Modo execução real
    python corrigir_nfs_canceladas_dryrun.py --nf 139272  # Testar NF específica
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.odoo.services.faturamento_service import FaturamentoService
from app.faturamento.models import FaturamentoProduto
from app.estoque.models import MovimentacaoEstoque
from app.separacao.models import Separacao
from app.embarques.models import EmbarqueItem
from datetime import datetime
import logging
import argparse

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def verificar_nf_cancelada(numero_nf: str, dry_run: bool = True):
    """
    Verifica e opcionalmente corrige uma NF cancelada específica
    
    Args:
        numero_nf: Número da NF a verificar
        dry_run: Se True, apenas simula. Se False, executa alterações
    
    Returns:
        Dict com informações sobre a NF
    """
    info = {
        'numero_nf': numero_nf,
        'existe_no_banco': False,
        'status_odoo': None,
        'precisa_correcao': False,
        'faturamentos': 0,
        'movimentacoes': 0,
        'embarques': 0,
        'separacoes': 0,
        'alteracoes_necessarias': []
    }
    
    try:
        # Verificar no Odoo
        service = FaturamentoService()
        connection = service.connection
        
        faturas = connection.search_read(
            'account.move',
            [('l10n_br_numero_nota_fiscal', '=', numero_nf)],
            ['id', 'state', 'l10n_br_numero_nota_fiscal', 'partner_id', 'date']
        )
        
        if faturas:
            fatura = faturas[0]
            info['status_odoo'] = fatura['state']
            
            if fatura['state'] == 'cancel':
                # Verificar no banco
                faturamentos = FaturamentoProduto.query.filter_by(numero_nf=numero_nf).all()
                info['faturamentos'] = len(faturamentos)
                info['existe_no_banco'] = len(faturamentos) > 0
                
                # Verificar se precisa correção
                fats_nao_cancelados = [f for f in faturamentos if f.status_nf != 'Cancelado']
                if fats_nao_cancelados:
                    info['precisa_correcao'] = True
                    info['alteracoes_necessarias'].append(
                        f"FaturamentoProduto: {len(fats_nao_cancelados)} registros para marcar como Cancelado"
                    )
                
                # Verificar MovimentacaoEstoque
                movs = MovimentacaoEstoque.query.filter_by(numero_nf=numero_nf, ativo=True).all()
                info['movimentacoes'] = len(movs)
                if movs:
                    info['precisa_correcao'] = True
                    info['alteracoes_necessarias'].append(
                        f"MovimentacaoEstoque: {len(movs)} registros para marcar como inativo"
                    )
                
                # Verificar EmbarqueItem
                embarques = EmbarqueItem.query.filter_by(nota_fiscal=numero_nf).all()
                info['embarques'] = len(embarques)
                if embarques:
                    info['precisa_correcao'] = True
                    info['alteracoes_necessarias'].append(
                        f"EmbarqueItem: {len(embarques)} registros para limpar NF"
                    )
                
                # Verificar Separacao
                separacoes = Separacao.query.filter_by(numero_nf=numero_nf).all()
                info['separacoes'] = len(separacoes)
                if separacoes:
                    info['precisa_correcao'] = True
                    info['alteracoes_necessarias'].append(
                        f"Separacao: {len(separacoes)} registros para reverter sincronização"
                    )
                
                # Se não é dry run e precisa correção, executar
                if not dry_run and info['precisa_correcao']:
                    resultado = service._processar_cancelamento_nf(numero_nf)
                    info['corrigido'] = resultado
                    
    except Exception as e:
        info['erro'] = str(e)
    
    return info

def processar_nfs_canceladas_dryrun(dry_run: bool = True, limite: int = 1000):
    """
    Processa NFs canceladas com opção de dry run
    
    Args:
        dry_run: Se True, apenas simula. Se False, executa alterações
        limite: Número máximo de NFs a processar
    
    Returns:
        Dict com estatísticas do processamento
    """
    try:
        print(f"\n{'='*80}")
        if dry_run:
            print("🔍 MODO DRY RUN - SIMULAÇÃO (nenhuma alteração será feita)")
        else:
            print("⚠️  MODO EXECUÇÃO REAL - ALTERAÇÕES SERÃO APLICADAS")
        print(f"{'='*80}\n")
        
        service = FaturamentoService()
        connection = service.connection
        
        # Buscar NFs canceladas no Odoo
        print("📋 Buscando NFs canceladas no Odoo...")
        faturas_canceladas = connection.search_read(
            'account.move',
            [
                ('state', '=', 'cancel'),
                ('l10n_br_numero_nota_fiscal', '!=', False),
                '|',
                ('l10n_br_tipo_pedido', '=', 'venda'),
                ('l10n_br_tipo_pedido', '=', 'bonificacao')
            ],
            ['id', 'l10n_br_numero_nota_fiscal', 'state', 'date', 'partner_id'],
            limit=limite
        )
        
        print(f"✅ Encontradas {len(faturas_canceladas)} NFs canceladas no Odoo\n")
        
        # Estatísticas
        stats = {
            'total_odoo': len(faturas_canceladas),
            'precisam_correcao': 0,
            'ja_corretas': 0,
            'nao_existentes': 0,
            'corrigidas': 0,
            'detalhes': []
        }
        
        print("🔄 Analisando NFs...")
        print("-" * 80)
        
        for i, fatura in enumerate(faturas_canceladas, 1):
            numero_nf = fatura.get('l10n_br_numero_nota_fiscal')
            if not numero_nf:
                continue
            
            # Verificar NF
            info = verificar_nf_cancelada(numero_nf, dry_run)
            
            if info['existe_no_banco']:
                if info['precisa_correcao']:
                    stats['precisam_correcao'] += 1
                    if not dry_run and info.get('corrigido'):
                        stats['corrigidas'] += 1
                    
                    # Mostrar detalhes das primeiras 10 que precisam correção
                    if stats['precisam_correcao'] <= 10:
                        print(f"\n📌 NF {numero_nf}:")
                        print(f"   Status Odoo: {info['status_odoo']}")
                        print(f"   Registros no banco:")
                        print(f"   - FaturamentoProduto: {info['faturamentos']}")
                        print(f"   - MovimentacaoEstoque: {info['movimentacoes']}")
                        print(f"   - EmbarqueItem: {info['embarques']}")
                        print(f"   - Separacao: {info['separacoes']}")
                        print(f"   Alterações necessárias:")
                        for alt in info['alteracoes_necessarias']:
                            print(f"   → {alt}")
                        if not dry_run:
                            status = "✅ CORRIGIDO" if info.get('corrigido') else "❌ ERRO"
                            print(f"   Status: {status}")
                else:
                    stats['ja_corretas'] += 1
            else:
                stats['nao_existentes'] += 1
            
            # Mostrar progresso a cada 50 NFs
            if i % 50 == 0:
                print(f"\n⏳ Processadas {i}/{len(faturas_canceladas)} NFs...")
        
        # Resumo final
        print(f"\n{'='*80}")
        print("📊 RESUMO DO PROCESSAMENTO")
        print(f"{'='*80}")
        print(f"Total de NFs canceladas no Odoo: {stats['total_odoo']}")
        print(f"NFs que precisam correção: {stats['precisam_correcao']}")
        print(f"NFs já corretas: {stats['ja_corretas']}")
        print(f"NFs não existentes no banco: {stats['nao_existentes']}")
        
        if not dry_run:
            print(f"NFs corrigidas: {stats['corrigidas']}")
        else:
            print(f"\n💡 MODO DRY RUN - Para executar as correções, use:")
            print(f"   python {sys.argv[0]} --execute")
        
        print(f"{'='*80}\n")
        
        return stats
        
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """Função principal com argumentos de linha de comando"""
    
    parser = argparse.ArgumentParser(
        description='Corrige NFs canceladas no Odoo',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:
  %(prog)s                    # Modo dry-run (padrão)
  %(prog)s --execute          # Executa correções
  %(prog)s --nf 139272        # Verifica NF específica
  %(prog)s --nf 139272 --execute  # Corrige NF específica
  %(prog)s --limite 100       # Processa apenas 100 NFs
        """
    )
    
    parser.add_argument(
        '--execute', '-e',
        action='store_true',
        help='Executa as correções (sem esta flag, apenas simula)'
    )
    
    parser.add_argument(
        '--nf',
        type=str,
        help='Processa apenas uma NF específica'
    )
    
    parser.add_argument(
        '--limite',
        type=int,
        default=1000,
        help='Número máximo de NFs a processar (padrão: 1000)'
    )
    
    args = parser.parse_args()
    
    app = create_app()
    with app.app_context():
        try:
            if args.nf:
                # Processar NF específica
                print(f"\n🔍 Verificando NF {args.nf}...")
                info = verificar_nf_cancelada(args.nf, dry_run=not args.execute)
                
                print(f"\n📋 INFORMAÇÕES DA NF {args.nf}:")
                print(f"   Status no Odoo: {info['status_odoo']}")
                print(f"   Existe no banco: {'SIM' if info['existe_no_banco'] else 'NÃO'}")
                
                if info['existe_no_banco']:
                    print(f"   Precisa correção: {'SIM' if info['precisa_correcao'] else 'NÃO'}")
                    print(f"   Registros:")
                    print(f"   - FaturamentoProduto: {info['faturamentos']}")
                    print(f"   - MovimentacaoEstoque: {info['movimentacoes']}")
                    print(f"   - EmbarqueItem: {info['embarques']}")
                    print(f"   - Separacao: {info['separacoes']}")
                    
                    if info['alteracoes_necessarias']:
                        print(f"   Alterações necessárias:")
                        for alt in info['alteracoes_necessarias']:
                            print(f"   → {alt}")
                    
                    if not args.execute and info['precisa_correcao']:
                        print(f"\n💡 Para corrigir esta NF, use:")
                        print(f"   python {sys.argv[0]} --nf {args.nf} --execute")
                    elif args.execute and info.get('corrigido'):
                        print(f"\n✅ NF CORRIGIDA COM SUCESSO!")
            else:
                # Processar todas as NFs
                processar_nfs_canceladas_dryrun(
                    dry_run=not args.execute,
                    limite=args.limite
                )
                
        except Exception as e:
            print(f"\n❌ ERRO FATAL: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

if __name__ == "__main__":
    main()
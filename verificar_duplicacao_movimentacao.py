#!/usr/bin/env python3
"""
Script para verificar duplicação de MovimentacaoEstoque
Identifica registros duplicados por numero_nf + cod_produto
"""

from app import create_app, db
from app.estoque.models import MovimentacaoEstoque
from sqlalchemy import func
import logging

app = create_app()

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def verificar_duplicacoes():
    """Verifica duplicações em MovimentacaoEstoque"""
    
    with app.app_context():
        logger.info("🔍 Verificando duplicações em MovimentacaoEstoque...")
        
        # 1. Verificar duplicações por numero_nf + cod_produto
        duplicados = db.session.query(
            MovimentacaoEstoque.numero_nf,
            MovimentacaoEstoque.cod_produto,
            func.count(MovimentacaoEstoque.id).label('count')
        ).filter(
            MovimentacaoEstoque.numero_nf.isnot(None),
            MovimentacaoEstoque.status_nf == 'FATURADO'
        ).group_by(
            MovimentacaoEstoque.numero_nf,
            MovimentacaoEstoque.cod_produto
        ).having(
            func.count(MovimentacaoEstoque.id) > 1
        ).all()
        
        if duplicados:
            logger.warning(f"⚠️ Encontradas {len(duplicados)} combinações duplicadas!")
            print("\n📊 DUPLICAÇÕES ENCONTRADAS:")
            print("-" * 80)
            
            total_registros_duplicados = 0
            exemplos_lote = []
            
            for nf, produto, count in duplicados[:10]:  # Mostrar até 10 exemplos
                print(f"\n NF: {nf} | Produto: {produto} | Ocorrências: {count}")
                
                # Buscar detalhes dos registros duplicados
                registros = MovimentacaoEstoque.query.filter_by(
                    numero_nf=nf,
                    cod_produto=produto,
                    status_nf='FATURADO'
                ).all()
                
                print("  Detalhes:")
                for reg in registros:
                    lote_info = reg.separacao_lote_id or "NULL"
                    print(f"    - ID: {reg.id} | Lote: {lote_info} | Pedido: {reg.num_pedido} | "
                          f"Qtd: {reg.qtd_movimentacao} | Criado: {reg.criado_em}")
                    
                    # Coletar exemplos de 'LOTE' antigo
                    if reg.separacao_lote_id == 'LOTE':
                        exemplos_lote.append(reg)
                
                total_registros_duplicados += count
            
            print("\n" + "=" * 80)
            print(f"📈 RESUMO:")
            print(f"  - Total de combinações duplicadas: {len(duplicados)}")
            print(f"  - Total de registros duplicados: {total_registros_duplicados}")
            
            # 2. Verificar registros com separacao_lote_id = 'LOTE'
            registros_lote = MovimentacaoEstoque.query.filter_by(
                separacao_lote_id='LOTE'
            ).count()
            
            if registros_lote > 0:
                print(f"\n⚠️ ATENÇÃO: {registros_lote} registros com separacao_lote_id='LOTE'")
                
                # Mostrar exemplos
                exemplos = MovimentacaoEstoque.query.filter_by(
                    separacao_lote_id='LOTE'
                ).limit(5).all()
                
                print("\n  Exemplos:")
                for ex in exemplos:
                    print(f"    - NF: {ex.numero_nf} | Produto: {ex.cod_produto} | "
                          f"Pedido: {ex.num_pedido} | Criado: {ex.criado_em}")
            
            # 3. Verificar registros sem lote (NULL)
            registros_sem_lote = MovimentacaoEstoque.query.filter(
                MovimentacaoEstoque.separacao_lote_id.is_(None),
                MovimentacaoEstoque.numero_nf.isnot(None),
                MovimentacaoEstoque.status_nf == 'FATURADO'
            ).count()
            
            print(f"\n📊 Registros sem lote (NULL): {registros_sem_lote}")
            
            # 4. Análise de padrões de duplicação
            print("\n🔍 ANÁLISE DE PADRÕES:")
            
            # Verificar se duplicações têm lotes diferentes
            duplicados_lotes_diferentes = 0
            for nf, produto, _ in duplicados:
                lotes = db.session.query(
                    MovimentacaoEstoque.separacao_lote_id
                ).filter_by(
                    numero_nf=nf,
                    cod_produto=produto,
                    status_nf='FATURADO'
                ).distinct().all()
                
                lotes_unicos = [l[0] for l in lotes]
                if len(lotes_unicos) > 1:
                    duplicados_lotes_diferentes += 1
            
            print(f"  - Duplicações com lotes diferentes: {duplicados_lotes_diferentes}")
            print(f"  - Duplicações com mesmo lote: {len(duplicados) - duplicados_lotes_diferentes}")
            
            return True
        else:
            logger.info("✅ Nenhuma duplicação encontrada!")
            return False

if __name__ == "__main__":
    verificar_duplicacoes()
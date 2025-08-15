#!/usr/bin/env python3
"""
Script para atualizar status dos pedidos para FATURADO
quando a NF existe em FaturamentoProduto

Execute via shell do Render:
python scripts/atualizar_status_faturado.py

Ou localmente:
python scripts/atualizar_status_faturado.py
"""

import sys
import os

# Adiciona o diretório pai ao path para importar app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from sqlalchemy import text
from datetime import datetime

def atualizar_status_faturado():
    """Atualiza status dos pedidos baseado na existência da NF em FaturamentoProduto"""
    app = create_app()
    
    with app.app_context():
        print("\n" + "="*60)
        print("🔧 ATUALIZANDO STATUS DOS PEDIDOS")
        print(f"📅 Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)
        
        try:
            # Primeiro, contar quantos pedidos têm NF preenchida
            result = db.session.execute(text("""
                SELECT COUNT(*) 
                FROM pedidos 
                WHERE nf IS NOT NULL 
                AND nf != ''
                AND status != 'FATURADO'
            """))
            total_com_nf = result.scalar()
            
            print(f"\n📊 Pedidos com NF preenchida (não FATURADO): {total_com_nf}")
            
            if total_com_nf == 0:
                print("ℹ️ Nenhum pedido para atualizar")
                return True
            
            # Buscar pedidos que têm NF em FaturamentoProduto
            print("\n🔍 Verificando NFs em FaturamentoProduto...")
            
            result = db.session.execute(text("""
                SELECT DISTINCT p.id, p.num_pedido, p.nf, p.status
                FROM pedidos p
                INNER JOIN faturamento_produtos fp ON p.nf = fp.numero_nf
                WHERE p.nf IS NOT NULL 
                AND p.nf != ''
                AND p.status != 'FATURADO'
                ORDER BY p.num_pedido
            """))
            
            pedidos_para_atualizar = result.fetchall()
            
            print(f"\n✅ Pedidos com NF encontrada em FaturamentoProduto: {len(pedidos_para_atualizar)}")
            
            if pedidos_para_atualizar:
                print("\n📝 Pedidos que serão atualizados:")
                for pedido in pedidos_para_atualizar[:10]:  # Mostrar até 10
                    print(f"   - Pedido {pedido[1]} | NF: {pedido[2]} | Status atual: {pedido[3]}")
                
                if len(pedidos_para_atualizar) > 10:
                    print(f"   ... e mais {len(pedidos_para_atualizar) - 10} pedidos")
                
                # Atualizar status para FATURADO
                print("\n🔄 Atualizando status para FATURADO...")
                
                result = db.session.execute(text("""
                    UPDATE pedidos 
                    SET status = 'FATURADO'
                    WHERE id IN (
                        SELECT DISTINCT p.id
                        FROM pedidos p
                        INNER JOIN faturamento_produtos fp ON p.nf = fp.numero_nf
                        WHERE p.nf IS NOT NULL 
                        AND p.nf != ''
                        AND p.status != 'FATURADO'
                    )
                """))
                
                linhas_atualizadas = result.rowcount
                db.session.commit()
                
                print(f"✅ {linhas_atualizadas} pedidos atualizados para FATURADO")
            
            # Verificar pedidos com NF que NÃO estão em FaturamentoProduto
            print("\n🔍 Verificando pedidos com NF sem faturamento...")
            
            result = db.session.execute(text("""
                SELECT COUNT(*)
                FROM pedidos p
                LEFT JOIN faturamento_produtos fp ON p.nf = fp.numero_nf
                WHERE p.nf IS NOT NULL 
                AND p.nf != ''
                AND fp.numero_nf IS NULL
                AND p.status = 'FATURADO'
            """))
            
            pedidos_sem_faturamento = result.scalar()
            
            if pedidos_sem_faturamento > 0:
                print(f"\n⚠️ {pedidos_sem_faturamento} pedidos com status FATURADO mas NF não encontrada em FaturamentoProduto")
                print("   Estes pedidos podem precisar de revisão ou a NF ainda não foi importada")
            
            # Estatísticas finais
            print("\n" + "="*60)
            print("📊 RESUMO FINAL:")
            print("="*60)
            
            result = db.session.execute(text("""
                SELECT status, COUNT(*) as total
                FROM pedidos
                WHERE nf IS NOT NULL AND nf != ''
                GROUP BY status
                ORDER BY total DESC
            """))
            
            print("\nPedidos com NF por status:")
            for row in result:
                print(f"   - {row[0]}: {row[1]} pedidos")
            
            print("\n✅ Atualização concluída com sucesso!")
            
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Erro durante atualização: {e}")
            return False

if __name__ == "__main__":
    try:
        print("🚀 Iniciando atualização de status...")
        success = atualizar_status_faturado()
        
        if success:
            sys.exit(0)
        else:
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ Erro fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
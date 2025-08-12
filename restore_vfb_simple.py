#!/usr/bin/env python3
"""
Script simples e direto para restaurar pedido VFB2500241
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from decimal import Decimal
from datetime import datetime

def main():
    app = create_app()
    with app.app_context():
        num_pedido = 'VFB2500241'
        lote_id = 'LOTE-20250811-351-160429'
        
        print("\n=== RESTAURAÇÃO SIMPLES VFB2500241 ===\n")
        
        # 1. Limpar alertas
        db.session.execute("""
            DELETE FROM alertas_separacao_cotada 
            WHERE num_pedido = :num_pedido
        """, {'num_pedido': num_pedido})
        print("✅ Alertas limpos")
        
        # 2. Limpar e recriar CarteiraPrincipal
        db.session.execute("""
            DELETE FROM carteira_principal 
            WHERE num_pedido = :num_pedido
        """, {'num_pedido': num_pedido})
        
        # Inserir os 3 itens originais
        db.session.execute("""
            INSERT INTO carteira_principal (
                num_pedido, cod_produto, nome_produto,
                qtd_produto_pedido, qtd_saldo_produto_pedido, qtd_cancelada_produto_pedido,
                preco_produto_pedido, peso_unitario_produto,
                cnpj_cpf, raz_social, raz_social_red, municipio, estado,
                data_pedido, expedicao, agendamento, protocolo,
                agendamento_confirmado, separacao_lote_id,
                vendedor, equipe_vendas
            ) VALUES 
            (:num_pedido, '4320162', 'DETERGENTE NEUTRO 5L',
             10, 10, 0, 25.50, 5.2,
             '07026806000172', 'MASTER COMERCIO DE PRODUTOS DE LIMPEZA LTD', 'MASTER COMERCIO', 
             'SAO PAULO', 'SP', '2025-01-10', '2025-01-13', '2025-01-14', 'PROT-2025-001',
             true, :lote_id, 'VENDEDOR01', 'EQUIPE01'),
            
            (:num_pedido, '4360162', 'DESINFETANTE LAVANDA 5L',
             10, 10, 0, 18.90, 5.1,
             '07026806000172', 'MASTER COMERCIO DE PRODUTOS DE LIMPEZA LTD', 'MASTER COMERCIO',
             'SAO PAULO', 'SP', '2025-01-10', '2025-01-13', '2025-01-14', 'PROT-2025-001',
             true, :lote_id, 'VENDEDOR01', 'EQUIPE01'),
            
            (:num_pedido, '4310162', 'MULTIUSO CLASSICO 500ML',
             10, 10, 0, 5.50, 0.52,
             '07026806000172', 'MASTER COMERCIO DE PRODUTOS DE LIMPEZA LTD', 'MASTER COMERCIO',
             'SAO PAULO', 'SP', '2025-01-10', '2025-01-13', '2025-01-14', 'PROT-2025-001',
             true, :lote_id, 'VENDEDOR01', 'EQUIPE01')
        """, {'num_pedido': num_pedido, 'lote_id': lote_id})
        
        print("✅ CarteiraPrincipal restaurada (3 itens)")
        
        # 3. Limpar e recriar Separacao
        db.session.execute("""
            DELETE FROM separacao 
            WHERE separacao_lote_id = :lote_id 
            AND num_pedido = :num_pedido
        """, {'lote_id': lote_id, 'num_pedido': num_pedido})
        
        # Inserir os 3 itens originais na separação
        db.session.execute("""
            INSERT INTO separacao (
                separacao_lote_id, num_pedido, cod_produto, nome_produto,
                qtd_saldo, valor_saldo, peso, pallet,
                cnpj_cpf, raz_social_red, nome_cidade, cod_uf,
                data_pedido, expedicao, agendamento, protocolo,
                tipo_envio, criado_em
            ) VALUES
            (:lote_id, :num_pedido, '4320162', 'DETERGENTE NEUTRO 5L',
             10, 255, 52, 0.052,
             '07026806000172', 'MASTER COMERCIO', 'SAO PAULO', 'SP',
             '2025-01-10', '2025-01-13', '2025-01-14', 'PROT-2025-001',
             'total', CURRENT_TIMESTAMP),
            
            (:lote_id, :num_pedido, '4360162', 'DESINFETANTE LAVANDA 5L',
             10, 189, 51, 0.051,
             '07026806000172', 'MASTER COMERCIO', 'SAO PAULO', 'SP',
             '2025-01-10', '2025-01-13', '2025-01-14', 'PROT-2025-001',
             'total', CURRENT_TIMESTAMP),
            
            (:lote_id, :num_pedido, '4310162', 'MULTIUSO CLASSICO 500ML',
             10, 55, 5.2, 0.0052,
             '07026806000172', 'MASTER COMERCIO', 'SAO PAULO', 'SP',
             '2025-01-10', '2025-01-13', '2025-01-14', 'PROT-2025-001',
             'total', CURRENT_TIMESTAMP)
        """, {'lote_id': lote_id, 'num_pedido': num_pedido})
        
        print("✅ Separação restaurada (3 itens)")
        
        # Commit
        db.session.commit()
        print("\n✅ RESTAURAÇÃO COMPLETA!\n")
        
        # Verificar resultado
        print("=== VERIFICAÇÃO ===")
        
        # Verificar CarteiraPrincipal
        result = db.session.execute("""
            SELECT cod_produto, qtd_saldo_produto_pedido 
            FROM carteira_principal 
            WHERE num_pedido = :num_pedido
            ORDER BY cod_produto
        """, {'num_pedido': num_pedido})
        
        print("\n📋 CarteiraPrincipal:")
        for row in result:
            print(f"  • {row[0]}: {row[1]} unidades")
        
        # Verificar Separação
        result = db.session.execute("""
            SELECT cod_produto, qtd_saldo 
            FROM separacao 
            WHERE separacao_lote_id = :lote_id 
            AND num_pedido = :num_pedido
            ORDER BY cod_produto
        """, {'lote_id': lote_id, 'num_pedido': num_pedido})
        
        print("\n📦 Separação:")
        for row in result:
            print(f"  • {row[0]}: {row[1]} unidades")
        
        print("\n🔄 Pronto para sincronizar com Odoo!")
        print("   Esperado após sync:")
        print("   • 4320162: 10 → 15 (aumento)")
        print("   • 4360162: 10 → 5 (redução)")
        print("   • 4310162: 10 → 0 (remoção)")
        print("   • 4350162: 0 → 10 (adição)")

if __name__ == "__main__":
    main()
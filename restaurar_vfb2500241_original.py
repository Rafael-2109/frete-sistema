#!/usr/bin/env python3
"""
Script para restaurar COMPLETAMENTE o pedido VFB2500241 ao estado original
Restaura tanto CarteiraPrincipal quanto Separacao
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.carteira.models import CarteiraPrincipal
from app.separacao.models import Separacao
from app.pedidos.models import Pedido
from app.carteira.models_alertas import AlertaSeparacaoCotada
from decimal import Decimal
from datetime import datetime

def restaurar_pedido_completo():
    """Restaura o pedido VFB2500241 ao estado original completo"""
    
    app = create_app()
    with app.app_context():
        num_pedido = 'VFB2500241'
        
        print("\n" + "="*60)
        print("RESTAURAÇÃO COMPLETA DO PEDIDO VFB2500241")
        print("="*60)
        
        # Buscar informações do pedido
        pedido = Pedido.query.filter_by(num_pedido=num_pedido).first()
        if not pedido:
            print(f"❌ Pedido {num_pedido} não encontrado!")
            return False
        
        lote_id = pedido.separacao_lote_id
        print(f"\n📦 Pedido: {num_pedido}")
        print(f"📋 Lote: {lote_id}")
        print(f"📊 Status: {pedido.status}")
        
        # ========== PARTE 1: LIMPAR ALERTAS ==========
        print("\n" + "-"*40)
        print("LIMPANDO ALERTAS")
        print("-"*40)
        
        alertas = AlertaSeparacaoCotada.query.filter_by(
            num_pedido=num_pedido
        ).all()
        
        for alerta in alertas:
            db.session.delete(alerta)
        
        print(f"✅ {len(alertas)} alertas removidos")
        
        # ========== PARTE 2: RESTAURAR CARTEIRA PRINCIPAL ==========
        print("\n" + "-"*40)
        print("RESTAURANDO CARTEIRA PRINCIPAL")
        print("-"*40)
        
        # Remover todos os itens atuais
        itens_atuais = CarteiraPrincipal.query.filter_by(num_pedido=num_pedido).all()
        for item in itens_atuais:
            db.session.delete(item)
        print(f"🗑️  {len(itens_atuais)} itens removidos da carteira")
        
        # Buscar um pedido de referência para copiar dados comuns
        ref_pedido = CarteiraPrincipal.query.filter(
            CarteiraPrincipal.cnpj_cpf == '07026806000172'
        ).first()
        
        # Dados comuns para todos os itens
        dados_comuns = {
            'cnpj_cpf': '07026806000172',
            'raz_social': 'MASTER COMERCIO DE PRODUTOS DE LIMPEZA LTD',
            'raz_social_red': 'MASTER COMERCIO',
            'municipio': 'SAO PAULO',
            'estado': 'SP',
            'vendedor': ref_pedido.vendedor if ref_pedido else 'VENDEDOR01',
            'equipe_vendas': ref_pedido.equipe_vendas if ref_pedido else 'EQUIPE01',
            'data_pedido': datetime(2025, 1, 10).date(),
            'expedicao': datetime(2025, 1, 13).date(),
            'agendamento': datetime(2025, 1, 14).date(),
            'protocolo': 'PROT-2025-001',
            'agendamento_confirmado': True,
            'separacao_lote_id': lote_id
        }
        
        # Criar os 3 itens originais
        itens_originais = [
            {
                'cod_produto': '4320162',
                'nome_produto': 'DETERGENTE NEUTRO 5L',
                'qtd_produto_pedido': Decimal('10'),
                'qtd_saldo_produto_pedido': Decimal('10'),
                'preco_produto_pedido': Decimal('25.50'),
                'peso_unitario_produto': Decimal('5.2')
            },
            {
                'cod_produto': '4360162',
                'nome_produto': 'DESINFETANTE LAVANDA 5L',
                'qtd_produto_pedido': Decimal('10'),
                'qtd_saldo_produto_pedido': Decimal('10'),
                'preco_produto_pedido': Decimal('18.90'),
                'peso_unitario_produto': Decimal('5.1')
            },
            {
                'cod_produto': '4310162',
                'nome_produto': 'MULTIUSO CLASSICO 500ML',
                'qtd_produto_pedido': Decimal('10'),
                'qtd_saldo_produto_pedido': Decimal('10'),
                'preco_produto_pedido': Decimal('5.50'),
                'peso_unitario_produto': Decimal('0.52')
            }
        ]
        
        print("\nCriando itens na CarteiraPrincipal:")
        for item_data in itens_originais:
            novo_item = CarteiraPrincipal(
                num_pedido=num_pedido,
                **item_data,
                **dados_comuns,
                qtd_cancelada_produto_pedido=Decimal('0')
            )
            db.session.add(novo_item)
            print(f"  ✅ {item_data['cod_produto']}: {item_data['qtd_produto_pedido']} unidades")
        
        # ========== PARTE 3: RESTAURAR SEPARAÇÃO ==========
        print("\n" + "-"*40)
        print("RESTAURANDO SEPARAÇÃO")
        print("-"*40)
        
        # Remover todos os itens atuais da separação
        itens_sep_atuais = Separacao.query.filter_by(
            separacao_lote_id=lote_id,
            num_pedido=num_pedido
        ).all()
        
        for item in itens_sep_atuais:
            db.session.delete(item)
        print(f"🗑️  {len(itens_sep_atuais)} itens removidos da separação")
        
        # Buscar um item de referência para copiar campos adicionais
        ref_sep = Separacao.query.filter_by(
            separacao_lote_id=lote_id
        ).first()
        
        # Dados comuns para separação
        dados_sep_comuns = {
            'cnpj_cpf': '07026806000172',
            'raz_social_red': 'MASTER COMERCIO',
            'nome_cidade': 'SAO PAULO',
            'cod_uf': 'SP',
            'data_pedido': datetime(2025, 1, 10).date(),
            'expedicao': datetime(2025, 1, 13).date(),
            'agendamento': datetime(2025, 1, 14).date(),
            'protocolo': 'PROT-2025-001',
            'tipo_envio': 'total',
            'roteirizacao': ref_sep.roteirizacao if ref_sep else None,
            'rota': ref_sep.rota if ref_sep else None,
            'sub_rota': ref_sep.sub_rota if ref_sep else None
        }
        
        # Criar os 3 itens originais na separação
        itens_sep_originais = [
            {
                'cod_produto': '4320162',
                'nome_produto': 'DETERGENTE NEUTRO 5L',
                'qtd_saldo': 10.0,
                'valor_saldo': 255.0,  # 10 * 25.50
                'peso': 52.0,  # 10 * 5.2
                'pallet': 0.052  # peso / 1000
            },
            {
                'cod_produto': '4360162',
                'nome_produto': 'DESINFETANTE LAVANDA 5L',
                'qtd_saldo': 10.0,
                'valor_saldo': 189.0,  # 10 * 18.90
                'peso': 51.0,  # 10 * 5.1
                'pallet': 0.051
            },
            {
                'cod_produto': '4310162',
                'nome_produto': 'MULTIUSO CLASSICO 500ML',
                'qtd_saldo': 10.0,
                'valor_saldo': 55.0,  # 10 * 5.50
                'peso': 5.2,  # 10 * 0.52
                'pallet': 0.0052
            }
        ]
        
        print("\nCriando itens na Separação:")
        for item_data in itens_sep_originais:
            nova_sep = Separacao(
                separacao_lote_id=lote_id,
                num_pedido=num_pedido,
                **item_data,
                **dados_sep_comuns
            )
            db.session.add(nova_sep)
            print(f"  ✅ {item_data['cod_produto']}: {item_data['qtd_saldo']} unidades")
        
        # ========== PARTE 4: CONFIRMAR RESTAURAÇÃO ==========
        print("\n" + "-"*40)
        print("SALVANDO ALTERAÇÕES")
        print("-"*40)
        
        try:
            db.session.commit()
            print("✅ Todas as alterações foram salvas com sucesso!")
        except Exception as e:
            db.session.rollback()
            print(f"❌ Erro ao salvar: {e}")
            return False
        
        # ========== PARTE 5: VERIFICAÇÃO FINAL ==========
        print("\n" + "="*60)
        print("VERIFICAÇÃO FINAL")
        print("="*60)
        
        # Verificar CarteiraPrincipal
        print("\n📋 CarteiraPrincipal:")
        itens_carteira = CarteiraPrincipal.query.filter_by(num_pedido=num_pedido).all()
        for item in itens_carteira:
            print(f"  • {item.cod_produto}: {item.qtd_saldo_produto_pedido} unidades")
        
        # Verificar Separação
        print("\n📦 Separação:")
        itens_sep = Separacao.query.filter_by(
            separacao_lote_id=lote_id,
            num_pedido=num_pedido
        ).all()
        for item in itens_sep:
            print(f"  • {item.cod_produto}: {item.qtd_saldo} unidades")
        
        # Verificar alertas
        alertas_restantes = AlertaSeparacaoCotada.query.filter_by(
            num_pedido=num_pedido,
            reimpresso=False
        ).count()
        print(f"\n📢 Alertas pendentes: {alertas_restantes}")
        
        print("\n" + "="*60)
        print("✅ RESTAURAÇÃO COMPLETA CONCLUÍDA!")
        print("="*60)
        print("\n📌 Estado original do pedido VFB2500241:")
        print("   • 3 produtos (4320162, 4360162, 4310162)")
        print("   • Cada produto com 10 unidades")
        print("   • Sem o produto 4350162")
        print("   • Todos os alertas limpos")
        print("\n🔄 Agora você pode sincronizar com o Odoo para testar as alterações!")
        
        return True

if __name__ == "__main__":
    restaurar_pedido_completo()
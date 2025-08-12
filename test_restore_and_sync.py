#!/usr/bin/env python3
"""
Script para restaurar pedido VFB2500241 ao estado original e testar sincronização
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.carteira.models import CarteiraPrincipal
from app.separacao.models import Separacao
from app.pedidos.models import Pedido
from app.carteira.services.separacao_update_service import SeparacaoUpdateService
from app.carteira.models_alertas import AlertaSeparacaoCotada
from decimal import Decimal
from datetime import datetime

def restaurar_pedido_original():
    """Restaura o pedido VFB2500241 para o estado original antes das alterações"""
    
    app = create_app()
    with app.app_context():
        num_pedido = 'VFB2500241'
        
        print("\n=== ESTADO ATUAL DA CARTEIRA ===")
        itens_carteira = CarteiraPrincipal.query.filter_by(num_pedido=num_pedido).all()
        print(f"Itens na CarteiraPrincipal para {num_pedido}:")
        for item in itens_carteira:
            print(f"  - {item.cod_produto}: qtd_saldo={item.qtd_saldo_produto_pedido}, qtd_original={item.qtd_produto_pedido}")
        
        print("\n=== ESTADO ATUAL DA SEPARAÇÃO ===")
        pedido = Pedido.query.filter_by(num_pedido=num_pedido).first()
        if pedido and pedido.separacao_lote_id:
            itens_sep = Separacao.query.filter_by(separacao_lote_id=pedido.separacao_lote_id).all()
            print(f"Itens na Separação (lote {pedido.separacao_lote_id}):")
            for item in itens_sep:
                print(f"  - {item.cod_produto}: {item.qtd_saldo}")
        
        print("\n=== RESTAURANDO CARTEIRA PARA ESTADO ORIGINAL ===")
        
        # 1. Restaurar 4320162 de 15 para 10
        item_4320162 = CarteiraPrincipal.query.filter_by(
            num_pedido=num_pedido,
            cod_produto='4320162'
        ).first()
        if item_4320162:
            print(f"1. Restaurando 4320162: {item_4320162.qtd_saldo_produto_pedido} -> 10")
            item_4320162.qtd_saldo_produto_pedido = Decimal('10')
            item_4320162.qtd_produto_pedido = Decimal('10')
            db.session.add(item_4320162)
        
        # 2. Restaurar 4360162 de 5 para 10
        item_4360162 = CarteiraPrincipal.query.filter_by(
            num_pedido=num_pedido,
            cod_produto='4360162'
        ).first()
        if item_4360162:
            print(f"2. Restaurando 4360162: {item_4360162.qtd_saldo_produto_pedido} -> 10")
            item_4360162.qtd_saldo_produto_pedido = Decimal('10')
            item_4360162.qtd_produto_pedido = Decimal('10')
            db.session.add(item_4360162)
        
        # 3. Restaurar 4310162 (que foi removido) - adicionar de volta com qtd 10
        item_4310162 = CarteiraPrincipal.query.filter_by(
            num_pedido=num_pedido,
            cod_produto='4310162'
        ).first()
        if not item_4310162:
            print("3. Recriando 4310162 com qtd 10")
            # Copiar dados de outro item como referência
            ref_item = CarteiraPrincipal.query.filter_by(num_pedido=num_pedido).first()
            if ref_item:
                novo_item = CarteiraPrincipal(
                    num_pedido=num_pedido,
                    cod_produto='4310162',
                    nome_produto='MULTIUSO CLASSICO 500ML',
                    qtd_produto_pedido=Decimal('10'),
                    qtd_saldo_produto_pedido=Decimal('10'),
                    qtd_cancelada_produto_pedido=Decimal('0'),
                    preco_produto_pedido=Decimal('5.50'),
                    cnpj_cpf=ref_item.cnpj_cpf,
                    raz_social=ref_item.raz_social,
                    raz_social_red=ref_item.raz_social_red,
                    municipio=ref_item.municipio,
                    estado=ref_item.estado,
                    vendedor=ref_item.vendedor,
                    equipe_vendas=ref_item.equipe_vendas,
                    data_pedido=ref_item.data_pedido,
                    expedicao=ref_item.expedicao,
                    agendamento=ref_item.agendamento,
                    protocolo=ref_item.protocolo,
                    peso_unitario_produto=Decimal('0.5'),
                    separacao_lote_id=pedido.separacao_lote_id if pedido else None
                )
                db.session.add(novo_item)
        else:
            print(f"3. Item 4310162 já existe com qtd: {item_4310162.qtd_saldo_produto_pedido}")
            item_4310162.qtd_saldo_produto_pedido = Decimal('10')
            item_4310162.qtd_produto_pedido = Decimal('10')
            db.session.add(item_4310162)
        
        # 4. Remover 4350162 (que foi adicionado)
        item_4350162 = CarteiraPrincipal.query.filter_by(
            num_pedido=num_pedido,
            cod_produto='4350162'
        ).first()
        if item_4350162:
            print(f"4. Removendo 4350162 da carteira")
            db.session.delete(item_4350162)
        else:
            print("4. Item 4350162 não existe na carteira (OK)")
        
        # Limpar alertas anteriores
        print("\n=== LIMPANDO ALERTAS ANTERIORES ===")
        if pedido and pedido.separacao_lote_id:
            alertas = AlertaSeparacaoCotada.query.filter_by(
                separacao_lote_id=pedido.separacao_lote_id,
                num_pedido=num_pedido
            ).all()
            for alerta in alertas:
                db.session.delete(alerta)
            print(f"Removidos {len(alertas)} alertas anteriores")
        
        # Salvar alterações
        try:
            db.session.commit()
            print("\n✅ CarteiraPrincipal restaurada ao estado original!")
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Erro ao restaurar: {e}")
            return False
        
        print("\n=== ESTADO APÓS RESTAURAÇÃO ===")
        itens_carteira = CarteiraPrincipal.query.filter_by(num_pedido=num_pedido).all()
        print(f"Itens na CarteiraPrincipal:")
        for item in itens_carteira:
            print(f"  - {item.cod_produto}: qtd={item.qtd_saldo_produto_pedido}")
        
        print("\n=== SIMULANDO ALTERAÇÕES DO ODOO ===")
        print("Agora vamos simular as alterações vindas do Odoo:")
        print("1. 4320162: 10 -> 15 (AUMENTO)")
        print("2. 4360162: 10 -> 5 (REDUÇÃO)")
        print("3. 4310162: 10 -> 0 (REMOÇÃO)")
        print("4. 4350162: 0 -> 10 (ADIÇÃO)")
        
        # Aplicar alterações na CarteiraPrincipal (simulando Odoo)
        print("\n=== APLICANDO ALTERAÇÕES NA CARTEIRA (SIMULANDO ODOO) ===")
        
        # 1. Aumentar 4320162 de 10 para 15
        item = CarteiraPrincipal.query.filter_by(num_pedido=num_pedido, cod_produto='4320162').first()
        if item:
            item.qtd_saldo_produto_pedido = Decimal('15')
            item.qtd_produto_pedido = Decimal('15')
            print(f"✅ 4320162: 10 -> 15")
        
        # 2. Reduzir 4360162 de 10 para 5
        item = CarteiraPrincipal.query.filter_by(num_pedido=num_pedido, cod_produto='4360162').first()
        if item:
            item.qtd_saldo_produto_pedido = Decimal('5')
            item.qtd_produto_pedido = Decimal('5')
            print(f"✅ 4360162: 10 -> 5")
        
        # 3. Remover 4310162
        item = CarteiraPrincipal.query.filter_by(num_pedido=num_pedido, cod_produto='4310162').first()
        if item:
            db.session.delete(item)
            print(f"✅ 4310162: Removido")
        
        # 4. Adicionar 4350162 com qtd 10
        ref_item = CarteiraPrincipal.query.filter_by(num_pedido=num_pedido).first()
        if ref_item:
            novo_item = CarteiraPrincipal(
                num_pedido=num_pedido,
                cod_produto='4350162',
                nome_produto='LIMPA VIDROS 500ML',
                qtd_produto_pedido=Decimal('10'),
                qtd_saldo_produto_pedido=Decimal('10'),
                qtd_cancelada_produto_pedido=Decimal('0'),
                preco_produto_pedido=Decimal('7.20'),
                cnpj_cpf=ref_item.cnpj_cpf,
                raz_social=ref_item.raz_social,
                raz_social_red=ref_item.raz_social_red,
                municipio=ref_item.municipio,
                estado=ref_item.estado,
                vendedor=ref_item.vendedor,
                equipe_vendas=ref_item.equipe_vendas,
                data_pedido=ref_item.data_pedido,
                expedicao=ref_item.expedicao,
                agendamento=ref_item.agendamento,
                protocolo=ref_item.protocolo,
                peso_unitario_produto=Decimal('0.5'),
                separacao_lote_id=pedido.separacao_lote_id if pedido else None
            )
            db.session.add(novo_item)
            print(f"✅ 4350162: Adicionado com qtd 10")
        
        db.session.commit()
        
        print("\n=== PROCESSANDO ALTERAÇÕES COM SeparacaoUpdateService ===")
        
        # Processar cada alteração usando o serviço
        resultados = []
        
        # 1. AUMENTO: 4320162
        print("\n1. Processando AUMENTO de 4320162...")
        resultado = SeparacaoUpdateService.processar_alteracao_pedido(
            num_pedido=num_pedido,
            cod_produto='4320162',
            alteracao_tipo='AUMENTO',
            qtd_anterior=10,
            qtd_nova=15,
            motivo="TESTE_SYNC"
        )
        resultados.append(('4320162 AUMENTO', resultado))
        
        # 2. REDUÇÃO: 4360162
        print("\n2. Processando REDUÇÃO de 4360162...")
        resultado = SeparacaoUpdateService.processar_alteracao_pedido(
            num_pedido=num_pedido,
            cod_produto='4360162',
            alteracao_tipo='REDUCAO',
            qtd_anterior=10,
            qtd_nova=5,
            motivo="TESTE_SYNC"
        )
        resultados.append(('4360162 REDUÇÃO', resultado))
        
        # 3. REMOÇÃO: 4310162
        print("\n3. Processando REMOÇÃO de 4310162...")
        resultado = SeparacaoUpdateService.processar_alteracao_pedido(
            num_pedido=num_pedido,
            cod_produto='4310162',
            alteracao_tipo='REMOCAO',
            qtd_anterior=10,
            qtd_nova=0,
            motivo="TESTE_SYNC"
        )
        resultados.append(('4310162 REMOÇÃO', resultado))
        
        # 4. ADIÇÃO: 4350162
        print("\n4. Processando ADIÇÃO de 4350162...")
        resultado = SeparacaoUpdateService.processar_alteracao_pedido(
            num_pedido=num_pedido,
            cod_produto='4350162',
            alteracao_tipo='ADICAO',
            qtd_anterior=0,
            qtd_nova=10,
            motivo="TESTE_SYNC"
        )
        resultados.append(('4350162 ADIÇÃO', resultado))
        
        print("\n=== RESULTADOS DO PROCESSAMENTO ===")
        for desc, res in resultados:
            print(f"\n{desc}:")
            if res.get('sucesso'):
                print(f"  ✅ Sucesso")
                if res.get('alertas_gerados'):
                    print(f"  📢 Alertas gerados: {res['alertas_gerados']}")
                if res.get('separacoes_atualizadas'):
                    for sep in res['separacoes_atualizadas']:
                        print(f"  📦 Separação {sep['separacao_lote_id']} ({sep['tipo']}/{sep['status']})")
                        for op in sep.get('operacoes', []):
                            print(f"     - {op}")
            else:
                print(f"  ❌ Erro: {res.get('erro')}")
        
        print("\n=== VERIFICAÇÃO FINAL ===")
        if pedido and pedido.separacao_lote_id:
            itens_sep = Separacao.query.filter_by(separacao_lote_id=pedido.separacao_lote_id).all()
            print(f"Itens na Separação após processamento:")
            for item in itens_sep:
                print(f"  - {item.cod_produto}: {item.qtd_saldo}")
            
            # Verificar se as alterações foram aplicadas corretamente
            print("\n📊 Validação das alterações:")
            
            # 4320162 deve ser 15
            item = next((i for i in itens_sep if i.cod_produto == '4320162'), None)
            if item and float(item.qtd_saldo) == 15:
                print("✅ 4320162: 15.0 (CORRETO)")
            else:
                print(f"❌ 4320162: {item.qtd_saldo if item else 'não encontrado'} (esperado 15.0)")
            
            # 4360162 deve ser 5
            item = next((i for i in itens_sep if i.cod_produto == '4360162'), None)
            if item and float(item.qtd_saldo) == 5:
                print("✅ 4360162: 5.0 (CORRETO)")
            else:
                print(f"❌ 4360162: {item.qtd_saldo if item else 'não encontrado'} (esperado 5.0)")
            
            # 4310162 não deve existir
            item = next((i for i in itens_sep if i.cod_produto == '4310162'), None)
            if not item:
                print("✅ 4310162: Removido (CORRETO)")
            else:
                print(f"❌ 4310162: {item.qtd_saldo} (deveria estar removido)")
            
            # 4350162 deve existir com qtd 10
            item = next((i for i in itens_sep if i.cod_produto == '4350162'), None)
            if item and float(item.qtd_saldo) == 10:
                print("✅ 4350162: 10.0 (CORRETO)")
            else:
                print(f"❌ 4350162: {item.qtd_saldo if item else 'não encontrado'} (esperado 10.0)")
            
            # Contar alertas
            alertas = AlertaSeparacaoCotada.query.filter_by(
                separacao_lote_id=pedido.separacao_lote_id,
                reimpresso=False
            ).count()
            print(f"\n📢 Total de alertas pendentes: {alertas}")
        
        return True

if __name__ == "__main__":
    restaurar_pedido_original()
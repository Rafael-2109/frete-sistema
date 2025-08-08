#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
🔍 TESTE DE SEPARAÇÃO E ESTOQUE
================================
Testa se separações são refletidas corretamente no estoque
"""

import os
import sys
from datetime import datetime, date, timedelta
from decimal import Decimal

# Adicionar o diretório do projeto ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.separacao.models import Separacao
from app.estoque.models_tempo_real import EstoqueTempoReal, MovimentacaoPrevista
from app.estoque.models import MovimentacaoEstoque

def testar_separacao_estoque():
    """Testa se separações afetam o estoque corretamente"""
    
    app = create_app()
    
    with app.app_context():
        print("\n" + "="*70)
        print("🔍 TESTE DE SEPARAÇÃO E REFLEXO NO ESTOQUE")
        print("="*70)
        
        # Produto de teste
        cod_produto_teste = 'TESTE_SEP_001'
        data_expedicao = date.today() + timedelta(days=3)
        
        # 1. Limpar dados anteriores
        print("\n1️⃣ Limpando dados de teste anteriores...")
        
        # Limpar separações de teste
        Separacao.query.filter_by(cod_produto=cod_produto_teste).delete()
        
        # Limpar movimentações previstas
        MovimentacaoPrevista.query.filter_by(cod_produto=cod_produto_teste).delete()
        
        # Limpar estoque tempo real
        EstoqueTempoReal.query.filter_by(cod_produto=cod_produto_teste).delete()
        
        # Limpar movimentações
        MovimentacaoEstoque.query.filter_by(cod_produto=cod_produto_teste).delete()
        
        db.session.commit()
        print("   ✅ Dados limpos")
        
        # 2. Criar estoque inicial
        print("\n2️⃣ Criando estoque inicial...")
        
        # Criar entrada no estoque
        entrada = MovimentacaoEstoque(
            cod_produto=cod_produto_teste,
            nome_produto='Produto Teste Separação',
            tipo_movimentacao='ENTRADA',
            qtd_movimentacao=Decimal('1000'),
            data_movimentacao=date.today(),
            local_movimentacao='COMPRA',
            observacao='Estoque inicial para teste'
        )
        db.session.add(entrada)
        db.session.commit()
        
        # Verificar estoque criado
        estoque = EstoqueTempoReal.query.filter_by(cod_produto=cod_produto_teste).first()
        if estoque:
            print(f"   ✅ Estoque inicial: {estoque.saldo_atual}")
        else:
            print("   ❌ ERRO: Estoque não foi criado!")
        
        # 3. Criar separação
        print("\n3️⃣ Criando separação...")
        
        separacao = Separacao(
            separacao_lote_id='LOTE_TESTE_001',
            num_pedido='PED_TESTE_001',
            cod_produto=cod_produto_teste,
            nome_produto='Produto Teste Separação',
            qtd_saldo=250.0,  # Separando 250 unidades
            valor_saldo=2500.0,
            peso=125.0,
            pallet=3.0,
            cnpj_cpf='12345678901234',
            raz_social_red='Cliente Teste',
            nome_cidade='São Paulo',
            cod_uf='SP',
            expedicao=data_expedicao,
            data_pedido=date.today(),
            tipo_envio='total'
        )
        
        print(f"   📦 Criando separação de {separacao.qtd_saldo} unidades")
        print(f"   📅 Data expedição: {separacao.expedicao}")
        
        db.session.add(separacao)
        db.session.commit()
        
        print("   ✅ Separação criada com sucesso")
        
        # 4. Verificar se movimentação prevista foi criada
        print("\n4️⃣ Verificando movimentação prevista...")
        
        mov_prevista = MovimentacaoPrevista.query.filter_by(
            cod_produto=cod_produto_teste,
            data_prevista=data_expedicao
        ).first()
        
        if mov_prevista:
            print(f"   ✅ Movimentação prevista encontrada:")
            print(f"      • Data: {mov_prevista.data_prevista}")
            print(f"      • Saída Prevista: {mov_prevista.saida_prevista}")
            print(f"      • Entrada Prevista: {mov_prevista.entrada_prevista}")
        else:
            print("   ❌ ERRO: Movimentação prevista NÃO foi criada!")
            
            # Verificar se há alguma movimentação prevista
            todas_mov = MovimentacaoPrevista.query.all()
            print(f"   📊 Total de movimentações previstas no banco: {len(todas_mov)}")
            
            for mov in todas_mov:
                print(f"      • {mov.cod_produto} - Data: {mov.data_prevista} - Saída: {mov.saida_prevista} | Entrada: {mov.entrada_prevista}")
        
        # 5. Verificar projeção de estoque
        print("\n5️⃣ Verificando projeção de estoque...")
        
        # Buscar todas as movimentações previstas do produto
        movs_previstas = MovimentacaoPrevista.query.filter_by(
            cod_produto=cod_produto_teste
        ).all()
        
        print(f"   📊 Total de movimentações previstas: {len(movs_previstas)}")
        
        for mov in movs_previstas:
            print(f"   • {mov.data_prevista}: Saída: {mov.saida_prevista or 0} | Entrada: {mov.entrada_prevista or 0}")
        
        # 6. Testar atualização da separação
        print("\n6️⃣ Atualizando quantidade da separação...")
        
        separacao.qtd_saldo = 350.0  # Aumentando para 350
        db.session.commit()
        
        print(f"   📦 Quantidade atualizada para {separacao.qtd_saldo}")
        
        # Verificar se movimentação foi atualizada
        mov_prevista = MovimentacaoPrevista.query.filter_by(
            cod_produto=cod_produto_teste,
            data_prevista=data_expedicao
        ).first()
        
        if mov_prevista:
            print(f"   ✅ Movimentação prevista atualizada: {mov_prevista.saida_prevista}")
        else:
            print("   ❌ ERRO: Movimentação prevista não encontrada após update!")
        
        # 7. Testar exclusão da separação
        print("\n7️⃣ Deletando separação...")
        
        db.session.delete(separacao)
        db.session.commit()
        
        # Verificar se movimentação foi removida
        mov_prevista = MovimentacaoPrevista.query.filter_by(
            cod_produto=cod_produto_teste,
            data_prevista=data_expedicao
        ).first()
        
        if not mov_prevista or mov_prevista.saida_prevista == 0:
            print("   ✅ Movimentação prevista removida/zerada corretamente")
        else:
            print(f"   ❌ ERRO: Movimentação ainda existe com quantidade: {mov_prevista.saida_prevista}")
        
        # 8. Limpar dados de teste
        print("\n8️⃣ Limpando dados de teste...")
        
        Separacao.query.filter_by(cod_produto=cod_produto_teste).delete()
        MovimentacaoPrevista.query.filter_by(cod_produto=cod_produto_teste).delete()
        EstoqueTempoReal.query.filter_by(cod_produto=cod_produto_teste).delete()
        MovimentacaoEstoque.query.filter_by(cod_produto=cod_produto_teste).delete()
        
        db.session.commit()
        print("   ✅ Dados de teste removidos")
        
        print("\n" + "="*70)
        print("📊 RESUMO DO TESTE")
        print("="*70)

if __name__ == '__main__':
    testar_separacao_estoque()
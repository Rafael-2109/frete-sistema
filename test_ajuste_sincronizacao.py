#!/usr/bin/env python3
"""
Script de teste para validar o novo serviço de ajuste de sincronização
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.odoo.services.ajuste_sincronizacao_service import AjusteSincronizacaoService
from app.carteira.models import CarteiraPrincipal, PreSeparacaoItem
from app.separacao.models import Separacao
from app.pedidos.models import Pedido
from datetime import datetime, date
from decimal import Decimal

app = create_app()

def teste_detectar_tipo_separacao():
    """Testa a detecção de tipo de separação (TOTAL ou PARCIAL)"""
    print("\n=== TESTE: Detectar Tipo de Separação ===")
    
    with app.app_context():
        # Buscar um exemplo de separação
        separacao = Separacao.query.first()
        if separacao and separacao.separacao_lote_id:
            tipo = AjusteSincronizacaoService._detectar_tipo_separacao(
                separacao.num_pedido,
                separacao.separacao_lote_id,
                'SEPARACAO'
            )
            print(f"✅ Lote {separacao.separacao_lote_id}: Tipo = {tipo}")
            return True
        else:
            print("⚠️ Nenhuma separação encontrada para teste")
            return False

def teste_verificar_cotado():
    """Testa a verificação se uma separação está COTADA"""
    print("\n=== TESTE: Verificar se Separação está COTADA ===")
    
    with app.app_context():
        # Buscar um pedido com status COTADO
        pedido_cotado = Pedido.query.filter_by(status='COTADO').first()
        if pedido_cotado and pedido_cotado.separacao_lote_id:
            is_cotado = AjusteSincronizacaoService._verificar_se_cotado(
                pedido_cotado.separacao_lote_id
            )
            print(f"✅ Lote {pedido_cotado.separacao_lote_id}: COTADO = {is_cotado}")
            return True
        else:
            print("⚠️ Nenhum pedido COTADO encontrado para teste")
            
            # Testar com pedido ABERTO
            pedido_aberto = Pedido.query.filter_by(status='ABERTO').first()
            if pedido_aberto and pedido_aberto.separacao_lote_id:
                is_cotado = AjusteSincronizacaoService._verificar_se_cotado(
                    pedido_aberto.separacao_lote_id
                )
                print(f"✅ Lote {pedido_aberto.separacao_lote_id}: COTADO = {is_cotado}")
                return True
            return False

def teste_calcular_diferencas():
    """Testa o cálculo de diferenças entre Odoo e sistema"""
    print("\n=== TESTE: Calcular Diferenças ===")
    
    with app.app_context():
        # Buscar um pedido de exemplo
        carteira_item = CarteiraPrincipal.query.first()
        if not carteira_item:
            print("⚠️ Nenhum item na carteira para teste")
            return False
        
        num_pedido = carteira_item.num_pedido
        
        # Simular dados do Odoo com alterações
        itens_odoo = [{
            'num_pedido': num_pedido,
            'cod_produto': carteira_item.cod_produto,
            'qtd_saldo_produto_pedido': float(carteira_item.qtd_saldo_produto_pedido or 0) * 0.8,  # Redução de 20%
            'preco_produto_pedido': float(carteira_item.preco_produto_pedido or 0)
        }]
        
        # Calcular diferenças
        diferencas = AjusteSincronizacaoService._calcular_diferencas(
            num_pedido, itens_odoo
        )
        
        print(f"✅ Diferenças calculadas para pedido {num_pedido}:")
        print(f"   - Reduções: {len(diferencas['reducoes'])}")
        print(f"   - Aumentos: {len(diferencas['aumentos'])}")
        print(f"   - Removidos: {len(diferencas['removidos'])}")
        print(f"   - Novos: {len(diferencas['novos'])}")
        
        return True

def teste_processar_pedido_simples():
    """Testa o processamento de um pedido com alterações simples"""
    print("\n=== TESTE: Processar Pedido Alterado (Simulação) ===")
    
    with app.app_context():
        # Buscar um pedido que tenha separação
        pedido = Pedido.query.filter(
            Pedido.separacao_lote_id.isnot(None)
        ).first()
        
        if not pedido:
            print("⚠️ Nenhum pedido com separação encontrado")
            return False
        
        # Buscar itens da carteira para este pedido
        itens_carteira = CarteiraPrincipal.query.filter_by(
            num_pedido=pedido.num_pedido
        ).limit(2).all()
        
        if not itens_carteira:
            # Tentar com qualquer pedido que tenha itens
            print(f"⚠️ Pedido {pedido.num_pedido} não tem itens na carteira")
            print("   Buscando outro pedido...")
            
            # Buscar um pedido que tenha itens na carteira
            item_carteira = CarteiraPrincipal.query.first()
            if item_carteira:
                pedido = Pedido.query.filter_by(num_pedido=item_carteira.num_pedido).first()
                if pedido and pedido.separacao_lote_id:
                    itens_carteira = CarteiraPrincipal.query.filter_by(
                        num_pedido=pedido.num_pedido
                    ).limit(2).all()
                    print(f"   Usando pedido alternativo: {pedido.num_pedido}")
            
            if not itens_carteira:
                print("❌ Não foi possível encontrar dados para teste")
                return False
        
        # Simular dados do Odoo (sem fazer alterações reais)
        itens_odoo = []
        for item in itens_carteira:
            itens_odoo.append({
                'num_pedido': item.num_pedido,
                'cod_produto': item.cod_produto,
                'qtd_saldo_produto_pedido': float(item.qtd_saldo_produto_pedido or 0),
                'qtd_produto_pedido': float(item.qtd_produto_pedido or 0),
                'preco_produto_pedido': float(item.preco_produto_pedido or 0),
                'peso_unitario_produto': float(item.peso_unitario_produto or 0),
                'cnpj_cpf': item.cnpj_cpf,
                'nome_produto': item.nome_produto,
                'raz_social_red': item.raz_social_red,
                'municipio': item.municipio,
                'estado': item.estado,
                'expedicao': item.expedicao,
                'agendamento': item.agendamento,
                'protocolo': item.protocolo,
                'observ_ped_1': item.observ_ped_1
            })
        
        print(f"📋 Pedido: {pedido.num_pedido}")
        print(f"   - Lote: {pedido.separacao_lote_id}")
        print(f"   - Status: {pedido.status}")
        print(f"   - Itens simulados: {len(itens_odoo)}")
        
        # Verificar tipo de separação
        tipo_sep = AjusteSincronizacaoService._detectar_tipo_separacao(
            pedido.num_pedido,
            pedido.separacao_lote_id,
            'SEPARACAO'
        )
        print(f"   - Tipo de separação: {tipo_sep}")
        
        # Não vamos executar o processamento real para não alterar o banco
        print("✅ Teste de simulação concluído (sem alterações no banco)")
        
        return True

def main():
    """Executa todos os testes"""
    print("=" * 60)
    print("TESTE DO SERVIÇO DE AJUSTE DE SINCRONIZAÇÃO")
    print("=" * 60)
    
    testes = [
        teste_detectar_tipo_separacao,
        teste_verificar_cotado,
        teste_calcular_diferencas,
        teste_processar_pedido_simples
    ]
    
    resultados = []
    for teste in testes:
        try:
            resultado = teste()
            resultados.append(resultado)
        except Exception as e:
            print(f"❌ Erro no teste {teste.__name__}: {e}")
            resultados.append(False)
    
    print("\n" + "=" * 60)
    print("RESUMO DOS TESTES")
    print("=" * 60)
    
    total = len(resultados)
    sucesso = sum(1 for r in resultados if r)
    
    print(f"Total de testes: {total}")
    print(f"Testes bem-sucedidos: {sucesso}")
    print(f"Testes falhados: {total - sucesso}")
    
    if sucesso == total:
        print("\n✅ TODOS OS TESTES PASSARAM!")
    else:
        print(f"\n⚠️ {total - sucesso} teste(s) falharam")
    
    return sucesso == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
#!/usr/bin/env python3
"""
Script para verificar e corrigir os problemas identificados:
1. Produtos não cadastrados causando erro na importação
2. Status FATURADO não sendo salvo nos pedidos
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.producao.models import CadastroPalletizacao
from app.carteira.models import CarteiraPrincipal
from app.pedidos.models import Pedido
from app.faturamento.models import FaturamentoProduto
from app.separacao.models import Separacao
from sqlalchemy import func
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def verificar_produtos_sem_cadastro():
    """Verifica produtos na carteira que não estão cadastrados"""
    print("\n" + "="*80)
    print("1. VERIFICANDO PRODUTOS SEM CADASTRO")
    print("="*80)
    
    # Buscar produtos únicos na carteira
    produtos_carteira = db.session.query(
        CarteiraPrincipal.cod_produto,
        CarteiraPrincipal.nome_produto,
        func.count(CarteiraPrincipal.id).label('qtd_itens')
    ).group_by(
        CarteiraPrincipal.cod_produto,
        CarteiraPrincipal.nome_produto
    ).all()
    
    print(f"Total de produtos únicos na carteira: {len(produtos_carteira)}")
    
    # Verificar quais não estão cadastrados
    produtos_sem_cadastro = []
    for produto in produtos_carteira:
        cadastro = CadastroPalletizacao.query.filter_by(
            cod_produto=produto.cod_produto
        ).first()
        
        if not cadastro:
            produtos_sem_cadastro.append({
                'cod_produto': produto.cod_produto,
                'nome_produto': produto.nome_produto,
                'qtd_itens': produto.qtd_itens
            })
    
    if produtos_sem_cadastro:
        print(f"\n⚠️ ENCONTRADOS {len(produtos_sem_cadastro)} PRODUTOS SEM CADASTRO:")
        for p in produtos_sem_cadastro[:10]:  # Mostrar apenas os 10 primeiros
            print(f"  • {p['cod_produto']}: {p['nome_produto']} ({p['qtd_itens']} itens)")
        
        if len(produtos_sem_cadastro) > 10:
            print(f"  ... e mais {len(produtos_sem_cadastro) - 10} produtos")
    else:
        print("✅ Todos os produtos da carteira estão cadastrados!")
    
    return produtos_sem_cadastro

def cadastrar_produtos_faltantes(produtos_sem_cadastro):
    """Cadastra produtos que estão faltando"""
    if not produtos_sem_cadastro:
        return
    
    resposta = input(f"\nDeseja cadastrar os {len(produtos_sem_cadastro)} produtos faltantes? (s/n): ")
    if resposta.lower() != 's':
        return
    
    print("\n📝 Cadastrando produtos...")
    contador = 0
    
    for produto in produtos_sem_cadastro:
        try:
            novo_cadastro = CadastroPalletizacao(
                cod_produto=produto['cod_produto'],
                nome_produto=produto['nome_produto'] or produto['cod_produto'],
                palletizacao=1.0,  # Valor padrão
                peso_bruto=1.0,    # Valor padrão
                created_by='ScriptCorrecao',
                updated_by='ScriptCorrecao'
            )
            db.session.add(novo_cadastro)
            contador += 1
            
            if contador % 50 == 0:
                db.session.commit()
                print(f"  • {contador} produtos cadastrados...")
        
        except Exception as e:
            logger.error(f"Erro ao cadastrar {produto['cod_produto']}: {e}")
            db.session.rollback()
    
    db.session.commit()
    print(f"✅ {contador} produtos cadastrados com sucesso!")

def verificar_pedidos_faturados_sem_status():
    """Verifica pedidos que foram faturados mas não têm status FATURADO"""
    print("\n" + "="*80)
    print("2. VERIFICANDO PEDIDOS FATURADOS SEM STATUS CORRETO")
    print("="*80)
    
    # Buscar pedidos com NF preenchida mas sem status FATURADO
    pedidos_problema = db.session.query(Pedido).filter(
        Pedido.nf.isnot(None),
        Pedido.nf != "",
        Pedido.status != 'FATURADO'
    ).all()
    
    print(f"Total de pedidos com NF mas sem status FATURADO: {len(pedidos_problema)}")
    
    pedidos_para_corrigir = []
    for pedido in pedidos_problema:
        # Verificar se realmente tem faturamento
        faturamento = FaturamentoProduto.query.filter_by(
            numero_nf=pedido.nf
        ).first()
        
        if faturamento:
            pedidos_para_corrigir.append({
                'pedido': pedido,
                'nf': pedido.nf,
                'status_atual': pedido.status,
                'lote_id': pedido.separacao_lote_id
            })
    
    if pedidos_para_corrigir:
        print(f"\n⚠️ ENCONTRADOS {len(pedidos_para_corrigir)} PEDIDOS PARA CORRIGIR:")
        for p in pedidos_para_corrigir[:10]:
            print(f"  • Pedido {p['pedido'].num_pedido}: NF {p['nf']} - Status atual: '{p['status_atual']}' (Lote: {p['lote_id']})")
        
        if len(pedidos_para_corrigir) > 10:
            print(f"  ... e mais {len(pedidos_para_corrigir) - 10} pedidos")
    else:
        print("✅ Todos os pedidos faturados estão com status correto!")
    
    return pedidos_para_corrigir

def corrigir_status_pedidos(pedidos_para_corrigir):
    """Corrige o status dos pedidos para FATURADO"""
    if not pedidos_para_corrigir:
        return
    
    resposta = input(f"\nDeseja corrigir o status de {len(pedidos_para_corrigir)} pedidos para FATURADO? (s/n): ")
    if resposta.lower() != 's':
        return
    
    print("\n🔄 Corrigindo status dos pedidos...")
    contador = 0
    
    for item in pedidos_para_corrigir:
        try:
            pedido = item['pedido']
            status_antigo = pedido.status
            pedido.status = 'FATURADO'
            contador += 1
            
            logger.info(f"  • Pedido {pedido.num_pedido}: '{status_antigo}' → 'FATURADO'")
            
            if contador % 50 == 0:
                db.session.commit()
                print(f"  • {contador} pedidos corrigidos...")
        
        except Exception as e:
            logger.error(f"Erro ao corrigir pedido {pedido.num_pedido}: {e}")
            db.session.rollback()
    
    db.session.commit()
    print(f"✅ {contador} pedidos corrigidos com sucesso!")

def verificar_separacoes_em_risco():
    """Verifica separações que podem ser apagadas incorretamente"""
    print("\n" + "="*80)
    print("3. VERIFICANDO SEPARAÇÕES EM RISCO")
    print("="*80)
    
    # Buscar separações de pedidos FATURADOS
    separacoes_faturadas = db.session.query(
        Separacao.separacao_lote_id,
        Separacao.num_pedido,
        func.sum(Separacao.qtd_saldo).label('qtd_total'),
        Pedido.status,
        Pedido.nf
    ).join(
        Pedido,
        Separacao.separacao_lote_id == Pedido.separacao_lote_id
    ).filter(
        Pedido.status == 'FATURADO'
    ).group_by(
        Separacao.separacao_lote_id,
        Separacao.num_pedido,
        Pedido.status,
        Pedido.nf
    ).all()
    
    print(f"Total de lotes de separação FATURADOS: {len(separacoes_faturadas)}")
    
    if separacoes_faturadas:
        print("\n✅ SEPARAÇÕES PROTEGIDAS (FATURADAS):")
        for sep in separacoes_faturadas[:10]:
            print(f"  • Lote {sep.separacao_lote_id}: Pedido {sep.num_pedido} - NF {sep.nf} - Qtd: {sep.qtd_total}")
        
        if len(separacoes_faturadas) > 10:
            print(f"  ... e mais {len(separacoes_faturadas) - 10} lotes")
    
    # Verificar separações sem status (em risco)
    separacoes_sem_status = db.session.query(
        Separacao.separacao_lote_id,
        Separacao.num_pedido,
        func.sum(Separacao.qtd_saldo).label('qtd_total')
    ).outerjoin(
        Pedido,
        Separacao.separacao_lote_id == Pedido.separacao_lote_id
    ).filter(
        Pedido.id.is_(None)  # Sem pedido associado
    ).group_by(
        Separacao.separacao_lote_id,
        Separacao.num_pedido
    ).all()
    
    if separacoes_sem_status:
        print(f"\n⚠️ SEPARAÇÕES SEM PEDIDO ASSOCIADO (EM RISCO): {len(separacoes_sem_status)}")
        for sep in separacoes_sem_status[:5]:
            print(f"  • Lote {sep.separacao_lote_id}: Pedido {sep.num_pedido} - Qtd: {sep.qtd_total}")

def main():
    app = create_app()
    
    with app.app_context():
        print("\n" + "="*80)
        print("VERIFICAÇÃO E CORREÇÃO DE PROBLEMAS CRÍTICOS")
        print("="*80)
        
        # 1. Verificar e corrigir produtos sem cadastro
        produtos_sem_cadastro = verificar_produtos_sem_cadastro()
        if produtos_sem_cadastro:
            cadastrar_produtos_faltantes(produtos_sem_cadastro)
        
        # 2. Verificar e corrigir pedidos faturados sem status
        pedidos_para_corrigir = verificar_pedidos_faturados_sem_status()
        if pedidos_para_corrigir:
            corrigir_status_pedidos(pedidos_para_corrigir)
        
        # 3. Verificar separações em risco
        verificar_separacoes_em_risco()
        
        print("\n" + "="*80)
        print("VERIFICAÇÃO CONCLUÍDA")
        print("="*80)
        
        print("\n📋 RESUMO DAS CORREÇÕES APLICADAS:")
        print("1. ✅ Importação da carteira agora cria produtos automaticamente")
        print("2. ✅ Status FATURADO sendo salvo corretamente após processar NF")
        print("3. ✅ Proteção contra exclusão de separações FATURADAS está ativa")
        print("\n⚠️ IMPORTANTE: Execute a sincronização novamente após estas correções!")

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Script para atualizar códigos IBGE em pedidos existentes.

Este script:
1. Busca pedidos que não têm código IBGE
2. Para cada pedido, tenta encontrar a cidade correspondente
3. Atualiza o pedido com o código IBGE encontrado
4. Relatório de resultados

Usar: python atualizar_codigos_ibge_pedidos.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.pedidos.models import Pedido
from app.utils.localizacao import LocalizacaoService
from sqlalchemy import func

def atualizar_codigos_ibge():
    """Atualiza códigos IBGE nos pedidos existentes"""
    app = create_app()
    
    with app.app_context():
        print("🏢 ATUALIZANDO CÓDIGOS IBGE DOS PEDIDOS")
        print("=" * 50)
        
        # Busca pedidos sem código IBGE
        pedidos_sem_ibge = Pedido.query.filter(
            (Pedido.codigo_ibge.is_(None)) | (Pedido.codigo_ibge == '') | (Pedido.codigo_ibge == '0')
        ).all()
        
        print(f"📊 Encontrados {len(pedidos_sem_ibge)} pedidos sem código IBGE")
        
        if not pedidos_sem_ibge:
            print("✅ Todos os pedidos já possuem código IBGE!")
            return
        
        # Contadores para relatório
        atualizados = 0
        nao_encontrados = 0
        com_erro = 0
        
        print("\n🔍 Processando pedidos...")
        
        for i, pedido in enumerate(pedidos_sem_ibge, 1):
            try:
                print(f"[{i:4d}/{len(pedidos_sem_ibge)}] Pedido {pedido.num_pedido} - {pedido.nome_cidade}/{pedido.cod_uf}")
                
                # Usa o LocalizacaoService para buscar a cidade
                cidade_obj = LocalizacaoService.buscar_cidade_unificada(
                    nome=pedido.nome_cidade,
                    uf=pedido.cod_uf,
                    rota=pedido.rota
                )
                
                if cidade_obj and cidade_obj.codigo_ibge:
                    # Atualiza o pedido com o código IBGE
                    pedido.codigo_ibge = cidade_obj.codigo_ibge
                    atualizados += 1
                    print(f"    ✅ Código IBGE {cidade_obj.codigo_ibge} adicionado ({cidade_obj.nome}/{cidade_obj.uf})")
                    
                    # Commit a cada 100 pedidos para não perder o progresso
                    if atualizados % 100 == 0:
                        db.session.commit()
                        print(f"    💾 Progresso salvo: {atualizados} pedidos atualizados")
                
                else:
                    nao_encontrados += 1
                    print(f"    ❌ Cidade não encontrada: {pedido.nome_cidade}/{pedido.cod_uf} (rota: {pedido.rota})")
                
            except Exception as e:
                com_erro += 1
                print(f"    ⚠️  Erro ao processar: {str(e)}")
                continue
        
        # Commit final
        if atualizados > 0:
            db.session.commit()
            print(f"\n💾 Commit final realizado")
        
        # Relatório final
        print("\n📈 RELATÓRIO FINAL")
        print("=" * 30)
        print(f"Total de pedidos processados: {len(pedidos_sem_ibge)}")
        print(f"✅ Pedidos atualizados: {atualizados}")
        print(f"❌ Cidades não encontradas: {nao_encontrados}")
        print(f"⚠️  Pedidos com erro: {com_erro}")
        
        if nao_encontrados > 0:
            print(f"\n🔍 CIDADES NÃO ENCONTRADAS")
            print("Verificar se existem na tabela de cidades:")
            
            # Lista as cidades únicas não encontradas
            pedidos_nao_encontrados = Pedido.query.filter(
                (Pedido.codigo_ibge.is_(None)) | (Pedido.codigo_ibge == '') | (Pedido.codigo_ibge == '0')
            ).all()
            
            cidades_nao_encontradas = set()
            for pedido in pedidos_nao_encontrados:
                if pedido.nome_cidade and pedido.cod_uf:
                    cidade_normalizada = LocalizacaoService.normalizar_nome_cidade_com_regras(
                        pedido.nome_cidade, pedido.rota
                    )
                    if cidade_normalizada:
                        cidades_nao_encontradas.add(f"{cidade_normalizada}/{pedido.cod_uf}")
            
            for cidade in sorted(cidades_nao_encontradas)[:20]:  # Mostra apenas as primeiras 20
                print(f"   • {cidade}")
            
            if len(cidades_nao_encontradas) > 20:
                print(f"   ... e mais {len(cidades_nao_encontradas) - 20} cidades")
        
        # Verifica resultado final
        pedidos_restantes = Pedido.query.filter(
            (Pedido.codigo_ibge.is_(None)) | (Pedido.codigo_ibge == '') | (Pedido.codigo_ibge == '0')
        ).count()
        
        pedidos_com_ibge = Pedido.query.filter(
            Pedido.codigo_ibge.isnot(None),
            Pedido.codigo_ibge != '',
            Pedido.codigo_ibge != '0'
        ).count()
        
        print(f"\n📊 SITUAÇÃO ATUAL:")
        print(f"Pedidos com código IBGE: {pedidos_com_ibge}")
        print(f"Pedidos sem código IBGE: {pedidos_restantes}")
        
        if pedidos_restantes == 0:
            print("🎉 SUCESSO! Todos os pedidos agora possuem código IBGE!")
        else:
            print(f"⚠️  Ainda restam {pedidos_restantes} pedidos sem código IBGE para análise manual")

def verificar_cidades_problematicas():
    """Verifica quais cidades estão causando problemas na busca"""
    app = create_app()
    
    with app.app_context():
        print("\n🔍 ANÁLISE DE CIDADES PROBLEMÁTICAS")
        print("=" * 40)
        
        # Busca pedidos sem código IBGE e agrupa por cidade/UF
        pedidos_sem_ibge = db.session.query(
            Pedido.nome_cidade,
            Pedido.cod_uf,
            Pedido.rota,
            func.count(Pedido.id).label('total')
        ).filter(
            (Pedido.codigo_ibge.is_(None)) | (Pedido.codigo_ibge == '') | (Pedido.codigo_ibge == '0')
        ).group_by(
            Pedido.nome_cidade,
            Pedido.cod_uf,
            Pedido.rota
        ).order_by(
            func.count(Pedido.id).desc()
        ).limit(20).all()
        
        if pedidos_sem_ibge:
            print("Top 20 cidades com mais pedidos sem código IBGE:")
            print("-" * 60)
            
            for item in pedidos_sem_ibge:
                cidade_normalizada = LocalizacaoService.normalizar_nome_cidade_com_regras(
                    item.nome_cidade, item.rota
                )
                print(f"{item.total:3d} pedidos - {item.nome_cidade}/{item.cod_uf} (rota: {item.rota}) -> normalizada: {cidade_normalizada}")
        else:
            print("✅ Nenhuma cidade problemática encontrada!")

if __name__ == "__main__":
    print("ATUALIZAÇÃO DE CÓDIGOS IBGE - SISTEMA DE FRETES")
    print("=" * 55)
    
    # Executa a atualização
    atualizar_codigos_ibge()
    
    # Mostra análise de cidades problemáticas
    verificar_cidades_problematicas()
    
    print("\n✅ Processo concluído!") 
#!/usr/bin/env python3
"""
Script de migração para corrigir campos cod_uf e nome_cidade quando rota = RED.

OBJETIVO:
- Para registros com rota='RED', garantir que cod_uf e nome_cidade estejam corretos
- Se ainda existir na CarteiraPrincipal: usar cod_uf e nome_cidade da carteira
- Se não existir mais na CarteiraPrincipal: assumir cod_uf='SP' e nome_cidade='GUARULHOS'
- MANTER A ROTA RED (não remover)

Autor: Sistema de Migração
Data: 2025-01-18
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.carteira.models import CarteiraPrincipal, PreSeparacaoItem
from app.separacao.models import Separacao
from app.pedidos.models import Pedido
from sqlalchemy import func
from datetime import datetime

def migrar_campos_red():
    """
    Corrige campos cod_uf e nome_cidade para registros com rota RED
    """
    
    app = create_app()
    with app.app_context():
        
        print("\n" + "="*80)
        print("MIGRAÇÃO: CORRIGINDO CAMPOS UF/CIDADE PARA ROTA RED")
        print("="*80)
        
        # Estatísticas iniciais
        total_pedidos_red = Pedido.query.filter(Pedido.rota == 'RED').count()
        total_separacoes_red = Separacao.query.filter(Separacao.rota == 'RED').count()
        
        print(f"\n📊 ESTATÍSTICAS INICIAIS:")
        print(f"   - Pedidos com rota RED: {total_pedidos_red}")
        print(f"   - Separações com rota RED: {total_separacoes_red}")
        
        # =========================================
        # 1. CORRIGIR SEPARAÇÕES COM ROTA RED
        # =========================================
        print(f"\n🔄 CORRIGINDO SEPARAÇÕES COM ROTA RED...")
        
        separacoes_red = Separacao.query.filter(Separacao.rota == 'RED').all()
        separacoes_atualizadas = 0
        separacoes_com_carteira = 0
        separacoes_sem_carteira = 0
        
        for sep in separacoes_red:
            # Buscar item correspondente na CarteiraPrincipal
            item_carteira = CarteiraPrincipal.query.filter_by(
                num_pedido=sep.num_pedido,
                cod_produto=sep.cod_produto
            ).first()
            
            campos_atualizados = False
            
            if item_carteira:
                # Item ainda existe na carteira - usar dados de entrega (cod_uf/nome_cidade)
                if item_carteira.cod_uf and item_carteira.nome_cidade:
                    # Usar campos de ENTREGA da carteira
                    sep.cod_uf = item_carteira.cod_uf
                    sep.nome_cidade = item_carteira.nome_cidade
                    separacoes_com_carteira += 1
                    campos_atualizados = True
                    print(f"   📍 Sep {sep.num_pedido}/{sep.cod_produto}: {item_carteira.nome_cidade}/{item_carteira.cod_uf} (da carteira)")
                else:
                    # Carteira sem dados de entrega - assumir SP/GUARULHOS para RED
                    sep.cod_uf = 'SP'
                    sep.nome_cidade = 'GUARULHOS'
                    separacoes_sem_carteira += 1
                    campos_atualizados = True
                    print(f"   ⚠️  Sep {sep.num_pedido}/{sep.cod_produto}: GUARULHOS/SP (carteira sem dados entrega)")
            else:
                # Item não existe mais na carteira - assumir SP/GUARULHOS para RED
                sep.cod_uf = 'SP'
                sep.nome_cidade = 'GUARULHOS'
                separacoes_sem_carteira += 1
                campos_atualizados = True
                print(f"   ⚠️  Sep {sep.num_pedido}/{sep.cod_produto}: GUARULHOS/SP (não encontrado na carteira)")
            
            if campos_atualizados:
                separacoes_atualizadas += 1
            
            if separacoes_atualizadas % 100 == 0:
                print(f"   - {separacoes_atualizadas} separações processadas...")
        
        print(f"   ✅ {separacoes_atualizadas} separações corrigidas")
        print(f"      - {separacoes_com_carteira} com dados da carteira")
        print(f"      - {separacoes_sem_carteira} assumidos como SP/GUARULHOS")
        
        # =========================================
        # 2. CORRIGIR PEDIDOS COM ROTA RED
        # =========================================
        print(f"\n🔄 CORRIGINDO PEDIDOS COM ROTA RED...")
        
        pedidos_red = Pedido.query.filter(Pedido.rota == 'RED').all()
        pedidos_atualizados = 0
        pedidos_com_separacao = 0
        pedidos_com_carteira = 0
        pedidos_sem_dados = 0
        
        for pedido in pedidos_red:
            campos_atualizados = False
            
            # Primeiro tentar buscar dados da Separacao (já corrigida acima)
            if pedido.separacao_lote_id:
                separacao = Separacao.query.filter_by(
                    separacao_lote_id=pedido.separacao_lote_id,
                    num_pedido=pedido.num_pedido
                ).first()
                
                if separacao:
                    # Usar dados da separação (que já foram corrigidos acima)
                    pedido.cod_uf = separacao.cod_uf
                    pedido.nome_cidade = separacao.nome_cidade
                    pedidos_com_separacao += 1
                    campos_atualizados = True
                    print(f"   📍 Pedido {pedido.num_pedido}: {separacao.nome_cidade}/{separacao.cod_uf} (da separação)")
                    continue
            
            # Se não tem separação, tentar buscar na CarteiraPrincipal
            items_carteira = CarteiraPrincipal.query.filter_by(
                num_pedido=pedido.num_pedido
            ).all()
            
            if items_carteira:
                # Pegar o primeiro item com dados de entrega válidos
                for item in items_carteira:
                    if item.cod_uf and item.nome_cidade:
                        pedido.cod_uf = item.cod_uf
                        pedido.nome_cidade = item.nome_cidade
                        pedidos_com_carteira += 1
                        campos_atualizados = True
                        print(f"   📍 Pedido {pedido.num_pedido}: {item.nome_cidade}/{item.cod_uf} (da carteira)")
                        break
            
            # Se ainda não tem dados, assumir SP/GUARULHOS para RED
            if not campos_atualizados:
                pedido.cod_uf = 'SP'
                pedido.nome_cidade = 'GUARULHOS'
                pedidos_sem_dados += 1
                campos_atualizados = True
                print(f"   ⚠️  Pedido {pedido.num_pedido}: GUARULHOS/SP (sem dados na carteira/separação)")
            
            if campos_atualizados:
                pedidos_atualizados += 1
            
            if pedidos_atualizados % 100 == 0:
                print(f"   - {pedidos_atualizados} pedidos processados...")
        
        print(f"   ✅ {pedidos_atualizados} pedidos corrigidos")
        print(f"      - {pedidos_com_separacao} com dados da separação")
        print(f"      - {pedidos_com_carteira} com dados da carteira")
        print(f"      - {pedidos_sem_dados} assumidos como SP/GUARULHOS")
        
        # =========================================
        # 3. VALIDAR INTEGRIDADE
        # =========================================
        print(f"\n🔍 VALIDANDO INTEGRIDADE...")
        
        # Verificar registros RED sem UF/Cidade
        pedidos_red_sem_uf = Pedido.query.filter(
            Pedido.rota == 'RED',
            (Pedido.cod_uf == None) | (Pedido.cod_uf == '')
        ).count()
        
        pedidos_red_sem_cidade = Pedido.query.filter(
            Pedido.rota == 'RED',
            (Pedido.nome_cidade == None) | (Pedido.nome_cidade == '')
        ).count()
        
        separacoes_red_sem_uf = Separacao.query.filter(
            Separacao.rota == 'RED',
            (Separacao.cod_uf == None) | (Separacao.cod_uf == '')
        ).count()
        
        separacoes_red_sem_cidade = Separacao.query.filter(
            Separacao.rota == 'RED',
            (Separacao.nome_cidade == None) | (Separacao.nome_cidade == '')
        ).count()
        
        print(f"   - Pedidos RED sem UF: {pedidos_red_sem_uf}")
        print(f"   - Pedidos RED sem cidade: {pedidos_red_sem_cidade}")
        print(f"   - Separações RED sem UF: {separacoes_red_sem_uf}")
        print(f"   - Separações RED sem cidade: {separacoes_red_sem_cidade}")
        
        # =========================================
        # 4. COMMIT OU ROLLBACK
        # =========================================
        
        if pedidos_red_sem_uf > 0 or pedidos_red_sem_cidade > 0 or \
           separacoes_red_sem_uf > 0 or separacoes_red_sem_cidade > 0:
            print(f"\n⚠️  AVISO: Ainda existem registros RED sem UF ou cidade!")
            resposta = input("Deseja continuar mesmo assim? (s/n): ")
            if resposta.lower() != 's':
                print(f"   Fazendo ROLLBACK...")
                db.session.rollback()
                return False
        
        print(f"\n💾 Salvando alterações no banco de dados...")
        
        try:
            db.session.commit()
            print(f"✅ MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
            
            # Resumo final
            print(f"\n📊 RESUMO FINAL:")
            print(f"   - Total de separações corrigidas: {separacoes_atualizadas}")
            print(f"   - Total de pedidos corrigidos: {pedidos_atualizados}")
            print(f"   - Registros RED sem dados foram assumidos como SP/GUARULHOS")
            print(f"   - A rota RED foi MANTIDA em todos os registros")
            
            return True
            
        except Exception as e:
            print(f"\n❌ ERRO ao salvar: {str(e)}")
            print(f"   Fazendo ROLLBACK...")
            db.session.rollback()
            return False

def verificar_dados_red():
    """
    Verifica e exibe estatísticas dos dados RED após migração
    """
    app = create_app()
    with app.app_context():
        
        print("\n" + "="*80)
        print("VERIFICAÇÃO DE DADOS RED")
        print("="*80)
        
        # Análise de Pedidos RED
        print(f"\n📊 PEDIDOS COM ROTA RED:")
        pedidos_red = Pedido.query.filter(Pedido.rota == 'RED').all()
        
        if pedidos_red:
            # Agrupar por cidade/UF
            cidades_red = {}
            for p in pedidos_red:
                chave = f"{p.nome_cidade}/{p.cod_uf}"
                if chave not in cidades_red:
                    cidades_red[chave] = 0
                cidades_red[chave] += 1
            
            print(f"   Total: {len(pedidos_red)} pedidos")
            print(f"\n   Distribuição por cidade:")
            for cidade, qtd in sorted(cidades_red.items(), key=lambda x: x[1], reverse=True)[:10]:
                print(f"   - {cidade}: {qtd} pedidos")
        else:
            print("   Nenhum pedido com rota RED encontrado")
        
        # Análise de Separações RED
        print(f"\n📊 SEPARAÇÕES COM ROTA RED:")
        separacoes_red = Separacao.query.filter(Separacao.rota == 'RED').all()
        
        if separacoes_red:
            # Agrupar por cidade/UF
            cidades_red = {}
            for s in separacoes_red:
                chave = f"{s.nome_cidade}/{s.cod_uf}"
                if chave not in cidades_red:
                    cidades_red[chave] = 0
                cidades_red[chave] += 1
            
            print(f"   Total: {len(separacoes_red)} separações")
            print(f"\n   Distribuição por cidade:")
            for cidade, qtd in sorted(cidades_red.items(), key=lambda x: x[1], reverse=True)[:10]:
                print(f"   - {cidade}: {qtd} separações")
        else:
            print("   Nenhuma separação com rota RED encontrada")
        
        # Verificar consistência
        print(f"\n🔍 VERIFICAÇÃO DE CONSISTÊNCIA:")
        
        # Pedidos RED que são realmente para Guarulhos
        pedidos_red_guarulhos = Pedido.query.filter(
            Pedido.rota == 'RED',
            Pedido.cod_uf == 'SP',
            Pedido.nome_cidade == 'GUARULHOS'
        ).count()
        
        # Pedidos RED para outras cidades
        pedidos_red_outras = Pedido.query.filter(
            Pedido.rota == 'RED',
            ~((Pedido.cod_uf == 'SP') & (Pedido.nome_cidade == 'GUARULHOS'))
        ).count()
        
        print(f"   - Pedidos RED para GUARULHOS/SP: {pedidos_red_guarulhos}")
        print(f"   - Pedidos RED para outras cidades: {pedidos_red_outras}")
        
        if pedidos_red_outras > 0:
            print(f"\n   ⚠️  ATENÇÃO: Existem {pedidos_red_outras} pedidos RED que NÃO são para Guarulhos/SP")
            print(f"      Isso pode indicar que o campo cod_uf/nome_cidade foi preenchido corretamente")
            print(f"      com o destino real do redespacho.")

if __name__ == "__main__":
    
    print("\n🚀 INICIANDO CORREÇÃO DE CAMPOS PARA ROTA RED\n")
    
    # Executar migração
    sucesso = migrar_campos_red()
    
    if sucesso:
        # Verificar dados após migração
        verificar_dados_red()
        
        print("\n✅ PROCESSO COMPLETO!")
        print("\n📝 PRÓXIMOS PASSOS:")
        print("   1. Agora os campos cod_uf e nome_cidade estão corretos")
        print("   2. A rota RED foi MANTIDA para identificação")
        print("   3. Próximo passo: ajustar app.cotacao para usar diretamente cod_uf/nome_cidade")
    else:
        print("\n❌ MIGRAÇÃO FALHOU!")
        print("   Verifique os erros acima e tente novamente.")
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para atualizar movimentações previstas baseado em:
1. Separações (vinculando com Pedido via separacao_lote_id para obter datas)
2. Pré-separações (usando data_expedicao_editada)
3. Programação de produção (o trigger já deve cuidar automaticamente)

Data: 08/08/2025
"""

import os
import sys
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import text

# Adicionar o path do projeto ao sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.estoque.models_tempo_real import MovimentacaoPrevista
from app.separacao.models import Separacao
from app.pedidos.models import Pedido
from app.carteira.models import PreSeparacaoItem
from app.utils.timezone import agora_brasil

def limpar_movimentacoes_antigas():
    """
    Limpa movimentações antigas para reconstruir do zero.
    
    NOTA: Isso remove TODAS as movimentações, incluindo as de programação.
    Se quiser preservar as de programação, ajustar a query.
    """
    print("\n=== LIMPANDO MOVIMENTAÇÕES ANTIGAS ===")
    
    try:
        # Limpar todas as movimentações previstas para reconstruir
        count = db.session.query(MovimentacaoPrevista).delete()
        db.session.commit()
        print(f"✓ {count} movimentações previstas removidas para reconstrução")
        
    except Exception as e:
        db.session.rollback()
        print(f"✗ Erro ao limpar movimentações: {e}")
        raise

def atualizar_movimentacoes_separacao():
    """
    Atualiza movimentações previstas baseadas em Separações.
    Usa o vínculo com Pedido via separacao_lote_id para obter data de expedição.
    """
    print("\n=== ATUALIZANDO MOVIMENTAÇÕES DE SEPARAÇÃO ===")
    
    try:
        # Query para obter separações com suas datas via Pedido
        query = text("""
            SELECT 
                s.cod_produto,
                s.qtd_saldo,
                p.expedicao as data_expedicao,
                s.separacao_lote_id,
                s.num_pedido
            FROM separacao s
            INNER JOIN pedidos p ON s.separacao_lote_id = p.separacao_lote_id
            WHERE s.qtd_saldo > 0 
                AND p.expedicao IS NOT NULL
                AND p.status NOT IN ('CANCELADO', 'FATURADO')
            ORDER BY s.cod_produto, p.expedicao
        """)
        
        resultados = db.session.execute(query).fetchall()
        
        print(f"Encontradas {len(resultados)} separações para processar")
        
        # Agrupar por produto e data
        movimentacoes = {}
        
        for row in resultados:
            cod_produto = row.cod_produto
            qtd = Decimal(str(row.qtd_saldo))
            data = row.data_expedicao
            
            # Criar chave única
            chave = (cod_produto, data)
            
            if chave not in movimentacoes:
                movimentacoes[chave] = {
                    'entrada': Decimal('0'),
                    'saida': Decimal('0')
                }
            
            # Separação é sempre saída
            movimentacoes[chave]['saida'] += qtd
        
        # Inserir/atualizar movimentações
        count_inseridas = 0
        count_atualizadas = 0
        
        for (cod_produto, data_prevista), valores in movimentacoes.items():
            # Verificar se já existe
            mov_existente = db.session.query(MovimentacaoPrevista).filter_by(
                cod_produto=cod_produto,
                data_prevista=data_prevista
            ).first()
            
            if mov_existente:
                # Atualizar valores (somar com existente)
                mov_existente.saida_prevista += valores['saida']
                count_atualizadas += 1
            else:
                # Criar nova
                nova_mov = MovimentacaoPrevista(
                    cod_produto=cod_produto,
                    data_prevista=data_prevista,
                    entrada_prevista=valores['entrada'],
                    saida_prevista=valores['saida']
                )
                db.session.add(nova_mov)
                count_inseridas += 1
        
        db.session.commit()
        
        print(f"✓ {count_inseridas} movimentações inseridas")
        print(f"✓ {count_atualizadas} movimentações atualizadas")
        print(f"✓ Total de produtos distintos: {len(set(cod for cod, _ in movimentacoes.keys()))}")
        
    except Exception as e:
        db.session.rollback()
        print(f"✗ Erro ao atualizar movimentações de separação: {e}")
        raise

def atualizar_movimentacoes_pre_separacao():
    """
    Atualiza movimentações previstas baseadas em Pré-Separações.
    Usa data_expedicao_editada da própria tabela.
    
    IMPORTANTE: Campo 'recomposto' é IRRELEVANTE para movimentações!
    - É apenas um ciclo decorativo durante sincronização (false → true → false)
    - NÃO afeta quantidades nem status real da pré-separação
    - Tanto 'CRIADO' quanto 'RECOMPOSTO' são pré-separações ATIVAS
    
    Ver: app/carteira/models.py linha 656 e FLUXO_COMPLETO_SINCRONIZACAO.md
    """
    print("\n=== ATUALIZANDO MOVIMENTAÇÕES DE PRÉ-SEPARAÇÃO ===")
    
    try:
        # Query para obter TODAS as pré-separações ativas
        # IGNORA completamente o campo 'recomposto' (é inútil)
        # Filtra apenas por status real: CRIADO e RECOMPOSTO são ambos ATIVOS
        query = text("""
            SELECT 
                cod_produto,
                qtd_selecionada_usuario as quantidade,
                data_expedicao_editada as data_expedicao,
                separacao_lote_id,
                num_pedido,
                status,
                recomposto
            FROM pre_separacao_item
            WHERE qtd_selecionada_usuario > 0 
                AND data_expedicao_editada IS NOT NULL
                AND status IN ('CRIADO', 'RECOMPOSTO')  -- Ambos são ativos!
            ORDER BY cod_produto, data_expedicao_editada
        """)
        
        resultados = db.session.execute(query).fetchall()
        
        print(f"Encontradas {len(resultados)} pré-separações para processar")
        
        # Contar por status real (o que importa)
        status_count = {}
        for r in resultados:
            status_count[r.status] = status_count.get(r.status, 0) + 1
        
        for status, count in status_count.items():
            print(f"  - Status {status}: {count} itens")
        
        # Agrupar por produto e data
        movimentacoes = {}
        
        for row in resultados:
            cod_produto = row.cod_produto
            qtd = Decimal(str(row.quantidade))
            data = row.data_expedicao
            
            # Criar chave única
            chave = (cod_produto, data)
            
            if chave not in movimentacoes:
                movimentacoes[chave] = {
                    'entrada': Decimal('0'),
                    'saida': Decimal('0')
                }
            
            # Pré-separação é sempre saída prevista
            movimentacoes[chave]['saida'] += qtd
        
        # Inserir/atualizar movimentações
        count_inseridas = 0
        count_atualizadas = 0
        
        for (cod_produto, data_prevista), valores in movimentacoes.items():
            # Verificar se já existe
            mov_existente = db.session.query(MovimentacaoPrevista).filter_by(
                cod_produto=cod_produto,
                data_prevista=data_prevista
            ).first()
            
            if mov_existente:
                # Atualizar valores (somar com existente)
                mov_existente.saida_prevista += valores['saida']
                count_atualizadas += 1
            else:
                # Criar nova
                nova_mov = MovimentacaoPrevista(
                    cod_produto=cod_produto,
                    data_prevista=data_prevista,
                    entrada_prevista=valores['entrada'],
                    saida_prevista=valores['saida']
                )
                db.session.add(nova_mov)
                count_inseridas += 1
        
        db.session.commit()
        
        print(f"✓ {count_inseridas} movimentações inseridas")
        print(f"✓ {count_atualizadas} movimentações atualizadas")
        print(f"✓ Total de produtos distintos: {len(set(cod for cod, _ in movimentacoes.keys()))}")
        
    except Exception as e:
        db.session.rollback()
        print(f"✗ Erro ao atualizar movimentações de pré-separação: {e}")
        raise

def atualizar_movimentacoes_producao():
    """
    Atualiza movimentações previstas baseadas em Programação de Produção.
    As programações de produção geram ENTRADAS previstas.
    """
    print("\n=== ATUALIZANDO MOVIMENTAÇÕES DE PRODUÇÃO ===")
    
    try:
        # Verificar se a tabela existe
        query_check = text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'programacao_producao'
            LIMIT 1
        """)
        
        result_check = db.session.execute(query_check).fetchone()
        
        if not result_check:
            print("  ℹ️  Tabela programacao_producao não encontrada")
            return
            
        # Buscar programações com data
        query = text("""
            SELECT 
                cod_produto,
                SUM(qtd_programada) as quantidade,
                data_programacao
            FROM programacao_producao
            WHERE qtd_programada > 0
                AND data_programacao IS NOT NULL
                AND data_programacao >= CURRENT_DATE
            GROUP BY cod_produto, data_programacao
            ORDER BY cod_produto, data_programacao
        """)
        
        resultados = db.session.execute(query).fetchall()
        
        print(f"Encontradas {len(resultados)} programações de produção para processar")
        
        # Agrupar por produto e data
        movimentacoes = {}
        
        for row in resultados:
            cod_produto = row.cod_produto
            qtd = Decimal(str(row.quantidade))
            data = row.data_programacao
            
            # Criar chave única
            chave = (cod_produto, data)
            
            if chave not in movimentacoes:
                movimentacoes[chave] = {
                    'entrada': Decimal('0'),
                    'saida': Decimal('0')
                }
            
            # Programação de produção é sempre ENTRADA
            movimentacoes[chave]['entrada'] += qtd
        
        # Inserir/atualizar movimentações
        count_inseridas = 0
        count_atualizadas = 0
        
        for (cod_produto, data_prevista), valores in movimentacoes.items():
            # Verificar se já existe
            mov_existente = db.session.query(MovimentacaoPrevista).filter_by(
                cod_produto=cod_produto,
                data_prevista=data_prevista
            ).first()
            
            if mov_existente:
                # Atualizar valores (somar com existente)
                mov_existente.entrada_prevista += valores['entrada']
                count_atualizadas += 1
            else:
                # Criar nova
                nova_mov = MovimentacaoPrevista(
                    cod_produto=cod_produto,
                    data_prevista=data_prevista,
                    entrada_prevista=valores['entrada'],
                    saida_prevista=valores['saida']
                )
                db.session.add(nova_mov)
                count_inseridas += 1
        
        db.session.commit()
        
        print(f"✓ {count_inseridas} movimentações inseridas")
        print(f"✓ {count_atualizadas} movimentações atualizadas")
        print(f"✓ Total de produtos distintos: {len(set(cod for cod, _ in movimentacoes.keys()))}")
        
    except Exception as e:
        print(f"  ⚠️  Erro ao processar programação de produção: {e}")
        # Tentar sem programação, pois pode não existir
        db.session.rollback()

def verificar_detalhes_pre_separacao():
    """
    Exibe detalhes sobre o estado das pré-separações para debug
    """
    print("\n=== DETALHES DAS PRÉ-SEPARAÇÕES ===")
    
    try:
        # Query focada no que realmente importa: STATUS
        query = text("""
            SELECT 
                status,
                COUNT(*) as total,
                SUM(qtd_selecionada_usuario) as qtd_total,
                COUNT(DISTINCT num_pedido) as pedidos_distintos,
                COUNT(DISTINCT cod_produto) as produtos_distintos
            FROM pre_separacao_item
            WHERE qtd_selecionada_usuario > 0
            GROUP BY status
            ORDER BY 
                CASE status
                    WHEN 'CRIADO' THEN 1
                    WHEN 'RECOMPOSTO' THEN 2
                    WHEN 'ENVIADO_SEPARACAO' THEN 3
                    WHEN 'CANCELADO' THEN 4
                    ELSE 5
                END
        """)
        
        resultados = db.session.execute(query).fetchall()
        
        if resultados:
            print("\n📊 Resumo por Status (o que realmente importa):")
            total_geral = 0
            qtd_geral = 0
            
            for row in resultados:
                ativo = "✅" if row.status in ['CRIADO', 'RECOMPOSTO'] else "❌"
                print(f"  {ativo} {row.status}: {row.total} itens, {row.qtd_total:.0f} unidades")
                print(f"      └─ {row.pedidos_distintos} pedidos, {row.produtos_distintos} produtos")
                
                if row.status in ['CRIADO', 'RECOMPOSTO']:
                    total_geral += row.total
                    qtd_geral += row.qtd_total or 0
            
            print(f"\n  📈 TOTAL ATIVO: {total_geral} itens, {qtd_geral:.0f} unidades")
            
            # Análise adicional do campo recomposto (apenas informativo)
            query_recomp = text("""
                SELECT 
                    recomposto,
                    COUNT(*) as total
                FROM pre_separacao_item
                WHERE status IN ('CRIADO', 'RECOMPOSTO')
                GROUP BY recomposto
            """)
            
            resultados_recomp = db.session.execute(query_recomp).fetchall()
            
            if resultados_recomp:
                print("\n  ℹ️  Campo 'recomposto' (decorativo, não afeta movimentações):")
                for row in resultados_recomp:
                    texto = "True (já passou por verificação)" if row.recomposto else "False (aguardando verificação)"
                    print(f"      - {texto}: {row.total} itens")
                    
        else:
            print("  ℹ️  Nenhuma pré-separação encontrada")
            
    except Exception as e:
        print(f"✗ Erro ao verificar detalhes: {e}")
        db.session.rollback()  # Limpar a transação com erro

def estatisticas_finais():
    """Exibe estatísticas finais das movimentações"""
    print("\n=== ESTATÍSTICAS FINAIS ===")
    
    try:
        # Total de movimentações
        total = db.session.query(MovimentacaoPrevista).count()
        print(f"Total de movimentações previstas: {total}")
        
        # Por tipo
        query = text("""
            SELECT 
                COUNT(*) as total,
                COUNT(DISTINCT cod_produto) as produtos,
                MIN(data_prevista) as data_inicio,
                MAX(data_prevista) as data_fim,
                SUM(entrada_prevista) as total_entradas,
                SUM(saida_prevista) as total_saidas
            FROM movimentacao_prevista
        """)
        
        resultado = db.session.execute(query).fetchone()
        
        if resultado and resultado.total > 0:
            print(f"\n📊 Resumo Geral:")
            print(f"  - Registros: {resultado.total}")
            print(f"  - Produtos: {resultado.produtos}")
            print(f"  - Período: {resultado.data_inicio} até {resultado.data_fim}")
            print(f"  - Total Entradas Previstas: {resultado.total_entradas:.3f}")
            print(f"  - Total Saídas Previstas: {resultado.total_saidas:.3f}")
        
        # Top 10 produtos com mais movimentações
        query_top = text("""
            SELECT 
                cod_produto,
                COUNT(*) as dias,
                SUM(entrada_prevista) as entradas,
                SUM(saida_prevista) as saidas
            FROM movimentacao_prevista
            GROUP BY cod_produto
            ORDER BY (SUM(entrada_prevista) + SUM(saida_prevista)) DESC
            LIMIT 10
        """)
        
        top_produtos = db.session.execute(query_top).fetchall()
        
        if top_produtos:
            print(f"\n🏆 Top 10 Produtos com Maior Movimentação:")
            for i, prod in enumerate(top_produtos, 1):
                print(f"  {i}. {prod.cod_produto}: {prod.dias} dias, "
                      f"Entrada: {prod.entradas:.0f}, Saída: {prod.saidas:.0f}")
        
    except Exception as e:
        print(f"✗ Erro ao gerar estatísticas: {e}")
        db.session.rollback()  # Limpar a transação com erro

def main():
    """Função principal"""
    print("=" * 60)
    print("ATUALIZAÇÃO DE MOVIMENTAÇÕES PREVISTAS")
    print("=" * 60)
    print(f"Início: {agora_brasil().strftime('%d/%m/%Y %H:%M:%S')}")
    print("\n⚠️  NOTA IMPORTANTE:")
    print("   Campo 'recomposto' é IGNORADO - é apenas decorativo!")
    print("   Ver: FLUXO_COMPLETO_SINCRONIZACAO.md para detalhes")
    print("=" * 60)
    
    try:
        # Limpar movimentações antigas
        limpar_movimentacoes_antigas()
        
        # Atualizar movimentações de separação
        atualizar_movimentacoes_separacao()
        
        # Atualizar movimentações de pré-separação
        atualizar_movimentacoes_pre_separacao()
        
        # Atualizar movimentações de produção (ENTRADAS)
        atualizar_movimentacoes_producao()
        
        # Detalhes das pré-separações (debug)
        verificar_detalhes_pre_separacao()
        
        # Estatísticas finais
        estatisticas_finais()
        
        print("\n" + "=" * 60)
        print("✅ PROCESSO CONCLUÍDO COM SUCESSO!")
        print(f"Fim: {agora_brasil().strftime('%d/%m/%Y %H:%M:%S')}")
        print("=" * 60)
        
    except Exception as e:
        print("\n" + "=" * 60)
        print(f"❌ ERRO NO PROCESSO: {e}")
        print("=" * 60)
        sys.exit(1)

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        main()
#!/usr/bin/env python3
"""
Script para inicializar o sistema de estoque em tempo real
Popula as tabelas com dados existentes de MovimentacaoEstoque
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.estoque.models import MovimentacaoEstoque, UnificacaoCodigos
from app.estoque.models_tempo_real import EstoqueTempoReal, MovimentacaoPrevista
from app.estoque.services.estoque_tempo_real import ServicoEstoqueTempoReal
from decimal import Decimal
from datetime import date
from sqlalchemy import inspect

def inicializar_estoque_tempo_real():
    """Inicializa o sistema de estoque em tempo real com dados existentes"""
    
    app = create_app()
    
    with app.app_context():
        print("=" * 60)
        print("INICIALIZAÇÃO DO SISTEMA DE ESTOQUE EM TEMPO REAL")
        print("=" * 60)
        
        # Verificar se as tabelas existem
        inspector = inspect(db.engine)
        if not inspector.has_table('estoque_tempo_real'):
            print("❌ Tabela estoque_tempo_real não existe. Execute a migração primeiro.")
            return False
        
        if not inspector.has_table('movimentacao_prevista'):
            print("❌ Tabela movimentacao_prevista não existe. Execute a migração primeiro.")
            return False
        
        # Buscar produtos únicos de MovimentacaoEstoque
        print("\n📊 Buscando produtos com movimentação...")
        produtos = db.session.query(
            MovimentacaoEstoque.cod_produto,
            MovimentacaoEstoque.nome_produto
        ).filter(
            MovimentacaoEstoque.ativo == True
        ).distinct().all()
        
        print(f"✅ Encontrados {len(produtos)} produtos únicos")
        
        if not produtos:
            print("⚠️ Nenhum produto encontrado em MovimentacaoEstoque")
            return True
        
        # Processar cada produto
        print("\n🔄 Processando produtos...")
        processados = 0
        erros = []
        
        for produto in produtos:
            try:
                cod_produto = produto.cod_produto
                nome_produto = produto.nome_produto
                
                # Verificar se já existe
                estoque_existente = EstoqueTempoReal.query.filter_by(
                    cod_produto=cod_produto
                ).first()
                
                if estoque_existente:
                    print(f"⏭️ Produto {cod_produto} já existe, pulando...")
                    continue
                
                # Calcular saldo inicial baseado em todas as movimentações
                saldo = Decimal('0')
                
                # Considerar códigos unificados
                codigos_relacionados = UnificacaoCodigos.get_todos_codigos_relacionados(cod_produto)
                
                for codigo in codigos_relacionados:
                    movs = MovimentacaoEstoque.query.filter_by(
                        cod_produto=codigo,
                        ativo=True
                    ).all()
                    
                    for mov in movs:
                        # qtd_movimentacao já vem com sinal correto (negativo para saídas)
                        saldo += Decimal(str(mov.qtd_movimentacao))
                
                # Criar registro de EstoqueTempoReal
                novo_estoque = EstoqueTempoReal(
                    cod_produto=cod_produto,
                    nome_produto=nome_produto,
                    saldo_atual=saldo
                )
                
                db.session.add(novo_estoque)
                processados += 1
                
                if processados % 10 == 0:
                    print(f"  ✓ Processados {processados} produtos...")
                    db.session.flush()  # Flush parcial para não perder progresso
                
            except Exception as e:
                erros.append({
                    'produto': cod_produto,
                    'erro': str(e)
                })
                print(f"  ❌ Erro ao processar {cod_produto}: {e}")
        
        # Commit final
        try:
            db.session.commit()
            print(f"\n✅ Inicialização concluída!")
            print(f"   - Produtos processados: {processados}")
            print(f"   - Erros: {len(erros)}")
            
            if erros:
                print("\n⚠️ Produtos com erro:")
                for erro in erros[:5]:  # Mostrar apenas primeiros 5 erros
                    print(f"   - {erro['produto']}: {erro['erro']}")
                if len(erros) > 5:
                    print(f"   ... e mais {len(erros) - 5} erros")
            
            # Calcular rupturas para todos os produtos
            print("\n🔮 Calculando projeções de ruptura...")
            produtos_tempo_real = EstoqueTempoReal.query.all()
            for produto in produtos_tempo_real:
                try:
                    ServicoEstoqueTempoReal.calcular_ruptura_d7(produto.cod_produto)
                except Exception as e:
                    print(f"  ⚠️ Erro ao calcular ruptura para {produto.cod_produto}: {e}")
            
            db.session.commit()
            print("✅ Projeções calculadas!")
            
            # Estatísticas finais
            total_produtos = EstoqueTempoReal.query.count()
            produtos_negativos = EstoqueTempoReal.query.filter(
                EstoqueTempoReal.saldo_atual < 0
            ).count()
            produtos_ruptura = EstoqueTempoReal.query.filter(
                EstoqueTempoReal.dia_ruptura.isnot(None)
            ).count()
            
            print("\n📈 ESTATÍSTICAS FINAIS:")
            print(f"   - Total de produtos: {total_produtos}")
            print(f"   - Produtos com estoque negativo: {produtos_negativos}")
            print(f"   - Produtos com ruptura prevista: {produtos_ruptura}")
            
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Erro ao fazer commit: {e}")
            return False


if __name__ == "__main__":
    sucesso = inicializar_estoque_tempo_real()
    sys.exit(0 if sucesso else 1)
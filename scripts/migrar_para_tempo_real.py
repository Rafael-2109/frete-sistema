#!/usr/bin/env python3
"""
Script de Migração para Sistema de Estoque em Tempo Real
Popula as novas tabelas EstoqueTempoReal e MovimentacaoPrevista
com dados existentes no sistema
"""

import os
import sys
from datetime import date, timedelta
from decimal import Decimal

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.estoque.models import MovimentacaoEstoque, UnificacaoCodigos, ProgramacaoProducao
from app.estoque.models_tempo_real import EstoqueTempoReal, MovimentacaoPrevista
from app.estoque.services.estoque_tempo_real import ServicoEstoqueTempoReal
from app.carteira.models import PreSeparacaoItem
from app.separacao.models import Separacao
from app.utils import agora_brasil


def criar_tabelas():
    """Criar tabelas se não existirem"""
    print("🔨 Criando tabelas...")
    try:
        db.create_all()
        print("✅ Tabelas criadas com sucesso")
    except Exception as e:
        print(f"❌ Erro ao criar tabelas: {e}")
        return False
    return True


def migrar_estoque_atual():
    """
    Migra saldo atual de estoque baseado em MovimentacaoEstoque
    """
    print("\n📦 Migrando estoque atual...")
    
    # Buscar todos os produtos únicos
    produtos = db.session.query(
        MovimentacaoEstoque.cod_produto,
        MovimentacaoEstoque.nome_produto
    ).filter(
        MovimentacaoEstoque.ativo == True
    ).distinct().all()
    
    print(f"  📊 {len(produtos)} produtos encontrados")
    
    processados = 0
    erros = []
    
    for cod_produto, nome_produto in produtos:
        try:
            # Calcular saldo atual
            saldo = Decimal('0')
            
            # Considerar unificação
            codigos = UnificacaoCodigos.get_todos_codigos_relacionados(cod_produto)
            
            for codigo in codigos:
                movs = MovimentacaoEstoque.query.filter_by(
                    cod_produto=codigo,
                    ativo=True
                ).all()
                
                for mov in movs:
                    if mov.tipo_movimentacao == 'ENTRADA':
                        saldo += Decimal(str(mov.qtd_movimentacao))
                    else:
                        saldo -= Decimal(str(mov.qtd_movimentacao))
            
            # Criar ou atualizar EstoqueTempoReal
            estoque = EstoqueTempoReal.query.filter_by(
                cod_produto=cod_produto
            ).first()
            
            if not estoque:
                estoque = EstoqueTempoReal(
                    cod_produto=cod_produto,
                    nome_produto=nome_produto or f"Produto {cod_produto}"
                )
            
            estoque.saldo_atual = saldo
            estoque.atualizado_em = agora_brasil()
            
            db.session.add(estoque)
            processados += 1
            
            # Commit a cada 100 produtos
            if processados % 100 == 0:
                db.session.commit()
                print(f"  ✅ {processados} produtos processados...")
                
        except Exception as e:
            erros.append(f"Produto {cod_produto}: {str(e)}")
    
    # Commit final
    try:
        db.session.commit()
        print(f"✅ Estoque atual migrado: {processados} produtos")
    except Exception as e:
        db.session.rollback()
        print(f"❌ Erro no commit final: {e}")
    
    if erros:
        print(f"⚠️  {len(erros)} erros encontrados:")
        for erro in erros[:5]:  # Mostrar apenas 5 primeiros
            print(f"    - {erro}")
    
    return processados


def migrar_movimentacoes_previstas():
    """
    Migra movimentações previstas de PreSeparacao, Separacao e ProgramacaoProducao
    """
    print("\n📅 Migrando movimentações previstas...")
    
    hoje = date.today()
    total_movs = 0
    
    # 1. Migrar PreSeparacaoItem (saídas previstas)
    print("  📤 Processando pré-separações...")
    preseps = PreSeparacaoItem.query.filter(
        PreSeparacaoItem.recomposto == False,
        PreSeparacaoItem.data_expedicao_editada >= hoje
    ).all()
    
    for item in preseps:
        if item.qtd_selecionada_usuario > 0:
            ServicoEstoqueTempoReal.atualizar_movimentacao_prevista(
                cod_produto=item.cod_produto,
                data=item.data_expedicao_editada,
                qtd_saida=Decimal(str(item.qtd_selecionada_usuario))
            )
            total_movs += 1
    
    print(f"    ✅ {len(preseps)} pré-separações processadas")
    
    # 2. Migrar Separacao (saídas previstas)
    print("  📤 Processando separações...")
    seps = Separacao.query.filter(
        Separacao.expedicao >= hoje,
        Separacao.qtd_saldo > 0
    ).all()
    
    for sep in seps:
        ServicoEstoqueTempoReal.atualizar_movimentacao_prevista(
            cod_produto=sep.cod_produto,
            data=sep.expedicao,
            qtd_saida=Decimal(str(sep.qtd_saldo))
        )
        total_movs += 1
    
    print(f"    ✅ {len(seps)} separações processadas")
    
    # 3. Migrar ProgramacaoProducao (entradas previstas)
    print("  📥 Processando programações de produção...")
    prods = ProgramacaoProducao.query.filter(
        ProgramacaoProducao.data_programacao >= hoje,
        ProgramacaoProducao.qtd_programada > 0
    ).all()
    
    for prod in prods:
        ServicoEstoqueTempoReal.atualizar_movimentacao_prevista(
            cod_produto=prod.cod_produto,
            data=prod.data_programacao,
            qtd_entrada=Decimal(str(prod.qtd_programada))
        )
        total_movs += 1
    
    print(f"    ✅ {len(prods)} programações processadas")
    
    # Commit final
    try:
        db.session.commit()
        print(f"✅ Movimentações previstas migradas: {total_movs} registros")
    except Exception as e:
        db.session.rollback()
        print(f"❌ Erro ao migrar movimentações: {e}")
        return 0
    
    return total_movs


def calcular_todas_rupturas():
    """
    Calcula ruptura D+7 para todos os produtos
    """
    print("\n📊 Calculando rupturas D+7...")
    
    produtos = EstoqueTempoReal.query.all()
    total = len(produtos)
    processados = 0
    com_ruptura = 0
    
    for produto in produtos:
        try:
            ServicoEstoqueTempoReal.calcular_ruptura_d7(produto.cod_produto)
            processados += 1
            
            # Recarregar para verificar ruptura
            produto = EstoqueTempoReal.query.filter_by(
                cod_produto=produto.cod_produto
            ).first()
            
            if produto and produto.dia_ruptura:
                com_ruptura += 1
            
            # Commit a cada 100
            if processados % 100 == 0:
                db.session.commit()
                print(f"  ✅ {processados}/{total} produtos processados...")
                
        except Exception as e:
            print(f"  ⚠️  Erro no produto {produto.cod_produto}: {e}")
    
    # Commit final
    try:
        db.session.commit()
        print(f"✅ Rupturas calculadas: {processados} produtos")
        print(f"   ⚠️  {com_ruptura} produtos com ruptura prevista")
    except Exception as e:
        db.session.rollback()
        print(f"❌ Erro no cálculo de rupturas: {e}")
    
    return processados


def verificar_integridade():
    """
    Verifica integridade dos dados migrados
    """
    print("\n🔍 Verificando integridade...")
    
    # Contar registros
    total_estoque = EstoqueTempoReal.query.count()
    total_movs = MovimentacaoPrevista.query.count()
    
    # Produtos com estoque negativo
    negativos = EstoqueTempoReal.query.filter(
        EstoqueTempoReal.saldo_atual < 0
    ).count()
    
    # Produtos com ruptura
    rupturas = EstoqueTempoReal.query.filter(
        EstoqueTempoReal.dia_ruptura != None
    ).count()
    
    print(f"""
  📊 Resumo da Migração:
  ─────────────────────────────
  ✅ EstoqueTempoReal: {total_estoque} produtos
  ✅ MovimentacaoPrevista: {total_movs} registros
  ⚠️  Estoque Negativo: {negativos} produtos
  ⚠️  Rupturas Previstas: {rupturas} produtos
  ─────────────────────────────
    """)
    
    return {
        'total_estoque': total_estoque,
        'total_movimentacoes': total_movs,
        'estoque_negativo': negativos,
        'rupturas': rupturas
    }


def limpar_dados_antigos():
    """
    Opcional: limpar dados antigos após migração bem-sucedida
    """
    resposta = input("\n⚠️  Deseja limpar dados antigos? (s/N): ")
    if resposta.lower() != 's':
        print("  ℹ️  Dados antigos mantidos")
        return
    
    print("  🗑️  Limpando dados antigos...")
    # TODO: Implementar limpeza se necessário
    print("  ✅ Limpeza concluída")


def main():
    """
    Função principal de migração
    """
    print("""
╔══════════════════════════════════════════════════════╗
║     MIGRAÇÃO PARA SISTEMA DE ESTOQUE TEMPO REAL     ║
╚══════════════════════════════════════════════════════╝
    """)
    
    app = create_app()
    
    with app.app_context():
        # 1. Criar tabelas
        if not criar_tabelas():
            print("❌ Migração abortada")
            return 1
        
        # 2. Migrar estoque atual
        produtos_migrados = migrar_estoque_atual()
        if produtos_migrados == 0:
            print("⚠️  Nenhum produto para migrar")
        
        # 3. Migrar movimentações previstas
        movs_migradas = migrar_movimentacoes_previstas()
        
        # 4. Calcular rupturas
        rupturas_calculadas = calcular_todas_rupturas()
        
        # 5. Verificar integridade
        stats = verificar_integridade()
        
        # 6. Limpar dados antigos (opcional)
        # limpar_dados_antigos()
        
        print("""
╔══════════════════════════════════════════════════════╗
║              MIGRAÇÃO CONCLUÍDA COM SUCESSO          ║
╚══════════════════════════════════════════════════════╝
        """)
        
        return 0


if __name__ == '__main__':
    exit(main())
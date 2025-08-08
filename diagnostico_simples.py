#!/usr/bin/env python3
"""
Script de diagnóstico simplificado para verificar o sistema de triggers.
Identifica problemas e sugere soluções.

Uso:
    python diagnostico_simples.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from sqlalchemy import inspect, text
from datetime import date
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def verificar_tabelas():
    """Verifica se as tabelas necessárias existem"""
    print("\n" + "="*60)
    print("1. VERIFICAÇÃO DE TABELAS")
    print("="*60)
    
    inspector = inspect(db.engine)
    tabelas_necessarias = {
        'estoque_tempo_real': 'Sistema de estoque em tempo real',
        'movimentacao_prevista': 'Movimentações futuras previstas',
        'movimentacao_estoque': 'Histórico de movimentações',
        'pre_separacao_item': 'Itens de pré-separação',
        'separacao': 'Separações efetivadas',
        'programacao_producao': 'Programação de produção'
    }
    
    status = {}
    for tabela, descricao in tabelas_necessarias.items():
        existe = inspector.has_table(tabela)
        status[tabela] = existe
        
        if existe:
            try:
                count = db.session.execute(
                    text(f"SELECT COUNT(*) FROM {tabela}")
                ).scalar()
                print(f"  ✅ {tabela}: {count} registros ({descricao})")
            except:
                print(f"  ⚠️  {tabela}: Existe mas não pode ser lida")
        else:
            print(f"  ❌ {tabela}: NÃO EXISTE ({descricao})")
    
    return all(status.values())


def testar_triggers():
    """Testa se os triggers estão funcionando"""
    print("\n" + "="*60)
    print("2. TESTE DE TRIGGERS")
    print("="*60)
    
    from app.estoque.models import MovimentacaoEstoque
    
    # Código de produto único para teste
    cod_teste = f'TEST_DIAG_{date.today().strftime("%Y%m%d_%H%M%S")}'
    
    try:
        print(f"\nTestando com produto: {cod_teste}")
        
        # 1. Criar movimentação
        print("  → Criando movimentação de entrada...")
        mov = MovimentacaoEstoque(
            cod_produto=cod_teste,
            nome_produto='Produto Teste Diagnóstico',
            data_movimentacao=date.today(),
            tipo_movimentacao='ENTRADA',
            local_movimentacao='TESTE',
            qtd_movimentacao=100,
            ativo=True
        )
        db.session.add(mov)
        db.session.commit()
        print("  ✅ Movimentação criada")
        
        # 2. Verificar EstoqueTempoReal
        print("  → Verificando EstoqueTempoReal...")
        result = db.session.execute(
            text("SELECT saldo_atual FROM estoque_tempo_real WHERE cod_produto = :cod"),
            {'cod': cod_teste}
        ).scalar()
        
        if result:
            if float(result) == 100:
                print(f"  ✅ EstoqueTempoReal atualizado corretamente: {result}")
                triggers_ok = True
            else:
                print(f"  ⚠️  EstoqueTempoReal com valor incorreto: {result} (esperado 100)")
                triggers_ok = False
        else:
            print("  ❌ EstoqueTempoReal NÃO foi atualizado")
            triggers_ok = False
        
        # 3. Limpar teste
        print("  → Limpando dados de teste...")
        db.session.execute(
            text("DELETE FROM movimentacao_estoque WHERE cod_produto = :cod"),
            {'cod': cod_teste}
        )
        db.session.execute(
            text("DELETE FROM estoque_tempo_real WHERE cod_produto = :cod"),
            {'cod': cod_teste}
        )
        db.session.commit()
        print("  ✅ Dados de teste removidos")
        
        return triggers_ok
        
    except Exception as e:
        print(f"  ❌ ERRO no teste: {e}")
        try:
            db.session.rollback()
            # Tentar limpar mesmo com erro
            db.session.execute(
                text("DELETE FROM movimentacao_estoque WHERE cod_produto LIKE 'TEST_DIAG_%'")
            )
            db.session.execute(
                text("DELETE FROM estoque_tempo_real WHERE cod_produto LIKE 'TEST_DIAG_%'")
            )
            db.session.commit()
        except:
            pass
        return False


def verificar_dados_recentes():
    """Verifica dados recentes para identificar problemas"""
    print("\n" + "="*60)
    print("3. ANÁLISE DE DADOS RECENTES")
    print("="*60)
    
    # Movimentações recentes
    try:
        result = db.session.execute(
            text("""
                SELECT tipo_movimentacao, COUNT(*) as qtd
                FROM movimentacao_estoque
                WHERE data_movimentacao >= CURRENT_DATE - INTERVAL '7 days'
                GROUP BY tipo_movimentacao
            """)
        ).fetchall()
        
        print("\nMovimentações últimos 7 dias:")
        for row in result:
            print(f"  • {row[0]}: {row[1]} registros")
    except Exception as e:
        print(f"  ❌ Erro ao verificar movimentações: {e}")
    
    # Pré-separações recentes
    try:
        result = db.session.execute(
            text("""
                SELECT COUNT(*) 
                FROM pre_separacao_item
                WHERE data_criacao >= CURRENT_DATE - INTERVAL '1 day'
            """)
        ).scalar()
        
        print(f"\nPré-separações último dia: {result or 0}")
    except Exception as e:
        print(f"  ❌ Erro ao verificar pré-separações: {e}")
    
    # Separações recentes
    try:
        result = db.session.execute(
            text("""
                SELECT COUNT(*) 
                FROM separacao
                WHERE criado_em >= CURRENT_DATE - INTERVAL '1 day'
            """)
        ).scalar()
        
        print(f"Separações último dia: {result or 0}")
    except Exception as e:
        print(f"  ❌ Erro ao verificar separações: {e}")
    
    return True


def sugerir_solucao(tabelas_ok, triggers_ok):
    """Sugere soluções baseadas no diagnóstico"""
    print("\n" + "="*60)
    print("DIAGNÓSTICO E SOLUÇÕES")
    print("="*60)
    
    if not tabelas_ok:
        print("\n❌ PROBLEMA: Tabelas de tempo real não existem")
        print("\n📋 SOLUÇÃO:")
        print("  1. Execute: python init_estoque_tempo_real.py")
        print("  2. Depois execute novamente este diagnóstico")
        return False
    
    if not triggers_ok:
        print("\n❌ PROBLEMA: Triggers não estão funcionando corretamente")
        print("\n📋 SOLUÇÃO:")
        print("  1. Execute: python corrigir_session_triggers.py")
        print("  2. Responda 's' quando solicitado")
        print("  3. Reinicie a aplicação após a correção")
        return False
    
    print("\n✅ SISTEMA FUNCIONANDO CORRETAMENTE!")
    print("\nTudo está configurado e operacional:")
    print("  • Tabelas de tempo real existem")
    print("  • Triggers estão atualizando corretamente")
    print("  • Dados estão sendo sincronizados")
    
    return True


def main():
    """Função principal de diagnóstico"""
    print("\n" + "="*70)
    print("DIAGNÓSTICO DO SISTEMA DE ESTOQUE EM TEMPO REAL")
    print("="*70)
    
    app = create_app()
    
    with app.app_context():
        # 1. Verificar tabelas
        tabelas_ok = verificar_tabelas()
        
        if not tabelas_ok:
            # Se não tem tabelas, não adianta testar triggers
            sugerir_solucao(tabelas_ok, False)
            return False
        
        # 2. Testar triggers
        triggers_ok = testar_triggers()
        
        # 3. Verificar dados recentes
        verificar_dados_recentes()
        
        # 4. Sugerir solução
        sistema_ok = sugerir_solucao(tabelas_ok, triggers_ok)
        
        if sistema_ok:
            print("\n🎯 PRÓXIMOS PASSOS:")
            print("  1. Teste criar uma pré-separação")
            print("  2. Verifique se aparece no cardex")
            print("  3. Confirme que o estoque atualiza em tempo real")
        
        return sistema_ok


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
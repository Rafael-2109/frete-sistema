#!/usr/bin/env python3
"""
Script de correção definitiva para o problema de session nos triggers.
Implementa uma solução robusta que evita completamente problemas de flush.

Uso:
    python corrigir_session_triggers.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from sqlalchemy import event, text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def remover_todos_triggers():
    """Remove TODOS os triggers existentes para evitar conflitos"""
    print("\n[1/5] Removendo TODOS os triggers existentes...")
    
    from app.estoque.models import MovimentacaoEstoque
    from app.carteira.models import PreSeparacaoItem
    from app.separacao.models import Separacao
    from app.producao.models import ProgramacaoProducao
    from app.embarques.models import EmbarqueItem
    
    modelos = [
        MovimentacaoEstoque,
        PreSeparacaoItem,
        Separacao,
        ProgramacaoProducao,
        EmbarqueItem
    ]
    
    count = 0
    for modelo in modelos:
        for evt in ['after_insert', 'after_update', 'after_delete']:
            try:
                listeners = list(event.contains(modelo, evt))
                for listener in listeners:
                    event.remove(modelo, evt, listener)
                    count += 1
            except:
                pass
    
    print(f"✅ {count} triggers removidos")
    return True


def criar_triggers_seguros():
    """Cria triggers que usam APENAS SQL direto, sem tocar na session"""
    print("\n[2/5] Criando triggers seguros com SQL direto...")
    
    from app.estoque.models import MovimentacaoEstoque, UnificacaoCodigos
    from app.carteira.models import PreSeparacaoItem
    from app.separacao.models import Separacao
    from app.producao.models import ProgramacaoProducao
    
    # ============================================================================
    # HELPER: Executar SQL com segurança
    # ============================================================================
    def executar_sql_seguro(connection, sql, params=None):
        """Executa SQL diretamente na connection, sem usar session"""
        try:
            result = connection.execute(text(sql), params or {})
            return result
        except Exception as e:
            logger.error(f"Erro SQL: {e}")
            # Não fazer rollback aqui - deixar o processo pai decidir
            return None
    
    # ============================================================================
    # TRIGGER: MovimentacaoEstoque → EstoqueTempoReal
    # ============================================================================
    @event.listens_for(MovimentacaoEstoque, 'after_insert')
    def mov_estoque_insert_seguro(mapper, connection, target):
        if not target.ativo:
            return
        
        sql = """
        INSERT INTO estoque_tempo_real (cod_produto, nome_produto, saldo_atual, atualizado_em)
        VALUES (:cod, :nome, :qtd, NOW())
        ON CONFLICT (cod_produto) DO UPDATE SET
            saldo_atual = estoque_tempo_real.saldo_atual + :qtd,
            atualizado_em = NOW()
        """
        
        executar_sql_seguro(connection, sql, {
            'cod': target.cod_produto,
            'nome': target.nome_produto or f'Produto {target.cod_produto}',
            'qtd': float(target.qtd_movimentacao)
        })
    
    @event.listens_for(MovimentacaoEstoque, 'after_update')
    def mov_estoque_update_seguro(mapper, connection, target):
        if not target.ativo:
            return
        
        # Obter valor anterior de forma segura
        hist = db.inspect(target)
        if hist and hasattr(hist, 'attrs'):
            attr_hist = hist.attrs.qtd_movimentacao.history
            qtd_anterior = attr_hist.deleted[0] if attr_hist.deleted else target.qtd_movimentacao
        else:
            qtd_anterior = target.qtd_movimentacao
        
        delta = float(target.qtd_movimentacao) - float(qtd_anterior)
        
        if delta != 0:
            sql = """
            UPDATE estoque_tempo_real 
            SET saldo_atual = saldo_atual + :delta,
                atualizado_em = NOW()
            WHERE cod_produto = :cod
            """
            
            executar_sql_seguro(connection, sql, {
                'cod': target.cod_produto,
                'delta': delta
            })
    
    @event.listens_for(MovimentacaoEstoque, 'after_delete')
    def mov_estoque_delete_seguro(mapper, connection, target):
        sql = """
        UPDATE estoque_tempo_real 
        SET saldo_atual = saldo_atual - :qtd,
            atualizado_em = NOW()
        WHERE cod_produto = :cod
        """
        
        executar_sql_seguro(connection, sql, {
            'cod': target.cod_produto,
            'qtd': float(target.qtd_movimentacao)
        })
    
    # ============================================================================
    # TRIGGER: PreSeparacaoItem → MovimentacaoPrevista
    # ============================================================================
    @event.listens_for(PreSeparacaoItem, 'after_insert')
    def presep_insert_seguro(mapper, connection, target):
        if target.recomposto or not target.data_expedicao_editada:
            return
        
        # UPSERT direto sem tocar na session
        sql = """
        INSERT INTO movimentacao_prevista (cod_produto, data_prevista, entrada_prevista, saida_prevista)
        VALUES (:cod, :data, 0, :qtd)
        ON CONFLICT (cod_produto, data_prevista) DO UPDATE SET
            saida_prevista = movimentacao_prevista.saida_prevista + :qtd
        """
        
        executar_sql_seguro(connection, sql, {
            'cod': target.cod_produto,
            'data': target.data_expedicao_editada,
            'qtd': float(target.qtd_selecionada_usuario)
        })
    
    @event.listens_for(PreSeparacaoItem, 'after_update')
    def presep_update_seguro(mapper, connection, target):
        if target.recomposto:
            return
        
        # Verificar mudanças de forma segura
        hist = db.inspect(target)
        if not hist or not hasattr(hist, 'attrs'):
            return
        
        # Se mudou a data
        if hist.attrs.data_expedicao_editada.history.has_changes():
            # Reverter anterior
            if hist.attrs.data_expedicao_editada.history.deleted:
                data_anterior = hist.attrs.data_expedicao_editada.history.deleted[0]
                qtd_anterior = (
                    hist.attrs.qtd_selecionada_usuario.history.deleted[0]
                    if hist.attrs.qtd_selecionada_usuario.history.deleted
                    else target.qtd_selecionada_usuario
                )
                
                if data_anterior and qtd_anterior:
                    sql_reverter = """
                    UPDATE movimentacao_prevista 
                    SET saida_prevista = GREATEST(0, saida_prevista - :qtd)
                    WHERE cod_produto = :cod AND data_prevista = :data
                    """
                    
                    executar_sql_seguro(connection, sql_reverter, {
                        'cod': target.cod_produto,
                        'data': data_anterior,
                        'qtd': float(qtd_anterior)
                    })
            
            # Adicionar nova
            if target.data_expedicao_editada:
                sql_adicionar = """
                INSERT INTO movimentacao_prevista (cod_produto, data_prevista, entrada_prevista, saida_prevista)
                VALUES (:cod, :data, 0, :qtd)
                ON CONFLICT (cod_produto, data_prevista) DO UPDATE SET
                    saida_prevista = movimentacao_prevista.saida_prevista + :qtd
                """
                
                executar_sql_seguro(connection, sql_adicionar, {
                    'cod': target.cod_produto,
                    'data': target.data_expedicao_editada,
                    'qtd': float(target.qtd_selecionada_usuario)
                })
    
    @event.listens_for(PreSeparacaoItem, 'after_delete')
    def presep_delete_seguro(mapper, connection, target):
        if target.recomposto or not target.data_expedicao_editada:
            return
        
        sql = """
        UPDATE movimentacao_prevista 
        SET saida_prevista = GREATEST(0, saida_prevista - :qtd)
        WHERE cod_produto = :cod AND data_prevista = :data
        """
        
        executar_sql_seguro(connection, sql, {
            'cod': target.cod_produto,
            'data': target.data_expedicao_editada,
            'qtd': float(target.qtd_selecionada_usuario)
        })
    
    # ============================================================================
    # TRIGGER: Separacao → MovimentacaoPrevista
    # ============================================================================
    @event.listens_for(Separacao, 'after_insert')
    def sep_insert_seguro(mapper, connection, target):
        if not target.expedicao or not target.qtd_saldo or target.qtd_saldo <= 0:
            return
        
        sql = """
        INSERT INTO movimentacao_prevista (cod_produto, data_prevista, entrada_prevista, saida_prevista)
        VALUES (:cod, :data, 0, :qtd)
        ON CONFLICT (cod_produto, data_prevista) DO UPDATE SET
            saida_prevista = movimentacao_prevista.saida_prevista + :qtd
        """
        
        executar_sql_seguro(connection, sql, {
            'cod': target.cod_produto,
            'data': target.expedicao,
            'qtd': float(target.qtd_saldo)
        })
    
    # ============================================================================
    # TRIGGER: ProgramacaoProducao → MovimentacaoPrevista
    # ============================================================================
    @event.listens_for(ProgramacaoProducao, 'after_insert')
    def prod_insert_seguro(mapper, connection, target):
        if not target.data_programacao or not target.qtd_programada or target.qtd_programada <= 0:
            return
        
        sql = """
        INSERT INTO movimentacao_prevista (cod_produto, data_prevista, entrada_prevista, saida_prevista)
        VALUES (:cod, :data, :qtd, 0)
        ON CONFLICT (cod_produto, data_prevista) DO UPDATE SET
            entrada_prevista = movimentacao_prevista.entrada_prevista + :qtd
        """
        
        executar_sql_seguro(connection, sql, {
            'cod': target.cod_produto,
            'data': target.data_programacao,
            'qtd': float(target.qtd_programada)
        })
    
    print("✅ Triggers seguros criados com sucesso")
    return True


def verificar_instalacao():
    """Verifica se a correção foi aplicada corretamente"""
    print("\n[3/5] Verificando instalação...")
    
    from sqlalchemy import inspect
    
    inspector = inspect(db.engine)
    
    # Verificar tabelas
    tabelas_ok = True
    for tabela in ['estoque_tempo_real', 'movimentacao_prevista']:
        if not inspector.has_table(tabela):
            print(f"❌ Tabela {tabela} não existe")
            tabelas_ok = False
    
    if tabelas_ok:
        print("✅ Todas as tabelas necessárias existem")
    
    return tabelas_ok


def sincronizar_dados_existentes():
    """Sincroniza dados existentes para as novas tabelas"""
    print("\n[4/5] Sincronizando dados existentes...")
    
    try:
        # Recalcular estoque_tempo_real baseado em movimentacao_estoque
        sql_recalculo = """
        INSERT INTO estoque_tempo_real (cod_produto, nome_produto, saldo_atual, atualizado_em)
        SELECT 
            cod_produto,
            MAX(nome_produto) as nome_produto,
            SUM(qtd_movimentacao) as saldo_atual,
            NOW() as atualizado_em
        FROM movimentacao_estoque
        WHERE ativo = true
        GROUP BY cod_produto
        ON CONFLICT (cod_produto) DO UPDATE SET
            saldo_atual = EXCLUDED.saldo_atual,
            atualizado_em = NOW()
        """
        
        result = db.session.execute(text(sql_recalculo))
        produtos_atualizados = result.rowcount
        
        # Sincronizar movimentacao_prevista de pre_separacao_item
        sql_presep = """
        INSERT INTO movimentacao_prevista (cod_produto, data_prevista, entrada_prevista, saida_prevista)
        SELECT 
            cod_produto,
            data_expedicao_editada,
            0 as entrada_prevista,
            SUM(qtd_selecionada_usuario) as saida_prevista
        FROM pre_separacao_item
        WHERE recomposto = false 
          AND data_expedicao_editada IS NOT NULL
        GROUP BY cod_produto, data_expedicao_editada
        ON CONFLICT (cod_produto, data_prevista) DO UPDATE SET
            saida_prevista = EXCLUDED.saida_prevista
        """
        
        result = db.session.execute(text(sql_presep))
        presep_sincronizadas = result.rowcount
        
        # Sincronizar movimentacao_prevista de separacao
        sql_sep = """
        INSERT INTO movimentacao_prevista (cod_produto, data_prevista, entrada_prevista, saida_prevista)
        SELECT 
            cod_produto,
            expedicao,
            0 as entrada_prevista,
            SUM(qtd_saldo) as saida_prevista
        FROM separacao
        WHERE expedicao IS NOT NULL 
          AND qtd_saldo > 0
        GROUP BY cod_produto, expedicao
        ON CONFLICT (cod_produto, data_prevista) DO UPDATE SET
            saida_prevista = movimentacao_prevista.saida_prevista + EXCLUDED.saida_prevista
        """
        
        result = db.session.execute(text(sql_sep))
        sep_sincronizadas = result.rowcount
        
        db.session.commit()
        
        print(f"✅ {produtos_atualizados} produtos atualizados em estoque_tempo_real")
        print(f"✅ {presep_sincronizadas} pré-separações sincronizadas")
        print(f"✅ {sep_sincronizadas} separações sincronizadas")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro na sincronização: {e}")
        db.session.rollback()
        return False


def testar_correcao():
    """Testa se a correção funcionou"""
    print("\n[5/5] Testando correção...")
    
    from app.estoque.models import MovimentacaoEstoque
    from datetime import date
    
    try:
        # Criar movimentação de teste
        mov = MovimentacaoEstoque(
            cod_produto='TEST_CORRECAO_001',
            nome_produto='Teste Correção',
            data_movimentacao=date.today(),
            tipo_movimentacao='ENTRADA',
            local_movimentacao='TESTE',
            qtd_movimentacao=999,
            ativo=True
        )
        
        db.session.add(mov)
        db.session.commit()
        
        # Verificar se atualizou estoque_tempo_real
        result = db.session.execute(
            text("SELECT saldo_atual FROM estoque_tempo_real WHERE cod_produto = :cod"),
            {'cod': 'TEST_CORRECAO_001'}
        ).scalar()
        
        if result and float(result) == 999:
            print("✅ Teste passou - triggers funcionando corretamente")
            
            # Limpar teste
            db.session.execute(
                text("DELETE FROM movimentacao_estoque WHERE cod_produto = :cod"),
                {'cod': 'TEST_CORRECAO_001'}
            )
            db.session.execute(
                text("DELETE FROM estoque_tempo_real WHERE cod_produto = :cod"),
                {'cod': 'TEST_CORRECAO_001'}
            )
            db.session.commit()
            
            return True
        else:
            print("❌ Teste falhou - triggers não atualizaram corretamente")
            return False
            
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        db.session.rollback()
        return False


def main():
    """Função principal de correção"""
    print("\n" + "="*70)
    print("CORREÇÃO DEFINITIVA DOS TRIGGERS")
    print("="*70)
    print("\nEsta correção irá:")
    print("1. Remover TODOS os triggers existentes")
    print("2. Criar triggers seguros que usam SQL direto")
    print("3. Sincronizar dados existentes")
    print("4. Testar o funcionamento")
    
    resposta = input("\nDeseja continuar? (s/n): ")
    if resposta.lower() != 's':
        print("Operação cancelada")
        return False
    
    app = create_app()
    
    with app.app_context():
        # 1. Remover triggers antigos
        remover_todos_triggers()
        
        # 2. Criar triggers seguros
        criar_triggers_seguros()
        
        # 3. Verificar instalação
        if not verificar_instalacao():
            print("\n❌ Instalação incompleta. Execute init_estoque_tempo_real.py primeiro")
            return False
        
        # 4. Sincronizar dados
        sincronizar_dados_existentes()
        
        # 5. Testar
        if testar_correcao():
            print("\n" + "="*70)
            print("✅ CORREÇÃO APLICADA COM SUCESSO!")
            print("="*70)
            print("\nO sistema agora está usando triggers seguros que:")
            print("• Usam SQL direto (sem tocar na session)")
            print("• Evitam problemas de flush")
            print("• Atualizam dados em tempo real")
            print("\nPróximos passos:")
            print("1. Reinicie a aplicação")
            print("2. Teste criar uma pré-separação")
            print("3. Verifique se os dados aparecem no cardex")
            
            return True
        else:
            print("\n❌ Correção aplicada mas teste falhou")
            print("Verifique os logs para mais detalhes")
            return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
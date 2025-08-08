#!/usr/bin/env python3
"""
Script de diagnóstico para identificar e corrigir problemas dos triggers.
Identifica a causa dos erros de session e aplica correções.

Uso:
    python diagnostico_triggers_sql.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from sqlalchemy import inspect, text, event
from datetime import date, datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DiagnosticoTriggers:
    """Diagnóstico e correção dos problemas de triggers"""
    
    @staticmethod
    def verificar_triggers_ativos():
        """Verifica quais triggers estão ativos no sistema"""
        print("\n" + "="*60)
        print("VERIFICAÇÃO DE TRIGGERS ATIVOS")
        print("="*60)
        
        # Verificar listeners SQLAlchemy registrados
        from app.estoque.models import MovimentacaoEstoque
        from app.carteira.models import PreSeparacaoItem
        from app.separacao.models import Separacao
        
        modelos = {
            'MovimentacaoEstoque': MovimentacaoEstoque,
            'PreSeparacaoItem': PreSeparacaoItem,
            'Separacao': Separacao
        }
        
        for nome, modelo in modelos.items():
            print(f"\n{nome}:")
            for evt in ['after_insert', 'after_update', 'after_delete']:
                # Forma correta de verificar listeners
                try:
                    # Obter o evento específico
                    evt_obj = getattr(event.Events, evt, None)
                    if evt_obj:
                        # Verificar se há listeners para este evento
                        has_listeners = bool(evt_obj.listeners_for(modelo, propagate=False))
                        if has_listeners:
                            print(f"  ✅ {evt}: Tem listeners")
                        else:
                            print(f"  ❌ {evt}: Sem listeners")
                    else:
                        print(f"  ⚠️  {evt}: Evento não encontrado")
                except Exception as e:
                    # Método alternativo - verificar diretamente
                    print(f"  ⚠️  {evt}: Não foi possível verificar ({str(e)[:30]}...)")
        
        return True
    
    @staticmethod
    def verificar_tabelas_tempo_real():
        """Verifica se as tabelas de tempo real existem"""
        print("\n" + "="*60)
        print("VERIFICAÇÃO DE TABELAS DE TEMPO REAL")
        print("="*60)
        
        inspector = inspect(db.engine)
        tabelas_necessarias = [
            'estoque_tempo_real',
            'movimentacao_prevista'
        ]
        
        todas_existem = True
        for tabela in tabelas_necessarias:
            if inspector.has_table(tabela):
                # Verificar número de registros
                result = db.session.execute(
                    text(f"SELECT COUNT(*) FROM {tabela}")
                ).scalar()
                print(f"✅ {tabela}: {result} registros")
            else:
                print(f"❌ {tabela}: NÃO EXISTE")
                todas_existem = False
        
        return todas_existem
    
    @staticmethod
    def verificar_problema_session():
        """Identifica problemas de session nos triggers"""
        print("\n" + "="*60)
        print("DIAGNÓSTICO DO PROBLEMA DE SESSION")
        print("="*60)
        
        problemas = []
        
        # Verificar se há triggers usando db.session durante flush
        print("\nVerificando código dos triggers para problemas conhecidos...")
        
        # Verificar se triggers_tempo_real.py está sendo usado
        try:
            from app.estoque import triggers_tempo_real
            print("⚠️  triggers_tempo_real.py está importado - pode causar problemas de flush")
            problemas.append("triggers_tempo_real usando db.session durante flush")
        except ImportError:
            print("✅ triggers_tempo_real.py não está sendo usado")
        
        # Verificar se triggers_sql_otimizado.py está ativo
        try:
            from app.estoque import triggers_sql_otimizado
            print("✅ triggers_sql_otimizado.py está importado - usa SQL direto")
        except ImportError:
            print("⚠️  triggers_sql_otimizado.py NÃO está sendo usado")
            problemas.append("triggers_sql_otimizado não está ativo")
        
        if problemas:
            print(f"\n❌ {len(problemas)} problema(s) encontrado(s):")
            for p in problemas:
                print(f"   - {p}")
        else:
            print("\n✅ Nenhum problema óbvio de session detectado")
        
        return problemas
    
    @staticmethod
    def testar_operacao_simples():
        """Testa uma operação simples para reproduzir o erro"""
        print("\n" + "="*60)
        print("TESTE DE OPERAÇÃO SIMPLES")
        print("="*60)
        
        try:
            from app.estoque.models import MovimentacaoEstoque
            
            # Criar movimentação de teste
            print("Criando movimentação de teste...")
            mov = MovimentacaoEstoque(
                cod_produto='TEST_DIAG_001',
                nome_produto='Produto Diagnóstico',
                data_movimentacao=date.today(),
                tipo_movimentacao='ENTRADA',
                local_movimentacao='TESTE',
                qtd_movimentacao=100,
                ativo=True
            )
            
            db.session.add(mov)
            db.session.commit()
            print("✅ Movimentação criada com sucesso")
            
            # Verificar se EstoqueTempoReal foi atualizado
            result = db.session.execute(
                text("SELECT saldo_atual FROM estoque_tempo_real WHERE cod_produto = :cod"),
                {'cod': 'TEST_DIAG_001'}
            ).scalar()
            
            if result:
                print(f"✅ EstoqueTempoReal atualizado: saldo = {result}")
            else:
                print("❌ EstoqueTempoReal NÃO foi atualizado")
            
            # Limpar teste
            db.session.execute(
                text("DELETE FROM movimentacao_estoque WHERE cod_produto = :cod"),
                {'cod': 'TEST_DIAG_001'}
            )
            db.session.execute(
                text("DELETE FROM estoque_tempo_real WHERE cod_produto = :cod"),
                {'cod': 'TEST_DIAG_001'}
            )
            db.session.commit()
            
            return True
            
        except Exception as e:
            print(f"❌ ERRO no teste: {e}")
            db.session.rollback()
            return False
    
    @staticmethod
    def aplicar_correcao_emergencial():
        """Aplica correção emergencial para o problema de session"""
        print("\n" + "="*60)
        print("APLICANDO CORREÇÃO EMERGENCIAL")
        print("="*60)
        
        # Desregistrar todos os listeners problemáticos
        print("1. Removendo listeners problemáticos...")
        
        from app.estoque.models import MovimentacaoEstoque
        from app.carteira.models import PreSeparacaoItem
        from app.separacao.models import Separacao
        
        modelos = [MovimentacaoEstoque, PreSeparacaoItem, Separacao]
        
        for modelo in modelos:
            for evt in ['after_insert', 'after_update', 'after_delete']:
                try:
                    # Remover todos os listeners existentes
                    event.remove(modelo, evt)
                    print(f"  Removidos listeners de {modelo.__name__}.{evt}")
                except:
                    pass
        
        print("\n2. Registrando triggers SQL otimizados...")
        
        # Importar e registrar triggers otimizados
        try:
            from app.estoque.triggers_sql_otimizado import (
                ativar_triggers_otimizados,
                desativar_triggers_antigos
            )
            
            desativar_triggers_antigos()
            ativar_triggers_otimizados()
            print("✅ Triggers SQL otimizados ativados")
            
        except ImportError:
            print("❌ triggers_sql_otimizado.py não encontrado")
            print("   Execute: python ativar_triggers_otimizados.py")
        
        return True
    
    @staticmethod
    def verificar_dados_faltantes():
        """Verifica dados que não estão sendo mostrados"""
        print("\n" + "="*60)
        print("VERIFICAÇÃO DE DADOS FALTANTES")
        print("="*60)
        
        # 1. Verificar saídas no cardex
        print("\n1. Saídas no cardex:")
        result = db.session.execute(
            text("""
                SELECT COUNT(*) 
                FROM movimentacao_estoque 
                WHERE tipo_movimentacao = 'SAIDA' 
                  AND data_movimentacao >= CURRENT_DATE - INTERVAL '7 days'
            """)
        ).scalar()
        print(f"   Saídas últimos 7 dias: {result}")
        
        # 2. Verificar programação de produção
        print("\n2. Programação de produção:")
        inspector = inspect(db.engine)
        if inspector.has_table('programacao_producao'):
            result = db.session.execute(
                text("""
                    SELECT COUNT(*) 
                    FROM programacao_producao 
                    WHERE data_programacao >= CURRENT_DATE
                """)
            ).scalar()
            print(f"   Programações futuras: {result}")
        else:
            print("   ❌ Tabela programacao_producao não existe")
        
        # 3. Verificar separações refletindo no estoque
        print("\n3. Separações no estoque:")
        result = db.session.execute(
            text("""
                SELECT COUNT(DISTINCT s.cod_produto)
                FROM separacao s
                LEFT JOIN movimentacao_prevista mp 
                  ON mp.cod_produto = s.cod_produto 
                  AND mp.data_prevista = s.expedicao
                WHERE s.criado_em >= CURRENT_DATE - INTERVAL '1 day'
                  AND mp.id IS NULL
            """)
        ).scalar()
        
        if result > 0:
            print(f"   ❌ {result} separações não refletidas em movimentacao_prevista")
        else:
            print("   ✅ Todas separações refletidas")
        
        return True


def main():
    """Função principal de diagnóstico"""
    print("\n" + "="*70)
    print("DIAGNÓSTICO COMPLETO DO SISTEMA DE TRIGGERS")
    print("="*70)
    
    app = create_app()
    
    with app.app_context():
        diagnostico = DiagnosticoTriggers()
        
        # 1. Verificar triggers ativos
        diagnostico.verificar_triggers_ativos()
        
        # 2. Verificar tabelas
        tabelas_ok = diagnostico.verificar_tabelas_tempo_real()
        
        if not tabelas_ok:
            print("\n⚠️  ATENÇÃO: Execute primeiro init_estoque_tempo_real.py")
            return False
        
        # 3. Diagnosticar problema de session
        problemas = diagnostico.verificar_problema_session()
        
        # 4. Testar operação
        teste_ok = diagnostico.testar_operacao_simples()
        
        # 5. Verificar dados faltantes
        diagnostico.verificar_dados_faltantes()
        
        # 6. Aplicar correção se necessário
        if problemas or not teste_ok:
            print("\n⚠️  PROBLEMAS DETECTADOS - Aplicando correção...")
            diagnostico.aplicar_correcao_emergencial()
            
            # Testar novamente
            print("\nTestando após correção...")
            teste_ok = diagnostico.testar_operacao_simples()
            
            if teste_ok:
                print("\n✅ CORREÇÃO APLICADA COM SUCESSO!")
                print("\nPróximos passos:")
                print("1. Reinicie a aplicação")
                print("2. Execute: python processar_movimentacoes_existentes.py")
                print("3. Teste criar uma pré-separação")
            else:
                print("\n❌ Correção não resolveu completamente")
                print("Verifique os logs para mais detalhes")
        else:
            print("\n✅ Sistema aparentemente funcionando corretamente")
        
        return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
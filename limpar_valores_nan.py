#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para Limpar Valores "nan" das Tabelas
===========================================

Este script remove todos os valores "nan" (string) das tabelas do banco,
convertendo-os para None (NULL) que é o valor correto para campos vazios.
"""

import sys
from app import create_app, db
from sqlalchemy import text, inspect
import pandas as pd

def limpar_valores_nan():
    """Remove valores 'nan' de todas as tabelas"""
    
    app = create_app()
    
    with app.app_context():
        print("🧹 === LIMPEZA DE VALORES 'nan' ===")
        
        # Lista das principais tabelas que podem ter valores nan
        tabelas_para_limpar = [
            ('tabelas_frete', [
                'valor_kg', 'frete_minimo_peso', 'percentual_valor', 'frete_minimo_valor',
                'percentual_gris', 'percentual_adv', 'percentual_rca', 'pedagio_por_100kg',
                'valor_despacho', 'valor_cte', 'valor_tas', 'criado_por'
            ]),
            ('cidades_atendidas', [
                'lead_time'
            ]),
            ('cidades', [
                'microrregiao', 'mesorregiao'
            ]),
            ('transportadoras', [
                'condicao_pgto'
            ]),
            ('pedidos', [
                'observacao', 'info_complementar', 'vendedor_responsavel'
            ]),
            ('fretes', [
                'observacoes', 'numero_cte', 'valor_cte'
            ])
        ]
        
        total_alteracoes = 0
        
        for tabela, colunas in tabelas_para_limpar:
            print(f"\n🔍 Verificando tabela: {tabela}")
            
            try:
                # Verifica se a tabela existe
                result = db.session.execute(text(f"SELECT COUNT(*) FROM information_schema.tables WHERE table_name = '{tabela}'"))
                if result.scalar() == 0:
                    print(f"⚠️ Tabela {tabela} não encontrada. Pulando...")
                    continue
                
                alteracoes_tabela = 0
                
                for coluna in colunas:
                    try:
                        # Verifica se a coluna existe
                        result = db.session.execute(text(f"SELECT COUNT(*) FROM information_schema.columns WHERE table_name = '{tabela}' AND column_name = '{coluna}'"))
                        if result.scalar() == 0:
                            print(f"   ⚠️ Coluna {coluna} não encontrada. Pulando...")
                            continue
                        
                        # Conta valores 'nan' atuais
                        count_result = db.session.execute(text(f"SELECT COUNT(*) FROM {tabela} WHERE {coluna} = 'nan'"))
                        count_nan = count_result.scalar()
                        
                        if count_nan > 0:
                            print(f"   🧹 Coluna {coluna}: {count_nan} valores 'nan' encontrados")
                            
                            # Limpa valores 'nan' -> NULL
                            db.session.execute(text(f"UPDATE {tabela} SET {coluna} = NULL WHERE {coluna} = 'nan'"))
                            alteracoes_tabela += count_nan
                            
                        # Também limpa outros valores problemáticos
                        outros_valores = ['NaN', 'None', 'null', 'NULL']
                        for valor in outros_valores:
                            count_result = db.session.execute(text(f"SELECT COUNT(*) FROM {tabela} WHERE {coluna} = '{valor}'"))
                            count_valor = count_result.scalar()
                            
                            if count_valor > 0:
                                print(f"   🧹 Coluna {coluna}: {count_valor} valores '{valor}' encontrados")
                                db.session.execute(text(f"UPDATE {tabela} SET {coluna} = NULL WHERE {coluna} = '{valor}'"))
                                alteracoes_tabela += count_valor
                        
                    except Exception as e:
                        print(f"   ❌ Erro na coluna {coluna}: {e}")
                        continue
                
                if alteracoes_tabela > 0:
                    print(f"   ✅ {alteracoes_tabela} valores limpos na tabela {tabela}")
                    total_alteracoes += alteracoes_tabela
                else:
                    print(f"   ✅ Tabela {tabela} já está limpa!")
                
            except Exception as e:
                print(f"❌ Erro na tabela {tabela}: {e}")
                continue
        
        # Limpeza específica para campos numéricos que podem ter 'nan'
        print(f"\n🔢 Limpeza específica de campos numéricos...")
        
        try:
            # Campos float/decimal em tabelas_frete
            campos_numericos = [
                'valor_kg', 'frete_minimo_peso', 'percentual_valor', 'frete_minimo_valor',
                'percentual_gris', 'percentual_adv', 'percentual_rca', 'pedagio_por_100kg',
                'valor_despacho', 'valor_cte', 'valor_tas'
            ]
            
            for campo in campos_numericos:
                try:
                    # Converte valores 'nan' e strings vazias para 0.0 em campos numéricos
                    count_result = db.session.execute(text(f"SELECT COUNT(*) FROM tabelas_frete WHERE {campo} = 'nan' OR {campo} = ''"))
                    count_nan = count_result.scalar()
                    
                    if count_nan > 0:
                        print(f"   🔢 Campo numérico {campo}: {count_nan} valores inválidos -> 0.0")
                        db.session.execute(text(f"UPDATE tabelas_frete SET {campo} = 0.0 WHERE {campo} = 'nan' OR {campo} = ''"))
                        total_alteracoes += count_nan
                        
                except Exception as e:
                    print(f"   ⚠️ Erro no campo numérico {campo}: {e}")
                    continue
                    
        except Exception as e:
            print(f"❌ Erro na limpeza de campos numéricos: {e}")
        
        # Commit das alterações
        try:
            db.session.commit()
            print(f"\n✅ Limpeza concluída com sucesso!")
            print(f"📊 Total de valores corrigidos: {total_alteracoes}")
            
            if total_alteracoes > 0:
                print(f"\n🎯 RESULTADO:")
                print(f"   • {total_alteracoes} valores 'nan' foram limpos")
                print(f"   • Valores de texto: convertidos para NULL")
                print(f"   • Valores numéricos: convertidos para 0.0")
                print(f"   • Banco de dados limpo e normalizado!")
            else:
                print(f"\n✅ Banco de dados já estava limpo!")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Erro ao salvar alterações: {e}")

def verificar_valores_nan():
    """Apenas verifica quantos valores 'nan' existem sem alterar"""
    
    app = create_app()
    
    with app.app_context():
        print("🔍 === VERIFICAÇÃO DE VALORES 'nan' ===")
        
        # Busca em todas as tabelas
        inspector = inspect(db.engine)
        tabelas = inspector.get_table_names()
        
        total_nan = 0
        
        for tabela in tabelas:
            try:
                colunas = inspector.get_columns(tabela)
                nan_tabela = 0
                
                for coluna in colunas:
                    nome_coluna = coluna['name']
                    
                    try:
                        count_result = db.session.execute(text(f"SELECT COUNT(*) FROM {tabela} WHERE {nome_coluna} = 'nan'"))
                        count_nan = count_result.scalar()
                        
                        if count_nan > 0:
                            print(f"   📊 {tabela}.{nome_coluna}: {count_nan} valores 'nan'")
                            nan_tabela += count_nan
                            
                    except Exception:
                        continue  # Ignora erros de coluna
                
                if nan_tabela > 0:
                    print(f"🔍 Tabela {tabela}: {nan_tabela} valores 'nan' total")
                    total_nan += nan_tabela
                    
            except Exception as e:
                continue  # Ignora erros de tabela
        
        print(f"\n📊 RESUMO GERAL:")
        print(f"   Total de valores 'nan' encontrados: {total_nan}")
        
        return total_nan > 0

if __name__ == "__main__":
    print("🧹 Limpador de Valores 'nan'")
    print("=" * 50)
    
    if len(sys.argv) > 1 and sys.argv[1] == "--verificar":
        verificar_valores_nan()
    else:
        print("1. Executando verificação...")
        tem_nan = verificar_valores_nan()
        
        if tem_nan:
            print("\n2. Executando limpeza...")
            limpar_valores_nan()
        else:
            print("\n✅ Nenhum valor 'nan' encontrado!")
    
    print("\n🏁 Script concluído!") 
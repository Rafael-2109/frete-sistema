#!/usr/bin/env python3
import os
import sys
from app import create_app, db

def fix_cnpj_columns():
    """Corrige as colunas CNPJ no PostgreSQL - versão forçada"""
    
    app = create_app()
    
    with app.app_context():
        try:
            print("🔧 FORÇANDO correção das colunas CNPJ...")
            
            # Verificar se estamos no PostgreSQL
            engine_name = db.engine.dialect.name
            print(f"🔍 Banco detectado: {engine_name}")
            
            if engine_name != 'postgresql':
                print("⚠️ Este script é específico para PostgreSQL")
                return True
            
            # Lista de correções com verificação antes e depois
            correccoes = [
                {
                    'tabela': 'transportadoras',
                    'coluna': 'cnpj', 
                    'comando': "ALTER TABLE transportadoras ALTER COLUMN cnpj TYPE VARCHAR(20);"
                },
                {
                    'tabela': 'cotacao_itens',
                    'coluna': 'cnpj_cliente',
                    'comando': "ALTER TABLE cotacao_itens ALTER COLUMN cnpj_cliente TYPE VARCHAR(20);"
                },
                {
                    'tabela': 'embarque_volumes', 
                    'coluna': 'cnpj_cliente',
                    'comando': "ALTER TABLE embarque_volumes ALTER COLUMN cnpj_cliente TYPE VARCHAR(20);"
                }
            ]
            
            for correcao in correccoes:
                tabela = correcao['tabela']
                coluna = correcao['coluna']
                comando = correcao['comando']
                
                try:
                    print(f"\n📋 Verificando {tabela}.{coluna}...")
                    
                    # Verificar se a tabela existe
                    check_table = f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '{tabela}');"
                    resultado = db.session.execute(db.text(check_table)).fetchone()
                    
                    if not resultado[0]:
                        print(f"  ⚠️ Tabela {tabela} não existe - pulando")
                        continue
                    
                    # Verificar tamanho atual da coluna
                    check_size = f"""
                    SELECT character_maximum_length 
                    FROM information_schema.columns 
                    WHERE table_name = '{tabela}' AND column_name = '{coluna}';
                    """
                    
                    size_result = db.session.execute(db.text(check_size)).fetchone()
                    
                    if size_result:
                        tamanho_atual = size_result[0]
                        print(f"  📏 Tamanho atual: {tamanho_atual}")
                        
                        if tamanho_atual and tamanho_atual >= 20:
                            print(f"  ✅ Já está correto (>= 20)")
                            continue
                    
                    # Executar correção
                    print(f"  🔧 Executando: {comando}")
                    db.session.execute(db.text(comando))
                    db.session.commit()
                    
                    # Verificar se funcionou
                    size_result_after = db.session.execute(db.text(check_size)).fetchone()
                    if size_result_after:
                        novo_tamanho = size_result_after[0]
                        print(f"  ✅ Novo tamanho: {novo_tamanho}")
                    else:
                        print(f"  ❌ Falha na verificação")
                        
                except Exception as e:
                    print(f"  ❌ Erro em {tabela}.{coluna}: {str(e)}")
                    db.session.rollback()
                    continue
            
            print("\n🎉 Processo de correção concluído!")
            return True
            
        except Exception as e:
            print(f"\n❌ Erro geral: {str(e)}")
            db.session.rollback()
            return False

if __name__ == "__main__":
    success = fix_cnpj_columns()
    sys.exit(0 if success else 1) 
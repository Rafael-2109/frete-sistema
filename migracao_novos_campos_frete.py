"""
Migração para adicionar novos campos de controle de cálculo de frete
Data: 19/08/2025
Autor: Sistema

ATENÇÃO: Execute este script para adicionar os novos campos ao banco de dados
"""

import sys
import os

# Adiciona o diretório do projeto ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime
from flask import Flask
from sqlalchemy import text
from app import create_app, db

# Cria a aplicação Flask
app = create_app()

def adicionar_campos_transportadora():
    """
    Adiciona novos campos boolean na tabela transportadoras para controlar 
    quando aplicar valores após comparação com frete mínimo
    """
    queries = [
        # Campos que devem ser aplicados APÓS comparação com frete mínimo
        "ALTER TABLE transportadoras ADD COLUMN IF NOT EXISTS aplica_gris_pos_minimo BOOLEAN DEFAULT FALSE",
        "ALTER TABLE transportadoras ADD COLUMN IF NOT EXISTS aplica_adv_pos_minimo BOOLEAN DEFAULT FALSE",
        "ALTER TABLE transportadoras ADD COLUMN IF NOT EXISTS aplica_rca_pos_minimo BOOLEAN DEFAULT FALSE",
        "ALTER TABLE transportadoras ADD COLUMN IF NOT EXISTS aplica_pedagio_pos_minimo BOOLEAN DEFAULT FALSE",
        "ALTER TABLE transportadoras ADD COLUMN IF NOT EXISTS aplica_despacho_pos_minimo BOOLEAN DEFAULT FALSE",
        "ALTER TABLE transportadoras ADD COLUMN IF NOT EXISTS aplica_cte_pos_minimo BOOLEAN DEFAULT FALSE",
        "ALTER TABLE transportadoras ADD COLUMN IF NOT EXISTS aplica_tas_pos_minimo BOOLEAN DEFAULT FALSE",
        
        # Tipo de cálculo de pedágio
        "ALTER TABLE transportadoras ADD COLUMN IF NOT EXISTS pedagio_por_fracao BOOLEAN DEFAULT TRUE",  # TRUE = por fração (arredonda), FALSE = direto
    ]
    
    print("\n=== ADICIONANDO CAMPOS NA TABELA TRANSPORTADORAS ===")
    for query in queries:
        try:
            db.session.execute(text(query))
            print(f"✅ Executado: {query[:80]}...")
        except Exception as e:
            print(f"⚠️ Erro ou campo já existe: {str(e)[:100]}")
    
    db.session.commit()
    print("✅ Campos de controle adicionados em transportadoras")


def adicionar_campos_tabelas_frete():
    """
    Adiciona novos campos nas tabelas de frete para valores mínimos e ICMS próprio
    """
    # Lista de tabelas que precisam dos novos campos
    tabelas = [
        'tabelas_frete',
        'historico_tabelas_frete',
        'cotacoes',
        'cotacao_itens',
        'embarques',
        'embarque_itens',
        'fretes'
    ]
    
    print("\n=== ADICIONANDO CAMPOS NAS TABELAS DE FRETE ===")
    
    for tabela in tabelas:
        # Determina se precisa prefixo "tabela_" baseado no nome da tabela
        prefixo = 'tabela_' if tabela in ['embarques', 'embarque_itens', 'fretes'] else ''
        
        queries = [
            f"ALTER TABLE {tabela} ADD COLUMN IF NOT EXISTS {prefixo}gris_minimo FLOAT DEFAULT 0",
            f"ALTER TABLE {tabela} ADD COLUMN IF NOT EXISTS {prefixo}adv_minimo FLOAT DEFAULT 0",
            f"ALTER TABLE {tabela} ADD COLUMN IF NOT EXISTS {prefixo}icms_proprio FLOAT DEFAULT NULL",  # NULL significa usar ICMS da cidade
        ]
        
        print(f"\n📁 Tabela: {tabela}")
        for query in queries:
            try:
                db.session.execute(text(query))
                print(f"  ✅ Campo adicionado: {query.split('EXISTS ')[1].split(' ')[0]}")
            except Exception as e:
                print(f"  ⚠️ Erro ou campo já existe: {str(e)[:100]}")
    
    db.session.commit()
    print("\n✅ Campos gris_minimo, adv_minimo e icms_proprio adicionados em todas as tabelas")


def criar_tabela_configuracao_frete():
    """
    Cria tabela para armazenar configurações específicas de cálculo de frete por transportadora
    (Opcional - para futuras expansões)
    """
    query = """
    CREATE TABLE IF NOT EXISTS configuracao_frete_transportadora (
        id SERIAL PRIMARY KEY,
        transportadora_id INTEGER NOT NULL REFERENCES transportadoras(id),
        
        -- Flags de aplicação pós-mínimo
        aplica_gris_pos_minimo BOOLEAN DEFAULT FALSE,
        aplica_adv_pos_minimo BOOLEAN DEFAULT FALSE,
        aplica_rca_pos_minimo BOOLEAN DEFAULT FALSE,
        aplica_pedagio_pos_minimo BOOLEAN DEFAULT FALSE,
        aplica_despacho_pos_minimo BOOLEAN DEFAULT FALSE,
        aplica_cte_pos_minimo BOOLEAN DEFAULT FALSE,
        aplica_tas_pos_minimo BOOLEAN DEFAULT FALSE,
        
        -- Tipo de cálculo
        pedagio_por_fracao BOOLEAN DEFAULT TRUE,
        
        -- Valores mínimos globais (podem sobrescrever tabela)
        gris_minimo_global FLOAT DEFAULT NULL,
        adv_minimo_global FLOAT DEFAULT NULL,
        
        -- Controle
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        criado_por VARCHAR(100),
        
        UNIQUE(transportadora_id)
    )
    """
    
    print("\n=== CRIANDO TABELA DE CONFIGURAÇÃO (OPCIONAL) ===")
    try:
        db.session.execute(text(query))
        db.session.commit()
        print("✅ Tabela configuracao_frete_transportadora criada")
    except Exception as e:
        print(f"⚠️ Tabela já existe ou erro: {str(e)[:100]}")


def atualizar_tabela_frete_manager():
    """
    Mostra as alterações necessárias no TabelaFreteManager
    """
    print("\n=== ATUALIZAÇÕES NECESSÁRIAS NO CÓDIGO ===")
    print("""
📝 TabelaFreteManager (app/utils/tabela_frete_manager.py):
   - Adicionar 'gris_minimo', 'adv_minimo', 'icms_proprio' na lista CAMPOS
   
📝 Modelos (models.py de cada módulo):
   - Adicionar os novos campos em cada modelo
   
📝 CalculadoraFrete (app/utils/calculadora_frete.py):
   - Implementar lógica de aplicação pós-frete mínimo
   - Implementar comparação com valores mínimos
   - Implementar ICMS próprio da tabela
   
📝 FreteSimulador (app/utils/frete_simulador.py):
   - Replicar mesma lógica da CalculadoraFrete
   
📝 Interface (templates/transportadoras/):
   - Adicionar campos de configuração na tela de transportadoras
    """)


def main():
    """
    Executa todas as migrações
    """
    print("=" * 60)
    print("MIGRAÇÃO DE NOVOS CAMPOS DE CÁLCULO DE FRETE")
    print("=" * 60)
    
    with app.app_context():
        try:
            # 1. Adiciona campos na tabela transportadoras
            adicionar_campos_transportadora()
            
            # 2. Adiciona campos nas tabelas de frete
            adicionar_campos_tabelas_frete()
            
            # 3. Cria tabela de configuração (opcional)
            criar_tabela_configuracao_frete()
            
            # 4. Mostra instruções de atualização do código
            atualizar_tabela_frete_manager()
            
            print("\n" + "=" * 60)
            print("✅ MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
            print("=" * 60)
            print("\n⚠️ PRÓXIMOS PASSOS:")
            print("1. Execute este script: python migracao_novos_campos_frete.py")
            print("2. Atualize os arquivos de modelo conforme indicado")
            print("3. Atualize a lógica de cálculo")
            print("4. Teste as alterações")
            
        except Exception as e:
            print(f"\n❌ ERRO NA MIGRAÇÃO: {str(e)}")
            db.session.rollback()
            raise


if __name__ == "__main__":
    main()
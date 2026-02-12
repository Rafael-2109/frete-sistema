"""
Script de Migração - Campos de Controle de Pagamento
Sistema MotoCHEFE

Adiciona campos para controle de:
1. Pagamento de custo de aquisição de motos (tabela moto)
2. Pagamento de montagem (tabela pedido_venda_moto_item)

Uso:
    python app/motochefe/scripts/adicionar_campos_pagamento.py

IMPORTANTE:
- Execute a partir da raiz do projeto
- Certifique-se de que o app Flask está configurado
- Os models Python já possuem estes campos definidos
- Este script sincroniza o banco de dados PostgreSQL

Referência: app/motochefe/scripts/add_campos_pagamento.sql
"""

import sys
import os

# Adicionar path do projeto
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from app import create_app, db
from sqlalchemy import text, inspect
from datetime import datetime
from app.utils.timezone import agora_utc_naive


def verificar_coluna_existe(tabela, coluna):
    """Verifica se coluna existe na tabela"""
    inspector = inspect(db.engine)
    colunas = [c['name'] for c in inspector.get_columns(tabela)]
    return coluna in colunas


def verificar_indice_existe(tabela, nome_indice):
    """Verifica se índice existe na tabela"""
    inspector = inspect(db.engine)
    indices = [idx['name'] for idx in inspector.get_indexes(tabela)]
    return nome_indice in indices


def adicionar_campos_pagamento_moto():
    """
    Adiciona campos de controle de pagamento na tabela moto
    - custo_pago: Valor efetivamente pago ao fornecedor
    - data_pagamento_custo: Data do pagamento
    - status_pagamento_custo: PENDENTE, PAGO, PARCIAL
    """
    print("\n🔍 Verificando tabela MOTO - Campos de Pagamento de Custo...")

    if not verificar_coluna_existe('moto', 'custo_pago'):
        print("   ⏳ Adicionando campo custo_pago...")
        sql = text("ALTER TABLE moto ADD COLUMN custo_pago NUMERIC(15, 2);")
        db.session.execute(sql)
        db.session.commit()
        print("   ✅ Campo custo_pago adicionado!")
    else:
        print("   ✅ Campo custo_pago já existe")

    if not verificar_coluna_existe('moto', 'data_pagamento_custo'):
        print("   ⏳ Adicionando campo data_pagamento_custo...")
        sql = text("ALTER TABLE moto ADD COLUMN data_pagamento_custo DATE;")
        db.session.execute(sql)
        db.session.commit()
        print("   ✅ Campo data_pagamento_custo adicionado!")
    else:
        print("   ✅ Campo data_pagamento_custo já existe")

    if not verificar_coluna_existe('moto', 'status_pagamento_custo'):
        print("   ⏳ Adicionando campo status_pagamento_custo...")
        sql = text("""
            ALTER TABLE moto
            ADD COLUMN status_pagamento_custo VARCHAR(20) DEFAULT 'PENDENTE' NOT NULL;
        """)
        db.session.execute(sql)
        db.session.commit()
        print("   ✅ Campo status_pagamento_custo adicionado!")
    else:
        print("   ✅ Campo status_pagamento_custo já existe")

    # Criar índice
    if not verificar_indice_existe('moto', 'idx_moto_status_pagamento'):
        print("   ⏳ Criando índice idx_moto_status_pagamento...")
        sql = text("""
            CREATE INDEX idx_moto_status_pagamento
            ON moto(status_pagamento_custo);
        """)
        db.session.execute(sql)
        db.session.commit()
        print("   ✅ Índice idx_moto_status_pagamento criado!")
    else:
        print("   ✅ Índice idx_moto_status_pagamento já existe")

    # Adicionar comentários nas colunas
    print("   ⏳ Adicionando comentários nas colunas...")
    try:
        sql = text("""
            COMMENT ON COLUMN moto.custo_pago IS 'Valor efetivamente pago ao fornecedor';
            COMMENT ON COLUMN moto.data_pagamento_custo IS 'Data do pagamento do custo de aquisição';
            COMMENT ON COLUMN moto.status_pagamento_custo IS 'PENDENTE, PAGO, PARCIAL';
        """)
        db.session.execute(sql)
        db.session.commit()
        print("   ✅ Comentários adicionados!")
    except Exception as e:
        print(f"   ⚠️  Comentários já existem ou erro: {e}")


def adicionar_campos_pagamento_montagem():
    """
    Adiciona campos de controle de pagamento de montagem
    - fornecedor_montagem: Equipe terceirizada responsável
    - montagem_paga: Flag indicando se foi paga
    - data_pagamento_montagem: Data do pagamento
    """
    print("\n🔍 Verificando tabela PEDIDO_VENDA_MOTO_ITEM - Campos de Pagamento de Montagem...")

    if not verificar_coluna_existe('pedido_venda_moto_item', 'fornecedor_montagem'):
        print("   ⏳ Adicionando campo fornecedor_montagem...")
        sql = text("ALTER TABLE pedido_venda_moto_item ADD COLUMN fornecedor_montagem VARCHAR(100);")
        db.session.execute(sql)
        db.session.commit()
        print("   ✅ Campo fornecedor_montagem adicionado!")
    else:
        print("   ✅ Campo fornecedor_montagem já existe")

    if not verificar_coluna_existe('pedido_venda_moto_item', 'montagem_paga'):
        print("   ⏳ Adicionando campo montagem_paga...")
        sql = text("""
            ALTER TABLE pedido_venda_moto_item
            ADD COLUMN montagem_paga BOOLEAN DEFAULT FALSE NOT NULL;
        """)
        db.session.execute(sql)
        db.session.commit()
        print("   ✅ Campo montagem_paga adicionado!")
    else:
        print("   ✅ Campo montagem_paga já existe")

    if not verificar_coluna_existe('pedido_venda_moto_item', 'data_pagamento_montagem'):
        print("   ⏳ Adicionando campo data_pagamento_montagem...")
        sql = text("ALTER TABLE pedido_venda_moto_item ADD COLUMN data_pagamento_montagem DATE;")
        db.session.execute(sql)
        db.session.commit()
        print("   ✅ Campo data_pagamento_montagem adicionado!")
    else:
        print("   ✅ Campo data_pagamento_montagem já existe")

    # Criar índice
    if not verificar_indice_existe('pedido_venda_moto_item', 'idx_montagem_paga'):
        print("   ⏳ Criando índice idx_montagem_paga...")
        sql = text("""
            CREATE INDEX idx_montagem_paga
            ON pedido_venda_moto_item(montagem_paga);
        """)
        db.session.execute(sql)
        db.session.commit()
        print("   ✅ Índice idx_montagem_paga criado!")
    else:
        print("   ✅ Índice idx_montagem_paga já existe")

    # Adicionar comentários nas colunas
    print("   ⏳ Adicionando comentários nas colunas...")
    try:
        sql = text("""
            COMMENT ON COLUMN pedido_venda_moto_item.fornecedor_montagem
                IS 'Equipe terceirizada responsável pela montagem';
            COMMENT ON COLUMN pedido_venda_moto_item.montagem_paga
                IS 'Indica se a montagem foi paga';
            COMMENT ON COLUMN pedido_venda_moto_item.data_pagamento_montagem
                IS 'Data do pagamento da montagem';
        """)
        db.session.execute(sql)
        db.session.commit()
        print("   ✅ Comentários adicionados!")
    except Exception as e:
        print(f"   ⚠️  Comentários já existem ou erro: {e}")


def verificar_campos_adicionados():
    """Executa verificação final dos campos adicionados"""
    print("\n🔍 VERIFICAÇÃO FINAL...")

    print("\n   📋 Campos na tabela MOTO:")
    sql = text("""
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_name = 'moto'
        AND column_name IN ('custo_pago', 'data_pagamento_custo', 'status_pagamento_custo')
        ORDER BY ordinal_position;
    """)
    resultado = db.session.execute(sql)
    campos_moto = resultado.fetchall()

    if campos_moto:
        for campo in campos_moto:
            print(f"      ✅ {campo[0]:30} | {campo[1]:20} | Nullable: {campo[2]:3} | Default: {campo[3]}")
    else:
        print("      ⚠️  Nenhum campo encontrado!")

    print("\n   📋 Campos na tabela PEDIDO_VENDA_MOTO_ITEM:")
    sql = text("""
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_name = 'pedido_venda_moto_item'
        AND column_name IN ('fornecedor_montagem', 'montagem_paga', 'data_pagamento_montagem')
        ORDER BY ordinal_position;
    """)
    resultado = db.session.execute(sql)
    campos_item = resultado.fetchall()

    if campos_item:
        for campo in campos_item:
            print(f"      ✅ {campo[0]:30} | {campo[1]:20} | Nullable: {campo[2]:3} | Default: {campo[3]}")
    else:
        print("      ⚠️  Nenhum campo encontrado!")


def main():
    """Executa a migração de campos de pagamento"""
    print("=" * 70)
    print("🔧 MIGRAÇÃO: CAMPOS DE CONTROLE DE PAGAMENTO - SISTEMA MOTOCHEFE")
    print("=" * 70)
    print(f"📅 Data: {agora_utc_naive().strftime('%d/%m/%Y %H:%M:%S')}")
    print("=" * 70)
    print("\n📝 DESCRIÇÃO:")
    print("   - Adiciona campos de controle de pagamento de custo de motos")
    print("   - Adiciona campos de controle de pagamento de montagem")
    print("   - Cria índices para otimização de consultas")
    print("=" * 70)

    app = create_app()

    with app.app_context():
        try:
            # Executar migrações
            adicionar_campos_pagamento_moto()
            adicionar_campos_pagamento_montagem()

            # Verificação final
            verificar_campos_adicionados()

            print("\n" + "=" * 70)
            print("✅ MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
            print("=" * 70)
            print("\n📊 RESUMO DAS ALTERAÇÕES:")
            print("   1. ✅ Tabela MOTO:")
            print("      - custo_pago (NUMERIC)")
            print("      - data_pagamento_custo (DATE)")
            print("      - status_pagamento_custo (VARCHAR - PENDENTE/PAGO/PARCIAL)")
            print("      - idx_moto_status_pagamento (INDEX)")
            print("\n   2. ✅ Tabela PEDIDO_VENDA_MOTO_ITEM:")
            print("      - fornecedor_montagem (VARCHAR)")
            print("      - montagem_paga (BOOLEAN)")
            print("      - data_pagamento_montagem (DATE)")
            print("      - idx_montagem_paga (INDEX)")
            print("\n⚠️  PRÓXIMOS PASSOS:")
            print("   1. Reiniciar servidor Flask (se estiver rodando)")
            print("   2. Testar funcionalidades de pagamento")
            print("   3. Verificar se os models estão sincronizados")
            print("   4. Implementar rotas para controle de pagamentos")
            print("\n💡 DICA:")
            print("   Os models Python já possuem estes campos definidos em:")
            print("   - app/motochefe/models/produto.py (Moto)")
            print("   - app/motochefe/models/vendas.py (PedidoVendaMotoItem)")
            print("\n")

        except Exception as e:
            print("\n" + "=" * 70)
            print(f"❌ ERRO NA MIGRAÇÃO: {e}")
            print("=" * 70)
            print("\n⚠️  DETALHES DO ERRO:")
            import traceback
            traceback.print_exc()
            print("\n⚠️  Reverta as alterações manualmente se necessário")
            db.session.rollback()
            raise


if __name__ == '__main__':
    main()

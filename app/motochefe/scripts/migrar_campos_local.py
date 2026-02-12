"""
Script de Migração Local - MotoCHEFE
Adiciona campos faltantes no banco de dados local

Uso:
    python app/motochefe/scripts/migrar_campos_local.py

IMPORTANTE:
- Execute a partir da raiz do projeto
- Certifique-se de que o app Flask está configurado
- Faz backup antes de executar (opcional)
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


def verificar_tabela_existe(tabela):
    """Verifica se tabela existe"""
    inspector = inspect(db.engine)
    return tabela in inspector.get_table_names()


def criar_tabela_empresa_venda_moto():
    """Cria tabela empresa_venda_moto se não existir"""
    print("\n🔍 Verificando tabela empresa_venda_moto...")

    if verificar_tabela_existe('empresa_venda_moto'):
        print("   ✅ Tabela empresa_venda_moto já existe")
        return

    print("   ⏳ Criando tabela empresa_venda_moto...")

    sql = text("""
        CREATE TABLE empresa_venda_moto (
            id SERIAL PRIMARY KEY,
            cnpj_empresa VARCHAR(20) NOT NULL UNIQUE,
            empresa VARCHAR(255) NOT NULL,

            chave_pix VARCHAR(100),
            banco VARCHAR(100),
            cod_banco VARCHAR(10),
            agencia VARCHAR(20),
            conta VARCHAR(20),

            ativo BOOLEAN NOT NULL DEFAULT TRUE,
            criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            criado_por VARCHAR(100),
            atualizado_em TIMESTAMP,
            atualizado_por VARCHAR(100)
        );

        CREATE INDEX idx_empresa_venda_moto_ativo ON empresa_venda_moto(ativo) WHERE ativo = TRUE;
        CREATE INDEX idx_empresa_venda_moto_cnpj ON empresa_venda_moto(cnpj_empresa);
    """)

    db.session.execute(sql)
    db.session.commit()
    print("   ✅ Tabela empresa_venda_moto criada com sucesso!")


def adicionar_campos_transportadora():
    """Adiciona dados bancários em transportadora_moto"""
    print("\n🔍 Verificando transportadora_moto...")

    campos = {
        'chave_pix': 'VARCHAR(100)',
        'agencia': 'VARCHAR(20)',
        'conta': 'VARCHAR(20)',
        'banco': 'VARCHAR(100)',
        'cod_banco': 'VARCHAR(10)'
    }

    for campo, tipo in campos.items():
        if not verificar_coluna_existe('transportadora_moto', campo):
            print(f"   ⏳ Adicionando coluna {campo}...")
            sql = text(f"ALTER TABLE transportadora_moto ADD COLUMN {campo} {tipo};")
            db.session.execute(sql)
            db.session.commit()
            print(f"   ✅ Coluna {campo} adicionada!")
        else:
            print(f"   ✅ Coluna {campo} já existe")


def adicionar_campo_empresa_venda_pedido():
    """Adiciona empresa_venda_id em pedido_venda_moto"""
    print("\n🔍 Verificando pedido_venda_moto...")

    if not verificar_coluna_existe('pedido_venda_moto', 'empresa_venda_id'):
        print("   ⏳ Adicionando coluna empresa_venda_id...")

        sql = text("""
            ALTER TABLE pedido_venda_moto
            ADD COLUMN empresa_venda_id INTEGER REFERENCES empresa_venda_moto(id);

            CREATE INDEX idx_pedido_venda_empresa ON pedido_venda_moto(empresa_venda_id);
        """)

        db.session.execute(sql)
        db.session.commit()
        print("   ✅ Coluna empresa_venda_id adicionada!")
    else:
        print("   ✅ Coluna empresa_venda_id já existe")


def adicionar_campo_prazo_titulo():
    """Adiciona prazo_dias e torna data_vencimento nullable em titulo_financeiro"""
    print("\n🔍 Verificando titulo_financeiro...")

    # Adicionar prazo_dias
    if not verificar_coluna_existe('titulo_financeiro', 'prazo_dias'):
        print("   ⏳ Adicionando coluna prazo_dias...")
        sql = text("ALTER TABLE titulo_financeiro ADD COLUMN prazo_dias INTEGER;")
        db.session.execute(sql)
        db.session.commit()
        print("   ✅ Coluna prazo_dias adicionada!")
    else:
        print("   ✅ Coluna prazo_dias já existe")

    # Tornar data_vencimento nullable
    print("   ⏳ Tornando data_vencimento nullable...")
    try:
        sql = text("ALTER TABLE titulo_financeiro ALTER COLUMN data_vencimento DROP NOT NULL;")
        db.session.execute(sql)
        db.session.commit()
        print("   ✅ data_vencimento agora é nullable!")
    except Exception as e:
        print(f"   ⚠️  data_vencimento já era nullable ou erro: {e}")


def adicionar_campos_embarque():
    """Adiciona campos de frete em embarque_moto"""
    print("\n🔍 Verificando embarque_moto...")

    campos = {
        'valor_frete_contratado': 'NUMERIC(15, 2)',
        'data_pagamento_frete': 'DATE',
        'status_pagamento_frete': "VARCHAR(20) DEFAULT 'PENDENTE'"
    }

    for campo, tipo in campos.items():
        if not verificar_coluna_existe('embarque_moto', campo):
            print(f"   ⏳ Adicionando coluna {campo}...")
            sql = text(f"ALTER TABLE embarque_moto ADD COLUMN {campo} {tipo};")
            db.session.execute(sql)
            db.session.commit()
            print(f"   ✅ Coluna {campo} adicionada!")
        else:
            print(f"   ✅ Coluna {campo} já existe")

    # Tornar valor_frete_pago nullable
    print("   ⏳ Tornando valor_frete_pago nullable...")
    try:
        sql = text("ALTER TABLE embarque_moto ALTER COLUMN valor_frete_pago DROP NOT NULL;")
        db.session.execute(sql)
        db.session.commit()
        print("   ✅ valor_frete_pago agora é nullable!")
    except Exception as e:
        print(f"   ⚠️  valor_frete_pago já era nullable ou erro: {e}")

    # Atualizar registros existentes
    print("   ⏳ Atualizando registros existentes...")
    try:
        sql = text("""
            UPDATE embarque_moto
            SET valor_frete_contratado = valor_frete_pago
            WHERE valor_frete_contratado IS NULL AND valor_frete_pago IS NOT NULL;
        """)
        db.session.execute(sql)
        db.session.commit()
        print("   ✅ Registros atualizados!")
    except Exception as e:
        print(f"   ⚠️  Erro ao atualizar: {e}")


def adicionar_campo_enviado_embarque_pedido():
    """Adiciona campo enviado em embarque_pedido"""
    print("\n🔍 Verificando embarque_pedido...")

    if not verificar_coluna_existe('embarque_pedido', 'enviado'):
        print("   ⏳ Adicionando coluna enviado...")

        sql = text("""
            ALTER TABLE embarque_pedido
            ADD COLUMN enviado BOOLEAN NOT NULL DEFAULT FALSE;

            CREATE INDEX idx_embarque_pedido_enviado ON embarque_pedido(enviado);
        """)

        db.session.execute(sql)
        db.session.commit()
        print("   ✅ Coluna enviado adicionada!")
    else:
        print("   ✅ Coluna enviado já existe")


def adicionar_campo_atualizado_comissao():
    """Adiciona atualizado_por em comissao_vendedor"""
    print("\n🔍 Verificando comissao_vendedor...")

    if not verificar_coluna_existe('comissao_vendedor', 'atualizado_por'):
        print("   ⏳ Adicionando coluna atualizado_por...")
        sql = text("ALTER TABLE comissao_vendedor ADD COLUMN atualizado_por VARCHAR(100);")
        db.session.execute(sql)
        db.session.commit()
        print("   ✅ Coluna atualizado_por adicionada!")
    else:
        print("   ✅ Coluna atualizado_por já existe")


def main():
    """Executa todas as migrações"""
    print("=" * 60)
    print("🔧 MIGRAÇÃO DE CAMPOS - SISTEMA MOTOCHEFE")
    print("=" * 60)
    print(f"📅 Data: {agora_utc_naive().strftime('%d/%m/%Y %H:%M:%S')}")
    print("=" * 60)

    app = create_app()

    with app.app_context():
        try:
            # Executar todas as migrações na ordem correta
            criar_tabela_empresa_venda_moto()  # Primeiro: criar tabela referenciada
            adicionar_campos_transportadora()
            adicionar_campo_empresa_venda_pedido()  # Depois: adicionar FK
            adicionar_campo_prazo_titulo()
            adicionar_campos_embarque()
            adicionar_campo_enviado_embarque_pedido()
            adicionar_campo_atualizado_comissao()

            print("\n" + "=" * 60)
            print("✅ MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
            print("=" * 60)
            print("\n⚠️  PRÓXIMOS PASSOS:")
            print("   1. Reiniciar servidor Flask")
            print("   2. Testar funcionalidades modificadas")
            print("   3. Verificar se todos os models funcionam corretamente")
            print("\n")

        except Exception as e:
            print("\n" + "=" * 60)
            print(f"❌ ERRO NA MIGRAÇÃO: {e}")
            print("=" * 60)
            print("\n⚠️  Reverta as alterações manualmente se necessário")
            db.session.rollback()
            raise


if __name__ == '__main__':
    main()

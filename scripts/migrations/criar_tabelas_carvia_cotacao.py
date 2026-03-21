"""
Migration: Criar tabelas carvia_cotacoes + carvia_cotacao_motos + carvia_pedidos + carvia_pedido_itens
Data: 2026-03-20
Descricao:
  - carvia_cotacoes: cotacoes comerciais proativas
  - carvia_cotacao_motos: itens de moto na cotacao
  - carvia_pedidos: pedidos vinculados a cotacao (SP/RJ)
  - carvia_pedido_itens: itens dos pedidos
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db


def verificar_antes(conn):
    """Verifica estado antes da migration"""
    for tabela in ['carvia_cotacoes', 'carvia_cotacao_motos', 'carvia_pedidos', 'carvia_pedido_itens']:
        result = conn.execute(db.text(
            "SELECT EXISTS ("
            "  SELECT 1 FROM information_schema.tables "
            f"  WHERE table_name = '{tabela}'"
            ")"
        ))
        print(f"[ANTES] {tabela} existe: {result.scalar()}")


def executar_migration(conn):
    """Executa DDL"""
    # 1. carvia_cotacoes
    conn.execute(db.text("""
        CREATE TABLE IF NOT EXISTS carvia_cotacoes (
            id SERIAL PRIMARY KEY,
            numero_cotacao VARCHAR(20) NOT NULL,
            cliente_id INTEGER NOT NULL REFERENCES carvia_clientes(id),
            endereco_origem_id INTEGER NOT NULL REFERENCES carvia_cliente_enderecos(id),
            endereco_destino_id INTEGER NOT NULL REFERENCES carvia_cliente_enderecos(id),
            tipo_material VARCHAR(20) NOT NULL,
            peso NUMERIC(15,3),
            valor_mercadoria NUMERIC(15,2),
            dimensao_c NUMERIC(10,4),
            dimensao_l NUMERIC(10,4),
            dimensao_a NUMERIC(10,4),
            peso_cubado NUMERIC(15,3),
            volumes INTEGER,
            valor_tabela NUMERIC(15,2),
            percentual_desconto NUMERIC(5,2) DEFAULT 0,
            valor_descontado NUMERIC(15,2),
            valor_final_aprovado NUMERIC(15,2),
            tabela_carvia_id INTEGER REFERENCES carvia_tabelas_frete(id),
            dentro_tabela BOOLEAN,
            detalhes_calculo JSONB,
            data_cotacao TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            data_expedicao DATE,
            data_agenda DATE,
            status VARCHAR(20) NOT NULL DEFAULT 'RASCUNHO',
            aprovado_por VARCHAR(100),
            aprovado_em TIMESTAMP WITHOUT TIME ZONE,
            observacoes TEXT,
            criado_por VARCHAR(100) NOT NULL,
            criado_em TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT ck_carvia_cotacao_status CHECK (
                status IN ('RASCUNHO','PENDENTE_ADMIN','ENVIADO','APROVADO','RECUSADO','CANCELADO')
            ),
            CONSTRAINT ck_carvia_cotacao_tipo_material CHECK (
                tipo_material IN ('CARGA_GERAL', 'MOTO')
            )
        )
    """))
    print("[OK] carvia_cotacoes criada")

    # Indices cotacoes
    conn.execute(db.text("CREATE INDEX IF NOT EXISTS ix_carvia_cotacao_numero ON carvia_cotacoes(numero_cotacao)"))
    conn.execute(db.text("CREATE INDEX IF NOT EXISTS ix_carvia_cotacao_cliente ON carvia_cotacoes(cliente_id)"))
    conn.execute(db.text("CREATE INDEX IF NOT EXISTS ix_carvia_cotacao_status ON carvia_cotacoes(status)"))
    print("[OK] Indices cotacoes criados")

    # 2. carvia_cotacao_motos
    conn.execute(db.text("""
        CREATE TABLE IF NOT EXISTS carvia_cotacao_motos (
            id SERIAL PRIMARY KEY,
            cotacao_id INTEGER NOT NULL REFERENCES carvia_cotacoes(id) ON DELETE CASCADE,
            modelo_moto_id INTEGER NOT NULL REFERENCES carvia_modelos_moto(id),
            categoria_moto_id INTEGER NOT NULL REFERENCES carvia_categorias_moto(id),
            quantidade INTEGER NOT NULL,
            peso_cubado_unitario NUMERIC(10,3),
            peso_cubado_total NUMERIC(15,3)
        )
    """))
    conn.execute(db.text("CREATE INDEX IF NOT EXISTS ix_carvia_cotmoto_cotacao ON carvia_cotacao_motos(cotacao_id)"))
    print("[OK] carvia_cotacao_motos criada")

    # 3. carvia_pedidos
    conn.execute(db.text("""
        CREATE TABLE IF NOT EXISTS carvia_pedidos (
            id SERIAL PRIMARY KEY,
            numero_pedido VARCHAR(20) NOT NULL,
            cotacao_id INTEGER NOT NULL REFERENCES carvia_cotacoes(id),
            filial VARCHAR(5) NOT NULL,
            tipo_separacao VARCHAR(20) NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'PENDENTE',
            observacoes TEXT,
            criado_por VARCHAR(100) NOT NULL,
            criado_em TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT ck_carvia_pedido_status CHECK (
                status IN ('PENDENTE','SEPARADO','FATURADO','EMBARCADO','CANCELADO')
            ),
            CONSTRAINT ck_carvia_pedido_filial CHECK (filial IN ('SP', 'RJ')),
            CONSTRAINT ck_carvia_pedido_tipo_sep CHECK (
                tipo_separacao IN ('ESTOQUE', 'CROSSDOCK')
            )
        )
    """))
    conn.execute(db.text("CREATE INDEX IF NOT EXISTS ix_carvia_pedido_numero ON carvia_pedidos(numero_pedido)"))
    conn.execute(db.text("CREATE INDEX IF NOT EXISTS ix_carvia_pedido_cotacao ON carvia_pedidos(cotacao_id)"))
    conn.execute(db.text("CREATE INDEX IF NOT EXISTS ix_carvia_pedido_status ON carvia_pedidos(status)"))
    print("[OK] carvia_pedidos criada")

    # 4. carvia_pedido_itens
    conn.execute(db.text("""
        CREATE TABLE IF NOT EXISTS carvia_pedido_itens (
            id SERIAL PRIMARY KEY,
            pedido_id INTEGER NOT NULL REFERENCES carvia_pedidos(id) ON DELETE CASCADE,
            modelo_moto_id INTEGER REFERENCES carvia_modelos_moto(id),
            descricao VARCHAR(255),
            cor VARCHAR(50),
            quantidade INTEGER NOT NULL,
            valor_unitario NUMERIC(15,2),
            valor_total NUMERIC(15,2),
            numero_nf VARCHAR(20)
        )
    """))
    conn.execute(db.text("CREATE INDEX IF NOT EXISTS ix_carvia_peditem_pedido ON carvia_pedido_itens(pedido_id)"))
    print("[OK] carvia_pedido_itens criada")


def verificar_depois(conn):
    """Verifica estado apos migration"""
    for tabela in ['carvia_cotacoes', 'carvia_cotacao_motos', 'carvia_pedidos', 'carvia_pedido_itens']:
        result = conn.execute(db.text(
            "SELECT EXISTS ("
            "  SELECT 1 FROM information_schema.tables "
            f"  WHERE table_name = '{tabela}'"
            ")"
        ))
        print(f"[DEPOIS] {tabela} existe: {result.scalar()}")


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        with db.engine.begin() as conn:
            print("=" * 60)
            print("Migration: Criar tabelas cotacao + pedidos CarVia")
            print("=" * 60)

            verificar_antes(conn)
            print("-" * 60)
            executar_migration(conn)
            print("-" * 60)
            verificar_depois(conn)

            print("=" * 60)
            print("Migration concluida com sucesso!")

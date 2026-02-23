"""
Script para criar tabelas do modulo Pessoal (financas pessoais)
Executar localmente: python scripts/migrations/criar_tabelas_pessoal.py
"""
import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def criar_tabelas_pessoal():
    """Cria as 7 tabelas do modulo pessoal"""
    app = create_app()
    with app.app_context():
        try:
            print("=" * 60)
            print("CRIANDO TABELAS DO MODULO PESSOAL")
            print("=" * 60)

            # ============================================
            # TABELA 1: pessoal_membros
            # ============================================
            print("\n[1/7] Criando tabela pessoal_membros...")

            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS pessoal_membros (
                    id SERIAL PRIMARY KEY,
                    nome VARCHAR(100) NOT NULL UNIQUE,
                    nome_completo VARCHAR(200),
                    papel VARCHAR(50),
                    ativo BOOLEAN DEFAULT TRUE,
                    criado_em TIMESTAMP DEFAULT NOW()
                );
            """))

            print("   Tabela pessoal_membros criada com sucesso!")

            # ============================================
            # TABELA 2: pessoal_contas
            # ============================================
            print("\n[2/7] Criando tabela pessoal_contas...")

            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS pessoal_contas (
                    id SERIAL PRIMARY KEY,
                    nome VARCHAR(100) NOT NULL,
                    tipo VARCHAR(20) NOT NULL,
                    banco VARCHAR(50) NOT NULL DEFAULT 'bradesco',
                    agencia VARCHAR(20),
                    numero_conta VARCHAR(30),
                    ultimos_digitos_cartao VARCHAR(10),
                    membro_id INTEGER REFERENCES pessoal_membros(id),
                    ativa BOOLEAN DEFAULT TRUE,
                    criado_em TIMESTAMP DEFAULT NOW()
                );
            """))

            print("   Tabela pessoal_contas criada com sucesso!")

            # ============================================
            # TABELA 3: pessoal_categorias
            # ============================================
            print("\n[3/7] Criando tabela pessoal_categorias...")

            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS pessoal_categorias (
                    id SERIAL PRIMARY KEY,
                    nome VARCHAR(100) NOT NULL UNIQUE,
                    grupo VARCHAR(100) NOT NULL,
                    icone VARCHAR(50),
                    ordem_exibicao INTEGER DEFAULT 0,
                    ativa BOOLEAN DEFAULT TRUE,
                    criado_em TIMESTAMP DEFAULT NOW()
                );
            """))

            print("   Tabela pessoal_categorias criada com sucesso!")

            # ============================================
            # TABELA 4: pessoal_regras_categorizacao
            # ============================================
            print("\n[4/7] Criando tabela pessoal_regras_categorizacao...")

            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS pessoal_regras_categorizacao (
                    id SERIAL PRIMARY KEY,
                    padrao_historico VARCHAR(300) NOT NULL,
                    tipo_regra VARCHAR(20) NOT NULL,
                    categoria_id INTEGER REFERENCES pessoal_categorias(id),
                    membro_id INTEGER REFERENCES pessoal_membros(id),
                    categorias_restritas_ids TEXT,
                    vezes_usado INTEGER DEFAULT 0,
                    confianca NUMERIC(5,2) DEFAULT 100,
                    origem VARCHAR(30) DEFAULT 'semente',
                    ativo BOOLEAN DEFAULT TRUE,
                    criado_em TIMESTAMP DEFAULT NOW(),
                    atualizado_em TIMESTAMP DEFAULT NOW()
                );
            """))

            print("   Tabela pessoal_regras_categorizacao criada com sucesso!")

            # ============================================
            # TABELA 5: pessoal_exclusoes_empresa
            # ============================================
            print("\n[5/7] Criando tabela pessoal_exclusoes_empresa...")

            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS pessoal_exclusoes_empresa (
                    id SERIAL PRIMARY KEY,
                    padrao VARCHAR(200) NOT NULL,
                    descricao VARCHAR(200),
                    ativo BOOLEAN DEFAULT TRUE
                );
            """))

            print("   Tabela pessoal_exclusoes_empresa criada com sucesso!")

            # ============================================
            # TABELA 6: pessoal_importacoes
            # ============================================
            print("\n[6/7] Criando tabela pessoal_importacoes...")

            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS pessoal_importacoes (
                    id SERIAL PRIMARY KEY,
                    conta_id INTEGER NOT NULL REFERENCES pessoal_contas(id),
                    nome_arquivo VARCHAR(255),
                    tipo_arquivo VARCHAR(30),
                    periodo_inicio DATE,
                    periodo_fim DATE,
                    situacao_fatura VARCHAR(30),
                    total_linhas INTEGER DEFAULT 0,
                    linhas_importadas INTEGER DEFAULT 0,
                    linhas_duplicadas INTEGER DEFAULT 0,
                    linhas_empresa_filtradas INTEGER DEFAULT 0,
                    status VARCHAR(20) DEFAULT 'IMPORTADO',
                    criado_em TIMESTAMP DEFAULT NOW(),
                    criado_por VARCHAR(100)
                );
            """))

            print("   Tabela pessoal_importacoes criada com sucesso!")

            # ============================================
            # TABELA 7: pessoal_transacoes
            # ============================================
            print("\n[7/7] Criando tabela pessoal_transacoes...")

            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS pessoal_transacoes (
                    id SERIAL PRIMARY KEY,
                    importacao_id INTEGER NOT NULL REFERENCES pessoal_importacoes(id),
                    conta_id INTEGER NOT NULL REFERENCES pessoal_contas(id),
                    data DATE NOT NULL,
                    historico VARCHAR(500) NOT NULL,
                    descricao VARCHAR(500),
                    historico_completo VARCHAR(1000),
                    documento VARCHAR(50),
                    valor NUMERIC(15,2) NOT NULL,
                    tipo VARCHAR(10) NOT NULL,
                    saldo NUMERIC(15,2),
                    valor_dolar NUMERIC(15,4),
                    parcela_atual INTEGER,
                    parcela_total INTEGER,
                    identificador_parcela VARCHAR(100),
                    categoria_id INTEGER REFERENCES pessoal_categorias(id),
                    regra_id INTEGER REFERENCES pessoal_regras_categorizacao(id),
                    categorizacao_auto BOOLEAN DEFAULT FALSE,
                    categorizacao_confianca NUMERIC(5,2),
                    membro_id INTEGER REFERENCES pessoal_membros(id),
                    membro_auto BOOLEAN DEFAULT FALSE,
                    excluir_relatorio BOOLEAN DEFAULT FALSE,
                    eh_pagamento_cartao BOOLEAN DEFAULT FALSE,
                    eh_transferencia_propria BOOLEAN DEFAULT FALSE,
                    observacao TEXT,
                    status VARCHAR(20) DEFAULT 'PENDENTE',
                    hash_transacao VARCHAR(64) NOT NULL UNIQUE,
                    criado_em TIMESTAMP DEFAULT NOW(),
                    atualizado_em TIMESTAMP DEFAULT NOW(),
                    categorizado_em TIMESTAMP,
                    categorizado_por VARCHAR(100)
                );
            """))

            # Indices para pessoal_transacoes
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_pessoal_transacoes_data
                    ON pessoal_transacoes(data);
            """))
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_pessoal_transacoes_conta
                    ON pessoal_transacoes(conta_id);
            """))
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_pessoal_transacoes_categoria
                    ON pessoal_transacoes(categoria_id);
            """))
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_pessoal_transacoes_membro
                    ON pessoal_transacoes(membro_id);
            """))
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_pessoal_transacoes_status
                    ON pessoal_transacoes(status);
            """))

            print("   Tabela pessoal_transacoes criada com sucesso!")

            db.session.commit()

            print("\n" + "=" * 60)
            print("TODAS AS 7 TABELAS CRIADAS COM SUCESSO!")
            print("=" * 60)

            # Verificar criacao
            result = db.session.execute(text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_name LIKE 'pessoal_%'
                ORDER BY table_name;
            """))
            tabelas = [row[0] for row in result.fetchall()]
            print(f"\nTabelas encontradas: {tabelas}")

        except Exception as e:
            print(f"\n[ERRO] Falha ao criar tabelas: {e}")
            db.session.rollback()
            raise


def popular_dados_semente():
    """Insere dados semente (membros, contas, categorias, regras, exclusoes)"""
    from app.pessoal.constants import (
        MEMBROS_FAMILIA,
        CONTAS_BANCARIAS,
        CATEGORIAS_DESPESAS,
        REGRAS_CATEGORIZACAO_SEMENTE,
        EXCLUSOES_EMPRESA,
    )

    app = create_app()
    with app.app_context():
        try:
            print("\n" + "=" * 60)
            print("POPULANDO DADOS SEMENTE")
            print("=" * 60)

            # ============================================
            # SEED 1: Membros
            # ============================================
            print("\n[SEED 1/5] Inserindo membros...")
            count_membros = 0
            for m in MEMBROS_FAMILIA:
                result = db.session.execute(text("""
                    INSERT INTO pessoal_membros (nome, nome_completo, papel)
                    VALUES (:nome, :nome_completo, :papel)
                    ON CONFLICT (nome) DO NOTHING
                    RETURNING id;
                """), {
                    "nome": m["nome"],
                    "nome_completo": m["nome_completo"],
                    "papel": m["papel"],
                })
                if result.fetchone():
                    count_membros += 1
            db.session.commit()
            print(f"   {count_membros} membros inseridos (de {len(MEMBROS_FAMILIA)} total)")

            # ============================================
            # SEED 2: Contas
            # ============================================
            print("\n[SEED 2/5] Inserindo contas bancarias...")
            count_contas = 0
            for c in CONTAS_BANCARIAS:
                # Buscar membro_id pelo nome
                membro_result = db.session.execute(text("""
                    SELECT id FROM pessoal_membros WHERE nome = :nome;
                """), {"nome": c["membro_nome"]})
                membro_row = membro_result.fetchone()
                membro_id = membro_row[0] if membro_row else None

                # Verificar se conta ja existe (por nome)
                existing = db.session.execute(text("""
                    SELECT id FROM pessoal_contas WHERE nome = :nome;
                """), {"nome": c["nome"]})
                if existing.fetchone():
                    continue

                db.session.execute(text("""
                    INSERT INTO pessoal_contas
                        (nome, tipo, banco, agencia, numero_conta, ultimos_digitos_cartao, membro_id)
                    VALUES
                        (:nome, :tipo, :banco, :agencia, :numero_conta, :ultimos_digitos_cartao, :membro_id);
                """), {
                    "nome": c["nome"],
                    "tipo": c["tipo"],
                    "banco": c["banco"],
                    "agencia": c["agencia"],
                    "numero_conta": c["numero_conta"],
                    "ultimos_digitos_cartao": c["ultimos_digitos_cartao"],
                    "membro_id": membro_id,
                })
                count_contas += 1
            db.session.commit()
            print(f"   {count_contas} contas inseridas (de {len(CONTAS_BANCARIAS)} total)")

            # ============================================
            # SEED 3: Categorias
            # ============================================
            print("\n[SEED 3/5] Inserindo categorias...")
            count_categorias = 0
            for cat in CATEGORIAS_DESPESAS:
                result = db.session.execute(text("""
                    INSERT INTO pessoal_categorias (nome, grupo, icone, ordem_exibicao)
                    VALUES (:nome, :grupo, :icone, :ordem)
                    ON CONFLICT (nome) DO NOTHING
                    RETURNING id;
                """), {
                    "nome": cat["nome"],
                    "grupo": cat["grupo"],
                    "icone": cat["icone"],
                    "ordem": cat["ordem"],
                })
                if result.fetchone():
                    count_categorias += 1
            db.session.commit()
            print(f"   {count_categorias} categorias inseridas (de {len(CATEGORIAS_DESPESAS)} total)")

            # ============================================
            # SEED 4: Regras de categorizacao semente
            # ============================================
            print("\n[SEED 4/5] Inserindo regras de categorizacao...")
            count_regras = 0
            for regra in REGRAS_CATEGORIZACAO_SEMENTE:
                # Verificar se regra ja existe (por padrao + tipo)
                existing = db.session.execute(text("""
                    SELECT id FROM pessoal_regras_categorizacao
                    WHERE padrao_historico = :padrao AND tipo_regra = :tipo;
                """), {
                    "padrao": regra["padrao"],
                    "tipo": regra["tipo"],
                })
                if existing.fetchone():
                    continue

                categoria_id = None
                categorias_restritas_ids = None

                if regra["tipo"] == "PADRAO" and regra.get("categoria"):
                    # Buscar categoria_id pelo nome
                    cat_result = db.session.execute(text("""
                        SELECT id FROM pessoal_categorias WHERE nome = :nome;
                    """), {"nome": regra["categoria"]})
                    cat_row = cat_result.fetchone()
                    if cat_row:
                        categoria_id = cat_row[0]
                    else:
                        print(f"   [AVISO] Categoria '{regra['categoria']}' nao encontrada, pulando regra '{regra['padrao']}'")
                        continue

                elif regra["tipo"] == "RELATIVO" and regra.get("categorias_restritas"):
                    # Buscar IDs das categorias restritas
                    ids_restritas = []
                    for cat_nome in regra["categorias_restritas"]:
                        cat_result = db.session.execute(text("""
                            SELECT id FROM pessoal_categorias WHERE nome = :nome;
                        """), {"nome": cat_nome})
                        cat_row = cat_result.fetchone()
                        if cat_row:
                            ids_restritas.append(cat_row[0])
                        else:
                            print(f"   [AVISO] Categoria restrita '{cat_nome}' nao encontrada")
                    categorias_restritas_ids = json.dumps(ids_restritas)

                db.session.execute(text("""
                    INSERT INTO pessoal_regras_categorizacao
                        (padrao_historico, tipo_regra, categoria_id, categorias_restritas_ids, origem)
                    VALUES
                        (:padrao, :tipo, :categoria_id, :categorias_restritas_ids, 'semente');
                """), {
                    "padrao": regra["padrao"],
                    "tipo": regra["tipo"],
                    "categoria_id": categoria_id,
                    "categorias_restritas_ids": categorias_restritas_ids,
                })
                count_regras += 1
            db.session.commit()
            print(f"   {count_regras} regras inseridas (de {len(REGRAS_CATEGORIZACAO_SEMENTE)} total)")

            # ============================================
            # SEED 5: Exclusoes empresa
            # ============================================
            print("\n[SEED 5/5] Inserindo exclusoes empresa...")
            count_exclusoes = 0
            for exc in EXCLUSOES_EMPRESA:
                # Verificar se exclusao ja existe (por padrao)
                existing = db.session.execute(text("""
                    SELECT id FROM pessoal_exclusoes_empresa WHERE padrao = :padrao;
                """), {"padrao": exc["padrao"]})
                if existing.fetchone():
                    continue

                db.session.execute(text("""
                    INSERT INTO pessoal_exclusoes_empresa (padrao, descricao)
                    VALUES (:padrao, :descricao);
                """), {
                    "padrao": exc["padrao"],
                    "descricao": exc["descricao"],
                })
                count_exclusoes += 1
            db.session.commit()
            print(f"   {count_exclusoes} exclusoes inseridas (de {len(EXCLUSOES_EMPRESA)} total)")

            print("\n" + "=" * 60)
            print("DADOS SEMENTE POPULADOS COM SUCESSO!")
            print("=" * 60)

            # Resumo final
            print("\nResumo:")
            for tabela in ['pessoal_membros', 'pessoal_contas', 'pessoal_categorias',
                           'pessoal_regras_categorizacao', 'pessoal_exclusoes_empresa']:
                result = db.session.execute(text(f"SELECT COUNT(*) FROM {tabela};"))
                count = result.scalar()
                print(f"   {tabela}: {count} registros")

        except Exception as e:
            print(f"\n[ERRO] Falha ao popular dados semente: {e}")
            db.session.rollback()
            raise


def verificar_tabelas():
    """Verifica se as tabelas existem e mostra sua estrutura"""
    app = create_app()
    with app.app_context():
        try:
            print("\n" + "=" * 60)
            print("VERIFICANDO ESTRUTURA DAS TABELAS")
            print("=" * 60)

            tabelas_pessoal = [
                'pessoal_membros', 'pessoal_contas', 'pessoal_categorias',
                'pessoal_regras_categorizacao', 'pessoal_exclusoes_empresa',
                'pessoal_importacoes', 'pessoal_transacoes',
            ]

            for tabela in tabelas_pessoal:
                result = db.session.execute(text("""
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns
                    WHERE table_name = :tabela
                    ORDER BY ordinal_position;
                """), {"tabela": tabela})
                rows = result.fetchall()
                if rows:
                    print(f"\n[{tabela}] ({len(rows)} colunas)")
                    for row in rows:
                        print(f"   {row[0]}: {row[1]} (nullable={row[2]})")
                else:
                    print(f"\n[{tabela}] NAO ENCONTRADA")

        except Exception as e:
            print(f"[ERRO] {e}")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Criar tabelas do modulo Pessoal')
    parser.add_argument('--verificar', action='store_true', help='Apenas verifica se as tabelas existem')
    parser.add_argument('--seed', action='store_true', help='Apenas popula dados semente (tabelas devem existir)')

    args = parser.parse_args()

    if args.verificar:
        verificar_tabelas()
    elif args.seed:
        popular_dados_semente()
    else:
        criar_tabelas_pessoal()
        popular_dados_semente()
        verificar_tabelas()

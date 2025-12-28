"""
Script de migracao - Tabela regra_comissao e campos relacionados
Cria estrutura para regras de comissao por grupo/cliente/produto

Uso:
    source .venv/bin/activate
    python scripts/migrations/criar_tabela_regra_comissao.py
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text
from datetime import datetime


def criar_tabela_regra_comissao():
    """Cria tabela regra_comissao"""
    print("\n[1/3] Criando tabela regra_comissao...")

    sql = """
    CREATE TABLE IF NOT EXISTS regra_comissao (
        id SERIAL PRIMARY KEY,

        -- Tipo de regra
        tipo_regra VARCHAR(20) NOT NULL,

        -- Criterio A: Grupo empresarial
        grupo_empresarial VARCHAR(100),

        -- Criterio B: Cliente
        raz_social_red VARCHAR(100),
        cliente_cod_uf VARCHAR(2),
        cliente_vendedor VARCHAR(100),
        cliente_equipe VARCHAR(100),

        -- Criterio C: Produto
        cod_produto VARCHAR(50),
        produto_grupo VARCHAR(100),
        produto_cliente VARCHAR(100),

        -- Percentual
        comissao_percentual NUMERIC(5, 2) NOT NULL,

        -- Vigencia
        vigencia_inicio DATE NOT NULL DEFAULT CURRENT_DATE,
        vigencia_fim DATE,

        -- Controle
        prioridade INTEGER DEFAULT 0,
        descricao TEXT,
        ativo BOOLEAN DEFAULT TRUE,
        criado_em TIMESTAMP DEFAULT NOW(),
        criado_por VARCHAR(100),
        atualizado_em TIMESTAMP DEFAULT NOW(),
        atualizado_por VARCHAR(100),

        CONSTRAINT chk_tipo_regra CHECK (tipo_regra IN ('GRUPO', 'CLIENTE', 'PRODUTO'))
    );
    """

    try:
        db.session.execute(text(sql))
        db.session.commit()
        print("   Tabela regra_comissao criada com sucesso!")
    except Exception as e:
        if 'already exists' in str(e).lower():
            print("   Tabela ja existe, pulando...")
        else:
            print(f"   Erro: {e}")
            db.session.rollback()
            return False

    # Criar indices
    indices = [
        ("idx_regra_comissao_tipo", "regra_comissao(tipo_regra)"),
        ("idx_regra_comissao_grupo", "regra_comissao(grupo_empresarial)"),
        ("idx_regra_comissao_cliente", "regra_comissao(raz_social_red)"),
        ("idx_regra_comissao_produto", "regra_comissao(cod_produto)"),
        ("idx_regra_comissao_ativo", "regra_comissao(ativo)"),
        ("idx_regra_comissao_vigencia", "regra_comissao(vigencia_inicio, vigencia_fim)"),
    ]

    for nome, definicao in indices:
        try:
            db.session.execute(text(f"CREATE INDEX IF NOT EXISTS {nome} ON {definicao};"))
            db.session.commit()
            print(f"   Indice {nome} criado")
        except Exception as e:
            if 'already exists' in str(e).lower():
                pass
            else:
                print(f"   Aviso: {e}")
            db.session.rollback()

    return True


def adicionar_campo_comissao_carteira():
    """Adiciona campo comissao_percentual na CarteiraPrincipal"""
    print("\n[2/3] Adicionando campo comissao_percentual em carteira_principal...")

    sql = """
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'carteira_principal'
            AND column_name = 'comissao_percentual'
        ) THEN
            ALTER TABLE carteira_principal
            ADD COLUMN comissao_percentual NUMERIC(5, 2) DEFAULT 0;

            COMMENT ON COLUMN carteira_principal.comissao_percentual IS
                'Percentual de comissao calculado (soma das regras aplicaveis)';
        END IF;
    END $$;
    """

    try:
        db.session.execute(text(sql))
        db.session.commit()
        print("   Campo comissao_percentual adicionado!")
    except Exception as e:
        print(f"   Erro: {e}")
        db.session.rollback()
        return False

    return True


def adicionar_parametro_perda():
    """Adiciona parametro PERCENTUAL_PERDA"""
    print("\n[3/3] Adicionando parametro PERCENTUAL_PERDA...")

    sql = """
    INSERT INTO parametro_custeio (chave, valor, descricao, atualizado_em, atualizado_por)
    VALUES (
        'PERCENTUAL_PERDA',
        0.00,
        'Percentual de perda aplicado sobre (custo_considerado + custo_producao). Ex: 0.5 = 0.5%',
        NOW(),
        'migracao'
    )
    ON CONFLICT (chave) DO NOTHING;
    """

    try:
        db.session.execute(text(sql))
        db.session.commit()
        print("   Parametro PERCENTUAL_PERDA adicionado!")
    except Exception as e:
        print(f"   Erro: {e}")
        db.session.rollback()
        return False

    return True


def verificar_estrutura():
    """Verifica se a estrutura foi criada corretamente"""
    print("\n[Verificacao]")

    # Verificar tabela regra_comissao
    result = db.session.execute(text("""
        SELECT COUNT(*) FROM information_schema.tables
        WHERE table_name = 'regra_comissao'
    """))
    existe_tabela = result.scalar() > 0
    print(f"   Tabela regra_comissao: {'OK' if existe_tabela else 'ERRO'}")

    # Verificar campo comissao_percentual
    result = db.session.execute(text("""
        SELECT COUNT(*) FROM information_schema.columns
        WHERE table_name = 'carteira_principal'
        AND column_name = 'comissao_percentual'
    """))
    existe_campo = result.scalar() > 0
    print(f"   Campo comissao_percentual: {'OK' if existe_campo else 'ERRO'}")

    # Verificar parametro
    result = db.session.execute(text("""
        SELECT valor FROM parametro_custeio WHERE chave = 'PERCENTUAL_PERDA'
    """))
    row = result.fetchone()
    existe_param = row is not None
    print(f"   Parametro PERCENTUAL_PERDA: {'OK' if existe_param else 'ERRO'}")
    if existe_param:
        print(f"      Valor atual: {row[0]}%")

    return existe_tabela and existe_campo and existe_param


def main():
    print("=" * 60)
    print("MIGRACAO: Regras de Comissao e Percentual de Perda")
    print("=" * 60)

    app = create_app()

    with app.app_context():
        # Executar migracoes
        criar_tabela_regra_comissao()
        adicionar_campo_comissao_carteira()
        adicionar_parametro_perda()

        # Verificar
        sucesso = verificar_estrutura()

        print("\n" + "=" * 60)
        if sucesso:
            print("MIGRACAO CONCLUIDA COM SUCESSO!")
        else:
            print("MIGRACAO CONCLUIDA COM ERROS - Verifique os logs")
        print("=" * 60)


if __name__ == '__main__':
    main()

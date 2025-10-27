"""
Script para corrigir estrutura da tabela grupo_empresarial

PROBLEMA:
- Banco pode estar com estrutura antiga (tipo_grupo, info_grupo[])
- Precisa migrar para estrutura nova (prefixo_cnpj por linha)

SOLUÇÃO:
- Remove colunas antigas (tipo_grupo, info_grupo)
- Adiciona colunas novas (prefixo_cnpj, descricao)
- Ajusta constraints e índices

USO:
    python migrations/fix_grupo_empresarial_structure.py
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from sqlalchemy import text

def verificar_estrutura_atual():
    """Verifica estrutura atual da tabela"""
    print("\n1. VERIFICANDO ESTRUTURA ATUAL...")

    result = db.session.execute(text("""
        SELECT column_name, data_type, character_maximum_length, is_nullable
        FROM information_schema.columns
        WHERE table_name = 'grupo_empresarial'
        ORDER BY ordinal_position
    """))

    colunas = result.fetchall()
    print(f"   Encontradas {len(colunas)} colunas:")

    colunas_dict = {}
    for col in colunas:
        print(f"   - {col[0]} ({col[1]}) {'NULL' if col[3] == 'YES' else 'NOT NULL'}")
        colunas_dict[col[0]] = col[1]

    return colunas_dict

def verificar_constraints():
    """Verifica constraints atuais"""
    print("\n2. VERIFICANDO CONSTRAINTS...")

    result = db.session.execute(text("""
        SELECT conname, pg_get_constraintdef(oid) as definicao
        FROM pg_constraint
        WHERE conrelid = 'grupo_empresarial'::regclass
    """))

    constraints = result.fetchall()
    print(f"   Encontrados {len(constraints)} constraints:")
    for c in constraints:
        print(f"   - {c[0]}: {c[1]}")

    return {c[0]: c[1] for c in constraints}

def verificar_indices():
    """Verifica índices atuais"""
    print("\n3. VERIFICANDO ÍNDICES...")

    result = db.session.execute(text("""
        SELECT indexname, indexdef
        FROM pg_indexes
        WHERE tablename = 'grupo_empresarial'
    """))

    indices = result.fetchall()
    print(f"   Encontrados {len(indices)} índices:")
    for idx in indices:
        print(f"   - {idx[0]}")

    return [idx[0] for idx in indices]

def verificar_dados():
    """Verifica se há dados na tabela"""
    print("\n4. VERIFICANDO DADOS...")

    result = db.session.execute(text("""
        SELECT COUNT(*) FROM grupo_empresarial
    """))

    count = result.scalar()
    print(f"   Total de registros: {count}")

    return count

def migrar_estrutura(colunas_atuais):
    """Migra estrutura da tabela"""
    print("\n5. MIGRANDO ESTRUTURA...")

    mudancas = []

    # PASSO 1: Remover colunas antigas se existirem
    if 'tipo_grupo' in colunas_atuais:
        print("   → Removendo coluna 'tipo_grupo'...")
        db.session.execute(text("ALTER TABLE grupo_empresarial DROP COLUMN IF EXISTS tipo_grupo"))
        mudancas.append("Removida coluna tipo_grupo")

    if 'info_grupo' in colunas_atuais:
        print("   → Removendo coluna 'info_grupo'...")
        db.session.execute(text("ALTER TABLE grupo_empresarial DROP COLUMN IF EXISTS info_grupo"))
        mudancas.append("Removida coluna info_grupo")

    # PASSO 2: Adicionar coluna prefixo_cnpj se não existir
    if 'prefixo_cnpj' not in colunas_atuais:
        print("   → Adicionando coluna 'prefixo_cnpj'...")
        db.session.execute(text("""
            ALTER TABLE grupo_empresarial
            ADD COLUMN prefixo_cnpj VARCHAR(8) NOT NULL DEFAULT '00000000'
        """))
        # Remover DEFAULT após criar
        db.session.execute(text("""
            ALTER TABLE grupo_empresarial
            ALTER COLUMN prefixo_cnpj DROP DEFAULT
        """))
        mudancas.append("Adicionada coluna prefixo_cnpj")

    # PASSO 3: Adicionar coluna descricao se não existir
    if 'descricao' not in colunas_atuais:
        print("   → Adicionando coluna 'descricao'...")
        db.session.execute(text("""
            ALTER TABLE grupo_empresarial
            ADD COLUMN descricao VARCHAR(255)
        """))
        mudancas.append("Adicionada coluna descricao")

    return mudancas

def ajustar_constraints_indices(constraints_atuais, indices_atuais):
    """Ajusta constraints e índices"""
    print("\n6. AJUSTANDO CONSTRAINTS E ÍNDICES...")

    mudancas = []

    # Remover índice UNIQUE de nome_grupo se existir
    if 'ix_grupo_empresarial_nome_grupo' in indices_atuais:
        print("   → Removendo índice UNIQUE de nome_grupo...")
        db.session.execute(text("DROP INDEX IF EXISTS ix_grupo_empresarial_nome_grupo"))
        mudancas.append("Removido índice UNIQUE de nome_grupo")

    # Remover índices antigos
    indices_remover = ['idx_grupo_tipo', 'idx_grupo_nome', 'idx_grupo_empresarial_nome_normal']
    for idx in indices_remover:
        if idx in indices_atuais:
            print(f"   → Removendo índice '{idx}'...")
            db.session.execute(text(f"DROP INDEX IF EXISTS {idx}"))
            mudancas.append(f"Removido índice {idx}")

    # Adicionar constraint UNIQUE em prefixo_cnpj
    if 'uk_prefixo_cnpj' not in constraints_atuais:
        print("   → Adicionando UNIQUE em prefixo_cnpj...")
        db.session.execute(text("""
            ALTER TABLE grupo_empresarial
            ADD CONSTRAINT uk_prefixo_cnpj UNIQUE (prefixo_cnpj)
        """))
        mudancas.append("Adicionado UNIQUE em prefixo_cnpj")

    # Criar índices necessários
    print("   → Criando índices necessários...")
    db.session.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_grupo_empresarial_nome
        ON grupo_empresarial(nome_grupo)
    """))

    db.session.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_grupo_empresarial_prefixo
        ON grupo_empresarial(prefixo_cnpj)
    """))

    mudancas.append("Índices criados/verificados")

    return mudancas

def fix_grupo_empresarial():
    """Executa correção completa"""

    app = create_app()

    with app.app_context():
        print("=" * 70)
        print("CORREÇÃO DA ESTRUTURA: grupo_empresarial")
        print("=" * 70)

        try:
            # Verificações iniciais
            colunas_atuais = verificar_estrutura_atual()
            constraints_atuais = verificar_constraints()
            indices_atuais = verificar_indices()
            count_dados = verificar_dados()

            # Verificar se precisa migrar
            precisa_migrar = (
                'tipo_grupo' in colunas_atuais or
                'info_grupo' in colunas_atuais or
                'prefixo_cnpj' not in colunas_atuais or
                'descricao' not in colunas_atuais
            )

            if not precisa_migrar:
                print("\n✅ Estrutura já está correta! Nada a fazer.")
                print("\nCOLUNAS ATUAIS:")
                for col in colunas_atuais:
                    print(f"   - {col}")
                return True

            # Confirmar migração
            print("\n" + "=" * 70)
            print("⚠️  MIGRAÇÃO NECESSÁRIA!")
            print("=" * 70)

            if count_dados > 0:
                print(f"\n❌ ATENÇÃO: Existem {count_dados} registros na tabela!")
                print("   A migração pode causar perda de dados.")
                print("   Recomendado fazer backup antes de continuar.")
                print("\nContinuar mesmo assim? (s/n): ", end='')
            else:
                print("\n✅ Tabela está vazia. Seguro para migrar.")
                print("\nContinuar? (s/n): ", end='')

            resposta = input().lower()
            if resposta != 's':
                print("\n❌ Migração cancelada pelo usuário.")
                return False

            # Executar migração
            print("\n" + "=" * 70)
            print("EXECUTANDO MIGRAÇÃO...")
            print("=" * 70)

            mudancas = []

            mudancas.extend(migrar_estrutura(colunas_atuais))
            mudancas.extend(ajustar_constraints_indices(constraints_atuais, indices_atuais))

            # Commit
            db.session.commit()

            # Verificar resultado final
            print("\n7. VERIFICANDO RESULTADO FINAL...")

            colunas_finais = verificar_estrutura_atual()
            constraints_finais = verificar_constraints()
            indices_finais = verificar_indices()

            # Resumo
            print("\n" + "=" * 70)
            print("✅ MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
            print("=" * 70)

            print("\nMUDANÇAS APLICADAS:")
            for i, mudanca in enumerate(mudancas, 1):
                print(f"   {i}. {mudanca}")

            print("\nESTRUTURA FINAL:")
            print("   Colunas:", len(colunas_finais))
            print("   Constraints:", len(constraints_finais))
            print("   Índices:", len(indices_finais))

            print("\n" + "=" * 70)
            print("PRÓXIMOS PASSOS:")
            print("=" * 70)
            print("1. Teste cadastrar um grupo empresarial na interface")
            print("2. Exemplo: Nome='Atacadao', Prefixos=['93209765', '73315333', '00063960']")
            print("3. Deve criar 3 linhas com mesmo nome_grupo mas prefixos diferentes")

            return True

        except Exception as e:
            db.session.rollback()
            print(f"\n❌ ERRO: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    fix_grupo_empresarial()

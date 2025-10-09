"""
Script para aumentar tamanho do campo numero_chassi no banco LOCAL
De: VARCHAR(17)
Para: VARCHAR(30)

Database: PostgreSQL/SQLite (Local)
Data: 06/10/2025
Motivo: Suportar variações de VIN com caracteres extras

COMO EXECUTAR:
    cd /home/rafaelnascimento/projetos/frete_sistema
    python app/motochefe/scripts/aumentar_chassi_local.py
"""

import sys
import os

# Adicionar path do projeto
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from app import create_app, db
from sqlalchemy import text, inspect


def verificar_estado_atual():
    """Verifica o estado atual da coluna numero_chassi"""
    print("\n" + "="*60)
    print("1. VERIFICANDO ESTADO ATUAL DA COLUNA")
    print("="*60)

    try:
        # Verificar estrutura da tabela
        inspector = inspect(db.engine)
        columns = inspector.get_columns('moto')

        chassi_col = next((col for col in columns if col['name'] == 'numero_chassi'), None)

        if chassi_col:
            print(f"✅ Coluna encontrada:")
            print(f"   - Nome: {chassi_col['name']}")
            print(f"   - Tipo: {chassi_col['type']}")
            print(f"   - Nullable: {chassi_col['nullable']}")

            # Verificar tamanho atual se for VARCHAR
            type_str = str(chassi_col['type'])
            if 'VARCHAR' in type_str.upper():
                print(f"   - Tamanho atual: {type_str}")
        else:
            print("❌ Coluna numero_chassi não encontrada!")
            return False

        # Verificar dados existentes
        result = db.session.execute(text("""
            SELECT
                MAX(LENGTH(numero_chassi)) as tamanho_maximo,
                MIN(LENGTH(numero_chassi)) as tamanho_minimo,
                COUNT(*) as total
            FROM moto
        """))

        row = result.fetchone()
        if row and row[2] > 0:
            print(f"\n📊 Dados existentes:")
            print(f"   - Total de motos: {row[2]}")
            print(f"   - Tamanho máximo de chassi: {row[0]} caracteres")
            print(f"   - Tamanho mínimo de chassi: {row[1]} caracteres")

            # Verificar se há chassi com mais de 17 caracteres
            result2 = db.session.execute(text("""
                SELECT numero_chassi, LENGTH(numero_chassi) as tamanho
                FROM moto
                WHERE LENGTH(numero_chassi) > 17
                ORDER BY LENGTH(numero_chassi) DESC
                LIMIT 5
            """))

            longos = result2.fetchall()
            if longos:
                print(f"\n⚠️  Chassi com mais de 17 caracteres encontrados:")
                for chassi, tamanho in longos:
                    print(f"   - {chassi} ({tamanho} chars)")
        else:
            print("\n📊 Nenhuma moto cadastrada ainda")

        return True

    except Exception as e:
        print(f"❌ Erro ao verificar estado atual: {e}")
        return False


def executar_alteracao():
    """Executa a alteração do tamanho da coluna"""
    print("\n" + "="*60)
    print("2. EXECUTANDO ALTERAÇÃO")
    print("="*60)

    try:
        # Detectar tipo de banco
        engine_name = db.engine.name
        print(f"🔧 Banco de dados detectado: {engine_name}")

        if engine_name == 'postgresql':
            # PostgreSQL
            sql = "ALTER TABLE transportadora_moto ALTER COLUMN telefone TYPE VARCHAR(50);"
            print(f"\n📝 SQL a executar (PostgreSQL):")
            print(f"   {sql}")

        elif engine_name == 'sqlite':
            # SQLite - não suporta ALTER COLUMN diretamente, mas permite tamanho flexível
            print("\n⚠️  SQLite detectado:")
            print("   SQLite não valida tamanho de VARCHAR, qualquer tamanho é aceito.")
            print("   Apenas atualize o modelo Python para db.String(30)")
            print("\n✅ Nenhuma alteração necessária no banco SQLite")
            return True

        else:
            print(f"⚠️  Banco {engine_name} não reconhecido")
            return False

        # Confirmar antes de executar
        print("\n⚠️  ATENÇÃO: Esta operação irá alterar a estrutura da tabela!")
        resposta = input("Deseja continuar? (sim/não): ").strip().lower()

        if resposta not in ['sim', 's', 'yes', 'y']:
            print("❌ Operação cancelada pelo usuário")
            return False

        # Executar ALTER TABLE
        db.session.execute(text(sql))
        db.session.commit()

        print("\n✅ Alteração executada com sucesso!")
        return True

    except Exception as e:
        db.session.rollback()
        print(f"\n❌ Erro ao executar alteração: {e}")
        return False


def verificar_resultado():
    """Verifica se a alteração foi aplicada corretamente"""
    print("\n" + "="*60)
    print("3. VERIFICANDO RESULTADO")
    print("="*60)

    try:
        inspector = inspect(db.engine)
        columns = inspector.get_columns('moto')

        chassi_col = next((col for col in columns if col['name'] == 'numero_chassi'), None)

        if chassi_col:
            type_str = str(chassi_col['type'])
            print(f"✅ Coluna atualizada:")
            print(f"   - Tipo: {type_str}")

            if '30' in type_str:
                print("\n🎉 SUCESSO! Coluna agora suporta até 30 caracteres")
            else:
                print("\n⚠️  Verificar se alteração foi aplicada corretamente")

        # Verificar integridade dos dados
        result = db.session.execute(text("SELECT COUNT(*) FROM moto"))
        total = result.fetchone()[0]
        print(f"\n📊 Integridade dos dados:")
        print(f"   - Total de motos: {total}")
        print(f"   - ✅ Todos os registros acessíveis")

        return True

    except Exception as e:
        print(f"❌ Erro ao verificar resultado: {e}")
        return False


def main():
    """Função principal"""
    print("\n" + "="*60)
    print("AUMENTAR TAMANHO DO CAMPO numero_chassi")
    print("De VARCHAR(17) para VARCHAR(30)")
    print("="*60)

    # Criar app Flask
    app = create_app()

    with app.app_context():
        # Passo 1: Verificar estado atual
        if not verificar_estado_atual():
            print("\n❌ Falha na verificação inicial. Abortando.")
            return

        # Passo 2: Executar alteração
        if not executar_alteracao():
            print("\n❌ Falha na execução da alteração. Abortando.")
            return

        # Passo 3: Verificar resultado
        if not verificar_resultado():
            print("\n⚠️  Verificação do resultado falhou")
            return

        print("\n" + "="*60)
        print("✅ PROCESSO CONCLUÍDO COM SUCESSO!")
        print("="*60)
        print("\n📝 PRÓXIMOS PASSOS:")
        print("   1. ✅ Modelo Python já atualizado para db.String(30)")
        print("   2. ✅ Validação de importação já atualizada para 30 chars")
        print("   3. 🔄 Executar script SQL no Render (se aplicável)")
        print("\n")


if __name__ == '__main__':
    main()

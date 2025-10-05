"""
Script para adicionar campo modelo_rejeitado na tabela moto
Executar: python3 -m app.motochefe.scripts.adicionar_campo_modelo_rejeitado
"""
from app import create_app, db
from sqlalchemy import text

def adicionar_campo_modelo_rejeitado():
    """Adiciona coluna modelo_rejeitado na tabela moto"""
    app = create_app()

    with app.app_context():
        try:
            # Verificar se a coluna já existe
            resultado = db.session.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='moto'
                AND column_name='modelo_rejeitado'
            """))

            existe = resultado.fetchone()

            if existe:
                print("✅ Coluna 'modelo_rejeitado' já existe na tabela 'moto'")
                return

            # Adicionar a coluna
            print("📝 Adicionando coluna 'modelo_rejeitado'...")
            db.session.execute(text("""
                ALTER TABLE moto
                ADD COLUMN modelo_rejeitado VARCHAR(100) NULL
            """))

            db.session.commit()
            print("✅ Coluna 'modelo_rejeitado' adicionada com sucesso!")

            # Criar índice para performance
            print("📝 Criando índice para busca rápida...")
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_moto_modelo_rejeitado
                ON moto(modelo_rejeitado)
                WHERE modelo_rejeitado IS NOT NULL
            """))

            db.session.commit()
            print("✅ Índice criado com sucesso!")

        except Exception as e:
            db.session.rollback()
            print(f"❌ Erro ao adicionar coluna: {str(e)}")
            raise

if __name__ == '__main__':
    adicionar_campo_modelo_rejeitado()

"""
Script para corrigir tamanho do campo tipo_pedido de VARCHAR(20) para VARCHAR(50)
Executar localmente com venv ativado

CONTEXTO:
- Campo l10n_br_tipo_pedido do Odoo Brasil tem valores com até 22 caracteres
- Valor que causou erro: 'serv-industrializacao' (22 chars)
- Outros valores grandes: 'compra-rec-ent-futura', 'importacao-transporte'

PROBLEMA:
- Campo tipo_pedido definido como VARCHAR(20) no banco
- Valor 'serv-industrializacao' (22 chars) causa erro de truncamento

SOLUÇÃO:
- Alterar para VARCHAR(50) para comportar TODOS os 38 tipos do Odoo Brasil

Executar com:
python3 scripts/migrations/fix_tipo_pedido_varchar_50.py
"""

import sys
import os

# Adicionar raiz do projeto ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text

def fix_tipo_pedido_length():
    """Altera tipo do campo tipo_pedido de VARCHAR(20) para VARCHAR(50)"""

    app = create_app()

    with app.app_context():
        try:
            # Verificar tipo atual
            print("🔍 Verificando tipo atual do campo...")
            result = db.session.execute(text("""
                SELECT column_name, data_type, character_maximum_length
                FROM information_schema.columns
                WHERE table_name = 'conhecimento_transporte'
                AND column_name = 'tipo_pedido'
            """))

            row = result.fetchone()
            if row:
                print(f"   Tipo atual: {row[1]}({row[2]})")
            else:
                print("   ⚠️  Campo tipo_pedido não encontrado!")
                return False

            # Verificar valores atuais na tabela
            print("\n📊 Verificando valores existentes...")
            result = db.session.execute(text("""
                SELECT DISTINCT tipo_pedido, LENGTH(tipo_pedido) as tamanho
                FROM conhecimento_transporte
                WHERE tipo_pedido IS NOT NULL
                ORDER BY tamanho DESC
                LIMIT 15
            """))

            print("   Valores encontrados (maiores primeiro):")
            valores = result.fetchall()
            if valores:
                for row in valores:
                    print(f"     '{row[0]}' ({row[1]} caracteres)")
            else:
                print("     (nenhum valor encontrado)")

            # Alterar para VARCHAR(50)
            print("\n🔧 Alterando tipo do campo para VARCHAR(50)...")
            db.session.execute(text("""
                ALTER TABLE conhecimento_transporte
                ALTER COLUMN tipo_pedido TYPE VARCHAR(50)
            """))

            db.session.commit()
            print("✅ Campo tipo_pedido alterado para VARCHAR(50) com sucesso!")

            # Verificar novamente
            print("\n🔍 Verificando tipo após alteração...")
            result = db.session.execute(text("""
                SELECT column_name, data_type, character_maximum_length
                FROM information_schema.columns
                WHERE table_name = 'conhecimento_transporte'
                AND column_name = 'tipo_pedido'
            """))

            row = result.fetchone()
            if row:
                print(f"   Tipo novo: {row[1]}({row[2]})")

            return True

        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Erro ao alterar campo: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    print("=" * 80)
    print("CORREÇÃO DE TAMANHO DO CAMPO tipo_pedido")
    print("=" * 80)
    print("\n📋 CONTEXTO:")
    print("   CTe DFe ID: 28699")
    print("   Chave: 35250950346989000168570010001053821030972112")
    print("   Tipo de Pedido: 'serv-industrializacao' (Serviço de Industrialização)")
    print("")
    print("🔍 O QUE É SERVIÇO DE INDUSTRIALIZAÇÃO?")
    print("   - NACOM envia matéria-prima (resina, tampas) para terceiro processar")
    print("   - Terceiro processa e transforma em produto acabado (frascos)")
    print("   - Terceiro devolve produto acabado para NACOM")
    print("   - CTe documenta esse transporte com tipo='serv-industrializacao'")
    print("")
    print("⚠️  PROBLEMA:")
    print("   - Campo atual: VARCHAR(20)")
    print("   - Valor tentado: 'serv-industrializacao' (22 caracteres)")
    print("   - Erro: value too long for type character varying(20)")
    print("")
    print("✅ SOLUÇÃO:")
    print("   - Alterar para VARCHAR(50)")
    print("   - Comporta TODOS os 38 tipos do Odoo Brasil (maior: 22 chars)")
    print("")
    print("=" * 80)

    resposta = input("\nDeseja prosseguir? (s/n): ")

    if resposta.lower() == 's':
        sucesso = fix_tipo_pedido_length()

        if sucesso:
            print("\n" + "=" * 80)
            print("✅ MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
            print("=" * 80)
            print("\n⚠️  AÇÃO NECESSÁRIA:")
            print("   Atualizar o modelo em app/fretes/models.py linha 541:")
            print("")
            print("   DE:  tipo_pedido = db.Column(db.String(20), nullable=True)")
            print("   PARA: tipo_pedido = db.Column(db.String(50), nullable=True)")
            print("")
            print("=" * 80)
        else:
            print("\n" + "=" * 80)
            print("❌ MIGRAÇÃO FALHOU - Verifique os erros acima")
            print("=" * 80)
    else:
        print("\n❌ Operação cancelada pelo usuário")

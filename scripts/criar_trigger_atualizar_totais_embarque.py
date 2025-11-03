"""
Script para criar trigger que atualiza automaticamente totais do embarque
quando EmbarqueItem for INSERT, UPDATE ou DELETE

✅ OBJETIVO:
- Garantir que embarque.pallet_total, embarque.peso_total e embarque.valor_total
  estejam sempre sincronizados com a soma dos itens ativos

✅ QUANDO EXECUTA:
- Após INSERT em embarque_itens
- Após UPDATE em embarque_itens (pallets, peso, valor ou status)
- Após DELETE em embarque_itens
"""
import sys
import os

# Adiciona o diretório raiz ao PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from sqlalchemy import text

def criar_trigger_atualizar_totais_embarque():
    app = create_app()

    with app.app_context():
        try:
            print("[INFO] Criando função trigger para atualizar totais do embarque...")

            # Cria a função trigger
            db.session.execute(text("""
                CREATE OR REPLACE FUNCTION atualizar_totais_embarque()
                RETURNS TRIGGER AS $$
                DECLARE
                    v_embarque_id INTEGER;
                BEGIN
                    -- Determina qual embarque_id atualizar
                    IF (TG_OP = 'DELETE') THEN
                        v_embarque_id := OLD.embarque_id;
                    ELSE
                        v_embarque_id := NEW.embarque_id;
                    END IF;

                    -- Atualiza totais do embarque com base nos itens ATIVOS
                    UPDATE embarques
                    SET
                        pallet_total = (
                            SELECT COALESCE(SUM(pallets), 0)
                            FROM embarque_itens
                            WHERE embarque_id = v_embarque_id
                            AND status = 'ativo'
                        ),
                        peso_total = (
                            SELECT COALESCE(SUM(peso), 0)
                            FROM embarque_itens
                            WHERE embarque_id = v_embarque_id
                            AND status = 'ativo'
                        ),
                        valor_total = (
                            SELECT COALESCE(SUM(valor), 0)
                            FROM embarque_itens
                            WHERE embarque_id = v_embarque_id
                            AND status = 'ativo'
                        )
                    WHERE id = v_embarque_id;

                    -- Log para debug
                    RAISE NOTICE 'Totais do embarque % atualizados via trigger', v_embarque_id;

                    RETURN NULL; -- Para trigger AFTER, o retorno é ignorado
                END;
                $$ LANGUAGE plpgsql;
            """))

            print("[INFO] ✅ Função trigger criada com sucesso!")

            # Remove trigger existente se houver
            print("[INFO] Removendo trigger antigo se existir...")
            db.session.execute(text("""
                DROP TRIGGER IF EXISTS trigger_atualizar_totais_embarque
                ON embarque_itens;
            """))

            # Cria o trigger
            print("[INFO] Criando trigger atualizar_totais_embarque...")
            db.session.execute(text("""
                CREATE TRIGGER trigger_atualizar_totais_embarque
                AFTER INSERT OR UPDATE OR DELETE ON embarque_itens
                FOR EACH ROW
                EXECUTE FUNCTION atualizar_totais_embarque();
            """))

            print("[INFO] ✅ Trigger criado com sucesso!")

            # Commit das mudanças
            db.session.commit()

            print("\n" + "="*70)
            print("✅ TRIGGER CRIADO COM SUCESSO!")
            print("="*70)
            print("\n📋 COMPORTAMENTO:")
            print("  - Ao inserir EmbarqueItem: Recalcula totais do embarque")
            print("  - Ao atualizar EmbarqueItem: Recalcula totais do embarque")
            print("  - Ao deletar EmbarqueItem: Recalcula totais do embarque")
            print("  - Considera APENAS itens com status='ativo'")
            print("\n💡 CAMPOS ATUALIZADOS AUTOMATICAMENTE:")
            print("  - embarque.pallet_total")
            print("  - embarque.peso_total")
            print("  - embarque.valor_total")
            print("\n🔍 TESTE O TRIGGER:")
            print("  1. Atualize pallets de um EmbarqueItem")
            print("  2. Consulte embarque.pallet_total - deve refletir a mudança")
            print("="*70)

        except Exception as e:
            db.session.rollback()
            print(f"\n❌ ERRO ao criar trigger: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    return True

if __name__ == '__main__':
    sucesso = criar_trigger_atualizar_totais_embarque()
    sys.exit(0 if sucesso else 1)

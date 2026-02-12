"""
Script de Migração - Configurações de Equipe de Vendas
Sistema MotoCHEFE

Adiciona campos de configuração em equipe_vendas_moto:
1. Responsável Movimentação (NACOM)
2. Tipo de Comissão (FIXA_EXCEDENTE ou PERCENTUAL)
3. Valores de comissão
4. Controle de rateio

Também torna equipe_vendas_id obrigatório em vendedor_moto
E remove responsavel_movimentacao de pedido_venda_moto

Uso:
    python app/motochefe/scripts/migrar_config_equipe_vendas.py
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from app import create_app, db
from sqlalchemy import text
from datetime import datetime
from app.utils.timezone import agora_utc_naive


def adicionar_campos_equipe_vendas():
    """Adiciona campos de configuração na tabela equipe_vendas_moto"""
    print("\n🔍 Adicionando campos em equipe_vendas_moto...")

    sql = text("""
    -- Configuração de Movimentação
    ALTER TABLE equipe_vendas_moto
    ADD COLUMN IF NOT EXISTS responsavel_movimentacao VARCHAR(20);

    -- Configuração de Comissão
    ALTER TABLE equipe_vendas_moto
    ADD COLUMN IF NOT EXISTS tipo_comissao VARCHAR(20) DEFAULT 'FIXA_EXCEDENTE' NOT NULL;

    ALTER TABLE equipe_vendas_moto
    ADD COLUMN IF NOT EXISTS valor_comissao_fixa NUMERIC(15, 2) DEFAULT 0 NOT NULL;

    ALTER TABLE equipe_vendas_moto
    ADD COLUMN IF NOT EXISTS percentual_comissao NUMERIC(5, 2) DEFAULT 0 NOT NULL;

    ALTER TABLE equipe_vendas_moto
    ADD COLUMN IF NOT EXISTS comissao_rateada BOOLEAN DEFAULT TRUE NOT NULL;

    -- Comentários
    COMMENT ON COLUMN equipe_vendas_moto.responsavel_movimentacao
        IS 'Responsável pela movimentação: NACOM';

    COMMENT ON COLUMN equipe_vendas_moto.tipo_comissao
        IS 'Tipo de comissão: FIXA_EXCEDENTE ou PERCENTUAL';

    COMMENT ON COLUMN equipe_vendas_moto.valor_comissao_fixa
        IS 'Valor fixo da comissão (usado em FIXA_EXCEDENTE)';

    COMMENT ON COLUMN equipe_vendas_moto.percentual_comissao
        IS 'Percentual da comissão sobre venda (usado em PERCENTUAL). Ex: 5.00 = 5%';

    COMMENT ON COLUMN equipe_vendas_moto.comissao_rateada
        IS 'TRUE: divide entre todos vendedores da equipe. FALSE: apenas vendedor do pedido';
    """)

    db.session.execute(sql)
    db.session.commit()
    print("   ✅ Campos adicionados em equipe_vendas_moto!")


def tornar_equipe_obrigatoria_vendedor():
    """Torna equipe_vendas_id obrigatório em vendedor_moto"""
    print("\n🔍 Tornando equipe_vendas_id obrigatório em vendedor_moto...")

    # Primeiro verificar se há vendedores sem equipe
    resultado = db.session.execute(text("""
        SELECT COUNT(*) FROM vendedor_moto WHERE equipe_vendas_id IS NULL
    """))
    qtd_sem_equipe = resultado.scalar()

    if qtd_sem_equipe > 0:
        print(f"   ⚠️  ATENÇÃO: Existem {qtd_sem_equipe} vendedores SEM equipe!")
        print("   ⚠️  Defina uma equipe para estes vendedores antes de prosseguir.")
        print("   ⚠️  Pulando esta alteração...")
        return False

    sql = text("""
    ALTER TABLE vendedor_moto
    ALTER COLUMN equipe_vendas_id SET NOT NULL;

    CREATE INDEX IF NOT EXISTS idx_vendedor_equipe ON vendedor_moto(equipe_vendas_id);

    COMMENT ON COLUMN vendedor_moto.equipe_vendas_id
        IS 'Equipe do vendedor (OBRIGATÓRIO - todo vendedor DEVE ter equipe)';
    """)

    db.session.execute(sql)
    db.session.commit()
    print("   ✅ equipe_vendas_id agora é obrigatório!")
    return True


def remover_responsavel_movimentacao_pedido():
    """Remove campo responsavel_movimentacao de pedido_venda_moto"""
    print("\n🔍 Removendo responsavel_movimentacao de pedido_venda_moto...")

    # Verificar se há pedidos usando este campo
    resultado = db.session.execute(text("""
        SELECT COUNT(*) FROM pedido_venda_moto
        WHERE responsavel_movimentacao IS NOT NULL
    """))
    qtd_com_valor = resultado.scalar()

    if qtd_com_valor > 0:
        print(f"   ⚠️  ATENÇÃO: {qtd_com_valor} pedidos possuem responsavel_movimentacao preenchido")
        print("   ⚠️  Estes valores serão perdidos ao remover a coluna")
        resposta = input("   ❓ Deseja continuar? (s/N): ")
        if resposta.lower() != 's':
            print("   ⚠️  Operação cancelada")
            return False

    sql = text("""
    ALTER TABLE pedido_venda_moto
    DROP COLUMN IF EXISTS responsavel_movimentacao;
    """)

    db.session.execute(sql)
    db.session.commit()
    print("   ✅ Campo responsavel_movimentacao removido de pedido_venda_moto!")
    return True


def verificar_resultado():
    """Verifica se as alterações foram aplicadas"""
    print("\n🔍 VERIFICAÇÃO FINAL...")

    print("\n   📋 Campos em equipe_vendas_moto:")
    sql = text("""
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_name = 'equipe_vendas_moto'
        AND column_name IN (
            'responsavel_movimentacao',
            'tipo_comissao',
            'valor_comissao_fixa',
            'percentual_comissao',
            'comissao_rateada'
        )
        ORDER BY ordinal_position;
    """)
    resultado = db.session.execute(sql)
    campos_equipe = resultado.fetchall()

    if campos_equipe:
        for campo in campos_equipe:
            print(f"      ✅ {campo[0]:30} | {campo[1]:20} | Nullable: {campo[2]:3} | Default: {campo[3]}")
    else:
        print("      ⚠️  Nenhum campo encontrado!")

    print("\n   📋 Campo equipe_vendas_id em vendedor_moto:")
    sql = text("""
        SELECT column_name, is_nullable
        FROM information_schema.columns
        WHERE table_name = 'vendedor_moto'
        AND column_name = 'equipe_vendas_id';
    """)
    resultado = db.session.execute(sql)
    campo_vendedor = resultado.fetchone()

    if campo_vendedor:
        nullable = campo_vendedor[1]
        if nullable == 'NO':
            print(f"      ✅ equipe_vendas_id: NOT NULL (obrigatório)")
        else:
            print(f"      ⚠️  equipe_vendas_id: NULL (ainda não está obrigatório)")

    print("\n   📋 Verificando remoção de responsavel_movimentacao em pedido_venda_moto:")
    sql = text("""
        SELECT COUNT(*) FROM information_schema.columns
        WHERE table_name = 'pedido_venda_moto'
        AND column_name = 'responsavel_movimentacao';
    """)
    resultado = db.session.execute(sql)
    existe = resultado.scalar()

    if existe == 0:
        print(f"      ✅ Campo responsavel_movimentacao removido com sucesso")
    else:
        print(f"      ⚠️  Campo responsavel_movimentacao ainda existe")


def main():
    """Executa todas as migrações"""
    print("=" * 80)
    print("🔧 MIGRAÇÃO: CONFIGURAÇÕES DE EQUIPE DE VENDAS - SISTEMA MOTOCHEFE")
    print("=" * 80)
    print(f"📅 Data: {agora_utc_naive().strftime('%d/%m/%Y %H:%M:%S')}")
    print("=" * 80)
    print("\n📝 ALTERAÇÕES:")
    print("   1. Adicionar campos de configuração em equipe_vendas_moto")
    print("   2. Tornar equipe_vendas_id obrigatório em vendedor_moto")
    print("   3. Remover responsavel_movimentacao de pedido_venda_moto")
    print("=" * 80)

    app = create_app()

    with app.app_context():
        try:
            # Executar migrações
            adicionar_campos_equipe_vendas()
            tornar_equipe_obrigatoria_vendedor()
            remover_responsavel_movimentacao_pedido()

            # Verificação final
            verificar_resultado()

            print("\n" + "=" * 80)
            print("✅ MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
            print("=" * 80)
            print("\n📊 RESUMO:")
            print("   1. ✅ Campos de configuração adicionados em EquipeVendasMoto")
            print("   2. ✅ equipe_vendas_id agora é obrigatório em VendedorMoto")
            print("   3. ✅ responsavel_movimentacao removido de PedidoVendaMoto")
            print("\n⚠️  PRÓXIMOS PASSOS:")
            print("   1. Reiniciar servidor Flask (se estiver rodando)")
            print("   2. Configurar cada equipe de vendas com suas regras")
            print("   3. Testar criação de vendedor (deve exigir equipe)")
            print("   4. Testar criação de pedido (número sequencial + sem movimentação)")
            print("\n")

        except Exception as e:
            print("\n" + "=" * 80)
            print(f"❌ ERRO NA MIGRAÇÃO: {e}")
            print("=" * 80)
            import traceback
            traceback.print_exc()
            db.session.rollback()
            raise


if __name__ == '__main__':
    main()

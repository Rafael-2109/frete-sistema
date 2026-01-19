"""
Migration: Adicionar equipe_vendas na VIEW pedidos
Data: 2026-01-19
Descrição: Altera a VIEW pedidos para incluir campo equipe_vendas via JOIN com carteira_principal

Executar: python scripts/migrations/add_equipe_vendas_view_pedidos.py
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def atualizar_view_pedidos():
    """Atualiza a VIEW pedidos para incluir equipe_vendas"""
    app = create_app()
    with app.app_context():
        try:
            print("🔄 Atualizando VIEW pedidos para incluir equipe_vendas...")

            # DROP e CREATE da VIEW com novo campo
            sql = text("""
                DROP VIEW IF EXISTS pedidos;

                CREATE VIEW pedidos AS
                SELECT
                    abs((('x'::text || substr(md5(s.separacao_lote_id::text), 1, 8)))::bit(32)::integer) AS id,
                    s.separacao_lote_id,
                    min(s.num_pedido::text) AS num_pedido,
                    min(s.data_pedido) AS data_pedido,
                    min(s.cnpj_cpf::text) AS cnpj_cpf,
                    min(s.raz_social_red::text) AS raz_social_red,
                    min(s.nome_cidade::text) AS nome_cidade,
                    min(s.cod_uf::text) AS cod_uf,
                    min(s.cidade_normalizada::text) AS cidade_normalizada,
                    min(s.uf_normalizada::text) AS uf_normalizada,
                    min(s.codigo_ibge::text) AS codigo_ibge,
                    COALESCE(sum(s.valor_saldo), 0::double precision) AS valor_saldo_total,
                    COALESCE(sum(s.pallet), 0::double precision) AS pallet_total,
                    COALESCE(sum(s.peso), 0::double precision) AS peso_total,
                    min(s.rota::text) AS rota,
                    min(s.sub_rota::text) AS sub_rota,
                    min(s.observ_ped_1::text) AS observ_ped_1,
                    min(s.roteirizacao::text) AS roteirizacao,
                    min(s.expedicao) AS expedicao,
                    min(s.agendamento) AS agendamento,
                    min(s.protocolo::text) AS protocolo,
                    bool_or(s.agendamento_confirmado) AS agendamento_confirmado,
                    NULL::character varying(100) AS transportadora,
                    NULL::double precision AS valor_frete,
                    NULL::double precision AS valor_por_kg,
                    NULL::character varying(100) AS nome_tabela,
                    NULL::character varying(50) AS modalidade,
                    NULL::character varying(100) AS melhor_opcao,
                    NULL::double precision AS valor_melhor_opcao,
                    NULL::integer AS lead_time,
                    min(s.data_embarque) AS data_embarque,
                    min(s.numero_nf::text) AS nf,
                    min(s.status::text) AS status,
                    bool_or(s.nf_cd) AS nf_cd,
                    min(s.pedido_cliente::text) AS pedido_cliente,
                    bool_or(s.separacao_impressa) AS separacao_impressa,
                    min(s.separacao_impressa_em) AS separacao_impressa_em,
                    min(s.separacao_impressa_por::text) AS separacao_impressa_por,
                    min(s.cotacao_id) AS cotacao_id,
                    NULL::integer AS usuario_id,
                    min(s.criado_em) AS criado_em,
                    -- 🆕 NOVO CAMPO: equipe_vendas via JOIN com carteira_principal
                    min(cp.equipe_vendas::text) AS equipe_vendas
                FROM separacao s
                LEFT JOIN carteira_principal cp
                    ON s.num_pedido = cp.num_pedido
                    AND s.cod_produto = cp.cod_produto
                WHERE s.separacao_lote_id IS NOT NULL
                    AND s.status::text <> 'PREVISAO'::text
                GROUP BY s.separacao_lote_id;
            """)

            db.session.execute(sql)
            db.session.commit()

            print("✅ VIEW pedidos atualizada com sucesso!")
            print("   → Campo equipe_vendas adicionado via JOIN com carteira_principal")

            # Verificar se o campo foi adicionado
            verificar = text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'pedidos' AND column_name = 'equipe_vendas';
            """)
            result = db.session.execute(verificar).fetchone()

            if result:
                print("✅ Campo equipe_vendas verificado na VIEW!")
            else:
                print("❌ ERRO: Campo equipe_vendas não encontrado na VIEW!")
                return False

            return True

        except Exception as e:
            print(f"❌ Erro ao atualizar VIEW: {e}")
            db.session.rollback()
            return False


if __name__ == '__main__':
    sucesso = atualizar_view_pedidos()
    sys.exit(0 if sucesso else 1)

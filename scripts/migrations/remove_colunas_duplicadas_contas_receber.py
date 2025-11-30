"""
Script para remover colunas duplicadas da tabela contas_a_receber
Esses dados serão obtidos dinamicamente via relacionamentos

Data: 28/11/2025

Colunas a remover:
- data_entrega_prevista (via entrega_monitorada.data_entrega_prevista)
- data_hora_entrega_realizada (via entrega_monitorada.data_hora_entrega_realizada)
- status_finalizacao (via entrega_monitorada.status_finalizacao)
- nova_nf (via entrega_monitorada.nova_nf)
- reagendar (via entrega_monitorada.reagendar)
- data_embarque (via entrega_monitorada.data_embarque)
- transportadora (via entrega_monitorada.transportadora)
- vendedor (via entrega_monitorada.vendedor)
- canhoto_arquivo (via entrega_monitorada.canhoto_arquivo)
- ultimo_agendamento_data (via entrega_monitorada.agendamentos)
- ultimo_agendamento_status (via entrega_monitorada.agendamentos)
- ultimo_agendamento_protocolo (via entrega_monitorada.agendamentos)
- nf_cd (via entrega_monitorada.nf_cd)
- nf_cancelada (via FaturamentoProduto.status_nf = 'Cancelado')
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def remover_colunas_duplicadas():
    app = create_app()

    colunas_para_remover = [
        'data_entrega_prevista',
        'data_hora_entrega_realizada',
        'status_finalizacao',
        'nova_nf',
        'reagendar',
        'data_embarque',
        'transportadora',
        'vendedor',
        'canhoto_arquivo',
        'ultimo_agendamento_data',
        'ultimo_agendamento_status',
        'ultimo_agendamento_protocolo',
        'nf_cd',
        'nf_cancelada'  # Agora obtido via FaturamentoProduto.status_nf = 'Cancelado'
    ]

    with app.app_context():
        try:
            for coluna in colunas_para_remover:
                # Verificar se a coluna existe
                resultado = db.session.execute(text(f"""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = 'contas_a_receber'
                    AND column_name = '{coluna}'
                """))

                if resultado.fetchone():
                    db.session.execute(text(f"""
                        ALTER TABLE contas_a_receber
                        DROP COLUMN {coluna}
                    """))
                    print(f"✅ Coluna '{coluna}' removida com sucesso!")
                else:
                    print(f"⚠️ Coluna '{coluna}' não existe na tabela")

            db.session.commit()
            print("\n✅ Todas as colunas duplicadas foram removidas!")
            return True

        except Exception as e:
            db.session.rollback()
            print(f"❌ Erro ao remover colunas: {str(e)}")
            return False


# SQL para rodar no Shell do Render:
"""
ALTER TABLE contas_a_receber DROP COLUMN IF EXISTS data_entrega_prevista;
ALTER TABLE contas_a_receber DROP COLUMN IF EXISTS data_hora_entrega_realizada;
ALTER TABLE contas_a_receber DROP COLUMN IF EXISTS status_finalizacao;
ALTER TABLE contas_a_receber DROP COLUMN IF EXISTS nova_nf;
ALTER TABLE contas_a_receber DROP COLUMN IF EXISTS reagendar;
ALTER TABLE contas_a_receber DROP COLUMN IF EXISTS data_embarque;
ALTER TABLE contas_a_receber DROP COLUMN IF EXISTS transportadora;
ALTER TABLE contas_a_receber DROP COLUMN IF EXISTS vendedor;
ALTER TABLE contas_a_receber DROP COLUMN IF EXISTS canhoto_arquivo;
ALTER TABLE contas_a_receber DROP COLUMN IF EXISTS ultimo_agendamento_data;
ALTER TABLE contas_a_receber DROP COLUMN IF EXISTS ultimo_agendamento_status;
ALTER TABLE contas_a_receber DROP COLUMN IF EXISTS ultimo_agendamento_protocolo;
ALTER TABLE contas_a_receber DROP COLUMN IF EXISTS nf_cd;
ALTER TABLE contas_a_receber DROP COLUMN IF EXISTS nf_cancelada;
"""


if __name__ == '__main__':
    remover_colunas_duplicadas()

"""Migration HORA 22: limpa HoraVenda do backfill TagPlus que ficou sem itens.

Contexto: o primeiro backfill (commit 06fee87a anterior) criou 10 vendas com
qtd_itens=0 porque o regex de extracao de chassi nao reconhecia o formato
das NFs historicas TagPlus (campo `item.detalhes` vinha vazio).

O fix do parser exige reprocessar essas NFs, mas a idempotencia por
chave_44 bloqueia novo import (cai em NfeJaImportada).

Esta data-fix limpa SO as vendas vazias para liberar reprocessamento:

  CRITERIO: origem_criacao='TAGPLUS_API'
            E NOT EXISTS (SELECT 1 FROM hora_venda_item WHERE venda_id=v.id)

Vendas com itens ja criados (backfill bem-sucedido) NAO sao tocadas.

Idempotente: roda 2x sem efeito na 2a — na 1a apaga as vazias, na 2a o
SELECT retorna 0 e nada e feito. Seguro para deixar permanente em build.sh.

Apaga em ordem (FKs):
  1. hora_venda_auditoria   (FK venda_id)
  2. hora_venda_divergencia (FK venda_id)
  3. hora_venda             (a propria)
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db  # noqa: E402


SQL_LISTAR = """
SELECT v.id, v.nf_saida_numero, v.nf_saida_chave_44,
       v.nome_cliente, v.valor_total
  FROM hora_venda v
 WHERE v.origem_criacao = 'TAGPLUS_API'
   AND NOT EXISTS (SELECT 1 FROM hora_venda_item i WHERE i.venda_id = v.id)
 ORDER BY v.id
"""

SQL_DEL_AUDIT = """
DELETE FROM hora_venda_auditoria
 WHERE venda_id IN (
    SELECT v.id FROM hora_venda v
     WHERE v.origem_criacao = 'TAGPLUS_API'
       AND NOT EXISTS (SELECT 1 FROM hora_venda_item i WHERE i.venda_id = v.id)
 )
"""

SQL_DEL_DIV = """
DELETE FROM hora_venda_divergencia
 WHERE venda_id IN (
    SELECT v.id FROM hora_venda v
     WHERE v.origem_criacao = 'TAGPLUS_API'
       AND NOT EXISTS (SELECT 1 FROM hora_venda_item i WHERE i.venda_id = v.id)
 )
"""

SQL_DEL_VENDA = """
DELETE FROM hora_venda v
 WHERE v.origem_criacao = 'TAGPLUS_API'
   AND NOT EXISTS (SELECT 1 FROM hora_venda_item i WHERE i.venda_id = v.id)
"""


def main() -> int:
    app = create_app()
    with app.app_context():
        # Verifica que a tabela existe (no-op se modulo HORA ainda nao foi
        # provisionado).
        existe = db.session.execute(db.text(
            "SELECT 1 FROM information_schema.tables WHERE table_name='hora_venda'"
        )).scalar()
        if not existe:
            print('hora_22: tabela hora_venda nao existe, nada a fazer.')
            return 0

        candidatas = db.session.execute(db.text(SQL_LISTAR)).fetchall()
        n = len(candidatas)
        if n == 0:
            print('hora_22: nenhuma venda backfill vazia — no-op.')
            return 0

        print(f'hora_22: {n} venda(s) TAGPLUS_API sem itens encontrada(s):')
        for row in candidatas:
            print(
                f'  - venda_id={row.id}  NF={row.nf_saida_numero}  '
                f'chave={row.nf_saida_chave_44}  cliente={row.nome_cliente}  '
                f'valor=R${row.valor_total}'
            )

        n_audit = db.session.execute(db.text(SQL_DEL_AUDIT)).rowcount
        n_div = db.session.execute(db.text(SQL_DEL_DIV)).rowcount
        n_venda = db.session.execute(db.text(SQL_DEL_VENDA)).rowcount
        db.session.commit()

        print(
            f'hora_22: removidas — '
            f'venda={n_venda}, divergencia={n_div}, auditoria={n_audit}'
        )
        if n_venda != n:
            print(
                f'[ATENCAO] esperado apagar {n} vendas, apagado {n_venda} '
                f'— investigar.'
            )
            return 1
        return 0


if __name__ == '__main__':
    sys.exit(main())

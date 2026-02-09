**OK****OK** 1- Ao alterar um pedido de compras, o sistema precisa revalida-lo nas telas de Status NF x PO + Divergencia NF x PO através de algum gatilho automatico / botão.
**OK****OK** 2- Acrescentar filtro de nome de produto + fornecedor em todas as telas que não houverem.
**OK****OK** 3- Acrescentar pesquisa por pedido de compras na tela de Status NF x PO.
**OK****OK** 4- Acrescentar recurso para poder escolher o pedido a ser "Conciliado" (integrado)
**OK****OK****OK** 5- Acrescentar link para Odoo no modal em Divergencia NF x PO.
**OK****OK****OK**6- Adicionar coluna de PO origem(N PO - 1 NF).
**OK****OK** 7- Priorizar integrar com o PO original sempre que possivel.
**OK****OK** 8- Reversão de integração - Voltar os pedidos ao original e desvincular a NF do PO + remover PO do DFe.
9- Picking com erro.
10- Link para Odoo no picking com erro.
11- Criar tela por data necessaria de compra
 Erro: (raised as a result of Query-invoked autoflush; consider using a session.no_autoflush block if this flush is occurring prematurely) (psycopg2.errors.StringDataRightTruncation) value too long for type character varying(100) [SQL: UPDATE picking_recebimento SET origin=%(origin)s, write_date=%(write_date)s, location_id=%(location_id)s, sincronizado_em=%(sincronizado_em)s, atualizado_em=%(atualizado_em)s WHERE picking_recebimento.id = %(picking_recebimento_id)s] [parameters: {'origin': 'Devolução de CD/CD/PALLET/00061, CD/CD/PALLET/00062, CD/CD/PALLET/00065, CD/CD/PALLET/00077, CD/CD/PALLET/00101...', 'write_date': datetime.datetime(2026, 2, 6, 21, 19, 39), 'location_id': 5, 'sincronizado_em': datetime.datetime(2026, 2, 9, 22, 28, 12, 726548), 'atualizado_em': datetime.datetime(2026, 2, 9, 22, 28, 12, 726552), 'picking_recebimento_id': 631}] (Background on this error at: https://sqlalche.me/e/20/9h9h)
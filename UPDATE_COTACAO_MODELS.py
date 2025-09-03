# APÓS A MIGRAÇÃO, APLICAR ESTAS MUDANÇAS EM app/cotacao/models.py

# LINHA 60 - MUDAR DE:
#     pedido_id = db.Column(db.Integer, db.ForeignKey('pedidos.id'), nullable=False)

# PARA:
#     separacao_lote_id = db.Column(db.String(50), nullable=False, index=True)
#     pedido_id_old = db.Column(db.Integer)  # Manter temporariamente para backup

# E adicionar property para compatibilidade:
#     @property
#     def pedido_id(self):
#         """Compatibilidade: retorna ID do pedido baseado em separacao_lote_id"""
#         if self.separacao_lote_id:
#             pedido = db.session.execute(
#                 db.text("SELECT id FROM pedidos WHERE separacao_lote_id = :lote"),
#                 {"lote": self.separacao_lote_id}
#             ).first()
#             return pedido[0] if pedido else None
#         return self.pedido_id_old
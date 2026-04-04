"""
Modelo EventoSupplyChain — tabela de eventos imutavel (append-only)
para auditoria e event sourcing de supply chain.

IMPORTANTE: Este modelo e READ-ONLY no Python. As escritas sao feitas
exclusivamente pelo trigger PostgreSQL audit_supply_chain_trigger().
O unico UPDATE permitido e para enriquecer qtd_projetada_dia via
enrichment_service.py.
"""
from app import db
from sqlalchemy.dialects.postgresql import JSONB, ARRAY


class EventoSupplyChain(db.Model):
    __tablename__ = 'evento_supply_chain'

    id                  = db.Column(db.BigInteger, primary_key=True)

    # Evento
    tipo_evento         = db.Column(db.String(10), nullable=False)   # INSERT, UPDATE, DELETE
    entidade            = db.Column(db.String(30), nullable=False)   # carteira, separacao, faturamento, movimentacao, producao, compra
    entidade_id         = db.Column(db.Integer)                      # PK do registro afetado

    # Campos de negocio desnormalizados (query direta sem parsear JSONB)
    num_pedido          = db.Column(db.String(50))
    cod_produto         = db.Column(db.String(50))
    numero_nf           = db.Column(db.String(20))
    separacao_lote_id   = db.Column(db.String(50))

    # Quantidade (campo principal de cada entidade)
    quantidade_anterior = db.Column(db.Numeric(15, 3))   # OLD.qtd_* (NULL em INSERT)
    quantidade_nova     = db.Column(db.Numeric(15, 3))   # NEW.qtd_* (NULL em DELETE)

    # Projecao de estoque (preenchido por Python pos-commit)
    qtd_projetada_dia   = db.Column(db.Numeric(15, 3))

    # Snapshot completo
    dados_antes         = db.Column(JSONB)               # row_to_json(OLD) — NULL em INSERT
    dados_depois        = db.Column(JSONB)               # row_to_json(NEW) — NULL em DELETE
    campos_alterados    = db.Column(ARRAY(db.Text))      # Lista de campos que mudaram (so UPDATE)

    # Contexto
    origem              = db.Column(db.String(50))       # SYNC_ODOO, USUARIO, SISTEMA, UPLOAD_EXCEL
    session_id          = db.Column(db.String(100))      # Correlaciona eventos de um mesmo sync
    registrado_em       = db.Column(db.DateTime, nullable=False)
    registrado_por      = db.Column(db.String(100))      # Usuario ou 'SISTEMA'

    # Indices definidos no SQL de migracao (nao duplicar aqui)
    # O SQLAlchemy detecta a tabela via metadata para Flask-Migrate

    def __repr__(self):
        return (
            f'<EventoSC {self.tipo_evento} {self.entidade} '
            f'pedido={self.num_pedido} produto={self.cod_produto}>'
        )

    def to_dict(self, include_snapshots=False):
        result = {
            'id': self.id,
            'tipo_evento': self.tipo_evento,
            'entidade': self.entidade,
            'entidade_id': self.entidade_id,
            'num_pedido': self.num_pedido,
            'cod_produto': self.cod_produto,
            'numero_nf': self.numero_nf,
            'separacao_lote_id': self.separacao_lote_id,
            'quantidade_anterior': float(self.quantidade_anterior) if self.quantidade_anterior is not None else None,
            'quantidade_nova': float(self.quantidade_nova) if self.quantidade_nova is not None else None,
            'qtd_projetada_dia': float(self.qtd_projetada_dia) if self.qtd_projetada_dia is not None else None,
            'campos_alterados': self.campos_alterados,
            'origem': self.origem,
            'session_id': self.session_id,
            'registrado_em': self.registrado_em.strftime('%d/%m/%Y %H:%M:%S') if self.registrado_em else None,
            'registrado_por': self.registrado_por,
        }
        if include_snapshots:
            result['dados_antes'] = self.dados_antes
            result['dados_depois'] = self.dados_depois
        return result

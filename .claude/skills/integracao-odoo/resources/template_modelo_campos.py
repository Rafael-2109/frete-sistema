"""
TEMPLATE: Campos para Modelo com Integração Odoo
=================================================

Copie estes campos para seu modelo SQLAlchemy.

Arquivos de referência:
- app/fretes/models.py - DespesaExtra
- app/fretes/models.py - Frete
"""

from datetime import datetime
from app import db


# ================================================================
# CAMPOS OBRIGATÓRIOS PARA INTEGRAÇÃO ODOO
# ================================================================

# Copie estes campos para dentro da sua classe Model:

class SeuModelo(db.Model):
    """Seu modelo com suporte a integração Odoo"""

    __tablename__ = 'sua_tabela'

    id = db.Column(db.Integer, primary_key=True)

    # ... seus campos existentes ...

    # ================================================
    # STATUS (obrigatório)
    # ================================================
    # Valores: PENDENTE, VINCULADO_CTE, LANCADO_ODOO, LANCADO, CANCELADO
    STATUS_CHOICES = ['PENDENTE', 'VINCULADO_CTE', 'LANCADO_ODOO', 'LANCADO', 'CANCELADO']
    status = db.Column(db.String(20), default='PENDENTE', nullable=False, index=True)

    # ================================================
    # VÍNCULO COM CTe (se aplicável)
    # ================================================
    # Use quando o lançamento é baseado em um CTe específico
    cte_id = db.Column(db.Integer, db.ForeignKey('conhecimento_transporte.id'), nullable=True, index=True)
    chave_cte = db.Column(db.String(44), nullable=True, index=True)  # Facilita buscas

    # ================================================
    # INTEGRAÇÃO ODOO (obrigatório)
    # ================================================
    odoo_dfe_id = db.Column(db.Integer, nullable=True, index=True)       # ID do DFe no Odoo
    odoo_purchase_order_id = db.Column(db.Integer, nullable=True)        # ID do PO no Odoo
    odoo_invoice_id = db.Column(db.Integer, nullable=True)               # ID da Invoice no Odoo
    lancado_odoo_em = db.Column(db.DateTime, nullable=True)              # Data/hora lançamento
    lancado_odoo_por = db.Column(db.String(100), nullable=True)          # Usuário que lançou

    # ================================================
    # RELACIONAMENTOS
    # ================================================
    cte = db.relationship('ConhecimentoTransporte', foreign_keys=[cte_id], backref='seus_registros')

    # ================================================
    # PROPERTIES ÚTEIS
    # ================================================

    @property
    def pode_lancar_odoo(self):
        """Verifica se pode ser lançado no Odoo"""
        return (
            self.cte_id is not None and
            self.status == 'VINCULADO_CTE'  # Ajustar conforme regra de negócio
        )

    @property
    def status_descricao(self):
        """Retorna descrição amigável do status"""
        descricoes = {
            'PENDENTE': 'Pendente',
            'VINCULADO_CTE': 'CTe Vinculado',
            'LANCADO_ODOO': 'Lançado no Odoo',
            'LANCADO': 'Lançado',
            'CANCELADO': 'Cancelado'
        }
        return descricoes.get(self.status, self.status)

    def __repr__(self):
        return f'<SeuModelo #{self.id} - {self.status}>'


# ================================================================
# EXEMPLO DE DOCUMENTAÇÃO PARA CLAUDE.md
# ================================================================

DOCUMENTACAO_CLAUDE_MD = """
## SeuModelo (app/seu_modulo/models.py)

### Modelo com suporte a integração Odoo

### ⚠️ REGRAS DE STATUS:
- **PENDENTE**: Criado, aguardando processamento
- **VINCULADO_CTE**: CTe vinculado, pronto para Odoo
- **LANCADO_ODOO**: Lançado com sucesso no Odoo (16 etapas)
- **LANCADO**: Finalizado sem Odoo
- **CANCELADO**: Cancelado

### 📋 Campos de Integração Odoo
```python
# STATUS:
status = db.Column(db.String(20), default='PENDENTE', nullable=False, index=True)

# VÍNCULO CTe:
cte_id = db.Column(db.Integer, db.ForeignKey('conhecimento_transporte.id'), nullable=True, index=True)
chave_cte = db.Column(db.String(44), nullable=True, index=True)

# INTEGRAÇÃO ODOO:
odoo_dfe_id = db.Column(db.Integer, nullable=True, index=True)
odoo_purchase_order_id = db.Column(db.Integer, nullable=True)
odoo_invoice_id = db.Column(db.Integer, nullable=True)
lancado_odoo_em = db.Column(db.DateTime, nullable=True)
lancado_odoo_por = db.Column(db.String(100), nullable=True)
```
"""

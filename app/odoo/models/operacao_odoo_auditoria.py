"""Model OperacaoOdooAuditoria — auditoria polimorfica de operacoes Odoo.

Substitui o padrao fretes-especifico (LancamentoFreteOdooAuditoria em
app/fretes/models.py:1047-1134) por uma tabela polimorfica que pode
auditar qualquer operacao Odoo (account.move, stock.picking, stock.lot, etc).

Spec: docs/superpowers/specs/2026-05-17-ajuste-inventario-nacom-lf-design.md §7.1
"""
from app import db
from app.utils.timezone import agora_utc_naive


class OperacaoOdooAuditoria(db.Model):
    __tablename__ = 'operacao_odoo_auditoria'

    id = db.Column(db.Integer, primary_key=True)
    external_id = db.Column(db.String(64), nullable=False, unique=True)
    tabela_origem = db.Column(db.String(40), nullable=False)
    registro_id = db.Column(db.Integer, nullable=False)
    acao = db.Column(db.String(20), nullable=False)
    modelo_odoo = db.Column(db.String(60), nullable=False)
    metodo_odoo = db.Column(db.String(60))
    odoo_id = db.Column(db.Integer)
    etapa = db.Column(db.Integer)
    etapa_descricao = db.Column(db.String(80))
    status = db.Column(db.String(20), nullable=False)
    payload_json = db.Column(db.JSON)
    resposta_json = db.Column(db.JSON)
    dados_antes_json = db.Column(db.JSON)
    dados_depois_json = db.Column(db.JSON)
    erro_msg = db.Column(db.Text)
    tempo_execucao_ms = db.Column(db.Integer)
    contexto_origem = db.Column(db.String(40))
    contexto_ref = db.Column(db.String(80))
    screenshot_s3_key = db.Column(db.String(255))
    executado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)
    executado_por = db.Column(db.String(80), nullable=False)

    def __repr__(self):
        return (
            f'<OperacaoOdooAuditoria {self.external_id} '
            f'{self.modelo_odoo}.{self.acao} status={self.status}>'
        )

    @classmethod
    def registrar(cls, *, external_id: str, tabela_origem: str, registro_id: int,
                  acao: str, modelo_odoo: str, status: str, executado_por: str,
                  **kwargs) -> 'OperacaoOdooAuditoria':
        """Helper para registrar uma operacao.

        Sanitiza automaticamente campos JSONB (sanitize_for_json).
        NAO commita — caller decide quando (padrao P5/P7 do app/odoo/CLAUDE.md).
        """
        from app.utils.json_helpers import sanitize_for_json
        kwargs.setdefault('executado_em', agora_utc_naive())
        for k in ('payload_json', 'resposta_json',
                  'dados_antes_json', 'dados_depois_json'):
            if k in kwargs and kwargs[k] is not None:
                kwargs[k] = sanitize_for_json(kwargs[k])
        rec = cls(
            external_id=external_id,
            tabela_origem=tabela_origem,
            registro_id=registro_id,
            acao=acao,
            modelo_odoo=modelo_odoo,
            status=status,
            executado_por=executado_por,
            **kwargs,
        )
        db.session.add(rec)
        db.session.flush()
        return rec

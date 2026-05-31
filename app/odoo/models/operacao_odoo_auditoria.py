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
    # G-AUDIT-2 v21+ FIX 2026-05-27: ampliado de 20 para 60 chars. Skill 5 v15a
    # usa nomes longos: 'criar_picking_entrada_destino_manual'=37, 'validar_picking_inter_company'=28.
    # Migration: scripts/migrations/v21_ampliar_operacao_odoo_auditoria.{sql,py}.
    acao = db.Column(db.String(60), nullable=False)
    modelo_odoo = db.Column(db.String(60), nullable=False)
    metodo_odoo = db.Column(db.String(60))
    odoo_id = db.Column(db.Integer)
    etapa = db.Column(db.Integer)
    etapa_descricao = db.Column(db.String(80))
    # G-AUDIT-2 v21+ FIX: ampliado de 20 para 30 chars (profilático). status atual
    # 'EXECUTADO_PARCIAL' (17), 'FALHA_AUTORIZACAO' (17), 'EXECUTADO_AUTO_CORRIGIDO' (24).
    status = db.Column(db.String(30), nullable=False)
    payload_json = db.Column(db.JSON)
    resposta_json = db.Column(db.JSON)
    dados_antes_json = db.Column(db.JSON)
    dados_depois_json = db.Column(db.JSON)
    erro_msg = db.Column(db.Text)
    tempo_execucao_ms = db.Column(db.Integer)
    contexto_origem = db.Column(db.String(40))
    contexto_ref = db.Column(db.String(80))
    # G-AUDIT-2 v21+ FIX: ampliado de 20 para 40 chars (profilático).
    # Atual F5a_PICKING_OK=14, mas pode crescer (ex: F5e_SEFAZ_OK_IDEMPOTENT).
    pipeline_etapa = db.Column(db.String(40))  # F5a..F5e — pos-G004/D003
    screenshot_s3_key = db.Column(db.String(255))
    executado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)
    executado_por = db.Column(db.String(80), nullable=False)
    # Audit hook deterministico (2026-05-28) — correlaciona com sessao do agente web.
    # Migration: scripts/migrations/2026_05_28_operacao_odoo_auditoria_session.{py,sql}.
    session_id = db.Column(db.String(64), index=True)  # FK logica para agent_sessions.session_id
    tool_use_id = db.Column(db.String(40), index=True)  # tool_use_id SDK Anthropic
    agent_type = db.Column(db.String(40), index=True)  # main|gestor-estoque-odoo|worker_rq|scheduler|cli

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

        Kwargs aceitos (todos opcionais):
        - metodo_odoo, odoo_id, etapa, etapa_descricao, payload_json,
          resposta_json, dados_antes_json, dados_depois_json, erro_msg,
          tempo_execucao_ms, contexto_origem, contexto_ref, screenshot_s3_key,
          pipeline_etapa, executado_em
        - session_id, tool_use_id, agent_type  (audit hook 2026-05-28)
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
        # BUG-1 (avaliacao 360, 2026-05-30): savepoint isola a falha do flush
        # da transacao do CALLER. A auditoria NUNCA deve poder derrubar a
        # operacao que esta auditando. Sem isto, um flush abortado (constraint,
        # tipo, tamanho de campo) poisonava a sessao e cascateava
        # PendingRollbackError no pipeline WRITE/SEFAZ (Sentry
        # PYTHON-FLASK-WX/WT/WS/WR/WQ, 2026-05-29). O hook em
        # odoo_audit_helpers.py ja envolvia esta chamada em begin_nested; agora
        # TODOS os 8 callers herdam a protecao (savepoint aninhado e seguro no
        # SQLAlchemy). A excecao do flush continua sendo propagada — o caller
        # decide se loga/re-tenta —, mas a transacao externa permanece sa
        # (ROLLBACK TO SAVEPOINT, nao da transacao inteira).
        with db.session.begin_nested():
            db.session.add(rec)
            db.session.flush()
        return rec

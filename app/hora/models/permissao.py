"""Permissoes granulares por usuario x modulo do HORA.

Modelo: 1 linha por (usuario, modulo) com 4 flags Ver/Criar/Editar/Apagar.

Default = TUDO BLOQUEADO para usuarios nao-admin sem entry. Admin
(perfil='administrador') passa em qualquer checagem.

NAO usa FK para `usuarios` para manter app/hora independente de app/auth
(mesma decisao usada em Usuario.loja_hora_id em app/auth/models.py).
"""
from __future__ import annotations

from app import db
from app.utils.timezone import agora_utc_naive


# Lista canonica dos modulos com permissoes granulares no HORA.
# Espelha os blueprints/secoes do menu (app/templates/hora/base.html).
# Mantida aqui para que UI e service usem a MESMA fonte de verdade.
MODULOS_HORA: list[tuple[str, str]] = [
    ('usuarios', 'Usuarios'),
    ('dashboard', 'Dashboard'),
    ('lojas', 'Lojas'),
    ('modelos', 'Modelos'),
    ('pedidos', 'Pedidos'),
    ('nfs', 'NFs de Entrada'),
    ('recebimentos', 'Recebimentos'),
    ('recebimento_resumo', 'Recebimento: Ver resumo/comparativo'),
    ('recebimento_motos_nf', 'Recebimento: Ver motos da NF'),
    ('estoque', 'Estoque'),
    ('estoque_valores', 'Estoque: Ver valores (R$)'),
    ('estoque_exportar', 'Estoque: Exportar Excel'),
    ('devolucoes', 'Devolucoes ao fornecedor (interno - resolucao recebimento)'),
    ('devolucoes_venda', 'Devolucoes de Venda (cliente devolveu)'),
    ('pecas', 'Pecas faltando'),
    ('transferencias', 'Transferencias entre filiais'),
    ('emprestimos', 'Emprestimos com lojas externas'),
    ('avarias', 'Avarias'),
    ('vendas', 'Vendas (Pedido de Venda)'),
    ('vendas_nf', 'Vendas: Emitir/Cancelar NF de saida (fiscal)'),
    ('vendas_exportar', 'Vendas: Exportar Excel (pedidos)'),
    ('vendas_descarte', 'Vendas: Descartar (NF teste)'),
    ('tagplus', 'Integracao TagPlus (NFe)'),
    ('pecas_cadastro', 'Cadastro de Pecas'),
    ('pecas_estoque', 'Estoque de Pecas'),
    ('comissao', 'Comissao (config + aprovacao de desconto)'),
]

# Modulos virtuais onde apenas a acao 'ver' tem semantica. As demais colunas
# da matriz aparecem como "—" (N/A) para evitar confusao do admin.
# Ex.: 'recebimento_resumo' controla se o conferente enxerga a tela-resumo
# com NF x Conferencia (item 3 do pedido do usuario 2026-04-23); 'criar/editar/
# apagar/aprovar' nao fazem sentido para essa feature.
MODULOS_SO_VER: set[str] = {
    'recebimento_resumo',
    'recebimento_motos_nf',
    # Flags de visibilidade fina dentro do Estoque/Vendas. Apenas 'ver' tem
    # semantica: gateiam, respectivamente, exibicao de valores R$ no detalhe
    # do chassi, exportacao Excel do estoque e exportacao Excel dos pedidos
    # de venda. Decorator/template checam `(<modulo>, 'ver')`.
    'estoque_valores',
    'estoque_exportar',
    'vendas_exportar',
    # Acao fiscal da NF de saida (emitir/preview/cancelar/CC-e), separada de
    # 'vendas' (que agora gateia apenas o PEDIDO de venda). Permite dar a um
    # vendedor o poder de criar pedido SEM o poder de emitir/cancelar a NFe.
    'vendas_nf',
}

# Modulos onde a acao 'aprovar' tem semantica REAL (decorator existe e e
# checado por uma rota). Em outros modulos a coluna "Aprovar" aparece como
# "—" (N/A) no gerenciador de permissoes para evitar confusao. Manter
# sincronizado com os `require_hora_perm(<modulo>, 'aprovar')` reais:
#   usuarios -> permissoes_aprovar / permissoes_rejeitar
#   modelos  -> modelos_unificacao (merge fisico) + pendencias
#   vendas   -> vendas_voltar_cotacao (reabrir CONFIRMADO; gerente)
# Decisao 2026-05-13: 'vendas/aprovar' habilitado no gerenciador para que
# gerentes possam ser configurados (era inacessivel antes deste commit).
MODULOS_COM_APROVAR: set[str] = {
    'usuarios',
    'modelos',
    'vendas',
    # comissao -> aprovacao de desconto acima do teto por modelo (#28, Fatia 2).
    'comissao',
}

ACOES_HORA: list[tuple[str, str]] = [
    ('ver', 'Ver'),
    ('criar', 'Criar'),
    ('editar', 'Editar'),
    ('apagar', 'Apagar'),
    ('aprovar', 'Aprovar'),
]


class HoraUserPermissao(db.Model):
    """Permissao granular por usuario x modulo HORA."""
    __tablename__ = 'hora_user_permissao'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False, index=True)
    modulo = db.Column(db.String(40), nullable=False)

    pode_ver = db.Column(db.Boolean, nullable=False, default=False)
    pode_criar = db.Column(db.Boolean, nullable=False, default=False)
    pode_editar = db.Column(db.Boolean, nullable=False, default=False)
    pode_apagar = db.Column(db.Boolean, nullable=False, default=False)
    pode_aprovar = db.Column(db.Boolean, nullable=False, default=False)

    atualizado_em = db.Column(
        db.DateTime, nullable=False,
        default=agora_utc_naive, onupdate=agora_utc_naive,
    )
    atualizado_por_id = db.Column(db.Integer, nullable=True)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'modulo', name='uq_hora_user_perm_user_mod'),
        db.Index('idx_hora_user_perm_lookup', 'user_id', 'modulo'),
    )

    def __repr__(self) -> str:
        flags = ''.join([
            'V' if self.pode_ver else '-',
            'C' if self.pode_criar else '-',
            'E' if self.pode_editar else '-',
            'A' if self.pode_apagar else '-',
            'P' if self.pode_aprovar else '-',
        ])
        return f'<HoraUserPermissao user={self.user_id} mod={self.modulo} {flags}>'

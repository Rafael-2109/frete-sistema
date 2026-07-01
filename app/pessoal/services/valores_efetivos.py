"""Expressao SQL canonica de "valor efetivo" do modulo Pessoal.

valor_efetivo = valor - COALESCE(valor_compensado, 0)

Fonte UNICA compartilhada por dashboard_service (competencia) e fluxo_caixa_service
(caixa), para que as duas superficies concordem no MESMO evento. Sem isto, o dashboard
somava o valor NOMINAL e divergia do fluxo (residuo de compensacao parcial contava a mais).

Espelha o proposito de PessoalTransacao.valor_efetivo (models.py) em nivel de expressao SQL.
Nao aplica clamp em 0: valor_compensado nunca excede valor (invariante do motor de
compensacao — recalcular_valor_compensado), entao a subtracao e sempre >= 0.
"""
from sqlalchemy import func

from app.pessoal.models import PessoalTransacao

EXPR_VALOR_EFETIVO = (
    PessoalTransacao.valor - func.coalesce(PessoalTransacao.valor_compensado, 0)
)

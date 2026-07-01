"""P3 — aprender_de_categorizacao nao pode criar regra com padrao DEGENERADO.

Bug auditado: regra id 989 com padrao_historico literal 'NULL' (aprendida de uma tx cujo
historico era o placeholder 'NULL' de descricao ausente no import). Como o match L1 e
substring, 'NULL' casaria qualquer historico que contenha 'NULL'. O guard len<3 nao pega
'NULL' (len 4). Descarta o texto degenerado (usa so CPF/CNPJ se houver).
"""
from uuid import uuid4

import pytest

from app.pessoal.services.aprendizado_service import aprender_de_categorizacao


@pytest.mark.integration
@pytest.mark.parametrize('placeholder', ['NULL', 'null', 'None', 'NaN'])
def test_aprender_ignora_padrao_degenerado(
    pessoal_ctx, make_transacao, categoria_alimentacao, placeholder,
):
    tx = make_transacao(
        historico=placeholder, historico_completo=placeholder,
        hash_transacao=f'deg{uuid4().hex[:8]}',
    )
    regra = aprender_de_categorizacao(tx.id, categoria_alimentacao.id)
    assert regra is None  # sem CPF e com padrao degenerado -> nenhuma regra criada

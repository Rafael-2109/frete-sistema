"""Re-roda categorizar_transacao em transacoes pessoais com `excluir_relatorio=False`
+ heuristica L4 detectavel (PAGTO. POR DEB EM C/C, transferencia propria, etc).

Motivo: bug em propagar_para_pendentes (corrigido em 2026-05-10) ignorava
flags `eh_pagamento_cartao` / `eh_transferencia_propria` / `excluir_relatorio`
quando categorizar_transacao retornava sem categoria_id (caso da Layer 4).
Resultado: transacoes "PAGTO. POR DEB EM C/C" e "SALDO ANTERIOR" voltaram a
aparecer no relatorio padrao apos qualquer descategorizar.

Este script aplica a logica corrigida nos dados ja existentes.

Idempotente: rodar 2x e a 2a vez nao altera nada (transacoes ja excluidas
nao sao reprocessadas).

Uso:
    source .venv/bin/activate
    python scripts/migrations/recategorizar_pendentes_pessoal.py             # dry-run
    python scripts/migrations/recategorizar_pendentes_pessoal.py --aplicar   # aplica
"""
from __future__ import annotations

import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from app import create_app, db  # noqa: E402
from app.pessoal.models import PessoalTransacao  # noqa: E402
from app.pessoal.services.categorizacao_service import categorizar_transacao  # noqa: E402
from app.utils.timezone import agora_utc_naive  # noqa: E402


def main(aplicar: bool = False):
    app = create_app()
    with app.app_context():
        print(f"[*] Modo: {'APLICAR' if aplicar else 'DRY-RUN'}")

        # Foca em candidatas a heuristica L4: hoje aparecem no relatorio
        # (excluir_relatorio=False) mas sao SALDO ANTERIOR ou pagamento de
        # cartao por DEB em C/C — devem ser excluidas.
        candidatas = PessoalTransacao.query.filter(
            PessoalTransacao.excluir_relatorio.is_(False),
        ).all()

        ajustes = []
        for t in candidatas:
            r = categorizar_transacao(t)
            mudou_excl = (r.excluir_relatorio is True) and (t.excluir_relatorio is False)
            mudou_pag  = (r.eh_pagamento_cartao is True) and (t.eh_pagamento_cartao is False)
            mudou_tp   = (r.eh_transferencia_propria is True) and (t.eh_transferencia_propria is False)
            if not (mudou_excl or mudou_pag or mudou_tp):
                continue
            ajustes.append((t, r))

        print(f'[*] Transacoes a corrigir: {len(ajustes)}')
        for t, r in ajustes[:30]:
            print(f"    id={t.id} data={t.data} hist={t.historico!r} "
                  f"excl: {t.excluir_relatorio}->{r.excluir_relatorio} "
                  f"pagcc: {t.eh_pagamento_cartao}->{r.eh_pagamento_cartao} "
                  f"tp: {t.eh_transferencia_propria}->{r.eh_transferencia_propria}")
        if len(ajustes) > 30:
            print(f'    ... +{len(ajustes) - 30} omitidas')

        if not aplicar:
            print('[OK] DRY-RUN. Reexecute com --aplicar para gravar.')
            return

        if not ajustes:
            print('[OK] Nada a fazer.')
            return

        atualizados = 0
        for t, r in ajustes:
            t.excluir_relatorio = r.excluir_relatorio
            t.eh_pagamento_cartao = r.eh_pagamento_cartao
            t.eh_transferencia_propria = r.eh_transferencia_propria
            if r.status == 'CATEGORIZADO' and (t.status or 'PENDENTE') == 'PENDENTE':
                t.status = 'CATEGORIZADO'
                t.categorizado_em = agora_utc_naive()
                t.categorizado_por = 'sistema (cleanup L4 2026-05-10)'
            atualizados += 1

        db.session.commit()
        print(f'[OK] {atualizados} transacoes corrigidas.')


if __name__ == '__main__':
    aplicar = '--aplicar' in sys.argv
    main(aplicar=aplicar)

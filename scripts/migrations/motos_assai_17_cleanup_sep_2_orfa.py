"""Data fix (2026-05-12): deletar AssaiSeparacao 2 orfa de teste.

Contexto: tela /motos-assai/pedidos/<pid>/separar/<lid> chamava
`get_ou_criar_separacao` que CRIAVA sep implicitamente quando a UI navegava
sem `?sep_id`. Cada navegacao gerava sep fantasma no banco.

Estado descoberto em 2026-05-12 no Render:
    Pedido 21439695/L (id=1), Loja 112 (id=10):
      - Sep 1: CANCELADA (motivo: "teste") @ 08:58 — usuario cancelou
      - Sep 2: EM_SEPARACAO @ 16:20 — criada AUTOMATICAMENTE pela rota
        ao operador clicar "Abrir" / "Continuar" / "Iniciar" sem sep_id

Sep 2 esta totalmente VAZIA (0 items, 0 saldos, 0 NFs apontando, 0 linhas
em `separacao` Nacom com lote `ASSAI-SEP-2`). Deletar e seguro.

Apos esta limpeza + correcao em `separacao_service.get_separacao_ativa`
(que substitui `get_ou_criar_separacao`), o bug nao se repete.

Migration 17 — apenas data fix (sem DDL), idempotente.

Padrao: rodar via `python scripts/migrations/motos_assai_17_cleanup_sep_2_orfa.py`.
"""
import os
import sys

# CLAUDE.md (memoria 2026-04-22): scripts em scripts/migrations/ DEVEM ter
# sys.path.insert antes de `from app import` para evitar ModuleNotFoundError
# em Render Shell.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app, db  # noqa: E402
from app.motos_assai.models import (  # noqa: E402
    AssaiSeparacao, AssaiSeparacaoItem, AssaiSeparacaoSaldoModelo,
    AssaiNfQpa, SEPARACAO_STATUS_EM_SEPARACAO,
)
from app.separacao.models import Separacao  # noqa: E402


SEP_ID_ALVO = 2  # AssaiSeparacao orfa identificada em prod


def main():
    app = create_app()
    with app.app_context():
        sep = AssaiSeparacao.query.get(SEP_ID_ALVO)
        if not sep:
            print(f'[skip] AssaiSeparacao {SEP_ID_ALVO} ja nao existe — idempotente OK')
            return

        # Validacao defensiva: so deletar se realmente esta vazia e nao tem
        # FKs externas apontando. Se algo mudou desde 2026-05-12, abortar.
        if sep.status != SEPARACAO_STATUS_EM_SEPARACAO:
            print(
                f'[abort] AssaiSeparacao {SEP_ID_ALVO} esta {sep.status} — '
                'esperado EM_SEPARACAO. Nao deletar.'
            )
            return

        items_count = AssaiSeparacaoItem.query.filter_by(separacao_id=SEP_ID_ALVO).count()
        saldos_count = AssaiSeparacaoSaldoModelo.query.filter_by(
            separacao_id=SEP_ID_ALVO
        ).count()
        nfs_count = AssaiNfQpa.query.filter_by(separacao_id=SEP_ID_ALVO).count()
        nacom_count = Separacao.query.filter_by(
            separacao_lote_id=f'ASSAI-SEP-{SEP_ID_ALVO}'
        ).count()

        print(f'[before] sep_id={SEP_ID_ALVO} pedido_id={sep.pedido_id} loja_id={sep.loja_id}')
        print(
            f'[before] items={items_count} saldos={saldos_count} '
            f'nfs_apontando={nfs_count} linhas_nacom={nacom_count}'
        )

        if items_count > 0 or saldos_count > 0 or nfs_count > 0 or nacom_count > 0:
            print(
                f'[abort] AssaiSeparacao {SEP_ID_ALVO} tem dependencias — '
                'nao deletar (operador deve revisar manualmente).'
            )
            return

        db.session.delete(sep)
        db.session.commit()

        # Verificacao depois
        still_exists = AssaiSeparacao.query.get(SEP_ID_ALVO)
        if still_exists:
            print(f'[error] AssaiSeparacao {SEP_ID_ALVO} ainda existe apos delete')
            sys.exit(1)

        print(f'[ok] AssaiSeparacao {SEP_ID_ALVO} deletada com sucesso')


if __name__ == '__main__':
    main()

"""Backfill: grava o grupo WhatsApp (whatsapp_grupo_jid) das lojas HORA.

Mapeia cada loja Comercial ao seu grupo WhatsApp (Evolution/Baileys),
confirmado pelo dono em 2026-06-27. Idempotente: UPDATE por apelido (case/
trim-insensitive) so' quando o valor difere; re-rodar e' no-op.

Pre-requisito: coluna hora_loja.whatsapp_grupo_jid (migration hora_56).

Uso:
    python scripts/hora/set_grupos_whatsapp_lojas.py
"""
import logging
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from sqlalchemy import text  # noqa: E402

from app import create_app, db  # noqa: E402

logger = logging.getLogger(__name__)

# apelido da loja (hora_loja.apelido) -> JID do grupo WhatsApp (Baileys, "...@g.us")
GRUPOS_POR_LOJA = {
    'MOTOCHEFE TATUAPE': '120363405889952573@g.us',       # Comercial Tatuapé MotoChefe
    'MOTOCHEFE BRAGANÇA': '120363407566508377@g.us',      # Comercial Bragança MotoChefe
    'MOTOCHEFE PRAIA GRANDE': '120363424382419784@g.us',  # Comercial PG MotoChefe
    'MOTOCHEFE SANTANA': '120363409045132066@g.us',       # Comercial Santana BLZN - MotoChefe
}


def main() -> None:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    app = create_app()
    with app.app_context():
        total = 0
        with db.engine.begin() as conn:
            for apelido, jid in GRUPOS_POR_LOJA.items():
                res = conn.execute(
                    text(
                        """
                        UPDATE hora_loja
                           SET whatsapp_grupo_jid = :jid
                         WHERE UPPER(TRIM(apelido)) = UPPER(:apelido)
                           AND (whatsapp_grupo_jid IS DISTINCT FROM :jid)
                        """
                    ),
                    {'jid': jid, 'apelido': apelido},
                )
                n = res.rowcount or 0
                total += n
                marca = 'ATUALIZADO' if n else 'ja ok / loja nao encontrada'
                print(f'  {apelido:28s} -> {jid}  ({marca})')

        print(f'\nBackfill grupos-loja concluido. Linhas alteradas: {total}.')


if __name__ == '__main__':
    main()

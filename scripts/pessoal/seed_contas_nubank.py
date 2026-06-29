"""Seed das contas Nubank do modulo Pessoal (NuConta + Cartao).

Cria 2 PessoalConta (idempotente — pula se ja existir por banco+numero_conta):
- NuConta  : conta_corrente, banco=nubank, numero_conta=63685323-8 (ACCTID do extrato OFX)
- Cartao   : cartao_credito, banco=nubank, numero_conta=<ACCTID UUID da fatura OFX>

O numero_conta guarda o ACCTID do OFX -> a importacao resolve a conta automaticamente.
Titular: membro 'Rafael'.

Uso:
    python scripts/pessoal/seed_contas_nubank.py                         # dry-run (local)
    python scripts/pessoal/seed_contas_nubank.py --confirmar             # grava (local)
    DATABASE_URL="$DATABASE_URL_PROD" python scripts/pessoal/seed_contas_nubank.py
    DATABASE_URL="$DATABASE_URL_PROD" python scripts/pessoal/seed_contas_nubank.py --confirmar
"""
import argparse
import logging
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db  # noqa: E402
from app.pessoal.models import PessoalConta, PessoalMembro  # noqa: E402

logger = logging.getLogger(__name__)

# ACCTIDs reais dos OFX Nubank (extrato e fatura)
CONTAS_NUBANK = [
    {
        'nome': 'Nubank NuConta',
        'tipo': 'conta_corrente',
        'banco': 'nubank',
        'numero_conta': '63685323-8',
    },
    {
        'nome': 'Nubank Cartão',
        'tipo': 'cartao_credito',
        'banco': 'nubank',
        'numero_conta': '5f00ffaf-315a-4466-aa0f-6ef2b15baa39',
    },
]

TITULAR = 'Rafael'


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--confirmar', action='store_true', help='grava (sem isto, dry-run)')
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    app = create_app()
    with app.app_context():
        membro = PessoalMembro.query.filter_by(nome=TITULAR).first()
        membro_id = membro.id if membro else None
        if membro_id is None:
            print(f"AVISO: membro '{TITULAR}' nao encontrado — contas ficarao sem titular.")

        criadas, existentes = [], []
        for c in CONTAS_NUBANK:
            ja = PessoalConta.query.filter_by(
                banco=c['banco'], numero_conta=c['numero_conta'],
            ).first()
            if ja:
                existentes.append(f"{ja.nome} (id={ja.id})")
                continue
            if args.confirmar:
                nova = PessoalConta(
                    nome=c['nome'], tipo=c['tipo'], banco=c['banco'],
                    numero_conta=c['numero_conta'], membro_id=membro_id, ativa=True,
                )
                db.session.add(nova)
                db.session.flush()
                criadas.append(f"{nova.nome} (id={nova.id})")
            else:
                criadas.append(f"{c['nome']} (DRY-RUN)")

        if args.confirmar:
            db.session.commit()

        print('--- Seed contas Nubank ---')
        print(f"Modo: {'GRAVADO' if args.confirmar else 'DRY-RUN (use --confirmar para gravar)'}")
        print(f"Titular: {TITULAR} (id={membro_id})")
        print(f"Ja existentes: {existentes or '-'}")
        print(f"{'Criadas' if args.confirmar else 'A criar'}: {criadas or '-'}")


if __name__ == '__main__':
    main()

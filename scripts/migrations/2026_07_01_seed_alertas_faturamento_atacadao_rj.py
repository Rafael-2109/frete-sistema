"""Seed: carga inicial dos CNPJs do Atacadao RJ nos Alertas de Faturamento.

Insere 31 lojas do Atacadao RJ em `alerta_faturamento_cnpj`, todas com a lista
de e-mails padrao (time Conservas Campo Belo) e ativas. Idempotente: pula CNPJ
que ja existe (nao sobrescreve edicoes feitas na tela). Novos CNPJs sao
incluidos depois pela tela `/faturamento/alertas`.

Pre-requisito: rodar antes `2026_07_01_alertas_faturamento_cnpj.py` (cria a tabela).
Fonte: C:\\Users\\marcus.lima\\Downloads\\atacadao_rj_cnpjs.xlsx (aba "Atacadao RJ").

Uso:
    python scripts/migrations/2026_07_01_seed_alertas_faturamento_atacadao_rj.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app, db  # noqa: E402
from app.faturamento.models import AlertaFaturamentoCnpj  # noqa: E402
from app.faturamento.services.alerta_faturamento_service import EMAILS_PADRAO  # noqa: E402

# (cnpj normalizado — so digitos, apelido)
CNPJS_ATACADAO_RJ = [
    ("75315333010252", "ATACADAO 102"),
    ("75315333013006", "ATACADAO 130"),
    ("75315333013600", "ATACADAO 136"),
    ("75315333015726", "ATACADAO 157"),
    ("75315333016293", "ATACADAO 162"),
    ("75315333017427", "ATACADAO 174"),
    ("75315333019390", "ATACADAO 193"),
    ("75315333020215", "ATACADAO 202"),
    ("75315333020720", "ATACADAO 207"),
    ("75315333021025", "ATACADAO 210"),
    ("75315333024717", "ATACADAO 247"),
    ("75315333024989", "ATACADAO 249"),
    ("75315333025950", "ATACADAO 259"),
    ("75315333027066", "ATACADAO 270"),
    ("75315333027570", "ATACADAO 275"),
    ("75315333027813", "ATACADAO 278"),
    ("75315333028976", "ATACADAO 289"),
    ("75315333029190", "ATACADAO 291"),
    ("75315333029271", "ATACADAO 292"),
    ("75315333029433", "ATACADAO 294"),
    ("75315333031926", "ATACADAO 319"),
    ("75315333033627", "ATACADAO 336"),
    ("75315333006301", "ATACADAO 63"),
    ("75315333006573", "ATACADAO 65"),
    ("75315333006735", "ATACADAO 67"),
    ("93209765067963", "ATACADAO 679"),
    ("93209765068188", "ATACADAO 681"),
    ("93209765069150", "ATACADAO 691"),
    ("93209765069907", "ATACADAO 699"),
    ("00063960002659", "ATACADAO 719"),
    ("93209765048900", "ATACADAO 815"),
]


def main():
    app = create_app()
    with app.app_context():
        criados, existentes = 0, 0
        for cnpj, apelido in CNPJS_ATACADAO_RJ:
            if AlertaFaturamentoCnpj.query.filter_by(cnpj=cnpj).first():
                existentes += 1
                continue
            db.session.add(AlertaFaturamentoCnpj(
                cnpj=cnpj, nome_cliente=apelido, emails=EMAILS_PADRAO,
                ativo=True, criado_por='seed_atacadao_rj',
            ))
            criados += 1
        db.session.commit()
        print(f"OK: {criados} CNPJs criados, {existentes} ja existiam "
              f"(total base = {len(CNPJS_ATACADAO_RJ)}).")


if __name__ == '__main__':
    main()

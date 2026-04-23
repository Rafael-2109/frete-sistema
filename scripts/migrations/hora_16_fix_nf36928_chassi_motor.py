"""Migration HORA 16: data-fix NF 36928 — inverter chassi <-> motor das 2 motos RET.

Causa: prompt LLM do parser DANFE CarVia ensinava a inverter chassi/motor
quando o padrao era "1o digito puro + 2o alfanumerico" (caso motos RET).
Fixo no prompt aplicado em app/carvia/services/parsers/danfe_pdf_parser.py.

Esta migration corrige APENAS os dados historicos da NF 36928
(chave 33260409089839000112550000000369281387401233). Idempotente.

Roda o SQL irmao (hora_16_fix_nf36928_chassi_motor.sql) e reporta estado
antes/depois dos 4 chassis envolvidos.
"""
import os
import sys

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
)

from app import create_app, db  # noqa: E402


CHASSIS_ENVOLVIDOS = (
    '172922504731222',            # correto (item 23, PRETO)
    '172922506731648',            # correto (item 24, CINZA)
    'LM60V1000W2025051000290',    # errado (antes gravado como chassi no item 23)
    'LM60V1000W2025062100443',    # errado (antes gravado como chassi no item 24)
)


def estado_hora_moto():
    rows = db.session.execute(
        db.text(
            "SELECT numero_chassi, numero_motor, cor FROM hora_moto "
            "WHERE numero_chassi = ANY(:chs) ORDER BY numero_chassi"
        ),
        {'chs': list(CHASSIS_ENVOLVIDOS)},
    ).fetchall()
    return [dict(chassi=r[0], motor=r[1], cor=r[2]) for r in rows]


def estado_nf_itens():
    rows = db.session.execute(
        db.text(
            "SELECT id, numero_chassi, numero_motor_texto_original, cor_texto_original "
            "FROM hora_nf_entrada_item WHERE id IN (23, 24) ORDER BY id"
        )
    ).fetchall()
    return [
        dict(id=r[0], chassi=r[1], motor_texto=r[2], cor_texto=r[3])
        for r in rows
    ]


def verificar(label: str):
    print(f"\n=== {label} ===")
    print("hora_nf_entrada_item (itens 23, 24):")
    for r in estado_nf_itens():
        print(f"  #{r['id']} chassi={r['chassi']!r} motor_texto={r['motor_texto']!r} cor={r['cor_texto']!r}")
    print("hora_moto (4 chassis envolvidos):")
    for r in estado_hora_moto():
        print(f"  chassi={r['chassi']!r} motor={r['motor']!r} cor={r['cor']!r}")


def executar_sql():
    path = os.path.join(
        os.path.dirname(__file__), 'hora_16_fix_nf36928_chassi_motor.sql'
    )
    with open(path, encoding='utf-8') as f:
        sql = f.read()
    db.session.execute(db.text(sql))
    db.session.commit()


def ja_aplicada() -> bool:
    """Ja aplicada APENAS quando AMBOS os itens (23 e 24) estao com chassi correto.

    Se apenas um esta correto (aplicacao parcial que crashou), retornamos False
    para o SQL (idempotente) tentar de novo — os UPDATEs tem guard WHERE que
    os torna no-op para quem ja foi corrigido.
    """
    rows = db.session.execute(
        db.text(
            "SELECT id, numero_chassi FROM hora_nf_entrada_item "
            "WHERE id IN (23, 24)"
        )
    ).fetchall()
    by_id = {r[0]: r[1] for r in rows}
    return (
        by_id.get(23) == '172922504731222'
        and by_id.get(24) == '172922506731648'
    )


def main():
    app = create_app()
    with app.app_context():
        verificar('ANTES')
        if ja_aplicada():
            print("\n[SKIP] Migration ja aplicada (item 23 ja tem chassi correto).")
            return
        print("\n[APLICANDO] Executando hora_16_fix_nf36928_chassi_motor.sql...")
        executar_sql()
        verificar('DEPOIS')
        print("\n[OK] Data-fix aplicado com sucesso.")


if __name__ == '__main__':
    main()

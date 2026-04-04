"""
Migration: Popular dimensoes internas do bau para todos os veiculos cadastrados.

Valores em centimetros (cm), pesquisados via fichas tecnicas e fontes do mercado.

Fontes:
  FIORINO: Ficha tecnica Fiat Fiorino Furgao MY24 (media.stellantis.com)
  VAN/HR: Hyundai HR bau padrao (Superbid/Truckvan)
  MASTER: Renault Master Grand Furgao L2H2 (dimensoes tipicas L2H2)
  IVECO: Iveco Daily chassi-cabine + bau (Superbid/BasWorld)
  3/4: MB Accelo 1016 / bau padrao 4t (VendaTruck, GuiaLog)
  TOCO: Bau padrao 6t (GuiaLog, Facchini, Santana Baus)
  TRUCK: Bau padrao truck 6x2 (Randon 8.55m)
  CARRETA: Semi-reboque padrao (GuiaLog, 14.94m)
  BI-TRUCK: Bau padrao bi-truck 8x2 (Mathias Implementos, Randon)
  CABOTAGEM: Container 40 pes dry ISO standard

Uso:
    source .venv/bin/activate
    python scripts/migrations/popular_dimensoes_bau_veiculos.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app, db
from sqlalchemy import text


# Dimensoes: (id, nome, comprimento_cm, largura_cm, altura_cm)
DIMENSOES = [
    (1,  'FIORINO',    188.7, 108.9, 133.9),
    (2,  'VAN/HR',     300.0, 180.0, 200.0),
    (3,  'MASTER',     373.0, 176.5, 185.6),
    (4,  'IVECO',      480.0, 215.0, 210.0),
    (5,  '3/4',        510.0, 215.0, 220.0),
    (6,  'TOCO',       700.0, 244.0, 260.0),
    (7,  'TRUCK',      850.0, 244.0, 260.0),
    (8,  'CARRETA',   1494.0, 248.0, 273.0),
    (9,  'BI-TRUCK',   950.0, 250.0, 265.0),
    (10, 'CABOTAGEM', 1203.2, 235.0, 239.2),
]


def main():
    app = create_app()
    with app.app_context():
        # BEFORE: estado atual
        print("=== BEFORE ===")
        result = db.session.execute(text(
            "SELECT id, nome, comprimento_bau, largura_bau, altura_bau "
            "FROM veiculos ORDER BY id"
        ))
        rows = result.fetchall()
        for r in rows:
            dims = f"{r[2]} x {r[3]} x {r[4]}" if r[2] else "SEM DIMENSOES"
            print(f"  [{r[0]}] {r[1]:12s} -> {dims}")

        # Aplicar updates (apenas onde NULL — nao sobrescreve manuais)
        print("\n=== APLICANDO ===")
        updated = 0
        for vid, nome, comp, larg, alt in DIMENSOES:
            result = db.session.execute(text("""
                UPDATE veiculos
                SET comprimento_bau = :comp,
                    largura_bau = :larg,
                    altura_bau = :alt
                WHERE id = :id AND nome = :nome
                  AND comprimento_bau IS NULL
            """), {'id': vid, 'nome': nome, 'comp': comp, 'larg': larg, 'alt': alt})

            if result.rowcount > 0:
                vol_m3 = (comp * larg * alt) / 1_000_000
                print(f"  + [{vid}] {nome:12s} -> {comp} x {larg} x {alt} cm ({vol_m3:.1f} m³)")
                updated += 1
            else:
                print(f"  = [{vid}] {nome:12s} -> ja possui dimensoes ou nao encontrado")

        db.session.commit()

        # AFTER: verificar resultado
        print(f"\n=== AFTER ({updated} atualizados) ===")
        result = db.session.execute(text(
            "SELECT id, nome, comprimento_bau, largura_bau, altura_bau "
            "FROM veiculos ORDER BY id"
        ))
        rows = result.fetchall()
        for r in rows:
            if r[2] and r[3] and r[4]:
                vol = (r[2] * r[3] * r[4]) / 1_000_000
                print(f"  [{r[0]}] {r[1]:12s} -> {r[2]} x {r[3]} x {r[4]} cm = {vol:.1f} m³")
            else:
                print(f"  [{r[0]}] {r[1]:12s} -> SEM DIMENSOES (FALHA!)")

        print("\nMigration concluida com sucesso!")


if __name__ == '__main__':
    main()

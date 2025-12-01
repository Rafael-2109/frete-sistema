"""
Script para corrigir inconsistências na flag nf_cd

PROBLEMAS CORRIGIDOS:
1. EntregaMonitorada com status_finalizacao preenchido E nf_cd=True (mutuamente exclusivos)
2. EntregaMonitorada com nf_cd=True mas sem evento "NF no CD"
3. Separacao com nf_cd diferente de EntregaMonitorada para mesmo lote/NF

Autor: Sistema
Data: 01/12/2025
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from datetime import datetime


def corrigir_nf_cd_inconsistentes(commit=False):
    """
    Corrige inconsistências na flag nf_cd.

    Args:
        commit: Se True, persiste as alterações. Se False, apenas mostra o que seria corrigido.
    """
    app = create_app()

    with app.app_context():
        from app.monitoramento.models import EntregaMonitorada, EventoEntrega
        from app.separacao.models import Separacao

        print("=" * 80)
        print(f"CORREÇÃO DE INCONSISTÊNCIAS NF_CD - {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        print("=" * 80)
        print(f"Modo: {'COMMIT (ALTERAÇÕES SERÃO SALVAS)' if commit else 'DRY-RUN (apenas visualização)'}")
        print("=" * 80)

        total_corrigidos = 0

        # =========================================================================
        # PROBLEMA 1: EntregaMonitorada com status_finalizacao E nf_cd=True
        # =========================================================================
        print("\n📋 PROBLEMA 1: Entregas finalizadas com nf_cd=True (mutuamente exclusivos)")
        print("-" * 80)

        entregas_finalizadas_com_nf_cd = EntregaMonitorada.query.filter(
            EntregaMonitorada.status_finalizacao.isnot(None),
            EntregaMonitorada.nf_cd == True
        ).all()

        print(f"Encontradas: {len(entregas_finalizadas_com_nf_cd)} entregas")

        for entrega in entregas_finalizadas_com_nf_cd:
            print(f"  - NF {entrega.numero_nf}: status_finalizacao='{entrega.status_finalizacao}', nf_cd={entrega.nf_cd}")
            print(f"    → Corrigindo: nf_cd=False")

            if commit:
                entrega.nf_cd = False

                # Sincronizar com Separacao
                if entrega.separacao_lote_id:
                    Separacao.query.filter_by(
                        separacao_lote_id=entrega.separacao_lote_id
                    ).update({'nf_cd': False})
                    print(f"    → Separacao sincronizada (lote {entrega.separacao_lote_id})")
                elif entrega.numero_nf:
                    Separacao.query.filter_by(
                        numero_nf=entrega.numero_nf
                    ).update({'nf_cd': False})
                    print(f"    → Separacao sincronizada (NF {entrega.numero_nf})")

            total_corrigidos += 1

        # =========================================================================
        # PROBLEMA 2: EntregaMonitorada com nf_cd=True mas sem evento "NF no CD"
        # =========================================================================
        print("\n📋 PROBLEMA 2: Entregas com nf_cd=True mas sem evento 'NF no CD'")
        print("-" * 80)

        entregas_nf_cd_true = EntregaMonitorada.query.filter(
            EntregaMonitorada.nf_cd == True
        ).all()

        entregas_sem_evento = []
        for entrega in entregas_nf_cd_true:
            # Verificar se tem evento "NF no CD"
            evento_nf_cd = EventoEntrega.query.filter_by(
                entrega_id=entrega.id,
                tipo_evento="NF no CD"
            ).first()

            if not evento_nf_cd:
                entregas_sem_evento.append(entrega)

        print(f"Encontradas: {len(entregas_sem_evento)} entregas com nf_cd=True sem evento")

        for entrega in entregas_sem_evento:
            print(f"  - NF {entrega.numero_nf}: nf_cd={entrega.nf_cd}, sem evento 'NF no CD'")
            print(f"    → Corrigindo: nf_cd=False (pois não há evidência de que NF voltou ao CD)")

            if commit:
                entrega.nf_cd = False

                # Sincronizar com Separacao
                if entrega.separacao_lote_id:
                    Separacao.query.filter_by(
                        separacao_lote_id=entrega.separacao_lote_id
                    ).update({'nf_cd': False})
                    print(f"    → Separacao sincronizada (lote {entrega.separacao_lote_id})")
                elif entrega.numero_nf:
                    Separacao.query.filter_by(
                        numero_nf=entrega.numero_nf
                    ).update({'nf_cd': False})
                    print(f"    → Separacao sincronizada (NF {entrega.numero_nf})")

            total_corrigidos += 1

        # =========================================================================
        # PROBLEMA 3: Separacao com nf_cd diferente de EntregaMonitorada
        # =========================================================================
        print("\n📋 PROBLEMA 3: Separacao com nf_cd inconsistente com EntregaMonitorada")
        print("-" * 80)

        # Buscar todas as separações com numero_nf preenchido
        separacoes_com_nf = db.session.query(
            Separacao.separacao_lote_id,
            Separacao.numero_nf,
            Separacao.nf_cd
        ).filter(
            Separacao.numero_nf.isnot(None),
            Separacao.numero_nf != ''
        ).distinct(Separacao.separacao_lote_id).all()

        inconsistencias_separacao = 0
        for sep in separacoes_com_nf:
            lote_id, numero_nf, sep_nf_cd = sep

            # Buscar EntregaMonitorada correspondente
            entrega = EntregaMonitorada.query.filter_by(numero_nf=numero_nf).first()

            if entrega and entrega.nf_cd != sep_nf_cd:
                print(f"  - Lote {lote_id}, NF {numero_nf}:")
                print(f"    Separacao.nf_cd={sep_nf_cd} vs EntregaMonitorada.nf_cd={entrega.nf_cd}")
                print(f"    → Corrigindo: Separacao.nf_cd={entrega.nf_cd}")

                if commit:
                    Separacao.query.filter_by(
                        separacao_lote_id=lote_id
                    ).update({'nf_cd': entrega.nf_cd})

                inconsistencias_separacao += 1
                total_corrigidos += 1

        print(f"Encontradas: {inconsistencias_separacao} inconsistências entre Separacao e EntregaMonitorada")

        # =========================================================================
        # COMMIT
        # =========================================================================
        if commit:
            db.session.commit()
            print("\n" + "=" * 80)
            print(f"✅ COMMIT REALIZADO - {total_corrigidos} correções aplicadas")
            print("=" * 80)
        else:
            print("\n" + "=" * 80)
            print(f"🔍 DRY-RUN FINALIZADO - {total_corrigidos} correções seriam aplicadas")
            print("Para aplicar as correções, execute com --commit")
            print("=" * 80)

        return total_corrigidos


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Corrige inconsistências na flag nf_cd')
    parser.add_argument('--commit', action='store_true', help='Aplica as correções no banco de dados')
    args = parser.parse_args()

    corrigir_nf_cd_inconsistentes(commit=args.commit)

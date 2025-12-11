# -*- coding: utf-8 -*-
"""
Script para corrigir raz_social e raz_social_red em ContasAReceber.

Problema: Os campos estavam sendo populados com valores idênticos porque
a prioridade estava invertida (usava partner_id_nome primeiro).

Correção: Agora busca do Odoo e atualiza com:
- raz_social: l10n_br_razao_social (razão social completa)
- raz_social_red: name (nome fantasia)

Execução local:
    source venv/bin/activate
    python scripts/corrigir_raz_social_contas_receber.py

Execução no Render Shell:
    python scripts/corrigir_raz_social_contas_receber.py

Autor: Sistema de Fretes
Data: 2025-12-11
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.financeiro.models import ContasAReceber
from app.financeiro.services.contas_receber_service import ContasReceberService


def corrigir_raz_social():
    """Corrige raz_social e raz_social_red buscando dados atualizados do Odoo."""
    app = create_app()
    with app.app_context():
        print("=" * 70)
        print("CORRIGINDO RAZ_SOCIAL E RAZ_SOCIAL_RED")
        print("=" * 70)

        # Inicializar serviço Odoo
        service = ContasReceberService()

        # Buscar CNPJs únicos dos registros locais
        registros = ContasAReceber.query.filter(
            ContasAReceber.cnpj.isnot(None)
        ).all()

        print(f"Total de registros com CNPJ: {len(registros)}")

        # Agrupar por CNPJ para otimizar busca no Odoo
        cnpjs_unicos = set()
        for r in registros:
            if r.cnpj:
                cnpjs_unicos.add(r.cnpj)

        print(f"CNPJs únicos: {len(cnpjs_unicos)}")
        print()

        # Buscar dados dos parceiros no Odoo em lotes
        print("Buscando dados do Odoo...")
        parceiros_map = {}

        cnpjs_lista = list(cnpjs_unicos)
        BATCH_SIZE = 100

        for i in range(0, len(cnpjs_lista), BATCH_SIZE):
            batch = cnpjs_lista[i:i + BATCH_SIZE]
            print(f"  Lote {i // BATCH_SIZE + 1}/{(len(cnpjs_lista) - 1) // BATCH_SIZE + 1}...")

            try:
                # Buscar parceiros pelo CNPJ
                parceiros = service.connection.search_read(
                    'res.partner',
                    [['l10n_br_cnpj', 'in', batch]],
                    fields=['id', 'name', 'l10n_br_razao_social', 'l10n_br_cnpj']
                )

                for p in parceiros:
                    cnpj = p.get('l10n_br_cnpj')
                    if cnpj:
                        parceiros_map[cnpj] = {
                            'name': p.get('name', ''),
                            'l10n_br_razao_social': p.get('l10n_br_razao_social') or ''
                        }
            except Exception as e:
                print(f"    Erro no lote: {e}")
                continue

        print(f"Parceiros encontrados no Odoo: {len(parceiros_map)}")
        print()

        # Atualizar registros locais
        print("Atualizando registros locais...")
        atualizados = 0
        sem_dados = 0
        ja_corretos = 0

        for registro in registros:
            cnpj = registro.cnpj
            dados_odoo = parceiros_map.get(cnpj)

            if not dados_odoo:
                sem_dados += 1
                continue

            # Valores corretos
            raz_social_correta = dados_odoo['l10n_br_razao_social'] or dados_odoo['name']
            raz_social_red_correta = dados_odoo['name'][:100] if dados_odoo['name'] else None

            # Verificar se precisa atualizar
            if registro.raz_social == raz_social_correta and registro.raz_social_red == raz_social_red_correta:
                ja_corretos += 1
                continue

            # Atualizar
            registro.raz_social = raz_social_correta
            registro.raz_social_red = raz_social_red_correta
            atualizados += 1

        db.session.commit()

        print()
        print("=" * 70)
        print("RESULTADO")
        print("=" * 70)
        print(f"Atualizados: {atualizados}")
        print(f"Já corretos: {ja_corretos}")
        print(f"Sem dados no Odoo: {sem_dados}")
        print()

        # Verificar amostra
        print("AMOSTRA (5 registros atualizados):")
        print("-" * 70)
        amostra = ContasAReceber.query.filter(
            ContasAReceber.cnpj.isnot(None)
        ).limit(5).all()

        for r in amostra:
            print(f"ID {r.id} | CNPJ: {r.cnpj}")
            print(f"  raz_social:     \"{r.raz_social[:50] if r.raz_social else 'N/A'}...\"")
            print(f"  raz_social_red: \"{r.raz_social_red[:50] if r.raz_social_red else 'N/A'}...\"")
            print(f"  Diferentes? {r.raz_social != r.raz_social_red}")
            print()


if __name__ == '__main__':
    corrigir_raz_social()

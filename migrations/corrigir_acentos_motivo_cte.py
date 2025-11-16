"""
Script para Corrigir Acentos em Motivos de CTe
===============================================

Remove acentos dos motivos de CTes complementares que já estão no banco
com caracteres corrompidos (�)

AUTOR: Sistema de Fretes
DATA: 15/11/2025
"""

import sys
import os
import unicodedata

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db  # noqa: E402
from app.fretes.models import ConhecimentoTransporte  # noqa: E402

def remover_acentos(texto):
    """Remove acentos e caracteres corrompidos de um texto"""
    if not texto:
        return texto

    # 1. Substituir caractere de substituição � por versão sem acento
    # Tentar mapear os casos mais comuns
    mapeamento = {
        'N�MERO': 'NUMERO',
        'N�mero': 'Numero',
        'VE�CULO': 'VEICULO',
        'Ve�culo': 'Veiculo',
        'PROPRIET�RIO': 'PROPRIETARIO',
        'Propriet�rio': 'Proprietario',
        'AP�LICE': 'APOLICE',
        'Ap�lice': 'Apolice',
        'sa�da': 'saida',
        'SA�DA': 'SAIDA',
    }

    for antigo, novo in mapeamento.items():
        texto = texto.replace(antigo, novo)

    # 2. Remover qualquer � restante
    texto = texto.replace('�', '')

    # 3. Normalizar e remover acentos normais
    texto_nfd = unicodedata.normalize('NFD', texto)
    texto_sem_acento = ''.join(char for char in texto_nfd if unicodedata.category(char) != 'Mn')

    return texto_sem_acento

def corrigir_acentos_ctes():
    """Corrige acentos em motivos de CTes"""
    app = create_app()

    with app.app_context():
        print("=" * 80)
        print("🔧 CORREÇÃO DE ACENTOS - Motivos de CTes Complementares")
        print("=" * 80)

        # Buscar CTes com motivo preenchido
        ctes = ConhecimentoTransporte.query.filter(
            ConhecimentoTransporte.motivo_complemento.isnot(None),
            ConhecimentoTransporte.motivo_complemento != ''
        ).all()

        print(f"\n📊 Total de CTes com motivo: {len(ctes)}")

        corrigidos = 0
        sem_alteracao = 0

        for cte in ctes:
            motivo_original = cte.motivo_complemento
            motivo_corrigido = remover_acentos(motivo_original)

            if motivo_original != motivo_corrigido:
                print(f"\n✏️  CTe {cte.numero_cte}:")
                print(f"   Antes:  {motivo_original[:80]}...")
                print(f"   Depois: {motivo_corrigido[:80]}...")

                cte.motivo_complemento = motivo_corrigido
                corrigidos += 1
            else:
                sem_alteracao += 1

        if corrigidos > 0:
            print(f"\n💾 Salvando alterações no banco...")
            db.session.commit()
            print(f"   ✅ {corrigidos} CTes corrigidos")
        else:
            print(f"\n✅ Nenhum CTe precisou ser corrigido")

        print(f"\n📊 Resumo:")
        print(f"   Corrigidos: {corrigidos}")
        print(f"   Sem alteração: {sem_alteracao}")
        print(f"   Total: {len(ctes)}")

        print("\n" + "=" * 80)
        print("✅ CORREÇÃO CONCLUÍDA!")
        print("=" * 80)

if __name__ == '__main__':
    corrigir_acentos_ctes()

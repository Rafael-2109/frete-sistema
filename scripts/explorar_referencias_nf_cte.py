"""
Script Exploratório: Mapear Relacionamento DFe → Referências de NFs
====================================================================

OBJETIVO:
    Buscar CTe específico e suas referências de NFs para validar:
    1. Nome do campo de relacionamento (refs_ids, referencia_ids, etc)
    2. Estrutura do modelo l10n_br_ciel_it_account.dfe.referencia
    3. Chaves de NF associadas ao CTe
    4. Extração do número da NF da chave (posições 26-33)

CTe DE TESTE:
    Chave: 35251121498155000170570010000025641000026852
    NFs esperadas:
    - 35251161724241000330550010001417681004039610 → NF 141768
    - 35251161724241000330550010001417691004039986 → NF 141769
    - 35251161724241000330550010001417701004040012 → NF 141770
    - 35251161724241000330550010001417711004040036 → NF 141771

AUTOR: Sistema de Fretes
DATA: 13/11/2025
"""

import sys
import os
from pprint import pprint
from datetime import datetime

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.odoo.utils.connection import get_odoo_connection


def extrair_numero_nf_da_chave(chave_nf):
    """
    Extrai o número da NF da chave de acesso (44 dígitos)

    Estrutura da chave de NF:
    - Posições 26-33: Número da NF (8 dígitos)

    Exemplo: 35251161724241000330550010001417681004039610
             ↑ UF (2)
               ↑ AAMM (4)
                   ↑ CNPJ (14)
                               ↑ Modelo (2)
                                 ↑ Série (3)
                                    ↑ Número NF (9) ← AQUI
                                             ↑ Tipo Emissão (1)
                                              ↑ Código Numérico (8)
                                                       ↑ DV (1)

    Args:
        chave_nf: Chave de acesso de 44 dígitos

    Returns:
        str: Número da NF (sem zeros à esquerda)
    """
    if not chave_nf or len(chave_nf) != 44:
        return None

    # Extrair número da NF (posições 25-33, índice Python 0-based)
    numero_nf = chave_nf[25:34]  # 9 dígitos

    # Remover zeros à esquerda
    numero_nf_limpo = str(int(numero_nf))

    return numero_nf_limpo


def explorar_referencias_nf():
    """
    Explora o relacionamento DFe → Referências de NFs
    """
    print("=" * 100)
    print("🔍 EXPLORANDO RELACIONAMENTO DFe → REFERÊNCIAS DE NFs")
    print("=" * 100)
    print()

    try:
        # 1. Conectar no Odoo
        print("1️⃣ Conectando no Odoo...")
        odoo = get_odoo_connection()

        if not odoo.authenticate():
            print("❌ Erro: Falha na autenticação")
            return

        print("✅ Conectado com sucesso!")
        print()

        # 2. Buscar CTe pela chave de acesso
        print("2️⃣ Buscando CTe com chave: 35251121498155000170570010000025641000026852")
        chave_cte = "35251121498155000170570010000025641000026852"

        filtro_chave = [
            ("protnfe_infnfe_chnfe", "=", chave_cte)
        ]

        # Buscar TODOS os campos para identificar o relacionamento
        cte = odoo.search_read(
            'l10n_br_ciel_it_account.dfe',
            filtro_chave,
            limit=1
        )

        if not cte or len(cte) == 0:
            print("❌ CTe não encontrado!")
            return

        cte_data = cte[0]
        cte_id = cte_data.get('id')

        print(f"✅ CTe encontrado!")
        print(f"   ID: {cte_id}")
        print(f"   Nome: {cte_data.get('name')}")
        print()

        # 3. Identificar campos de relacionamento (terminam com _ids)
        print("3️⃣ Identificando campos de relacionamento no CTe...")
        print()

        campos_relacionamento = []
        for campo, valor in cte_data.items():
            if campo.endswith('_ids') and isinstance(valor, list) and len(valor) > 0:
                campos_relacionamento.append((campo, valor))

        print(f"✅ Encontrados {len(campos_relacionamento)} campos de relacionamento com dados:")
        print()

        for campo, valor in campos_relacionamento:
            print(f"   📌 {campo:40} → {len(valor)} registro(s)")

        print()
        print("=" * 100)

        # 4. Procurar especificamente por referências de NF
        print()
        print("4️⃣ Buscando campo de referências de NF...")
        print()

        campo_referencia = None
        ids_referencia = []

        # Tentar nomes comuns
        nomes_possiveis = ['refs_ids', 'referencia_ids', 'infdoc_ids', 'documento_referencia_ids', 'nfe_ref_ids']

        for nome in nomes_possiveis:
            if nome in cte_data and isinstance(cte_data[nome], list) and len(cte_data[nome]) > 0:
                campo_referencia = nome
                ids_referencia = cte_data[nome]
                print(f"✅ Campo encontrado: {nome}")
                print(f"   IDs: {ids_referencia}")
                break

        if not campo_referencia:
            print("⚠️  Campo de referências não encontrado nos nomes comuns")
            print()
            print("📋 Todos os campos xxx_ids disponíveis:")
            for campo, valor in campos_relacionamento:
                print(f"   - {campo}: {valor}")
            print()
            print("💡 Por favor, identifique manualmente qual campo contém as referências de NF")
            return

        print()
        print("=" * 100)

        # 5. Buscar registros de referência
        print()
        print("5️⃣ Buscando registros de referência...")
        print()

        # Buscar campos do modelo de referência
        print("   🔍 Buscando estrutura do modelo l10n_br_ciel_it_account.dfe.referencia...")

        campos_referencia_info = odoo.execute_kw(
            'l10n_br_ciel_it_account.dfe.referencia',
            'fields_get',
            [],
            {'attributes': ['string', 'type']}
        )

        print(f"   ✅ Modelo tem {len(campos_referencia_info)} campos")
        print()

        # Buscar registros
        referencias = odoo.read(
            'l10n_br_ciel_it_account.dfe.referencia',
            ids_referencia
        )

        print(f"✅ Encontrados {len(referencias)} registro(s) de referência")
        print()

        # 6. Extrair chaves de NF
        print("=" * 100)
        print()
        print("6️⃣ EXTRAINDO CHAVES DE NF E NÚMEROS...")
        print()

        chaves_nf_encontradas = []
        numeros_nf_extraidos = []

        for i, ref in enumerate(referencias, 1):
            print(f"📋 Referência {i}:")
            print(f"   ID: {ref.get('id')}")

            # Procurar campo com chave de NF
            chave_nf = None
            campo_chave = None

            # Tentar campos comuns
            campos_chave_possiveis = [
                'infdoc_infnfe_chave',
                'chave_nfe',
                'chave_acesso',
                'nfe_chave',
                'chave'
            ]

            for nome_campo in campos_chave_possiveis:
                if nome_campo in ref and ref[nome_campo]:
                    chave_nf = ref[nome_campo]
                    campo_chave = nome_campo
                    break

            if chave_nf:
                print(f"   ✅ Campo da chave: {campo_chave}")
                print(f"   📄 Chave NF: {chave_nf}")

                # Extrair número da NF
                numero_nf = extrair_numero_nf_da_chave(chave_nf)
                if numero_nf:
                    print(f"   🔢 Número NF extraído: {numero_nf}")
                    numeros_nf_extraidos.append(numero_nf)
                    chaves_nf_encontradas.append(chave_nf)
                else:
                    print(f"   ⚠️  Não foi possível extrair número da NF")
            else:
                print(f"   ⚠️  Chave de NF não encontrada")
                print(f"   📋 Campos disponíveis: {list(ref.keys())}")

            print()

        # 7. Resumo
        print("=" * 100)
        print()
        print("📊 RESUMO DA EXPLORAÇÃO")
        print("=" * 100)
        print()

        print(f"✅ CTe ID: {cte_id}")
        print(f"✅ Chave CTe: {chave_cte}")
        print(f"✅ Campo de relacionamento: {campo_referencia}")
        print(f"✅ Total de referências: {len(referencias)}")
        print()

        if chaves_nf_encontradas:
            print("📄 CHAVES DE NF ENCONTRADAS:")
            for chave in chaves_nf_encontradas:
                print(f"   - {chave}")
            print()

        if numeros_nf_extraidos:
            print("🔢 NÚMEROS DE NF EXTRAÍDOS:")
            for numero in numeros_nf_extraidos:
                print(f"   - {numero}")
            print()

            # Formato para armazenamento
            nfs_string = ",".join(numeros_nf_extraidos)
            nfs_json = numeros_nf_extraidos

            print("💾 FORMATOS DE ARMAZENAMENTO SUGERIDOS:")
            print()
            print(f"   String (TEXT): \"{nfs_string}\"")
            print(f"   JSON (TEXT):   {nfs_json}")
            print()

        # 8. Validação com NFs esperadas
        print("=" * 100)
        print()
        print("🎯 VALIDAÇÃO COM NFs ESPERADAS")
        print("=" * 100)
        print()

        nfs_esperadas = ["141768", "141769", "141770", "141771"]

        print("NFs Esperadas:")
        for nf in nfs_esperadas:
            status = "✅" if nf in numeros_nf_extraidos else "❌"
            print(f"   {status} NF {nf}")

        print()

        if set(nfs_esperadas) == set(numeros_nf_extraidos):
            print("✅ VALIDAÇÃO 100% CORRETA! Todas as NFs esperadas foram encontradas!")
        else:
            faltando = set(nfs_esperadas) - set(numeros_nf_extraidos)
            extras = set(numeros_nf_extraidos) - set(nfs_esperadas)

            if faltando:
                print(f"⚠️  NFs faltando: {faltando}")
            if extras:
                print(f"⚠️  NFs extras encontradas: {extras}")

        print()
        print("=" * 100)
        print()
        print("✅ EXPLORAÇÃO CONCLUÍDA!")
        print()

        # Salvar resultado em arquivo
        log_file = os.path.join(os.path.dirname(__file__), 'exploracao_referencias_nf.txt')

        with open(log_file, 'w', encoding='utf-8') as f:
            f.write("=" * 100 + "\n")
            f.write("EXPLORAÇÃO: RELACIONAMENTO DFe → REFERÊNCIAS DE NFs\n")
            f.write(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
            f.write("=" * 100 + "\n\n")

            f.write(f"CTe ID: {cte_id}\n")
            f.write(f"Chave CTe: {chave_cte}\n")
            f.write(f"Campo de relacionamento: {campo_referencia}\n")
            f.write(f"Total de referências: {len(referencias)}\n\n")

            f.write("CAMPO DA CHAVE NF: " + (campo_chave or 'NÃO ENCONTRADO') + "\n\n")

            f.write("CHAVES DE NF:\n")
            for chave in chaves_nf_encontradas:
                f.write(f"  - {chave}\n")
            f.write("\n")

            f.write("NÚMEROS DE NF EXTRAÍDOS:\n")
            for numero in numeros_nf_extraidos:
                f.write(f"  - {numero}\n")
            f.write("\n")

            f.write("FORMATO STRING: " + ",".join(numeros_nf_extraidos) + "\n")
            f.write("FORMATO JSON: " + str(numeros_nf_extraidos) + "\n\n")

            f.write("ESTRUTURA DO MODELO dfe.referencia:\n")
            for campo, info in campos_referencia_info.items():
                f.write(f"  {campo:50} | {info.get('string', '')[:40]:40} | {info.get('type')}\n")

        print(f"📄 Resultado salvo em: {log_file}")
        print()

    except Exception as e:
        print(f"❌ ERRO FATAL: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    explorar_referencias_nf()

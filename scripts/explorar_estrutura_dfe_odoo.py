"""
Script Exploratório: Mapear Estrutura do Modelo DFe no Odoo
=============================================================

OBJETIVO:
    Buscar um CTe real do Odoo e listar TODOS os campos disponíveis
    com seus valores para garantir mapeamento 100% preciso

MODELO: l10n_br_ciel_it_account.dfe
FILTRO: is_cte = True
CHAVE DE REFERÊNCIA: 35251138402404000265570010000001171188192945

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


def explorar_estrutura_dfe():
    """
    Explora a estrutura completa do modelo DFe no Odoo
    buscando um CTe real como exemplo
    """
    print("=" * 100)
    print("🔍 EXPLORANDO ESTRUTURA DO MODELO DFe NO ODOO")
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

        # 2. Buscar CTe pela chave de acesso conhecida
        print("2️⃣ Buscando CTe com chave de acesso: 35251138402404000265570010000001171188192945")
        chave_referencia = "35251138402404000265570010000001171188192945"

        filtro_chave = [
            ("protnfe_infnfe_chnfe", "=", chave_referencia)
        ]

        cte_chave = odoo.search_read(
            'l10n_br_ciel_it_account.dfe',
            filtro_chave,
            fields=['id', 'name'],
            limit=1
        )

        if cte_chave and len(cte_chave) > 0:
            print(f"✅ CTe encontrado pela chave!")
            print(f"   ID: {cte_chave[0].get('id')}")
            print(f"   Nome: {cte_chave[0].get('name')}")
            cte_id = cte_chave[0].get('id')
        else:
            # Se não encontrar pela chave, buscar qualquer CTe
            print("⚠️  CTe com essa chave não encontrado")
            print()
            print("3️⃣ Buscando QUALQUER CTe disponível...")

            filtro_generico = [
                "&",
                "|",
                ("active", "=", True),
                ("active", "=", False),
                ("is_cte", "=", True)
            ]

            ctes = odoo.search_read(
                'l10n_br_ciel_it_account.dfe',
                filtro_generico,
                fields=['id', 'name', 'protnfe_infnfe_chnfe'],
                limit=1
            )

            if not ctes or len(ctes) == 0:
                print("❌ NENHUM CTe encontrado no Odoo!")
                print()
                print("IMPORTANTE: Verifique se:")
                print("  - O campo 'is_cte' existe no modelo")
                print("  - Existem CTes cadastrados no sistema")
                print("  - O filtro está correto")
                return

            cte_id = ctes[0].get('id')
            print(f"✅ CTe encontrado!")
            print(f"   ID: {cte_id}")
            print(f"   Nome: {ctes[0].get('name')}")
            print(f"   Chave: {ctes[0].get('protnfe_infnfe_chnfe')}")

        print()
        print("=" * 100)

        # 3. Buscar TODOS os campos do modelo (metadados)
        print()
        print("4️⃣ Buscando LISTA DE TODOS OS CAMPOS do modelo l10n_br_ciel_it_account.dfe...")
        print()

        try:
            campos_info = odoo.execute_kw(
                'l10n_br_ciel_it_account.dfe',
                'fields_get',
                [],
                {'attributes': ['string', 'type', 'relation', 'required', 'readonly']}
            )

            print(f"✅ Total de campos no modelo: {len(campos_info)}")
            print()

            # Separar campos por categoria
            campos_texto = []
            campos_numero = []
            campos_data = []
            campos_boolean = []
            campos_relacionamento = []
            campos_outros = []

            for nome_campo, info in campos_info.items():
                tipo = info.get('type')
                label = info.get('string', '')

                if tipo in ['char', 'text']:
                    campos_texto.append((nome_campo, label, tipo))
                elif tipo in ['integer', 'float', 'monetary']:
                    campos_numero.append((nome_campo, label, tipo))
                elif tipo in ['date', 'datetime']:
                    campos_data.append((nome_campo, label, tipo))
                elif tipo == 'boolean':
                    campos_boolean.append((nome_campo, label, tipo))
                elif tipo in ['many2one', 'one2many', 'many2many']:
                    relacao = info.get('relation', '')
                    campos_relacionamento.append((nome_campo, label, tipo, relacao))
                else:
                    campos_outros.append((nome_campo, label, tipo))

            # Salvar em arquivo de log
            log_file = os.path.join(os.path.dirname(__file__), 'exploracao_dfe_campos.txt')

            with open(log_file, 'w', encoding='utf-8') as f:
                f.write("=" * 100 + "\n")
                f.write("LISTA COMPLETA DE CAMPOS DO MODELO l10n_br_ciel_it_account.dfe\n")
                f.write(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
                f.write("=" * 100 + "\n\n")

                f.write(f"TOTAL DE CAMPOS: {len(campos_info)}\n\n")

                # Campos de texto
                f.write("=" * 100 + "\n")
                f.write(f"CAMPOS DE TEXTO (char/text): {len(campos_texto)}\n")
                f.write("=" * 100 + "\n")
                for nome, label, tipo in sorted(campos_texto):
                    f.write(f"  {nome:60} | {label:40} | {tipo}\n")
                f.write("\n\n")

                # Campos numéricos
                f.write("=" * 100 + "\n")
                f.write(f"CAMPOS NUMÉRICOS (integer/float/monetary): {len(campos_numero)}\n")
                f.write("=" * 100 + "\n")
                for nome, label, tipo in sorted(campos_numero):
                    f.write(f"  {nome:60} | {label:40} | {tipo}\n")
                f.write("\n\n")

                # Campos de data
                f.write("=" * 100 + "\n")
                f.write(f"CAMPOS DE DATA (date/datetime): {len(campos_data)}\n")
                f.write("=" * 100 + "\n")
                for nome, label, tipo in sorted(campos_data):
                    f.write(f"  {nome:60} | {label:40} | {tipo}\n")
                f.write("\n\n")

                # Campos boolean
                f.write("=" * 100 + "\n")
                f.write(f"CAMPOS BOOLEAN: {len(campos_boolean)}\n")
                f.write("=" * 100 + "\n")
                for nome, label, tipo in sorted(campos_boolean):
                    f.write(f"  {nome:60} | {label:40} | {tipo}\n")
                f.write("\n\n")

                # Campos de relacionamento
                f.write("=" * 100 + "\n")
                f.write(f"CAMPOS DE RELACIONAMENTO (many2one/one2many/many2many): {len(campos_relacionamento)}\n")
                f.write("=" * 100 + "\n")
                for nome, label, tipo, relacao in sorted(campos_relacionamento):
                    f.write(f"  {nome:60} | {label:30} | {tipo:15} | → {relacao}\n")
                f.write("\n\n")

                # Outros campos
                if campos_outros:
                    f.write("=" * 100 + "\n")
                    f.write(f"OUTROS CAMPOS: {len(campos_outros)}\n")
                    f.write("=" * 100 + "\n")
                    for nome, label, tipo in sorted(campos_outros):
                        f.write(f"  {nome:60} | {label:40} | {tipo}\n")
                    f.write("\n\n")

            print(f"✅ Lista completa salva em: {log_file}")
            print()

        except Exception as e:
            print(f"⚠️  Erro ao buscar metadados dos campos: {e}")
            print()

        # 4. Buscar TODOS os dados do CTe específico
        print()
        print("5️⃣ Buscando TODOS os dados do CTe encontrado...")
        print()

        # Não passar 'fields' para buscar TODOS os campos
        cte_completo = odoo.read(
            'l10n_br_ciel_it_account.dfe',
            [cte_id]
        )

        if not cte_completo or len(cte_completo) == 0:
            print("❌ Erro ao buscar dados completos do CTe")
            return

        cte_data = cte_completo[0]

        print(f"✅ Dados do CTe carregados!")
        print(f"   Total de campos retornados: {len(cte_data)}")
        print()

        # 5. Salvar dados em arquivo
        log_file_dados = os.path.join(os.path.dirname(__file__), 'exploracao_dfe_dados.txt')

        with open(log_file_dados, 'w', encoding='utf-8') as f:
            f.write("=" * 100 + "\n")
            f.write("DADOS COMPLETOS DE UM CTe REAL DO ODOO\n")
            f.write(f"CTe ID: {cte_id}\n")
            f.write(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
            f.write("=" * 100 + "\n\n")

            # Ordenar campos alfabeticamente
            for campo in sorted(cte_data.keys()):
                valor = cte_data.get(campo)

                # Formatar valor para exibição
                if isinstance(valor, (list, tuple)) and len(valor) == 2 and isinstance(valor[0], int):
                    # Relacionamento many2one: [id, nome]
                    valor_formatado = f"[{valor[0]}, '{valor[1]}']"
                elif isinstance(valor, list) and all(isinstance(x, int) for x in valor):
                    # Relacionamento one2many/many2many: [id1, id2, ...]
                    valor_formatado = f"[{', '.join(map(str, valor))}] ({len(valor)} itens)"
                elif isinstance(valor, str) and len(valor) > 100:
                    # Texto longo (pode ser XML, PDF base64, etc)
                    valor_formatado = f"{valor[:100]}... ({len(valor)} caracteres)"
                else:
                    valor_formatado = str(valor)

                f.write(f"{campo:60} = {valor_formatado}\n")

        print(f"✅ Dados completos salvos em: {log_file_dados}")
        print()

        # 6. Exibir campos CRÍTICOS para CTe (preview)
        print()
        print("=" * 100)
        print("📋 PREVIEW - CAMPOS CRÍTICOS PARA CTe")
        print("=" * 100)
        print()

        campos_criticos = [
            ('id', 'ID do DFe'),
            ('name', 'Nome/Número'),
            ('active', 'Ativo'),
            ('is_cte', 'É CTe?'),
            ('l10n_br_status', 'Status'),
            ('protnfe_infnfe_chnfe', 'Chave de Acesso'),
            ('nfe_infnfe_ide_nnf', 'Número CTe'),
            ('nfe_infnfe_ide_serie', 'Série'),
            ('nfe_infnfe_ide_dhemi', 'Data Emissão'),
            ('nfe_infnfe_total_icmstot_vnf', 'Valor Total'),
            ('nfe_infnfe_total_icms_vfrete', 'Valor Frete'),
            ('nfe_infnfe_total_icms_vicms', 'Valor ICMS'),
            ('nfe_infnfe_emit_cnpj', 'CNPJ Emitente'),
            ('nfe_infnfe_emit_xnome', 'Nome Emitente'),
            ('nfe_infnfe_dest_cnpj', 'CNPJ Destinatário'),
            ('nfe_infnfe_rem_cnpj', 'CNPJ Remetente'),
            ('nfe_infnfe_exped_cnpj', 'CNPJ Expedidor'),
            ('nfe_infnfe_infadic_infcpl', 'Informações Complementares'),
            ('l10n_br_pdf_dfe', 'PDF (base64)'),
            ('l10n_br_pdf_dfe_fname', 'Nome arquivo PDF'),
            ('l10n_br_xml_dfe', 'XML (base64)'),
            ('l10n_br_xml_dfe_fname', 'Nome arquivo XML'),
        ]

        for campo, descricao in campos_criticos:
            valor = cte_data.get(campo)

            # Formatar valor para exibição
            if valor is None:
                valor_exibir = "NULL"
            elif isinstance(valor, (list, tuple)) and len(valor) == 2:
                valor_exibir = f"[{valor[0]}, '{valor[1]}']"
            elif isinstance(valor, list):
                valor_exibir = f"[{len(valor)} itens]"
            elif isinstance(valor, str) and len(valor) > 80:
                valor_exibir = f"{valor[:80]}... ({len(valor)} chars)"
            else:
                valor_exibir = str(valor)

            status = "✅" if valor else "⚠️ "
            print(f"{status} {descricao:35} | {campo:45} = {valor_exibir}")

        print()
        print("=" * 100)
        print()
        print("✅ EXPLORAÇÃO CONCLUÍDA COM SUCESSO!")
        print()
        print(f"📄 Arquivos gerados:")
        print(f"   1. {log_file}")
        print(f"   2. {log_file_dados}")
        print()
        print("💡 Use esses arquivos como referência para criar o modelo ConhecimentoTransporte")
        print()

    except Exception as e:
        print(f"❌ ERRO FATAL: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    explorar_estrutura_dfe()

"""
Script para investigar CTe duplicado no ODOO

Busca no Odoo todos os DFes com a chave de acesso duplicada
para entender por que existem múltiplos registros

Chave investigada: 35240647543687000175570010000059641031340579
"""

import sys
import os
from pprint import pprint
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.odoo.utils.connection import get_odoo_connection

def investigar_cte_odoo():
    """Investiga CTe duplicado no Odoo"""

    chave_acesso = '35240647543687000175570010000059641031340579'

    print("=" * 100)
    print("🔍 INVESTIGAÇÃO DE CTE DUPLICADO NO ODOO")
    print("=" * 100)
    print(f"Chave de Acesso: {chave_acesso}")
    print()

    try:
        # Conectar ao Odoo
        odoo = get_odoo_connection()

        if not odoo.authenticate():
            print("❌ Erro: Falha na autenticação com Odoo")
            return

        print("✅ Conectado ao Odoo com sucesso!")
        print()

        # 1. Buscar TODOS os DFes com essa chave de acesso
        print("📊 1. BUSCANDO TODOS OS DFes COM ESSA CHAVE DE ACESSO NO ODOO:")
        print("-" * 100)

        filtros = [
            '&',
            '|',
            ('active', '=', True),
            ('active', '=', False),
            ('protnfe_infnfe_chnfe', '=', chave_acesso)
        ]

        campos = [
            'id',
            'name',
            'active',
            'is_cte',
            'l10n_br_status',
            'l10n_br_data_entrada',
            'l10n_br_tipo_pedido',
            'write_date',
            'create_date',

            # Chave e numeração
            'protnfe_infnfe_chnfe',
            'nfe_infnfe_ide_nnf',
            'nfe_infnfe_ide_serie',

            # Data
            'nfe_infnfe_ide_dhemi',

            # Valores
            'nfe_infnfe_total_icmstot_vnf',
            'nfe_infnfe_total_icms_vfrete',
            'nfe_infnfe_total_icms_vicms',

            # Emissor
            'nfe_infnfe_emit_cnpj',
            'nfe_infnfe_emit_xnome',

            # Destinatário
            'nfe_infnfe_dest_cnpj',

            # Remetente
            'nfe_infnfe_rem_cnpj',

            # Relacionamentos
            'partner_id',
            'invoice_ids',
            'purchase_fiscal_id',

            # Referências de NFs
            'refs_ids',
        ]

        print(f"🔍 Filtro: protnfe_infnfe_chnfe = {chave_acesso}")
        print()

        dfes = odoo.execute_kw(
            'l10n_br_ciel_it_account.dfe',
            'search_read',
            [filtros],
            {'fields': campos}
        )

        if not dfes:
            print("❌ NENHUM DFe encontrado no Odoo com essa chave de acesso!")
            print()
            return

        print(f"✅ Encontrados {len(dfes)} DFe(s) no Odoo:")
        print()

        # Mapear status
        status_map = {
            '01': 'Rascunho',
            '02': 'Sincronizado',
            '03': 'Ciência/Confirmado',
            '04': 'PO',
            '05': 'Rateio',
            '06': 'Concluído',
            '07': 'Rejeitado'
        }

        # Processar cada DFe
        for idx, dfe in enumerate(dfes, 1):
            print(f"{'=' * 100}")
            print(f"📋 DFe {idx} de {len(dfes)}")
            print(f"{'=' * 100}")
            print()

            print(f"🆔 IDENTIFICAÇÃO:")
            print(f"   - ID Odoo: {dfe.get('id')}")
            print(f"   - Name: {dfe.get('name')}")
            print(f"   - Ativo: {dfe.get('active')}")
            print(f"   - É CTe: {dfe.get('is_cte')}")
            print()

            print(f"📅 DATAS:")
            print(f"   - Criado em (create_date): {dfe.get('create_date')}")
            print(f"   - Atualizado em (write_date): {dfe.get('write_date')}")
            print(f"   - Data Emissão CTe: {dfe.get('nfe_infnfe_ide_dhemi')}")
            print(f"   - Data Entrada: {dfe.get('l10n_br_data_entrada')}")
            print()

            print(f"📊 STATUS E WORKFLOW:")
            status_code = dfe.get('l10n_br_status')
            print(f"   - Status Código: {status_code}")
            print(f"   - Status Descrição: {status_map.get(status_code, 'Desconhecido')}")
            print(f"   - Tipo Pedido: {dfe.get('l10n_br_tipo_pedido')}")
            print()

            print(f"📄 DADOS DO CTe:")
            print(f"   - Chave de Acesso: {dfe.get('protnfe_infnfe_chnfe')}")
            print(f"   - Número: {dfe.get('nfe_infnfe_ide_nnf')}")
            print(f"   - Série: {dfe.get('nfe_infnfe_ide_serie')}")
            print()

            print(f"💰 VALORES:")
            print(f"   - Valor Total: R$ {dfe.get('nfe_infnfe_total_icmstot_vnf', 0):,.2f}")
            print(f"   - Valor Frete: R$ {dfe.get('nfe_infnfe_total_icms_vfrete', 0):,.2f}")
            print(f"   - Valor ICMS: R$ {dfe.get('nfe_infnfe_total_icms_vicms', 0):,.2f}")
            print()

            print(f"🏢 PARTES ENVOLVIDAS:")
            print(f"   - CNPJ Emitente: {dfe.get('nfe_infnfe_emit_cnpj')}")
            print(f"   - Nome Emitente: {dfe.get('nfe_infnfe_emit_xnome')}")
            print(f"   - CNPJ Destinatário: {dfe.get('nfe_infnfe_dest_cnpj')}")
            print(f"   - CNPJ Remetente: {dfe.get('nfe_infnfe_rem_cnpj')}")
            print()

            print(f"🔗 RELACIONAMENTOS ODOO:")
            partner_id = dfe.get('partner_id')
            if isinstance(partner_id, (list, tuple)):
                print(f"   - Partner ID: {partner_id[0]} ({partner_id[1]})")
            else:
                print(f"   - Partner ID: {partner_id}")

            invoice_ids = dfe.get('invoice_ids')
            print(f"   - Invoice IDs: {invoice_ids}")

            purchase_fiscal_id = dfe.get('purchase_fiscal_id')
            if isinstance(purchase_fiscal_id, (list, tuple)):
                print(f"   - Purchase Fiscal ID: {purchase_fiscal_id[0]} ({purchase_fiscal_id[1]})")
            else:
                print(f"   - Purchase Fiscal ID: {purchase_fiscal_id}")
            print()

            print(f"📦 REFERÊNCIAS DE NFs:")
            refs_ids = dfe.get('refs_ids')
            if refs_ids:
                print(f"   - Total de refs_ids: {len(refs_ids)}")
                print(f"   - IDs: {refs_ids[:10]}{'...' if len(refs_ids) > 10 else ''}")

                # Buscar números das NFs
                try:
                    referencias = odoo.read(
                        'l10n_br_ciel_it_account.dfe.referencia',
                        refs_ids[:10],  # Limitar a 10 para não sobrecarregar
                        ['infdoc_infnfe_chave']
                    )

                    numeros_nfs = []
                    for ref in referencias:
                        chave_nf = ref.get('infdoc_infnfe_chave')
                        if chave_nf and len(chave_nf) == 44:
                            numero_nf = chave_nf[25:34]
                            numero_nf_limpo = str(int(numero_nf))
                            numeros_nfs.append(numero_nf_limpo)

                    if numeros_nfs:
                        print(f"   - Números NFs: {', '.join(numeros_nfs)}")
                except Exception as e:
                    print(f"   - ⚠️ Erro ao buscar NFs: {e}")
            else:
                print(f"   - Nenhuma referência de NF")
            print()

            print(f"📋 JSON COMPLETO:")
            print("-" * 100)
            print(json.dumps(dfe, indent=2, default=str, ensure_ascii=False))
            print()

        # 2. Comparar os registros (se houver múltiplos)
        if len(dfes) > 1:
            print()
            print("=" * 100)
            print("🔬 COMPARAÇÃO ENTRE OS REGISTROS:")
            print("=" * 100)
            print()

            # Campos importantes para comparar
            campos_comparacao = [
                'id', 'name', 'active', 'is_cte', 'l10n_br_status',
                'create_date', 'write_date', 'nfe_infnfe_ide_dhemi',
                'l10n_br_data_entrada', 'nfe_infnfe_total_icmstot_vnf',
                'partner_id', 'invoice_ids', 'purchase_fiscal_id', 'refs_ids'
            ]

            print("📊 DIFERENÇAS ENTRE OS REGISTROS:")
            print()

            for campo in campos_comparacao:
                valores = [dfe.get(campo) for dfe in dfes]
                valores_unicos = set(str(v) for v in valores)

                if len(valores_unicos) > 1:
                    print(f"⚠️  {campo}:")
                    for idx, valor in enumerate(valores, 1):
                        print(f"      DFe {idx}: {valor}")
                    print()

        # 3. Resumo e diagnóstico
        print()
        print("=" * 100)
        print("📝 DIAGNÓSTICO:")
        print("=" * 100)
        print()

        if len(dfes) > 1:
            print(f"🔴 PROBLEMA IDENTIFICADO:")
            print(f"   Existem {len(dfes)} DFes no Odoo com a MESMA chave de acesso!")
            print()

            # Analisar se são reprocessamentos
            create_dates = [dfe.get('create_date') for dfe in dfes]
            print(f"   Datas de criação:")
            for idx, date in enumerate(create_dates, 1):
                print(f"      DFe {idx}: {date}")
            print()

            # Analisar se status são diferentes
            status = [dfe.get('l10n_br_status') for dfe in dfes]
            if len(set(status)) > 1:
                print(f"   ⚠️  Status DIFERENTES entre os DFes:")
                for idx, s in enumerate(status, 1):
                    print(f"      DFe {idx}: {s} ({status_map.get(s, 'Desconhecido')})")
            else:
                print(f"   ✅ Todos os DFes têm o mesmo status: {status[0]}")
            print()

            # Analisar active
            actives = [dfe.get('active') for dfe in dfes]
            if len(set(actives)) > 1:
                print(f"   ⚠️  Flag ACTIVE DIFERENTE:")
                for idx, a in enumerate(actives, 1):
                    print(f"      DFe {idx}: {a}")
            else:
                print(f"   ✅ Todos os DFes têm a mesma flag active: {actives[0]}")
            print()

            print(f"💡 POSSÍVEIS CAUSAS:")
            print(f"   1. Reprocessamento no Odoo (mesmo CTe importado múltiplas vezes)")
            print(f"   2. CTe foi cancelado e um novo DFe foi criado")
            print(f"   3. Erro no processo de sincronização do Odoo")
            print(f"   4. CTe foi editado e um novo registro foi criado")
            print()

            print(f"🔧 SOLUÇÃO RECOMENDADA:")
            print(f"   1. Verificar qual DFe é o CORRETO (mais recente? active=True?)")
            print(f"   2. Ajustar cte_service.py para buscar por chave_acesso PRIMEIRO")
            print(f"   3. Se encontrar múltiplos, escolher o mais recente ou active=True")
            print(f"   4. Atualizar o registro existente ao invés de criar novo")
        else:
            print(f"✅ Apenas 1 DFe encontrado no Odoo (esperado)")
            print()
            print(f"💡 OBSERVAÇÃO:")
            print(f"   O erro de duplicate key pode ter ocorrido por:")
            print(f"   1. Sincronização simultânea (race condition)")
            print(f"   2. Tentativa de inserir o mesmo DFe múltiplas vezes")
            print(f"   3. Transação não commitada anteriormente")

        print()
        print("=" * 100)

    except Exception as e:
        print(f"❌ Erro ao buscar no Odoo: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    investigar_cte_odoo()

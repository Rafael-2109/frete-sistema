"""
Script DIRETO para investigar CTe duplicado no ODOO
Sem dependências do app - conecta direto

Chave investigada: 35240647543687000175570010000059641031340579
"""

import xmlrpc.client
import os
import json
from dotenv import load_dotenv

# Carregar .env
load_dotenv()

def investigar_cte_odoo():
    """Investiga CTe duplicado no Odoo"""

    chave_acesso = '35240647543687000175570010000059641031340579'

    # Credenciais do Odoo
    url = os.getenv('ODOO_URL')
    db = os.getenv('ODOO_DB')
    username = os.getenv('ODOO_USERNAME')
    password = os.getenv('ODOO_API_KEY') or os.getenv('ODOO_PASSWORD')

    if not all([url, db, username, password]):
        print("❌ Credenciais do Odoo não configuradas no .env")
        return

    print("=" * 100)
    print("🔍 INVESTIGAÇÃO DE CTE DUPLICADO NO ODOO")
    print("=" * 100)
    print(f"Chave de Acesso: {chave_acesso}")
    print(f"Odoo URL: {url}")
    print(f"Odoo DB: {db}")
    print()

    try:
        # Conectar ao Odoo
        common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
        uid = common.authenticate(db, username, password, {})

        if not uid:
            print("❌ Falha na autenticação do Odoo")
            return

        print(f"✅ Autenticado no Odoo - UID: {uid}")
        print()

        models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

        # 1. Buscar TODOS os DFes com essa chave de acesso
        print("📊 BUSCANDO TODOS OS DFes COM ESSA CHAVE DE ACESSO NO ODOO:")
        print("-" * 100)

        filtros = [
            '&',
            '|',
            ('active', '=', True),
            ('active', '=', False),
            ('protnfe_infnfe_chnfe', '=', chave_acesso)
        ]

        campos = [
            'id', 'name', 'active', 'is_cte', 'l10n_br_status',
            'l10n_br_data_entrada', 'l10n_br_tipo_pedido',
            'write_date', 'create_date',
            'protnfe_infnfe_chnfe', 'nfe_infnfe_ide_nnf', 'nfe_infnfe_ide_serie',
            'nfe_infnfe_ide_dhemi', 'nfe_infnfe_total_icmstot_vnf',
            'nfe_infnfe_total_icms_vfrete', 'nfe_infnfe_total_icms_vicms',
            'nfe_infnfe_emit_cnpj', 'nfe_infnfe_emit_xnome',
            'nfe_infnfe_dest_cnpj', 'nfe_infnfe_rem_cnpj',
            'partner_id', 'invoice_ids', 'purchase_fiscal_id', 'refs_ids'
        ]

        print(f"🔍 Buscando DFes com chave: {chave_acesso}")
        print()

        dfes = models.execute_kw(
            db, uid, password,
            'l10n_br_ciel_it_account.dfe', 'search_read',
            [filtros],
            {'fields': campos}
        )

        if not dfes:
            print("❌ NENHUM DFe encontrado no Odoo com essa chave de acesso!")
            return

        print(f"✅ Encontrados {len(dfes)} DFe(s) no Odoo")
        print()

        # Status map
        status_map = {
            '01': 'Rascunho', '02': 'Sincronizado', '03': 'Ciência/Confirmado',
            '04': 'PO', '05': 'Rateio', '06': 'Concluído', '07': 'Rejeitado'
        }

        # Processar cada DFe
        for idx, dfe in enumerate(dfes, 1):
            print(f"{'=' * 100}")
            print(f"📋 DFe {idx} de {len(dfes)}")
            print(f"{'=' * 100}")
            print()

            print(f"🆔 IDENTIFICAÇÃO:")
            print(f"   ID Odoo: {dfe.get('id')}")
            print(f"   Name: {dfe.get('name')}")
            print(f"   Ativo: {dfe.get('active')}")
            print(f"   É CTe: {dfe.get('is_cte')}")
            print()

            print(f"📅 DATAS:")
            print(f"   Criado em: {dfe.get('create_date')}")
            print(f"   Atualizado em: {dfe.get('write_date')}")
            print(f"   Data Emissão: {dfe.get('nfe_infnfe_ide_dhemi')}")
            print(f"   Data Entrada: {dfe.get('l10n_br_data_entrada')}")
            print()

            status_code = dfe.get('l10n_br_status')
            print(f"📊 STATUS:")
            print(f"   Código: {status_code}")
            print(f"   Descrição: {status_map.get(status_code, 'Desconhecido')}")
            print(f"   Tipo Pedido: {dfe.get('l10n_br_tipo_pedido')}")
            print()

            print(f"📄 CTe:")
            print(f"   Chave: {dfe.get('protnfe_infnfe_chnfe')}")
            print(f"   Número: {dfe.get('nfe_infnfe_ide_nnf')}")
            print(f"   Série: {dfe.get('nfe_infnfe_ide_serie')}")
            print()

            print(f"💰 VALORES:")
            print(f"   Total: R$ {dfe.get('nfe_infnfe_total_icmstot_vnf', 0):,.2f}")
            print(f"   Frete: R$ {dfe.get('nfe_infnfe_total_icms_vfrete') or 0:,.2f}")
            print(f"   ICMS: R$ {dfe.get('nfe_infnfe_total_icms_vicms', 0):,.2f}")
            print()

            print(f"🏢 PARTES:")
            print(f"   Emitente: {dfe.get('nfe_infnfe_emit_cnpj')} - {dfe.get('nfe_infnfe_emit_xnome')}")
            print(f"   Destinatário: {dfe.get('nfe_infnfe_dest_cnpj')}")
            print(f"   Remetente: {dfe.get('nfe_infnfe_rem_cnpj')}")
            print()

            print(f"🔗 RELACIONAMENTOS:")
            partner = dfe.get('partner_id')
            print(f"   Partner: {partner[0] if isinstance(partner, (list, tuple)) else partner}")
            print(f"   Invoices: {dfe.get('invoice_ids')}")
            purchase = dfe.get('purchase_fiscal_id')
            print(f"   Purchase: {purchase[0] if isinstance(purchase, (list, tuple)) else purchase}")
            print()

            refs = dfe.get('refs_ids')
            if refs:
                print(f"📦 REFERÊNCIAS:")
                print(f"   Total: {len(refs)}")
                print(f"   IDs: {refs[:5]}{'...' if len(refs) > 5 else ''}")

                # Buscar NFs
                try:
                    referencias = models.execute_kw(
                        db, uid, password,
                        'l10n_br_ciel_it_account.dfe.referencia', 'read',
                        [refs[:10]],
                        {'fields': ['infdoc_infnfe_chave']}
                    )

                    nfs = []
                    for ref in referencias:
                        chave_nf = ref.get('infdoc_infnfe_chave')
                        if chave_nf and len(chave_nf) == 44:
                            nfs.append(str(int(chave_nf[25:34])))

                    if nfs:
                        print(f"   NFs: {', '.join(nfs)}")
                except Exception as e:
                    print(f"   ⚠️ Erro ao buscar NFs: {e}")
            print()

            print(f"📋 JSON COMPLETO:")
            print(json.dumps(dfe, indent=2, default=str, ensure_ascii=False))
            print()

        # Comparar se múltiplos
        if len(dfes) > 1:
            print()
            print("=" * 100)
            print("🔬 COMPARAÇÃO:")
            print("=" * 100)
            print()

            campos_comp = [
                'id', 'name', 'active', 'l10n_br_status',
                'create_date', 'write_date', 'nfe_infnfe_total_icmstot_vnf',
                'invoice_ids', 'purchase_fiscal_id'
            ]

            print("📊 DIFERENÇAS:")
            for campo in campos_comp:
                valores = [str(dfe.get(campo)) for dfe in dfes]
                if len(set(valores)) > 1:
                    print(f"\n⚠️  {campo}:")
                    for i, v in enumerate(valores, 1):
                        print(f"      DFe {i}: {v}")

        # Diagnóstico
        print()
        print("=" * 100)
        print("📝 DIAGNÓSTICO:")
        print("=" * 100)

        if len(dfes) > 1:
            print(f"\n🔴 {len(dfes)} DFes com MESMA chave no Odoo!")
            print(f"\n   IDs: {[d['id'] for d in dfes]}")
            print(f"   Criados em: {[d.get('create_date') for d in dfes]}")
            print(f"   Status: {[status_map.get(d.get('l10n_br_status'), 'Desc') for d in dfes]}")
            print(f"   Active: {[d.get('active') for d in dfes]}")

            print(f"\n💡 CAUSA PROVÁVEL:")
            print(f"   - Odoo criou múltiplos DFes para o mesmo CTe")
            print(f"   - Reprocessamento ou reimportação")

            print(f"\n🔧 SOLUÇÃO:")
            print(f"   Alterar cte_service.py para:")
            print(f"   1. Buscar por chave_acesso PRIMEIRO")
            print(f"   2. Se múltiplos, escolher o mais recente (write_date)")
            print(f"   3. Atualizar existente ao invés de inserir")
        else:
            print(f"\n✅ Apenas 1 DFe (normal)")

        print("\n" + "=" * 100)

    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    investigar_cte_odoo()

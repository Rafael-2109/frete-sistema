#!/usr/bin/env python3
"""
Script para popular dados de teste do Recebimento (Fase 1 + Fase 2).

Executa o job de validação para um período específico,
simulando como o scheduler fará automaticamente.

Período: 13/01/2026 a 15/01/2026
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from datetime import datetime, timedelta

# Período de teste
DATA_INICIO = datetime(2026, 1, 13, 0, 0, 0)
DATA_FIM = datetime(2026, 1, 15, 23, 59, 59)

# CNPJs do grupo a ignorar
CNPJS_IGNORAR = ['61724241', '18467441']


def executar_teste():
    """Executa o teste de validação de recebimento."""
    from app import create_app, db
    from app.recebimento.jobs.validacao_recebimento_job import ValidacaoRecebimentoJob
    from app.recebimento.services.depara_service import DeparaService
    from app.odoo.utils.connection import get_odoo_connection

    app = create_app()
    with app.app_context():
        print("=" * 70)
        print("POPULANDO DADOS DE TESTE - RECEBIMENTO (FASE 1 + FASE 2)")
        print("=" * 70)
        print(f"Período: {DATA_INICIO.strftime('%d/%m/%Y')} a {DATA_FIM.strftime('%d/%m/%Y')}")
        print("=" * 70)

        # 1. SYNC DE-PARA
        print("\n[1/4] Sincronizando De-Para do Odoo...")
        try:
            depara_service = DeparaService()
            resultado_depara = depara_service.importar_do_odoo(limit=500)
            print(f"   ✅ Importados: {resultado_depara.get('importados', 0)}")
            print(f"   ✅ Atualizados: {resultado_depara.get('atualizados', 0)}")
            print(f"   ❌ Erros: {resultado_depara.get('erros', 0)}")
        except Exception as e:
            print(f"   ❌ Erro ao sincronizar De-Para: {e}")

        # 2. BUSCAR DFEs DO PERÍODO
        print("\n[2/4] Buscando DFEs de compra do período...")
        odoo = get_odoo_connection()
        if not odoo.authenticate():
            print("   ❌ Falha na autenticação com Odoo")
            return

        data_inicio_str = DATA_INICIO.strftime('%Y-%m-%d %H:%M:%S')
        data_fim_str = DATA_FIM.strftime('%Y-%m-%d %H:%M:%S')

        filtro = [
            ['l10n_br_tipo_pedido', '=', 'compra'],
            ['l10n_br_status', '=', '04'],  # Processado
            ['nfe_infnfe_ide_finnfe', '!=', '4'],  # Não é devolução
            ['is_cte', '=', False],  # Apenas NF-e
            ['write_date', '>=', data_inicio_str],
            ['write_date', '<=', data_fim_str]
        ]

        dfes = odoo.search_read(
            'l10n_br_ciel_it_account.dfe',
            filtro,
            fields=[
                'id', 'name', 'nfe_infnfe_ide_nnf', 'nfe_infnfe_ide_serie',
                'protnfe_infnfe_chnfe',
                'nfe_infnfe_emit_cnpj', 'nfe_infnfe_emit_xnome',
                'nfe_infnfe_ide_dhemi',
                'nfe_infnfe_total_icmstot_vnf',
                'write_date'
            ],
            limit=200
        )

        if not dfes:
            print("   ⚠️ Nenhum DFE encontrado no período")
            return

        # Filtrar CNPJs do grupo
        dfes_filtrados = []
        for dfe in dfes:
            cnpj = dfe.get('nfe_infnfe_emit_cnpj', '')
            cnpj_limpo = ''.join(c for c in cnpj if c.isdigit())
            ignorar = any(cnpj_limpo.startswith(p) for p in CNPJS_IGNORAR)
            if not ignorar:
                dfes_filtrados.append(dfe)

        print(f"   Total no Odoo: {len(dfes)}")
        print(f"   Após filtrar grupo: {len(dfes_filtrados)}")

        if not dfes_filtrados:
            print("   ⚠️ Todos os DFEs são do grupo interno")
            return

        # Mostrar DFEs encontrados
        print("\n   DFEs encontrados:")
        print("   " + "-" * 66)
        for dfe in dfes_filtrados[:15]:
            dfe_id = dfe.get('id')
            nf = dfe.get('nfe_infnfe_ide_nnf', 'N/A')
            razao = dfe.get('nfe_infnfe_emit_xnome', '')[:30]
            valor = dfe.get('nfe_infnfe_total_icmstot_vnf', 0)
            data = dfe.get('write_date', '')[:10]
            print(f"   ID {dfe_id:>6} | NF {nf:>9} | {razao:<30} | R$ {valor:>12,.2f} | {data}")

        if len(dfes_filtrados) > 15:
            print(f"   ... e mais {len(dfes_filtrados) - 15} DFEs")

        print("   " + "-" * 66)

        # 3. EXECUTAR VALIDAÇÃO
        print(f"\n[3/4] Executando validações (Fase 1 + Fase 2)...")

        from app.recebimento.models import ValidacaoFiscalDfe, ValidacaoNfPoDfe
        from app.recebimento.services.validacao_fiscal_service import ValidacaoFiscalService
        from app.recebimento.services.validacao_nf_po_service import ValidacaoNfPoService

        service_fiscal = ValidacaoFiscalService()
        service_nf_po = ValidacaoNfPoService()

        stats = {
            'processados': 0,
            'fase1': {'aprovados': 0, 'bloqueados': 0, 'primeira_compra': 0, 'erros': 0},
            'fase2': {'aprovados': 0, 'bloqueados': 0, 'erros': 0}
        }

        for i, dfe in enumerate(dfes_filtrados, 1):
            dfe_id = dfe.get('id')
            numero_nf = dfe.get('nfe_infnfe_ide_nnf')
            chave_nfe = dfe.get('protnfe_infnfe_chnfe')
            cnpj = dfe.get('nfe_infnfe_emit_cnpj', '')
            razao = dfe.get('nfe_infnfe_emit_xnome', '')
            cnpj_limpo = ''.join(c for c in cnpj if c.isdigit())

            print(f"\n   [{i}/{len(dfes_filtrados)}] DFE {dfe_id} - NF {numero_nf} ({razao[:25]})")

            # === FASE 1: VALIDAÇÃO FISCAL ===
            try:
                # Criar/atualizar registro
                registro1 = ValidacaoFiscalDfe.query.filter_by(odoo_dfe_id=dfe_id).first()
                if not registro1:
                    registro1 = ValidacaoFiscalDfe(
                        odoo_dfe_id=dfe_id,
                        numero_nf=numero_nf,
                        chave_nfe=chave_nfe,
                        cnpj_fornecedor=cnpj_limpo,
                        razao_fornecedor=razao,
                        status='validando'
                    )
                    db.session.add(registro1)
                else:
                    registro1.status = 'validando'
                db.session.commit()

                # Executar validação fiscal
                resultado1 = service_fiscal.validar_nf(dfe_id)

                # Atualizar status
                status1 = resultado1.get('status', 'erro')
                registro1.status = status1
                registro1.total_linhas = resultado1.get('linhas_validadas', 0)
                registro1.linhas_divergentes = len(resultado1.get('divergencias', []))
                registro1.linhas_primeira_compra = len(resultado1.get('primeira_compra', []))
                registro1.linhas_aprovadas = (
                    registro1.total_linhas -
                    registro1.linhas_divergentes -
                    registro1.linhas_primeira_compra
                )
                registro1.validado_em = datetime.utcnow()
                registro1.atualizado_em = datetime.utcnow()

                if resultado1.get('erro'):
                    registro1.erro_mensagem = resultado1['erro']

                db.session.commit()

                # Contabilizar
                if status1 == 'aprovado':
                    stats['fase1']['aprovados'] += 1
                    print(f"        Fase 1: ✅ APROVADO ({registro1.total_linhas} itens)")
                elif status1 == 'bloqueado':
                    stats['fase1']['bloqueados'] += 1
                    print(f"        Fase 1: ❌ BLOQUEADO ({registro1.linhas_divergentes} divergências)")
                elif status1 == 'primeira_compra':
                    stats['fase1']['primeira_compra'] += 1
                    print(f"        Fase 1: 🆕 PRIMEIRA COMPRA ({registro1.linhas_primeira_compra} itens)")
                else:
                    stats['fase1']['erros'] += 1
                    print(f"        Fase 1: ⚠️ {status1}")

            except Exception as e:
                print(f"        Fase 1: ❌ ERRO - {e}")
                stats['fase1']['erros'] += 1

            # === FASE 2: VALIDAÇÃO NF × PO ===
            try:
                resultado2 = service_nf_po.validar_dfe(dfe_id)

                status2 = resultado2.get('status', 'erro')

                # Contabilizar
                if status2 == 'aprovado':
                    stats['fase2']['aprovados'] += 1
                    print(f"        Fase 2: ✅ APROVADO ({resultado2.get('itens_match', 0)} matches)")
                elif status2 == 'bloqueado':
                    stats['fase2']['bloqueados'] += 1
                    motivo = resultado2.get('motivo', 'divergências')
                    print(f"        Fase 2: ❌ BLOQUEADO ({motivo})")
                else:
                    stats['fase2']['erros'] += 1
                    erro = resultado2.get('erro', status2)
                    print(f"        Fase 2: ⚠️ {erro}")

            except Exception as e:
                print(f"        Fase 2: ❌ ERRO - {e}")
                stats['fase2']['erros'] += 1

            stats['processados'] += 1

        # 4. RESUMO FINAL
        print("\n" + "=" * 70)
        print("RESUMO DA POPULAÇÃO DE DADOS")
        print("=" * 70)
        print(f"\nTotal DFEs processados: {stats['processados']}")
        print("\nFASE 1 - Validação Fiscal:")
        print(f"   ✅ Aprovados: {stats['fase1']['aprovados']}")
        print(f"   ❌ Bloqueados: {stats['fase1']['bloqueados']}")
        print(f"   🆕 Primeira Compra: {stats['fase1']['primeira_compra']}")
        print(f"   ⚠️ Erros: {stats['fase1']['erros']}")
        print("\nFASE 2 - Validação NF × PO:")
        print(f"   ✅ Aprovados: {stats['fase2']['aprovados']}")
        print(f"   ❌ Bloqueados: {stats['fase2']['bloqueados']}")
        print(f"   ⚠️ Erros: {stats['fase2']['erros']}")

        # Verificar registros no banco
        print("\n" + "-" * 70)
        print("REGISTROS NO BANCO:")
        total_fiscal = ValidacaoFiscalDfe.query.count()
        total_nf_po = ValidacaoNfPoDfe.query.count()
        print(f"   validacao_fiscal_dfe: {total_fiscal} registros")
        print(f"   validacao_nf_po_dfe: {total_nf_po} registros")

        print("\n" + "=" * 70)
        print("✅ POPULAÇÃO DE DADOS CONCLUÍDA!")
        print("=" * 70)


if __name__ == '__main__':
    executar_teste()

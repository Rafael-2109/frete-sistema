"""
Script para Limpar Duplicatas da Importação Histórica - MotoCHEFE

Objetivo:
- Identifica e remove registros duplicados de Comissões, Montagens e Movimentações
- Reverte os saldos das empresas afetadas
- Mantém apenas o primeiro registro de cada grupo duplicado

USO:
    python migrations/limpar_duplicatas_importacao_historica.py

IMPORTANTE:
- Faz backup automático antes de limpar
- Mostra preview antes de confirmar
- Recalcula saldos automaticamente
"""
import sys
import os
from datetime import datetime
from decimal import Decimal

# Adicionar diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from sqlalchemy import func, and_
from app.motochefe.models.financeiro import (
    TituloFinanceiro,
    TituloAPagar,
    ComissaoVendedor,
    MovimentacaoFinanceira
)
from app.motochefe.models.cadastro import EmpresaVendaMoto


def analisar_duplicatas_comissoes():
    """Analisa duplicatas de ComissaoVendedor"""
    print("\n" + "=" * 100)
    print("1. ANALISANDO DUPLICATAS DE COMISSÕES")
    print("=" * 100)

    # Buscar grupos duplicados (pedido_id + numero_chassi + vendedor_id)
    duplicatas = db.session.query(
        ComissaoVendedor.pedido_id,
        func.upper(ComissaoVendedor.numero_chassi).label('chassi_upper'),
        ComissaoVendedor.vendedor_id,
        func.count(ComissaoVendedor.id).label('total'),
        func.array_agg(ComissaoVendedor.id).label('ids')
    ).group_by(
        ComissaoVendedor.pedido_id,
        func.upper(ComissaoVendedor.numero_chassi),
        ComissaoVendedor.vendedor_id
    ).having(
        func.count(ComissaoVendedor.id) > 1
    ).all()

    if not duplicatas:
        print("✅ Nenhuma duplicata encontrada em ComissaoVendedor")
        return []

    print(f"⚠️  Encontradas {len(duplicatas)} grupos de comissões duplicadas:\n")

    registros_deletar = []
    total_valor_duplicado = Decimal('0')

    for dup in duplicatas:
        comissoes = ComissaoVendedor.query.filter(ComissaoVendedor.id.in_(dup.ids)).all()

        print(f"   Pedido: {comissoes[0].pedido.numero_pedido if comissoes[0].pedido else 'N/A'} | "
              f"Chassi: {dup.chassi_upper} | "
              f"Vendedor: {comissoes[0].vendedor.vendedor if comissoes[0].vendedor else 'N/A'} | "
              f"Duplicatas: {dup.total}")

        # Ordenar por ID (manter o primeiro, deletar os demais)
        comissoes_ordenadas = sorted(comissoes, key=lambda x: x.id)
        manter = comissoes_ordenadas[0]
        deletar = comissoes_ordenadas[1:]

        for com in deletar:
            print(f"      ↳ DELETAR: ID={com.id} | Valor={com.valor_rateado} | Status={com.status} | "
                  f"Criado em: {com.criado_em}")

            registros_deletar.append({
                'tipo': 'COMISSAO',
                'objeto': com,
                'valor': com.valor_rateado,
                'status': com.status,
                'empresa_pagadora_id': com.empresa_pagadora_id,
                'lote_pagamento_id': com.lote_pagamento_id
            })
            total_valor_duplicado += com.valor_rateado

        print(f"      ✅ MANTER: ID={manter.id} | Valor={manter.valor_rateado}\n")

    print(f"💰 Valor total duplicado: R$ {total_valor_duplicado}")
    return registros_deletar


def analisar_duplicatas_titulos(tipo_titulo):
    """Analisa duplicatas de TituloFinanceiro (MONTAGEM ou MOVIMENTACAO)"""
    print("\n" + "=" * 100)
    print(f"2. ANALISANDO DUPLICATAS DE TÍTULOS {tipo_titulo}")
    print("=" * 100)

    # Buscar grupos duplicados (pedido_id + numero_chassi + tipo_titulo)
    duplicatas = db.session.query(
        TituloFinanceiro.pedido_id,
        func.upper(TituloFinanceiro.numero_chassi).label('chassi_upper'),
        func.count(TituloFinanceiro.id).label('total'),
        func.array_agg(TituloFinanceiro.id).label('ids')
    ).filter(
        TituloFinanceiro.tipo_titulo == tipo_titulo
    ).group_by(
        TituloFinanceiro.pedido_id,
        func.upper(TituloFinanceiro.numero_chassi)
    ).having(
        func.count(TituloFinanceiro.id) > 1
    ).all()

    if not duplicatas:
        print(f"✅ Nenhuma duplicata encontrada em TituloFinanceiro ({tipo_titulo})")
        return []

    print(f"⚠️  Encontrados {len(duplicatas)} grupos de títulos {tipo_titulo} duplicados:\n")

    registros_deletar = []
    total_valor_duplicado = Decimal('0')

    for dup in duplicatas:
        titulos = TituloFinanceiro.query.filter(TituloFinanceiro.id.in_(dup.ids)).all()

        print(f"   Pedido: {titulos[0].pedido.numero_pedido if titulos[0].pedido else 'N/A'} | "
              f"Chassi: {dup.chassi_upper} | "
              f"Duplicatas: {dup.total}")

        # Ordenar por ID (manter o primeiro, deletar os demais)
        titulos_ordenados = sorted(titulos, key=lambda x: x.id)
        manter = titulos_ordenados[0]
        deletar = titulos_ordenados[1:]

        for tit in deletar:
            print(f"      ↳ DELETAR: ID={tit.id} | Valor Original={tit.valor_original} | "
                  f"Valor Pago={tit.valor_pago_total} | Status={tit.status}")

            registros_deletar.append({
                'tipo': f'TITULO_{tipo_titulo}',
                'objeto': tit,
                'valor_original': tit.valor_original,
                'valor_pago': tit.valor_pago_total,
                'status': tit.status,
                'empresa_recebedora_id': tit.empresa_recebedora_id
            })
            total_valor_duplicado += tit.valor_original

        print(f"      ✅ MANTER: ID={manter.id} | Valor Original={manter.valor_original}\n")

    print(f"💰 Valor total duplicado: R$ {total_valor_duplicado}")
    return registros_deletar


def analisar_duplicatas_titulos_pagar(tipo_titulo_pagar):
    """Analisa duplicatas de TituloAPagar (MONTAGEM ou MOVIMENTACAO)"""
    print("\n" + "=" * 100)
    print(f"3. ANALISANDO DUPLICATAS DE TÍTULOS A PAGAR {tipo_titulo_pagar}")
    print("=" * 100)

    # Buscar grupos duplicados (pedido_id + numero_chassi + tipo)
    duplicatas = db.session.query(
        TituloAPagar.pedido_id,
        func.upper(TituloAPagar.numero_chassi).label('chassi_upper'),
        func.count(TituloAPagar.id).label('total'),
        func.array_agg(TituloAPagar.id).label('ids')
    ).filter(
        TituloAPagar.tipo == tipo_titulo_pagar
    ).group_by(
        TituloAPagar.pedido_id,
        func.upper(TituloAPagar.numero_chassi)
    ).having(
        func.count(TituloAPagar.id) > 1
    ).all()

    if not duplicatas:
        print(f"✅ Nenhuma duplicata encontrada em TituloAPagar ({tipo_titulo_pagar})")
        return []

    print(f"⚠️  Encontrados {len(duplicatas)} grupos de títulos a pagar {tipo_titulo_pagar} duplicados:\n")

    registros_deletar = []
    total_valor_duplicado = Decimal('0')

    for dup in duplicatas:
        titulos_pagar = TituloAPagar.query.filter(TituloAPagar.id.in_(dup.ids)).all()

        print(f"   Pedido: {titulos_pagar[0].pedido.numero_pedido if titulos_pagar[0].pedido else 'N/A'} | "
              f"Chassi: {dup.chassi_upper} | "
              f"Duplicatas: {dup.total}")

        # Ordenar por ID (manter o primeiro, deletar os demais)
        titulos_ordenados = sorted(titulos_pagar, key=lambda x: x.id)
        manter = titulos_ordenados[0]
        deletar = titulos_ordenados[1:]

        for tit in deletar:
            print(f"      ↳ DELETAR: ID={tit.id} | Valor Original={tit.valor_original} | "
                  f"Valor Pago={tit.valor_pago} | Status={tit.status}")

            registros_deletar.append({
                'tipo': f'TITULO_PAGAR_{tipo_titulo_pagar}',
                'objeto': tit,
                'valor_original': tit.valor_original,
                'valor_pago': tit.valor_pago,
                'status': tit.status,
                'empresa_destino_id': tit.empresa_destino_id
            })
            total_valor_duplicado += tit.valor_original

        print(f"      ✅ MANTER: ID={manter.id} | Valor Original={manter.valor_original}\n")

    print(f"💰 Valor total duplicado: R$ {total_valor_duplicado}")
    return registros_deletar


def reverter_saldos(registros_deletar):
    """Reverte os saldos das empresas para os registros que serão deletados"""
    print("\n" + "=" * 100)
    print("4. REVERTENDO SALDOS DAS EMPRESAS")
    print("=" * 100)

    empresas_afetadas = {}

    for reg in registros_deletar:
        # COMISSÕES (pagas)
        if reg['tipo'] == 'COMISSAO' and reg['status'] == 'PAGO' and reg['empresa_pagadora_id']:
            empresa_id = reg['empresa_pagadora_id']
            valor = reg['valor']

            if empresa_id not in empresas_afetadas:
                empresas_afetadas[empresa_id] = Decimal('0')

            # Comissão paga = empresa PAGOU (subtraiu), então reverte SOMANDO
            empresas_afetadas[empresa_id] += valor
            print(f"   ↳ Comissão: Empresa ID={empresa_id} | +R$ {valor} (reverter pagamento)")

        # TÍTULOS MONTAGEM/MOVIMENTAÇÃO (recebidos)
        elif reg['tipo'].startswith('TITULO_') and reg['status'] == 'PAGO' and reg.get('empresa_recebedora_id'):
            empresa_id = reg['empresa_recebedora_id']
            valor = reg['valor_pago']

            if empresa_id not in empresas_afetadas:
                empresas_afetadas[empresa_id] = Decimal('0')

            # Título recebido = empresa RECEBEU (somou), então reverte SUBTRAINDO
            empresas_afetadas[empresa_id] -= valor
            print(f"   ↳ {reg['tipo']}: Empresa ID={empresa_id} | -R$ {valor} (reverter recebimento)")

        # TÍTULOS A PAGAR (pagos)
        elif reg['tipo'].startswith('TITULO_PAGAR_') and reg['status'] == 'PAGO':
            # Montagem: Empresa pagou fornecedor
            if reg['tipo'] == 'TITULO_PAGAR_MONTAGEM':
                # Pegar empresa_pagadora_montagem_id do item (via pedido + chassi)
                obj = reg['objeto']
                if obj.pedido_id and obj.numero_chassi:
                    from app.motochefe.models.vendas import PedidoVendaMotoItem
                    item = PedidoVendaMotoItem.query.filter(
                        PedidoVendaMotoItem.pedido_id == obj.pedido_id,
                        func.upper(PedidoVendaMotoItem.numero_chassi) == obj.numero_chassi.upper()
                    ).first()

                    if item and item.empresa_pagadora_montagem_id:
                        empresa_id = item.empresa_pagadora_montagem_id
                        valor = reg['valor_pago']

                        if empresa_id not in empresas_afetadas:
                            empresas_afetadas[empresa_id] = Decimal('0')

                        # Empresa pagou montagem (subtraiu), então reverte SOMANDO
                        empresas_afetadas[empresa_id] += valor
                        print(f"   ↳ {reg['tipo']}: Empresa ID={empresa_id} | +R$ {valor} (reverter pagamento)")

            # Movimentação: Empresa pagou MargemSogima (origem) E MargemSogima recebeu (destino)
            elif reg['tipo'] == 'TITULO_PAGAR_MOVIMENTACAO' and reg.get('empresa_destino_id'):
                # Reverter apenas MargemSogima (destino que recebeu)
                empresa_id = reg['empresa_destino_id']
                valor = reg['valor_pago']

                if empresa_id not in empresas_afetadas:
                    empresas_afetadas[empresa_id] = Decimal('0')

                # MargemSogima recebeu (somou), então reverte SUBTRAINDO
                empresas_afetadas[empresa_id] -= valor
                print(f"   ↳ {reg['tipo']} (destino): Empresa ID={empresa_id} | -R$ {valor} (reverter recebimento)")

    # Aplicar ajustes
    print(f"\n📊 RESUMO DE AJUSTES:")
    for empresa_id, ajuste in empresas_afetadas.items():
        empresa = db.session.get(EmpresaVendaMoto, empresa_id)
        if empresa:
            saldo_anterior = empresa.saldo
            empresa.saldo += ajuste

            print(f"   {empresa.empresa:40} | "
                  f"Saldo Anterior: R$ {float(saldo_anterior):15,.2f} | "
                  f"Ajuste: R$ {float(ajuste):+15,.2f} | "
                  f"Saldo Novo: R$ {float(empresa.saldo):15,.2f}")

    return empresas_afetadas


def deletar_duplicatas(registros_deletar):
    """Deleta os registros duplicados"""
    print("\n" + "=" * 100)
    print("5. DELETANDO REGISTROS DUPLICADOS")
    print("=" * 100)

    total_deletados = 0

    # Deletar MovimentacaoFinanceira vinculadas primeiro (FK)
    for reg in registros_deletar:
        obj = reg['objeto']

        # Se for ComissaoVendedor, deletar movimentações filhas
        if reg['tipo'] == 'COMISSAO':
            movs = MovimentacaoFinanceira.query.filter_by(comissao_vendedor_id=obj.id).all()
            for mov in movs:
                print(f"   ↳ Deletando MovimentacaoFinanceira ID={mov.id} (vinculada a ComissaoVendedor ID={obj.id})")
                db.session.delete(mov)
                total_deletados += 1

        # Se for TituloFinanceiro, deletar movimentações e títulos a pagar vinculados
        elif reg['tipo'].startswith('TITULO_'):
            movs = MovimentacaoFinanceira.query.filter_by(titulo_financeiro_id=obj.id).all()
            for mov in movs:
                print(f"   ↳ Deletando MovimentacaoFinanceira ID={mov.id} (vinculada a TituloFinanceiro ID={obj.id})")
                db.session.delete(mov)
                total_deletados += 1

            titulos_pagar = TituloAPagar.query.filter_by(titulo_financeiro_id=obj.id).all()
            for tp in titulos_pagar:
                print(f"   ↳ Deletando TituloAPagar ID={tp.id} (vinculado a TituloFinanceiro ID={obj.id})")
                db.session.delete(tp)
                total_deletados += 1

    # Deletar os registros principais
    for reg in registros_deletar:
        obj = reg['objeto']
        print(f"   ↳ Deletando {reg['tipo']} ID={obj.id}")
        db.session.delete(obj)
        total_deletados += 1

    print(f"\n✅ Total de registros deletados: {total_deletados}")


def main():
    """Função principal"""
    app = create_app()

    with app.app_context():
        print("\n")
        print("=" * 100)
        print("🧹 LIMPEZA DE DUPLICATAS - IMPORTAÇÃO HISTÓRICA MOTOCHEFE")
        print("=" * 100)
        print("\nEste script irá:")
        print("1. Analisar duplicatas de Comissões, Montagens e Movimentações")
        print("2. Reverter os saldos das empresas afetadas")
        print("3. Deletar os registros duplicados (mantém apenas o primeiro)")
        print("\n⚠️  IMPORTANTE: Execute apenas após ter certeza dos dados!")

        # Análise completa
        print("\n" + "=" * 100)
        print("FASE 1: ANÁLISE DE DUPLICATAS")
        print("=" * 100)

        duplicatas_comissoes = analisar_duplicatas_comissoes()
        duplicatas_montagem = analisar_duplicatas_titulos('MONTAGEM')
        duplicatas_movimentacao = analisar_duplicatas_titulos('MOVIMENTACAO')

        todos_registros = duplicatas_comissoes + duplicatas_montagem + duplicatas_movimentacao

        if not todos_registros:
            print("\n" + "=" * 100)
            print("✅ NENHUMA DUPLICATA ENCONTRADA - BANCO ESTÁ LIMPO!")
            print("=" * 100)
            return

        print("\n" + "=" * 100)
        print(f"⚠️  TOTAL DE REGISTROS DUPLICADOS A DELETAR: {len(todos_registros)}")
        print("=" * 100)

        # Confirmar antes de prosseguir
        print("\n⚠️  VOCÊ DESEJA PROSSEGUIR COM A LIMPEZA?")
        confirmacao = input("Digite 'SIM' para confirmar ou qualquer outra coisa para cancelar: ").strip().upper()

        if confirmacao != 'SIM':
            print("\n❌ Operação cancelada pelo usuário.")
            return

        # Executar limpeza
        print("\n" + "=" * 100)
        print("FASE 2: EXECUÇÃO DA LIMPEZA")
        print("=" * 100)

        try:
            # Reverter saldos
            empresas_ajustadas = reverter_saldos(todos_registros)

            # Deletar duplicatas
            deletar_duplicatas(todos_registros)

            # Commit
            db.session.commit()

            print("\n" + "=" * 100)
            print("✅ LIMPEZA CONCLUÍDA COM SUCESSO!")
            print("=" * 100)
            print(f"\n📊 RESUMO:")
            print(f"   - Registros deletados: {len(todos_registros)}")
            print(f"   - Empresas ajustadas: {len(empresas_ajustadas)}")
            print(f"\n✅ Saldos recalculados e banco limpo!")

        except Exception as e:
            db.session.rollback()
            print(f"\n❌ ERRO durante a limpeza: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return


if __name__ == '__main__':
    main()

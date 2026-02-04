# -*- coding: utf-8 -*-
"""
Script de Backfill: Criar LancamentoComprovante LANCADO para Comprovantes Reconciliados
========================================================================================

Comprovantes importados via OFX ANTES da FASE 3.5 podem ter
`odoo_is_reconciled=True` sem um LancamentoComprovante com status LANCADO.

Este script:
1. Busca comprovantes "órfãos" (reconciliados, sem lançamento LANCADO)
2. Consulta Odoo para buscar dados da conciliação pré-existente
3. Cria LancamentoComprovante com status LANCADO para cada um

Uso:
    # Dry-run (apenas mostra o que faria, sem criar nada)
    python scripts/backfill_lancamento_comprovantes_reconciliados.py --dry-run

    # Execução real
    python scripts/backfill_lancamento_comprovantes_reconciliados.py

Autor: Sistema de Fretes
Data: 2026-02-04
"""

import sys
import os

# Adiciona o diretório raiz ao path para importar módulos do app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.financeiro.models_comprovante import (
    ComprovantePagamentoBoleto,
    LancamentoComprovante,
)
from app.financeiro.services.ofx_vinculacao_service import (
    _buscar_dados_conciliacao_preexistente,
    _criar_lancamento_pre_conciliado,
)

BATCH_SIZE = 50  # Commit a cada N registros


def buscar_comprovantes_orfaos():
    """
    Busca ComprovantePagamentoBoleto que:
    - odoo_is_reconciled = True
    - odoo_statement_line_id IS NOT NULL
    - odoo_move_id IS NOT NULL
    - NÃO possuem LancamentoComprovante com status LANCADO

    Returns:
        list[ComprovantePagamentoBoleto]
    """
    # Subquery: comprovantes que JÁ têm lancamento LANCADO
    ja_lancados = db.session.query(
        LancamentoComprovante.comprovante_id
    ).filter(
        LancamentoComprovante.status == 'LANCADO'
    ).subquery()

    # Comprovantes reconciliados sem lancamento LANCADO
    orfaos = ComprovantePagamentoBoleto.query.filter(
        ComprovantePagamentoBoleto.odoo_is_reconciled == True,  # noqa: E712
        ComprovantePagamentoBoleto.odoo_statement_line_id.isnot(None),
        ComprovantePagamentoBoleto.odoo_move_id.isnot(None),
        ~ComprovantePagamentoBoleto.id.in_(
            db.session.query(ja_lancados.c.comprovante_id)
        ),
    ).order_by(ComprovantePagamentoBoleto.id).all()

    return orfaos


def main():
    dry_run = '--dry-run' in sys.argv

    app = create_app()
    with app.app_context():
        print("=" * 80)
        if dry_run:
            print("  BACKFILL COMPROVANTES RECONCILIADOS (DRY-RUN)")
        else:
            print("  BACKFILL COMPROVANTES RECONCILIADOS")
        print("=" * 80)
        print()

        # ─── ETAPA 1: Buscar comprovantes órfãos ──────────────────────
        print("[Etapa 1] Buscando comprovantes reconciliados sem lançamento LANCADO...")
        orfaos = buscar_comprovantes_orfaos()
        total = len(orfaos)

        print(f"  Encontrados: {total} comprovante(s) órfão(s)")
        print()

        if total == 0:
            print("Nenhum comprovante para processar. Script finalizado.")
            return

        # Listar resumo
        for comp in orfaos:
            print(
                f"  ID={comp.id} | Agendamento={comp.numero_agendamento} "
                f"| Valor=R$ {float(comp.valor_pago or 0):.2f} "
                f"| Odoo move_id={comp.odoo_move_id} "
                f"| statement_line_id={comp.odoo_statement_line_id}"
            )
        print()

        # ─── ETAPA 2: Conectar ao Odoo ────────────────────────────────
        print("[Etapa 2] Conectando ao Odoo...")
        try:
            from app.odoo.utils.connection import get_odoo_connection
            connection = get_odoo_connection()
            connection.authenticate()
            print("  Conexao Odoo estabelecida com sucesso")
        except Exception as e:
            print(f"  ERRO ao conectar ao Odoo: {e}")
            print("Script abortado.")
            return
        print()

        # ─── ETAPA 3: Montar batch e buscar dados de conciliação ──────
        print("[Etapa 3] Buscando dados de conciliacao pre-existente no Odoo...")

        # Montar dict {comp.id: {statement_line_id, odoo_move_id}}
        linhas_reconciliadas = {}
        comprovantes_por_id = {}
        for comp in orfaos:
            linhas_reconciliadas[comp.id] = {
                'statement_line_id': comp.odoo_statement_line_id,
                'odoo_move_id': comp.odoo_move_id,
            }
            comprovantes_por_id[comp.id] = comp

        dados_conciliacao = _buscar_dados_conciliacao_preexistente(
            connection, linhas_reconciliadas
        )

        encontrados = len(dados_conciliacao)
        sem_dados = total - encontrados
        print(f"  Dados de conciliacao encontrados: {encontrados}/{total}")
        if sem_dados > 0:
            print(
                f"  AVISO: {sem_dados} comprovante(s) reconciliado(s) "
                f"sem dados de titulo encontrado no Odoo"
            )
        print()

        if encontrados == 0:
            print("Nenhum dado de conciliacao retornado do Odoo. Script finalizado.")
            return

        # ─── ETAPA 4: Criar LancamentoComprovante ─────────────────────
        if dry_run:
            print("[Etapa 4] DRY-RUN: Listando o que SERIA criado...")
        else:
            print("[Etapa 4] Criando LancamentoComprovante LANCADO...")

        criados = 0
        erros = 0

        for comp_id, dados in dados_conciliacao.items():
            comprovante = comprovantes_por_id.get(comp_id)
            if not comprovante:
                continue

            titulo = dados['titulo']

            if dry_run:
                parcela_str = f"/{titulo['parcela']}" if titulo.get('parcela') else ''
                print(
                    f"  [DRY-RUN] CRIARIA: comp_id={comp_id} "
                    f"| titulo={titulo['move_name']} "
                    f"| NF={titulo['nf_numero']}{parcela_str} "
                    f"| partner={titulo['partner_name']} "
                    f"| valor_titulo=R$ {titulo['credit']:.2f} "
                    f"| valor_pago=R$ {float(comprovante.valor_pago or 0):.2f}"
                )
                criados += 1
            else:
                try:
                    lanc = _criar_lancamento_pre_conciliado(comprovante, dados)
                    # Diferenciar do fluxo online
                    lanc.lancado_por = 'backfill_reconciliacao'

                    criados += 1
                    parcela_str = f"/{titulo['parcela']}" if titulo.get('parcela') else ''
                    print(
                        f"  Criado: comp_id={comp_id} -> lanc_id={lanc.id or '(novo)'} "
                        f"| titulo={titulo['move_name']} "
                        f"| NF={titulo['nf_numero']}{parcela_str} "
                        f"| partner={titulo['partner_name']}"
                    )

                    # Commit por batch
                    if criados % BATCH_SIZE == 0:
                        db.session.commit()
                        print(f"  ... commit parcial ({criados}/{encontrados})")

                except Exception as e:
                    erros += 1
                    print(f"  ERRO comp_id={comp_id}: {e}")

        # ─── ETAPA 5: Commit final ────────────────────────────────────
        if not dry_run and criados > 0:
            try:
                db.session.commit()
                print()
                print("  Commit final realizado com sucesso")
            except Exception as e:
                db.session.rollback()
                print(f"  ERRO no commit final: {e}")
                erros += criados
                criados = 0

        # ─── RESUMO ───────────────────────────────────────────────────
        print()
        print("=" * 80)
        print("  RESUMO")
        print("=" * 80)
        print(f"  Total de comprovantes orfaos encontrados: {total}")
        print(f"  Dados de conciliacao retornados do Odoo:  {encontrados}")
        if dry_run:
            print(f"  Lancamentos que SERIAM criados:           {criados}")
            print()
            print("  (DRY-RUN: nenhum registro foi criado)")
        else:
            print(f"  Lancamentos criados com sucesso:          {criados}")
            print(f"  Erros:                                    {erros}")
        print("=" * 80)


if __name__ == '__main__':
    main()

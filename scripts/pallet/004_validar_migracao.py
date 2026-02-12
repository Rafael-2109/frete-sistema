#!/usr/bin/env python
"""
Script de validação de migração: Verifica integridade dos dados migrados

Este script valida a integridade dos dados migrados pelos scripts 001, 002 e 003,
garantindo que:
- Todas as tabelas existem e têm dados
- Integridade referencial está OK (todas FKs resolvem)
- Quantidades são consistentes (saldo <= original)
- Status está consistente com saldo
- Totais fonte vs destino batem
- Não há registros órfãos

Dependências (ordem de execução):
    1. scripts/pallet/001_criar_tabelas_pallet_v2.py (cria tabelas)
    2. scripts/pallet/002_migrar_movimentacao_para_nf_remessa.py (migra MovimentacaoEstoque)
    3. scripts/pallet/003_migrar_vale_pallet_para_documento.py (migra ValePallet)
    4. scripts/pallet/004_validar_migracao.py (ESTE SCRIPT)

Spec: .claude/ralph-loop/specs/prd-reestruturacao-modulo-pallets.md
IMPLEMENTATION_PLAN.md: Fase 1.3.3

Uso:
    cd /home/rafaelnascimento/projetos/frete_sistema
    source .venv/bin/activate
    python scripts/pallet/004_validar_migracao.py

    # Verbose (mostra detalhes de cada problema):
    python scripts/pallet/004_validar_migracao.py --verbose

    # Salvar relatório em arquivo:
    python scripts/pallet/004_validar_migracao.py --output relatorio.txt
"""
import sys
import os
import argparse
from datetime import datetime

# Adicionar o diretório raiz ao path para imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text
from app.utils.timezone import agora_utc_naive


# ============================================================================
# CONSTANTES
# ============================================================================

TABELAS_V2 = [
    'pallet_nf_remessa',
    'pallet_creditos',
    'pallet_documentos',
    'pallet_solucoes',
    'pallet_nf_solucoes',
]

TABELAS_LEGADO = [
    'movimentacao_estoque',
    'vale_pallets',
]


# ============================================================================
# VERIFICAÇÕES DE ESTRUTURA
# ============================================================================

def verificar_tabelas_existem():
    """
    Verificação 1: Todas as tabelas v2 existem

    Retorna: (ok, mensagens)
    """
    print("\n" + "=" * 70)
    print("📋 VERIFICAÇÃO 1: Tabelas Existem")
    print("=" * 70)

    problemas = []
    ok = []

    for tabela in TABELAS_V2:
        result = db.session.execute(text(f"""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = '{tabela}'
            )
        """)).scalar()

        if result:
            # Contar registros
            count = db.session.execute(text(f"SELECT COUNT(*) FROM {tabela}")).scalar() or 0
            ok.append(f"✅ {tabela}: {count:,} registros")
        else:
            problemas.append(f"❌ {tabela}: NÃO EXISTE")

    for msg in ok:
        print(f"  {msg}")
    for msg in problemas:
        print(f"  {msg}")

    if problemas:
        print("\n⚠️  Execute primeiro: python scripts/pallet/001_criar_tabelas_pallet_v2.py")
        return False, problemas

    print("\n✅ Todas as tabelas v2 existem")
    return True, []


def verificar_tabelas_legado_existem():
    """
    Verificação 2: Tabelas legado existem (para comparação)

    Retorna: (ok, mensagens)
    """
    print("\n" + "=" * 70)
    print("📋 VERIFICAÇÃO 2: Tabelas Legado (Fonte)")
    print("=" * 70)

    problemas = []
    ok = []

    for tabela in TABELAS_LEGADO:
        result = db.session.execute(text(f"""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = '{tabela}'
            )
        """)).scalar()

        if result:
            count = db.session.execute(text(f"SELECT COUNT(*) FROM {tabela}")).scalar() or 0
            ok.append(f"✅ {tabela}: {count:,} registros")
        else:
            problemas.append(f"⚠️ {tabela}: NÃO EXISTE (pode não haver dados legado)")

    for msg in ok:
        print(f"  {msg}")
    for msg in problemas:
        print(f"  {msg}")

    # Não é erro crítico se tabelas legado não existirem
    return True, problemas


# ============================================================================
# VERIFICAÇÕES DE INTEGRIDADE REFERENCIAL
# ============================================================================

def verificar_fk_creditos_nf_remessa(verbose=False):
    """
    Verificação 3: Todos os créditos têm NF remessa válida

    FK: pallet_creditos.nf_remessa_id → pallet_nf_remessa.id
    """
    print("\n" + "=" * 70)
    print("📋 VERIFICAÇÃO 3: FK Créditos → NF Remessa")
    print("=" * 70)

    # Buscar créditos órfãos (sem NF remessa)
    result = db.session.execute(text("""
        SELECT c.id, c.nf_remessa_id, c.cnpj_responsavel, c.qtd_original
        FROM pallet_creditos c
        LEFT JOIN pallet_nf_remessa nfr ON c.nf_remessa_id = nfr.id
        WHERE nfr.id IS NULL
        LIMIT 100
    """)).fetchall()

    if result:
        print(f"  ❌ {len(result)} créditos SEM NF remessa válida:")
        if verbose:
            for row in result[:10]:
                print(f"     - Crédito #{row[0]}: nf_remessa_id={row[1]}, CNPJ={row[2]}, qtd={row[3]}")
            if len(result) > 10:
                print(f"     ... e mais {len(result) - 10} registros")
        return False, [f"{len(result)} créditos sem NF remessa"]

    # Contar total válido
    total = db.session.execute(text("""
        SELECT COUNT(*) FROM pallet_creditos c
        INNER JOIN pallet_nf_remessa nfr ON c.nf_remessa_id = nfr.id
    """)).scalar() or 0

    print(f"  ✅ {total:,} créditos com FK válida")
    return True, []


def verificar_fk_documentos_credito(verbose=False):
    """
    Verificação 4: Todos os documentos têm crédito válido

    FK: pallet_documentos.credito_id → pallet_creditos.id
    """
    print("\n" + "=" * 70)
    print("📋 VERIFICAÇÃO 4: FK Documentos → Créditos")
    print("=" * 70)

    # Buscar documentos órfãos
    result = db.session.execute(text("""
        SELECT d.id, d.credito_id, d.tipo, d.numero_documento
        FROM pallet_documentos d
        LEFT JOIN pallet_creditos c ON d.credito_id = c.id
        WHERE c.id IS NULL
        LIMIT 100
    """)).fetchall()

    if result:
        print(f"  ❌ {len(result)} documentos SEM crédito válido:")
        if verbose:
            for row in result[:10]:
                print(f"     - Documento #{row[0]}: credito_id={row[1]}, tipo={row[2]}, num={row[3]}")
            if len(result) > 10:
                print(f"     ... e mais {len(result) - 10} registros")
        return False, [f"{len(result)} documentos sem crédito"]

    total = db.session.execute(text("""
        SELECT COUNT(*) FROM pallet_documentos d
        INNER JOIN pallet_creditos c ON d.credito_id = c.id
    """)).scalar() or 0

    print(f"  ✅ {total:,} documentos com FK válida")
    return True, []


def verificar_fk_solucoes_credito(verbose=False):
    """
    Verificação 5: Todas as soluções têm crédito válido

    FK: pallet_solucoes.credito_id → pallet_creditos.id
    """
    print("\n" + "=" * 70)
    print("📋 VERIFICAÇÃO 5: FK Soluções → Créditos")
    print("=" * 70)

    # Buscar soluções órfãs
    result = db.session.execute(text("""
        SELECT s.id, s.credito_id, s.tipo, s.quantidade
        FROM pallet_solucoes s
        LEFT JOIN pallet_creditos c ON s.credito_id = c.id
        WHERE c.id IS NULL
        LIMIT 100
    """)).fetchall()

    if result:
        print(f"  ❌ {len(result)} soluções SEM crédito válido:")
        if verbose:
            for row in result[:10]:
                print(f"     - Solução #{row[0]}: credito_id={row[1]}, tipo={row[2]}, qtd={row[3]}")
            if len(result) > 10:
                print(f"     ... e mais {len(result) - 10} registros")
        return False, [f"{len(result)} soluções sem crédito"]

    total = db.session.execute(text("""
        SELECT COUNT(*) FROM pallet_solucoes s
        INNER JOIN pallet_creditos c ON s.credito_id = c.id
    """)).scalar() or 0

    print(f"  ✅ {total:,} soluções com FK válida")
    return True, []


def verificar_fk_nf_solucoes(verbose=False):
    """
    Verificação 6: Todas as soluções de NF têm NF remessa válida

    FK: pallet_nf_solucoes.nf_remessa_id → pallet_nf_remessa.id
    """
    print("\n" + "=" * 70)
    print("📋 VERIFICAÇÃO 6: FK Soluções NF → NF Remessa")
    print("=" * 70)

    # Buscar soluções NF órfãs
    result = db.session.execute(text("""
        SELECT ns.id, ns.nf_remessa_id, ns.tipo, ns.quantidade
        FROM pallet_nf_solucoes ns
        LEFT JOIN pallet_nf_remessa nfr ON ns.nf_remessa_id = nfr.id
        WHERE nfr.id IS NULL
        LIMIT 100
    """)).fetchall()

    if result:
        print(f"  ❌ {len(result)} soluções NF SEM NF remessa válida:")
        if verbose:
            for row in result[:10]:
                print(f"     - Solução NF #{row[0]}: nf_remessa_id={row[1]}, tipo={row[2]}, qtd={row[3]}")
            if len(result) > 10:
                print(f"     ... e mais {len(result) - 10} registros")
        return False, [f"{len(result)} soluções NF sem NF remessa"]

    total = db.session.execute(text("""
        SELECT COUNT(*) FROM pallet_nf_solucoes ns
        INNER JOIN pallet_nf_remessa nfr ON ns.nf_remessa_id = nfr.id
    """)).scalar() or 0

    print(f"  ✅ {total:,} soluções NF com FK válida")
    return True, []


# ============================================================================
# VERIFICAÇÕES DE CONSISTÊNCIA DE DADOS
# ============================================================================

def verificar_saldo_credito(verbose=False):
    """
    Verificação 7: Saldo do crédito não excede original

    Regra: qtd_saldo <= qtd_original
    """
    print("\n" + "=" * 70)
    print("📋 VERIFICAÇÃO 7: Saldo <= Original (Créditos)")
    print("=" * 70)

    # Buscar créditos com saldo maior que original
    result = db.session.execute(text("""
        SELECT id, cnpj_responsavel, qtd_original, qtd_saldo, status
        FROM pallet_creditos
        WHERE qtd_saldo > qtd_original
        LIMIT 100
    """)).fetchall()

    if result:
        print(f"  ❌ {len(result)} créditos com saldo > original:")
        if verbose:
            for row in result[:10]:
                print(f"     - Crédito #{row[0]}: CNPJ={row[1]}, original={row[2]}, saldo={row[3]}, status={row[4]}")
            if len(result) > 10:
                print(f"     ... e mais {len(result) - 10} registros")
        return False, [f"{len(result)} créditos com saldo inválido"]

    # Contar total
    total = db.session.execute(text("SELECT COUNT(*) FROM pallet_creditos")).scalar() or 0
    print(f"  ✅ {total:,} créditos com saldo válido (saldo <= original)")
    return True, []


def verificar_status_vs_saldo(verbose=False):
    """
    Verificação 8: Status consistente com saldo

    Regras:
    - RESOLVIDO: qtd_saldo = 0
    - PARCIAL: 0 < qtd_saldo < qtd_original
    - PENDENTE: qtd_saldo = qtd_original
    """
    print("\n" + "=" * 70)
    print("📋 VERIFICAÇÃO 8: Status vs Saldo (Créditos)")
    print("=" * 70)

    problemas = []

    # RESOLVIDO com saldo > 0
    resolvido_com_saldo = db.session.execute(text("""
        SELECT id, cnpj_responsavel, qtd_original, qtd_saldo
        FROM pallet_creditos
        WHERE status = 'RESOLVIDO' AND qtd_saldo > 0
        LIMIT 50
    """)).fetchall()

    if resolvido_com_saldo:
        msg = f"{len(resolvido_com_saldo)} créditos RESOLVIDOS com saldo > 0"
        problemas.append(msg)
        print(f"  ⚠️  {msg}")
        if verbose:
            for row in resolvido_com_saldo[:5]:
                print(f"     - Crédito #{row[0]}: CNPJ={row[1]}, original={row[2]}, saldo={row[3]}")

    # PENDENTE com saldo < original
    pendente_com_baixo = db.session.execute(text("""
        SELECT id, cnpj_responsavel, qtd_original, qtd_saldo
        FROM pallet_creditos
        WHERE status = 'PENDENTE' AND qtd_saldo < qtd_original AND qtd_saldo > 0
        LIMIT 50
    """)).fetchall()

    if pendente_com_baixo:
        msg = f"{len(pendente_com_baixo)} créditos PENDENTES que deveriam ser PARCIAIS"
        problemas.append(msg)
        print(f"  ⚠️  {msg}")
        if verbose:
            for row in pendente_com_baixo[:5]:
                print(f"     - Crédito #{row[0]}: CNPJ={row[1]}, original={row[2]}, saldo={row[3]}")

    if not problemas:
        total = db.session.execute(text("SELECT COUNT(*) FROM pallet_creditos")).scalar() or 0
        print(f"  ✅ {total:,} créditos com status consistente")
        return True, []

    # Não é erro crítico, apenas aviso
    print(f"\n  ⚠️  {len(problemas)} inconsistências de status (pode ser corrigido automaticamente)")
    return True, problemas  # Retorna True pois não é bloqueante


def verificar_soma_solucoes_vs_original(verbose=False):
    """
    Verificação 9: Soma das soluções não excede o original

    Regra: SUM(pallet_solucoes.quantidade) <= pallet_creditos.qtd_original
    """
    print("\n" + "=" * 70)
    print("📋 VERIFICAÇÃO 9: Soma Soluções <= Original")
    print("=" * 70)

    # Buscar créditos onde soma das soluções excede original
    result = db.session.execute(text("""
        SELECT c.id, c.cnpj_responsavel, c.qtd_original, COALESCE(SUM(s.quantidade), 0) as total_solucoes
        FROM pallet_creditos c
        LEFT JOIN pallet_solucoes s ON s.credito_id = c.id
        GROUP BY c.id, c.cnpj_responsavel, c.qtd_original
        HAVING COALESCE(SUM(s.quantidade), 0) > c.qtd_original
        LIMIT 100
    """)).fetchall()

    if result:
        print(f"  ❌ {len(result)} créditos com soluções excedendo original:")
        if verbose:
            for row in result[:10]:
                print(f"     - Crédito #{row[0]}: CNPJ={row[1]}, original={row[2]}, soma_solucoes={row[3]}")
            if len(result) > 10:
                print(f"     ... e mais {len(result) - 10} registros")
        return False, [f"{len(result)} créditos com soluções excedentes"]

    total = db.session.execute(text("SELECT COUNT(*) FROM pallet_creditos")).scalar() or 0
    print(f"  ✅ {total:,} créditos com soma de soluções válida")
    return True, []


# ============================================================================
# VERIFICAÇÕES DE MIGRAÇÃO
# ============================================================================

def verificar_migracao_movimentacao(verbose=False):
    """
    Verificação 10: Migração de MovimentacaoEstoque

    Compara: movimentacao_estoque (PALLET+REMESSA) vs pallet_nf_remessa
    """
    print("\n" + "=" * 70)
    print("📋 VERIFICAÇÃO 10: Migração MovimentacaoEstoque → NF Remessa")
    print("=" * 70)

    # Verificar se tabela existe
    exists = db.session.execute(text("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = 'movimentacao_estoque'
        )
    """)).scalar()

    if not exists:
        print("  ℹ️  Tabela movimentacao_estoque não existe (ok se sistema novo)")
        return True, []

    # Contar fonte
    fonte = db.session.execute(text("""
        SELECT COUNT(*)
        FROM movimentacao_estoque
        WHERE local_movimentacao = 'PALLET'
          AND tipo_movimentacao = 'REMESSA'
          AND ativo = TRUE
    """)).scalar() or 0

    # Contar migrados (com movimentacao_estoque_id)
    migrados = db.session.execute(text("""
        SELECT COUNT(*)
        FROM pallet_nf_remessa
        WHERE movimentacao_estoque_id IS NOT NULL
    """)).scalar() or 0

    # Contar total destino
    destino = db.session.execute(text("SELECT COUNT(*) FROM pallet_nf_remessa")).scalar() or 0

    print(f"  📊 Fonte (MovimentacaoEstoque PALLET+REMESSA): {fonte:,}")
    print(f"  📊 Migrados (com movimentacao_estoque_id): {migrados:,}")
    print(f"  📊 Total NF Remessa: {destino:,}")

    if fonte > 0:
        pct = (migrados / fonte) * 100 if fonte > 0 else 0
        print(f"  📊 Percentual migrado: {pct:.1f}%")

        if migrados < fonte:
            faltando = fonte - migrados
            print(f"  ⚠️  {faltando:,} registros NÃO migrados")
            if verbose:
                # Listar alguns não migrados
                result = db.session.execute(text("""
                    SELECT id, numero_nf, cnpj_destinatario, qtd_movimentacao
                    FROM movimentacao_estoque
                    WHERE local_movimentacao = 'PALLET'
                      AND tipo_movimentacao = 'REMESSA'
                      AND ativo = TRUE
                      AND id NOT IN (
                          SELECT movimentacao_estoque_id FROM pallet_nf_remessa
                          WHERE movimentacao_estoque_id IS NOT NULL
                      )
                    LIMIT 10
                """)).fetchall()

                print("     Exemplos não migrados:")
                for row in result:
                    print(f"     - MovEst #{row[0]}: NF={row[1]}, CNPJ={row[2]}, qtd={row[3]}")
            return True, [f"{faltando} registros não migrados de MovimentacaoEstoque"]

    print(f"  ✅ Migração completa ({migrados:,}/{fonte:,})")
    return True, []


def verificar_migracao_vale_pallet(verbose=False):
    """
    Verificação 11: Migração de ValePallet

    Compara: vale_pallets vs pallet_documentos
    """
    print("\n" + "=" * 70)
    print("📋 VERIFICAÇÃO 11: Migração ValePallet → Documentos")
    print("=" * 70)

    # Verificar se tabela existe
    exists = db.session.execute(text("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = 'vale_pallets'
        )
    """)).scalar()

    if not exists:
        print("  ℹ️  Tabela vale_pallets não existe (ok se sistema novo)")
        return True, []

    # Contar fonte
    fonte = db.session.execute(text("""
        SELECT COUNT(*)
        FROM vale_pallets
        WHERE ativo = TRUE
    """)).scalar() or 0

    # Contar migrados (com vale_pallet_id)
    migrados = db.session.execute(text("""
        SELECT COUNT(*)
        FROM pallet_documentos
        WHERE vale_pallet_id IS NOT NULL
    """)).scalar() or 0

    # Contar sem crédito (SEM_CREDITO)
    sem_credito = db.session.execute(text("""
        SELECT COUNT(*)
        FROM vale_pallets vp
        WHERE vp.ativo = TRUE
          AND NOT EXISTS (
              SELECT 1 FROM pallet_nf_remessa nfr
              WHERE nfr.numero_nf = vp.nf_pallet
          )
    """)).scalar() or 0

    destino = db.session.execute(text("SELECT COUNT(*) FROM pallet_documentos")).scalar() or 0

    print(f"  📊 Fonte (ValePallet ativos): {fonte:,}")
    print(f"  📊 Migrados (com vale_pallet_id): {migrados:,}")
    print(f"  📊 Sem crédito correspondente: {sem_credito:,}")
    print(f"  📊 Total Documentos: {destino:,}")

    if fonte > 0:
        migrado_pct = (migrados / fonte) * 100
        print(f"  📊 Percentual migrado: {migrado_pct:.1f}%")

        faltando = fonte - migrados - sem_credito
        if faltando > 0:
            print(f"  ⚠️  {faltando:,} registros NÃO migrados (além dos sem crédito)")
            if verbose:
                result = db.session.execute(text("""
                    SELECT id, nf_pallet, cnpj_cliente, quantidade
                    FROM vale_pallets
                    WHERE ativo = TRUE
                      AND id NOT IN (
                          SELECT vale_pallet_id FROM pallet_documentos
                          WHERE vale_pallet_id IS NOT NULL
                      )
                    LIMIT 10
                """)).fetchall()

                print("     Exemplos não migrados:")
                for row in result:
                    print(f"     - Vale #{row[0]}: NF={row[1]}, CNPJ={row[2]}, qtd={row[3]}")
            return True, [f"{faltando} registros não migrados de ValePallet"]

    print(f"  ✅ Migração completa (migrados={migrados:,}, sem_credito={sem_credito:,})")
    return True, []


# ============================================================================
# VERIFICAÇÕES DE QUANTIDADES TOTAIS
# ============================================================================

def verificar_totais_quantidades(verbose=False):
    """
    Verificação 12: Totais de quantidades

    Compara totais para garantir consistência
    """
    print("\n" + "=" * 70)
    print("📋 VERIFICAÇÃO 12: Totais de Quantidades")
    print("=" * 70)

    # Total quantidade em NF Remessa
    total_nf = db.session.execute(text("""
        SELECT COALESCE(SUM(quantidade), 0) FROM pallet_nf_remessa WHERE ativo = TRUE
    """)).scalar() or 0

    # Total original em Créditos
    total_creditos_original = db.session.execute(text("""
        SELECT COALESCE(SUM(qtd_original), 0) FROM pallet_creditos WHERE ativo = TRUE
    """)).scalar() or 0

    # Total saldo em Créditos
    total_creditos_saldo = db.session.execute(text("""
        SELECT COALESCE(SUM(qtd_saldo), 0) FROM pallet_creditos WHERE ativo = TRUE
    """)).scalar() or 0

    # Total em Soluções
    total_solucoes = db.session.execute(text("""
        SELECT COALESCE(SUM(quantidade), 0) FROM pallet_solucoes WHERE ativo = TRUE
    """)).scalar() or 0

    print(f"  📊 Total NF Remessa (quantidade): {total_nf:,}")
    print(f"  📊 Total Créditos (original): {total_creditos_original:,}")
    print(f"  📊 Total Créditos (saldo): {total_creditos_saldo:,}")
    print(f"  📊 Total Soluções: {total_solucoes:,}")

    problemas = []

    # NF Remessa deve = Créditos Original
    if total_nf != total_creditos_original:
        diff = abs(total_nf - total_creditos_original)
        msg = f"NF Remessa ({total_nf:,}) ≠ Créditos Original ({total_creditos_original:,}), diff={diff:,}"
        problemas.append(msg)
        print(f"  ⚠️  {msg}")

    # Créditos Original - Soluções = Créditos Saldo
    esperado_saldo = total_creditos_original - total_solucoes
    if esperado_saldo != total_creditos_saldo:
        diff = abs(esperado_saldo - total_creditos_saldo)
        msg = f"Saldo esperado ({esperado_saldo:,}) ≠ Saldo atual ({total_creditos_saldo:,}), diff={diff:,}"
        problemas.append(msg)
        print(f"  ⚠️  {msg}")

    if not problemas:
        print(f"  ✅ Totais consistentes")
        return True, []

    return True, problemas  # Retorna True pois pode haver soluções parciais


# ============================================================================
# VERIFICAÇÕES EXTRAS
# ============================================================================

def verificar_nf_remessa_duplicadas(verbose=False):
    """
    Verificação 13: NFs de remessa duplicadas

    Cada numero_nf deve ser único (por série se aplicável)
    """
    print("\n" + "=" * 70)
    print("📋 VERIFICAÇÃO 13: NFs Remessa Duplicadas")
    print("=" * 70)

    result = db.session.execute(text("""
        SELECT numero_nf, serie, COUNT(*) as qtd
        FROM pallet_nf_remessa
        WHERE ativo = TRUE
        GROUP BY numero_nf, serie
        HAVING COUNT(*) > 1
        LIMIT 50
    """)).fetchall()

    if result:
        print(f"  ❌ {len(result)} NFs duplicadas:")
        if verbose:
            for row in result[:10]:
                print(f"     - NF {row[0]} (série {row[1]}): {row[2]} registros")
            if len(result) > 10:
                print(f"     ... e mais {len(result) - 10}")
        return False, [f"{len(result)} NFs duplicadas"]

    total = db.session.execute(text("""
        SELECT COUNT(DISTINCT numero_nf) FROM pallet_nf_remessa WHERE ativo = TRUE
    """)).scalar() or 0
    print(f"  ✅ {total:,} NFs únicas (sem duplicatas)")
    return True, []


def verificar_cnpj_validos(verbose=False):
    """
    Verificação 14: CNPJs em formato válido (14 dígitos ou NULL)
    """
    print("\n" + "=" * 70)
    print("📋 VERIFICAÇÃO 14: Formato de CNPJs")
    print("=" * 70)

    # CNPJs inválidos em NF Remessa
    invalidos_nf = db.session.execute(text("""
        SELECT id, numero_nf, cnpj_destinatario
        FROM pallet_nf_remessa
        WHERE cnpj_destinatario IS NOT NULL
          AND LENGTH(REGEXP_REPLACE(cnpj_destinatario, '[^0-9]', '', 'g')) NOT IN (11, 14)
          AND cnpj_destinatario != ''
        LIMIT 50
    """)).fetchall()

    # CNPJs inválidos em Créditos
    invalidos_cred = db.session.execute(text("""
        SELECT id, cnpj_responsavel
        FROM pallet_creditos
        WHERE cnpj_responsavel IS NOT NULL
          AND LENGTH(REGEXP_REPLACE(cnpj_responsavel, '[^0-9]', '', 'g')) NOT IN (11, 14)
          AND cnpj_responsavel != ''
        LIMIT 50
    """)).fetchall()

    problemas = []

    if invalidos_nf:
        msg = f"{len(invalidos_nf)} CNPJs inválidos em NF Remessa"
        problemas.append(msg)
        print(f"  ⚠️  {msg}")
        if verbose:
            for row in invalidos_nf[:5]:
                print(f"     - NF #{row[0]} ({row[1]}): CNPJ='{row[2]}'")

    if invalidos_cred:
        msg = f"{len(invalidos_cred)} CNPJs inválidos em Créditos"
        problemas.append(msg)
        print(f"  ⚠️  {msg}")
        if verbose:
            for row in invalidos_cred[:5]:
                print(f"     - Crédito #{row[0]}: CNPJ='{row[1]}'")

    if not problemas:
        print("  ✅ Todos os CNPJs em formato válido")
        return True, []

    return True, problemas  # Aviso, não erro crítico


# ============================================================================
# RESUMO E RELATÓRIO
# ============================================================================

def gerar_resumo(resultados):
    """Gera resumo final da validação"""
    print("\n" + "=" * 70)
    print("📊 RESUMO DA VALIDAÇÃO")
    print("=" * 70)

    total_checks = len(resultados)
    erros = [r for r in resultados if not r['ok']]
    avisos = [r for r in resultados if r['ok'] and r['problemas']]
    ok = [r for r in resultados if r['ok'] and not r['problemas']]

    print(f"\n  Total de verificações: {total_checks}")
    print(f"  ✅ OK: {len(ok)}")
    print(f"  ⚠️  Avisos: {len(avisos)}")
    print(f"  ❌ Erros: {len(erros)}")

    if erros:
        print("\n  ❌ ERROS CRÍTICOS:")
        for r in erros:
            print(f"     - {r['nome']}")
            for p in r['problemas']:
                print(f"       → {p}")

    if avisos:
        print("\n  ⚠️  AVISOS:")
        for r in avisos:
            print(f"     - {r['nome']}")
            for p in r['problemas']:
                print(f"       → {p}")

    # Status final
    print("\n" + "=" * 70)
    if erros:
        print("❌ VALIDAÇÃO FALHOU - Corrija os erros antes de prosseguir")
        return False
    elif avisos:
        print("⚠️  VALIDAÇÃO OK COM AVISOS - Revise os avisos")
        return True
    else:
        print("✅ VALIDAÇÃO COMPLETA - Todos os dados estão íntegros")
        return True


def salvar_relatorio(resultados, output_file):
    """Salva relatório em arquivo"""
    with open(output_file, 'w') as f:
        f.write("=" * 70 + "\n")
        f.write("RELATÓRIO DE VALIDAÇÃO DE MIGRAÇÃO - PALLET V2\n")
        f.write(f"Data: {agora_utc_naive().strftime('%d/%m/%Y %H:%M:%S')}\n")
        f.write("=" * 70 + "\n\n")

        for r in resultados:
            status = "✅" if r['ok'] and not r['problemas'] else ("⚠️" if r['ok'] else "❌")
            f.write(f"{status} {r['nome']}\n")
            for p in r['problemas']:
                f.write(f"   → {p}\n")
            f.write("\n")

        # Resumo
        erros = [r for r in resultados if not r['ok']]
        avisos = [r for r in resultados if r['ok'] and r['problemas']]

        f.write("=" * 70 + "\n")
        f.write("RESUMO\n")
        f.write(f"Total: {len(resultados)} verificações\n")
        f.write(f"Erros: {len(erros)}\n")
        f.write(f"Avisos: {len(avisos)}\n")
        f.write("=" * 70 + "\n")

    print(f"\n📄 Relatório salvo em: {output_file}")


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Valida integridade dos dados migrados para o módulo de pallet v2'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Mostra detalhes de cada problema encontrado'
    )
    parser.add_argument(
        '--output', '-o',
        type=str,
        help='Salva relatório em arquivo'
    )
    args = parser.parse_args()

    print("\n" + "=" * 70)
    print("🔍 VALIDAÇÃO DE MIGRAÇÃO - PALLET V2")
    print("=" * 70)
    print(f"Data: {agora_utc_naive().strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"Verbose: {'Sim' if args.verbose else 'Não'}")

    app = create_app()

    with app.app_context():
        resultados = []

        # 1. Estrutura
        ok, probs = verificar_tabelas_existem()
        resultados.append({'nome': 'Tabelas V2 existem', 'ok': ok, 'problemas': probs})

        if not ok:
            print("\n❌ ABORTANDO: Tabelas v2 não existem. Execute script 001 primeiro.")
            return 1

        ok, probs = verificar_tabelas_legado_existem()
        resultados.append({'nome': 'Tabelas legado existem', 'ok': ok, 'problemas': probs})

        # 2. Integridade referencial
        ok, probs = verificar_fk_creditos_nf_remessa(args.verbose)
        resultados.append({'nome': 'FK Créditos → NF Remessa', 'ok': ok, 'problemas': probs})

        ok, probs = verificar_fk_documentos_credito(args.verbose)
        resultados.append({'nome': 'FK Documentos → Créditos', 'ok': ok, 'problemas': probs})

        ok, probs = verificar_fk_solucoes_credito(args.verbose)
        resultados.append({'nome': 'FK Soluções → Créditos', 'ok': ok, 'problemas': probs})

        ok, probs = verificar_fk_nf_solucoes(args.verbose)
        resultados.append({'nome': 'FK Soluções NF → NF Remessa', 'ok': ok, 'problemas': probs})

        # 3. Consistência de dados
        ok, probs = verificar_saldo_credito(args.verbose)
        resultados.append({'nome': 'Saldo <= Original', 'ok': ok, 'problemas': probs})

        ok, probs = verificar_status_vs_saldo(args.verbose)
        resultados.append({'nome': 'Status vs Saldo', 'ok': ok, 'problemas': probs})

        ok, probs = verificar_soma_solucoes_vs_original(args.verbose)
        resultados.append({'nome': 'Soma Soluções <= Original', 'ok': ok, 'problemas': probs})

        # 4. Migração
        ok, probs = verificar_migracao_movimentacao(args.verbose)
        resultados.append({'nome': 'Migração MovimentacaoEstoque', 'ok': ok, 'problemas': probs})

        ok, probs = verificar_migracao_vale_pallet(args.verbose)
        resultados.append({'nome': 'Migração ValePallet', 'ok': ok, 'problemas': probs})

        # 5. Quantidades totais
        ok, probs = verificar_totais_quantidades(args.verbose)
        resultados.append({'nome': 'Totais de Quantidades', 'ok': ok, 'problemas': probs})

        # 6. Extras
        ok, probs = verificar_nf_remessa_duplicadas(args.verbose)
        resultados.append({'nome': 'NFs Duplicadas', 'ok': ok, 'problemas': probs})

        ok, probs = verificar_cnpj_validos(args.verbose)
        resultados.append({'nome': 'Formato CNPJs', 'ok': ok, 'problemas': probs})

        # Resumo
        sucesso = gerar_resumo(resultados)

        # Salvar relatório se solicitado
        if args.output:
            salvar_relatorio(resultados, args.output)

        return 0 if sucesso else 1


if __name__ == '__main__':
    sys.exit(main())

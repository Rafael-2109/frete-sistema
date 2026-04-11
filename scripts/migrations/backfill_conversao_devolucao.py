"""
Backfill: Recalcular quantidade_convertida e fator_conversao (De-Para) nas devoluções.

Dois modos de operação:
  --modo qtd       Recalcula quantidade_convertida nas linhas de NFD (corrige arredondamento)
  --modo depara    Preenche fator_conversao no De-Para via CadastroPalletizacao (regex NxM)
  --modo ambos     Executa os dois

Flags:
  --dry-run        Apenas mostra o que seria alterado, sem gravar
  --verbose        Mostra detalhes de cada linha/registro

Uso:
    source .venv/bin/activate
    python scripts/migrations/backfill_conversao_devolucao.py --modo qtd --dry-run
    python scripts/migrations/backfill_conversao_devolucao.py --modo depara --dry-run
    python scripts/migrations/backfill_conversao_devolucao.py --modo ambos
"""

import argparse
import re
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from decimal import Decimal
from app import create_app
from app import db


# =========================================================================
# MODO 1: Recalcular quantidade_convertida nas linhas de NFD
# =========================================================================

def backfill_quantidade_convertida(dry_run=False, verbose=False):
    """
    Recalcula quantidade_convertida = quantidade / qtd_por_caixa com 4 casas.

    Afeta linhas onde:
    - qtd_por_caixa > 1 (tem conversão)
    - quantidade IS NOT NULL
    - quantidade_convertida IS NOT NULL (já foi calculada antes)
    - o valor atual difere do recalculado (evita writes desnecessários)

    Também recalcula peso_bruto quando CadastroPalletizacao.peso_bruto disponível.
    """
    from app.devolucao.models import NFDevolucaoLinha
    from app.producao.models import CadastroPalletizacao

    print("\n" + "=" * 60)
    print("BACKFILL: quantidade_convertida (precisão 4 casas)")
    print("=" * 60)

    # Buscar linhas candidatas
    linhas = NFDevolucaoLinha.query.filter(
        NFDevolucaoLinha.qtd_por_caixa.isnot(None),
        NFDevolucaoLinha.qtd_por_caixa > 1,
        NFDevolucaoLinha.quantidade.isnot(None),
        NFDevolucaoLinha.quantidade_convertida.isnot(None)
    ).all()

    print(f"Linhas candidatas: {len(linhas)}")

    # Cache de CadastroPalletizacao para peso
    codigos = set(l.codigo_produto_interno for l in linhas if l.codigo_produto_interno)
    cadastro_cache = {}
    if codigos:
        produtos = CadastroPalletizacao.query.filter(
            CadastroPalletizacao.cod_produto.in_(codigos)
        ).all()
        cadastro_cache = {p.cod_produto: p for p in produtos}
        print(f"Produtos em cache: {len(cadastro_cache)}")

    alteradas_qtd = 0
    alteradas_peso = 0
    skipped = 0
    delta_valor_total = 0.0  # Impacto financeiro acumulado (valor/cx)

    for linha in linhas:
        qtd = float(linha.quantidade)
        fator = int(linha.qtd_por_caixa)
        atual = float(linha.quantidade_convertida)

        # Recalcular com 4 casas
        correto = round(qtd / fator, 4)
        diff_qtd = abs(atual - correto)

        if diff_qtd < 0.00005:
            skipped += 1
            continue

        # Calcular impacto no valor/cx (valor_total / quantidade_convertida)
        valor_total = float(linha.valor_total) if linha.valor_total else None
        valor_cx_antes = None
        valor_cx_depois = None
        if valor_total and atual > 0 and correto > 0:
            valor_cx_antes = round(valor_total / atual, 2)
            valor_cx_depois = round(valor_total / correto, 2)
            delta_valor_total += abs(valor_cx_depois - valor_cx_antes)

        if verbose:
            valor_info = ""
            if valor_cx_antes is not None:
                valor_info = f" | valor/cx: R$ {valor_cx_antes:.2f} -> R$ {valor_cx_depois:.2f}"
            print(f"  Linha {linha.id}: {qtd} / {fator} = {correto:.4f} (era {atual:.4f}){valor_info}")

        if not dry_run:
            linha.quantidade_convertida = Decimal(str(correto))

        alteradas_qtd += 1

        # Recalcular peso se possível
        produto = cadastro_cache.get(linha.codigo_produto_interno)
        if produto and produto.peso_bruto:
            peso_correto = round(correto * float(produto.peso_bruto), 2)
            peso_atual = float(linha.peso_bruto) if linha.peso_bruto else None

            if peso_atual is None or abs(peso_atual - peso_correto) >= 0.005:
                if verbose:
                    print(f"    Peso: {peso_atual} -> {peso_correto}")
                if not dry_run:
                    linha.peso_bruto = Decimal(str(peso_correto))
                alteradas_peso += 1

    if not dry_run and alteradas_qtd > 0:
        db.session.commit()

    print(f"\nResultado:")
    print(f"  Quantidade recalculada: {alteradas_qtd}")
    print(f"  Peso recalculado:       {alteradas_peso}")
    print(f"  Sem alteração:          {skipped}")
    print(f"  Impacto valor/cx total: R$ {delta_valor_total:.2f} (soma das diferenças absolutas)")
    print(f"  {'[DRY-RUN] Nada gravado.' if dry_run else '[OK] Gravado com sucesso.'}")


# =========================================================================
# MODO 2: Preencher fator_conversao no De-Para
# =========================================================================

def backfill_depara_fator(dry_run=False, verbose=False):
    """
    Preenche fator_conversao nos registros De-Para que estão com default 1.0
    quando o produto interno tem padrão NxM no nome.

    Lógica:
    1. Buscar De-Para com fator_conversao = 1.0 e unidade_medida_cliente = UNIDADE
    2. Lookup nosso_codigo → CadastroPalletizacao.nome_produto
    3. Extrair N do padrão NxM via regex
    4. Se N > 1, atualizar fator_conversao = N
    """
    from app.devolucao.models import DeParaProdutoCliente
    from app.producao.models import CadastroPalletizacao

    print("\n" + "=" * 60)
    print("BACKFILL: fator_conversao no De-Para")
    print("=" * 60)

    # Padrões de unidade que indicam UNIDADE (não CAIXA)
    UNIDADE_PATTERNS = ['UND', 'UNID', 'UN', 'UNI', 'PC', 'PECA', 'BD', 'BALDE',
                        'BLD', 'SC', 'SACO', 'PT', 'POTE', 'BL', 'BA', 'SH', 'SACHE']

    def is_unidade(um):
        if not um:
            return False
        um_upper = um.upper().strip()
        return any(u in um_upper for u in UNIDADE_PATTERNS)

    # Buscar De-Para com fator = 1.0 (default, possivelmente errado)
    deparas = DeParaProdutoCliente.query.filter(
        DeParaProdutoCliente.ativo.is_(True),
        DeParaProdutoCliente.fator_conversao == 1.0
    ).all()

    print(f"De-Para com fator=1.0: {len(deparas)}")

    # Cache de CadastroPalletizacao
    codigos = set(d.nosso_codigo for d in deparas if d.nosso_codigo)
    cadastro_cache = {}
    if codigos:
        produtos = CadastroPalletizacao.query.filter(
            CadastroPalletizacao.cod_produto.in_(codigos)
        ).all()
        cadastro_cache = {p.cod_produto: p for p in produtos}
        print(f"Produtos em cache: {len(cadastro_cache)}")

    atualizados = 0
    sem_produto = 0
    sem_padrao = 0
    nao_unidade = 0

    for depara in deparas:
        # Verificar se unidade do cliente indica UNIDADE
        if depara.unidade_medida_cliente and not is_unidade(depara.unidade_medida_cliente):
            nao_unidade += 1
            continue

        # Buscar produto no cache
        produto = cadastro_cache.get(depara.nosso_codigo)
        if not produto or not produto.nome_produto:
            sem_produto += 1
            continue

        # Extrair NxM do nome
        match = re.search(r'(\d+)[Xx]\d+', produto.nome_produto)
        if not match:
            sem_padrao += 1
            continue

        fator = int(match.group(1))
        if fator <= 1:
            sem_padrao += 1
            continue

        if verbose:
            print(f"  De-Para {depara.id}: {depara.prefixo_cnpj}/{depara.codigo_cliente} "
                  f"-> {depara.nosso_codigo} ({produto.nome_produto}) fator={fator}")

        if not dry_run:
            depara.fator_conversao = Decimal(str(fator))

        atualizados += 1

    if not dry_run and atualizados > 0:
        db.session.commit()

    print(f"\nResultado:")
    print(f"  Fator atualizado:       {atualizados}")
    print(f"  Sem produto cadastro:   {sem_produto}")
    print(f"  Sem padrão NxM no nome: {sem_padrao}")
    print(f"  Unidade não é UN:       {nao_unidade}")
    print(f"  {'[DRY-RUN] Nada gravado.' if dry_run else '[OK] Gravado com sucesso.'}")


# =========================================================================
# MODO 3: Recalcular qtd_convertida de linhas que têm De-Para atualizado
#          mas qtd_convertida foi calculada com fator errado
# =========================================================================

def backfill_linhas_sem_conversao(dry_run=False, verbose=False):
    """
    Busca linhas de NFD que:
    - Têm código interno resolvido
    - NÃO têm quantidade_convertida (ficaram sem conversão)
    - Têm unidade de medida que indica UNIDADE

    Para essas, tenta calcular via CadastroPalletizacao.nome_produto → regex NxM.
    """
    from app.devolucao.models import NFDevolucaoLinha
    from app.producao.models import CadastroPalletizacao

    print("\n" + "=" * 60)
    print("BACKFILL: linhas sem conversão (quantidade_convertida IS NULL)")
    print("=" * 60)

    UNIDADE_PATTERNS = ['UND', 'UNID', 'UN', 'UNI', 'PC', 'PECA', 'BD', 'BALDE',
                        'BLD', 'SC', 'SACO', 'PT', 'POTE', 'BL', 'BA', 'SH', 'SACHE']

    def is_unidade(um):
        if not um:
            return False
        um_upper = um.upper().strip()
        return any(u in um_upper for u in UNIDADE_PATTERNS)

    linhas = NFDevolucaoLinha.query.filter(
        NFDevolucaoLinha.codigo_produto_interno.isnot(None),
        NFDevolucaoLinha.quantidade.isnot(None),
        NFDevolucaoLinha.quantidade_convertida.is_(None)
    ).all()

    print(f"Linhas sem conversão: {len(linhas)}")

    # Filtrar apenas UNIDADE
    linhas_unidade = [l for l in linhas if is_unidade(l.unidade_medida)]
    print(f"  com unidade tipo UN: {len(linhas_unidade)}")

    codigos = set(l.codigo_produto_interno for l in linhas_unidade)
    cadastro_cache = {}
    if codigos:
        produtos = CadastroPalletizacao.query.filter(
            CadastroPalletizacao.cod_produto.in_(codigos)
        ).all()
        cadastro_cache = {p.cod_produto: p for p in produtos}

    preenchidas = 0
    sem_padrao = 0

    for linha in linhas_unidade:
        produto = cadastro_cache.get(linha.codigo_produto_interno)
        if not produto or not produto.nome_produto:
            sem_padrao += 1
            continue

        match = re.search(r'(\d+)[Xx]\d+', produto.nome_produto)
        if not match:
            sem_padrao += 1
            continue

        fator = int(match.group(1))
        if fator <= 1:
            sem_padrao += 1
            continue

        qtd = float(linha.quantidade)
        qtd_convertida = round(qtd / fator, 4)

        if verbose:
            print(f"  Linha {linha.id}: {qtd} {linha.unidade_medida} / {fator} = {qtd_convertida:.4f} cx "
                  f"({produto.nome_produto})")

        if not dry_run:
            linha.qtd_por_caixa = fator
            linha.quantidade_convertida = Decimal(str(qtd_convertida))

            # Peso
            if produto.peso_bruto:
                peso = round(qtd_convertida * float(produto.peso_bruto), 2)
                linha.peso_bruto = Decimal(str(peso))

        preenchidas += 1

    if not dry_run and preenchidas > 0:
        db.session.commit()

    print(f"\nResultado:")
    print(f"  Conversão preenchida:   {preenchidas}")
    print(f"  Sem padrão NxM:         {sem_padrao}")
    print(f"  {'[DRY-RUN] Nada gravado.' if dry_run else '[OK] Gravado com sucesso.'}")


# =========================================================================
# MAIN
# =========================================================================

def main():
    parser = argparse.ArgumentParser(description='Backfill conversão devoluções')
    parser.add_argument('--modo', required=True,
                        choices=['qtd', 'depara', 'nulas', 'ambos', 'tudo'],
                        help='qtd=recalcular quantidade_convertida, '
                             'depara=preencher fator no De-Para, '
                             'nulas=preencher linhas sem conversão, '
                             'ambos=qtd+depara, tudo=todos')
    parser.add_argument('--dry-run', action='store_true',
                        help='Apenas mostra o que seria alterado')
    parser.add_argument('--verbose', action='store_true',
                        help='Mostra detalhes de cada registro')
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        print(f"Modo: {args.modo} | Dry-run: {args.dry_run} | Verbose: {args.verbose}")

        if args.modo in ('depara', 'ambos', 'tudo'):
            backfill_depara_fator(dry_run=args.dry_run, verbose=args.verbose)

        if args.modo in ('qtd', 'ambos', 'tudo'):
            backfill_quantidade_convertida(dry_run=args.dry_run, verbose=args.verbose)

        if args.modo in ('nulas', 'tudo'):
            backfill_linhas_sem_conversao(dry_run=args.dry_run, verbose=args.verbose)


if __name__ == '__main__':
    main()

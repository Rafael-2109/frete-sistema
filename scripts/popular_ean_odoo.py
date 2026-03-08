"""
Script para popular o campo codigo_ean na tabela cadastro_palletizacao
usando dados do Odoo (product.product.barcode_nacom via XML-RPC).

Para cada registro com codigo_ean IS NULL, busca o produto no Odoo
pelo default_code e preenche com barcode_nacom se disponivel.

Executar com:
    source .venv/bin/activate
    python scripts/popular_ean_odoo.py
    python scripts/popular_ean_odoo.py --dry-run
    python scripts/popular_ean_odoo.py --batch-size 100
"""

import sys
import os
import argparse
import ssl
import xmlrpc.client

# Adicionar raiz do projeto ao path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv

load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

from app import create_app, db
from app.producao.models import CadastroPalletizacao


def conectar_odoo():
    """Conecta ao Odoo via XML-RPC e retorna (uid, models_proxy)."""
    url = os.environ.get("ODOO_URL")
    odoo_db = os.environ.get("ODOO_DATABASE") or os.environ.get("ODOO_DB")
    username = os.environ.get("ODOO_USERNAME") or os.environ.get("ODOO_USER")
    password = os.environ.get("ODOO_PASSWORD")

    if not all([url, odoo_db, username, password]):
        faltando = []
        if not url:
            faltando.append("ODOO_URL")
        if not odoo_db:
            faltando.append("ODOO_DB")
        if not username:
            faltando.append("ODOO_USER")
        if not password:
            faltando.append("ODOO_PASSWORD")
        raise ValueError(
            f"Variaveis de ambiente obrigatorias nao definidas: {', '.join(faltando)}"
        )

    ssl_context = ssl.create_default_context()
    if url and ("localhost" in url or "127.0.0.1" in url):
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

    print(f"Conectando ao Odoo: {url} (DB: {odoo_db})")

    common = xmlrpc.client.ServerProxy(
        f"{url}/xmlrpc/2/common", context=ssl_context, allow_none=True
    )
    uid = common.authenticate(odoo_db, username, password, {})

    if not uid:
        raise ConnectionError("Falha na autenticacao com Odoo. Verifique as credenciais.")

    print(f"Autenticado no Odoo - UID: {uid}")

    models = xmlrpc.client.ServerProxy(
        f"{url}/xmlrpc/2/object", context=ssl_context, allow_none=True
    )

    return uid, models, odoo_db, password


def buscar_ean_odoo(models, uid, odoo_db, password, cod_produtos, batch_size):
    """
    Busca barcode_nacom no Odoo para uma lista de cod_produto.

    Retorna dict {cod_produto: barcode_nacom} para produtos encontrados.
    Tambem retorna sets de nao_encontrados e sem_ean.
    """
    resultado = {}
    nao_encontrados = set()
    sem_ean = set()

    # Processar em lotes
    for i in range(0, len(cod_produtos), batch_size):
        lote = cod_produtos[i : i + batch_size]
        print(
            f"  Consultando Odoo - lote {i // batch_size + 1} "
            f"({len(lote)} produtos, {i + 1}-{i + len(lote)} de {len(cod_produtos)})..."
        )

        try:
            produtos_odoo = models.execute_kw(
                odoo_db,
                uid,
                password,
                "product.product",
                "search_read",
                [[["default_code", "in", lote]]],
                {"fields": ["default_code", "barcode_nacom"], "limit": False},
            )
        except Exception as e:
            print(f"  ERRO ao consultar lote no Odoo: {e}")
            # Marcar todos do lote como nao encontrados para nao perder a contagem
            nao_encontrados.update(lote)
            continue

        # Indexar por default_code
        odoo_map = {}
        for p in produtos_odoo:
            code = p.get("default_code")
            if code:
                odoo_map[code] = p.get("barcode_nacom") or None

        # Classificar cada produto do lote
        for cod in lote:
            if cod not in odoo_map:
                nao_encontrados.add(cod)
            elif odoo_map[cod] is None or odoo_map[cod] is False:
                sem_ean.add(cod)
            else:
                resultado[cod] = odoo_map[cod]

    return resultado, nao_encontrados, sem_ean


def popular_ean(dry_run=False, batch_size=50):
    """Funcao principal: busca EAN no Odoo e atualiza cadastro_palletizacao."""

    app = create_app()

    with app.app_context():
        # 1. Buscar registros sem codigo_ean
        registros = (
            CadastroPalletizacao.query.filter(
                CadastroPalletizacao.codigo_ean.is_(None)
            )
            .order_by(CadastroPalletizacao.cod_produto)
            .all()
        )

        if not registros:
            print("Nenhum registro com codigo_ean NULL encontrado. Nada a fazer.")
            return

        print(f"Encontrados {len(registros)} registros com codigo_ean NULL")
        print()

        # 2. Extrair cod_produto (valores simples, antes de operacao longa)
        cod_produtos = [r.cod_produto for r in registros]
        registro_map = {r.cod_produto: r.id for r in registros}

        # 3. Conectar ao Odoo e buscar EANs
        uid, models, odoo_db, password = conectar_odoo()
        print()

        ean_map, nao_encontrados, sem_ean = buscar_ean_odoo(
            models, uid, odoo_db, password, cod_produtos, batch_size
        )
        print()

        # 4. Atualizar registros locais
        atualizados = 0
        erros = 0

        if ean_map:
            if dry_run:
                print("[DRY-RUN] Atualizacoes que seriam feitas:")
            else:
                print("Atualizando registros no banco local...")

            for cod_produto, barcode in ean_map.items():
                try:
                    registro_id = registro_map[cod_produto]

                    if dry_run:
                        print(f"  {cod_produto} -> codigo_ean = {barcode}")
                    else:
                        registro = db.session.get(CadastroPalletizacao, registro_id)
                        if registro:
                            registro.codigo_ean = barcode
                            atualizados += 1

                except Exception as e:
                    print(f"  ERRO ao atualizar {cod_produto}: {e}")
                    erros += 1

            if not dry_run and atualizados > 0:
                try:
                    db.session.commit()
                    print(f"Commit realizado: {atualizados} registros atualizados")
                except Exception as e:
                    db.session.rollback()
                    print(f"ERRO no commit: {e}")
                    return
        else:
            print("Nenhum EAN encontrado no Odoo para os produtos pendentes.")

        # 5. Relatorio
        print()
        print("=" * 60)
        print("RELATORIO")
        print("=" * 60)
        print(f"  Total com codigo_ean NULL:    {len(registros)}")
        print(f"  Atualizados:                  {atualizados if not dry_run else len(ean_map)} {'(dry-run)' if dry_run else ''}")
        print(f"  Sem EAN no Odoo:              {len(sem_ean)}")
        print(f"  Nao encontrados no Odoo:      {len(nao_encontrados)}")
        if erros:
            print(f"  Erros:                        {erros}")
        print("=" * 60)

        if nao_encontrados and len(nao_encontrados) <= 20:
            print()
            print("Produtos nao encontrados no Odoo:")
            for cod in sorted(nao_encontrados):
                print(f"  - {cod}")

        if sem_ean and len(sem_ean) <= 20:
            print()
            print("Produtos sem barcode_nacom no Odoo:")
            for cod in sorted(sem_ean):
                print(f"  - {cod}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Popular codigo_ean em cadastro_palletizacao a partir do Odoo"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mostra o que seria atualizado sem gravar no banco",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Quantidade de produtos por consulta ao Odoo (default: 50)",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("POPULAR codigo_ean EM cadastro_palletizacao VIA ODOO")
    print("=" * 60)
    if args.dry_run:
        print("[MODO DRY-RUN - nenhuma alteracao sera gravada]")
    print(f"Batch size: {args.batch_size}")
    print()

    popular_ean(dry_run=args.dry_run, batch_size=args.batch_size)

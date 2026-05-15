#!/usr/bin/env python3
"""
Export catalogo Tray Commerce (Motochefe Maringa) -> CSVs prontos para import na Bagy.

Fonte:
    https://www.motochefemaringa.com.br/web_api/products  (API publica, sem auth)
    + sitemap interno + HTML das paginas (descricao rica)

Uso:
    python scripts/ecommerce/export_tray_to_bagy.py
    python scripts/ecommerce/export_tray_to_bagy.py --quick           # so API (sem descricao)
    python scripts/ecommerce/export_tray_to_bagy.py --output-dir /tmp/saida
    python scripts/ecommerce/export_tray_to_bagy.py --store-url https://outra-loja-tray.com.br

Outputs (em ./scripts/ecommerce/output/ por default):
    produtos_bagy.csv          - CSV pronto para import na Bagy (UTF-8 com BOM)
    categorias.csv             - categorias detectadas (criar antes na Bagy)
    marcas.csv                 - marcas detectadas (criar antes na Bagy)
    imagens.csv                - produto_id, posicao, URL HD (download separado via wget/aria2)
    produtos_com_variacao.csv  - IDs com has_variation=1 (cadastrar variantes manual na Bagy)
    tray_raw_dump.json         - dump cru completo da API (referencia)
    log.txt                    - log de execucao

IMPORTANTE: nomes das colunas Bagy estao baseados em pesquisa publica da doc.
            Antes do import real, baixe o modelo oficial no painel Bagy
            (Produtos -> Mais acoes -> Importar produtos -> Baixar modelo)
            e ajuste os nomes de coluna se houver diferenca.
"""

from __future__ import annotations

import argparse
import csv
import html as html_lib
import json
import logging
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup

# Tray publica em ISO-8859-1; converter para UTF-8 antes de parsear
TRAY_CHARSET = "iso-8859-1"
DEFAULT_STORE_URL = "https://www.motochefemaringa.com.br"
PAGE_LIMIT = 50  # maximo permitido pela API Tray
REQUEST_TIMEOUT = 20
USER_AGENT = "Mozilla/5.0 (compatible; CatalogExporter/1.0)"


# ============================================================================
# Modelo intermediario (Tray -> normalizado)
# ============================================================================

@dataclass
class ProdutoNormalizado:
    """Modelo intermediario entre Tray e Bagy."""
    id_externo: str
    nome: str
    slug: str
    url_publica: str
    referencia: str
    modelo: str
    ean: str
    ncm: str
    marca: str
    marca_id: str
    preco: str
    preco_promocional: str
    ativo: bool
    tem_variacao: bool
    categoria_1: str
    categoria_2: str
    categoria_3: str
    meta_titulo: str
    meta_descricao: str
    meta_keywords: str
    descricao_curta: str
    descricao_completa: str  # preenchida em modo --full
    imagens: list[str] = field(default_factory=list)
    propriedades: dict[str, Any] = field(default_factory=dict)


# ============================================================================
# Fetcher Tray
# ============================================================================

class TrayFetcher:
    def __init__(self, store_url: str, log: logging.Logger):
        self.store_url = store_url.rstrip("/")
        self.log = log
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})

    def _get(self, path: str, **params) -> dict:
        """GET com decode ISO-8859-1 -> UTF-8 e parse JSON."""
        url = f"{self.store_url}{path}"
        self.log.debug("GET %s params=%s", url, params)
        resp = self.session.get(url, params=params, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        # Tray retorna ISO-8859-1 mesmo declarando UTF-8 as vezes; forcar decode
        text = resp.content.decode(TRAY_CHARSET, errors="replace")
        return json.loads(text)

    def fetch_all_products(self) -> list[dict]:
        """Paginar /web_api/products ate cobrir todos. Retorna lista de Product dicts."""
        all_products: list[dict] = []
        page = 1
        while True:
            data = self._get("/web_api/products", page=page, limit=PAGE_LIMIT)
            paging = data.get("paging", {})
            total = int(paging.get("total", 0))
            products = data.get("Products", [])
            for entry in products:
                all_products.append(entry["Product"])
            self.log.info("Fetched page %d: +%d (acumulado %d/%d)",
                          page, len(products), len(all_products), total)
            if len(all_products) >= total or not products:
                break
            page += 1
            time.sleep(0.3)  # cortesia com a API
        return all_products

    def fetch_brands(self) -> list[dict]:
        try:
            data = self._get("/web_api/brands")
            brands = []
            for entry in data.get("Brands", []):
                if isinstance(entry, dict):
                    brands.append(entry.get("Brand", entry))
            return brands
        except (requests.RequestException, json.JSONDecodeError, KeyError) as e:
            self.log.warning("Falha ao buscar /web_api/brands: %s", e)
            return []

    def fetch_product_description(self, product_url: str) -> tuple[str, str]:
        """Parsear pagina HTML do produto para extrair descricao curta e completa.

        Retorna (descricao_curta, descricao_completa). String vazia em caso de falha.
        """
        try:
            resp = self.session.get(product_url, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            html = resp.content.decode(TRAY_CHARSET, errors="replace")
        except requests.RequestException as e:
            self.log.warning("Falha HTML %s: %s", product_url, e)
            return "", ""

        # 1) JSON-LD (descricao curta + estruturada)
        descricao_curta = ""
        for m in re.finditer(
            r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
            html, re.DOTALL,
        ):
            try:
                obj = json.loads(m.group(1))
                if isinstance(obj, dict) and obj.get("@type") == "Product":
                    descricao_curta = (obj.get("description") or "").strip()
                    break
            except json.JSONDecodeError:
                continue

        # 2) Descricao completa - bloco no DOM (Tray usa varios padroes)
        soup = BeautifulSoup(html, "html.parser")
        descricao_completa = ""
        for selector in [
            "#productDescription",
            ".productDescription",
            ".product-description",
            "[itemprop='description']",
            "#tabDescription",
            ".tab-description",
        ]:
            node = soup.select_one(selector)
            if node:
                text = node.get_text(separator="\n", strip=True)
                if len(text) > len(descricao_completa):
                    descricao_completa = text
        # Fallback para descricao_curta se nao achou completa
        if not descricao_completa:
            descricao_completa = descricao_curta
        # Decodificar entities HTML (&ccedil; -> c, &amp; -> &, etc.)
        descricao_curta = html_lib.unescape(descricao_curta)
        descricao_completa = html_lib.unescape(descricao_completa)
        return descricao_curta, descricao_completa


# ============================================================================
# Mapeamento Tray -> Normalizado
# ============================================================================

CATEGORIA_SLUG_LABELS = {
    "autopropelido": "Autopropelido",
    "acessorios": "Acessorios",
    "bicicletas": "Bicicletas",
    "scooter": "Scooter",
    "motos": "Motos",
    "patinete": "Patinete",
    "patinetes": "Patinetes",
    "triciclo": "Triciclo",
    "triciclos": "Triciclos",
    "pecas": "Pecas",
    "baterias": "Baterias",
}

# Slugs que NAO sao categoria real (sao paginas de listagem genericas Tray)
SLUGS_NAO_CATEGORIA = {"todos", "all", "produtos"}


def slug_para_categoria(slug: str) -> tuple[str, str, str]:
    """Tray slug 'autopropelido/bike-eletrica-xyz' -> ('Autopropelido', '', '').

    Retorna ('A_CLASSIFICAR', '', '') para slugs sem prefixo de categoria ou
    com prefixo generico ('todos/...'), sinalizando revisao manual.
    """
    if not slug:
        return "A_CLASSIFICAR", "", ""
    partes = [p for p in slug.split("/") if p][:-1]  # ultima parte e o produto
    if not partes:
        return "A_CLASSIFICAR", "", ""
    cats = []
    for p in partes[:3]:
        if p.lower() in SLUGS_NAO_CATEGORIA:
            cats.append("A_CLASSIFICAR")
        else:
            label = CATEGORIA_SLUG_LABELS.get(p.lower(), p.replace("-", " ").title())
            cats.append(label)
    while len(cats) < 3:
        cats.append("")
    return cats[0], cats[1], cats[2]


def _to_float(valor: Any) -> float | None:
    if valor is None or valor == "":
        return None
    try:
        return float(str(valor).replace(",", "."))
    except (ValueError, TypeError):
        return None


def mapear_precos(tray_price: Any, tray_promotional: Any) -> tuple[str, str]:
    """Mapeia precos Tray -> (bagy_price, bagy_price_compare).

    Convencoes:
      - Tray.price = preco base/cheio
      - Tray.promotional_price = preco com desconto (quando > 0 e < price)
      - Bagy.price = preco final que cliente paga
      - Bagy.price_compare = preco 'de' riscado (sempre maior que price)

    Logica:
      Se ha promocao real (0 < promo < price):
          Bagy.price = promo;  Bagy.price_compare = price
      Senao:
          Bagy.price = price;  Bagy.price_compare = ''
    """
    p_base = _to_float(tray_price)
    p_promo = _to_float(tray_promotional)
    if p_base is None or p_base <= 0:
        return "0", ""
    if p_promo is not None and 0 < p_promo < p_base:
        return f"{p_promo:.2f}", f"{p_base:.2f}"
    return f"{p_base:.2f}", ""


def extrair_imagens_https(product_image: list[dict]) -> list[str]:
    """Tray ProductImage -> lista de URLs HD (https)."""
    urls = []
    for img in product_image or []:
        if isinstance(img, dict) and img.get("https"):
            urls.append(img["https"])
    return urls


def extrair_meta(metatag: list | dict) -> tuple[str, str, str]:
    """Extrai meta_title, meta_description, meta_keywords de metatag (formato variado)."""
    if not metatag:
        return "", "", ""
    title = description = keywords = ""
    items = metatag if isinstance(metatag, list) else [metatag]
    for entry in items:
        if not isinstance(entry, dict):
            continue
        for key, val in entry.items():
            kl = str(key).lower()
            if "title" in kl and not title:
                title = str(val)
            elif "description" in kl and not description:
                description = str(val)
            elif "keyword" in kl and not keywords:
                keywords = str(val)
    return title, description, keywords


def normalizar_produto(prod: dict) -> ProdutoNormalizado:
    cat1, cat2, cat3 = slug_para_categoria(prod.get("slug", ""))
    meta_t, meta_d, meta_k = extrair_meta(prod.get("metatag"))
    bagy_price, bagy_price_compare = mapear_precos(
        prod.get("price"), prod.get("promotional_price")
    )
    return ProdutoNormalizado(
        id_externo=str(prod.get("id", "")),
        nome=(prod.get("name") or "").strip(),
        slug=prod.get("slug", ""),
        url_publica=(prod.get("url") or {}).get("https", "") if isinstance(prod.get("url"), dict) else "",
        referencia=prod.get("reference") or prod.get("ean") or str(prod.get("id", "")),
        modelo=prod.get("model") or "",
        ean=prod.get("ean") or "",
        ncm=prod.get("ncm") or "",
        marca=prod.get("brand") or "",
        marca_id=str(prod.get("brand_id") or ""),
        preco=bagy_price,
        preco_promocional=bagy_price_compare,
        ativo=str(prod.get("available", "0")) == "1",
        tem_variacao=str(prod.get("has_variation", "0")) == "1",
        categoria_1=cat1,
        categoria_2=cat2,
        categoria_3=cat3,
        meta_titulo=meta_t,
        meta_descricao=meta_d,
        meta_keywords=meta_k,
        descricao_curta="",  # preenchido em modo --full
        descricao_completa="",
        imagens=extrair_imagens_https(prod.get("ProductImage", [])),
        propriedades=prod.get("Properties") or {},
    )


# ============================================================================
# Writers CSV (formato Bagy)
# ============================================================================

# IMPORTANTE: nomes de coluna baseados em pesquisa publica da doc Bagy.
# Confirmar contra o modelo oficial (painel Bagy -> Produtos -> Importar -> Baixar modelo).
BAGY_COLUNAS = [
    "product_external_id",   # OBRIGATORIO - id unico do produto (usamos id Tray)
    "variation_external_id", # OBRIGATORIO para variacoes
    "name",
    "description",           # aceita HTML
    "short_description",
    "price",
    "price_compare",         # preco "de" (riscado)
    "category_1",
    "category_2",
    "category_3",
    "brand",
    "reference",             # SKU / referencia interna
    "model",
    "ean",                   # = gtin / barcode
    "ncm",
    "weight",                # em kg
    "height",                # em cm
    "width",                 # em cm
    "depth",                 # em cm
    "active",                # 1/0
    "meta_title",
    "meta_description",
    "meta_keywords",
    "url",                   # slug / URL amigavel
    "image_url",             # primeira imagem (URL HD)
    # Multiplas imagens: alguns CSVs Bagy aceitam image_url_2, image_url_3...
    # ou uma coluna images com URLs separadas por ";". Verificar template.
    "image_url_2",
    "image_url_3",
    "image_url_4",
    "image_url_5",
]


def produto_para_linha_bagy(p: ProdutoNormalizado) -> dict[str, str]:
    """Mapeia ProdutoNormalizado -> dict com chaves BAGY_COLUNAS."""
    imgs = p.imagens + [""] * 5  # padding para evitar IndexError
    descricao = p.descricao_completa or p.descricao_curta or p.nome
    short = p.descricao_curta or (descricao[:240] if descricao else p.nome)
    return {
        "product_external_id": p.id_externo,
        "variation_external_id": "",  # sem variacao no export base
        "name": p.nome,
        "description": descricao,
        "short_description": short,
        "price": p.preco,
        "price_compare": p.preco_promocional,
        "category_1": p.categoria_1,
        "category_2": p.categoria_2,
        "category_3": p.categoria_3,
        "brand": p.marca,
        "reference": p.referencia,
        "model": p.modelo,
        "ean": p.ean,
        "ncm": p.ncm,
        "weight": "",   # nao disponivel na API publica
        "height": "",
        "width": "",
        "depth": "",
        "active": "1" if p.ativo else "0",
        "meta_title": p.meta_titulo,
        "meta_description": p.meta_descricao,
        "meta_keywords": p.meta_keywords,
        "url": p.slug,
        "image_url": imgs[0],
        "image_url_2": imgs[1],
        "image_url_3": imgs[2],
        "image_url_4": imgs[3],
        "image_url_5": imgs[4],
    }


def escrever_csv(path: Path, header: list[str], rows: list[dict], log: logging.Logger):
    path.parent.mkdir(parents=True, exist_ok=True)
    # utf-8-sig facilita abertura no Excel BR sem perder acento
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=header, quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in header})
    log.info("Escrito %s (%d linhas)", path, len(rows))


# ============================================================================
# Main pipeline
# ============================================================================

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--store-url", default=DEFAULT_STORE_URL,
                        help=f"URL base da loja Tray (default: {DEFAULT_STORE_URL})")
    parser.add_argument("--output-dir", default="scripts/ecommerce/output",
                        help="Diretorio de saida (default: scripts/ecommerce/output)")
    parser.add_argument("--quick", action="store_true",
                        help="Pular fetch HTML (sem descricao rica) - mais rapido")
    parser.add_argument("--verbose", "-v", action="store_true", help="Log debug")
    args = parser.parse_args(argv)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Logger: stderr + arquivo
    log = logging.getLogger("export_tray")
    log.setLevel(logging.DEBUG if args.verbose else logging.INFO)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    sh = logging.StreamHandler(sys.stderr)
    sh.setFormatter(formatter)
    log.addHandler(sh)
    fh = logging.FileHandler(out_dir / "log.txt", encoding="utf-8")
    fh.setFormatter(formatter)
    log.addHandler(fh)

    log.info("=== Export Tray -> Bagy ===")
    log.info("Store URL: %s", args.store_url)
    log.info("Modo: %s", "quick (so API)" if args.quick else "full (API + HTML)")

    fetcher = TrayFetcher(args.store_url, log)

    # 1) Catalogo
    raw_products = fetcher.fetch_all_products()
    log.info("Total produtos baixados: %d", len(raw_products))

    # 2) Dump cru (referencia)
    (out_dir / "tray_raw_dump.json").write_text(
        json.dumps(raw_products, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    log.info("Dump cru: %s", out_dir / "tray_raw_dump.json")

    # 3) Normalizar
    normalizados = [normalizar_produto(p) for p in raw_products]

    # 4) Modo full: pegar descricao via HTML (1 req por produto)
    if not args.quick:
        log.info("Buscando descricoes via HTML (%d produtos)...", len(normalizados))
        for i, p in enumerate(normalizados, 1):
            if not p.url_publica:
                continue
            curta, completa = fetcher.fetch_product_description(p.url_publica)
            p.descricao_curta = curta
            p.descricao_completa = completa
            if i % 10 == 0:
                log.info("  ... %d/%d", i, len(normalizados))
            time.sleep(0.2)

    # 5) CSV produtos (formato Bagy)
    rows = [produto_para_linha_bagy(p) for p in normalizados]
    escrever_csv(out_dir / "produtos_bagy.csv", BAGY_COLUNAS, rows, log)

    # 6) Categorias detectadas
    cats = set()
    for p in normalizados:
        for c in (p.categoria_1, p.categoria_2, p.categoria_3):
            if c:
                cats.add(c)
    cat_rows = [{"categoria": c, "criar_na_bagy": "sim"} for c in sorted(cats)]
    escrever_csv(out_dir / "categorias.csv",
                 ["categoria", "criar_na_bagy"], cat_rows, log)

    # 7) Marcas
    marcas: dict[str, str] = {}
    for p in normalizados:
        if p.marca:
            marcas[p.marca] = p.marca_id
    marca_rows = [{"marca": m, "tray_brand_id": i} for m, i in sorted(marcas.items())]
    escrever_csv(out_dir / "marcas.csv", ["marca", "tray_brand_id"], marca_rows, log)

    # 8) Imagens (download separado)
    imagem_rows = []
    for p in normalizados:
        for pos, url in enumerate(p.imagens, 1):
            imagem_rows.append({
                "produto_id": p.id_externo,
                "produto_nome": p.nome,
                "posicao": pos,
                "url_hd": url,
            })
    escrever_csv(out_dir / "imagens.csv",
                 ["produto_id", "produto_nome", "posicao", "url_hd"],
                 imagem_rows, log)

    # 9) Produtos com variacao (revisao manual)
    var_rows = [{
        "produto_id": p.id_externo,
        "nome": p.nome,
        "url": p.url_publica,
        "categoria_1": p.categoria_1,
        "obs": "Cadastrar variacoes manualmente no painel Bagy ou via API",
    } for p in normalizados if p.tem_variacao]
    escrever_csv(out_dir / "produtos_com_variacao.csv",
                 ["produto_id", "nome", "url", "categoria_1", "obs"],
                 var_rows, log)

    # 10) Resumo final
    log.info("=== Resumo ===")
    log.info("  Produtos exportados: %d", len(normalizados))
    log.info("  Com variacao (revisar manual): %d", sum(1 for p in normalizados if p.tem_variacao))
    log.info("  Ativos: %d / Inativos: %d",
             sum(1 for p in normalizados if p.ativo),
             sum(1 for p in normalizados if not p.ativo))
    log.info("  Categorias unicas: %d", len(cats))
    log.info("  Marcas unicas: %d", len(marcas))
    log.info("  URLs de imagem: %d", len(imagem_rows))
    log.info("Output: %s", out_dir.resolve())
    return 0


if __name__ == "__main__":
    sys.exit(main())

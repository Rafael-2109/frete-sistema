#!/usr/bin/env python3
"""
Analisa o XEROX baixado por xerox_site.sh e extrai os artefatos de tema
(CSS, design tokens, fontes, JS, imagens) prontos para reaplicar na Bagy.

A Bagy NAO aceita upload direto de tema HTML/CSS pronto. Ela tem editor
visual + bloco CSS customizado + secoes HTML. Este script gera arquivos
auxiliares que voce cola/aplica no painel Bagy:

    tema_referencia/
    ├── css_custom_bagy.css       - CSS pronto para colar no painel Bagy
                                    (design tokens + estilos do tema atual)
    ├── design_tokens.json        - cores, fontes, breakpoints extraidos
    ├── fontes.txt                - fontes Google detectadas (importar na Bagy)
    ├── imagens_tema/             - logo, banners, icones (upload manual)
    ├── html_referencia/          - HTML de paginas-chave (consultar layout)
    └── inventario.txt            - relatorio de tudo que foi encontrado

Uso:
    python scripts/ecommerce/extract_theme.py
    python scripts/ecommerce/extract_theme.py --mirror-dir /caminho/mirror
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import shutil
import sys
from pathlib import Path

DEFAULT_MIRROR_DIR = Path(__file__).parent / "mirror"
DEFAULT_OUTPUT_DIR = Path(__file__).parent / "tema_referencia"

# Padroes de design tokens (variaveis CSS) usados pelo Tray Theme Base
DESIGN_TOKEN_PATTERN = re.compile(r"--([\w_-]+)\s*:\s*([^;]+);", re.MULTILINE)

# Fontes Google referenciadas (aceita & e &amp;)
GOOGLE_FONT_PATTERN = re.compile(
    r"https?://fonts\.googleapis\.com/css2?\?family=([^&\"'>\s]+)",
)

# Style inline em HTML
STYLE_BLOCK_PATTERN = re.compile(r"<style[^>]*>(.*?)</style>", re.DOTALL | re.IGNORECASE)

# Tray Commerce serve HTML em ISO-8859-1
HTML_ENCODING = "iso-8859-1"

# Imagens do tema (logo, banners, icones — diferente de imagens de produto)
TEMA_IMG_KEYWORDS = ("logo", "banner", "icon", "favicon", "footer", "header", "marca")

# Arquivos CSS principais do tema Tray (nomes conhecidos)
CSS_TEMA_NAMES = ("style.min.css", "personalizacao.css", "swiper.min.css", "theme.css")


def setup_logging(verbose: bool):
    log = logging.getLogger("extract_theme")
    log.setLevel(logging.DEBUG if verbose else logging.INFO)
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
    log.addHandler(handler)
    return log


def encontrar_arquivos_css(mirror_dir: Path, log) -> list[Path]:
    """Localiza CSS principais do tema (prioriza style.min.css, personalizacao)."""
    todos_css = list(mirror_dir.rglob("*.css"))
    log.info("Total de arquivos CSS no mirror: %d", len(todos_css))

    # Priorizar nomes conhecidos do Tray Theme Base
    principais = []
    outros = []
    for css in todos_css:
        if any(name in css.name.lower() for name in CSS_TEMA_NAMES):
            principais.append(css)
        else:
            outros.append(css)

    # Filtrar libs (bootstrap, jquery-ui, etc) que nao precisam ser replicadas
    libs_blacklist = ("bootstrap", "jquery", "swiper", "fontawesome", "font-awesome",
                      "select2", "datepicker", "owl", "slick")
    customizados = [c for c in outros
                    if not any(lib in c.name.lower() for lib in libs_blacklist)]

    log.info("CSS principais (tema): %d", len(principais))
    log.info("CSS customizados (excluindo libs): %d", len(customizados))
    return principais + customizados


def _ler_arquivo(path: Path) -> str:
    """Le arquivo tentando ISO-8859-1 (Tray) com fallback UTF-8."""
    try:
        return path.read_bytes().decode(HTML_ENCODING, errors="replace")
    except OSError:
        return ""


def extrair_design_tokens(mirror_dir: Path, css_files: list[Path], log) -> dict[str, str]:
    """Extrai variaveis CSS (--color_primary, --font_family, etc.).

    Tray Theme Base coloca tokens INLINE no <style> de cada HTML, nao em CSS
    separado. Buscar nos dois lugares (CSS + HTML inline). Filtra valores
    vazios (Tray gera --color_x: ; quando opcional nao foi setado).
    """
    tokens: dict[str, str] = {}
    libs_skip = ("swiper", "fontawesome", "font-awesome", "bootstrap")

    # Pass 1: CSS files (filtrando libs externas que tem tokens proprios)
    for css in css_files:
        if any(lib in css.name.lower() for lib in libs_skip):
            continue
        text = _ler_arquivo(css)
        for match in DESIGN_TOKEN_PATTERN.finditer(text):
            name = match.group(1).strip()
            value = match.group(2).strip()
            if value and value not in (";", "") and name not in tokens:
                tokens[name] = value

    # Pass 2: <style> blocks dentro de HTML (onde Tray realmente coloca os tokens)
    for html in mirror_dir.rglob("*.html"):
        text = _ler_arquivo(html)
        for style_match in STYLE_BLOCK_PATTERN.finditer(text):
            for match in DESIGN_TOKEN_PATTERN.finditer(style_match.group(1)):
                name = match.group(1).strip()
                value = match.group(2).strip()
                if value and value not in (";", "") and name not in tokens:
                    tokens[name] = value

    log.info("Design tokens extraidos: %d (CSS + HTML inline)", len(tokens))
    return tokens


def detectar_fontes(mirror_dir: Path, tokens: dict[str, str], log) -> list[str]:
    """Procura referencias a fontes Google.

    3 fontes:
      1. Token --font_family (mais confiavel — Tray sempre define)
      2. URL Google Fonts crua (?family=)
      3. URL Google Fonts URL-encoded pelo wget (%3Ffamily=)
    """
    import html as html_lib
    import urllib.parse
    fontes_set: set[str] = set()

    # Fonte 1: token --font_family
    for nome, valor in tokens.items():
        if "font" in nome.lower() and "family" in nome.lower():
            # "'Montserrat', sans-serif" -> "Montserrat"
            primeira = valor.split(",")[0].strip().strip("'\"")
            if primeira and primeira.lower() not in ("inherit", "initial", "sans-serif", "serif"):
                fontes_set.add(primeira)

    # Fontes 2+3: URL Google Fonts (com decode URL-encoded do wget)
    pattern_flexivel = re.compile(
        r"fonts\.googleapis\.com/css2?(?:\?|%3F)family=([A-Za-z+]+)",
        re.IGNORECASE,
    )
    for ext in ("*.html", "*.css"):
        for arq in mirror_dir.rglob(ext):
            text = html_lib.unescape(_ler_arquivo(arq))
            text = urllib.parse.unquote(text)  # decodifica %3F -> ?, %3B -> ;
            for match in pattern_flexivel.finditer(text):
                family = match.group(1).replace("+", " ").strip()
                if family:
                    fontes_set.add(family)

    log.info("Fontes detectadas: %s", sorted(fontes_set))
    return sorted(fontes_set)


def detectar_logo_e_assets_visuais(mirror_dir: Path, log) -> set[Path]:
    """Procura URLs referenciadas como logo/banner em HTML, mesmo em img_prod/.

    Tray armazena o logo da loja em /img/img_prod/ (por design ruim). Filtro
    por keyword no nome falha. Solucao: parsear HTML procurando img/a com
    classes/IDs caracteristicos.
    """
    referencias: set[str] = set()
    padroes_logo = [
        re.compile(r'<img[^>]+(?:alt|class|id)=["\'][^"\']*(?:logo|brand)[^"\']*["\'][^>]*src=["\']([^"\']+)["\']', re.IGNORECASE),
        re.compile(r'<a[^>]+(?:class|id)=["\'][^"\']*logo[^"\']*["\'][^>]*>.*?<img[^>]+src=["\']([^"\']+)["\']', re.IGNORECASE | re.DOTALL),
        re.compile(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', re.IGNORECASE),
        re.compile(r'<link[^>]+rel=["\'][^"\']*icon[^"\']*["\'][^>]+href=["\']([^"\']+)["\']', re.IGNORECASE),
    ]
    home = mirror_dir / "www.motochefemaringa.com.br" / "index.html"
    htmls = [home] if home.exists() else list(mirror_dir.rglob("index.html"))[:3]
    if not htmls:
        htmls = list(mirror_dir.rglob("*.html"))[:5]

    for html in htmls:
        text = _ler_arquivo(html)
        for pat in padroes_logo:
            for match in pat.finditer(text):
                url = match.group(1).strip()
                if url and not url.startswith("data:"):
                    referencias.add(url)

    # Mapear URLs para arquivos baixados
    encontrados: set[Path] = set()
    for url in referencias:
        # extrair nome do arquivo da URL
        nome_base = re.sub(r'\?.*$', '', url.rsplit('/', 1)[-1])
        if not nome_base:
            continue
        for arq in mirror_dir.rglob(nome_base + "*"):
            if arq.is_file():
                encontrados.add(arq)
    log.info("Assets visuais (logo/og:image/favicon) referenciados: %d arquivos",
             len(encontrados))
    return encontrados


def coletar_imagens_tema(mirror_dir: Path, log) -> list[Path]:
    """Coleta imagens do TEMA (logo, banners, icones), nao de produto.

    Combina 3 fontes:
      1. Imagens com keyword no nome/path (logo, banner, icon, etc.)
      2. Imagens fora de img_prod/ (tema vive em files/{store_id}/themes/)
      3. URLs detectadas via parser HTML (logo, og:image, favicon)
    """
    candidatos: set[Path] = set()

    # Fonte 1+2: regex no path
    for ext in ("*.png", "*.jpg", "*.jpeg", "*.svg", "*.webp", "*.ico"):
        for img in mirror_dir.rglob(ext):
            path_lower = str(img).lower()
            name_lower = img.name.lower()
            # Tema: arquivos em files/<store>/themes/
            if "/themes/" in path_lower or "/themes-store/" in path_lower:
                candidatos.add(img)
                continue
            # Keyword no nome (logo, banner, etc.) — mesmo em img_prod
            if any(kw in name_lower for kw in TEMA_IMG_KEYWORDS):
                candidatos.add(img)
                continue
            # Fora de img_prod com keyword no path
            if "img_prod" not in path_lower and any(kw in path_lower for kw in TEMA_IMG_KEYWORDS):
                candidatos.add(img)

    # Fonte 3: imagens referenciadas como logo/og no HTML
    candidatos.update(detectar_logo_e_assets_visuais(mirror_dir, log))

    log.info("Imagens de tema detectadas (combinado): %d", len(candidatos))
    return sorted(candidatos)


def coletar_paginas_chave(mirror_dir: Path, log) -> list[Path]:
    """Coleta HTML de paginas estruturalmente importantes."""
    paginas_alvo = (
        "index.html",
        "quem-somos",
        "contato",
        "como-comprar",
        "politica-de-frete-e-entregas",
        "trocas-e-devolucoes",
        "seguranca",
        "tempo-de-garantia",
        "vendas-corporativas",
    )
    encontradas = []
    for html in mirror_dir.rglob("*.html"):
        nome = html.stem.lower()
        if any(alvo in nome or alvo in str(html).lower() for alvo in paginas_alvo):
            encontradas.append(html)
    log.info("Paginas-chave HTML: %d", len(encontradas))
    return encontradas


def gerar_css_custom_bagy(tokens: dict[str, str], css_files: list[Path],
                          output_path: Path, log):
    """Concatena CSS principais + tokens em arquivo unico para colar na Bagy."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    linhas = [
        "/* ========================================================== */",
        "/* CSS extraido do XEROX motochefemaringa.com.br (Tray Theme)  */",
        "/* Cole no painel Bagy: Loja virtual -> Editor visual ->        */",
        "/* Configuracoes -> CSS customizado                            */",
        "/* ========================================================== */",
        "",
        ":root {",
    ]
    for name, value in sorted(tokens.items()):
        linhas.append(f"  --{name}: {value};")
    linhas.append("}")
    linhas.append("")

    # Anexar CSS principal (style.min.css se existir)
    for css in css_files:
        if "style" in css.name.lower() or "personalizacao" in css.name.lower():
            try:
                content = css.read_text(encoding="utf-8", errors="replace")
            except OSError as e:
                log.warning("Falha ao incluir %s: %s", css, e)
                continue
            linhas.append("")
            linhas.append(f"/* === Origem: {css.name} === */")
            linhas.append(content)
            linhas.append(f"/* === Fim: {css.name} === */")

    output_path.write_text("\n".join(linhas), encoding="utf-8")
    log.info("CSS para Bagy escrito: %s (%d KB)", output_path,
             output_path.stat().st_size // 1024)


def gerar_inventario(output_dir: Path, dados: dict, log):
    """Relatorio textual de tudo que foi encontrado."""
    inv = output_dir / "inventario.txt"
    linhas = [
        "=== INVENTARIO XEROX -> Tema Bagy ===",
        f"Gerado em: {dados['timestamp']}",
        f"Mirror analisado: {dados['mirror_dir']}",
        "",
        f"Design tokens extraidos: {len(dados['tokens'])}",
        f"Fontes Google detectadas: {', '.join(dados['fontes']) or '(nenhuma)'}",
        f"CSS files analisados: {len(dados['css_files'])}",
        f"Imagens de tema: {len(dados['imagens'])}",
        f"Paginas-chave HTML: {len(dados['paginas'])}",
        "",
        "=== Cores principais (do design tokens) ===",
    ]
    cores = {k: v for k, v in dados["tokens"].items()
             if "color" in k.lower() and v.startswith("#")}
    for k, v in sorted(cores.items()):
        linhas.append(f"  {k:>40}: {v}")

    linhas += [
        "",
        "=== Fontes a adicionar no painel Bagy ===",
        "(Loja virtual -> Editor visual -> Tipografia)",
    ]
    for f in dados["fontes"]:
        linhas.append(f"  - {f}")

    linhas += [
        "",
        "=== Imagens de tema (upload manual no painel Bagy) ===",
    ]
    for img in dados["imagens"][:50]:
        linhas.append(f"  {img.name}  ({img.stat().st_size // 1024} KB)")
    if len(dados["imagens"]) > 50:
        linhas.append(f"  ... e mais {len(dados['imagens']) - 50}")

    linhas += [
        "",
        "=== Paginas-chave (referencia de layout) ===",
        "(Olhar na pasta html_referencia/ ou copiar texto para Bagy)",
    ]
    for p in dados["paginas"]:
        linhas.append(f"  {p.name}")

    linhas += [
        "",
        "=== Proximo passo ===",
        "1. Criar conta Bagy (plano Escala R$ 119/mes para acesso CSS)",
        "2. Escolher tema base mais proximo no painel Bagy",
        "3. Copiar tema_referencia/css_custom_bagy.css no painel",
        "4. Importar fontes (Tipografia)",
        "5. Upload de logo/banners da pasta imagens_tema/",
        "6. Replicar texto das paginas institucionais (html_referencia/)",
        "7. Importar produtos via produtos_bagy.csv (script anterior)",
    ]
    inv.write_text("\n".join(linhas), encoding="utf-8")
    log.info("Inventario: %s", inv)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--mirror-dir", default=str(DEFAULT_MIRROR_DIR),
                        help="Diretorio do XEROX (default: scripts/ecommerce/mirror)")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR),
                        help="Saida (default: scripts/ecommerce/tema_referencia)")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args(argv)

    log = setup_logging(args.verbose)
    mirror_dir = Path(args.mirror_dir)
    output_dir = Path(args.output_dir)

    if not mirror_dir.exists():
        log.error("Mirror nao encontrado: %s", mirror_dir)
        log.error("Rode primeiro: bash scripts/ecommerce/xerox_site.sh")
        return 1

    log.info("=== Extract theme ===")
    log.info("Mirror: %s", mirror_dir)
    log.info("Output: %s", output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    # 1) CSS files
    css_files = encontrar_arquivos_css(mirror_dir, log)

    # 2) Design tokens (CSS + HTML inline)
    tokens = extrair_design_tokens(mirror_dir, css_files, log)

    # 3) Fontes Google (depende dos tokens)
    fontes = detectar_fontes(mirror_dir, tokens, log)

    # 4) Imagens de tema
    imagens = coletar_imagens_tema(mirror_dir, log)

    # 5) Paginas-chave
    paginas = coletar_paginas_chave(mirror_dir, log)

    # 6) Gerar artefatos
    gerar_css_custom_bagy(tokens, css_files, output_dir / "css_custom_bagy.css", log)

    (output_dir / "design_tokens.json").write_text(
        json.dumps(tokens, indent=2, ensure_ascii=False), encoding="utf-8")
    log.info("Tokens: %s", output_dir / "design_tokens.json")

    (output_dir / "fontes.txt").write_text("\n".join(fontes), encoding="utf-8")

    # Copiar imagens de tema
    img_dir = output_dir / "imagens_tema"
    img_dir.mkdir(exist_ok=True)
    for img in imagens:
        try:
            shutil.copy2(img, img_dir / img.name)
        except OSError as e:
            log.warning("Falha ao copiar %s: %s", img, e)
    log.info("Imagens de tema copiadas: %s", img_dir)

    # Copiar paginas-chave
    html_dir = output_dir / "html_referencia"
    html_dir.mkdir(exist_ok=True)
    for p in paginas:
        try:
            shutil.copy2(p, html_dir / p.name)
        except OSError as e:
            log.warning("Falha ao copiar %s: %s", p, e)
    log.info("HTML referencia copiado: %s", html_dir)

    # Inventario
    from datetime import datetime
    gerar_inventario(output_dir, {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "mirror_dir": str(mirror_dir),
        "tokens": tokens,
        "fontes": fontes,
        "css_files": css_files,
        "imagens": imagens,
        "paginas": paginas,
    }, log)

    log.info("=== Pronto ===")
    log.info("Output: %s", output_dir.resolve())
    return 0


if __name__ == "__main__":
    sys.exit(main())

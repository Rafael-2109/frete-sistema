#!/usr/bin/env python3
"""
imprimir_pedidos.py -- Imprime pedidos do portal Atacadao como PDF.

Dois modos:
  - Detalhe: --pedido (abre pagina do pedido especifico, gera PDF)
  - Listagem: --cnpj sem --pedido (lista pedidos da unidade, gera PDF)

Uso:
    python imprimir_pedidos.py --pedido 457652
    python imprimir_pedidos.py --cnpj 75315333003043
    python imprimir_pedidos.py --pedido 457652 --cnpj 75315333003043
    python imprimir_pedidos.py --pedido 457652 --dry-run

Saida:
    JSON padronizado com resultado e caminho do PDF.
"""
import argparse
import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path

# Adicionar raiz do projeto ao path para imports
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

from atacadao_common import (
    gerar_saida,
    capturar_screenshot,
    criar_client_com_sessao,
    ATACADAO_URLS,
    TIMEOUTS,
)

logger = logging.getLogger(__name__)

# Diretorio de saida (separado de protocolos)
PDF_DIR = Path("/tmp/pedidos_atacadao")

# ──────────────────────────────────────────────
# Seletores do fluxo de Unidade (CNPJ)
# ──────────────────────────────────────────────

SELETORES_UNIDADE = {
    "toggle_filtros": 'a[data-toggle="collapse"][data-target="#filtros-collapse"]',
    "abrir_modal_unidade": "#filtro-unidade > div.input-group.f_editando > span:nth-child(3) > button",
    "campo_cnpj_modal": "#modal-unidades > div > div > div.modal-body > form > div > div.col-md-5.form-group > input",
    "botao_filtrar_modal": "#modal-unidades > div > div > div.modal-body > form > div > div.col-md-1.form-group > button",
    "radio_unidade": 'input[name="m_unidades_modal-unidades"]',
    "botao_confirmar_modal": "#modal-unidades > div > div > div.modal-footer > div > div > button.btn.btn-primary.selecionar",
    "modal_unidades": "#modal-unidades",
}

SELETORES_PEDIDO = {
    "campo_nr_pedido": "#nr_pedido",
    "botao_filtrar": "#enviarFiltros",
    "link_exibir": 'a[href*="/pedidos/"][title="Exibir"]',
    "limpar_data_elaboracao": 'button[data-target_daterangepicker="dthr_elaboracao"][data-action="remove"]',
}

SELETOR_CONTENT_WRAPPER = ".content-wrapper"


# ──────────────────────────────────────────────
# Validacao de entradas
# ──────────────────────────────────────────────

def _validar_entradas(pedido, cnpj):
    """Valida --pedido e/ou --cnpj.

    Args:
        pedido: Numero do pedido (str ou None)
        cnpj: CNPJ da unidade (str ou None)

    Returns:
        tuple: (pedido_limpo, cnpj_limpo)

    Raises:
        ValueError: Se entradas invalidas
    """
    if not pedido and not cnpj:
        raise ValueError(
            "Pelo menos --pedido ou --cnpj deve ser fornecido. "
            "Use --pedido para detalhe de um pedido, "
            "--cnpj para listar pedidos de uma unidade."
        )

    pedido_limpo = None
    cnpj_limpo = None

    if pedido:
        # Remover espacos
        pedido = pedido.strip()
        if not pedido.isdigit():
            raise ValueError(
                f"Pedido invalido (deve ser numerico): '{pedido}'"
            )
        if len(pedido) > 8:
            raise ValueError(
                f"Pedido invalido (maximo 8 digitos, recebeu {len(pedido)}): '{pedido}'. "
                "Se voce quis passar um CNPJ, use --cnpj."
            )
        pedido_limpo = pedido

    if cnpj:
        # Limpar formatacao: pontos, barras, hifens
        cnpj_limpo = re.sub(r"[.\-/]", "", cnpj.strip())
        if not cnpj_limpo.isdigit():
            raise ValueError(
                f"CNPJ invalido (deve conter apenas numeros): '{cnpj}'"
            )
        if len(cnpj_limpo) != 14:
            raise ValueError(
                f"CNPJ invalido (deve ter 14 digitos, recebeu {len(cnpj_limpo)}): '{cnpj_limpo}'"
            )

    return pedido_limpo, cnpj_limpo


# ──────────────────────────────────────────────
# Abrir area de filtros
# ──────────────────────────────────────────────

def _abrir_filtros(page):
    """Abre a area de filtros colapsavel na pagina de pedidos.

    Estrategia em 3 niveis:
    1. Verificar se campo ja esta visivel (filtros abertos)
    2. JS: forcar Bootstrap collapse show (mais confiavel que click)
    3. Fallback: clicar toggle

    Args:
        page: Playwright Page (sync)

    Returns:
        bool: True se filtros foram abertos (campo #nr_pedido visivel)
    """
    try:
        # 1. Aguardar pagina estabilizar (Vue.js / Bootstrap init)
        page.wait_for_timeout(2000)

        # 2. Verificar se campo ja esta visivel
        try:
            page.wait_for_selector(
                SELETORES_PEDIDO["campo_nr_pedido"],
                state="visible",
                timeout=2000,
            )
            logger.info("Filtros ja estao abertos")
            return True
        except Exception:
            pass

        # 3. Estrategia JS: forcar collapse aberto via Bootstrap/jQuery
        logger.info("Filtros fechados, forcando abertura via JS...")
        page.evaluate("""() => {
            const collapse = document.querySelector('#filtros-collapse');
            if (collapse) {
                // Bootstrap 3: adicionar 'in' e remover 'collapse'
                collapse.classList.add('in', 'show');
                collapse.classList.remove('collapsing');
                collapse.style.height = '';
                collapse.style.display = 'block';
                collapse.style.overflow = 'visible';
                // Tentar tambem via jQuery/Bootstrap API
                try { $(collapse).collapse('show'); } catch(e) {}
            }
        }""")
        page.wait_for_timeout(500)

        # 4. Verificar se funcionou
        try:
            page.wait_for_selector(
                SELETORES_PEDIDO["campo_nr_pedido"],
                state="visible",
                timeout=3000,
            )
            logger.info("Filtros abertos via JS")
            return True
        except Exception:
            pass

        # 5. Fallback: clicar toggle
        logger.info("JS nao funcionou, tentando click no toggle...")
        toggle = page.locator(SELETORES_UNIDADE["toggle_filtros"])
        if toggle.count() > 0:
            toggle.first.click()
            try:
                page.wait_for_selector(
                    SELETORES_PEDIDO["campo_nr_pedido"],
                    state="visible",
                    timeout=5000,
                )
                logger.info("Filtros abertos via click")
                return True
            except Exception:
                # Pode ter fechado — tentar clicar novamente
                toggle.first.click()
                page.wait_for_selector(
                    SELETORES_PEDIDO["campo_nr_pedido"],
                    state="visible",
                    timeout=5000,
                )
                return True

        logger.error("Nao foi possivel abrir filtros por nenhuma estrategia")
        return False
    except Exception as e:
        logger.warning(f"Erro ao abrir filtros: {e}")
        return False


# ──────────────────────────────────────────────
# Limpar filtro de data (pode restringir resultados)
# ──────────────────────────────────────────────

def _limpar_filtro_data(page):
    """Limpa filtro de data de elaboracao se presente.

    Args:
        page: Playwright Page (sync)
    """
    try:
        botao = page.locator(SELETORES_PEDIDO["limpar_data_elaboracao"])
        if botao.is_visible(timeout=1000):
            botao.click()
            page.wait_for_timeout(300)
            logger.info("Filtro dthr_elaboracao limpo")
    except Exception:
        pass  # Botao nao encontrado — ok


# ──────────────────────────────────────────────
# Filtrar por Unidade (CNPJ) via modal
# ──────────────────────────────────────────────

def _filtrar_unidade(page, cnpj):
    """Seleciona Unidade via modal de CNPJ na pagina de pedidos.

    Fluxo:
    1. Abre modal #modal-unidades
    2. Preenche CNPJ no campo de busca
    3. Clica filtrar dentro do modal
    4. Seleciona primeiro radio
    5. Confirma selecao

    Args:
        page: Playwright Page (sync)
        cnpj: CNPJ limpo (14 digitos)

    Returns:
        str ou None: Texto da unidade selecionada (ex: "183 - FILIAL X")
    """
    try:
        # 1. Abrir modal Unidade
        logger.info("Abrindo modal de Unidades...")
        btn_modal = page.locator(SELETORES_UNIDADE["abrir_modal_unidade"])
        btn_modal.click(timeout=TIMEOUTS["element_wait"])

        # 2. Aguardar modal ficar visivel
        page.wait_for_selector(
            SELETORES_UNIDADE["modal_unidades"],
            state="visible",
            timeout=TIMEOUTS["modal_wait"],
        )
        page.wait_for_timeout(500)

        # 3. Preencher CNPJ no campo do modal
        logger.info(f"Preenchendo CNPJ: {cnpj}")
        campo_cnpj = page.locator(SELETORES_UNIDADE["campo_cnpj_modal"])
        campo_cnpj.fill(cnpj)

        # 4. Clicar filtrar no modal
        logger.info("Filtrando no modal...")
        btn_filtrar = page.locator(SELETORES_UNIDADE["botao_filtrar_modal"])
        btn_filtrar.click()
        page.wait_for_timeout(2000)  # Aguardar AJAX do modal

        # 5. Selecionar primeiro radio (resultado da busca)
        radios = page.locator(SELETORES_UNIDADE["radio_unidade"])
        total_radios = radios.count()

        if total_radios == 0:
            logger.error(f"Nenhuma unidade encontrada para CNPJ {cnpj}")
            return None

        logger.info(f"Encontrada(s) {total_radios} unidade(s). Selecionando primeira...")
        radios.first.click()

        # Tentar extrair nome da unidade do value do radio (JSON) ou label
        unidade_texto = None
        try:
            value = radios.first.get_attribute("value")
            if value:
                import json
                data = json.loads(value)
                # Tentar extrair identificador (estrutura pode variar)
                nome = data.get("nome_fantasia") or data.get("razao_social") or data.get("nome", "")
                cod = data.get("codigo") or data.get("id", "")
                if cod and nome:
                    unidade_texto = f"{cod} - {nome}"
                elif nome:
                    unidade_texto = nome
        except Exception:
            pass

        if not unidade_texto:
            # Fallback: capturar texto da linha selecionada
            try:
                parent_row = radios.first.locator("xpath=ancestor::tr")
                unidade_texto = parent_row.text_content().strip()[:80]
            except Exception:
                unidade_texto = f"CNPJ {cnpj}"

        # 6. Confirmar selecao
        logger.info("Confirmando selecao...")
        btn_confirmar = page.locator(SELETORES_UNIDADE["botao_confirmar_modal"])
        btn_confirmar.click()
        page.wait_for_timeout(1000)  # Aguardar modal fechar

        logger.info(f"Unidade selecionada: {unidade_texto}")
        return unidade_texto

    except Exception as e:
        logger.error(f"Erro ao filtrar unidade: {e}")
        return None


# ──────────────────────────────────────────────
# Buscar pedido por numero
# ──────────────────────────────────────────────

def _buscar_pedido(page, nr_pedido):
    """Busca pedido por numero e clica em Exibir para abrir detalhe.

    Baseado em playwright_client.py:buscar_pedido e buscar_pedido_robusto.
    Verifica a coluna "N pedido original" (2a coluna) e clica no link
    a[title="Exibir"] dentro da linha correspondente.

    Args:
        page: Playwright Page (sync)
        nr_pedido: Numero do pedido (string)

    Returns:
        bool: True se pedido encontrado e pagina de detalhe aberta
    """
    try:
        # Aguardar campo ficar visivel e editavel antes de preencher
        logger.info(f"Aguardando campo #nr_pedido ficar visivel...")
        page.wait_for_selector(
            SELETORES_PEDIDO["campo_nr_pedido"],
            state="visible",
            timeout=10000,
        )

        # Limpar campo e preencher numero do pedido
        logger.info(f"Preenchendo pedido: {nr_pedido}")
        page.fill(SELETORES_PEDIDO["campo_nr_pedido"], "")
        page.wait_for_timeout(200)
        page.fill(SELETORES_PEDIDO["campo_nr_pedido"], nr_pedido)

        # Buscar com tentativas
        for tentativa in range(3):
            logger.info(f"Tentativa {tentativa + 1}/3...")

            # JS click — VueTables intercepta pointer events no click normal
            page.evaluate("document.querySelector('#enviarFiltros').click()")
            page.wait_for_timeout(2500 if tentativa == 0 else 1500)

            # Verificar resultados iterando as linhas da tabela
            linhas = page.locator("table tbody tr").all()
            for linha in linhas:
                colunas = linha.locator("td").all()
                if len(colunas) >= 2:
                    # 2a coluna = "N pedido original" (igual buscar_pedido_robusto)
                    pedido_original = colunas[1].text_content().strip()
                    if pedido_original == nr_pedido:
                        logger.info(f"Pedido {nr_pedido} encontrado na tabela!")

                        # Tentar link a[title="Exibir"] dentro da linha
                        link_exibir = linha.locator('a[title="Exibir"]')
                        if link_exibir.count() > 0:
                            link_exibir.first.click()
                            page.wait_for_load_state("domcontentloaded", timeout=TIMEOUTS["page_load"])
                            page.wait_for_timeout(1000)
                            return True

                        # Fallback: qualquer <a> com href contendo /pedidos/
                        link_pedido = linha.locator('a[href*="/pedidos/"]')
                        if link_pedido.count() > 0:
                            link_pedido.first.click()
                            page.wait_for_load_state("domcontentloaded", timeout=TIMEOUTS["page_load"])
                            page.wait_for_timeout(1000)
                            return True

                        # Fallback 2: clicar na primeira coluna (numero do pedido pode ser link)
                        primeiro_link = linha.locator("a").first
                        if primeiro_link.count() > 0:
                            primeiro_link.click()
                            page.wait_for_load_state("domcontentloaded", timeout=TIMEOUTS["page_load"])
                            page.wait_for_timeout(1000)
                            return True

                        # Ultimo recurso: navegar diretamente via URL
                        pedido_id = colunas[0].text_content().strip()
                        logger.info(f"Sem link clicavel, navegando para /pedidos/{pedido_id}")
                        page.goto(
                            ATACADAO_URLS["pedido_detalhe"].format(pedido_id=pedido_id),
                            wait_until="domcontentloaded",
                            timeout=TIMEOUTS["page_load"],
                        )
                        page.wait_for_timeout(1500)
                        return True

            # Limpar e tentar novamente
            if tentativa < 2:
                page.fill(SELETORES_PEDIDO["campo_nr_pedido"], "")
                page.wait_for_timeout(300)
                page.fill(SELETORES_PEDIDO["campo_nr_pedido"], nr_pedido)

        logger.warning(f"Pedido {nr_pedido} nao encontrado apos 3 tentativas")
        return False

    except Exception as e:
        logger.error(f"Erro ao buscar pedido: {e}")
        return False


# ──────────────────────────────────────────────
# Captura de PDF (tecnica de impressao_protocolo.py)
# ──────────────────────────────────────────────

def _capturar_pdf(page, nome_arquivo, diretorio=None):
    """Gera PDF via print direto da pagina (page.pdf()).

    Injeta CSS para esconder sidebar/navbar e ajustar layout,
    depois faz page.pdf() na pagina original — print real, nao reconstrucao.

    Args:
        page: Playwright Page (sync) — pagina a imprimir
        nome_arquivo: Nome base do PDF (sem extensao)
        diretorio: Path de destino (default: PDF_DIR)

    Returns:
        dict: {pdf_path, pdf_filename, pdf_size_kb} ou None se falhar
    """
    diretorio = diretorio or PDF_DIR
    diretorio.mkdir(parents=True, exist_ok=True)

    try:
        # 1. Injetar CSS de impressao para esconder elementos de navegacao
        logger.info("Injetando CSS de impressao...")
        page.evaluate("""() => {
            const style = document.createElement('style');
            style.id = 'print-override';
            style.textContent = `
                /* Esconder sidebar, navbar, footer */
                .main-sidebar, .main-header, .navbar,
                .control-sidebar, .main-footer,
                .sidebar-mini .main-sidebar,
                nav.navbar, header, footer {
                    display: none !important;
                }
                /* Content-wrapper ocupa toda largura */
                .content-wrapper {
                    margin-left: 0 !important;
                    min-height: auto !important;
                }
                body {
                    background: white !important;
                    overflow: visible !important;
                }
                /* Garantir que tabelas nao sejam cortadas */
                table { page-break-inside: auto; }
                tr { page-break-inside: avoid; }
            `;
            document.head.appendChild(style);
        }""")
        page.wait_for_timeout(500)

        # 2. Gerar PDF direto da pagina
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pdf_filename = f"{nome_arquivo}_{timestamp}.pdf"
        pdf_path = diretorio / pdf_filename

        logger.info(f"Gerando PDF (print direto)...")
        page.pdf(
            path=str(pdf_path),
            format="A4",
            print_background=True,
            margin={
                "top": "10mm",
                "right": "10mm",
                "bottom": "10mm",
                "left": "10mm",
            },
        )

        # 3. Remover CSS injetado (limpar pagina para uso posterior)
        page.evaluate("""() => {
            const style = document.getElementById('print-override');
            if (style) style.remove();
        }""")

        if not pdf_path.exists():
            logger.error("PDF nao foi criado")
            return None

        tamanho_kb = pdf_path.stat().st_size / 1024
        logger.info(f"PDF gerado: {pdf_path} ({tamanho_kb:.1f} KB)")

        return {
            "pdf_path": str(pdf_path),
            "pdf_filename": pdf_filename,
            "pdf_size_kb": round(tamanho_kb, 2),
        }

    except Exception as e:
        logger.error(f"Erro ao gerar PDF: {e}")
        return None


# ──────────────────────────────────────────────
# Orquestrador principal
# ──────────────────────────────────────────────

def imprimir_pedidos(pedido=None, cnpj=None, dry_run=False):
    """Orquestra impressao de pedidos do portal Atacadao.

    Args:
        pedido: Numero do pedido (ou None para modo listagem)
        cnpj: CNPJ da unidade (14 digitos, ou None)
        dry_run: Se True, apenas preview sem gerar PDF

    Returns:
        dict: Resultado JSON padronizado via gerar_saida()
    """
    # 1. Validar entradas
    try:
        pedido, cnpj = _validar_entradas(pedido, cnpj)
    except ValueError as e:
        return gerar_saida(False, erro=str(e))

    # Determinar modo
    if pedido:
        modo = "detalhe"
    else:
        modo = "listagem"

    # 2. Dry-run — apenas preview
    if dry_run:
        info = {
            "modo": "dry-run",
            "modo_real": modo,
            "pedido": pedido,
            "cnpj": cnpj,
            "url_base": ATACADAO_URLS["pedidos"],
        }
        if pedido:
            info["descricao"] = f"Abriria detalhe do pedido {pedido} e geraria PDF"
        else:
            info["descricao"] = f"Listaria pedidos da unidade CNPJ {cnpj} e geraria PDF"
        if cnpj:
            info["fluxo_unidade"] = "Selecionaria unidade via modal de CNPJ"

        return gerar_saida(True, **info)

    # 3. Execucao real — abrir browser com sessao
    client = None
    try:
        client = criar_client_com_sessao(headless=True)
        page = client.page

        # Ja estamos em /pedidos (verificar_sessao_sync navega para la)
        logger.info("Sessao valida. Iniciando fluxo de impressao...")

        # 4. Abrir area de filtros
        if not _abrir_filtros(page):
            capturar_screenshot(page, "erro_filtros")
            return gerar_saida(
                False,
                erro="Nao foi possivel abrir area de filtros",
                modo=modo,
            )

        # 5. Limpar filtro de data (pode restringir resultados)
        _limpar_filtro_data(page)

        # 6. [Se CNPJ] Filtrar por Unidade
        unidade_texto = None
        if cnpj:
            unidade_texto = _filtrar_unidade(page, cnpj)
            if not unidade_texto:
                capturar_screenshot(page, "erro_unidade")
                return gerar_saida(
                    False,
                    erro=f"Nenhuma unidade encontrada para CNPJ {cnpj}",
                    cnpj=cnpj,
                    modo=modo,
                )

        # 7. Modo DETALHE: buscar pedido e abrir pagina de detalhe
        if modo == "detalhe":
            if not _buscar_pedido(page, pedido):
                capturar_screenshot(page, f"pedido_nao_encontrado_{pedido}")
                return gerar_saida(
                    False,
                    erro=f"Pedido {pedido} nao encontrado no portal",
                    pedido=pedido,
                    cnpj=cnpj,
                    unidade=unidade_texto,
                    modo=modo,
                )

            # Capturar screenshot como evidencia antes do PDF
            screenshot_path = capturar_screenshot(page, f"detalhe_pedido_{pedido}")

            # Gerar PDF do detalhe
            pdf_result = _capturar_pdf(
                page, f"pedido_{pedido}"
            )

            if not pdf_result:
                return gerar_saida(
                    False,
                    erro="Falha ao gerar PDF do detalhe do pedido",
                    pedido=pedido,
                    modo=modo,
                    screenshot=screenshot_path,
                )

            return gerar_saida(
                True,
                modo=modo,
                pedido=pedido,
                cnpj=cnpj,
                unidade=unidade_texto,
                screenshot=screenshot_path,
                **pdf_result,
            )

        # 8. Modo LISTAGEM: aplicar filtros e capturar tabela
        else:
            # JS click — VueTables pode interceptar pointer events
            page.evaluate("document.querySelector('#enviarFiltros').click()")
            page.wait_for_timeout(2000)

            # Capturar screenshot como evidencia
            screenshot_path = capturar_screenshot(page, f"listagem_pedidos_{cnpj}")

            # Gerar PDF da listagem
            pdf_result = _capturar_pdf(
                page, f"listagem_{cnpj}"
            )

            if not pdf_result:
                return gerar_saida(
                    False,
                    erro="Falha ao gerar PDF da listagem de pedidos",
                    cnpj=cnpj,
                    unidade=unidade_texto,
                    modo=modo,
                    screenshot=screenshot_path,
                )

            return gerar_saida(
                True,
                modo=modo,
                cnpj=cnpj,
                unidade=unidade_texto,
                screenshot=screenshot_path,
                **pdf_result,
            )

    except RuntimeError as e:
        # Sessao expirada ou storage_state nao encontrado
        return gerar_saida(
            False,
            erro=str(e),
            requer_login="sessao" in str(e).lower() or "storage" in str(e).lower(),
            instrucao="Faca re-login interativo: python -m app.portal.atacadao.login_interativo",
        )

    except Exception as e:
        logger.error(f"Erro inesperado: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return gerar_saida(
            False,
            erro=f"Erro inesperado: {str(e)}",
            modo=modo,
        )

    finally:
        if client:
            try:
                client.fechar()
            except Exception:
                pass


# ──────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Imprime pedidos do portal Atacadao como PDF"
    )
    parser.add_argument(
        "--pedido",
        help="Numero do pedido (1-8 digitos). Ex: 457652",
    )
    parser.add_argument(
        "--cnpj",
        help="CNPJ da unidade (14 digitos, com ou sem formatacao). Ex: 75315333003043",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Apenas preview sem gerar PDF",
    )

    args = parser.parse_args()

    if not args.pedido and not args.cnpj:
        parser.error("Pelo menos --pedido ou --cnpj deve ser fornecido")

    resultado = imprimir_pedidos(
        pedido=args.pedido,
        cnpj=args.cnpj,
        dry_run=args.dry_run,
    )

    if not resultado.get("sucesso"):
        sys.exit(1)


if __name__ == "__main__":
    main()

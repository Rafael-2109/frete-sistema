import asyncio

from playwright.async_api import Playwright, async_playwright, expect


async def run(playwright: Playwright) -> None:
    browser = await playwright.chromium.launch(headless=False)
    context = await browser.new_context(storage_state="/home/rafaelnascimento/projetos/frete_sistema/app/portal/sendas/sendas_state.json")
    page = await context.new_page()
    await page.goto("https://plataforma.trizy.com.br/")
    await page.goto("https://plataforma.trizy.com.br/#/")
    await page.goto("https://plataforma.trizy.com.br/#/authenticate?redirectTo=Lw%3D%3D&externalQueryParams=e30%3D&trizyId=0&continueAuth")
    await page.goto("https://plataforma.trizy.com.br/#/terminal/painel")
    await page.get_by_label("Menu").click()
    await page.locator("releases-panel path").click()
    await page.get_by_role("button", name="Gestão de Pedidos").click()
    await page.frame_locator("#iframe-servico").get_by_role("button", name="AÇÕES").click()
    await page.frame_locator("#iframe-servico").get_by_role("menuitem", name="CONSUMIR ITENS").click()
    await page.frame_locator("#iframe-servico").get_by_role("button", name="DOWNLOAD PLANILHA").click()
    async with page.expect_download() as download_info:
        await page.frame_locator("#iframe-servico").get_by_role("menuitem", name="TODOS ITENS").click()
    download = await download_info.value

    # ---------------------
    await context.close()
    await browser.close()


async def main() -> None:
    async with async_playwright() as playwright:
        await run(playwright)


asyncio.run(main())

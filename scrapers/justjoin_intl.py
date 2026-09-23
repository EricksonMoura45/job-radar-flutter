import time

from playwright.sync_api import sync_playwright

from core.job import Job, extrair_data_publicacao
from core.logger import get_logger
from scrapers.base import BaseScraper

logger = get_logger()


def _modalidade(texto: str) -> str:
    texto_normalizado = texto.lower()
    if "hybrid" in texto_normalizado or "híbrido" in texto_normalizado:
        return "Híbrido"
    if "remote" in texto_normalizado or "remoto" in texto_normalizado:
        return "Remoto"
    if "office" in texto_normalizado or "on-site" in texto_normalizado:
        return "Presencial"
    return ""


def montar_job(titulo: str, empresa: str, local: str, texto_card: str, link: str) -> Job:
    return Job(
        titulo=titulo,
        empresa=empresa or "Não informado",
        local=local or "Não informado",
        link=link,
        site="Just Join IT",
        publicado_em=extrair_data_publicacao(texto_card),
        modalidade=_modalidade(texto_card),
    )


class JustJoinIntlScraper(BaseScraper):
    """Busca cards Flutter no board europeu Just Join IT.

    O board é renderizado pelo servidor, mas não oferece uma API pública
    estável. A busca é feita no board geral e o título é filtrado localmente,
    evitando depender de uma rota de keyword que muda com frequência.
    """

    def __init__(self, termos_busca: list[str], paginas: int = 3):
        self.termos_busca = termos_busca
        self.paginas = paginas

    def buscar_vagas(self) -> list[Job]:
        vagas: list[Job] = []
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(
                viewport={"width": 1440, "height": 1000},
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36"
                ),
            )
            try:
                for pagina in range(1, self.paginas + 1):
                    url = "https://justjoin.it/job-offers/all-locations"
                    if pagina > 1:
                        url += f"?page={pagina}"
                    page.goto(url, wait_until="domcontentloaded", timeout=60000)
                    page.wait_for_timeout(1500)

                    if page.get_by_text("DECLINE ALL", exact=True).count():
                        page.get_by_text("DECLINE ALL", exact=True).click(force=True)

                    cards = page.locator("a.offer_list_offer_title_link")
                    for index in range(cards.count()):
                        card_link = cards.nth(index)
                        titulo = card_link.inner_text().strip()
                        if not any(termo.lower() in titulo.lower() for termo in self.termos_busca):
                            continue

                        container = card_link.locator("xpath=../../../../..").first
                        texto_card = container.inner_text()
                        linhas = [linha.strip() for linha in texto_card.splitlines() if linha.strip()]
                        empresa = linhas[0] if linhas else "Não informado"
                        local = ""
                        for linha in linhas[1:]:
                            if linha != titulo and linha not in {"Hybrid", "Remote", "Office"}:
                                local = linha
                                break

                        link = card_link.get_attribute("href")
                        if not link:
                            continue
                        job = montar_job(titulo, empresa, local, texto_card, link)
                        vagas.append(job)
            except Exception as error:
                logger.warning(f"[Just Join IT] Falha ao consultar a fonte: {type(error).__name__}")
            finally:
                browser.close()

        logger.info(f"[Just Join IT] {len(vagas)} vaga(s) Flutter encontrada(s)")
        return vagas
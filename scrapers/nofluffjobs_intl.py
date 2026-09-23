from playwright.sync_api import sync_playwright

from core.job import Job, extrair_data_publicacao
from core.logger import get_logger
from scrapers.base import BaseScraper

logger = get_logger()


def montar_job(titulo: str, empresa: str, local: str, texto_card: str, link: str) -> Job:
    return Job(
        titulo=titulo,
        empresa=empresa or "Não informado",
        local=local or "Não informado",
        link=link,
        site="No Fluff Jobs",
        publicado_em=extrair_data_publicacao(texto_card),
        modalidade="Remoto" if "remote" in texto_card.lower() or "remoto" in texto_card.lower() else "",
        escopo_indefinido=True,
    )


class NoFluffJobsIntlScraper(BaseScraper):
    """Busca Flutter no No Fluff Jobs em mercados europeus e nos EUA.

    A plataforma pode bloquear IPs automatizados com 403. Nesse caso a fonte
    é registrada como indisponível e as demais fontes continuam normalmente.
    """

    PAISES = ("pl", "de", "nl", "es", "us")

    def __init__(self, termos_busca: list[str]):
        self.termos_busca = termos_busca

    def buscar_vagas(self) -> list[Job]:
        vagas: list[Job] = []
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page()
            try:
                for pais in self.PAISES:
                    page.goto(
                        f"https://nofluffjobs.com/{pais}/Flutter",
                        wait_until="domcontentloaded",
                        timeout=30000,
                    )
                    if page.url.startswith("https://nofluffjobs.com/") and page.title().startswith("ERROR"):
                        logger.warning(f"[No Fluff Jobs] Fonte bloqueada em {pais} (HTTP/CloudFront)")
                        continue
                    for card in page.locator('a[href*="/job/"]').all():
                        texto = card.inner_text().strip()
                        if not any(termo.lower() in texto.lower() for termo in self.termos_busca):
                            continue
                        link = card.get_attribute("href")
                        if not link:
                            continue
                        if link.startswith("/"):
                            link = f"https://nofluffjobs.com{link}"
                        linhas = [linha.strip() for linha in texto.splitlines() if linha.strip()]
                        titulo = linhas[0] if linhas else "Flutter"
                        empresa = linhas[1] if len(linhas) > 1 else "Não informado"
                        vagas.append(montar_job(titulo, empresa, "Remote", texto, link))
            except Exception as error:
                logger.warning(f"[No Fluff Jobs] Fonte indisponível: {type(error).__name__}")
            finally:
                browser.close()

        logger.info(f"[No Fluff Jobs] {len(vagas)} vaga(s) Flutter encontrada(s)")
        return vagas
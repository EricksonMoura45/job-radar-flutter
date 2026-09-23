from dataclasses import dataclass

from playwright.sync_api import sync_playwright

from core.job import Job, extrair_data_publicacao
from core.logger import get_logger
from scrapers.base import BaseScraper

logger = get_logger()


@dataclass(frozen=True)
class Board:
    nome: str
    url: str
    link_selector: str
    site: str


BOARDS = (
    Board("Remotar", "https://remotar.com.br/", 'a[href*="/job/"]', "Remotar"),
    Board("Remote OK", "https://remoteok.com/", "tr.job", "Remote OK"),
    Board("Wellfound", "https://wellfound.com/jobs", 'a[href*="/jobs/"]', "Wellfound"),
    Board("Arc", "https://arc.dev/remote-jobs", 'a[href*="/remote-jobs/j/"], a[href*="/remote-jobs/details/"]', "Arc.dev"),
    Board("FlutterJobs", "https://flutterjobs.com/", 'a[href*="/l/"]', "FlutterJobs"),
    Board("ProgramaThor", "https://programathor.com.br/jobs", 'a[href*="/jobs/"]', "ProgramaThor"),
    Board("Revelo", "https://revelo.com.br/vagas", 'a[href*="/vagas/"]', "Revelo"),
    Board("RemoteYeah", "https://remoteyeah.com/", 'a[href*="/jobs/"]', "RemoteYeah"),
)


def _texto_limpo(texto: str) -> list[str]:
    return [linha.strip() for linha in texto.splitlines() if linha.strip()]


def _extrair_empresa(linhas: list[str], titulo: str) -> str:
    for linha in linhas:
        if linha != titulo and linha.lower() not in {"apply", "ver vaga", "candidatar"}:
            return linha
    return "Não informado"


def montar_job(board: Board, titulo: str, texto_card: str, link: str) -> Job:
    linhas = _texto_limpo(texto_card)
    local = next(
        (
            linha
            for linha in linhas
            if any(sinal in linha.lower() for sinal in ("remote", "remoto", "worldwide", "europe", "usa", "united", "brasil"))
        ),
        "Não informado",
    )
    remoto = any(sinal in texto_card.lower() for sinal in ("remote", "remoto", "100% remoto"))
    modalidade = "Remoto" if remoto else ""
    return Job(
        titulo=titulo,
        empresa=_extrair_empresa(linhas, titulo),
        local=local,
        link=link,
        site=board.site,
        publicado_em=extrair_data_publicacao(texto_card),
        modalidade=modalidade,
        escopo_indefinido=remoto,
    )


class FlutterBoardsIntlScraper(BaseScraper):
    """Consulta boards adicionais com listagens públicas renderizadas.

    O título e o texto do card precisam conter Flutter; isso evita transformar
    um board genérico em fonte de ruído. Cada board é isolado para que 403,
    login ou mudança de layout não interrompa os demais.
    """

    def __init__(self, termos_busca: list[str]):
        self.termos_busca = termos_busca

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
            for board in BOARDS:
                try:
                    response = page.goto(board.url, wait_until="domcontentloaded", timeout=30000)
                    page.wait_for_timeout(1200)
                    if response and response.status >= 400:
                        logger.warning(f"[{board.nome}] indisponível: HTTP {response.status}")
                        continue

                    links = page.locator(board.link_selector)
                    encontrados = 0
                    links_vistos: set[str] = set()
                    for index in range(links.count()):
                        link_el = links.nth(index)
                        texto = link_el.inner_text().strip()
                        if link_el.evaluate("e => e.tagName") == "TR":
                            nested_link = link_el.locator('a[href*="/remote-jobs/"]').first
                            if nested_link.count():
                                texto = link_el.inner_text().strip()
                                link_el = nested_link
                        if "flutter" not in texto.lower():
                            for nivel in range(1, 4):
                                candidato = link_el.locator("xpath=" + "/.." * nivel).first
                                if candidato.count() and "flutter" in candidato.inner_text().lower():
                                    texto = candidato.inner_text().strip()
                                    break
                        if "flutter" not in texto.lower():
                            continue
                        titulo = next((linha for linha in _texto_limpo(texto) if "flutter" in linha.lower()), texto)
                        link = link_el.get_attribute("href")
                        if not link:
                            continue
                        if link.startswith("/"):
                            link = board.url.rstrip("/") + link
                        if link in links_vistos:
                            continue
                        links_vistos.add(link)
                        linhas = _texto_limpo(texto)
                        titulo = next(
                            (
                                linha
                                for linha in linhas
                                if "flutter" in linha.lower()
                                and not linha.lower().startswith("permalink:")
                            ),
                            titulo,
                        )
                        vagas.append(montar_job(board, titulo, texto, link))
                        encontrados += 1
                    logger.info(f"[{board.nome}] {encontrados} vaga(s) Flutter encontrada(s)")
                except Exception as error:
                    logger.warning(f"[{board.nome}] indisponível: {type(error).__name__}")
            browser.close()

        logger.info(f"[Flutter boards] {len(vagas)} vaga(s) encontrada(s) no total")
        return vagas
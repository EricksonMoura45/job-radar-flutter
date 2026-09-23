from core.perfis import PERFIL_FLUTTER_GLOBAL
from core.job import Job
from scrapers.justjoin_intl import _modalidade, montar_job as montar_job_justjoin
from scrapers.nofluffjobs_intl import montar_job as montar_job_nofluff
from scrapers.flutter_boards_intl import BOARDS, montar_job as montar_job_board


def test_justjoin_detecta_modalidade_remota():
    assert _modalidade("Company\nWarsaw\nRemote") == "Remoto"
    assert _modalidade("Company\nWarsaw\nHybrid") == "Híbrido"


def test_justjoin_monta_vaga_flutter_remota():
    job = montar_job_justjoin(
        "Flutter Developer",
        "Empresa Europa",
        "Warsaw",
        "Empresa Europa\nWarsaw\nRemote",
        "https://justjoin.it/job-offer/flutter-developer",
    )
    assert job.site == "Just Join IT"
    assert job.modalidade == "Remoto"
    assert job.combina_com(PERFIL_FLUTTER_GLOBAL.regras)


def test_nofluff_monta_vaga_remota_sem_inferir_sede_da_empresa():
    job = montar_job_nofluff(
        "Senior Flutter Developer",
        "Empresa dos EUA",
        "Remote",
        "Senior Flutter Developer\nEmpresa dos EUA\nRemote",
        "https://nofluffjobs.com/job/flutter-developer",
    )
    assert job.site == "No Fluff Jobs"
    assert job.escopo_indefinido
    assert job.combina_com(PERFIL_FLUTTER_GLOBAL.regras)


def test_flutter_global_rejeita_vaga_hibrida():
    job = Job(
        titulo="Flutter Developer",
        empresa="Empresa Europa",
        local="Berlin, Germany",
        link="https://example.com/flutter",
        site="Teste",
        modalidade="Híbrido",
    )
    assert job.combina_com(PERFIL_FLUTTER_GLOBAL.regras)


def test_flutter_global_aceita_vaga_presencial_em_qualquer_pais():
    job = Job(
        titulo="Flutter Developer",
        empresa="Empresa dos EUA",
        local="Austin, Texas, United States",
        link="https://example.com/flutter-us",
        site="Teste",
        modalidade="Presencial",
    )
    assert job.combina_com(PERFIL_FLUTTER_GLOBAL.regras)


def test_board_flutter_remoto_monta_job_aceito():
    board = next(board for board in BOARDS if board.site == "Remote OK")
    job = montar_job_board(
        board,
        "Flutter Engineer",
        "Flutter Engineer\nWorldwide\nRemote",
        "https://remoteok.com/remote-jobs/flutter-engineer",
    )
    assert job.site == "Remote OK"
    assert job.modalidade == "Remoto"
    assert job.combina_com(PERFIL_FLUTTER_GLOBAL.regras)
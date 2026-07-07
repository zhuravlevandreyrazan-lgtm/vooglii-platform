from __future__ import annotations

import io
import zipfile
from pathlib import Path

from openpyxl import Workbook

from vooglii_validation.wb_weekly_loader import load_wb_weekly_reference


def _write_reference_xlsx(path: Path) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Итоги"
    rows = [
        ["Еженедельный отчет 29.06.2026 - 05.07.2026 №772098550", None],
        ["Выручка", 22321.85],
        ["К перечислению продавцу", 18001.45],
        ["Логистика", 300.12],
        ["Хранение", 40.55],
        ["Эквайринг", 88.91],
        ["Удержания", 120.0],
        ["Прочие удержания", 55.0],
        ["Штрафы", 10.0],
        ["Реклама", 2171.61],
        ["Количество заказов", 15],
        ["Количество выкупов", 12],
        ["Количество возвратов", 3],
    ]
    for row in rows:
        sheet.append(row)
    workbook.save(path)


def test_weekly_loader_reads_xlsx(tmp_path):
    path = tmp_path / "Еженедельный отчет 29.06.2026 - 05.07.2026 №772098550.xlsx"
    _write_reference_xlsx(path)

    reference = load_wb_weekly_reference(str(path))

    assert str(reference.period_from) == "2026-06-29"
    assert str(reference.period_to) == "2026-07-05"
    assert reference.report_number == "772098550"
    assert reference.revenue == 22321.85
    assert reference.advertising == 2171.61
    assert reference.buyouts_count == 12


def test_weekly_loader_reads_zip_with_xlsx(tmp_path):
    xlsx_path = tmp_path / "nested.xlsx"
    _write_reference_xlsx(xlsx_path)
    zip_path = tmp_path / "Еженедельный детализированный отчет №772098550_250023510.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("report.xlsx", xlsx_path.read_bytes())

    reference = load_wb_weekly_reference(str(zip_path))

    assert reference.metadata["source_kind"] == "zip"
    assert reference.revenue == 22321.85
    assert reference.payout == 18001.45

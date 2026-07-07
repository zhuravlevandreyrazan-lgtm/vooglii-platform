from __future__ import annotations

from vooglii_telegram.services import sync_service


def test_update_text_uses_singular_grammar_for_advertising_and_cost():
    text = sync_service.format_sync_result(
        {
            "blocks": {
                "advertising": {"status": "PARTIAL", "raw_status": "ADS_PARTIAL"},
                "cost": {"status": "OK", "raw_status": "SUCCESS"},
            },
            "overall_status": "PARTIAL",
        }
    )

    assert "⚠ Реклама обновлена частично" in text
    assert "✅ Себестоимость обновлена" in text
    assert "Реклама обновлены частично" not in text
    assert "Себестоимость обновлён" not in text


def test_sync_status_lines_use_singular_grammar():
    assert sync_service._sync_status_line("advertising", {"status": "OK"}, None) == "Реклама: обновлена"
    assert sync_service._sync_status_line("advertising", {"status": "PARTIAL"}, None) == "Реклама: обновлена частично"
    assert sync_service._sync_status_line("cost", {"status": "OK"}, None) == "Себестоимость: заполнена"

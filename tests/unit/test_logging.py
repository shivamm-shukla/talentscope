import json
import logging
import sys

from core.logging import JsonFormatter


def _record(**extra: object) -> logging.LogRecord:
    record = logging.LogRecord(
        name="talentscope.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="something happened",
        args=(),
        exc_info=None,
    )
    for key, value in extra.items():
        setattr(record, key, value)
    return record


def test_formats_a_plain_record_as_json_with_expected_fields() -> None:
    payload = json.loads(JsonFormatter().format(_record()))
    assert payload["level"] == "INFO"
    assert payload["logger"] == "talentscope.test"
    assert payload["message"] == "something happened"
    assert "timestamp" in payload
    assert "extra" not in payload


def test_extra_fields_are_nested_under_extra() -> None:
    payload = json.loads(JsonFormatter().format(_record(fetched=3, matched=1)))
    assert payload["extra"] == {"fetched": 3, "matched": 1}


def test_exception_info_is_included() -> None:
    try:
        raise ValueError("boom")
    except ValueError:
        record = _record()
        record.exc_info = sys.exc_info()
    payload = json.loads(JsonFormatter().format(record))
    assert "ValueError: boom" in payload["exception"]

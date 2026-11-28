from types import SimpleNamespace

import pytest

from app.services.simulation_worker import accounted_tokens


@pytest.mark.parametrize(
    "events,expected",
    [
        ([{"attempt": 1, "reserved_tokens": 1000}], 1000),
        (
            [
                {"attempt": 1, "reserved_tokens": 1000},
                {"attempt": 1, "input_tokens": 100, "output_tokens": 200},
                {"attempt": 1, "error": "token_budget"},
            ],
            300,
        ),
        (
            [
                {"attempt": 1, "reserved_tokens": 1000},
                {"attempt": 1, "input_tokens": 0, "output_tokens": 0},
            ],
            0,
        ),
        (
            [
                {"attempt": 1, "reserved_tokens": 1000},
                {"attempt": 1, "error": "provider_unavailable"},
            ],
            1000,
        ),
        (
            [
                {"attempt": 1, "reserved_tokens": 1000},
                {"attempt": 1, "input_tokens": 100, "output_tokens": None},
            ],
            1000,
        ),
        (
            [
                {"attempt": 1, "reserved_tokens": 1000},
                {"attempt": 1, "input_tokens": 100, "output_tokens": 1200},
            ],
            1300,
        ),
        (
            [
                {"attempt": 1, "reserved_tokens": 1000},
                {"attempt": 1, "input_tokens": 100, "output_tokens": 200},
                {"attempt": 1, "input_tokens": 100, "output_tokens": 200},
                {"attempt": 2, "reserved_tokens": 1000},
            ],
            1300,
        ),
    ],
)
def test_known_usage_replaces_reservations_without_releasing_unknown_usage(
    events, expected
):
    assert accounted_tokens([SimpleNamespace(history=events)]) == expected


def test_attempt_numbers_are_scoped_to_each_persona():
    rows = [
        SimpleNamespace(
            history=[{"attempt": 1, "input_tokens": 100, "output_tokens": 200}]
        ),
        SimpleNamespace(history=[{"attempt": 1, "reserved_tokens": 1000}]),
    ]
    assert accounted_tokens(rows) == 1300

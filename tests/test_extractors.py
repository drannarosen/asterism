from asterism.extractors import (
    available_domain_extractors,
    extract_invariants,
    extract_line_invariant_kinds,
)


def test_available_domain_extractors_are_stable() -> None:
    assert available_domain_extractors() == (
        "equation",
        "units",
        "probability",
        "tolerance",
        "api_contract",
        "failing_test",
        "citation",
    )


def test_extract_line_invariant_kinds_covers_scientific_domains() -> None:
    assert extract_line_invariant_kinds("Equation: E = mc^2") == ("equation",)
    assert extract_line_invariant_kinds("units: cgs") == ("units",)
    assert extract_line_invariant_kinds("prior: log-flat") == ("prior",)
    assert extract_line_invariant_kinds("likelihood: gaussian") == ("likelihood",)
    assert extract_line_invariant_kinds("tolerance threshold") == ("tolerance",)
    assert extract_line_invariant_kinds("API schema contract") == ("api_contract",)
    assert extract_line_invariant_kinds("FAILED test_energy") == ("failing_test",)
    assert extract_line_invariant_kinds("doi:10.1234/example") == ("citation",)


def test_extract_invariants_preserves_line_offsets() -> None:
    markers = extract_invariants("intro\nunits: cgs\nEquation: E = mc^2\n", line_offset=10)

    assert [(marker.kind, marker.line_start) for marker in markers] == [
        ("units", 12),
        ("equation", 13),
    ]


def test_extractors_ignore_lockfile_assignments() -> None:
    content = 'name = "mypy"\nversion = "2.1.0"\nsdist = { url = "https://example.test" }\n'

    assert extract_invariants(content) == []

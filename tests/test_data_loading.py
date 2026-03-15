import app as app_module


def test_load_icd10_map():
    data = app_module.load_icd10_map()
    assert isinstance(data, dict)
    for code in ["A000", "A001", "A0100"]:
        assert code in data


def test_load_excluded_codes():
    excluded = app_module.load_excluded_codes()
    assert isinstance(excluded, set)
    assert "D8130" in excluded

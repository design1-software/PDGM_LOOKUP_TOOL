import app as app_module


def test_load_icd10_map():
    data = app_module.load_icd10_map()
    assert isinstance(data, dict)
    for code in ["A000", "A001", "A0100"]:
        assert code in data

import app as app_module


def test_normalize_icd10():
    assert app_module.normalize_icd10(" e11.01 ") == "E1101"


def test_normalize_query():
    assert app_module.normalize_query(" Diabetes Type 2  ") == "diabetes type 2"


def test_index_normalization(client):
    resp = client.post("/", data={"query": "e11.01"})
    assert resp.status_code == 200
    assert b"E11.01" in resp.data

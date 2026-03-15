import importlib


def test_reference_block_affects_prompt(tmp_path, monkeypatch):
    pdir = tmp_path / "prompts"
    pdir.mkdir()
    (pdir / "roadmap_template.md").write_text("TEMPLATE {reference_block}")
    (pdir / "roadmap_reference.md").write_text("REF_A")
    monkeypatch.setenv("PROMPT_DIR", str(pdir))
    import enhanced_prompt_manager as prompt_manager
    importlib.reload(prompt_manager)
    out1 = prompt_manager.build_system_prompt("roadmap", "MMTA", "E11.1", [])
    (pdir / "roadmap_reference.md").write_text("REF_B")
    importlib.reload(prompt_manager)
    out2 = prompt_manager.build_system_prompt("roadmap", "MMTA", "E11.1", [])
    assert out1 != out2

"""Section 111 reporting exclusions must not drive home health results."""

import pytest
from flask import template_rendered


@pytest.mark.parametrize('code', ['D8130', 'E1165', 'B950'])
def test_direct_lookup_does_not_assert_billability(client, app, monkeypatch, code):
    # D8130 was covered by the former Section 111 exclusion-loader test.
    # Include an ordinary lookup and a genuine principal-diagnosis warning.
    import blueprints.main.routes as routes

    monkeypatch.setattr(routes, 'ai_followup_question', lambda _: '')
    contexts = []

    def capture(sender, template, context, **extra):
        contexts.append(context)

    with template_rendered.connected_to(capture, app):
        response = client.post('/', data={'query': code})

    assert response.status_code == 200
    text = contexts[-1]['result']['Text']
    assert 'Description:' in text
    assert 'Code First:' in text
    assert 'Billable:' not in text
    assert 'Section 111' not in text
    if code == 'B950':
        assert 'Unacceptable PDx: Yes' in text


def test_ai_mapping_prompt_does_not_use_section111(monkeypatch, tmp_path):
    import app as core

    captured = {}
    expected = (
        'Focus of Care: E1165 Type 2 diabetes mellitus with hyperglycemia '
        'I MMTA_ENDO  ICD-10: E11.65\n'
        'Description: Type 2 diabetes mellitus with hyperglycemia\n'
        'PDGM Group: MMTA_ENDO\nComorbidity Group: No_group\n'
        'Code First: 0\nReason: Matches the supplied clinical phrase.'
    )

    def fake_call(system_prompt, user_prompt, max_tokens):
        captured.update(system=system_prompt, user=user_prompt)
        return expected

    monkeypatch.setattr(core, 'client', object())
    monkeypatch.setattr(core, 'get_candidate_codes', lambda _: [core.icd10_data['E1165']])
    monkeypatch.setattr(core, '_call_claude', fake_call)
    monkeypatch.setattr(core, 'AI_LOG_PATH', tmp_path / 'ai.jsonl')

    assert core.ai_map_phrase_to_code('diabetes with hyperglycemia') == expected
    prompt = captured['system'] + captured['user']
    assert 'Section 111' not in prompt
    assert 'Codes excluded as primary' not in prompt
    assert 'Billable:' not in prompt
    assert 'Do not determine or report billability or payment coverage.' in captured['system']
    assert 'E1165|' in captured['user']


def test_response_parsers_ignore_legacy_billability_lines():
    from app import parse_pdgm_details as core_parser
    from services.pdgm.impl import parse_pdgm_details as service_parser

    legacy_text = (
        'Focus of Care: E11.65\nDescription: Diabetes\n'
        'Comorbidity Group: No_group\nBillable: Yes\n'
    )
    for parse in (core_parser, service_parser):
        assert parse(legacy_text) == {
            'focus_of_care': 'E11.65',
            'description': 'Diabetes',
            'comorbidity_group': 'No_group',
        }

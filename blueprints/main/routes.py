from flask import jsonify, request, redirect, url_for, flash, render_template, session, get_flashed_messages
# removed flask_login import
from . import bp

from app import (
    normalize_icd10, format_icd10, format_pdgm_group,
    ai_map_phrase_to_code, ai_followup_question,
)
from services.pdgm.datasets import diagnosis_metadata, DiagnosisDateError, manifest
from services.pdgm.repository import get_icd10_map
import re
from services import cms_data
from services.pdgm.eligibility import assess_primary_diagnosis
from services.reimbursement_service import (
    ReimbursementService,
    ai_map_phrase_to_code_with_payment,
    format_payment_range_lines,
)
from app_core.extensions import cache
import uuid


@cache.memoize(timeout=3600)
def get_cached_icd10_data(code, service_date=None):
    return get_icd10_map(service_date).get(code)


def get_cached_ai_response(query, service_date=None):
    """AI response with simple Flask-Caching."""
    key = f"ai_response:{service_date}:{query.lower().strip()}"
    cached = cache.get(key)
    if cached:
        return cached
    result = ai_map_phrase_to_code(query, service_date=service_date)
    cache.set(key, result, timeout=1800)
    return result


@bp.route('/', methods=['GET', 'POST'])
def index():
    result = None
    query = ""
    area_code = ""
    try:
        metadata = diagnosis_metadata(request.values.get('service_date'))
    except DiagnosisDateError as e:
        return jsonify(error=str(e)), 400
    service_date = metadata['service_date']

    if request.method == 'POST':
        query = (request.form.get('query') or request.form.get('diagnosis') or '').strip()
        if not query:
            flash('Query field is required.')
            return redirect(url_for('main.index'))

        follow_answer = request.form.get("follow_answer", "").strip()
        full_query = f"{query} {follow_answer}" if follow_answer else query
        area_code = request.form.get('area_code', '').strip()

        icd_code = normalize_icd10(full_query)
        row = get_cached_icd10_data(icd_code, service_date)
        if row:
            focus = (
                f"Focus of Care: {format_icd10(row['icd10_code'])} "
                f"{row.get('description','')} "
                f"{row.get('pdgm_clinical_group_code','')} "
                f"{format_pdgm_group(row.get('pdgm_clinical_group_name',''))}  "
                f"ICD-10: {icd_code}"
            )
            assessment = assess_primary_diagnosis(row)

            lines = [
                focus,
                f"Description: {row.get('description','')}",
                f"PDGM Group: {format_pdgm_group(row.get('pdgm_clinical_group_name',''))}",
                f"Comorbidity Group: {row.get('COMORBIDITY_GROUP','')}",
                'Code First: ' + ('Review sequencing instructions below' if any(
                    flag['code'] == 'CODE_FIRST' for flag in assessment['flags']
                ) else 'No code-first entry in loaded mapping'),
            ]
            labels = {
                'UNACCEPTABLE_PDX': 'Unacceptable PDx: Yes',
                'UNSPECIFIED_PDX': 'Unspecified PDx: Yes',
            }
            for flag in assessment['flags']:
                lines.append(f"{labels.get(flag['code'], flag['code'])} - {flag['message']}")
                lines.append(f"What this means: {flag['explanation']}")
                lines.append(f"Next step: {flag['next_step']}")
            text_result = "\n".join(lines)
            # A diagnosis fixes the clinical group but not the functional level,
            # admission source/timing or comorbidity adjustment, so show the
            # bounded range rather than inventing the missing dimensions.
            if area_code and assessment['primary_eligibility']['eligible']:
                rng = ReimbursementService().payment_range(
                    row.get('pdgm_clinical_group_code', ''), area_code
                )
                range_lines = format_payment_range_lines(rng)
                if range_lines:
                    text_result += "\n" + "\n".join(range_lines)
            follow_up = ai_followup_question(full_query)
            result = {'Text': text_result, 'FollowUp': follow_up}
        elif re.fullmatch(r'[A-Z][0-9][0-9A-Z]{1,5}', icd_code):
            assessment = assess_primary_diagnosis(None)
            result = {'Text': '\n'.join(flag['message'] + '\n' + flag['explanation']
                       + '\nNext step: ' + flag['next_step'] for flag in assessment['flags']),
                      'FollowUp': ''}
        else:
            from services.pdgm.rules_engine import lookup_pdgm
            result = lookup_pdgm(full_query, service_date)

    return render_template(
        'index.html',
        result=result,
        diagnosis_data=metadata,
        service_date=service_date,
        diagnosis_date_min=manifest()['releases'][0]['effective_from'],
        diagnosis_date_max=manifest()['releases'][-1]['effective_through'],
        query=query,
        area_code=area_code,
        payment_areas=cms_data.list_areas(),
        lead_captured=session.get('lead_captured', False),
        lead_email=session.get('lead_email', ''),
    )

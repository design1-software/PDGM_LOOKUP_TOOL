from flask import request, redirect, url_for, flash, render_template, session, get_flashed_messages
# removed flask_login import
from . import bp

from app import (
    normalize_icd10, format_icd10, format_pdgm_group,
    icd10_data, excluded_codes,
    ai_map_phrase_to_code, ai_followup_question,
)
from services import cms_data
from services.reimbursement_service import (
    ReimbursementService,
    ai_map_phrase_to_code_with_payment,
    format_payment_range_lines,
)
from app_core.extensions import cache
import uuid


@cache.memoize(timeout=3600)
def get_cached_icd10_data(code):
    return icd10_data.get(code)


def get_cached_ai_response(query):
    """AI response with simple Flask-Caching."""
    key = f"ai_response:{query.lower().strip()}"
    cached = cache.get(key)
    if cached:
        return cached
    result = ai_map_phrase_to_code(query)
    cache.set(key, result, timeout=1800)
    return result


@bp.route('/', methods=['GET', 'POST'])
def index():
    result = None
    query = ""
    area_code = ""

    if request.method == 'POST':
        query = request.form.get('query', '').strip()
        if not query:
            flash('Query field is required.')
            return redirect(url_for('main.index'))

        follow_answer = request.form.get("follow_answer", "").strip()
        full_query = f"{query} {follow_answer}" if follow_answer else query
        area_code = request.form.get('area_code', '').strip()

        icd_code = normalize_icd10(full_query)
        row = get_cached_icd10_data(icd_code)
        if row:
            excluded = icd_code in excluded_codes
            focus = (
                f"Focus of Care: {format_icd10(row['icd10_code'])} "
                f"{row.get('description','')} "
                f"{row.get('pdgm_clinical_group_code','')} "
                f"{format_pdgm_group(row.get('pdgm_clinical_group_name',''))}  "
                f"ICD-10: {icd_code}"
            )
            # Unacceptable/unspecified PDX flags from CMS
            unacceptable_pdx = row.get('UNACCEPTABLE_PDX', '0') == '1'
            unspecified_pdx = row.get('UNSPECIFIED_PDX', '0') == '1'

            lines = [
                focus,
                f"Description: {row.get('description','')}",
                f"PDGM Group: {format_pdgm_group(row.get('pdgm_clinical_group_name',''))}",
                f"Comorbidity Group: {row.get('COMORBIDITY_GROUP','')}",
                f"Primary Awarding: {row.get('PRIMARY_AWARDING_FLAG','')}",
                f"Code First: {row.get('CODE_FIRST','')}",
                f"Billable: {'No (Section 111 Excluded)' if excluded else 'Yes'}",
            ]
            if unacceptable_pdx:
                lines.append("Unacceptable PDx: Yes - This code cannot be used as a principal diagnosis")
            if unspecified_pdx:
                lines.append("Unspecified PDx: Yes - A more specific code should be used when possible")
            text_result = "\n".join(lines)
            # A diagnosis fixes the clinical group but not the functional level,
            # admission source/timing or comorbidity adjustment, so show the
            # bounded range rather than inventing the missing dimensions.
            if area_code:
                rng = ReimbursementService().payment_range(
                    row.get('pdgm_clinical_group_code', ''), area_code
                )
                range_lines = format_payment_range_lines(rng)
                if range_lines:
                    text_result += "\n" + "\n".join(range_lines)
            follow_up = ai_followup_question(full_query)
            result = {'Text': text_result, 'FollowUp': follow_up}
        else:
            ai_func = lambda _: get_cached_ai_response(full_query)
            ai_response = ai_map_phrase_to_code_with_payment(ai_func, full_query)
            follow_up = ai_followup_question(full_query)
            result = {'AI': ai_response, 'FollowUp': follow_up}

    return render_template(
        'index.html',
        result=result,
        query=query,
        area_code=area_code,
        payment_areas=cms_data.list_areas(),
        lead_captured=session.get('lead_captured', False),
        lead_email=session.get('lead_email', ''),
    )

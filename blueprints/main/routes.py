from flask import request, redirect, url_for, flash, render_template, session, get_flashed_messages
# removed flask_login import
from . import bp

from app import (
    normalize_icd10, format_icd10, format_pdgm_group,
    icd10_data, excluded_codes,
    ai_map_phrase_to_code, ai_followup_question,
)
from services.reimbursement_service import (
    ReimbursementService,
    ai_map_phrase_to_code_with_payment,
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
    zip_code = ""
    visit_count_input = None

    if request.method == 'POST':
        query = request.form.get('query', '').strip()
        if not query:
            flash('Query field is required.')
            return redirect(url_for('main.index'))

        follow_answer = request.form.get("follow_answer", "").strip()
        full_query = f"{query} {follow_answer}" if follow_answer else query
        zip_code = request.form.get('zip_code', '').strip()
        visit_count_input = request.form.get('visit_count')
        try:
            visit_count_input = int(visit_count_input) if visit_count_input else None
        except ValueError:
            visit_count_input = None

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
            if zip_code or visit_count_input is not None:
                service = ReimbursementService()
                pay = service.calculate_payment(
                    row.get('pdgm_clinical_group_code', ''),
                    zip_code,
                    visit_count_input,
                )
                if pay.get('estimated_payment'):
                    pay_lines = [
                        "",
                        "ESTIMATED REIMBURSEMENT:",
                        f"Payment Amount: ${pay['estimated_payment']:,.2f}",
                        f"Base Rate: ${pay['base_rate']:,.2f}",
                        f"PDGM Multiplier: {pay['pdgm_multiplier']}",
                        f"Wage Index: {pay['wage_index']:.3f}",
                    ]
                    if pay['is_lupa']:
                        pay_lines.append(
                            f"LUPA Alert: Visit count ({visit_count_input}) below threshold ({pay['lupa_threshold']})"
                        )
                    pay_lines.append("")
                    pay_lines.append(pay['disclaimer'])
                    text_result += "\n" + "\n".join(pay_lines)
            follow_up = ai_followup_question(full_query)
            result = {'Text': text_result, 'FollowUp': follow_up}
        else:
            ai_func = lambda _: get_cached_ai_response(full_query)
            ai_response = ai_map_phrase_to_code_with_payment(
                ai_func, full_query, zip_code, visit_count_input
            )
            follow_up = ai_followup_question(full_query)
            result = {'AI': ai_response, 'FollowUp': follow_up}

    return render_template(
        'index.html',
        result=result,
        query=query,
        zip_code=zip_code,
        visit_count_value=visit_count_input,
        lead_captured=session.get('lead_captured', False),
        lead_email=session.get('lead_email', ''),
    )

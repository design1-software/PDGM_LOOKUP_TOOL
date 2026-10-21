"""Issue-specific review paths and neutral, incomplete clarification templates.

No patient record is accepted, stored, or inferred here. Staff complete the
template with relevant documentation and clinical indicators in their browser.
"""
from .eligibility import assess_primary_diagnosis
from .impl import format_icd10

DETAILS = {
    'type': 'type or subtype of the condition',
    'site': 'anatomical site',
    'laterality': 'laterality (right, left, or bilateral, as applicable)',
    'acuity': 'acuity or course of the condition',
    'severity': 'severity or stage, as applicable',
    'complications': 'presence or absence of associated complications',
    'condition_detail': 'additional condition-specific detail',
}
PLACEHOLDERS = [
    '[ADD CURRENT DOCUMENTATION WITH SOURCE AND DATE]',
    '[ADD RELEVANT CLINICAL INDICATORS WITH SOURCES AND DATES]',
]


class ClarificationError(ValueError):
    pass


def blocked_workflow(state, message):
    return {'state': state, 'can_prepare': False, 'message': message, 'issues': []}


def clarification_workflow(row):
    assessment = assess_primary_diagnosis(row)
    codes = {flag['code'] for flag in assessment['flags']}
    if 'CODE_NOT_FOUND' in codes:
        return blocked_workflow(
            'verify_code', 'Verify the exact code and Claim From date, then rerun the lookup. '
            'A provider request is not appropriate based only on an unresolved code.')
    issues = []
    if codes & {'MANIFESTATION', 'CODE_FIRST'}:
        issues.append({
            'code': 'sequencing', 'label': 'Underlying condition or relationship',
            'instruction_review_required': 'CODE_FIRST' in codes,
            'detail_required': False,
        })
    if 'UNSPECIFIED_PDX' in codes:
        issues.append({
            'code': 'specificity', 'label': 'Missing diagnosis detail',
            'instruction_review_required': False, 'detail_required': True,
        })
    # Prefer the specific sequencing/specificity issue over duplicating the
    # generic missing-group explanation in a second provider request.
    if not issues and codes & {'UNACCEPTABLE_PDX', 'NO_CLINICAL_GROUP', 'ECOI'}:
        issues.append({
            'code': 'primary_condition', 'label': 'Condition responsible for home health services',
            'instruction_review_required': False, 'detail_required': False,
        })
    if not issues:
        return blocked_workflow(
            'no_issue', 'No clarification issue was identified by these mapping checks.')
    return {
        'state': 'review_documentation', 'can_prepare': True, 'issues': issues,
        'message': 'Review the current record first. If the needed information is already '
                   'documented, resolve the coding issue from that record. Prepare a '
                   'clarification template only when information remains missing or unclear.',
        'detail_options': [{'code': code, 'label': label} for code, label in DETAILS.items()],
    }


def prepare_template(row, body):
    workflow = clarification_workflow(row)
    if not workflow['can_prepare']:
        raise ClarificationError(workflow['message'])
    issue = next((issue for issue in workflow['issues'] if issue['code'] == body.get('issue')), None)
    if issue is None:
        raise ClarificationError('Select an issue identified by the verified lookup.')
    if body.get('documentation_reviewed') is not True or body.get('clarification_needed') is not True:
        raise ClarificationError('Review the record and confirm that clarification is still needed.')
    if issue['instruction_review_required'] and body.get('instruction_reviewed') is not True:
        raise ClarificationError('Review the applicable Code first instruction and confirm that it applies.')
    if issue['code'] == 'specificity':
        detail = DETAILS.get(body.get('missing_detail'))
        if not detail:
            raise ClarificationError('Select the detail that remains missing or unclear in the record.')
        question = ('Based on the information above and your clinical assessment, please clarify the '
                    f'{detail} of the condition being addressed, to the extent it can be determined.')
    elif issue['code'] == 'sequencing':
        question = ('Based on the information above and your clinical assessment, please clarify '
                    'any underlying or causal condition and its relationship to the condition being '
                    'addressed, if clinically supported. If no underlying condition is identified, '
                    'please indicate that.')
    else:
        question = ('Based on the information above and your clinical assessment, please clarify '
                    'the condition chiefly responsible for the patient’s home health services.')
    code = format_icd10(row['icd10_code'])
    text = (
        'Please clarify the clinical documentation for the condition identified for review as:\n'
        f"{code} — {row.get('description', '')}\n\n"
        f'Current documentation and its source/date:\n{PLACEHOLDERS[0]}\n\n'
        f'Relevant clinical findings, treatment, or monitoring and their sources/dates:\n{PLACEHOLDERS[1]}\n\n'
        f'{question}\n\n'
        'Please document your assessment in the medical record. If the information cannot be '
        'determined or the request does not apply, please indicate that. Your response should '
        'reflect your independent clinical judgment.'
    )
    return {
        'subject': 'Documentation clarification request', 'body': text,
        'required_placeholders': PLACEHOLDERS.copy(),
        'completion_note': 'Add the relevant current documentation and clinical indicators with '
                           'their sources/dates, then review the complete request before using it.',
    }

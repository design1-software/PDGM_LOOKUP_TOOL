"""Shared primary-diagnosis checks against the loaded PDGM mapping.

Passing these checks is not a coverage or billability determination.
"""


# Explanations stay deterministic and tied to mapping evidence, not AI output.
_GUIDANCE = {
    'CODE_NOT_FOUND': (
        'No diagnosis code was verified in the loaded PDGM mapping. '
        'This alone does not establish that an entered code is invalid.',
        'Check the entry and the code set applicable to the service date. '
        'For a clinical phrase, identify the documented diagnosis and verify its code. '
        'Do not substitute an unconfirmed diagnosis or send a provider request based only on this result.',
    ),
    'UNACCEPTABLE_PDX': (
        'The loaded mapping marks this code as unacceptable in the primary diagnosis position.',
        'Review the documented reason for home health services and select an appropriate '
        'primary diagnosis supported by the record. Request provider clarification only '
        'if the documentation does not identify that condition.',
    ),
    'UNSPECIFIED_PDX': (
        'The loaded mapping identifies an unspecified diagnosis. This warning alone '
        'does not establish that a more specific diagnosis is documented.',
        'Check for documented details such as site, laterality, acuity, or complications. '
        'Use greater specificity only when supported; clarify missing details with the provider when needed.',
    ),
    'MANIFESTATION': (
        'This code describes a manifestation of another condition and cannot lead the diagnosis sequence.',
        'Review the applicable ICD-10-CM instruction and the documented underlying condition. '
        'Sequence that condition first when supported. Request clarification if the required '
        'condition or relationship is not documented; do not infer it.',
    ),
    'ECOI': (
        'This code describes an external cause or circumstance rather than the condition '
        'to use as the primary diagnosis.',
        'Identify the documented injury or condition chiefly responsible for home health '
        'services. Review the external-cause code for secondary reporting as applicable.',
    ),
    'CODE_FIRST': (
        'The mapping contains a code-first entry. The applicable instruction can depend '
        'on the documented circumstances; this entry alone does not prohibit primary use.',
        'Review the code and inherited notes in the ICD-10-CM Tabular List for the service date. '
        'If the instruction applies, sequence the documented underlying or causal condition first. '
        'Clarify missing documentation with the provider rather than assuming a diagnosis.',
    ),
    'NO_CLINICAL_GROUP': (
        'The loaded mapping has no usable PDGM clinical group for this code, so it cannot '
        'support a primary-diagnosis HIPPS calculation here. This does not establish that '
        'the ICD-10-CM code itself is invalid.',
        'Verify the code and mapping version for the service date. Review the documented '
        'reason for home health services and applicable sequencing instructions. If the '
        'record is insufficient, request clarification; do not choose a replacement solely for payment.',
    ),
}


def assess_primary_diagnosis(row):
    flags = []
    if not row:
        flags.append({
            'type': 'error', 'code': 'CODE_NOT_FOUND',
            'message': 'Diagnosis code not found in the loaded PDGM mapping',
        })
    else:
        rules = (
            ('UNACCEPTABLE_PDX', 'UNACCEPTABLE_PDX', 'error',
             'Unacceptable principal diagnosis — cannot be used as primary Dx'),
            ('UNSPECIFIED_PDX', 'UNSPECIFIED_PDX', 'warning',
             'Unspecified diagnosis — use a more specific code when possible'),
            ('MANIFESTATION_FLAG', 'MANIFESTATION', 'error',
             'Manifestation code — must be sequenced after the underlying condition'),
            ('ECOI_FLAG', 'ECOI', 'error',
             'External cause code — cannot be used as principal diagnosis'),
        )
        for field, code, severity, message in rules:
            if row.get(field) == '1':
                flags.append({'type': severity, 'code': code, 'message': message})

        code_first = str(row.get('CODE_FIRST') or '').strip()
        # CODE_FIRST is not Boolean: the mapping contains entries such as 10
        # and 110. We do not have the instruction text/clinical context needed
        # to turn an entry into an unconditional primary-diagnosis restriction.
        if code_first and code_first != '0':
            flags.append({
                'type': 'warning', 'code': 'CODE_FIRST',
                'message': 'Code-first sequencing needs review',
            })

        if row.get('pdgm_clinical_group_code') not in tuple('ABCDEFGHIJKL'):
            flags.append({
                'type': 'error', 'code': 'NO_CLINICAL_GROUP',
                'message': 'No PDGM clinical group for this code',
            })

    for flag in flags:
        flag['explanation'], flag['next_step'] = _GUIDANCE[flag['code']]

    blocking_codes = [flag['code'] for flag in flags if flag['type'] == 'error']
    return {
        'primary_eligibility': {
            'eligible': not blocking_codes,
            'blocking_codes': blocking_codes,
        },
        'flags': flags,
    }

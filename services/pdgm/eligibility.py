"""Shared primary-diagnosis checks against the loaded PDGM mapping.

Passing these checks is not a coverage or billability determination.
"""


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

        if row.get('pdgm_clinical_group_code') not in tuple('ABCDEFGHIJKL'):
            flags.append({
                'type': 'error', 'code': 'NO_CLINICAL_GROUP',
                'message': 'No PDGM clinical group for this code',
            })

    blocking_codes = [flag['code'] for flag in flags if flag['type'] == 'error']
    return {
        'primary_eligibility': {
            'eligible': not blocking_codes,
            'blocking_codes': blocking_codes,
        },
        'flags': flags,
    }

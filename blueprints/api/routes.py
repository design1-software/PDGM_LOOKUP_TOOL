from services.pdgm.datasets import diagnosis_metadata, DiagnosisDateError, DiagnosisDataError
from services.pdgm.clarification import clarification_workflow, blocked_workflow, prepare_template, ClarificationError
from flask import jsonify, current_app, request, session
from schemas.pdgm import (
    ValidationError, validate_lookup_request, validate_roadmap_request,
    validate_assessment_request, validate_hipps_request,
)
from app_core.extensions import limiter
from . import bp


def require_lead_capture(f):
    """Reject API calls when the lead gate hasn't been completed."""
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('lead_captured'):
            return jsonify({'error': 'Please provide your name and email to use this tool.'}), 403
        return f(*args, **kwargs)
    return decorated


@bp.get('/healthz')
def healthz():
    return jsonify(status='ok')


@bp.get('/version')
def version():
    env = current_app.config.get('ENVIRONMENT', 'development')
    return jsonify(environment=env, version='mvp')


@bp.post('/api/lookup')
@limiter.limit("30 per minute; 500 per hour")
@require_lead_capture
def api_lookup():
    """CSV-driven PDGM lookup for an ICD-10 code or phrase."""
    try:
        body = request.get_json(silent=True) or {}
        v = validate_lookup_request(body)
        query = v['query']
        zip_code = v.get('zip_code', '')
        area_code = v.get('area_code', '')
        # visit_count is still accepted by the schema but unused here: LUPA
        # status depends on the HIPPS group's threshold, which this route
        # cannot determine. POST /api/hipps handles that.

        from services.pdgm.rules_engine import lookup_pdgm
        payload = lookup_pdgm(query, v['service_date'])
        payload['diagnosis_data'] = diagnosis_metadata(v['service_date'])

        if payload.get('selection_required'):
            return jsonify(payload)

        from services.pdgm.eligibility import assess_primary_diagnosis
        assessment = assess_primary_diagnosis(payload.get('raw'))
        payload.update(assessment)
        payload['clarification_workflow'] = clarification_workflow(payload.get('raw'))

        # Payment range when an area is supplied. A diagnosis fixes the clinical
        # group but not the functional level, admission source/timing, or
        # comorbidity adjustment, so an exact payment isn't knowable here --
        # POST /api/hipps takes those inputs and returns a single figure.
        if not assessment['primary_eligibility']['eligible']:
            payload['payment_note'] = (
                'A payment estimate is not available for this primary diagnosis. '
                'Review the diagnosis alerts.'
            )
        elif area_code:
            from services.reimbursement_service import ReimbursementService
            group_code = (payload.get('raw') or {}).get('pdgm_clinical_group_code', '')
            if group_code:
                payload['payment_range'] = ReimbursementService().payment_range(
                    group_code, area_code
                )
        elif zip_code:
            payload['payment_note'] = (
                'area_code is required for a wage-adjusted estimate. CMS keys '
                'the HH PPS wage index on CBSA, not ZIP. See '
                'GET /api/wage-index-areas.'
            )

        return jsonify(payload)
    except (ValidationError, DiagnosisDateError) as ve:
        return jsonify(error=str(ve), clarification_workflow=blocked_workflow(
            'verify_input', 'Check the entry and Claim From date, then rerun the lookup.')), 400
    except Exception as e:
        current_app.logger.error(f'/api/lookup error: {e}')
        return jsonify(error='lookup failed', clarification_workflow=blocked_workflow(
            'technical_failure', 'Retry the lookup. If the problem continues, contact your '
            'application administrator. No provider clarification draft was prepared.')), 500


@bp.post('/api/provider-clarification')
@limiter.limit('10 per minute; 50 per hour')
@require_lead_capture
def api_provider_clarification():
    """Prepare a template from a freshly verified code/date, never patient text."""
    try:
        body = request.get_json(silent=True)
        allowed = {'icd10', 'service_date', 'issue', 'documentation_reviewed',
                   'clarification_needed', 'instruction_reviewed', 'missing_detail'}
        if not isinstance(body, dict) or set(body) - allowed:
            raise ClarificationError('Use only the code, date, issue, and review selections from the lookup.')
        if not isinstance(body.get('icd10'), str) or not 3 <= len(body['icd10']) <= 10:
            raise ClarificationError('A verified ICD-10 code is required.')
        if not body.get('service_date'):
            raise ClarificationError('Use the Claim From date from the verified lookup.')
        if body.get('missing_detail') is not None and not isinstance(body['missing_detail'], str):
            raise ClarificationError('Select a missing-detail option.')
        from services.pdgm.repository import get_icd10_map, normalize_icd10
        metadata = diagnosis_metadata(body['service_date'])
        row = get_icd10_map(metadata['service_date']).get(normalize_icd10(body['icd10']))
        workflow = clarification_workflow(row)
        if not workflow['can_prepare']:
            return jsonify(error=workflow['message'], clarification_workflow=workflow), 400
        draft = prepare_template(row, body)
        return jsonify(draft=draft, diagnosis_data=metadata, clarification_workflow=workflow)
    except (ClarificationError, DiagnosisDateError) as e:
        return jsonify(error=str(e)), 400
    except Exception:
        current_app.logger.error('/api/provider-clarification failed')
        return jsonify(error='Template preparation failed. Retry or contact your application administrator.',
                       clarification_workflow=blocked_workflow('technical_failure',
                       'No provider clarification draft was prepared.')), 500


@bp.post('/api/roadmap')
@limiter.limit("10 per minute; 50 per hour")
@require_lead_capture
def api_roadmap():
    try:
        body = request.get_json(silent=True) or {}
        v = validate_roadmap_request(body)
        from app import ai_documentation_roadmap
        result = ai_documentation_roadmap(v['diagnosis'], v['pdgm_group'], v['disciplines'])
        return jsonify({'roadmap': result})
    except (ValidationError, DiagnosisDateError) as ve:
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        current_app.logger.error(f'/api/roadmap error: {e}')
        return jsonify({'error': 'failed to generate roadmap'}), 500


@bp.post('/api/assessment')
@limiter.limit("10 per minute; 50 per hour")
@require_lead_capture
def api_assessment():
    try:
        body = request.get_json(silent=True) or {}
        v = validate_assessment_request(body)
        from app import ai_sample_oasis_assessment
        result = ai_sample_oasis_assessment(v['diagnosis'], v['pdgm_group'])
        return jsonify({'assessment': result})
    except (ValidationError, DiagnosisDateError) as ve:
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        current_app.logger.error(f'/api/assessment error: {e}')
        return jsonify({'error': 'failed to generate assessment'}), 500

@bp.post('/api/hipps')
@limiter.limit("30 per minute")
@require_lead_capture
def api_hipps():
    """Calculate HIPPS code from PDGM dimensions."""
    try:
        body = request.get_json(silent=True) or {}
        v = validate_hipps_request(body)

        from app import normalize_icd10
        from services.pdgm.comorbidity import determine_comorbidity_adjustment
        from services.pdgm.functional import calculate_functional_level
        from services.pdgm.hipps import generate_hipps_code, decode_hipps, calculate_payment

        from services.pdgm.repository import get_icd10_map
        from services.pdgm.eligibility import assess_primary_diagnosis

        # Use the same mapping and primary-diagnosis assessment as lookup.
        primary_norm = normalize_icd10(v['primary_icd10'])
        data = get_icd10_map(v['service_date'])
        metadata = diagnosis_metadata(v['service_date'])
        primary_row = data.get(primary_norm)
        assessment = assess_primary_diagnosis(primary_row)
        if not assessment['primary_eligibility']['eligible']:
            error = (f"ICD-10 code not found: {v['primary_icd10']}" if not primary_row
                     else '; '.join(flag['message'] for flag in assessment['flags']
                                    if flag['type'] == 'error'))
            return jsonify(error=error, diagnosis_data=metadata, **assessment), 400

        clinical_group = primary_row['pdgm_clinical_group_code']

        # Comorbidity adjustment
        primary_subgroup = primary_row.get('COMORBIDITY_GROUP', 'No_group')
        secondary_subgroups = []
        secondary_details = []
        for code_str in v['secondary_icd10s']:
            norm = normalize_icd10(code_str)
            row = data.get(norm)
            if not row:
                return jsonify(error=f"Secondary diagnosis not found for this claim From date: {code_str}",
                               diagnosis_data=metadata), 400
            if row:
                secondary_subgroups.append(row.get('COMORBIDITY_GROUP', 'No_group'))
                secondary_details.append({
                    'icd10': code_str,
                    'description': row.get('description', ''),
                    'comorbidity_group': row.get('COMORBIDITY_GROUP', 'No_group'),
                })

        comorbidity_adj = determine_comorbidity_adjustment(primary_subgroup, secondary_subgroups)

        # Functional level
        functional = calculate_functional_level(
            v['gg0130'], v['gg0170'], clinical_group
        )

        # Generate HIPPS code
        hipps_code = generate_hipps_code(
            clinical_group=clinical_group,
            admission_source=v['admission_source'],
            episode_timing=v['episode_timing'],
            functional_level=functional['level'],
            comorbidity_adjustment=comorbidity_adj,
        )

        # The HIPPS code and its dimensions never depend on geography, so they
        # are always returned. Payment does: CMS keys the wage index on CBSA
        # and publishes no ZIP-to-CBSA mapping, so without an area_code there
        # is no defensible payment figure.
        #
        # `payment` is either a complete payment object or null -- never a
        # half-populated error shape. Returning the error shape is what
        # crashed the client while it formatted fields that weren't there.
        breakdown = decode_hipps(hipps_code)
        payment = None
        payment_note = None
        if v['area_code']:
            calculated = calculate_payment(hipps_code, v['area_code'])
            if calculated.get('estimated_payment') is not None:
                payment = calculated
            else:
                problems = (calculated.get('invalid_inputs')
                            or calculated.get('missing_inputs') or ['unknown'])
                payment_note = ('Payment could not be calculated: %s'
                                % '; '.join(problems))
        elif v['zip_code']:
            payment_note = ('A site of service is required for a payment '
                            'estimate. CMS keys the wage index on CBSA, not '
                            'ZIP, so choose an area rather than entering a ZIP.')
        else:
            payment_note = ('Select a site of service to see the estimated '
                            'payment for this HIPPS code.')

        return jsonify({
            **assessment,
            'diagnosis_data': metadata,
            'hipps_code': hipps_code,
            'primary': {
                'icd10': v['primary_icd10'],
                'description': primary_row.get('description', ''),
                'clinical_group': clinical_group,
                'clinical_group_name': primary_row.get('pdgm_clinical_group_name', ''),
                'comorbidity_group': primary_subgroup,
            },
            'secondary_diagnoses': secondary_details,
            'dimensions': breakdown,
            'functional': functional,
            'comorbidity_adjustment': comorbidity_adj,
            'payment': payment,
            'payment_note': payment_note,
        })
    except (ValidationError, DiagnosisDateError) as ve:
        return jsonify({'error': str(ve)}), 400
    except ValueError as ve:
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        current_app.logger.error(f'/api/hipps error: {e}')
        return jsonify({'error': 'HIPPS calculation failed'}), 500


@bp.get('/api/case-mix-weights')
def api_case_mix_weights():
    """Expose all 432 CY 2026 CMS case-mix weights and LUPA thresholds.

    Keyed by real HIPPS code (e.g. 1KC11). Source: CY 2026 HH PPS final rule,
    see data/cms/cy2026/SOURCES.md.
    """
    from services import cms_data
    from services.reimbursement_service import (
        NATIONAL_30_DAY_RATE, NATIONAL_30_DAY_RATE_NO_QUALITY, PAYMENT_YEAR,
    )
    table = cms_data.load_case_mix_table()
    return jsonify(
        weights={cell['hipps']: cell['weight'] for cell in table.values()},
        lupa_thresholds={cell['hipps']: cell['lupa_threshold'] for cell in table.values()},
        national_rate=NATIONAL_30_DAY_RATE,
        national_rate_no_quality_data=NATIONAL_30_DAY_RATE_NO_QUALITY,
        payment_year=PAYMENT_YEAR,
    )


@bp.get('/api/wage-index-areas')
def api_wage_index_areas():
    """List the CY 2026 CMS wage index areas accepted as area_code."""
    from services import cms_data
    return jsonify(areas=[
        {
            'code': area['code'],
            'name': area['name'],
            'wage_index': area['wage_index'],
            'kind': area['kind'],
            'states': area['states'],
        }
        for area in cms_data.list_areas()
    ])


@bp.post('/api/comorbidity-check')
def api_comorbidity_check():
    """Live comorbidity adjustment check without full HIPPS calculation."""
    try:
        body = request.get_json(silent=True) or {}
        primary_code = body.get('primary_icd10', '')
        secondary_codes = body.get('secondary_icd10s', [])
        from app import normalize_icd10
        from services.pdgm.comorbidity import determine_comorbidity_adjustment
        from services.pdgm.repository import get_icd10_map
        service_date = body.get('service_date')
        metadata = diagnosis_metadata(service_date)
        service_date = metadata['service_date']
        data = get_icd10_map(service_date)
        primary_row = data.get(normalize_icd10(primary_code), {})
        if not primary_row:
            return jsonify(error='Primary diagnosis not found for this claim From date'), 400
        primary_sg = primary_row.get('COMORBIDITY_GROUP', 'No_group')
        secondary_sgs = []
        for c in secondary_codes:
            row = data.get(normalize_icd10(c), {})
            if not row:
                return jsonify(error=f'Secondary diagnosis not found for this claim From date: {c}'), 400
            secondary_sgs.append(row.get('COMORBIDITY_GROUP', 'No_group'))
        adj = determine_comorbidity_adjustment(primary_sg, secondary_sgs)
        return jsonify(adjustment=adj, primary_subgroup=primary_sg, secondary_subgroups=secondary_sgs, diagnosis_data=metadata)
    except DiagnosisDateError as e:
        return jsonify(error=str(e)), 400
    except DiagnosisDataError:
        return jsonify(error='Diagnosis data verification failed'), 500
    except Exception as e:
        return jsonify(adjustment='None', error=str(e))


@bp.post('/api/compare')
@limiter.limit("30 per minute")
@require_lead_capture
def api_compare():
    """Side-by-side diagnosis comparison."""
    try:
        body = request.get_json(silent=True) or {}
        service_date = body.get('service_date')
        metadata = diagnosis_metadata(service_date)
        service_date = metadata['service_date']
        code_a = body.get('code_a', '')
        code_b = body.get('code_b', '')
        from app import normalize_icd10
        from services import cms_data
        from services.reimbursement_service import NATIONAL_30_DAY_RATE

        area_code = (body.get('area_code') or '').strip()
        table = cms_data.load_case_mix_table()

        def build_info(code_str):
            from services.pdgm.rules_engine import explain_pdgm_for_icd10
            info = explain_pdgm_for_icd10(normalize_icd10(code_str), service_date)
            raw = info.get('raw') or {}
            cg = raw.get('pdgm_clinical_group_code', '')
            if not cg:
                info['payment_range'] = None
                return info
            if area_code:
                # Wage-adjusted range for a specific area.
                from services.reimbursement_service import ReimbursementService
                rng = ReimbursementService().payment_range(cg, area_code)
                info['payment_range'] = None if rng.get('error') else {
                    'min': rng['min_payment'],
                    'max': rng['max_payment'],
                    'area_name': rng['area_name'],
                    'wage_index': rng['wage_index'],
                }
                return info
            # No area given: unadjusted national range, clearly labelled.
            weights = [c['weight'] for k, c in table.items() if k[0] == cg]
            info['payment_range'] = {
                'min': round(min(weights) * NATIONAL_30_DAY_RATE, 2),
                'max': round(max(weights) * NATIONAL_30_DAY_RATE, 2),
                'wage_adjusted': False,
                'note': 'National rates, not wage-adjusted. Pass area_code for '
                        'a geography-specific range.',
            } if weights else None
            return info

        return jsonify(a=build_info(code_a), b=build_info(code_b), diagnosis_data=metadata)
    except DiagnosisDateError as e:
        return jsonify(error=str(e)), 400
    except Exception as e:
        current_app.logger.error(f'/api/compare error: {e}')
        return jsonify({'error': 'comparison failed'}), 500


@bp.get('/api/offline-data')
@limiter.limit("10 per minute")
@require_lead_capture
def api_offline_data():
    """Compact ICD-10 map for offline PWA lookups."""
    from services.pdgm.repository import get_icd10_map
    try:
        service_date = request.args.get('service_date')
        metadata = diagnosis_metadata(service_date)
        service_date = metadata['service_date']
        data = get_icd10_map(service_date)
    except DiagnosisDateError as e:
        return jsonify(error=str(e)), 400
    compact = {}
    for code, row in data.items():
        compact[code] = {
            'd': row.get('description', ''),
            'g': row.get('pdgm_clinical_group_code', ''),
            'gn': row.get('pdgm_clinical_group_name', ''),
            'cg': row.get('COMORBIDITY_GROUP', ''),
        }
    return jsonify(data=compact, diagnosis_data=metadata)


@bp.get('/api/suggest')
def api_suggest():
    try:
        q = request.args.get('q', '').strip()
        if not q or len(q) < 2:
            return jsonify({'success': True, 'suggestions': []})
        if len(q) > 500:
            return jsonify(error='Search must be 500 characters or fewer.'), 400
        from app import search_icd10_codes
        service_date = request.args.get('service_date')
        metadata = diagnosis_metadata(service_date)
        service_date = metadata['service_date']
        results = search_icd10_codes(q, service_date=service_date)
        return jsonify({'success': True, 'suggestions': results,
                        'diagnosis_data': metadata})
    except DiagnosisDateError as e:
        return jsonify(error=str(e)), 400
    except Exception as e:
        current_app.logger.error(f'/api/suggest error: {e}')
        return jsonify({'error': 'failed to load suggestions'}), 500

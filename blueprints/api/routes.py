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
        visit_count = v.get('visit_count')

        from services.pdgm.rules_engine import lookup_pdgm
        payload = lookup_pdgm(query)

        # Red flag alerts from CSV data
        raw = payload.get('raw') or {}
        flags = []
        if raw.get('UNACCEPTABLE_PDX') == '1':
            flags.append({'type': 'error', 'code': 'UNACCEPTABLE_PDX',
                          'message': 'Unacceptable principal diagnosis — cannot be used as primary Dx'})
        if raw.get('UNSPECIFIED_PDX') == '1':
            flags.append({'type': 'warning', 'code': 'UNSPECIFIED_PDX',
                          'message': 'Unspecified diagnosis — use a more specific code when possible'})
        if raw.get('MANIFESTATION_FLAG') == '1':
            flags.append({'type': 'warning', 'code': 'MANIFESTATION',
                          'message': 'Manifestation code — must be sequenced after the underlying condition'})
        if raw.get('ECOI_FLAG') == '1':
            flags.append({'type': 'warning', 'code': 'ECOI',
                          'message': 'External cause code — cannot be used as principal diagnosis'})
        if raw.get('PRIMARY_AWARDING_FLAG') == '0' and raw.get('pdgm_clinical_group_code'):
            flags.append({'type': 'info', 'code': 'NO_PRIMARY_AWARD',
                          'message': 'This code does not qualify for primary awarding'})
        if flags:
            payload['flags'] = flags

        # Append payment estimate if zip_code or visit_count provided
        if zip_code or visit_count is not None:
            from services.reimbursement_service import ReimbursementService, extract_pdgm_code_from_response
            pdgm_code = (payload.get('raw') or {}).get('pdgm_clinical_group_code', '')
            if not pdgm_code:
                pdgm_code = (payload.get('raw') or {}).get('pdgm_clinical_group_name', '')
            if pdgm_code:
                service = ReimbursementService()
                payment = service.calculate_payment(pdgm_code, zip_code, visit_count)
                payload['payment'] = payment

        return jsonify(payload)
    except ValidationError as ve:
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        current_app.logger.error(f'/api/lookup error: {e}')
        return jsonify({'error': 'lookup failed'}), 500


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
    except ValidationError as ve:
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
    except ValidationError as ve:
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

        from app import normalize_icd10, icd10_data
        from services.pdgm.comorbidity import determine_comorbidity_adjustment
        from services.pdgm.functional import calculate_functional_level
        from services.pdgm.hipps import generate_hipps_code, decode_hipps, calculate_payment

        # Look up primary diagnosis
        primary_norm = normalize_icd10(v['primary_icd10'])
        primary_row = icd10_data.get(primary_norm)
        if not primary_row:
            return jsonify({'error': f"ICD-10 code not found: {v['primary_icd10']}"}), 400

        clinical_group = primary_row.get('pdgm_clinical_group_code', '')
        if not clinical_group or clinical_group == 'NA':
            return jsonify({'error': 'No PDGM clinical group for this code'}), 400

        # Comorbidity adjustment
        primary_subgroup = primary_row.get('COMORBIDITY_GROUP', 'No_group')
        secondary_subgroups = []
        secondary_details = []
        for code_str in v['secondary_icd10s']:
            norm = normalize_icd10(code_str)
            row = icd10_data.get(norm)
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

        # Decode and calculate payment
        breakdown = decode_hipps(hipps_code)
        payment = calculate_payment(hipps_code, v['zip_code'])

        return jsonify({
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
        })
    except ValidationError as ve:
        return jsonify({'error': str(ve)}), 400
    except ValueError as ve:
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        current_app.logger.error(f'/api/hipps error: {e}')
        return jsonify({'error': 'HIPPS calculation failed'}), 500


@bp.get('/api/case-mix-weights')
def api_case_mix_weights():
    """Expose all HIPPS case-mix weights for client-side impact calculations."""
    from services.pdgm.hipps import CASE_MIX_WEIGHTS, NATIONAL_30DAY_RATE
    return jsonify(weights=CASE_MIX_WEIGHTS, national_rate=NATIONAL_30DAY_RATE)


@bp.post('/api/comorbidity-check')
def api_comorbidity_check():
    """Live comorbidity adjustment check without full HIPPS calculation."""
    try:
        body = request.get_json(silent=True) or {}
        primary_code = body.get('primary_icd10', '')
        secondary_codes = body.get('secondary_icd10s', [])
        from app import normalize_icd10, icd10_data
        from services.pdgm.comorbidity import determine_comorbidity_adjustment
        primary_row = icd10_data.get(normalize_icd10(primary_code), {})
        primary_sg = primary_row.get('COMORBIDITY_GROUP', 'No_group')
        secondary_sgs = []
        for c in secondary_codes:
            row = icd10_data.get(normalize_icd10(c), {})
            secondary_sgs.append(row.get('COMORBIDITY_GROUP', 'No_group'))
        adj = determine_comorbidity_adjustment(primary_sg, secondary_sgs)
        return jsonify(adjustment=adj, primary_subgroup=primary_sg, secondary_subgroups=secondary_sgs)
    except Exception as e:
        return jsonify(adjustment='None', error=str(e))


@bp.post('/api/compare')
@limiter.limit("30 per minute")
@require_lead_capture
def api_compare():
    """Side-by-side diagnosis comparison."""
    try:
        body = request.get_json(silent=True) or {}
        code_a = body.get('code_a', '')
        code_b = body.get('code_b', '')
        from app import normalize_icd10, icd10_data
        from services.pdgm.hipps import CASE_MIX_WEIGHTS, NATIONAL_30DAY_RATE

        def build_info(code_str):
            from services.pdgm.rules_engine import explain_pdgm_for_icd10
            info = explain_pdgm_for_icd10(normalize_icd10(code_str))
            raw = info.get('raw') or {}
            cg = raw.get('pdgm_clinical_group_code', '')
            weights = [CASE_MIX_WEIGHTS[k] for k in CASE_MIX_WEIGHTS if k.startswith(cg)] if cg else []
            info['payment_range'] = {
                'min': round(min(weights) * NATIONAL_30DAY_RATE, 2),
                'max': round(max(weights) * NATIONAL_30DAY_RATE, 2),
            } if weights else None
            return info

        return jsonify(a=build_info(code_a), b=build_info(code_b))
    except Exception as e:
        current_app.logger.error(f'/api/compare error: {e}')
        return jsonify({'error': 'comparison failed'}), 500


@bp.get('/api/offline-data')
@limiter.limit("10 per minute")
@require_lead_capture
def api_offline_data():
    """Compact ICD-10 map for offline PWA lookups."""
    from app import icd10_data
    compact = {}
    for code, row in icd10_data.items():
        compact[code] = {
            'd': row.get('description', ''),
            'g': row.get('pdgm_clinical_group_code', ''),
            'gn': row.get('pdgm_clinical_group_name', ''),
            'cg': row.get('COMORBIDITY_GROUP', ''),
        }
    return jsonify(data=compact)


@bp.get('/api/suggest')
def api_suggest():
    try:
        q = request.args.get('q', '').strip()
        if not q or len(q) < 3:
            return jsonify({'success': True, 'suggestions': []})
        from app import search_icd10_codes
        results = search_icd10_codes(q)
        return jsonify({'success': True, 'suggestions': results})
    except Exception as e:
        current_app.logger.error(f'/api/suggest error: {e}')
        return jsonify({'error': 'failed to load suggestions'}), 500

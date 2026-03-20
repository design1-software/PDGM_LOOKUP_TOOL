from flask import jsonify, current_app, request
from schemas.pdgm import (
    ValidationError, validate_lookup_request, validate_roadmap_request,
    validate_assessment_request, validate_hipps_request,
)
from . import bp


@bp.get('/healthz')
def healthz():
    return jsonify(status='ok')


@bp.get('/version')
def version():
    env = current_app.config.get('ENVIRONMENT', 'development')
    return jsonify(environment=env, version='mvp')


@bp.post('/api/lookup')
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

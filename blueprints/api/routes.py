from flask import jsonify, current_app, request
from schemas.pdgm import ValidationError, validate_lookup_request, validate_roadmap_request, validate_assessment_request
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

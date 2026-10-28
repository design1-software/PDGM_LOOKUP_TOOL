from flask import jsonify, render_template, request

from app_core.extensions import limiter
from services.pdgm import referral_readiness
from . import bp


def _options():
    return {
        'events': referral_readiness.EVENTS,
        'practitioners': referral_readiness.PRACTITIONERS,
        'dx_locations': referral_readiness.DX_LOCATIONS,
        'homebound_c1': referral_readiness.HOMEBOUND_C1,
        'homebound_c2': referral_readiness.HOMEBOUND_C2,
        'services': referral_readiness.SERVICES,
    }


# Not behind the lead-capture gate: the tool is in testing and is meant to be
# usable by reps without an account. Nothing submitted here is stored.
@bp.route('/referral-check', methods=['GET', 'POST'])
@limiter.limit("60 per minute")
def check():
    result = None
    if request.method == 'POST':
        result = referral_readiness.evaluate(request.form)
    return render_template(
        'referral_check.html',
        result=result,
        form=request.form,
        options=_options(),
        phi_notice=referral_readiness.PHI_NOTICE,
    )


@bp.post('/api/referral-check')
@limiter.limit("60 per minute")
def check_api():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(error='JSON body required'), 400
    return jsonify(referral_readiness.evaluate(data))

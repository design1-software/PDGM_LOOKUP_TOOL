from flask import Blueprint, request, jsonify, session
from models.user import db, User

auth_bp = Blueprint("auth", __name__, url_prefix="/api")

@auth_bp.route('/capture-lead', methods=['POST'])
def capture_lead():
    data = request.json or {}
    name = data.get('name', '').strip()
    email = data.get('email', '').strip()

    if not email:
        return jsonify({'success': False, 'error': 'Email is required.'}), 400

    user = User.query.filter_by(email=email).first()
    if not user:
        user = User(name=name, email=email)
        db.session.add(user)
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': 'Database error.'}), 500
    else:
        # Update name if provided and missing
        if name and not user.name:
            user.name = name
            db.session.commit()

    session['lead_captured'] = True
    session['lead_email'] = user.email
    
    return jsonify({'success': True, 'message': 'Lead captured.'})


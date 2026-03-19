from flask import request, render_template, redirect, url_for, flash, Response, session
from datetime import datetime, timedelta
from . import bp


@bp.route('/recert', methods=['GET', 'POST'])
def recert():
    result = None
    soc_date_input = ''
    episode_length_input = 60
    if request.method == 'POST':
        soc_date_input = request.form.get('soc_date', '')
        episode_length_input = int(request.form.get('episode_length', 60))
        try:
            start = datetime.strptime(soc_date_input, '%Y-%m-%d').date()
            due_date = start + timedelta(days=episode_length_input)
            result = due_date.strftime('%B %d, %Y')
        except ValueError:
            flash('Invalid date.')
    return render_template('recert.html',
                             result=result,
                             soc_date_input=soc_date_input,
                             episode_length_input=episode_length_input,
                             lead_captured=session.get('lead_captured', False),
                             lead_email=session.get('lead_email', ''))


@bp.route('/recert/ics')
def recert_ics():
    soc = request.args.get('soc')
    length = int(request.args.get('length', 60))
    try:
        start = datetime.strptime(soc, '%Y-%m-%d').date()
        due_date = start + timedelta(days=length)
    except (TypeError, ValueError):
        return "Invalid date", 400
    date_str = due_date.strftime('%Y%m%d')
    ics = "\n".join([
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//ReferralMate//Recert//EN",
        "BEGIN:VEVENT",
        f"DTSTART;VALUE=DATE:{date_str}",
        f"DTEND;VALUE=DATE:{date_str}",
        "SUMMARY:Recert Due",
        "DESCRIPTION:Recertification due",
        "END:VEVENT",
        "END:VCALENDAR",
    ])
    headers = {"Content-Disposition": "attachment; filename=recert.ics"}
    return Response(ics, mimetype='text/calendar', headers=headers)


@bp.route('/recert/email', methods=['POST'])
def recert_email():
    soc = request.form.get('soc_date', '')
    length = int(request.form.get('episode_length', 60))
    recipient = request.form.get('email', '')
    try:
        start = datetime.strptime(soc, '%Y-%m-%d').date()
        due_date = start + timedelta(days=length)
    except ValueError:
        flash('Invalid date.')
        return redirect(url_for('recert.recert'))
    body = f"Recertification is due on {due_date.strftime('%B %d, %Y')}"
    try:
        from flask_mail import Message
        from flask import current_app
        from app_core.extensions import mail
        msg = Message('Recert Reminder', recipients=[recipient], body=body)
        mail.send(msg)
        flash('Reminder sent.')
    except Exception:
        flash('Could not send email.')
    return redirect(url_for('recert.recert'))

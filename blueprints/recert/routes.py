from flask import request, render_template, redirect, url_for, flash, Response, session, make_response
from datetime import datetime, timedelta
from . import bp


def _calculate_recert(soc_str, episode_length):
    """Parse SOC date and return (start_date, due_date) or raise ValueError."""
    start = datetime.strptime(soc_str, '%Y-%m-%d').date()
    due = start + timedelta(days=episode_length)
    return start, due


def _days_until(due_date):
    """Return days from today until due_date."""
    return (due_date - datetime.now().date()).days


@bp.route('/recert', methods=['GET', 'POST'])
def recert():
    due = None
    soc = ''
    length = 60
    days_remaining = None
    if request.method == 'POST':
        soc = request.form.get('soc_date', '')
        length = int(request.form.get('episode_length', 60))
        try:
            start, due_date = _calculate_recert(soc, length)
            due = due_date.strftime('%B %d, %Y')
            days_remaining = _days_until(due_date)
        except ValueError:
            flash('Invalid date.')
    return render_template('recert.html',
                           due=due,
                           soc=soc,
                           length=length,
                           days_remaining=days_remaining,
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


@bp.route('/recert/download')
def recert_download():
    """Generate a downloadable recert summary PDF-style HTML for clinicians."""
    soc = request.args.get('soc', '')
    length = int(request.args.get('length', 60))
    try:
        start, due_date = _calculate_recert(soc, length)
    except (TypeError, ValueError):
        return "Invalid date", 400
    days_remaining = _days_until(due_date)
    risk = "HIGH" if days_remaining <= 7 else "MODERATE" if days_remaining <= 14 else "LOW"
    risk_color = "#dc2626" if risk == "HIGH" else "#f59e0b" if risk == "MODERATE" else "#10b981"
    generated = datetime.now().strftime('%B %d, %Y at %I:%M %p')

    html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<title>Recertification Risk Summary</title>
<style>
    body {{ font-family: Arial, Helvetica, sans-serif; max-width: 700px; margin: 2rem auto; padding: 0 1rem; color: #1e293b; }}
    .header {{ text-align: center; border-bottom: 3px solid #2563eb; padding-bottom: 1rem; margin-bottom: 2rem; }}
    .header h1 {{ color: #1e293b; font-size: 1.5rem; margin: 0; }}
    .header p {{ color: #64748b; font-size: 0.9rem; margin: 0.25rem 0 0; }}
    .risk-badge {{ display: inline-block; background: {risk_color}; color: white; padding: 0.5rem 1.5rem; border-radius: 0.5rem; font-weight: 700; font-size: 1.25rem; margin: 1rem 0; }}
    table {{ width: 100%; border-collapse: collapse; margin: 1.5rem 0; }}
    th, td {{ padding: 0.75rem 1rem; text-align: left; border-bottom: 1px solid #e2e8f0; }}
    th {{ background: #f8fafc; font-weight: 600; color: #374151; width: 40%; }}
    .warning {{ background: #fef2f2; border: 1px solid #fca5a5; border-radius: 0.5rem; padding: 1rem; margin: 1.5rem 0; }}
    .warning strong {{ color: #dc2626; }}
    .actions {{ background: #f0f9ff; border: 1px solid #93c5fd; border-radius: 0.5rem; padding: 1rem 1.5rem; margin: 1.5rem 0; }}
    .actions h3 {{ margin: 0 0 0.75rem; color: #1e40af; font-size: 1rem; }}
    .actions ul {{ margin: 0; padding-left: 1.5rem; }}
    .actions li {{ margin-bottom: 0.5rem; color: #334155; }}
    .footer {{ text-align: center; color: #94a3b8; font-size: 0.8rem; margin-top: 2rem; padding-top: 1rem; border-top: 1px solid #e2e8f0; }}
    @media print {{ body {{ margin: 0; }} }}
</style></head><body>
<div class="header">
    <h1>Recertification Risk Summary</h1>
    <p>ReferralMate &bull; ClearChoiceFTF &bull; Generated {generated}</p>
</div>

<div style="text-align: center;">
    <div class="risk-badge">RISK LEVEL: {risk}</div>
</div>

<table>
    <tr><th>Start of Care (SOC)</th><td>{start.strftime('%B %d, %Y')}</td></tr>
    <tr><th>Episode Length</th><td>{length} days</td></tr>
    <tr><th>Recertification Due</th><td><strong>{due_date.strftime('%B %d, %Y')}</strong></td></tr>
    <tr><th>Days Remaining</th><td><strong>{days_remaining} days</strong></td></tr>
</table>

<div class="warning">
    <strong>If recertification is missed:</strong> The patient must be discharged and re-admitted,
    triggering a billing reset and potential gap in care. Timely physician orders and
    face-to-face encounter documentation are required.
</div>

<div class="actions">
    <h3>Clinician Action Items</h3>
    <ul>
        <li>Schedule physician face-to-face encounter before <strong>{due_date.strftime('%B %d, %Y')}</strong></li>
        <li>Prepare updated Plan of Care with current goals and interventions</li>
        <li>Document continued skilled need and homebound status</li>
        <li>Obtain signed recertification order from physician</li>
        <li>Submit OASIS recertification assessment (RFA 4)</li>
    </ul>
</div>

<div class="footer">
    <p>This document is for informational purposes only and does not constitute clinical or billing advice.</p>
    <p>Powered by ReferralMate | ClearChoiceFTF</p>
</div>
</body></html>"""

    response = make_response(html)
    response.headers['Content-Type'] = 'text/html; charset=utf-8'
    response.headers['Content-Disposition'] = f'attachment; filename=recert_summary_{due_date.strftime("%Y%m%d")}.html'
    return response


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

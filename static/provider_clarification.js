/* Issue-specific templates; patient documentation is edited locally only. */
(function () {
    'use strict';
    function element(tag, className, text) {
        const node = document.createElement(tag);
        if (className) node.className = className;
        if (text) node.textContent = text;
        return node;
    }
    function checkbox(parent, label, id) {
        const row = element('label', 'clarification-check');
        const input = element('input');
        input.type = 'checkbox';
        input.id = id;
        row.appendChild(input);
        row.appendChild(element('span', '', label));
        parent.appendChild(row);
        return input;
    }
    function select(parent, label, id, options) {
        const group = element('div', 'form-group');
        const caption = element('label', 'form-label', label);
        caption.htmlFor = id;
        const input = element('select', 'form-input');
        input.id = id;
        [{ code: '', label: 'Select an option' }, ...options].forEach(option => {
            const node = element('option', '', option.label);
            node.value = option.code;
            input.appendChild(node);
        });
        group.appendChild(caption);
        group.appendChild(input);
        parent.appendChild(group);
        return { group, input };
    }

    window.clearProviderClarification = function () {
        document.getElementById('provider-clarification')?.remove();
    };

    window.renderProviderClarification = function (data) {
        window.clearProviderClarification();
        const workflow = data.clarification_workflow;
        if (!workflow || workflow.state === 'no_issue') return;
        const host = document.getElementById('response-content');
        if (!host) return;
        const panel = element('section', 'consolidated-results-card provider-workflow');
        panel.id = 'provider-clarification';
        panel.appendChild(element('h4', 'section-title', 'Documentation review'));
        panel.appendChild(element('p', 'clarification-help', workflow.message));
        host.appendChild(panel);
        if (!workflow.can_prepare) return;

        const issue = select(panel, 'What needs clarification?', 'clarification-issue', workflow.issues);
        if (workflow.issues.length === 1) issue.input.value = workflow.issues[0].code;
        const detail = select(panel, 'Which detail is still missing or unclear?',
            'clarification-detail', workflow.detail_options || []);
        const reviewed = checkbox(panel,
            'I verified this code against the referral/current record and reviewed the available documentation.',
            'clarification-reviewed');
        const needed = checkbox(panel, 'The needed information remains missing or unclear after review.',
            'clarification-needed');
        const instructionGroup = element('div');
        panel.appendChild(instructionGroup);
        const instruction = checkbox(instructionGroup,
            'I reviewed the applicable Code first instruction and confirmed that it applies to this case.',
            'clarification-instruction');
        const prepare = element('button', 'btn-export', 'Prepare clarification template');
        prepare.type = 'button';
        prepare.id = 'clarification-prepare';
        panel.appendChild(prepare);
        const status = element('p', 'clarification-help');
        status.setAttribute('role', 'status');
        status.setAttribute('aria-live', 'polite');
        panel.appendChild(status);
        const draftArea = element('div', 'clarification-draft');
        draftArea.hidden = true;
        panel.appendChild(draftArea);
        let revision = 0;
        let busy = false;
        let packet = null;
        let editor = null;
        let finalReview = null;
        let copy = null;
        let print = null;

        function selectedIssue() {
            return workflow.issues.find(item => item.code === issue.input.value);
        }
        function canPrepare() {
            const selected = selectedIssue();
            return window.currentResults === data && selected && reviewed.checked && needed.checked
                && (!selected.detail_required || !!detail.input.value)
                && (!selected.instruction_review_required || instruction.checked);
        }
        function sync() {
            const selected = selectedIssue();
            detail.group.hidden = !selected?.detail_required;
            instructionGroup.hidden = !selected?.instruction_review_required;
            prepare.disabled = busy || !canPrepare();
        }
        function canUseDraft() {
            return window.currentResults === data && packet && editor.value.trim()
                && finalReview.checked
                && !packet.required_placeholders.some(marker => editor.value.includes(marker));
        }
        function syncDraftActions() {
            copy.disabled = print.disabled = !canUseDraft();
        }
        [issue.input, detail.input, reviewed, needed, instruction].forEach(control => {
            control.addEventListener('change', () => {
                revision++;
                packet = null;
                draftArea.replaceChildren();
                draftArea.hidden = true;
                status.textContent = '';
                sync();
            });
        });

        prepare.addEventListener('click', async () => {
            if (!canPrepare()) return;
            const requestRevision = revision;
            busy = true;
            packet = null;
            draftArea.replaceChildren();
            draftArea.hidden = true;
            status.textContent = 'Preparing template…';
            sync();
            try {
                const response = await fetch('/api/provider-clarification', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        icd10: data.icd10, service_date: data.diagnosis_data?.service_date,
                        issue: issue.input.value, missing_detail: detail.input.value || null,
                        documentation_reviewed: reviewed.checked, clarification_needed: needed.checked,
                        instruction_reviewed: instruction.checked,
                    }),
                });
                const result = await response.json();
                if (window.currentResults !== data || revision !== requestRevision) return;
                if (!response.ok || !result.draft) {
                    status.textContent = result.error || 'Template unavailable. Retry or contact your application administrator.';
                    return;
                }
                packet = result.draft;
                draftArea.hidden = false;
                draftArea.appendChild(element('h4', 'section-title', 'Complete and review the draft'));
                draftArea.appendChild(element('p', 'clarification-help', packet.completion_note));
                draftArea.appendChild(element('p', 'clarification-help',
                    'Edits stay in this browser and are not saved by this feature. Add patient identifiers in your approved communication system.'));
                draftArea.appendChild(element('p', '', 'Subject: ' + packet.subject));
                const label = element('label', 'form-label', 'Editable clarification draft');
                label.htmlFor = 'clarification-editor';
                draftArea.appendChild(label);
                editor = element('textarea', 'form-input clarification-editor');
                editor.id = 'clarification-editor';
                editor.value = packet.body;
                editor.rows = 16;
                draftArea.appendChild(editor);
                finalReview = checkbox(draftArea,
                    'I added relevant documentation and clinical indicators with sources/dates and reviewed the complete wording.',
                    'clarification-final-review');
                const actions = element('div', 'clarification-actions');
                copy = element('button', 'btn-export', 'Copy request');
                copy.id = 'clarification-copy';
                copy.type = 'button';
                print = element('button', 'btn-export', 'Print request');
                print.id = 'clarification-print';
                print.type = 'button';
                actions.appendChild(copy);
                actions.appendChild(print);
                draftArea.appendChild(actions);
                editor.addEventListener('input', () => {
                    finalReview.checked = false;
                    syncDraftActions();
                });
                finalReview.addEventListener('change', syncDraftActions);
                copy.addEventListener('click', async () => {
                    if (!canUseDraft()) return;
                    try {
                        await navigator.clipboard.writeText('Subject: ' + packet.subject + '\n\n' + editor.value);
                        status.textContent = 'Request copied. Send through your approved communication system.';
                    } catch (_) {
                        status.textContent = 'Copy failed. Select the draft text and copy manually.';
                    }
                });
                print.addEventListener('click', () => {
                    if (!canUseDraft()) return;
                    const page = window.open('', '', 'width=800,height=650');
                    if (!page) { status.textContent = 'Allow pop-ups to print this request.'; return; }
                    page.document.title = 'Documentation clarification request';
                    const text = page.document.createElement('pre');
                    text.textContent = 'Subject: ' + packet.subject + '\n\n' + editor.value;
                    text.style.whiteSpace = 'pre-wrap';
                    text.style.fontFamily = 'Arial, sans-serif';
                    page.document.body.appendChild(text);
                    page.focus();
                    page.print();
                });
                syncDraftActions();
                status.textContent = 'Template prepared. Complete the marked sections and review before copying or printing.';
            } catch (_) {
                if (window.currentResults === data && revision === requestRevision) {
                    status.textContent = 'Template preparation failed. Retry or contact your application administrator. No request was prepared.';
                }
            } finally {
                busy = false;
                sync();
            }
        });
        sync();
    };
})();

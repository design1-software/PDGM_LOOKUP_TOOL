/* Potential matches require a deliberate choice before diagnosis analysis. */
(() => {
    let currentChoices = null;
    window.clearDiagnosisChoices = function () {
        currentChoices = null;
        document.getElementById('diagnosis-choices')?.remove();
    };
    window.renderDiagnosisChoices = function (result) {
        window.clearDiagnosisChoices();
        currentChoices = result;
        const form = document.getElementById('pdgm-form');
        const panel = document.createElement('section');
        panel.id = 'diagnosis-choices';
        panel.className = 'query-results';
        panel.setAttribute('aria-label', 'Choose a potential diagnosis match');
        const heading = document.createElement('h3');
        heading.textContent = result.candidates.length ? 'Choose a potential match' : 'No matching descriptions found';
        heading.tabIndex = -1;
        panel.appendChild(heading);
        const note = document.createElement('p');
        note.textContent = result.candidates.length
            ? 'Search matches are possibilities, not a confirmed diagnosis. Choose only a code supported by the documentation. Review the full description, including type, site, laterality, and complications. Refine your search if none fit.'
            : 'Try a shorter condition name, a common abbreviation, or an ICD-10 code. Check spelling and the Claim From date. No diagnosis has been selected and no provider request was prepared.';
        panel.appendChild(note);
        const provenance = document.createElement('p');
        provenance.textContent = `Search: ${result.query} · Claim From date: ${result.diagnosis_data.service_date} · CMS HHGS ${result.diagnosis_data.grouper_version}. Showing up to 25 options; enter more detail to narrow the list.`;
        panel.appendChild(provenance);
        result.candidates.forEach(candidate => {
            const button = document.createElement('button');
            button.type = 'button';
            button.className = 'autocomplete-item';
            button.style.cssText = 'display:block;width:100%;text-align:left;white-space:normal;margin:0.5rem 0;padding:0.75rem;';
            button.textContent = `${candidate.code} — ${candidate.description}`;
            button.addEventListener('click', () => {
                // Do not apply a list from a previous date or search.
                const input = document.getElementById('diagnosis-input');
                if (currentChoices !== result ||
                    document.getElementById('service-date').value !== result.diagnosis_data.service_date ||
                    input.value.trim() !== result.query) return;
                input.value = candidate.code;
                window.clearDiagnosisChoices();
                form.requestSubmit();
            });
            panel.appendChild(button);
        });
        form.parentNode.insertBefore(panel, form.nextSibling);
        heading.focus();
    };
})();

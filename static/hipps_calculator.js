/**
 * HIPPS Code Calculator UI Logic
 * Handles secondary diagnoses, GG scores, and API interaction.
 */

(function () {
    const secondaryDxList = [];
    let ggScoresVisible = false;

    // --- Secondary Diagnosis Management ---

    window.addSecondaryDx = function () {
        const input = document.getElementById('secondary-dx-input');
        const code = input.value.trim();
        if (!code) return;
        if (secondaryDxList.length >= 5) {
            alert('Maximum 5 secondary diagnoses.');
            return;
        }
        if (secondaryDxList.includes(code.toUpperCase())) {
            alert('Already added.');
            return;
        }
        secondaryDxList.push(code.toUpperCase());
        input.value = '';
        renderSecondaryDxTags();
    };

    window.removeSecondaryDx = function (index) {
        secondaryDxList.splice(index, 1);
        renderSecondaryDxTags();
    };

    function renderSecondaryDxTags() {
        const container = document.getElementById('secondary-dx-tags');
        if (!container) return;
        container.innerHTML = secondaryDxList.map((code, i) =>
            `<span class="secondary-dx-tag">${code}<button onclick="removeSecondaryDx(${i})">&times;</button></span>`
        ).join('');
        checkComorbidityLive();
        updateHIPPSProgress();
    }

    // --- Dynamic Comorbidity Checker ---
    async function checkComorbidityLive() {
        if (!window.currentResults?.icd10 || secondaryDxList.length === 0) {
            renderComorbidityBadge('None');
            return;
        }
        try {
            const resp = await fetch('/api/comorbidity-check', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    primary_icd10: window.currentResults.icd10,
                    secondary_icd10s: secondaryDxList,
                    service_date: window.currentResults.diagnosis_data?.service_date
                })
            });
            const data = await resp.json();
            renderComorbidityBadge(data.error ? 'Review codes' : data.adjustment);
        } catch (e) {
            renderComorbidityBadge('None');
        }
    }

    function renderComorbidityBadge(level) {
        let badge = document.getElementById('comorbidity-badge');
        if (!badge) {
            const label = document.querySelector('.hipps-field label');
            if (!label) return;
            // Find the "Secondary Diagnoses" label
            const labels = document.querySelectorAll('.hipps-field label');
            for (const l of labels) {
                if (l.textContent.includes('Secondary')) {
                    badge = document.createElement('span');
                    badge.id = 'comorbidity-badge';
                    badge.className = 'comorbidity-badge';
                    l.appendChild(badge);
                    break;
                }
            }
            if (!badge) return;
        }
        const cls = level === 'High' ? 'adj-high' : level === 'Low' ? 'adj-low' : 'adj-none';
        badge.className = 'comorbidity-badge ' + cls + ' just-changed';
        badge.textContent = level === 'Review codes' ? 'Review diagnosis codes'
            : level === 'None' ? 'No Adjustment' : level + ' Comorbidity';
        setTimeout(() => badge.classList.remove('just-changed'), 500);
    }

    // --- HIPPS Progress Indicator ---
    function updateHIPPSProgress() {
        const fill = document.getElementById('hipps-progress-fill');
        const text = document.getElementById('hipps-progress-text');
        if (!fill || !text) return;
        let completed = 0;
        const total = 4;
        if (window.currentResults?.icd10) completed++;
        if (document.querySelector('input[name="admission_source"]:checked')) completed++;
        if (document.querySelector('input[name="episode_timing"]:checked')) completed++;
        const ggFilled = document.querySelectorAll('[data-gg]:not([value=""])').length;
        if (ggFilled > 0) completed++;
        fill.style.width = ((completed / total) * 100) + '%';
        text.textContent = completed + '/' + total + ' sections';
    }

    // --- GG Scores Toggle ---

    window.toggleGGScores = function () {
        const section = document.getElementById('gg-scores-section');
        ggScoresVisible = !ggScoresVisible;
        section.style.display = ggScoresVisible ? 'block' : 'none';
        document.getElementById('gg-toggle-btn').textContent =
            ggScoresVisible ? 'Hide Functional Scores (GG Items)' : 'Enter Functional Scores (GG Items) — optional';
    };

    // --- Event listeners for progress + impact updates ---
    document.addEventListener('DOMContentLoaded', function () {
        document.querySelectorAll('input[name="admission_source"], input[name="episode_timing"]').forEach(function (el) {
            el.addEventListener('change', function () { updateHIPPSProgress(); });
        });
        document.querySelectorAll('[data-gg]').forEach(function (el) {
            el.addEventListener('change', function () { updateHIPPSProgress(); });
        });
        updateHIPPSProgress();
    });

    // --- Collect GG Scores ---

    function collectGGScores(prefix) {
        const scores = {};
        document.querySelectorAll(`[data-gg="${prefix}"]`).forEach(el => {
            const item = el.dataset.item;
            const val = parseInt(el.value, 10);
            if (!isNaN(val) && val > 0) {
                scores[item] = val;
            }
        });
        return scores;
    }

    // --- Populate the site-of-service selector from CMS areas ---

    function loadAreas() {
        const sel = document.getElementById('hipps-area-code');
        if (!sel) return;
        fetch('/api/wage-index-areas')
            .then(r => r.json())
            .then(data => {
                const byState = {};
                (data.areas || []).forEach(a => {
                    const st = (a.states && a.states[0]) || 'Other';
                    (byState[st] = byState[st] || []).push(a);
                });
                Object.keys(byState).sort().forEach(st => {
                    const g = document.createElement('optgroup');
                    g.label = st;
                    byState[st].forEach(a => {
                        const o = document.createElement('option');
                        o.value = a.code;
                        o.textContent = `${a.name} \u2014 WI ${a.wage_index.toFixed(4)}`;
                        g.appendChild(o);
                    });
                    sel.appendChild(g);
                });
            })
            .catch(() => { /* selector stays usable; payment just won't render */ });
    }

    document.addEventListener('DOMContentLoaded', loadAreas);

    // --- Calculate HIPPS ---

    window.calculateHIPPS = function () {
        const data = window.currentResults;
        if (!data || !data.icd10) {
            alert('Please run a PDGM lookup first.');
            return;
        }

        if (data.primary_eligibility?.eligible !== true) {
            alert('This diagnosis cannot be used for HIPPS calculation. Review the diagnosis alerts.');
            return;
        }

        const btn = document.getElementById('btn-calc-hipps');
        btn.disabled = true;
        btn.textContent = 'Calculating...';

        const payload = {
            primary_icd10: data.icd10,
            service_date: data.diagnosis_data?.service_date,
            secondary_icd10s: secondaryDxList,
            admission_source: parseInt(document.querySelector('input[name="admission_source"]:checked')?.value || '1', 10),
            episode_timing: parseInt(document.querySelector('input[name="episode_timing"]:checked')?.value || '1', 10),
            gg0130: collectGGScores('gg0130'),
            gg0170: collectGGScores('gg0170'),
            // CMS keys the wage index on CBSA, not ZIP. area-code is the
            // selector populated from GET /api/wage-index-areas.
            area_code: document.getElementById('hipps-area-code')?.value
                || document.getElementById('area-code')?.value || '',
        };

        fetch('/api/hipps', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        })
            .then(r => r.json())
            .then(result => {
                // Ignore a calculation for a diagnosis the user has since replaced.
                if (window.currentResults !== data) return;
                btn.disabled = false;
                btn.textContent = 'Calculate HIPPS Code';
                if (result.error) {
                    alert(result.error);
                    return;
                }
                renderHIPPSResult(result);
            })
            .catch(() => {
                if (window.currentResults !== data) return;
                btn.disabled = false;
                btn.textContent = 'Calculate HIPPS Code';
                alert('HIPPS calculation failed.');
            });
    };

    // --- Render Result ---

    function money(n) {
        return '$' + n.toLocaleString('en-US', {
            minimumFractionDigits: 2, maximumFractionDigits: 2,
        });
    }

    function renderHIPPSResult(r) {
        const container = document.getElementById('hipps-result');
        const d = r.dimensions;
        const p = r.payment;   // complete object, or null when no site of service

        // The HIPPS code and its dimensions never depend on geography, so they
        // always render. Only the payment block is conditional -- reading
        // payment fields unconditionally is what previously threw and surfaced
        // as "HIPPS calculation failed".
        const weight = d.case_mix_weight;

        let paymentBlock;
        if (p) {
            paymentBlock = `
            <div class="hipps-payment">
                <div class="pay-label">${p.is_lupa ? 'Estimated LUPA Payment' : 'Estimated 30-Day Payment'}</div>
                <div class="amount">${money(p.estimated_payment)}</div>
                <div class="pay-detail">National rate ${money(p.national_base_rate)} × weight ${weight.toFixed(4)}, wage-adjusted for ${p.area_name}</div>
                <div class="pay-detail">LUPA threshold: ${p.lupa_threshold} visits</div>
                <div class="pay-detail" style="margin-top:0.5rem; font-style:italic;">${p.disclaimer}</div>
            </div>`;
        } else {
            paymentBlock = `
            <div class="hipps-payment">
                <div class="pay-label">Estimated 30-Day Payment</div>
                <div class="amount" style="font-size:1.1rem; opacity:0.75;">Not available</div>
                <div class="pay-detail">${r.payment_note || 'Select a site of service to see the payment for this HIPPS code.'}</div>
            </div>`;
        }

        const wageRow = p
            ? `<div class="item"><span class="item-label">Wage Index</span><span class="item-value">${p.wage_index.toFixed(4)} — ${p.area_name}</span></div>`
            : '';

        container.innerHTML = `
            <div class="hipps-code-display">
                <div class="code">${r.hipps_code}</div>
                <div class="code-label">HIPPS Code — Case-Mix Weight: ${weight.toFixed(4)}</div>
            </div>
            <div class="hipps-breakdown">
                <div class="item"><span class="item-label">Clinical Group</span><span class="item-value">${d.clinical_group} — ${d.clinical_group_name}</span></div>
                <div class="item"><span class="item-label">Admission Source</span><span class="item-value">${d.admission_source}</span></div>
                <div class="item"><span class="item-label">Episode Timing</span><span class="item-value">${d.episode_timing}</span></div>
                <div class="item"><span class="item-label">Functional Level</span><span class="item-value">${d.functional_level} (score: ${r.functional.raw_score}/${r.functional.max_possible})</span></div>
                <div class="item"><span class="item-label">Comorbidity Adj.</span><span class="item-value">${d.comorbidity_adjustment}</span></div>
                <div class="item"><span class="item-label">LUPA Threshold</span><span class="item-value">${d.lupa_threshold} visits</span></div>
                ${wageRow}
            </div>
            ${paymentBlock}
        `;
        container.style.display = 'block';
    }
})();

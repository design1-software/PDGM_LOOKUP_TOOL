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
                    secondary_icd10s: secondaryDxList
                })
            });
            const data = await resp.json();
            renderComorbidityBadge(data.adjustment);
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
        badge.textContent = level === 'None' ? 'No Adjustment' : level + ' Comorbidity';
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

    // --- Calculate HIPPS ---

    window.calculateHIPPS = function () {
        const data = window.currentResults;
        if (!data || !data.icd10) {
            alert('Please run a PDGM lookup first.');
            return;
        }

        const btn = document.getElementById('btn-calc-hipps');
        btn.disabled = true;
        btn.textContent = 'Calculating...';

        const payload = {
            primary_icd10: data.icd10,
            secondary_icd10s: secondaryDxList,
            admission_source: parseInt(document.querySelector('input[name="admission_source"]:checked')?.value || '1', 10),
            episode_timing: parseInt(document.querySelector('input[name="episode_timing"]:checked')?.value || '1', 10),
            gg0130: collectGGScores('gg0130'),
            gg0170: collectGGScores('gg0170'),
            zip_code: document.getElementById('zip-input')?.value || '',
        };

        fetch('/api/hipps', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        })
            .then(r => r.json())
            .then(result => {
                btn.disabled = false;
                btn.textContent = 'Calculate HIPPS Code';
                if (result.error) {
                    alert(result.error);
                    return;
                }
                renderHIPPSResult(result);
            })
            .catch(() => {
                btn.disabled = false;
                btn.textContent = 'Calculate HIPPS Code';
                alert('HIPPS calculation failed.');
            });
    };

    // --- Render Result ---

    function renderHIPPSResult(r) {
        const container = document.getElementById('hipps-result');
        const d = r.dimensions;
        const p = r.payment;

        container.innerHTML = `
            <div class="hipps-code-display">
                <div class="code">${r.hipps_code}</div>
                <div class="code-label">HIPPS Code — Case-Mix Weight: ${p.case_mix_weight.toFixed(4)}</div>
            </div>
            <div class="hipps-breakdown">
                <div class="item"><span class="item-label">Clinical Group</span><span class="item-value">${d.clinical_group} — ${d.clinical_group_name}</span></div>
                <div class="item"><span class="item-label">Admission Source</span><span class="item-value">${d.admission_source}</span></div>
                <div class="item"><span class="item-label">Episode Timing</span><span class="item-value">${d.episode_timing}</span></div>
                <div class="item"><span class="item-label">Functional Level</span><span class="item-value">${d.functional_level} (score: ${r.functional.raw_score}/${r.functional.max_possible})</span></div>
                <div class="item"><span class="item-label">Comorbidity Adj.</span><span class="item-value">${d.comorbidity_adjustment}</span></div>
                <div class="item"><span class="item-label">Wage Index</span><span class="item-value">${p.wage_index.toFixed(3)}</span></div>
            </div>
            <div class="hipps-payment">
                <div class="pay-label">Estimated 30-Day Payment</div>
                <div class="amount">$${p.estimated_payment.toLocaleString('en-US', { minimumFractionDigits: 2 })}</div>
                <div class="pay-detail">Base: $${p.adjusted_base_rate.toLocaleString('en-US', { minimumFractionDigits: 2 })} × Weight: ${p.case_mix_weight.toFixed(4)}</div>
                <div class="pay-detail" style="margin-top:0.5rem; font-style:italic;">${p.disclaimer}</div>
            </div>
        `;
        container.style.display = 'block';
    }
})();

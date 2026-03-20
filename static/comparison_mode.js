/**
 * PDGM Comparison Mode — Side-by-side diagnosis comparison
 */
(function () {
    'use strict';

    window.openComparisonMode = function () {
        if (!window.currentResults || !window.currentResults.icd10) {
            alert('Run a PDGM lookup first.');
            return;
        }

        const codeA = window.currentResults.icd10;
        const descA = window.currentResults.raw?.description || '';
        const modal = document.getElementById('comparison-modal');
        if (!modal) return;

        document.getElementById('compare-code-a').textContent = codeA;
        document.getElementById('compare-desc-a').textContent = descA;
        document.getElementById('compare-input-b').value = '';
        document.getElementById('compare-result').innerHTML = '';

        modal.style.display = 'block';
        void modal.offsetHeight;
        modal.classList.add('modal-visible');
    };

    window.closeComparisonModal = function () {
        const modal = document.getElementById('comparison-modal');
        modal.classList.remove('modal-visible');
        setTimeout(function () { modal.style.display = 'none'; }, 300);
    };

    window.runComparison = async function () {
        const codeA = window.currentResults.icd10;
        const codeB = document.getElementById('compare-input-b').value.trim();
        if (!codeB) { alert('Enter a second ICD-10 code.'); return; }

        const btn = document.getElementById('compare-go-btn');
        btn.disabled = true;
        btn.textContent = 'Comparing...';

        try {
            const resp = await fetch('/api/compare', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ code_a: codeA, code_b: codeB })
            });
            const data = await resp.json();
            if (data.error) { alert(data.error); return; }
            renderComparison(data);
        } catch (e) {
            alert('Comparison failed.');
        } finally {
            btn.disabled = false;
            btn.textContent = 'Compare';
        }
    };

    function renderComparison(data) {
        const container = document.getElementById('compare-result');
        const a = data.a, b = data.b;
        const rawA = a.raw || {}, rawB = b.raw || {};
        const groupA = rawA.pdgm_clinical_group_name || 'N/A';
        const groupB = rawB.pdgm_clinical_group_name || 'N/A';
        const descA = rawA.description || 'N/A';
        const descB = rawB.description || 'N/A';
        const codeA = rawA.pdgm_clinical_group_code || '';
        const codeB = rawB.pdgm_clinical_group_code || '';
        const comorbA = rawA.COMORBIDITY_GROUP || 'N/A';
        const comorbB = rawB.COMORBIDITY_GROUP || 'N/A';
        const payA = a.payment_range;
        const payB = b.payment_range;

        function diffClass(va, vb) { return va !== vb ? ' class="comparison-diff"' : ''; }
        function fmtPay(range) {
            if (!range) return 'N/A';
            return '$' + range.min.toLocaleString('en-US', { minimumFractionDigits: 2 }) +
                ' — $' + range.max.toLocaleString('en-US', { minimumFractionDigits: 2 });
        }

        container.innerHTML = `
            <div class="comparison-grid">
                <div class="comparison-col">
                    <h4>Diagnosis A: ${a.icd10 || rawA.icd10_code || ''}</h4>
                    <p><strong>Description:</strong> ${descA}</p>
                    <p><strong>Clinical Group:</strong> <span${diffClass(codeA, codeB)}>${groupA} (${codeA})</span></p>
                    <p><strong>Comorbidity Group:</strong> <span${diffClass(comorbA, comorbB)}>${comorbA}</span></p>
                    <p><strong>Payment Range:</strong> <span${diffClass(fmtPay(payA), fmtPay(payB))}>${fmtPay(payA)}</span></p>
                </div>
                <div class="comparison-col">
                    <h4>Diagnosis B: ${b.icd10 || rawB.icd10_code || ''}</h4>
                    <p><strong>Description:</strong> ${descB}</p>
                    <p><strong>Clinical Group:</strong> <span${diffClass(codeA, codeB)}>${groupB} (${codeB})</span></p>
                    <p><strong>Comorbidity Group:</strong> <span${diffClass(comorbA, comorbB)}>${comorbB}</span></p>
                    <p><strong>Payment Range:</strong> <span${diffClass(fmtPay(payA), fmtPay(payB))}>${fmtPay(payB)}</span></p>
                </div>
            </div>
        `;
    }
})();

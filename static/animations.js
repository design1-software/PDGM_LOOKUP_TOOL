/**
 * PDGM Lookup Tool — Animation Controller
 * Handles counter animations, skeleton loading, modal transitions,
 * HIPPS code flip-in, and copy button feedback.
 */

(function () {
    'use strict';

    // ---- 1. COUNTER ANIMATION ----

    window.animateCounter = function (element, target, prefix, suffix, duration) {
        prefix = prefix || '';
        suffix = suffix || '';
        duration = duration || 800;
        const start = 0;
        const startTime = performance.now();

        function step(now) {
            const elapsed = now - startTime;
            const progress = Math.min(elapsed / duration, 1);
            // Ease-out cubic
            const eased = 1 - Math.pow(1 - progress, 3);
            const current = start + (target - eased < 1 ? eased : eased) * target;
            element.textContent = prefix + current.toLocaleString('en-US', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
            }) + suffix;
            if (progress < 1) {
                requestAnimationFrame(step);
            } else {
                element.textContent = prefix + target.toLocaleString('en-US', {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2,
                }) + suffix;
            }
        }
        requestAnimationFrame(step);
    };

    // ---- 2. SKELETON LOADING ----

    window.showSkeleton = function (containerId) {
        const el = document.getElementById(containerId);
        if (!el) return;
        el.innerHTML = `
            <div class="skeleton-card">
                <div class="skeleton skeleton-title"></div>
                <div class="skeleton skeleton-line long"></div>
                <div class="skeleton skeleton-line medium"></div>
                <div class="skeleton skeleton-line short"></div>
            </div>
            <div class="skeleton-card" style="animation-delay: 0.1s;">
                <div class="skeleton skeleton-title"></div>
                <div class="skeleton skeleton-line full"></div>
                <div class="skeleton skeleton-line long"></div>
                <div class="skeleton skeleton-line medium"></div>
            </div>
        `;
    };

    // ---- 3. MODAL TRANSITIONS ----

    const origShowRoadmap = window.showRoadmap;
    const origShowAssessment = window.showAssessment;
    const origCloseRoadmap = window.closeRoadmapModal;
    const origCloseAssessment = window.closeAssessmentModal;

    function openModal(id) {
        const modal = document.getElementById(id);
        if (!modal) return;
        // Remove display:none first so transition can fire
        modal.style.display = 'block';
        // Force reflow
        void modal.offsetHeight;
        modal.classList.add('modal-visible');
    }

    function closeModal(id) {
        const modal = document.getElementById(id);
        if (!modal) return;
        modal.classList.remove('modal-visible');
        setTimeout(function () {
            modal.style.display = 'none';
        }, 300);
    }

    // Override modal functions after DOM load
    document.addEventListener('DOMContentLoaded', function () {
        // Patch close functions
        window.closeRoadmapModal = function () { closeModal('roadmap-modal'); };
        window.closeAssessmentModal = function () { closeModal('assessment-modal'); };

        // Patch open: intercept showRoadmap/showAssessment to use animated open
        const _origShowRoadmap = window.showRoadmap;
        window.showRoadmap = async function () {
            if (!window.currentResults) return;
            const pdgmGroup = window.currentResults.raw?.pdgm_clinical_group_name || window.currentResults.pdgm_group || '';
            const select = document.getElementById('discipline-select');
            const disciplines = Array.from(select.selectedOptions).map(function (o) { return o.value; });
            openModal('roadmap-modal');
            document.getElementById('roadmap-body').innerHTML = '<div class="skeleton-card"><div class="skeleton skeleton-title"></div><div class="skeleton skeleton-line long"></div><div class="skeleton skeleton-line medium"></div><div class="skeleton skeleton-line short"></div></div>';
            try {
                const resp = await fetch('/api/roadmap', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ diagnosis: window.currentQuery, pdgm_group: pdgmGroup, disciplines: disciplines })
                });
                const data = await resp.json();
                if (data.roadmap) {
                    document.getElementById('roadmap-body').innerText = data.roadmap;
                } else {
                    document.getElementById('roadmap-body').innerText = data.error || 'Error generating roadmap.';
                }
            } catch (e) {
                document.getElementById('roadmap-body').innerText = 'Network error.';
            }
        };

        window.showAssessment = async function () {
            if (!window.currentResults) return;
            const pdgmGroup = window.currentResults.raw?.pdgm_clinical_group_name || window.currentResults.pdgm_group || '';
            const select = document.getElementById('discipline-select');
            const disciplines = Array.from(select.selectedOptions).map(function (o) { return o.value; });
            openModal('assessment-modal');
            document.getElementById('assessment-body').innerHTML = '<div class="skeleton-card"><div class="skeleton skeleton-title"></div><div class="skeleton skeleton-line long"></div><div class="skeleton skeleton-line medium"></div><div class="skeleton skeleton-line short"></div></div>';
            try {
                const resp = await fetch('/api/assessment', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ diagnosis: window.currentQuery, pdgm_group: pdgmGroup, disciplines: disciplines })
                });
                const data = await resp.json();
                if (data.assessment) {
                    document.getElementById('assessment-body').innerText = data.assessment;
                } else {
                    document.getElementById('assessment-body').innerText = data.error || 'Error generating assessment.';
                }
            } catch (e) {
                document.getElementById('assessment-body').innerText = 'Network error.';
            }
        };

        // Click outside modal to close (animated)
        window.onclick = function (event) {
            if (event.target.classList.contains('modal')) {
                closeModal(event.target.id);
            }
        };
    });

    // ---- 4. COPY BUTTON CHECKMARK FEEDBACK ----

    const origCopy = window.copyToClipboard;
    document.addEventListener('DOMContentLoaded', function () {
        window.copyToClipboard = function () {
            if (!window.currentResults) return;
            const data = window.currentResults;
            const icd10 = data.icd10 || data.icd_code || '';
            const pdgmGroup = data.raw?.pdgm_clinical_group_name || data.pdgm_group || '';
            const description = data.raw?.description || data.description || '';
            let text = 'PDGM Lookup Results\n\nQuery: ' + window.currentQuery +
                '\nICD-10: ' + icd10 + '\nClinical Group: ' + pdgmGroup +
                '\nDescription: ' + description;
            if (data.payment && data.payment.estimated_payment) {
                var p = data.payment;
                text += '\n\nEstimated Reimbursement: $' + p.estimated_payment.toLocaleString('en-US', { minimumFractionDigits: 2 });
                text += '\nBase Rate: $' + p.base_rate.toLocaleString('en-US', { minimumFractionDigits: 2 });
                text += '\nWage Index: ' + p.wage_index.toFixed(3);
                if (p.is_lupa) text += '\nLUPA Alert: Visit count below threshold (' + p.lupa_threshold + ')';
            }

            const btn = event.target.closest('.btn-export') || event.target;
            const origText = btn.textContent;

            navigator.clipboard.writeText(text).then(function () {
                btn.classList.add('copied');
                btn.textContent = 'Copied!';
                setTimeout(function () {
                    btn.classList.remove('copied');
                    btn.textContent = origText;
                }, 2000);
            }).catch(function () {
                btn.textContent = 'Failed';
                setTimeout(function () { btn.textContent = origText; }, 1500);
            });
        };
    });

    // ---- 5. SKELETON IN PROGRESS HANDLER ----

    // Patch enhanced_query_progress to show skeleton instead of spinner
    document.addEventListener('DOMContentLoaded', function () {
        const resultsSection = document.getElementById('results');
        const responseContent = document.getElementById('response-content');
        if (!resultsSection || !responseContent) return;

        // Observe when results section becomes visible to inject skeleton
        const observer = new MutationObserver(function (mutations) {
            mutations.forEach(function (m) {
                if (m.attributeName === 'style' && resultsSection.style.display === 'block' && !responseContent.innerHTML.trim()) {
                    showSkeleton('response-content');
                }
            });
        });
        observer.observe(resultsSection, { attributes: true });
    });

    // ---- 6. HIPPS CODE FLIP-IN ----

    // Patch the HIPPS result renderer to wrap each char in a span
    const origRenderHIPPS = window.calculateHIPPS;
    document.addEventListener('DOMContentLoaded', function () {
        // We patch the render inside hipps_calculator.js by observing the result container
        const hippsResult = document.getElementById('hipps-result');
        if (!hippsResult) return;

        const hippsObserver = new MutationObserver(function () {
            const codeEl = hippsResult.querySelector('.hipps-code-display .code');
            if (codeEl && !codeEl.querySelector('.hipps-code-char')) {
                const text = codeEl.textContent.trim();
                codeEl.innerHTML = text.split('').map(function (ch) {
                    return '<span class="hipps-code-char">' + ch + '</span>';
                }).join('');
            }

            // Animate payment counter
            const amountEl = hippsResult.querySelector('.hipps-payment .amount');
            if (amountEl && !amountEl.dataset.animated) {
                amountEl.dataset.animated = '1';
                const raw = amountEl.textContent.replace(/[^0-9.]/g, '');
                const target = parseFloat(raw);
                if (!isNaN(target)) {
                    animateCounter(amountEl, target, '$', '', 900);
                }
            }
        });
        hippsObserver.observe(hippsResult, { childList: true, subtree: true });
    });

    // ---- 7. PAYMENT AMOUNT COUNTER IN RESULTS ----

    // Observe response-content for payment values to animate
    document.addEventListener('DOMContentLoaded', function () {
        const responseContent = document.getElementById('response-content');
        if (!responseContent) return;

        const payObserver = new MutationObserver(function () {
            const paymentValues = responseContent.querySelectorAll('.highlight-value');
            paymentValues.forEach(function (el) {
                if (el.dataset.animated) return;
                const text = el.textContent;
                if (text.startsWith('$')) {
                    el.dataset.animated = '1';
                    const target = parseFloat(text.replace(/[^0-9.]/g, ''));
                    if (!isNaN(target)) {
                        animateCounter(el, target, '$', '', 800);
                    }
                }
            });
        });
        payObserver.observe(responseContent, { childList: true, subtree: true });
    });

})();

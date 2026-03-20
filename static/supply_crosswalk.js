/**
 * Supply & Documentation Cross-Walk for Wound/Diabetic Codes
 * Shows supply reminders and documentation requirements when relevant codes are looked up.
 */
(function () {
    'use strict';

    const SUPPLY_CROSSWALK = {
        'L89': { category: 'Pressure Ulcer/Injury', supplies: ['Wound vac/NPWT', 'Foam dressings', 'Hydrocolloid', 'Barrier cream', 'Specialty mattress'], docs: ['Wound measurements (L x W x D)', 'Stage/injury classification', 'Braden Scale score', 'Turning/repositioning schedule', 'Wound bed description', 'Periwound condition'] },
        'L97': { category: 'Non-Pressure Chronic Ulcer', supplies: ['Compression wraps', 'Unna boot', 'Alginate dressings', 'Silver dressings', 'Wound cleanser'], docs: ['ABI documentation', 'Vascular status', 'Wound measurements', 'Wound etiology', 'Edema assessment'] },
        'L98': { category: 'Skin Disorder', supplies: ['Wound care supplies', 'Topical medications', 'Protective dressings'], docs: ['Wound description', 'Treatment response', 'Contributing factors'] },
        'E08': { category: 'Diabetes with Complications', supplies: ['Glucose monitor', 'Insulin supplies', 'Diabetic foot care kit'], docs: ['HbA1c level', 'Blood glucose log', 'Monofilament testing', 'Foot inspection findings'] },
        'E09': { category: 'Drug-Induced Diabetes', supplies: ['Glucose monitor', 'Insulin supplies'], docs: ['Causative medication', 'HbA1c level', 'Blood glucose monitoring plan'] },
        'E10': { category: 'Type 1 Diabetes', supplies: ['Insulin pump supplies', 'CGM sensor', 'Glucose monitor', 'Ketone strips'], docs: ['HbA1c level', 'Insulin regimen', 'Hypoglycemia action plan', 'Carb counting education'] },
        'E11': { category: 'Type 2 Diabetes', supplies: ['Glucose monitor', 'Test strips', 'Lancets', 'Insulin supplies'], docs: ['HbA1c level', 'Medication reconciliation', 'Dietary assessment', 'Foot exam findings', 'Monofilament testing'] },
        'E13': { category: 'Other Diabetes', supplies: ['Glucose monitor', 'Insulin supplies'], docs: ['HbA1c level', 'Blood glucose log', 'Diabetes type specification'] },
        'T81': { category: 'Surgical Complication', supplies: ['Wound care supplies', 'Steri-strips', 'Drainage supplies'], docs: ['Surgical site description', 'Signs of infection assessment', 'Surgeon communication'] },
        'I83': { category: 'Varicose Veins with Ulcer', supplies: ['Compression stockings', 'Multilayer wraps', 'Foam dressings'], docs: ['ABI documentation', 'Leg circumference measurements', 'Edema grading'] },
        'I87': { category: 'Venous Insufficiency', supplies: ['Compression therapy', 'Elevation wedge', 'Moisturizer'], docs: ['Venous status assessment', 'Edema measurements', 'Skin integrity check'] },
        'T84': { category: 'Orthopedic Device Complication', supplies: ['Wound care supplies', 'Ice packs', 'Immobilization device'], docs: ['Device/implant details', 'Wound assessment', 'ROM measurements', 'Weight-bearing status'] },
        'S72': { category: 'Hip Fracture', supplies: ['Walker/cane', 'Hip precaution kit', 'Elevated toilet seat', 'Grab bars'], docs: ['Weight-bearing status', 'Fall risk assessment (Morse scale)', 'Pain scale', 'Surgical approach/precautions'] },
        'Z96': { category: 'Joint Replacement Status', supplies: ['Assistive device', 'Ice machine', 'CPM machine', 'TED hose'], docs: ['ROM measurements', 'Weight-bearing status', 'DVT prophylaxis', 'Surgical precautions (anterior/posterior)'] },
    };

    window.getSupplyCrosswalk = function (icd10Code) {
        if (!icd10Code) return null;
        const normalized = icd10Code.replace('.', '').toUpperCase();
        for (const [prefix, data] of Object.entries(SUPPLY_CROSSWALK)) {
            if (normalized.startsWith(prefix.replace('.', ''))) {
                return data;
            }
        }
        return null;
    };

    window.renderSupplyCrosswalk = function (data) {
        if (!data) return '';
        return `
            <div class="supply-reminder">
                <h4><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"/></svg> ${data.category} — Supply & Documentation Reminders</h4>
                <div class="supply-list">
                    ${data.supplies.map(s => `<span class="supply-tag">${s}</span>`).join('')}
                </div>
                <ul class="doc-checklist">
                    ${data.docs.map(d => `<li>${d}</li>`).join('')}
                </ul>
            </div>
        `;
    };
})();

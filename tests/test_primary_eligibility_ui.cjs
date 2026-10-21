// Run with: node --test tests/test_primary_eligibility_ui.cjs
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');

function harness() {
    function node() {
        return { children: [], innerHTML: '', textContent: '',
            appendChild(child) { this.children.push(child); } };
    }
    const elements = {
        'response-content': node(),
        'hipps-result': { innerHTML: 'Previous payment', style: { display: 'block' } },
        'btn-calc-hipps': { disabled: false, textContent: '' },
        'results': { style: { display: 'block' } },
        'service-date': { value: '' },
    };
    const alerts = [];
    const context = vm.createContext({
        window: {}, alert: message => alerts.push(message),
        document: {
            createElement: () => node(),
            addEventListener() {},
            getElementById: id => elements[id] || null,
            querySelector: () => null,
            querySelectorAll: () => [],
        },
        escapeHtml: text => String(text),
        AbortController,
        setTimeout: callback => callback(), clearTimeout() {}, clearInterval() {},
        fetch() { throw Error('Unexpected request'); },
    });
    vm.runInContext(fs.readFileSync(path.join(root, 'static/hipps_calculator.js'), 'utf8'), context);
    const template = fs.readFileSync(path.join(root, 'templates/index.html'), 'utf8');
    const start = template.indexOf('function displayResults(data) {');
    const end = template.indexOf('// Authentication Modal Functions', start);
    vm.runInContext(template.slice(start, end), context);
    return { context, elements, alerts };
}

test('new blocked lookup clears old payment and disables HIPPS; valid lookup enables it', () => {
    const { context, elements } = harness();
    context.displayResults({ icd10: 'B95.0', primary_eligibility: { eligible: false } });
    assert.equal(elements['hipps-result'].innerHTML, '');
    assert.equal(elements['hipps-result'].style.display, 'none');
    assert.equal(elements['btn-calc-hipps'].disabled, true);
    context.displayResults({ icd10: 'E11.65', primary_eligibility: { eligible: true } });
    assert.equal(elements['btn-calc-hipps'].disabled, false);
    context.displayResults({ icd10: 'E11.65' });
    assert.equal(elements['btn-calc-hipps'].disabled, true);
});

test('result identifies the exact diagnosis release and selected date', () => {
    const { context, elements } = harness();
    context.displayResults({ raw: { icd10_code: 'D6911' }, diagnosis_data: {
        service_date: '2026-10-01', grouper_version: '07.2.26',
        effective_from: '2026-10-01', effective_through: '2026-12-31', verified_on: '2026-10-21',
    } });
    assert.match(elements['response-content'].innerHTML, /Claim From date: 2026-10-01/);
    assert.match(elements['response-content'].innerHTML, /CMS HHGS 07.2.26/);
});

test('changing the date invalidates previous diagnosis and payment results', () => {
    const { context, elements } = harness();
    context.window.currentResults = { icd10: 'D691' };
    context.clearDiagnosisResultsForDateChange();
    assert.equal(context.window.currentResults, null);
    assert.equal(elements['results'].style.display, 'none');
    assert.equal(elements['hipps-result'].innerHTML, '');
    assert.equal(elements['btn-calc-hipps'].disabled, true);
});

test('HIPPS request retains the date of the verified lookup', async () => {
    const { context } = harness();
    let sent;
    context.fetch = async (url, options) => {
        sent = JSON.parse(options.body);
        return { json: async () => ({ error: 'Stop after request capture' }) };
    };
    context.window.currentResults = { icd10: 'D691', primary_eligibility: { eligible: true },
        diagnosis_data: { service_date: '2026-09-30' } };
    context.window.calculateHIPPS();
    await new Promise(setImmediate);
    assert.equal(sent.service_date, '2026-09-30');
});

test('lookup request sends date and surfaces unsupported-date errors', async () => {
    const { context } = harness();
    context.document.readyState = 'loading';
    vm.runInContext(fs.readFileSync(path.join(root, 'static/enhanced_query_progress.js'), 'utf8'), context);
    let sent;
    context.fetch = async (url, options) => {
        sent = JSON.parse(options.body);
        return { ok: false, status: 400, json: async () => ({ error: 'No verified mapping for this date' }) };
    };
    const method = vm.runInContext('PDGMQueryProgress.prototype.makeAPIRequest', context);
    await assert.rejects(method.call({}, new Map([
        ['diagnosis', 'E1165'], ['service_date', '2027-01-01'],
    ])), /No verified mapping for this date/);
    assert.equal(sent.service_date, '2027-01-01');
});

test('an in-flight lookup for another date cannot restore stale results', () => {
    const { context, elements } = harness();
    context.document.readyState = 'loading';
    vm.runInContext(fs.readFileSync(path.join(root, 'static/enhanced_query_progress.js'), 'utf8'), context);
    elements['service-date'].value = '2026-10-01';
    elements['enhanced-progress-container'] = { style: {}, querySelector: () => ({ style: {} }) };
    context.window.currentResults = null;
    const complete = vm.runInContext('PDGMQueryProgress.prototype.completeProgress', context);
    complete.call({ progressStages: [] }, { diagnosis_data: { service_date: '2026-09-30' } });
    assert.equal(context.window.currentResults, null);
    assert.equal(elements['enhanced-progress-container'].style.display, 'none');
});

test('diagnosis alerts show explanation and next step as text, with existing severity styling', () => {
    const { context, elements } = harness();
    context.displayResults({
        icd10: 'D63.1', raw: { icd10_code: 'D631' },
        primary_eligibility: { eligible: false },
        flags: [{ type: 'warning', message: 'Code-first sequencing needs review',
            explanation: '<img src=x onerror=alert(1)>', next_step: 'Review the documented underlying condition.' }],
    });
    const badge = elements['response-content'].children[0].children[0];
    const content = badge.children[0];
    assert.equal(badge.className, 'flag-badge flag-warning');
    assert.match(content.children[0].textContent, /Code-first sequencing/);
    assert.equal(content.children[1].textContent, '<img src=x onerror=alert(1)>');
    assert.equal(content.children[1].innerHTML, '');
    assert.equal(content.children[2].textContent, 'Next step: Review the documented underlying condition.');
});

test('unresolved lookup is labeled unverified rather than complete', () => {
    const { context, elements } = harness();
    context.displayResults({ raw: {}, primary_eligibility: { eligible: false } });
    assert.match(elements['response-content'].innerHTML, /Diagnosis not verified/);
    assert.doesNotMatch(elements['response-content'].innerHTML, /PDGM Analysis Complete/);
});

test('older flags without explanation fields still render', () => {
    const { context, elements } = harness();
    context.displayResults({ flags: [{ type: 'error', message: 'Legacy warning' }] });
    const content = elements['response-content'].children[0].children[0].children[0];
    assert.equal(content.children.length, 1);
    assert.match(content.children[0].textContent, /Legacy warning/);
});

test('direct JavaScript invocation cannot calculate a blocked diagnosis', () => {
    const { context, alerts } = harness();
    context.window.currentResults = { icd10: 'B95.0', primary_eligibility: { eligible: false } };
    context.window.calculateHIPPS();
    assert.equal(alerts.length, 1);
    assert.match(alerts[0], /diagnosis alerts/);
});

test('late calculation response cannot restore payment for a replaced diagnosis', async () => {
    const { context, elements, alerts } = harness();
    let resolve;
    context.fetch = () => new Promise(done => { resolve = done; });
    context.window.currentResults = { icd10: 'E11.65', primary_eligibility: { eligible: true } };
    context.window.calculateHIPPS();
    context.window.currentResults = { icd10: 'B95.0', primary_eligibility: { eligible: false } };
    context.displayResults(context.window.currentResults);
    resolve({ json: async () => ({ error: 'Old response' }) });
    await new Promise(setImmediate);
    assert.equal(alerts.length, 0);
    assert.equal(elements['btn-calc-hipps'].disabled, true);
    assert.equal(elements['hipps-result'].innerHTML, '');
});

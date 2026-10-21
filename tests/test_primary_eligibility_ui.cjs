// Run with: node --test tests/test_primary_eligibility_ui.cjs
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');

function harness() {
    const elements = {
        'response-content': { innerHTML: '', appendChild() {} },
        'hipps-result': { innerHTML: 'Previous payment', style: { display: 'block' } },
        'btn-calc-hipps': { disabled: false, textContent: '' },
    };
    const alerts = [];
    const context = vm.createContext({
        window: {}, alert: message => alerts.push(message),
        document: {
            addEventListener() {},
            getElementById: id => elements[id] || null,
            querySelector: () => null,
            querySelectorAll: () => [],
        },
        escapeHtml: text => String(text),
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

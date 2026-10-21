const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

class Node {
    constructor() {
        this.children = []; this.events = {}; this.value = ''; this.style = {};
        this.checked = false; this.textContent = ''; this.disabled = false;
    }
    appendChild(child) { child.parent = this; this.children.push(child); }
    replaceChildren() { this.children = []; }
    remove() { this.parent.children = this.parent.children.filter(item => item !== this); }
    setAttribute(key, value) { this[key] = value; }
    addEventListener(type, callback) { (this.events[type] ||= []).push(callback); }
    async emit(type) { for (const callback of this.events[type] || []) await callback({ target: this }); }
    find(id) { return this.id === id ? this : this.children.map(child => child.find(id)).find(Boolean); }
}

const BODY = 'Current record: [RECORD]\nClinical findings: [INDICATORS]\nPlease clarify.';
function harness(issue = 'primary_condition') {
    const root = new Node(); root.id = 'response-content';
    const requests = [], copied = [], printed = [];
    const data = { icd10: 'M62.81', diagnosis_data: { service_date: '2026-10-21' },
        clarification_workflow: { state: 'review_documentation', can_prepare: true, message: 'Review documentation.',
            issues: [{ code: issue, label: issue, detail_required: issue === 'specificity',
                instruction_review_required: issue === 'sequencing' }],
            detail_options: [{ code: 'acuity', label: 'Acuity' }] } };
    const context = vm.createContext({
        window: { currentResults: data, open() {
            return { document: { body: { appendChild: node => printed.push(node) }, createElement: () => new Node() },
                focus() {}, print() {} };
        } },
        document: { createElement: () => new Node(), getElementById: id => root.find(id) },
        navigator: { clipboard: { writeText: async text => copied.push(text) } },
        fetch: async (url, options) => {
            requests.push(JSON.parse(options.body));
            return { ok: true, json: async () => ({ draft: { subject: 'Clarification', body: BODY,
                completion_note: 'Complete locally.', required_placeholders: ['[RECORD]', '[INDICATORS]'] } }) };
        },
    });
    vm.runInContext(fs.readFileSync(path.join(__dirname, '../static/provider_clarification.js'), 'utf8'), context);
    context.window.renderProviderClarification(data);
    const get = id => root.find('clarification-' + id);
    async function checked(name, value = true) { get(name).checked = value; await get(name).emit('change'); }
    async function review() { await checked('reviewed'); await checked('needed'); }
    return { context, root, data, get, checked, review, requests, copied, printed };
}

test('documentation review and unresolved information are required before preparing a template', async () => {
    const h = harness();
    assert.equal(h.get('prepare').disabled, true);
    await h.get('prepare').emit('click');
    assert.equal(h.requests.length, 0);
    await h.review();
    assert.equal(h.get('prepare').disabled, false);
    await h.get('prepare').emit('click');
    assert.equal(h.requests.length, 1);
    assert.equal(h.requests[0].service_date, '2026-10-21');
    await h.checked('needed', false);
    assert.equal(h.get('prepare').disabled, true);
    assert.equal(h.get('editor'), undefined);
});

test('sequencing and specificity require their respective extra review selections', async () => {
    const sequencing = harness('sequencing');
    await sequencing.review();
    assert.equal(sequencing.get('prepare').disabled, true);
    await sequencing.checked('instruction');
    assert.equal(sequencing.get('prepare').disabled, false);
    const specificity = harness('specificity');
    await specificity.review();
    assert.equal(specificity.get('prepare').disabled, true);
    specificity.get('detail').value = 'acuity';
    await specificity.get('detail').emit('change');
    assert.equal(specificity.get('prepare').disabled, false);
    await specificity.get('prepare').emit('click');
    assert.equal(specificity.requests[0].missing_detail, 'acuity');
});

test('local context and final review gate copy/print, and edits are never posted to the server', async () => {
    const h = harness(); await h.review(); await h.get('prepare').emit('click');
    await h.checked('final-review');
    assert.equal(h.get('copy').disabled, true);
    h.get('editor').value = BODY.replace('[RECORD]', 'Source note 10/20: documented condition')
        .replace('[INDICATORS]', '<script>not executable</script> Source exam 10/21: findings');
    await h.get('editor').emit('input');
    assert.equal(h.get('final-review').checked, false);
    await h.checked('final-review');
    assert.equal(h.get('copy').disabled, false);
    await h.get('copy').emit('click');
    await h.get('print').emit('click');
    assert.match(h.copied[0], /Source note/);
    assert.match(h.printed[0].textContent, /<script>not executable<\/script>/);
    assert.equal(h.printed[0].children.length, 0);
    assert.equal(h.requests.length, 1);
    assert.doesNotMatch(JSON.stringify(h.requests), /Source note|Source exam/);
});

test('unresolved codes and technical failures expose no preparation action', () => {
    for (const state of ['verify_code', 'technical_failure', 'no_issue']) {
        const h = harness();
        h.data.clarification_workflow = { state, can_prepare: false, message: 'Verify or retry.', issues: [] };
        h.context.window.renderProviderClarification(h.data);
        assert.equal(h.get('prepare'), undefined);
        assert.equal(h.get('editor'), undefined);
    }
});

test('a late template response cannot restore an obsolete draft', async () => {
    const h = harness(); await h.review();
    let resolve;
    h.context.fetch = () => new Promise(done => { resolve = done; });
    const pending = h.get('prepare').emit('click');
    h.context.window.currentResults = { icd10: 'E11.65' };
    h.context.window.clearProviderClarification();
    resolve({ ok: true, json: async () => ({ draft: { body: BODY } }) });
    await pending;
    assert.equal(h.get('editor'), undefined);
    assert.equal(h.root.find('provider-clarification'), undefined);
});

test('technical template failures never create an editor or a request', async () => {
    const h = harness(); await h.review();
    h.context.fetch = async () => { throw Error('Offline'); };
    await h.get('prepare').emit('click');
    assert.equal(h.get('editor'), undefined);
    assert.equal(h.get('prepare').disabled, false);
});

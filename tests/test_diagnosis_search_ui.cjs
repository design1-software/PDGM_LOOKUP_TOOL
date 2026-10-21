const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const root = path.resolve(__dirname, '..');

function harness() {
    const elements = {};
    function node() {
        return { children: [], style: {}, events: {}, textContent: '', innerHTML: '',
            setAttribute() {}, focus() { this.focused = true; },
            appendChild(child) { this.children.push(child); child.parentNode = this; },
            insertBefore(child) { this.appendChild(child); if (child.id) elements[child.id] = child; },
            addEventListener(name, cb) { this.events[name] = cb; },
            remove() { delete elements[this.id]; },
            querySelector() { return node(); },
        };
    }
    const form = node(); form.parentNode = node();
    let submits = 0; form.requestSubmit = () => { submits++; };
    elements['pdgm-form'] = form;
    elements['diagnosis-input'] = { value: 'heart failure' };
    elements['service-date'] = { value: '2026-10-21' };
    elements['enhanced-progress-container'] = node();
    for (const id of ['results', 'hipps-panel', 'roadmap-container', 'export-section']) {
        elements[id] = node(); elements[id].style.display = 'none';
    }
    const timers = [];
    const context = vm.createContext({ window: {},
        document: { readyState: 'loading', addEventListener() {},
            createElement: node, getElementById: id => elements[id], querySelector() {} },
        setTimeout: cb => timers.push(cb), clearTimeout() {}, clearInterval() {},
    });
    for (const file of ['diagnosis_search.js', 'enhanced_query_progress.js']) {
        vm.runInContext(fs.readFileSync(path.join(root, 'static', file), 'utf8'), context);
    }
    const result = { selection_required: true, query: 'heart failure',
        candidates: [{ code: 'I50.9', description: '<img src=x> Heart failure, unspecified' }],
        diagnosis_data: { service_date: '2026-10-21', grouper_version: '07.2.26' } };
    return { context, elements, result, timers, submits: () => submits };
}

test('potential match descriptions render as text, with no automatic selection', () => {
    const h = harness();
    h.context.window.renderDiagnosisChoices(h.result);
    const panel = h.elements['diagnosis-choices'];
    assert.equal(h.submits(), 0);
    assert.equal(panel.children[3].textContent, 'I50.9 — <img src=x> Heart failure, unspecified');
    assert.equal(panel.children[3].innerHTML, '');
    assert.match(panel.children[1].textContent, /not a confirmed diagnosis/);
    assert.equal(panel.children[0].focused, true);
    panel.children[3].events.click();
    assert.equal(h.elements['diagnosis-input'].value, 'I50.9');
    assert.equal(h.elements['service-date'].value, '2026-10-21');
    assert.equal(h.submits(), 1);
    assert.equal(h.elements['diagnosis-choices'], undefined);
});

test('date changes, edited text, and discarded lists cannot select stale codes', () => {
    for (const change of ['date', 'text', 'clear']) {
        const h = harness(); h.context.window.renderDiagnosisChoices(h.result);
        const button = h.elements['diagnosis-choices'].children[3];
        if (change === 'date') h.elements['service-date'].value = '2026-09-30';
        if (change === 'text') h.elements['diagnosis-input'].value = 'diabetes';
        if (change === 'clear') h.context.window.clearDiagnosisChoices();
        button.events.click();
        assert.equal(h.submits(), 0);
    }
});

test('no matches explains refinement without clinical actions', () => {
    const h = harness(); h.result.candidates = [];
    h.context.window.renderDiagnosisChoices(h.result);
    const panel = h.elements['diagnosis-choices'];
    assert.equal(panel.children.length, 3);
    assert.match(panel.children[0].textContent, /No matching descriptions/);
    assert.match(panel.children[1].textContent, /Check spelling/);
    assert.match(panel.children[1].textContent, /no provider request/);
});

test('candidate response never becomes current diagnosis or opens payment tools', () => {
    const h = harness();
    const complete = vm.runInContext('PDGMQueryProgress.prototype.completeProgress', h.context);
    complete.call({ requestId: 3, progressStages: [], completeStage() {} }, h.result);
    h.timers[0]();
    assert.equal(h.context.window.currentResults, null);
    assert.ok(h.elements['diagnosis-choices']);
    for (const id of ['results', 'hipps-panel', 'roadmap-container', 'export-section']) {
        assert.equal(h.elements[id].style.display, 'none');
    }
});

test('delayed completed searches cannot hide a newer query or restore discarded choices', () => {
    const h = harness();
    const progress = { requestId: 1, progressStages: [], completeStage() {} };
    const complete = vm.runInContext('PDGMQueryProgress.prototype.completeProgress', h.context);
    complete.call(progress, h.result);
    progress.requestId = 2;
    h.elements['enhanced-progress-container'].style.display = 'block';
    h.timers[0]();
    assert.equal(h.elements['enhanced-progress-container'].style.display, 'block');
    assert.equal(h.elements['diagnosis-choices'], undefined);
});

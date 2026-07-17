const assert = require('node:assert/strict');
const test = require('node:test');

const {
  prepareAnalysisPresentation,
  renderAnalysisActions,
} = require('../../resources/ui/analysis-presentation.js');

function presentationFixture() {
  const shownClasses = [];
  return {
    shownClasses,
    mask: {
      classList: {
        add(name) { shownClasses.push(name); },
      },
    },
    title: { textContent: 'Existing analysis' },
    body: {
      innerHTML: '<div>Existing content</div>',
      attributes: {},
      setAttribute(name, value) { this.attributes[name] = value; },
    },
  };
}

test('initial analysis resets content and opens the modal', () => {
  const fixture = presentationFixture();

  prepareAnalysisPresentation({
    mask: fixture.mask,
    title: fixture.title,
    body: fixture.body,
    titleText: 'Usage analysis',
    loadingHTML: '<div>Loading</div>',
    preserveContent: false,
  });

  assert.equal(fixture.title.textContent, 'Usage analysis');
  assert.equal(fixture.body.innerHTML, '<div>Loading</div>');
  assert.deepEqual(fixture.shownClasses, ['show']);
  assert.equal(fixture.body.attributes['aria-busy'], 'true');
});

test('background refresh keeps the existing modal presentation stable', () => {
  const fixture = presentationFixture();

  prepareAnalysisPresentation({
    mask: fixture.mask,
    title: fixture.title,
    body: fixture.body,
    titleText: 'Usage analysis',
    loadingHTML: '<div>Loading</div>',
    preserveContent: true,
  });

  assert.equal(fixture.title.textContent, 'Existing analysis');
  assert.equal(fixture.body.innerHTML, '<div>Existing content</div>');
  assert.deepEqual(fixture.shownClasses, []);
  assert.equal(fixture.body.attributes['aria-busy'], 'true');
});

test('analysis rows render open, analyze, and delete actions in order', () => {
  const html = renderAnalysisActions({
    path: '/Users/test/project',
    name: 'project',
    canDelete: true,
    labels: { open: '打开', analyze: '分析', delete: '删除' },
  });

  assert.ok(html.indexOf('>打开<') < html.indexOf('>分析<'));
  assert.ok(html.indexOf('>分析<') < html.indexOf('>删除<'));
  assert.match(html, /data-reveal="\/Users\/test\/project"/);
  assert.match(html, /data-analyze-path="\/Users\/test\/project"/);
  assert.doesNotMatch(html, /Finder/);
});

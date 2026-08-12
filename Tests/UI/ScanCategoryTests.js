const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');

const appSource = fs.readFileSync(
  path.join(__dirname, '../../resources/ui/app.js'),
  'utf8',
);

test('scan scopes replace Trash with System Temporary Files', () => {
  const order = appSource.match(/const CAT_ORDER = \[([^\]]+)\]/)?.[1] || '';

  assert.match(order, /system_temp/);
  assert.doesNotMatch(order, /trash/);
  assert.match(appSource, /system_temp: '系统临时文件'/);
  assert.match(appSource, /system_temp: 'System Temporary Files'/);
});

test('trash-specific permanent deletion UI is removed', () => {
  assert.doesNotMatch(appSource, /confirmCleanTrash/);
  assert.doesNotMatch(appSource, /scan\.trash/);
  assert.doesNotMatch(appSource, /permTrashWarn/);
});

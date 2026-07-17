const assert = require('node:assert/strict');
const test = require('node:test');

const { diskSummary } = require('../../resources/ui/disk-presentation.js');

test('formats disk capacity using decimal GB like macOS', () => {
  const summary = diskSummary({
    total: 245_110_000_000,
    used: 209_720_000_000,
    free: 35_390_000_000,
    available: 38_230_000_000,
    reclaimable: 2_840_000_000,
  }, {
    available: '可用',
    reclaimable: '系统可清除',
  });

  assert.equal(summary.primary, '209.7 / 245.1 GB');
  assert.equal(summary.secondary, '可用 38.2 GB · 系统可清除 2.8 GB');
});

test('falls back to free capacity and omits an empty reclaimable label', () => {
  const summary = diskSummary({
    total: 100_000_000_000,
    used: 70_000_000_000,
    free: 30_000_000_000,
  }, {
    available: 'Available',
    reclaimable: 'Reclaimable',
  });

  assert.equal(summary.primary, '70.0 / 100.0 GB');
  assert.equal(summary.secondary, 'Available 30.0 GB');
});

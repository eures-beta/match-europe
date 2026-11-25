const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

// Execute the actual trusted workflow script, without checkout, token or network.
const workflow = fs.readFileSync(
  path.join(__dirname, '../../.github/workflows/preview-relay.yml'),
  'utf8',
);
const script = workflow
  .split('          script: |\n')[1]
  .split('\n')
  .map((line) => line.slice(12))
  .join('\n');

async function relay(outcomes, retryAfter = null) {
  const requests = [];
  const waits = [];
  const failures = [];
  const queue = [...outcomes];
  await vm.runInNewContext(`(async () => {${script}\n})()`, {
    process: { env: { DISPATCH_TOKEN: 'test-only' } },
    context: {
      payload: { workflow_run: { id: 123, path: '.github/workflows/preview-request.yml' } },
    },
    AbortSignal,
    fetch: async (url, options) => {
      requests.push({ url, options });
      const status = queue.shift();
      if (status === 'network') throw new Error('test-only');
      assert.ok(Number.isInteger(status), 'unexpected extra request');
      return { ok: status === 204, status, headers: { get: () => retryAfter } };
    },
    setTimeout: (resolve, ms) => {
      waits.push(ms);
      resolve();
    },
    core: {
      info() {},
      warning() {},
      setFailed(message) {
        failures.push(message);
      },
    },
  });
  return { requests, waits, failures };
}

test('500 then success retries the identical source signal after 10 seconds', async () => {
  const result = await relay([500, 204]);
  assert.deepEqual(result.waits, [10000]);
  assert.deepEqual(result.failures, []);
  assert.equal(result.requests.length, 2);
  assert.equal(result.requests[0].options.body, result.requests[1].options.body);
  assert.deepEqual(JSON.parse(result.requests[0].options.body), {
    ref: 'main',
    inputs: { source_run: '123' },
  });
});

test('network and server errors stop after four attempts with spaced delays', async () => {
  const result = await relay(['network', 502, 503, 504]);
  assert.deepEqual(result.waits, [10000, 30000, 60000]);
  assert.equal(result.requests.length, 4);
  assert.equal(result.failures.length, 1);
});

test('permanent failures are not retried', async () => {
  for (const status of [400, 401, 403, 404, 422]) {
    const result = await relay([status]);
    assert.equal(result.requests.length, 1);
    assert.deepEqual(result.waits, []);
    assert.equal(result.failures.length, 1);
  }
});

test('429 respects Retry-After within the bounded job', async () => {
  const result = await relay([429, 204], '45');
  assert.deepEqual(result.waits, [45000]);
  assert.deepEqual(result.failures, []);
});

test('long Retry-After fails explicitly instead of retrying too early', async () => {
  const result = await relay([429], '120');
  assert.deepEqual(result.waits, []);
  assert.equal(result.requests.length, 1);
  assert.equal(result.failures.length, 1);
});

test('immediate success does not wait or dispatch twice', async () => {
  const result = await relay([204]);
  assert.equal(result.requests.length, 1);
  assert.deepEqual(result.waits, []);
  assert.deepEqual(result.failures, []);
});

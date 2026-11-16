const assert = require('node:assert/strict');
const test = require('node:test');
const propose = require('../../.github/python-update.cjs');

function scenario({ same = false, existing = false, advanced = false } = {}) {
  const calls = [];
  const digest = `sha256:${'a'.repeat(64)}`;
  const method = (name, result) => async (input) => {
    calls.push([name, input]);
    if (name === 'getRef' && !existing) throw Object.assign(new Error('missing'), { status: 404 });
    return { data: typeof result === 'function' ? result(input) : result };
  };
  const github = {
    rest: {
      repos: {
        getCommit: method('getCommit', { sha: 'base', commit: { tree: { sha: 'base-tree' } } }),
        getContent: method('getContent', ({ path }) => ({
          content: Buffer.from(
            path === '.python-version'
              ? advanced
                ? '3.16.0'
                : same
                  ? '3.15.0'
                  : '3.14'
              : same
                ? digest
                : `sha256:${'b'.repeat(64)}`,
          ).toString('base64'),
        })),
      },
      git: {
        getRef: method('getRef', {}),
        createTree: method('createTree', { sha: 'tree' }),
        createCommit: method('createCommit', { sha: 'commit' }),
        createRef: method('createRef', {}),
      },
      pulls: {
        list: method('list', existing ? [{ number: 99, html_url: 'existing-pr' }] : []),
        create: method('create', { number: 99, html_url: 'new-pr' }),
        requestReviewers: method('review', {}),
      },
      issues: { addAssignees: method('assign', {}) },
      actions: { createWorkflowDispatch: method('dispatch', {}) },
    },
  };
  return {
    calls,
    run: () =>
      propose({
        github,
        context: { repo: { owner: 'test', repo: 'test' } },
        core: { info() {} },
        checkoutSha: 'base',
        readFile: (path) => (path === '.python-version' ? '3.15.0\n' : digest + '\n'),
      }),
  };
}

test('one atomic commit updates only the version and Docker lock, then dispatches validation', async () => {
  const { run, calls } = scenario();
  await run();
  assert.deepEqual(
    calls.find(([name]) => name === 'createTree')[1].tree.map(({ path }) => path),
    ['.python-version', '.python-image-digest'],
  );
  assert.deepEqual(calls.find(([name]) => name === 'createCommit')[1].parents, ['base']);
  assert.equal(calls.filter(([name]) => name === 'dispatch').length, 4);
  assert.equal(calls.find(([name]) => name === 'create')[1].base, 'main');
});

test('no update makes no branch, PR or validation run', async () => {
  const { run, calls } = scenario({ same: true });
  await run();
  assert.equal(
    calls.some(([name]) => ['create', 'createRef', 'dispatch'].includes(name)),
    false,
  );
});

test('existing proposal is never force-pushed or duplicated; failed validations can retry', async () => {
  const { run, calls } = scenario({ existing: true });
  await run();
  assert.equal(
    calls.some(([name]) => ['create', 'createRef', 'createCommit'].includes(name)),
    false,
  );
  assert.equal(calls.filter(([name]) => name === 'dispatch').length, 4);
});

test('a concurrent update of main cannot cause a downgrade', async () => {
  const { run, calls } = scenario({ advanced: true });
  await assert.rejects(run(), /refusing a downgrade/);
  assert.equal(
    calls.some(([name]) => name === 'createRef'),
    false,
  );
});

// Only the two runtime lock files can be published. No shell, force push or merge.
const fs = require('node:fs');
const { execFileSync } = require('node:child_process');

module.exports = async function propose({
  github,
  context,
  core,
  readFile = fs.readFileSync,
  checkoutSha = execFileSync('git', ['rev-parse', 'HEAD'], { encoding: 'utf8' }).trim(),
}) {
  const repo = context.repo;
  const files = ['.python-version', '.python-image-digest'];
  const version = readFile(files[0], 'utf8').trim();
  const digest = readFile(files[1], 'utf8').trim();
  if (!/^3\.\d+(\.\d+)?$/.test(version) || !/^sha256:[a-f0-9]{64}$/.test(digest)) {
    throw new Error('Invalid runtime lock files');
  }
  const { data: base } = await github.rest.repos.getCommit({ ...repo, ref: 'main' });
  if (base.sha !== checkoutSha) {
    throw new Error('Main advanced during the check; retry the workflow');
  }
  const previous = await github.rest.repos.getContent({
    ...repo,
    path: files[0],
    ref: base.sha,
  });
  const oldVersion = Buffer.from(previous.data.content, 'base64').toString().trim();
  const previousDigest = await github.rest.repos.getContent({
    ...repo,
    path: files[1],
    ref: base.sha,
  });
  const oldDigest = Buffer.from(previousDigest.data.content, 'base64').toString().trim();
  const compareVersions = (left, right) => {
    const a = left.split('.').map(Number);
    const b = right.split('.').map(Number);
    for (let i = 0; i < Math.max(a.length, b.length); i++) {
      const difference = (a[i] ?? 0) - (b[i] ?? 0);
      if (difference) return difference;
    }
    return 0;
  };
  if (compareVersions(version, oldVersion) < 0) {
    throw new Error('Main advanced during the check; refusing a downgrade');
  }
  if (version === oldVersion && digest === oldDigest) {
    core.info(`Python ${version}: no update`);
    return;
  }
  const branch = `automation/python-runtime-${version}-${digest.slice(7, 19)}`;
  let existing;
  try {
    existing = await github.rest.git.getRef({ ...repo, ref: `heads/${branch}` });
  } catch (error) {
    if (error.status !== 404) throw error;
  }
  if (!existing) {
    const { data: tree } = await github.rest.git.createTree({
      ...repo,
      base_tree: base.commit.tree.sha,
      tree: files.map((path) => ({
        path,
        mode: '100644',
        type: 'blob',
        content: readFile(path, 'utf8'),
      })),
    });
    const { data: commit } = await github.rest.git.createCommit({
      ...repo,
      message: `Mettre à jour Python vers ${version}`,
      tree: tree.sha,
      parents: [base.sha],
    });
    await github.rest.git.createRef({ ...repo, ref: `refs/heads/${branch}`, sha: commit.sha });
  }
  const { data: prs } = await github.rest.pulls.list({
    ...repo,
    state: 'open',
    head: `${repo.owner}:${branch}`,
  });
  let pr = prs[0];
  if (!pr) {
    const result = await github.rest.pulls.create({
      ...repo,
      base: 'main',
      head: branch,
      title: `Mettre à jour Python de ${oldVersion} vers ${version}`,
      body: [
        '## :busts_in_silhouette: Qui ?',
        'Équipe technique ; les utilisateurs conservent les mêmes parcours.',
        '## :sparkles: Quoi ?',
        `Une version stable de CPython est disponible : ${oldVersion} → ${version}.`,
        'La déclaration commune et son image Docker officielle verrouillée sont mises à jour ensemble.',
        '## :thinking: Pourquoi ?',
        'Maintenir le runtime Python et son image système sans vérification manuelle des versions.',
        '## :cake: Comment ?',
        'Une source commune alimente les installations, la CI et les tests Docker. Aucune fusion automatique.',
        '## :seedling: Quels modèles Django sont créés ?',
        'Aucun.',
        '## :hammer_and_wrench: Quels modèles Django sont modifiés ?',
        'Aucun ; aucune migration.',
        '## :floppy_disk: Quelles nouvelles données sont sauvegardées en base de données ?',
        'Aucune.',
        '## :new: Quelles applications Django sont créées ?',
        'Aucune.',
        '## :jigsaw: Quelles applications Django sont modifiées ?',
        'Aucune modification du code métier.',
        '## :desert_island: Comment tester ?',
        'Les contrôles habituels sont lancés explicitement sur cette branche : PostgreSQL, HTTP sous 256 Mio, qualité et traductions.',
        'Consulter leurs résultats avant fusion. Aucune fusion ni mise en production automatique.',
        '## :rotating_light: À vérifier',
        'Vérifier aussi la disponibilité de cette version chez Clever Cloud et sur les postes locaux.',
        'Sources : tags officiels python/cpython et image officielle library/python.',
      ].join('\n\n'),
    });
    pr = result.data;
    await github.rest.issues.addAssignees({
      ...repo,
      issue_number: pr.number,
      assignees: ['dejafait'],
    });
    await github.rest.pulls.requestReviewers({
      ...repo,
      pull_number: pr.number,
      reviewers: ['dejafait'],
    });
  }
  core.info(pr.html_url);
  // GITHUB_TOKEN pushes do not reliably start the normal push/PR workflows.
  // Explicit dispatches use the candidate branch and read-only validation jobs.
  for (const workflow_id of [
    'ready-for-production-check.yml',
    'black.yml',
    'templates.yml',
    'javascript.yml',
  ]) {
    await github.rest.actions.createWorkflowDispatch({ ...repo, workflow_id, ref: branch });
  }
};

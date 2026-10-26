// Screen 1 only. Reuse the employer shell and unchanged institutional assets.
const fs = require('node:fs');
const path = require('node:path');
const copy = require('./candidate-copy.json');
const escape = value => String(value).replace(/[&<>"']/g, char => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
}[char]));

for (const lang of ['fr', 'en', 'de']) {
  const t = copy[lang];
  let html = fs.readFileSync(path.join(__dirname, `${lang}.html`), 'utf8');
  const logos = html.match(/<div class="employer-partner-logos"[\s\S]*?\n    <\/div>/)[0];
  const choices = t.choices.map((label, index) => `
    <button class="import-choice" type="button" data-candidate-choice="${index}">
      <span class="choice-symbol" aria-hidden="true">${['CV', 'URL', 'Aa'][index]}</span>
      <span><strong>${escape(label)}</strong><span class="choice-description">${escape(t.descriptions[index])}</span></span>
      <span class="choice-arrow" aria-hidden="true">→</span>
    </button>`).join('');
  const main = `<main id="main-content" class="section candidate-landing-page">
    <div class="shell candidate-landing-layout">
      <article class="candidate-letter">
        ${logos}
        <div class="candidate-letter-head"><div class="kicker">${escape(t.kicker)}</div>
          <h1>${escape(t.title)}</h1><p class="lede">${escape(t.intro)}</p>
        </div>
        <div><h2 class="choice-heading">${escape(t.choiceTitle)}</h2><div class="entry-choices">${choices}</div></div>
        <p id="candidate-status" class="candidate-highlight" role="status" hidden
           data-selection-notice="${escape(t.selectionNotice)}" data-account-notice="${escape(t.accountNotice)}"></p>
      </article>
      <aside class="candidate-sidebar">
        <article class="surface-card candidate-info-card"><h2>${escape(t.nextTitle)}</h2>
          <ol>${t.nextSteps.map(step => `<li>${escape(step)}</li>`).join('')}</ol>
        </article>
        <article class="surface-card candidate-info-card"><h2>${escape(t.controlTitle)}</h2><p>${escape(t.controlText)}</p></article>
      </aside>
    </div>
  </main>`;
  html = html.replace(/<title>.*?<\/title>/, `<title>Match Europe — ${escape(t.kicker)}</title>`)
    .replace('</head>', '<link rel="stylesheet" href="candidate.css"></head>')
    .replace(/(<p class="preview-note" id="preview-note">).*?(<\/p>)/, `$1${escape(t.preview)}$2`)
    .replace(/<main[\s\S]*?<\/main>/, main)
    .replace('class="nav-pill is-active"', 'class="nav-pill"')
    .replace(`class="nav-pill" href="/forms/eures-beta/candidate?lang=${lang}"`,
      `class="nav-pill is-active" aria-current="page" href="candidate-${lang}.html"`)
    .replace(/(class="lang-link[^\"]*" href=")([a-z]{2})\.html/g, '$1candidate-$2.html')
    .replace(/<a class="nav-pill employer-account-link" data-employer-account[^>]*>([^<]*)<\/a>/,
      '<button type="button" class="nav-pill employer-account-link" data-candidate-account>$1</button>')
    .replace('</body>', '<script src="candidate.js" defer></script></body>');
  fs.writeFileSync(path.join(__dirname, `candidate-${lang}.html`), html);
}

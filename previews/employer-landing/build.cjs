// Preview only: reuse the existing template and CSS without changing application routes.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '../..');
const source = fs.readFileSync(path.join(root, 'forms/eures-beta/app.js'), 'utf8');
const pageUrlForFooter = (page, lang) => `/forms/eures-beta/${page}?lang=${lang}`;
const prequalification = JSON.parse(fs.readFileSync(path.join(__dirname, 'privacy-prequalification.json'), 'utf8'));
const drafts = JSON.parse(fs.readFileSync(path.join(__dirname, 'copy.json'), 'utf8'));
for (const lang of ['fr', 'en', 'de']) {
  const context = vm.createContext({ URLSearchParams, window: { location: { search: `?lang=${lang}` } } });
  vm.runInContext(source.replace(/render\(\);\s*$/, ''), context);
  context.draft = drafts[lang];
  context.lang = lang;
  let html = vm.runInContext(`(() => {
    const t = structuredCloneForPreview(copy[lang]);
    t.employerLanding = draft;
    t.common.ctaQuestionnaire = draft.cta;
    t.common.matchingTitle = draft.benefitsTitle;
    t.common.matchingBullets = draft.benefits;
    return employerLandingTemplate(lang, t);
  })()`, Object.assign(context, { structuredCloneForPreview: x => JSON.parse(JSON.stringify(x)) }));
  // Official supplied assets: preserve the full images, including their white margins.
  html = html.replace(/<div class="candidate-logos"[\s\S]*?(?=<div class="candidate-letter-head">)/, `
    <div class="employer-partner-logos" role="group" aria-label="${drafts[lang].partners}">
      <div class="employer-partner-logo employer-partner-eures"><img src="assets/eures-ela.jpg" alt="EURES / European Labour Authority" width="5956" height="2372"></div>
      <div class="employer-partner-logo employer-partner-ft"><img src="assets/france-travail.svg" alt="République française — France Travail" width="893" height="296"></div>
      <div class="employer-partner-logo employer-partner-adem"><img src="assets/adem.png" alt="ADEM — Agence pour le développement de l’emploi" width="591" height="591"></div>
      <div class="employer-partner-logo employer-partner-forem"><img src="assets/forem.png" alt="Le Forem" width="795" height="229"></div>
    </div>
    `);
  // Keep the next-steps card focused on the journey, without repeated partner tags.
  html = html.replace(/<div class="tag-row">[\s\S]*?<\/div>/, '');
  const action = html.match(/<div class="landing-actions">[\s\S]*?<\/div>/);
  if (!action) throw new Error('Employer landing action missing');
  html = html.replace(action[0], '').replace(
    /(<p class="lede">[\s\S]*?<\/p>)/,
    `$1\n${action[0]}`
  );
  html = html.replace('aria-label="Partners"', `aria-label="${drafts[lang].partners}"`)
    .replace('aria-label="Primary"', `aria-label="${drafts[lang].navigation}"`)
    .replace('<main class=', '<main id="main-content" class=')
    .replace(/<a class="primary-action"[^>]*>([^<]*)<\/a>/, `<a class="primary-action" href="import-${lang}.html">$1</a>`);
  const footerText = {
    fr: ['Match Europe · Une expérimentation France Travail / EURES / ADEM / Le Forem / ELA', 'Liens utiles'],
    en: ['Match Europe · A France Travail / EURES / ADEM / Le Forem / ELA experiment', 'Useful links'],
    de: ['Match Europe · Eine Erprobung von France Travail / EURES / ADEM / Le Forem / ELA', 'Weitere Links']
  }[lang];
  html = html.replace(/<footer class="footer">[\s\S]*?<\/footer>/, `
    <footer class="employer-preview-footer">
      <div class="shell employer-preview-footer-inner">
        <p>${footerText[0]}</p>
        <nav aria-label="${footerText[1]}">
          <a href="${pageUrlForFooter('le-projet', lang)}">${vm.runInContext('copy[lang].common.navProject', context)}</a>
          <a href="${pageUrlForFooter('journal', lang)}">${vm.runInContext('copy[lang].common.navJournal', context)}</a>
          <a href="privacy-${lang}.html">${vm.runInContext('privacyCopy[lang].navLabel', context)}</a>
        </nav>
      </div>
    </footer>`);
  // Extend the local notice with the agreed prequalification information.
  context.prequalification = prequalification[lang];
  vm.runInContext(`privacyCopy[lang].sections.splice(3, 0, [prequalification.aiTitle, prequalification.aiItems], [prequalification.title, prequalification.items]);`, context);
  // Existing legal facts are retained pending review for the new journey.
  const privacyNotice = vm.runInContext('privacyTemplate(lang, copy[lang])', context)
    .replace(/<footer class="footer">[\s\S]*?<\/footer>/, html.match(/<footer class="employer-preview-footer">[\s\S]*?<\/footer>/)[0])
    .replace(/href="\/forms\/eures-beta\/privacy\?lang=(fr|en|de)"/g, 'href="privacy-$1.html"')
    .replace(/href="\/forms\/eures-beta\/(?:employer)?\?lang=(fr|en|de)"/g, 'href="$1.html"');
  const noticeWarning = {
    fr: 'Notice existante du 3 août 2026 — à actualiser pour le parcours d’import d’offre. Copie locale, non validée pour ce nouveau parcours.',
    en: 'Existing notice dated 3 August 2026 — needs updating for the offer import journey. Local copy, not validated for this new journey.',
    de: 'Bestehender Hinweis vom 3. August 2026 — für den Angebotsimport zu aktualisieren. Lokale Kopie, für diesen neuen Ablauf nicht bestätigt.'
  }[lang];
  fs.writeFileSync(path.join(__dirname, `privacy-${lang}.html`), `<!doctype html><html lang="${lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>${vm.runInContext('privacyCopy[lang].navLabel', context)}</title><link rel="stylesheet" href="../../forms/eures-beta/site.css"></head><body><p class="shell" role="note">${noticeWarning}</p>${privacyNotice}</body></html>`);
  // Keep all navigation local to the static preview server, with working language switches.
  html = html.replace(/href="\/forms\/eures-beta\/employer\?lang=(fr|en|de)"/g, 'href="$1.html"');
  const accountLabel = {fr:'Me connecter', en:'Sign in', de:'Anmelden'}[lang];
  html = html.replace(/(<div class="lang-switch"[^>]*>[\s\S]*?<\/div>)/, `<div class="employer-header-actions">$1<a class="nav-pill employer-account-link" data-employer-account href="/employer/access/?lang=${lang}">${accountLabel}</a></div>`);
  html = html.replace('</header>', `<style>.site-header .employer-header-actions{display:flex;align-items:center;justify-content:flex-end;gap:.75rem;flex-wrap:wrap;margin-left:auto}.site-header .employer-header-actions .lang-switch{width:auto}.site-header .employer-account-link{display:inline-flex;align-items:center;justify-content:center;min-height:44px;box-sizing:border-box;white-space:nowrap;background:#d6e9ff;color:#003566;border-color:#8cb8e8;font-weight:700}.site-header .employer-account-link:hover{background:#c4dfff;border-color:#527faf}.employer-account-link:focus-visible{outline:3px solid var(--accent);outline-offset:3px}@media(max-width:700px){.site-header .employer-header-actions{width:100%;gap:.5rem;justify-content:space-between}}</style></header>`);
  fs.writeFileSync(path.join(__dirname, `${lang}.html`), `<!doctype html>
<html lang="${lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Match Europe — ${drafts[lang].kicker}</title>
<link rel="stylesheet" href="../../forms/eures-beta/site.css">
<style>.employer-partner-logos{display:grid;grid-template-columns:1.5fr 1.4fr 1fr 1fr;align-items:center;gap:24px;padding:20px;margin-bottom:24px;background:#fff;border:1px solid var(--line);border-radius:16px}.employer-partner-logo{display:flex;align-items:center;justify-content:center;min-width:0;padding:8px}.employer-partner-logo img{display:block;width:100%;height:auto;object-fit:contain}.employer-partner-forem img{max-width:110px}@media(max-width:700px){.employer-partner-logos{grid-template-columns:1fr 1fr;gap:12px 24px;padding:16px}.employer-partner-eures img{max-width:210px}.employer-partner-ft img{max-width:190px}.employer-partner-adem img{max-width:112px}.employer-partner-forem img{max-width:110px}}.employer-preview-footer{margin-top:32px;border-top:1px solid var(--line);padding:24px 0 32px;color:var(--muted);font-size:14px}.employer-preview-footer-inner{display:flex;flex-direction:column;align-items:flex-start;gap:14px}.employer-preview-footer-inner>p{max-width:100%;text-wrap:balance}.employer-preview-legal{margin-top:16px;padding-top:16px;border-top:1px solid var(--line)}.employer-preview-footer p{margin:0;line-height:1.6}.employer-preview-footer nav{display:flex;flex-wrap:wrap;gap:12px 24px}.employer-preview-footer a{color:inherit;text-decoration:underline;text-underline-offset:4px}.employer-preview-footer a:hover{color:var(--text)}.employer-preview-footer a:focus-visible{outline:2px solid var(--accent);outline-offset:4px}@media(max-width:640px){.employer-preview-footer-inner{align-items:flex-start;flex-direction:column}}.preview-note{margin:0;padding:12px 24px;background:#fff0bd;color:#17324d;text-align:center}.primary-action:disabled{cursor:default;opacity:1}.skip-preview{position:absolute;left:-10000px}.skip-preview:focus{left:12px;top:12px;background:white;padding:12px;z-index:100}</style>
</head><body><a class="skip-preview" href="#main-content">${drafts[lang].skip}</a><p class="preview-note" id="preview-note">${drafts[lang].preview}</p>${html}</body></html>\n`);
}
require('./build-import.cjs');

require('./build-candidate.cjs');

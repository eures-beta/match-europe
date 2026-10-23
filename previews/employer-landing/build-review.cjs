const translations = require('./review-copy.json');
const snapshot = require('./aglae-offer-snapshot.json');
const esc = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
module.exports = function buildReview(lang) {
  const t = translations[lang];
  const choices = values => Object.entries(values).map(([value,label]) => `<option value="${esc(value)}">${esc(label)}</option>`).join('');
  const fields = Object.entries(t.fields).map(([name,label]) => {
    let control;
    if (name === 'contractType') control = `<select id="review-${name}" name="${name}" required>${choices(t.contracts)}</select>`;
    else if (['description','desiredProfile'].includes(name)) control = `<textarea id="review-${name}" name="${name}" rows="5" maxlength="${name === 'description' ? 16000 : 4000}" ${name === 'description' ? 'required' : ''}></textarea>`;
    else control = `<input id="review-${name}" name="${name}" required maxlength="${{title:125,companyName:100,city:50}[name]}">`;
    return `<div class="review-field"><label for="review-${name}">${esc(label)}</label>${control}</div>`;
  }).join('');
  const clarifications = Object.entries(t.clarifications).map(([name,label]) => `<div class="review-field clarification-item" data-clarification="${name}"><label id="clarify-label-${name}" for="clarify-${name}">${esc(label)}</label><p id="clarify-hint-${name}" class="mini-note">${esc(t.clarificationHints[name])}</p><input id="clarify-${name}" name="clarify-${name}" maxlength="1000" aria-describedby="clarify-hint-${name}"></div>`).join('');
  const questions = t.questions.map((_,i) => `<fieldset class="review-question"><legend>${esc(t.questionLabel)} ${i+1}</legend><label class="review-check"><input type="checkbox" id="question-enabled-${i}"><span>${esc(t.include)}</span></label><label class="visually-hidden" for="question-text-${i}">${esc(t.questionLabel)} ${i+1}</label><textarea id="question-text-${i}" rows="2" maxlength="2000"></textarea><label class="review-check"><input type="checkbox" id="question-mandatory-${i}"><span>${esc(t.mandatory)}</span></label></fieldset>`).join('');
  const r=t.requirements;
  const checks = (name,options) => `<div class="mobility-options">${Object.entries(options).map(([value,label]) => `<label><input type="checkbox" name="${name}" value="${esc(value)}"><span>${esc(label)}</span></label>`).join('')}</div>`;
  const requirements = `<fieldset class="mobility-field"><legend>${esc(r.conditionsTitle)}</legend><p class="mini-note">${esc(r.conditionsHelp)}</p>${checks('workConditions',r.conditions)}</fieldset>
    <fieldset class="mobility-field"><legend>${esc(r.permitTitle)}</legend><div class="mobility-options">${Object.entries(r.permitChoices).filter(([value]) => value !== '').map(([value,label]) => `<label><input type="radio" name="permitRequired" value="${value}" ${value===''?'checked':''}><span>${esc(label)}</span></label>`).join('')}</div></fieldset>
    <div id="permit-details" hidden><fieldset class="mobility-field"><legend>${esc(r.permitsTitle)}</legend>${checks('permits',r.permits)}</fieldset><div id="permit-other-field" hidden><label for="permit-other">${esc(r.otherPermit)}</label><input id="permit-other" maxlength="500"></div></div>`;
  return `<section id="review-step" data-step class="surface-card import-card" hidden>
    <h1 tabindex="-1">${esc(t.title)}</h1>
    <p id="review-provenance" class="review-provenance"></p>
    <p class="mini-note">${esc(t.preview)}</p>
    <form id="review-form" novalidate>
      <h2>${esc(t.dataTitle)}</h2><div class="review-fields">${fields}</div>
      <h2>${esc(t.clarifyTitle)}</h2><p>${esc(t.clarifyIntro)}</p><section id="clarifications-known" hidden><h3>${esc(t.knownTitle)}</h3><div class="review-fields"></div></section><section id="clarifications-missing"><h3>${esc(t.missingTitle)}</h3><p class="mini-note">${esc(t.missingHint)}</p><div class="review-fields">${clarifications}</div></section>
      <div class="mobility-fields requirements-fields">${requirements}</div><h3>${esc(t.mobilityTitle)}</h3><div class="mobility-fields">${['crossBorder','relocation'].map(name => `<fieldset class="mobility-field"><legend>${esc(t[name])}</legend><div class="mobility-options">${Object.entries(t.choices).filter(([value]) => value !== '').map(([value,label],i) => `<label for="review-${name}-${i}"><input id="review-${name}-${i}" type="radio" name="${name}" value="${esc(value)}" ${value === '' ? 'checked' : ''}><span>${esc(label)}</span></label>`).join('')}</div></fieldset>`).join('')}</div>
      <fieldset class="mobility-field arrival-aids"><legend>${esc(r.aidsTitle)}</legend>${checks('arrivalAids',r.aids)}</fieldset><div id="aid-other-field" hidden><label for="aid-other">${esc(r.otherAid)}</label><input id="aid-other" maxlength="500"></div>
      <fieldset id="prequalification-section" hidden disabled><h2>${esc(t.questionsTitle)}</h2><button id="suggest-questions" type="button" class="ghost-action">${esc(r.suggest)}</button><p class="mini-note">${esc(r.suggestHelp)}</p><p>${esc(t.questionsIntro)}</p>${questions}
      <label for="question-custom">${esc(t.custom)}</label><textarea id="question-custom" rows="2" maxlength="2000"></textarea>
      </fieldset><section class="review-provenance review-privacy-compact"><h2>${esc(r.privacyTitle)}</h2><p>${esc(r.privacyText)}</p><p>${esc(r.privacyLocal)}</p><a href="privacy-${lang}.html">${esc(r.privacyLink)}</a></section>
      <label class="review-check review-confirm"><input type="checkbox" id="review-confirm"><span>${esc(t.confirmation)}</span></label>
      <p id="review-error" class="import-error" role="alert"></p><p id="review-status" role="status"></p>
      <div class="landing-actions"><button type="button" id="review-draft" class="ghost-action">${esc(t.draft)}</button><button type="submit" class="primary-action">${esc(t.validate)}</button></div>
      <button type="button" id="review-download" class="import-text-button" hidden>${esc(t.downloadValidated)}</button><br>
      <button type="button" id="review-back" class="import-text-button">${esc(t.back)}</button>
    </form>
    <script type="application/json" id="review-strings">${JSON.stringify(t).replace(/</g,'\\u003c')}</script>
    <script type="application/json" id="review-snapshot">${JSON.stringify(snapshot).replace(/</g,'\\u003c')}</script>
  </section>
  <section id="completion-step" data-step class="surface-card import-card" hidden>
    <h1 tabindex="-1">${esc(t.completion.title)}</h1><p class="lede">${esc(t.completion.intro)}</p>
    <h2>${esc(t.completion.nextTitle)}</h2><ol class="completion-next">${t.completion.steps.map(step=>`<li>${esc(step)}</li>`).join('')}</ol>
    <p class="review-provenance">${esc(t.completion.local)}</p>
    <details id="completed-offer"><summary>${esc(t.completion.view)}</summary><dl id="completed-offer-data"></dl></details>
    <div class="landing-actions"><a class="primary-action" href="${lang}.html" id="completion-home">${esc(t.completion.home)}</a><button type="button" class="ghost-action" id="completion-another">${esc(t.completion.another)}</button></div>
  </section>`;
};

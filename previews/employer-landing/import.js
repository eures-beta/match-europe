'use strict';
// Document reading uses the local API only when explicitly enabled.
const strings = JSON.parse(document.getElementById('import-strings').textContent);
const input = document.getElementById('offer-file');
const fileForm = document.getElementById('file-form');
const manualForm = document.getElementById('manual-form');
const urlForm = document.getElementById('url-form');
const emailForm = document.getElementById('email-form');
const error = document.getElementById('file-error');
const liveAPI = window.localEmployerAPI;
if (document.body.dataset.liveLocal === 'true' && !liveAPI) {
  throw new Error('Local API client unavailable; refusing simulated fallback.');
}
let validFile = false;
let selectionVersion = 0;
let previousStep = 'file-step';
let sourceToken = null;

// A changed source needs a new preparation agreement.
for (const id of ['offer-url', 'offer-text', 'offer-file']) {
  document.getElementById(id).addEventListener(id === 'offer-file' ? 'change' : 'input', () => {
    sourceToken = null;
  });
}

function showStep(id) {
  document.querySelector('.import-steps').hidden = id === 'completion-step';
  for (const el of document.querySelectorAll('[data-step]')) el.hidden = el.id !== id;
  const step = id === 'email-step' ? 2 : ['ready-step','review-step','prepare-step'].includes(id) ? 1 : 0;
  document.querySelectorAll('.import-steps li').forEach((el, index) => {
    if (index === step) el.setAttribute('aria-current', 'step');
    else el.removeAttribute('aria-current');
  });
  document.getElementById(id).querySelector('h1').focus();
  document.dispatchEvent(new CustomEvent('me-step-change',{detail:id}));
}

input.addEventListener('change', async () => {
  const version = ++selectionVersion;
  validFile = false;
  error.textContent = '';
  document.getElementById('selected-file').textContent = '';
  const files = [...input.files];
  if (!files.length) return;
  if (files.length > 8 || files.reduce((sum, file) => sum + file.size, 0) > 10 * 1024 * 1024) { error.textContent = strings.large; return; }
  if (files.some(file => !/\.(pdf|png|jpe?g)$/i.test(file.name)) || (files.length > 1 && files.some(file => /\.pdf$/i.test(file.name)))) { error.textContent = strings.invalid; return; }
  try {
    for (const file of files) {
      const header = new Uint8Array(await file.slice(0,8).arrayBuffer());
      const pdf = /\.pdf$/i.test(file.name) && String.fromCharCode(...header).startsWith('%PDF-');
      const png = /\.png$/i.test(file.name) && [137,80,78,71,13,10,26,10].every((value,index) => header[index] === value);
      const jpeg = /\.jpe?g$/i.test(file.name) && header[0] === 255 && header[1] === 216 && header[2] === 255;
      if (!pdf && !png && !jpeg) { error.textContent = strings.invalid; return; }
    }
    if (version !== selectionVersion) return;
    validFile = true;
    document.getElementById('selected-file').textContent = strings.selected + files.map(file => file.name).join(' → ');
  } catch {
    if (version === selectionVersion) error.textContent = strings.unreadable;
  }
});

fileForm.addEventListener('submit', async event => {
  event.preventDefault();
  if (!validFile) { error.textContent = strings.missing; input.focus(); return; }
  const button = fileForm.querySelector('[type=submit]');
  const version = selectionVersion;
  try {
    if (liveAPI) {
      button.disabled = true; button.textContent = strings.readingPdf;
      const data = new FormData(); data.set('kind','pdf');
      for (const file of input.files) data.append('document',file);
      data.set('agreement','true');
      const result = await liveAPI.request('source/',{method:'POST',body:data});
      if (version !== selectionVersion) return;
      sourceToken = result.token;
      window.meReview.loadLive(result);
    }
    error.textContent = '';
    previousStep = 'file-step';
    if (liveAPI) showStep('review-step');
    else { window.meReview.prepare(previousStep); showStep('review-step'); }
  } catch (exc) {
    error.textContent = strings.errorPrefix + (strings.errors[exc.code] || strings.errors.network);
  } finally { button.disabled = false; button.textContent = liveAPI ? strings.readPdf : strings.continue; }
});
document.getElementById('pdf-choice').addEventListener('click', () => showStep('file-step'));
document.getElementById('file-back').addEventListener('click', () => showStep('choice-step'));
document.getElementById('manual-choice').addEventListener('click', () => showStep('manual-step'));
document.getElementById('url-choice').addEventListener('click', () => showStep('url-step'));
document.getElementById('url-back').addEventListener('click', () => showStep('choice-step'));
urlForm.addEventListener('submit', async event => {
  event.preventDefault();
  const field = document.getElementById('offer-url');
  const errorBox = document.getElementById('url-error');errorBox.hidden = true;errorBox.replaceChildren();
  const button = urlForm.querySelector('[type=submit]');
  try {
    const url = new URL(field.value.trim());
    const host = url.hostname.toLowerCase().replace(/\.$/, '');
    // Preview validation only. Real fetching must also check DNS, redirects and size server-side.
    if (url.protocol !== 'https:' || url.username || url.password ||
        (url.port && url.port !== '443') || !host.includes('.') ||
        /^[\d.]+$/.test(host) || host.includes(':') ||
        /(^|\.)(localhost|local|internal|test|invalid|example|lan|home)$/.test(host)) throw new Error();
    document.getElementById('url-error').textContent = '';
    if (liveAPI) {
      if (!urlForm.reportValidity()) return;
      button.disabled = true; button.textContent = strings.readingUrl;
      const data = new FormData();data.set('url',field.value.trim());data.set('agreement','true');
      const result = await liveAPI.request('source/',{method:'POST',body:data});sourceToken = result.token;window.meReview.loadLive(result);
    }
    previousStep = 'url-step';
    if (liveAPI) showStep('review-step');
    else { window.meReview.prepare(previousStep); showStep('review-step'); }
  } catch (exc) {
    errorBox.hidden = false;errorBox.tabIndex = -1;
    const title = document.createElement('strong'); title.textContent = strings.urlErrorTitle;
    const explanation = document.createElement('p');explanation.textContent = exc.code ? (strings.errors[exc.code] || strings.errors.network) : strings.urlInvalid;
    const fallback = document.createElement('p');fallback.textContent = strings.urlFallback;
    errorBox.append(title,explanation,fallback);
    for (const [label,step] of [[strings.pdfChoice,'file-step'],[strings.textChoice,'manual-step']]) {
      const option=document.createElement('button');option.type='button';option.className='ghost-action';option.textContent=label;
      option.addEventListener('click',()=>showStep(step));errorBox.append(option);
    }
    errorBox.focus();
  } finally { button.disabled=false;button.textContent=liveAPI ? strings.readUrl : strings.continue; }
});
document.getElementById('manual-back').addEventListener('click', () => showStep('choice-step'));
manualForm.addEventListener('submit', async event => {
  event.preventDefault();
  const field = document.getElementById('offer-text');
  if (!field.value.trim()) {
    document.getElementById('manual-error').textContent = strings.emptyManual;
    field.focus(); return;
  }
  document.getElementById('manual-error').textContent = '';
  previousStep = 'manual-step';
  if (liveAPI) {
    const button=manualForm.querySelector('[type=submit]');button.disabled=true;
    try {
      const data=new FormData();data.set('kind','manual');data.set('text',field.value);data.set('agreement','true');
      const result=await liveAPI.request('source/',{method:'POST',body:data});sourceToken=result.token;window.meReview.loadLive(result);showStep('review-step');
    } catch(exc) { document.getElementById('manual-error').textContent=strings.errors[exc.code] || strings.errors.network; }
    finally {button.disabled=false;}
  } else { window.meReview.prepare(previousStep);showStep('review-step'); }
});
document.addEventListener('me-request-email',()=>showStep('email-step'));
document.getElementById('email-back').addEventListener('click', () => showStep('review-step'));
emailForm.addEventListener('submit', async event => {
  event.preventDefault();
  if (!emailForm.reportValidity()) return;
  if (liveAPI) {
    const message = document.getElementById('import-live-status');
    message.textContent = strings.busy;
    const button = emailForm.querySelector('[type=submit]'); button.disabled = true;
    const form = new FormData();
    form.set('contact', JSON.stringify(window.meContact.initial()));
    form.set('email', document.getElementById('work-email').value.trim());
    form.set('agreement', 'true');
    form.set('data',JSON.stringify(window.meReview.collect()));
    const kind = previousStep === 'url-step' ? 'url' : previousStep === 'manual-step' ? 'manual' : 'pdf';
    form.set('kind', kind);
    if (kind === 'url') { form.set('url', document.getElementById('offer-url').value.trim());form.set('sourceToken', sourceToken || ''); }
    if (kind === 'manual') form.set('text', document.getElementById('offer-text').value);
    if (kind === 'pdf') form.set('sourceToken', sourceToken || '');
    try {
      const result = await liveAPI.request('', {method:'POST',body:form});
      if (result.login_url) { window.location.assign(result.login_url); return; }
      window.meReview.loadLive(result); window.meReview.saved(); message.textContent = ''; showStep(window.meReview.stage || 'review-step');
    } catch (exc) { if (exc.data?.id) { window.meReview.loadLive(exc.data); showStep(window.meReview.stage || 'review-step'); } else message.textContent = strings.errorPrefix + (strings.errors[exc.code] || strings.errors.network); }
    finally { button.disabled = false; }
    return;
  }
  window.meReview.prepare(previousStep);
  showStep(window.meReview.stage || 'review-step');
});
document.addEventListener('me-review-open', () => showStep(window.meReview.stage || 'review-step'));
document.getElementById('review-back').addEventListener('click', () => showStep(previousStep));
document.getElementById('restart').addEventListener('click', () => {
  ++selectionVersion;
  window.meReview.reset();
  fileForm.reset(); manualForm.reset(); urlForm.reset(); emailForm.reset(); validFile = false;
  error.textContent = ''; document.getElementById('selected-file').textContent = '';
  document.getElementById('manual-error').textContent = '';
  document.getElementById('url-error').textContent = '';
  showStep('choice-step');
});
// Never place these values in sessionStorage, localStorage, URLs or analytics.
if (liveAPI) {
  input.accept = 'application/pdf,image/png,image/jpeg,.pdf,.png,.jpg,.jpeg';
  input.multiple = true;
  document.querySelector("#file-step h1").textContent = strings.documentChoice;
  document.querySelector("#file-step > p").textContent = strings.documentDescription;
  document.querySelector('label[for="offer-file"]').textContent = strings.documentLabel;
  document.getElementById('file-help').textContent = strings.documentHelp;
  document.querySelector('#pdf-choice strong').textContent = strings.documentChoice;
  document.querySelector('#pdf-choice .choice-description').textContent = strings.documentDescription;
  const requestedDraft = new URL(window.location.href).searchParams.get('offer');
  if (requestedDraft && /^[0-9a-f-]{36}$/i.test(requestedDraft)) {
    liveAPI.request(requestedDraft+'/').then(result=>{
      window.meReview.loadLive(result);showStep(window.meReview.stage || 'review-step');
    }).catch(()=>{ /* Session ownership remains enforced by the server. */ });
  }

  document.getElementById('preview-note').textContent = strings.livePreview;
  document.getElementById('email-help').textContent = strings.liveEmailHelp;
  document.getElementById('url-preview').textContent = strings.liveUrl;
  const pdfNote = document.createElement('p'); pdfNote.className = 'mini-note'; pdfNote.id = 'pdf-read-agreement-note'; pdfNote.textContent = strings.readPdfAgreement;
  fileForm.querySelector('.landing-actions').before(pdfNote);
  fileForm.querySelector('[type=submit]').textContent = strings.readPdf;
  fileForm.querySelector('[type=submit]').setAttribute('aria-describedby',pdfNote.id);
  document.getElementById('url-read-agreement-note').hidden = false;
  urlForm.querySelector('[type=submit]').setAttribute('aria-describedby','url-read-agreement-note');
  urlForm.querySelector('[type=submit]').textContent = strings.readUrl;
  document.getElementById('review-back').textContent = strings.back;
  const message = document.createElement('p'); message.id = 'import-live-status'; message.setAttribute('role','status');
  emailForm.append(message);
  const container = document.createElement('section'); container.id = 'saved-drafts';
  document.getElementById('choice-step').append(container);
  liveAPI.request('').then(result => {
    if (!result.drafts.length) return;
    const heading = document.createElement('h2'); heading.textContent = strings.draftsTitle; container.append(heading);
    for (const draft of result.drafts) {
      const button = document.createElement('button');button.type = 'button';button.className = 'import-text-button';button.textContent = draft.title || draft.id;
      button.addEventListener('click', async () => {
        try { window.meReview.loadLive(await liveAPI.request(draft.id+'/')); showStep(window.meReview.stage || 'review-step'); }
        catch (exc) { message.textContent = strings.errors[exc.code] || strings.errors.network; container.append(message); }
      });
      container.append(button,document.createElement('br'));
    }
  }).catch(() => {});
}

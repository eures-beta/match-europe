// UI review of a real, fixed sandbox response. No key, API call or automatic persistence.
(() => {
  const t = JSON.parse(document.getElementById('review-strings').textContent);
  const snapshot = JSON.parse(document.getElementById('review-snapshot').textContent);
  const form = document.getElementById('review-form');
  const status = document.getElementById('review-status');
  const error = document.getElementById('review-error');
  const confirm = document.getElementById('review-confirm');
  const downloadValidated = document.getElementById('review-download');
  let source = null;
  let validated = false;
  let preparedSignature = null;
  const api = window.offerImportAPI;
  let current = null;
  let busy = false;
  const canonical = value => {
    try { const url = new URL(value); return url.origin + url.pathname.replace(/\/$/, ''); }
    catch { return null; }
  };
  const field = name => document.getElementById('review-' + name);
  const questionInputs = i => ({enabled:document.getElementById(`question-enabled-${i}`), text:document.getElementById(`question-text-${i}`), mandatory:document.getElementById(`question-mandatory-${i}`)});
  function syncQuestion(i) {
    const q = questionInputs(i);
    q.text.disabled = q.mandatory.disabled = !q.enabled.checked;
    if (!q.enabled.checked) q.mandatory.checked = false;
  }
  function arrangeClarifications() {
    const known = document.querySelector('#clarifications-known > .review-fields');
    const missing = document.querySelector('#clarifications-missing > .review-fields');
    for (const name of Object.keys(t.clarifications)) {
      const input = document.getElementById('clarify-' + name);
      const item = input.closest('.clarification-item');
      // Unwrap previous display without replacing the original input or its value.
      const previous = item.querySelector('details');
      if (previous) { while (previous.childNodes.length > 1) item.append(previous.childNodes[1]); previous.remove(); }
      item.querySelector('.clarification-value')?.remove();
      if (input.value.trim()) {
        const value = document.createElement('p'); value.className = 'clarification-value'; value.textContent = input.value;
        const details = document.createElement('details');
        const summary = document.createElement('summary'); summary.textContent = t.editInformation + ' — ' + t.clarifications[name];
        details.append(summary, item.querySelector('.mini-note'), input);
        item.append(value, details); known.append(item);
      } else missing.append(item);
    }
    document.getElementById('clarifications-known').hidden = !known.children.length;
    document.getElementById('clarifications-missing').hidden = !missing.children.length;
  }
  const selected = name => [...form.querySelectorAll('input[name='+name+']:checked')].map(input=>input.value);
  function syncRequirements() {
    const yes=form.querySelector('[name=permitRequired]:checked')?.value === 'yes';
    document.getElementById('permit-details').hidden=!yes;
    document.getElementById('permit-other-field').hidden=!yes || !selected('permits').includes('other');
    document.getElementById('aid-other-field').hidden=!selected('arrivalAids').includes('other');
  }
  function loadRequirements(values) {
    const r=values.requirements || {};
    for (const name of ['workConditions','permits','arrivalAids']) {
      for(const input of form.querySelectorAll('input[name='+name+']')) input.checked=(r[name] || []).includes(input.value);
    }
    for(const input of form.querySelectorAll('[name=permitRequired]')) input.checked=input.value===(r.permitRequired || '');
    document.getElementById('permit-other').value=r.permitOther || '';
    document.getElementById('aid-other').value=r.aidOther || '';
    syncRequirements();
  }
  const suggestedQuestions=new Map();
  document.getElementById('suggest-questions').addEventListener('click',()=>{
    const r=t.requirements; const proposed=[...t.liveQuestions];
    const conditions=selected('workConditions').filter(v=>!['none','unknown'].includes(v)).map(v=>r.conditions[v]);
    const permits=selected('permits').map(v=>v==='other'?document.getElementById('permit-other').value:r.permits[v]).filter(Boolean);
    if(conditions.length) proposed[2]=r.questionConditions.replace('{items}',conditions.join(', '));
    if(form.querySelector('[name=permitRequired]:checked')?.value==='yes' && permits.length) proposed[1]=r.questionPermits.replace('{items}',permits.join(', '));
    if(selected('arrivalAids').some(v=>!['none','unknown'].includes(v))) proposed[3]=r.questionArrival;
    proposed.forEach((text,i)=>{
      const q=questionInputs(i);const previous=suggestedQuestions.get(i);
      if(!q.text.value || q.text.value===t.liveQuestions[i] || q.text.value===previous) {q.text.value=text;suggestedQuestions.set(i,text);}
    });
    invalidate();
  });
  function showCompletion(result) {
    const values=result.data;
    const list=document.getElementById('completed-offer-data');list.replaceChildren();
    function row(label,value) {
      if(!value) return;
      const term=document.createElement('dt');term.textContent=label;
      const definition=document.createElement('dd');definition.textContent=value;list.append(term,definition);
    }
    for(const [name,label] of Object.entries(t.fields)) row(label,name==='contractType'?t.contracts[values[name]]:values[name]);
    if(window.meOccupation) row(window.meOccupation.summaryLabel,window.meOccupation.summary(values.occupation));
    for(const [name,label] of Object.entries(t.clarifications)) row(label,values.clarifications?.[name]);
    for(const name of ['crossBorder','relocation']) if(values[name]) row(t[name],t.choices[values[name]]);
    const r=values.requirements || {};const labels=t.requirements;
    row(labels.conditionsTitle,(r.workConditions || []).map(v=>labels.conditions[v]).filter(Boolean).join(', '));
    if(r.permitRequired) row(labels.permitTitle,labels.permitChoices[r.permitRequired]);
    row(labels.permitsTitle,(r.permits || []).map(v=>v==='other'?r.permitOther:labels.permits[v]).filter(Boolean).join(', '));
    row(labels.aidsTitle,(r.arrivalAids || []).map(v=>v==='other'?r.aidOther:labels.aids[v]).filter(Boolean).join(', '));
    document.getElementById('completed-offer').open=false;
    window.meReview.stage='completion-step';
  }
  document.getElementById('completion-another').addEventListener('click',()=>{
    window.meReview.stage='choice-step';document.dispatchEvent(new Event('me-review-open'));
  });
  function collect(state) {
    const values = {};
    for (const name of Object.keys(t.fields)) values[name] = field(name).value.trim();
    if(window.meOccupation) values.occupation=window.meOccupation.collect();
    values.clarifications = {};
    for (const name of Object.keys(t.clarifications)) values.clarifications[name] = document.getElementById('clarify-' + name).value.trim();
    values.requirements={workConditions:selected('workConditions'),permitRequired:form.querySelector('[name=permitRequired]:checked')?.value || '',permits:[],permitOther:'',arrivalAids:selected('arrivalAids'),aidOther:selected('arrivalAids').includes('other')?document.getElementById('aid-other').value.trim():''};
    if(values.requirements.permitRequired==='yes') {values.requirements.permits=selected('permits');values.requirements.permitOther=selected('permits').includes('other')?document.getElementById('permit-other').value.trim():'';}
    values.crossBorder = form.querySelector('[name="crossBorder"]:checked')?.value || '';
    values.relocation = form.querySelector('[name="relocation"]:checked')?.value || '';
    // Temporarily hidden prequalification: preserve saved questions without adding any.
    values.questions = current?.data?.questions || [];
    return {schemaVersion:1, state, source, sandboxOfferId:source?.type === 'sandbox-snapshot' ? snapshot.id : null,
      active:false, confirmed:state === 'validated', ...values};
  }
  function download(state) {
    const blob = new Blob([JSON.stringify(collect(state), null, 2)], {type:'application/json'});
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url; link.download = `match-europe-offer-${state}.json`; link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  function invalidate() {
    if (validated || confirm.checked) {
      confirm.checked = false; status.textContent = t.changed;
    }
    validated = false; downloadValidated.hidden = true; error.textContent = '';

  }
  // Keep edits on back/forward navigation when the source has not changed.
  window.meReview = {
    stage: 'review-step',
    collect: () => collect('draft'),
    saved() { status.textContent=t.localSaved; },
    isPending: () => Boolean(current && !current.id),
    setContact(result) { current.contact = result.contact; current.revision = result.revision; },
    loadLive(result) {
      window.meContact?.load(result);
      current = result;
      const pending=!result.id;
      const draft=document.getElementById('review-draft');
      draft.textContent=pending ? t.localSave : t.liveDraft;
      draft.className=pending ? 'primary-action' : 'ghost-action';
      form.querySelector('[type=submit]').hidden=pending;
      confirm.closest('label').hidden=pending;
      document.querySelector('#review-step > .mini-note').textContent=result.localOnly ? t.localReaderNote : t.liveNote;
      if(result.localOnly) {
        const privacy=document.querySelector('.review-privacy-compact');
        if(privacy) {
          const paragraphs=privacy.querySelectorAll('p');
          paragraphs[paragraphs.length-1].textContent=t.localPrivacy;
        }
      }
      form.reset(); status.textContent = ''; error.textContent = ''; downloadValidated.hidden = true;
      if(result.synced) { showCompletion(result); return; }
      this.stage = result.stage === 'prepare' ? 'prepare-step' : 'review-step';
      document.querySelectorAll('.document-warnings').forEach(node => node.remove());
      if (result.data.extractionWarnings?.length) {
        const box = document.createElement('section'); box.className = 'document-warnings'; box.setAttribute('role','status');
        const heading = document.createElement('h2'); heading.textContent = t.documentWarnings.title; box.append(heading);
        const list = document.createElement('ul');
        for (const warning of result.data.extractionWarnings) {
          const item = document.createElement('li');
          item.textContent = (t.documentWarnings[warning.field] || t.documentWarnings.other) + (warning.values.length ? ' : ' + warning.values.join(' / ') : '');
          list.append(item);
        }
        box.append(list);
        document.getElementById(this.stage).querySelector('h1').after(box);
      }
      if (this.stage === 'prepare-step') {
        for (const name of ['title','companyName','city','description']) document.getElementById('prepare-'+name).value=result.data[name] || '';
        document.getElementById('prepare-error').textContent=result.error ? (t.errors[result.error] || t.errors.sandbox_error) : '';
        return;
      }
      const values = result.data;
      suggestedQuestions.clear(); loadRequirements(values);
      for (const name of Object.keys(t.fields)) field(name).value = values[name] || '';
      window.meOccupation?.load(values.occupation);
      for (const name of Object.keys(t.clarifications)) document.getElementById('clarify-'+name).value = values.clarifications?.[name] || '';
      arrangeClarifications();
      for (const name of ['crossBorder','relocation']) {
        for (const radio of form.querySelectorAll('input[type=radio][name='+name+']')) radio.checked = radio.value === (values[name] || '');
      }
      t.questions.forEach((_,i) => {
        const q = questionInputs(i); const saved = values.questions?.[i];
        q.text.value = saved?.question || t.liveQuestions[i]; q.enabled.checked = Boolean(saved); q.mandatory.checked = Boolean(saved?.mandatory);syncQuestion(i);
      });
      document.getElementById('question-custom').value = values.questions?.[5]?.question || '';
      document.getElementById('review-provenance').textContent = (result.localOnly ? t.localReaderOrigin : t.liveOrigin) + (result.source ? ' '+result.source : '');
      document.getElementById('review-provenance').style.overflowWrap = 'anywhere';
      if (result.synced) status.textContent = t.liveSynced;
      showGeo(); showResponse();
    },
    prepare(mode) {
      const raw = mode === 'url-step' ? document.getElementById('offer-url').value.trim()
        : mode === 'manual-step' ? document.getElementById('offer-text').value
        : '';
      const file = document.getElementById('offer-file').files[0];
      const signature = JSON.stringify([mode,raw,file?.name,file?.size,file?.lastModified]);
      if (signature === preparedSignature) return;
      preparedSignature = signature;
      form.reset(); validated = false; status.textContent = ''; error.textContent = ''; downloadValidated.hidden = true;
      const usesSnapshot = mode === 'url-step' && canonical(raw) === canonical(snapshot.sourceUrl);
      source = usesSnapshot ? {type:'sandbox-snapshot', url:snapshot.sourceUrl, retrievedAt:snapshot.retrievedAt, approximateLocation:true}
        : {type:mode === 'url-step' ? 'url-unread' : mode === 'manual-step' ? 'manual' : 'pdf-unread'};
      document.getElementById('review-provenance').textContent = usesSnapshot ? t.snapshot : t.blank;
      for (const name of Object.keys(t.fields)) field(name).value = usesSnapshot ? (name === 'city' ? snapshot.workplaceLocation.city : snapshot[name] || '') : '';
      if (mode === 'manual-step') field('description').value = raw.slice(0,16000);
      window.meOccupation?.load();
      arrangeClarifications();
      t.questions.forEach((question,i) => {
        const q = questionInputs(i); q.text.value = usesSnapshot ? question : ''; q.enabled.checked = false; q.mandatory.checked = false; syncQuestion(i);
      });
    },
    reset() { current = null; preparedSignature = null; form.reset(); window.meOccupation?.reset(); validated = false; downloadValidated.hidden = true; }
  };
  form.addEventListener('input', event => {
    const item = event.target.closest('.clarification-item');
    if (item?.querySelector('.clarification-value')) item.querySelector('.clarification-value').textContent = event.target.value;
    if (event.target !== confirm) invalidate();
  });
  form.addEventListener('change', event => {
    const input=event.target;
    if(['workConditions','arrivalAids'].includes(input.name) && input.checked) {
      for(const other of form.querySelectorAll('input[name='+input.name+']')) {
        if(other!==input && (['none','unknown'].includes(input.value) || ['none','unknown'].includes(other.value))) other.checked=false;
      }
    }
    syncRequirements();
    if (event.target !== confirm) invalidate();
    if(event.target === field('city')) showGeo();
    t.questions.forEach((_,i) => syncQuestion(i));
  });
  t.errors.occupation_required=JSON.parse(document.getElementById('occupation-strings')?.textContent || '{}').required;
  async function liveAction(action) {
    if (busy || !current) return;
    if (!current.id) { document.dispatchEvent(new Event('me-request-email'));return; }
    busy = true;
    const controls = [...form.querySelectorAll('button')]; controls.forEach(b => b.disabled = true);
    status.textContent = action === 'validate' ? t.syncBusy : t.saveBusy; error.textContent = '';
    try {
      const result = await api.update(current.id,{action,revision:current.revision,data:collect('draft'),confirmed:confirm.checked});
      current = result; showGeo();showResponse();
      status.textContent = action === 'validate' ? t.liveSynced : t.liveSaved;
      if (action === 'validate' && result.synced) {
        confirm.checked = false;showCompletion(result);document.dispatchEvent(new Event('me-review-open'));
      }
    } catch (exc) {
      if (exc.data?.revision) current.revision = exc.data.revision;
      error.textContent = t.errors[exc.code] || t.errors.network; status.textContent = '';
    } finally { busy = false; controls.forEach(b => b.disabled = false); }
  }
  document.getElementById('review-draft').addEventListener('click', () => {
    if (api) return liveAction('save');
    download('draft'); status.textContent = t.draftSaved;
  });
  form.addEventListener('submit', async event => {
    event.preventDefault();
    const emptyQuestion = -1; // Prequalification section is temporarily disabled.
    const missing = ['title','companyName','city','contractType','description'].find(name => !field(name).value.trim());
    if (missing || emptyQuestion >= 0 || !confirm.checked || !form.checkValidity()) {
      error.textContent = t.required;
      if (missing) field(missing).focus(); else if (emptyQuestion >= 0) questionInputs(emptyQuestion).text.focus(); else if (!confirm.checked) confirm.focus(); else form.reportValidity();
      return;
    }
    if(window.meOccupation && !window.meOccupation.validate()) return;
    if (api) { await liveAction('validate'); return; }
    error.textContent = ''; validated = true; status.textContent = t.validated; downloadValidated.hidden = false;
  });
  downloadValidated.addEventListener('click', () => { if (validated && confirm.checked) download('validated'); });
  function showGeo() {
    if (!api) return;
    const candidate = current?.data?.geo;
    const point = candidate?.query === field('city').value.trim() ? candidate : null;
    const container = document.getElementById('location-result'); container.replaceChildren();
    const city=field('city').value.trim();
    if (!city) return;
    const link=document.createElement('a');link.className='ghost-action';
    link.href=point ? `https://www.openstreetmap.org/?mlat=${encodeURIComponent(point.latitude)}&mlon=${encodeURIComponent(point.longitude)}#map=16/${point.latitude}/${point.longitude}` : `https://www.openstreetmap.org/search?query=${encodeURIComponent(city)}`;
    link.target='_blank';link.rel='noopener noreferrer';link.textContent=t.map;container.append(link);
    const attribution=document.createElement('p');attribution.className='mini-note';attribution.textContent=point?.attribution || '© OpenStreetMap contributors';container.append(attribution);
  }
  function showResponse() {}
  if (api) {
    const prepare=document.createElement('section');prepare.id='prepare-step';prepare.dataset.step='';prepare.className='surface-card import-card';prepare.hidden=true;
    const heading=document.createElement('h1');heading.tabIndex=-1;heading.textContent=t.prepareTitle;
    const intro=document.createElement('p');intro.textContent=t.prepareIntro;
    const preparation=document.createElement('form');
    for (const name of ['title','companyName','city','description']) {
      const label=document.createElement('label');label.htmlFor='prepare-'+name;label.textContent=t.fields[name];
      const input=document.createElement(name === 'description' ? 'textarea' : 'input');input.id='prepare-'+name;input.required=true;
      input.maxLength={title:125,companyName:100,city:150,description:16000}[name];preparation.append(label,input);
    }
    const failure=document.createElement('p');failure.id='prepare-error';failure.className='import-error';failure.setAttribute('role','alert');
    const send=document.createElement('button');send.type='submit';send.className='primary-action';send.textContent=t.prepareButton;
    preparation.append(failure,send);prepare.append(heading,intro,preparation);document.querySelector('.import-shell').append(prepare);
    preparation.addEventListener('submit',async event => {
      event.preventDefault();if (!preparation.reportValidity()) return;
      send.disabled=true;failure.textContent=t.syncBusy;
      const data={...current.data};for (const name of ['title','companyName','city','description']) data[name]=document.getElementById('prepare-'+name).value.trim();
      try {
        const result=await api.update(current.id,{action:'prepare',revision:current.revision,data});
        window.meReview.loadLive(result);document.dispatchEvent(new Event('me-review-open'));
      } catch(exc) {
        if (exc.data?.revision) current.revision=exc.data.revision;
        failure.textContent=t.errors[exc.code] || t.errors.network;
      } finally {send.disabled=false;}
    });
    document.getElementById('review-draft').textContent = t.liveDraft;
    form.querySelector('[type=submit]').textContent = t.liveValidate;
    document.querySelector('#review-step > .mini-note').textContent = t.liveNote;
    confirm.nextElementSibling.textContent = t.liveConfirmation;
    const geo=document.createElement('div');geo.className='review-provenance';
    const notice=document.createElement('p');notice.textContent=t.geocodeNotice;geo.append(notice);
    const result=document.createElement('div');result.id='location-result';geo.append(result);
    field('city').parentElement.append(geo);

  }
})();

// Shared local catalogue, explicit employer choices, no external request.
(() => {
  const strings = document.getElementById('occupation-strings');
  if (!strings) return;
  const t = JSON.parse(strings.textContent);
  const title = document.getElementById('review-title');
  const lang = document.documentElement.lang;
  const form = document.getElementById('review-form');
  const node = (tag, text, parent) => { const el=document.createElement(tag); if(text) el.textContent=text; if(parent) parent.append(el); return el; };
  const box=node('section'); box.className='occupation-picker'; box.style.gridColumn='1 / -1';
  title.closest('.review-field').after(box);
  box.setAttribute('aria-label',t.proposals);
  const feedback=node('div','',box); feedback.className='occupation-feedback';
  const error=node('p','',feedback); error.id='occupation-error'; error.setAttribute('role','alert'); error.className='import-error';
  const retry=node('button',t.retry,feedback);retry.type='button';retry.className='ghost-action occupation-change';retry.hidden=true;
  const fallback=node('section','',box); fallback.hidden=true;
  const fallbackIntro=node('p',t.manualIntro,fallback);
  const queryLabel=node('label',t.conciseQuery,fallback); queryLabel.htmlFor='occupation-query';
  const query=node('input','',fallback); query.id='occupation-query'; query.type='text'; query.maxLength=150; query.autocomplete='off';query.placeholder=t.searchExample; query.setAttribute('aria-describedby','occupation-query-help occupation-error'); query.setAttribute('aria-controls','occupation-results'); query.style.width='100%';
  const help=node('p',t.conciseHelp,fallback); help.id='occupation-query-help';
  const status=node('p','',box); status.setAttribute('role','status');
  node('p',t.independentHelp,box);
  const list=node('div','',box); list.id='occupation-results';
  const near=node('button',t.near,box); near.type='button'; near.className='ghost-action occupation-change'; near.hidden=true;
  const custom=node('div','',box); custom.hidden=true;
  node('p',t.personalHelp,custom);
  const label=node('label',t.personal,custom); label.htmlFor='occupation-personal';
  const personal=node('textarea','',custom); personal.id='occupation-personal'; personal.maxLength=2000; personal.rows=3;
  let version='1.2.1', searchedTitle='', cards=[], choices=new Set(), offered=[], serial=0, timer=null, controller=null, fromDocument=false;
  let romeCards=[], romeChoices=new Set();
  function render() {
    list.replaceChildren();
    node('h3',t.escoHeading,list);
    for(const selected of [true,false]) {
      const groupCards=cards.filter(job=>choices.has(job.uri)===selected);
      if(!groupCards.length) continue;
      const group=node('section','',list);node('h4',selected?t.saved:t.proposals,group);
    for(const job of groupCards) {
      const article=node('article','',group); article.className='review-question';
      const label=node('label','',article); label.className='review-check';
      const check=node('input','',label); check.type='checkbox'; check.value=job.uri; check.checked=choices.has(job.uri);
      const text=node('span','',label); node('strong',job.label,text); node('span',job.description,text).style.display='block';
      check.addEventListener('change',()=>{ if(check.checked) choices.add(job.uri); else choices.delete(job.uri); error.textContent=''; });
      const details=node('details','',article); node('summary',t.escoReference,details);
      const link=node('a','ESCO — '+job.label,details); link.href='https://esco.ec.europa.eu/en/classification/occupation?uri='+encodeURIComponent(job.uri); link.target='_blank'; link.rel='noopener noreferrer';
      node('p',job.esco_code,details);

    }
    }
    if(!cards.length) node('p',t.noEsco,list);
    node('h3',t.romeHeading,list);
    node('p',t.romeHelp,list);
    if(!romeCards.length) node('p',t.noRomeResult,list);
    for(const job of romeCards) {
      const article=node('article','',list); article.className='review-question';article.lang='fr';
      const label=node('label','',article); label.className='review-check';
      const check=node('input','',label);check.type='checkbox';check.checked=romeChoices.has(job.code);
      node('strong',`ROME ${job.code} — ${job.label}`,label);
      check.addEventListener('change',()=>{if(check.checked)romeChoices.add(job.code);else romeChoices.delete(job.code);error.textContent='';});
      if(job.matched_labels?.length) node('p',job.matched_labels.join(' · '),article);
    }
  }
  function cancel() { clearTimeout(timer); controller?.abort(); serial++;near.disabled=false; }
  function clear() { cancel();retry.hidden=true;romeCards=[];romeChoices=new Set(); searchedTitle=''; cards=[];choices=new Set();offered=[];personal.value='';custom.hidden=true;near.hidden=true;list.replaceChildren();error.textContent=''; }
  function manual(message=t.manualIntro,focus=false) { fallback.hidden=false;fallbackIntro.textContent=message;fallbackIntro.hidden=message===t.manualHelp;if(focus) query.focus(); }
  async function find(mode='search',useContext=false,fromTitle=false) {
    clearTimeout(timer);
    const q=(fromTitle?title.value:query.value).trim();
    if(!q) {manual(t.manualHelp);status.textContent='';return;}
    cancel(); const request=serial; const boundTitle=title.value.trim(); controller=new AbortController();
    if(mode==='near') { offered=[...new Set([...offered,...cards.map(row=>row.uri)])]; }
    else {offered=[];}
    status.textContent=t.busy; status.className=''; error.textContent='';retry.hidden=true;
    try {
      const context=useContext?[document.getElementById('review-description').value,document.getElementById('review-desiredProfile').value].join('\n').slice(0,20000):'';
      const csrf=document.cookie.split('; ').find(value=>value.startsWith('csrftoken='))?.split('=')[1] || '';
      const response=await fetch('/api/occupations/',{method:'POST',credentials:'same-origin',signal:controller.signal,headers:{'Content-Type':'application/json','X-CSRFToken':csrf},body:JSON.stringify({q,lang,mode,excluded:offered,context,independent:true})});
      if(!response.ok) throw new Error('catalogue');
      const result=await response.json();
      if(request!==serial || title.value.trim()!==boundTitle) return;
      version=result.version;searchedTitle=boundTitle;
      const retainedRome=romeCards.filter(row=>romeChoices.has(row.code));
      romeCards=[...retainedRome,...(result.rome_results || []).filter(row=>!retainedRome.some(old=>old.code===row.code))];
      const retained=cards.filter(row=>choices.has(row.uri));
      cards=[...retained,...result.results.filter(row=>!retained.some(old=>old.uri===row.uri))];render();
      if(fromTitle && !result.results.length && !result.rome_results?.length) manual(fromDocument?t.automaticFailure:t.manualIntro);
      if(!fromTitle) fallbackIntro.hidden=true;
      const count=result.results.length+(result.rome_results || []).length;
      status.textContent=count?t.resultsFound.replace('{count}',String(count)):(fromTitle?'':t.empty);
      status.className=count?'visually-hidden':'';
      if(result.total>result.results.length) status.textContent+=' '+t.limited;
      custom.hidden=(fromTitle || result.results.length>0 || result.rome_results?.length>0) && !personal.value;
      near.hidden=mode==='near' || (!result.results.length && !result.rome_results?.length);
    } catch(exc) { if(request===serial && exc.name!=='AbortError') {manual(t.manualHelp);status.textContent='';error.textContent=t.searchFailed;retry.hidden=false;} }
  }
  function schedule(mode) {
    cancel();fallbackIntro.hidden=true;status.className='visually-hidden';cards=cards.filter(row=>choices.has(row.uri));render();near.hidden=true;
    const q=(query.value).trim();
    if(q.length<2) {status.textContent=t.startTyping;return;}
    status.textContent=t.busy;timer=setTimeout(()=>find(mode),300);
  }
  retry.addEventListener('click',()=>find('search',true,true));
  query.addEventListener('input',()=>schedule('search'));
  query.addEventListener('keydown',event=>{if(event.key==='Enter'){event.preventDefault();find();}});
  near.addEventListener('click',()=>{manual(t.manualHelp,true);status.textContent='';cards=cards.filter(row=>choices.has(row.uri));render();near.hidden=true;});
  personal.addEventListener('input',()=>{searchedTitle=title.value.trim();error.textContent='';});
  title.addEventListener('input',()=>{clear();fallback.hidden=true;query.value='';status.textContent=t.busy;timer=setTimeout(()=>find('search',true,true),300);});
  window.meOccupation={
    load(value,detected=false) {
      fromDocument=detected;
      clear();fallback.hidden=true;query.value='';status.textContent='';
      document.querySelector('label[for=review-title]').textContent=detected?t.detectedTitle:t.ownTitle;
      if(value && value.title===title.value.trim()) {
        version=value.version;searchedTitle=value.title;choices=new Set(value.uris || []);cards=value.jobs || [];romeCards=value.rome_jobs || [];romeChoices=new Set(value.rome_codes || []);personal.value=value.personal || '';custom.hidden=!personal.value;render();
      }
      find('search',true,true);
    },
    reset:clear,
    collect() { return {version,title:title.value.trim(),language:lang,rome_codes:searchedTitle===title.value.trim()?[...romeChoices]:[],uris:searchedTitle===title.value.trim()?[...choices]:[],personal:searchedTitle===title.value.trim()?personal.value.trim():''}; },
    validate() {
      const value=this.collect();
      if(!value.uris.length && !value.rome_codes.length && !value.personal) {error.textContent=t.required;box.scrollIntoView({block:'center'});if(fallback.hidden){near.focus();}else{query.focus();}return false;}return true;
    },
    summary(value) { return [...(value?.jobs || cards.filter(job=>(value?.uris || []).includes(job.uri))).map(job=>'ESCO — '+job.label+' — '+job.description),...(value?.rome_jobs || romeCards.filter(job=>(value?.rome_codes || []).includes(job.code))).map(job=>'ROME '+job.code+' — '+job.label),value?.personal].filter(Boolean).join('\n\n'); },
    summaryLabel:t.saved,
  };
})();

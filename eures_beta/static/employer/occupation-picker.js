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
  const heading=node('h3',t.heading,box); heading.id='occupation-heading'; box.setAttribute('aria-labelledby',heading.id);
  const intro=node('p',t.intro,box);heading.hidden=intro.hidden=true;
  const fallback=node('section','',box); fallback.hidden=true;
  const fallbackIntro=node('p',t.manualIntro,fallback);
  const queryLabel=node('label',t.manualQuery,fallback); queryLabel.htmlFor='occupation-query';
  const query=node('input','',fallback); query.id='occupation-query'; query.type='text'; query.maxLength=150; query.autocomplete='off'; query.setAttribute('aria-describedby','occupation-query-help'); query.setAttribute('aria-controls','occupation-results'); query.style.width='100%';
  const help=node('p',t.queryHelp,fallback); help.id='occupation-query-help';
  const codeDetails=node('details','',fallback); node('summary',t.codeDetails,codeDetails);
  const codeLabel=node('label',t.codeLabel,codeDetails); codeLabel.htmlFor='occupation-code';
  const code=node('input','',codeDetails); code.id='occupation-code'; code.type='text'; code.maxLength=150; code.autocomplete='off'; code.setAttribute('aria-describedby','occupation-code-help');
  const codeHelp=node('p',t.codeHelp,codeDetails); codeHelp.id='occupation-code-help';
  const search=node('button',t.search,fallback); search.type='button'; search.className='ghost-action';
  const status=node('p','',box); status.setAttribute('role','status');
  const list=node('div','',box); list.id='occupation-results';
  const near=node('button',t.near,box); near.type='button'; near.className='import-text-button'; near.hidden=true;
  const custom=node('div','',box); custom.hidden=true;
  node('p',t.personalHelp,custom);
  const label=node('label',t.personal,custom); label.htmlFor='occupation-personal';
  const personal=node('textarea','',custom); personal.id='occupation-personal'; personal.maxLength=2000; personal.rows=3;
  const error=node('p','',box); error.setAttribute('role','alert'); error.className='import-error';
  let version='1.2.1', searchedTitle='', cards=[], choices=new Set(), offered=[], serial=0, timer=null, controller=null;
  function render() {
    list.replaceChildren();
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
      const details=node('details','',article); node('summary',t.references,details);
      const link=node('a','ESCO — '+job.label,details); link.href='https://esco.ec.europa.eu/en/classification/occupation?uri='+encodeURIComponent(job.uri); link.target='_blank'; link.rel='noopener noreferrer';
      node('p',[job.esco_code,job.reference].filter(Boolean).join(' · '),details);
      const refs=node('ul','',details);
      for(const fiche of job.rome_fiches || []) node('li','ROME '+fiche.code+' — '+fiche.label,refs);
      if(!job.rome_fiches?.length) node('p',t.noRome,details);
      for(const match of job.rome || []) node('p',`ROME ${match.id} — ${match.label} · ${match.relation}`,details);
      node('p',t.versions,details);
    }
    }
  }
  function cancel() { clearTimeout(timer); controller?.abort(); serial++; search.disabled=near.disabled=false; }
  function clear() { cancel(); searchedTitle=''; cards=[];choices=new Set();offered=[];personal.value='';custom.hidden=true;near.hidden=true;list.replaceChildren();error.textContent=''; }
  function manual(message=t.manualIntro,focus=false) { fallback.hidden=false;fallbackIntro.textContent=message;if(focus) query.focus(); }
  async function find(mode='search',useContext=false,fromTitle=false) {
    clearTimeout(timer);
    const q=(fromTitle?title.value:mode==='reference'?code.value:query.value).trim();
    if(!q) {manual(t.manualHelp);status.textContent='';return;}
    cancel(); const request=serial; const boundTitle=title.value.trim(); controller=new AbortController();
    if(mode==='near') { offered=[...new Set([...offered,...cards.map(row=>row.uri)])]; }
    else {offered=[];}
    status.textContent=t.busy; error.textContent='';
    try {
      const context=useContext?[document.getElementById('review-description').value,document.getElementById('review-desiredProfile').value].join('\n').slice(0,20000):'';
      const csrf=document.cookie.split('; ').find(value=>value.startsWith('csrftoken='))?.split('=')[1] || '';
      const response=await fetch('/api/occupations/',{method:'POST',credentials:'same-origin',signal:controller.signal,headers:{'Content-Type':'application/json','X-CSRFToken':csrf},body:JSON.stringify({q,lang,mode,excluded:offered,context})});
      if(!response.ok) throw new Error('catalogue');
      const result=await response.json();
      if(request!==serial || title.value.trim()!==boundTitle) return;
      version=result.version;searchedTitle=boundTitle;
      const retained=cards.filter(row=>choices.has(row.uri));
      cards=[...retained,...result.results.filter(row=>!retained.some(old=>old.uri===row.uri))];render();heading.hidden=intro.hidden=!cards.length;
      if(fromTitle && !result.results.length) manual();
      if(!fromTitle) fallbackIntro.textContent=result.results.length?t.manualHelp:t.manualIntro;
      status.textContent=result.results.length?t.found.replace('{count}',String(result.total || result.results.length)):(fromTitle?'':t.empty);
      if(result.total>result.results.length) status.textContent+=' '+t.limited;
      custom.hidden=(fromTitle || result.results.length>0) && !personal.value;
      near.hidden=mode==='near' || mode==='reference' || !result.results.length;
    } catch(exc) { if(request===serial && exc.name!=='AbortError') {manual(t.manualHelp);status.textContent='';error.textContent=t.error;} }
  }
  function schedule(mode) {
    cancel();cards=cards.filter(row=>choices.has(row.uri));render();near.hidden=true;
    if(mode==='search') code.value='';
    const q=(mode==='reference'?code.value:query.value).trim();
    if(q.length<2) {status.textContent=t.startTyping;return;}
    status.textContent=t.busy;timer=setTimeout(()=>find(mode),300);
  }
  query.addEventListener('input',()=>schedule('search'));
  code.addEventListener('input',()=>schedule('reference'));
  for(const input of [query,code]) input.addEventListener('keydown',event=>{if(event.key==='Enter'){event.preventDefault();find(input===code?'reference':'search');}});
  search.addEventListener('click',()=>find(code.value.trim()?'reference':'search'));
  near.addEventListener('click',()=>{manual(t.manualHelp,true);cards=cards.filter(row=>choices.has(row.uri));render();heading.hidden=intro.hidden=!cards.length;near.hidden=true;});
  personal.addEventListener('input',()=>{searchedTitle=title.value.trim();error.textContent='';});
  title.addEventListener('input',()=>{clear();fallback.hidden=true;query.value='';code.value='';status.textContent=t.busy;timer=setTimeout(()=>find('search',true,true),300);});
  window.meOccupation={
    load(value,detected=false) {
      clear();fallback.hidden=true;query.value='';code.value='';status.textContent='';
      document.querySelector('label[for=review-title]').textContent=detected?t.detectedTitle:t.ownTitle;
      if(value && value.title===title.value.trim()) {
        version=value.version;searchedTitle=value.title;choices=new Set(value.uris || []);cards=value.jobs || [];personal.value=value.personal || '';custom.hidden=!personal.value;render();
      }
      find('search',true,true);
    },
    reset:clear,
    collect() { return {version,title:title.value.trim(),language:lang,uris:searchedTitle===title.value.trim()?[...choices]:[],personal:searchedTitle===title.value.trim()?personal.value.trim():''}; },
    validate() {
      const value=this.collect();
      if(!value.uris.length && !value.personal) {error.textContent=t.required;box.scrollIntoView({block:'center'});if(fallback.hidden){near.focus();}else{query.focus();}return false;}return true;
    },
    summary(value) { return [...(value?.jobs || []).map(job=>job.label+' — '+job.description),value?.personal].filter(Boolean).join('\n\n'); },
    summaryLabel:t.saved,
  };
})();

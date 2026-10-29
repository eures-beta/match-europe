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
  node('p',t.intro,box);
  const search=node('button',t.search,box); search.type='button'; search.className='ghost-action';
  const status=node('p','',box); status.setAttribute('role','status');
  const list=node('div','',box);
  const near=node('button',t.near,box); near.type='button'; near.className='import-text-button'; near.hidden=true;
  const custom=node('div','',box); custom.hidden=true;
  node('p',t.personalHelp,custom);
  const label=node('label',t.personal,custom); label.htmlFor='occupation-personal';
  const personal=node('textarea','',custom); personal.id='occupation-personal'; personal.maxLength=2000; personal.rows=3;
  const error=node('p','',box); error.setAttribute('role','alert'); error.className='import-error';
  let version='1.2.1', searchedTitle='', cards=[], choices=new Set(), offered=[], serial=0;
  const dirty=()=>form.dispatchEvent(new Event('input',{bubbles:true}));
  function render() {
    list.replaceChildren();
    for(const job of cards) {
      const article=node('article','',list); article.className='review-question';
      const label=node('label','',article); label.className='review-check';
      const check=node('input','',label); check.type='checkbox'; check.value=job.uri; check.checked=choices.has(job.uri);
      const text=node('span','',label); node('strong',job.label,text); node('span',job.description,text).style.display='block';
      check.addEventListener('change',()=>{ if(check.checked) choices.add(job.uri); else choices.delete(job.uri); error.textContent=''; });
      const details=node('details','',article); node('summary',t.references,details);
      const link=node('a','ESCO — '+job.label,details); link.href='https://esco.ec.europa.eu/en/classification/occupation?uri='+encodeURIComponent(job.uri); link.target='_blank'; link.rel='noopener noreferrer';
      node('p',job.reference,details);
      const refs=node('ul','',details);
      for(const fiche of job.rome_fiches || []) node('li','ROME '+fiche.code+' — '+fiche.label,refs);
      if(!job.rome_fiches?.length) node('p',t.noRome,details);
      for(const match of job.rome || []) node('p',`ROME ${match.id} — ${match.label} · ${match.relation}`,details);
      node('p',t.versions,details);
    }
  }
  function clear() { serial++; searchedTitle=''; cards=[];choices=new Set();offered=[];personal.value='';custom.hidden=true;near.hidden=true;list.replaceChildren();error.textContent=''; }
  async function find(mode='search') {
    const q=title.value.trim(); if(!q) {title.focus();return;}
    const request=++serial;
    if(mode==='near') { offered=[...new Set([...offered,...cards.map(row=>row.uri)])]; choices.clear(); }
    else {offered=[];}
    status.textContent=t.busy; error.textContent=''; search.disabled=near.disabled=true;
    try {
      const context=[document.getElementById('review-description').value,document.getElementById('review-desiredProfile').value].join('\n').slice(0,20000);
      const csrf=document.cookie.split('; ').find(value=>value.startsWith('csrftoken='))?.split('=')[1] || '';
      const response=await fetch('/api/occupations/',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-CSRFToken':csrf},body:JSON.stringify({q,lang,mode,excluded:offered,context})});
      if(!response.ok) throw new Error('catalogue');
      const result=await response.json();
      if(request!==serial || title.value.trim()!==q) return;
      version=result.version;searchedTitle=q;
      const retained=mode==='search'?cards.filter(row=>choices.has(row.uri)):[];
      cards=[...retained,...result.results.filter(row=>!retained.some(old=>old.uri===row.uri))];render();
      status.textContent=mode==='near'?t.related:cards.length?'':t.empty;
      custom.hidden=mode!=='near' && cards.length>0 && !personal.value;
      near.hidden=mode==='near' || !cards.length;
    } catch { if(request===serial) {status.textContent='';error.textContent=t.error;} }
    finally { if(request===serial) search.disabled=near.disabled=false; }
  }
  search.addEventListener('click',()=>find()); near.addEventListener('click',()=>{dirty();find('near');});
  personal.addEventListener('input',()=>{error.textContent='';});
  title.addEventListener('input',()=>{clear();search.disabled=false;near.disabled=false;status.textContent=t.changed;});
  window.meOccupation={
    load(value) {
      clear();search.disabled=false;near.disabled=false;status.textContent='';
      if(value && value.title===title.value.trim()) {
        version=value.version;searchedTitle=value.title;choices=new Set(value.uris || []);cards=value.jobs || [];personal.value=value.personal || '';custom.hidden=!personal.value;render();
      }
      find();
    },
    reset:clear,
    collect() { return {version,title:title.value.trim(),language:lang,uris:searchedTitle===title.value.trim()?[...choices]:[],personal:searchedTitle===title.value.trim()?personal.value.trim():''}; },
    validate() {
      const value=this.collect();
      if(!value.uris.length && !value.personal) {error.textContent=t.required;box.scrollIntoView({block:'center'});search.focus();return false;}return true;
    },
    summary(value) { return [...(value?.jobs || []).map(job=>job.label+' — '+job.description),value?.personal].filter(Boolean).join('\n\n'); },
    summaryLabel:t.saved,
  };
})();

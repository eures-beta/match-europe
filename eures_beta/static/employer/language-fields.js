// Explicit language levels; language names use the browser's localised ISO catalogue.
(() => {
  const input=document.getElementById('clarify-frenchLevel');
  const item=input.closest('.clarification-item');
  const t=Object.fromEntries([...document.querySelectorAll('#language-labels [data-key]')].map(el=>[el.dataset.key,el.textContent]));
  const lang=document.documentElement.lang.slice(0,2) || 'fr';
  const normal=value=>value.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().trim();
  const names=['fr','en','de'].map(locale=>new Intl.DisplayNames([locale],{type:'language'}));
  const display=new Intl.DisplayNames([lang],{type:'language'});
  const codes='aa ab ae af ak am an ar as av ay az ba be bg bh bi bm bn bo br bs ca ce ch co cr cs cu cv cy da de dv dz ee el en eo es et eu fa ff fi fj fo fr fy ga gd gl gn gu gv ha he hi ho hr ht hu hy hz ia id ie ig ii ik io is it iu ja jv ka kg ki kj kk kl km kn ko kr ks ku kv kw ky la lb lg li ln lo lt lu lv mg mh mi mk ml mn mr ms mt my na nb nd ne ng nl nn no nr nv ny oc oj om or os pa pi pl ps pt qu rm rn ro ru rw sa sc sd se sg si sk sl sm sn so sq sr ss st su sv sw ta te tg th ti tk tl tn to tr ts tt tw ty ug uk ur uz ve vi vo wa wo xh yi yo za zh zu'.split(' ');
  const catalogue=codes.map(code=>({code,label:display.of(code),aliases:[code,...names.map(dict=>dict.of(code))].map(normal)}));
  // Historical labels may differ from the browser's preferred names.
  for(const code of ['fr','de','en','lb']) catalogue.find(row=>row.code===code).aliases.push(normal(t[code]));
  const box=document.createElement('fieldset');box.className='language-fields guided-condition';
  const legend=document.createElement('legend');legend.textContent=t.title;box.append(legend);
  const help=document.createElement('p');help.className='mini-note';help.textContent=t.help;box.append(help);
  const source=document.createElement('p');source.className='mini-note';box.append(source);
  const warning=document.createElement('p');warning.className='mini-note';warning.textContent=t.uncertain;box.append(warning);
  const rows=document.createElement('div');box.append(rows);
  const add=document.createElement('button');add.type='button';add.className='ghost-action';add.textContent=t.add;box.append(add);
  const searchBox=document.createElement('div');searchBox.className='language-search';box.append(searchBox);
  const label=document.createElement('label');label.htmlFor='language-search';label.textContent=t.search;
  const search=document.createElement('input');search.id=label.htmlFor;search.type='search';search.autocomplete='off';search.maxLength=80;
  const results=document.createElement('ul');results.id='language-suggestions';search.setAttribute('aria-controls',results.id);
  const status=document.createElement('p');status.setAttribute('role','status');status.className='mini-note';
  searchBox.append(label,search,results,status);
  const noneLabel=document.createElement('label');noneLabel.className='review-check';
  const none=document.createElement('input');none.type='checkbox';none.id='language-none';
  const noneText=document.createElement('span');noneText.textContent=t.noRequirement;noneLabel.append(none,noneText);box.append(noneLabel);
  item.append(box);
  const selected=new Map();let last=null,retained='';
  function validate() {none.setCustomValidity(selected.size || none.checked ? '' : t.selectLanguage);}
  function write() {
    const values=none.checked ? t.noRequirement : [...selected.values()].map(row=>row.label+' : '+row.control.value).join('; ');
    input.value=values+(retained ? ' | Source : '+retained : '');last=input.value;
    input.dispatchEvent(new Event('input',{bubbles:true}));validate();
  }
  function create(entry,level='',detected=false) {
    if(selected.has(entry.code))return;
    none.checked=false;
    const row=document.createElement('div');row.className='language-row';
    const lab=document.createElement('label');lab.htmlFor='language-'+entry.code;lab.textContent=entry.label;
    const control=document.createElement('select');control.id=lab.htmlFor;control.required=true;
    for(const value of ['','A1','A2','B1','B2','C1','C2']) {const option=document.createElement('option');option.value=value;option.textContent=value ? t[value] : t.choose;control.append(option);}
    control.value=level;
    const note=document.createElement('p');note.className='mini-note';note.id='language-note-'+entry.code;control.setAttribute('aria-describedby',note.id);
    function describe(){note.textContent=(detected ? t.detected+' ' : '')+(t[control.value] || '');}
    control.addEventListener('change',()=>{detected=false;describe();write();});
    const remove=document.createElement('button');remove.type='button';remove.className='ghost-action';remove.textContent=t.remove+' — '+entry.label;
    remove.onclick=()=>{row.remove();selected.delete(entry.code);write();add.focus();};
    row.append(lab,control,note,remove);rows.append(row);selected.set(entry.code,{label:entry.label,control});describe();validate();
  }
  function suggest() {
    results.replaceChildren();const q=normal(search.value);status.textContent='';if(!q)return;
    const matches=catalogue.filter(row=>!selected.has(row.code) && row.aliases.some(alias=>alias.includes(q))).sort((a,b)=>Number(b.aliases.includes(q))-Number(a.aliases.includes(q)) || a.label.localeCompare(b.label,lang)).slice(0,8);
    if(!matches.length)status.textContent=t.notFound;
    for(const entry of matches){const li=document.createElement('li');const button=document.createElement('button');button.type='button';button.className='ghost-action';button.textContent=entry.label;button.onclick=()=>{create(entry);search.value='';results.replaceChildren();searchBox.hidden=true;write();document.getElementById('language-'+entry.code).focus();};li.append(button);results.append(li);}
  }
  add.onclick=()=>{searchBox.hidden=false;search.focus();};
  search.addEventListener('input',suggest);
  search.addEventListener('keydown',event=>{if(event.key==='Enter'){event.preventDefault();const matches=[...results.querySelectorAll('button')];if(matches.length===1)matches[0].click();}});
  none.addEventListener('change',()=>{if(none.checked){selected.clear();rows.replaceChildren();search.value='';results.replaceChildren();}write();});
  function load() {
    if(input.value===last)return;
    last=input.value;selected.clear();rows.replaceChildren();none.checked=false;retained='';search.value='';results.replaceChildren();searchBox.hidden=true;
    const pieces=input.value.split(' | Source : ');const raw=pieces.shift();retained=pieces.join(' | Source : ');
    const noneLabels=['Aucune exigence linguistique particulière','No particular language requirement','Keine besonderen Sprachanforderungen'];
    const unparsed=[];let negative=0;const seen=new Set();
    for(const part of raw.split(/[;\n]/).map(value=>value.trim()).filter(Boolean)) {
      if(noneLabels.includes(part)){none.checked=true;continue;}
      const match=part.match(/^([^:]+)\s*:\s*(A1|A2|B1|B2|C1|C2|Pas nécessaire|Not required|Nicht erforderlich)\s*$/i);
      const entry=match && catalogue.find(row=>row.aliases.includes(normal(match[1])));
      if(!entry){unparsed.push(part);continue;}
      if(!/^[ABC][12]$/i.test(match[2])){negative++;continue;}
      if(seen.has(entry.code)){unparsed.push(part);const previous=selected.get(entry.code);if(previous)previous.control.value='';continue;}
      seen.add(entry.code);create(entry,match[2].toUpperCase(),true);
    }
    // A former list of four explicit "not required" answers is compatible.
    if(!selected.size && negative>=4 && !unparsed.length)none.checked=true;
    if(selected.size)none.checked=false;
    if(unparsed.length)retained=[...unparsed,retained].filter(Boolean).join('; ');
    source.textContent=input.value ? t.source+' : '+input.value : '';source.hidden=!retained;
    warning.hidden=!retained;validate();
  }
  document.addEventListener('me-step-change',event=>{if(event.detail==='review-step')load();});
  load();
})();

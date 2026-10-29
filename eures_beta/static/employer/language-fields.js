// Explicit language levels only: never infer a CEFR level from vague wording.
(() => {
  const form=document.getElementById('review-form');
  const input=document.getElementById('clarify-frenchLevel');
  const item=input.closest('.clarification-item');
  const t=Object.fromEntries([...document.querySelectorAll('#language-labels [data-key]')].map(el=>[el.dataset.key,el.textContent]));
  const keys=['fr','de','en','lb'];
  const aliases={fr:['fr','french','français','francais','französisch'],de:['de','german','allemand','deutsch'],en:['en','english','anglais','englisch'],lb:['lb','luxembourgish','luxembourgeois','luxemburgisch']};
  const box=document.createElement('fieldset');box.className='language-fields guided-condition';
  const legend=document.createElement('legend');legend.textContent=t.title;box.append(legend);
  const help=document.createElement('p');help.className='mini-note';help.textContent=t.help;box.append(help);
  const source=document.createElement('p');source.className='mini-note';box.append(source);
  const warning=document.createElement('p');warning.className='mini-note';warning.textContent=t.uncertain;box.append(warning);
  const fields={};
  function select(key,label) {
    const row=document.createElement('div');row.className='language-row';
    const lab=document.createElement('label');lab.htmlFor='language-'+key;lab.textContent=label;
    const control=document.createElement('select');control.id=lab.htmlFor;
    for(const value of ['', 'none','A1','A2','B1','B2','C1','C2']) {const option=document.createElement('option');option.value=value;option.textContent=value ? t[value] : t.choose;control.append(option);}
    const note=document.createElement('p');note.className='mini-note';note.id='language-note-'+key;control.setAttribute('aria-describedby',note.id);
    row.append(lab,control,note);box.append(row);fields[key]={control,note};return control;
  }
  for(const key of keys) select(key,t[key]).required=true;
  const otherRow=document.createElement('div');otherRow.className='review-field';
  const otherLabel=document.createElement('label');otherLabel.htmlFor='language-other-name';otherLabel.textContent=t.other;
  const other=document.createElement('input');other.id=otherLabel.htmlFor;other.maxLength=80;
  otherRow.append(otherLabel,other);box.append(otherRow);
  select('other',t.otherLevel);
  item.append(box);
  let last=null, retained='';
  function sync() {
    fields.other.control.required=Boolean(other.value.trim());fields.other.control.disabled=!other.value.trim();
    for(const key of [...keys,'other']) if(!fields[key].note.dataset.detected) fields[key].note.textContent=fields[key].control.value ? t[fields[key].control.value] : '';
  }
  function write() {
    sync();
    const rows=keys.filter(key=>fields[key].control.value).map(key=>t[key]+' : '+(fields[key].control.value === 'none' ? t.none : fields[key].control.value));
    if(other.value.trim() && fields.other.control.value) rows.push(other.value.trim()+' : '+fields.other.control.value);
    input.value=rows.join('; ')+(retained ? ' | Source : '+retained : '');last=input.value;
    input.dispatchEvent(new Event('input',{bubbles:true}));
  }
  box.addEventListener('change',event=>{const entry=Object.values(fields).find(row=>row.control===event.target);if(entry){delete entry.note.dataset.detected;}write();});
  other.addEventListener('input',write);
  function load() {
    if(input.value===last)return;
    last=input.value;retained='';other.value='';
    for(const row of Object.values(fields)){row.control.value='';row.note.textContent='';delete row.note.dataset.detected;}
    const pieces=input.value.split(' | Source : ');const raw=pieces.shift();retained=pieces.join(' | Source : ');
    let unparsed=[];const seen=new Set();
    for(const part of raw.split(/[;\n]/).map(value=>value.trim()).filter(Boolean)) {
      const match=part.match(/^([^:]+)\s*:\s*(A1|A2|B1|B2|C1|C2|Pas nécessaire|Not required|Nicht erforderlich)\s*$/i);
      const key=match && keys.find(key=>aliases[key].includes(match[1].trim().toLowerCase()));
      if(key && seen.has(key)) {
        fields[key].control.value='';fields[key].note.textContent='';delete fields[key].note.dataset.detected;unparsed.push(part);
      } else if(key && !fields[key].control.value) {
        seen.add(key);
        fields[key].control.value=/^[ABC][12]$/i.test(match[2]) ? match[2].toUpperCase() : 'none';
        fields[key].note.textContent=t.detected+' '+t[fields[key].control.value];fields[key].note.dataset.detected='true';
      } else if(match && !key && !other.value) {
        other.value=match[1].trim().slice(0,80);fields.other.control.value=/^[ABC][12]$/i.test(match[2]) ? match[2].toUpperCase() : 'none';
      } else unparsed.push(part);
    }
    if(unparsed.length)retained=[...unparsed,retained].filter(Boolean).join('; ');
    source.textContent=input.value ? t.source+' : '+input.value : '';source.hidden=!input.value;
    warning.hidden=!retained;sync();
  }
  document.addEventListener('me-step-change',event=>{if(event.detail==='review-step')load();});
  load();
})();

 'use strict';
(() => {
  const api = window.employerAPI;
  if (!api) return;
  const t = JSON.parse(document.getElementById('contact-strings').textContent);
  let current = null;
  function fields(prefix) {
    const box = document.createElement('fieldset'); box.className = 'alt-panel';
    const legend = document.createElement('legend'); legend.textContent = t.title; box.append(legend);
    const privacy = document.createElement('p'); privacy.id = prefix+'-privacy'; privacy.className = 'mini-note'; privacy.textContent = t.privacy; box.append(privacy);
    for (const [name,type,max,autocomplete] of [['name','text',150,'name'],['email','email',254,'email'],['phone','tel',40,'tel'],['function','text',150,'organization-title']]) {
      const row = document.createElement('div'); row.className = 'review-field';
      const label = document.createElement('label'); label.htmlFor = prefix+'-'+name; label.textContent = t[name];
      const input = document.createElement('input'); input.id = label.htmlFor; input.name = name; input.type = type; input.maxLength = max;
      input.autocomplete = autocomplete; input.required = ['name','email'].includes(name); input.setAttribute('aria-describedby',privacy.id);
      row.append(label,input); box.append(row);
    }
    const help = document.createElement('p'); help.className = 'mini-note'; help.textContent = t.help; box.append(help);
    return box;
  }
  const initial = fields('initial-contact');
  document.getElementById('email-form').insertBefore(initial,document.querySelector('#email-form .landing-actions'));
  let customEmail = false;
  document.getElementById('email-form').addEventListener('reset',()=>{customEmail=false;});
  document.getElementById('initial-contact-email').addEventListener('input',()=>{customEmail=true;});
  document.getElementById('work-email').addEventListener('input',event=>{
    if (!customEmail) document.getElementById('initial-contact-email').value=event.target.value;
  });
  const editor=document.createElement('form'); editor.id='contact-editor'; editor.className='alt-panel'; editor.hidden=true;
  editor.append(fields('edit-contact'));
  const save=document.createElement('button'); save.type='submit'; save.className='primary-action'; save.textContent=t.save;
  const status=document.createElement('p'); status.setAttribute('role','status');
  editor.append(save,status);
  function values(prefix) { return Object.fromEntries(['name','email','phone','function'].map(name=>[name,document.getElementById(prefix+'-'+name).value.trim()])); }
  window.meContact={
    initial:()=>values('initial-contact'),
    load(result) {
      current={id:result.id,revision:result.revision}; status.textContent='';
      for (const name of ['name','email','phone','function']) editor.querySelector('[name='+name+']').value=result.contact?.[name] || '';
    }
  };
  document.addEventListener('me-step-change',event=>{
    const visible=Boolean(current?.id) && ['prepare-step','review-step','completion-step'].includes(event.detail);
    editor.hidden=!visible;
    if (visible) document.getElementById(event.detail).append(editor);
  });
  editor.addEventListener('submit',async event=>{
    event.preventDefault(); if (!current || !editor.reportValidity()) return;
    save.disabled=true; status.textContent='';
    try {
      const result=await api.update(current.id,{action:'contact',revision:current.revision,contact:values('edit-contact')});
      current.revision=result.revision; window.meReview.setContact(result); status.textContent=t.saved;
    } catch(exc) { status.textContent=exc.code==='conflict' ? t.conflict : t.error; }
    finally { save.disabled=false; }
  });
  // Other offer saves advance the revision without replacing unsaved contact edits.
  document.addEventListener('me-import-revision',event=>{
    if(current?.id===event.detail.id) current.revision=event.detail.revision;
  });
})();

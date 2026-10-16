'use strict';
window.localEmployerAPI = document.body.dataset.liveLocal === 'true' ? {
  async request(path, options = {}) {
    const csrf = document.cookie.split('; ').find(x => x.startsWith('csrftoken='))?.split('=')[1] || '';
    let response;
    try { response = await fetch('/local-api/imports/' + path, {...options, credentials:'same-origin', headers:{...options.headers,'X-CSRFToken':csrf}}); }
    catch { throw Object.assign(new Error('network'), {code:'network'}); }
    let data;
    try { data = await response.json(); } catch { throw Object.assign(new Error('network'), {code:'network'}); }
    if (data.id && data.revision) document.dispatchEvent(new CustomEvent('me-import-revision',{detail:data}));
    if (!response.ok) throw Object.assign(new Error(data.error || 'network'), {code:data.error || 'network',data});
    return data;
  },
  update(id, payload) { return this.request(id+'/', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)}); }
} : null;

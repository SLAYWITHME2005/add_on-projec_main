const keyInput = document.getElementById('key');
const loadBtn = document.getElementById('load');
const listBody = document.querySelector('#list tbody');
const createBtn = document.getElementById('create');

function headers(){
  return {'Content-Type':'application/json','x-api-key': keyInput.value};
}

loadBtn.addEventListener('click', async ()=>{
  listBody.innerHTML='';
  const res = await fetch('/admin/faqs', {headers: {'x-api-key': keyInput.value}});
  if(!res.ok){ alert('Failed to load FAQs'); return; }
  const faqs = await res.json();
  for(const f of faqs){
    const tr = document.createElement('tr');
    tr.innerHTML = `<td>${f.id}</td><td>${escapeHtml(f.question)}</td><td>${escapeHtml(f.answer)}</td><td>${(f.tags||[]).join(',')}</td><td><button data-id="${f.id}" class="del">Delete</button></td>`;
    listBody.appendChild(tr);
  }
  for(const btn of document.querySelectorAll('.del')){
    btn.onclick = async (e)=>{
      const id = e.target.dataset.id;
      if(!confirm('Delete FAQ '+id+'?')) return;
      const r = await fetch('/admin/faqs/'+id, {method:'DELETE', headers: {'x-api-key': keyInput.value}});
      if(r.ok) loadBtn.click(); else alert('delete failed');
    }
  }
});

createBtn.addEventListener('click', async ()=>{
  const q = document.getElementById('q').value;
  const a = document.getElementById('a').value;
  const t = document.getElementById('t').value.split(',').map(x=>x.trim()).filter(Boolean);
  const res = await fetch('/admin/faqs', {method:'POST', headers: headers(), body: JSON.stringify({question:q,answer:a,tags:t})});
  if(res.ok){ alert('created'); loadBtn.click(); } else { alert('create failed'); }
});

function escapeHtml(s){ return s.replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;'); }

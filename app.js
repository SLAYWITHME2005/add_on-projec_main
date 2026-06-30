const messages = document.getElementById('messages');
const msgBox = document.getElementById('msg');
const send = document.getElementById('send');
const kSlider = document.getElementById('kSlider');
const kVal = document.getElementById('kVal');
const tempSlider = document.getElementById('tempSlider');
const tVal = document.getElementById('tVal');

function append(text, cls='bot'){
  const d = document.createElement('div');
  d.className = 'msg ' + cls;
  d.textContent = text;
  messages.appendChild(d);
  messages.scrollTop = messages.scrollHeight;
}

send.addEventListener('click', async ()=>{
  const text = msgBox.value.trim();
  if(!text) return;
  append(text, 'user');
  msgBox.value = '';
  append('Thinking...', 'bot');
  const k = parseInt(kSlider ? kSlider.value : 5);
  const temperature = parseFloat(tempSlider ? tempSlider.value : 0.0);
  const resp = await fetch('/chat', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({message:text, k:k, temperature:temperature})});
  const data = await resp.json();
  // remove last placeholder
  messages.removeChild(messages.lastChild);
  if(data.answer){
    append(data.answer, 'bot');
  } else {
    append('No answer found.', 'bot');
  }
});

// update UI labels for sliders
if(kSlider){
  kSlider.addEventListener('input', ()=>{ kVal.textContent = kSlider.value });
}
if(tempSlider){
  tempSlider.addEventListener('input', ()=>{ tVal.textContent = tempSlider.value });
}

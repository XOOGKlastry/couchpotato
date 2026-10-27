'use strict';
const $ = id => document.getElementById(id);
// This setting is injected here so older Android WebViews receive it from the
// updated Windows app without requiring a new APK.
const idleLabel=document.createElement('label'),idleText=document.createElement('span'),idleInput=document.createElement('input'),idleStatus=document.createElement('p');
idleLabel.className='setting-row';idleLabel.htmlFor='idle-shutdown';idleText.textContent='Wyłącz po 4 h bezczynności';idleInput.type='checkbox';idleInput.id='idle-shutdown';idleStatus.id='idle-status';idleStatus.setAttribute('role','status');idleStatus.textContent='Liczy brak używania myszy i klawiatury.';idleLabel.append(idleText,idleInput);const extensionHelp=document.querySelector('.extension-help');extensionHelp.before(idleLabel,idleStatus);document.querySelector('.edition').textContent='REMOTE / 1.8';
let token = localStorage.getItem('kanapaToken') || '';
let queue = Promise.resolve(), toastTimer, pingBusy = false, powerState = 'idle', powerDeadline = 0;
function status(message, state = '') {
  $('status').textContent = message;
  $('status-dot').className = 'status-dot ' + state;
}
function toast(message, error = false) {
  clearTimeout(toastTimer);
  $('toast').textContent = message;
  $('toast').className = 'toast' + (error ? ' error' : '');
  $('toast').hidden = false;
  toastTimer = setTimeout(() => { $('toast').hidden = true; }, error ? 5000 : 2300);
}
function ready() {
  $('pair').hidden = true;
  $('controls').hidden = false;
  $('power-button').disabled = false;
  status('Połączono z laptopem', 'connected');
}
function disconnected() {
  suspendExtras();
  token = '';
  localStorage.removeItem('kanapaToken');
  $('pair').hidden = false;
  $('controls').hidden = true;
  $('power-button').disabled = true;
  if ($('power-dialog').open) $('power-dialog').close();
  status('Połącz pilot ponownie', 'error');
}
function renderPower() {
  $('power-banner').hidden = powerState === 'idle';
  $('cancel-shutdown').hidden = powerState === 'sent' || powerState === 'error';
  $('power-button').disabled = !token || powerState === 'sent';
  if (powerState === 'countdown') {
    const seconds = Math.max(0, Math.ceil((powerDeadline - Date.now()) / 1000));
    $('power-title').textContent = seconds ? `Wyłączenie za ${seconds} s` : 'Przekazywanie do Windows…';
    $('power-description').textContent = seconds ? 'Możesz jeszcze zmienić zdanie.' : 'Sprawdź ekran laptopa.';
  } else if (powerState === 'sent') {
    $('power-title').textContent = 'Polecenie wyłączenia wysłane';
    $('power-description').textContent = 'Jeśli Windows prosi o zapis plików, spójrz na ekran.';
  } else if (powerState === 'error') {
    $('power-title').textContent = 'Nie udało się wyłączyć laptopa';
    $('power-description').textContent = 'Sprawdź uprawnienia Windows lub spróbuj ponownie.';
  }
}
function updatePower(power) {
  if (!power) return;
  powerState = power.state;
  powerDeadline = Date.now() + power.seconds * 1000;
  renderPower();
}
async function api(path, data, auth = true) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 4500);
  try {
    const response = await fetch(path, {
      method: 'POST', headers: { 'Content-Type': 'application/json', ...(auth ? { Authorization: 'Bearer ' + token } : {}) },
      body: JSON.stringify(data), signal: controller.signal
    });
    if (!response.ok) {
      if (response.status === 401) disconnected();
      throw Error(response.status === 429 ? 'Za dużo prób. Odczekaj 5 minut.' :
        response.status === 403 ? 'Nieprawidłowy kod lub brak dostępu.' :
        response.status === 401 ? 'Wpisz aktualny kod z laptopa.' :
        (await response.json().catch(() => ({}))).error || 'Polecenie nie zostało wykonane. Sprawdź laptop.');
    }
    const result = await response.json();
    updatePower(result.power);
    if(result.youtube)renderYoutube(result.youtube);
    return result;
  } catch (e) {
    if (e.name === 'AbortError' || e instanceof TypeError) throw Error('Brak połączenia. Sprawdź Wi-Fi i laptop.');
    throw e;
  } finally { clearTimeout(timer); }
}
function send(data, successMessage = '', shouldSend = () => true) {
  // Serialize real input; keep the queue usable after a network error.
  const job = queue.then(async () => {
    if(window.couchLayoutEditing||!shouldSend())return true;
    try {
      await api('/action', data);
      status('Połączono z laptopem', 'connected');
      if (successMessage) toast(successMessage);
      return true;
    } catch (e) { status('Sprawdź połączenie', 'error'); toast(e.message, true); return false; }
  });
  queue = job.then(() => {});
  return job;
}
async function pair(code) {
  const data = await api('/pair', { code }, false);
  token = data.token;
  localStorage.setItem('kanapaToken', token);
  ready();
  await ping();
}
$('pin').addEventListener('input', () => { $('pin').value = $('pin').value.replace(/\D/g, '').slice(0, 4); });
$('pairform').onsubmit = async e => {
  e.preventDefault();
  const button = e.submitter || $('pairform').querySelector('button');
  button.disabled = true;
  try { await pair($('pin').value); } catch (e) { status('Nie udało się połączyć', 'error'); toast(e.message, true); }
  finally { button.disabled = false; }
};
const serviceNames = { youtube: 'YouTube', hbo: 'HBO Max', canal: 'CANAL+', polsat: 'Polsat Box Go' };
document.querySelectorAll('[data-service]').forEach(b => b.onclick = () => send({ action: 'open', service: b.dataset.service }, 'Otwieram ' + serviceNames[b.dataset.service] + ' na laptopie'));
document.querySelectorAll('[data-key]').forEach(b => b.onclick = () => send({ action: 'key', key: b.dataset.key }));
document.querySelectorAll('[data-shortcut]').forEach(b => b.onclick = () => send({action: 'shortcut', shortcut: b.dataset.shortcut}));
document.querySelectorAll('[data-action]').forEach(button => button.onclick = () => send({ action: button.dataset.action }));
let chromeMode=false;
function clearChromeMode(){chromeMode=false;$('text').placeholder='Szukaj / wpisz…';}
$('new-chrome-tab').onclick=async()=>{
  $('text').value='';$('text').focus();$('text').placeholder='Adres lub wyszukiwanie…';
  $('new-chrome-tab').disabled=true;$('text-send').disabled=true;
  chromeMode=await send({action:'new_chrome_tab'});
  if(!chromeMode)clearChromeMode();
  $('new-chrome-tab').disabled=false;$('text-send').disabled=false;
};
$('text-delete').onclick=()=>{
 if(window.couchLayoutEditing)return;
 const input=$('text');
 if(input.value){
  const end=input.selectionEnd??input.value.length,start=input.selectionStart??end;
  const before=input.value.slice(0,start),cut=start===end?before.length-Array.from(before).slice(-1).join('').length:start;
  input.value=input.value.slice(0,cut)+input.value.slice(end);input.focus();input.setSelectionRange(cut,cut);
 }else send({action:'key',key:'backspace'});
};
$('textform').onsubmit=async e=>{
  e.preventDefault();
  if(!$('text').value||$('text-send').disabled)return;
  $('text-send').disabled=true;
  const success=await send({action:chromeMode?'chrome_search':'text',text:$('text').value});
  $('text-send').disabled=false;
  if(success&&chromeMode){clearChromeMode();$('text').blur();}
};
document.querySelectorAll('[data-service],[data-brave],[data-shortcut],[data-key]').forEach(b=>b.addEventListener('click',clearChromeMode));
$('power-button').onclick = () => {
  if (powerState === 'countdown') { $('power-banner').scrollIntoView({ block: 'center', behavior: 'smooth' }); return; }
  $('power-dialog').showModal();
};
$('keep-watching').onclick = () => $('power-dialog').close();
$('confirm-shutdown').onclick = async () => {
  $('confirm-shutdown').disabled = true;
  const success = await send({ action: 'shutdown', confirmed: true });
  $('confirm-shutdown').disabled = false;
  if (success) {
    $('power-dialog').close();
    $('power-banner').scrollIntoView({ block: 'center', behavior: 'smooth' });
  }
};
$('cancel-shutdown').onclick = async () => {
  $('cancel-shutdown').disabled = true;
  await send({ action: 'cancel_shutdown' }, 'Wyłączenie anulowane. Miłego seansu!');
  $('cancel-shutdown').disabled = false;
};
const touch = new TouchRemote($('pad'), (data,valid) => send(data,'',valid), () => Boolean(token));
touch.onHold=multiplier=>{
  $('scroll-multiplier').hidden=!multiplier;
  $('scroll-multiplier').textContent=multiplier+'×';
  document.querySelector('.pad-center').classList.toggle('hold-active',Boolean(multiplier));
};
if(navigator.userAgent.includes('couchpotatoAndroid/'))$('native-connection').hidden=false;
document.querySelectorAll('[data-hold-scroll]').forEach(b => touch.bindHold(b, Number(b.dataset.holdScroll)));
setInterval(() => touch.tick(), 45);
window.addEventListener('blur', () => touch.reset());
document.addEventListener('visibilitychange', () => { if(document.hidden) touch.reset(); });
let braveLinks = [{name:'',url:''},{name:'',url:''},{name:'',url:''}];
try {
  const stored = JSON.parse(localStorage.getItem('kanapaBrave') || 'null');
  if(Array.isArray(stored) && stored.length === 3) braveLinks = stored.map(x => ({name: typeof x?.name === 'string' ? x.name.slice(0,24) : '',url: typeof x?.url === 'string' ? x.url : ''}));
} catch (_) {}
function renderBrave(){braveLinks.forEach((link,i) => { $('brave-label-'+i).textContent=link.name||'Brave '+(i+1); const button=document.querySelector('[data-brave="'+i+'"]'); button.title=link.name||'Ustaw skrót Brave '+(i+1);button.setAttribute('aria-label',button.title); });}
function editBrave(){braveLinks.forEach((link,i) => { $('brave-name-'+i).value=link.name; $('brave-url-'+i).value=link.url; });$('brave-dialog').showModal();}
$('edit-brave').onclick=editBrave;
$('close-brave').onclick=()=>$('brave-dialog').close();
$('brave-form').onsubmit=e=>{
  e.preventDefault();
  const links=[];
  for(let i=0;i<3;i++){
    const name=$('brave-name-'+i).value.trim(), url=$('brave-url-'+i).value.trim();
    if(!name&&!url){links.push({name:'',url:''});continue;}
    try{const u=new URL(url);if(!name||u.protocol!=='https:'||!u.hostname||u.username||u.password||/\s/.test(url))throw Error();}
    catch(_){toast('Serwis '+(i+1)+': podaj nazwę i adres https://…',true);return;}
    links.push({name,url});
  }
  try{localStorage.setItem('kanapaBrave',JSON.stringify(links));}
  catch(_){toast('Przeglądarka nie pozwala zapisać skrótów. Wyłącz tryb prywatny.',true);return;}
  braveLinks=links;renderBrave();$('brave-dialog').close();toast('Skróty zapisane');
};
document.querySelectorAll('[data-brave]').forEach(b=>b.onclick=()=>{
  const link=braveLinks[Number(b.dataset.brave)];
  if(!link.url){editBrave();return;}
  send({action:'open_brave',url:link.url},'Otwieram '+link.name+' w Brave');
});
renderBrave();
async function ping() {
  if (!token || pingBusy || document.hidden) return;
  pingBusy = true;
  try { await api('/ping', {}); status('Połączono z laptopem', 'connected'); }
  catch (e) { status(powerState === 'sent' ? 'Laptop rozłączony' : 'Brak połączenia z laptopem', 'error'); }
  finally { pingBusy = false; }
}
(async () => {
  try {
    if (location.hostname === '127.0.0.1' || location.hostname === 'localhost') {
      const r = await fetch('/setup');
      if (r.ok) {
        const s = await r.json();
        $('setup').hidden = false;
        document.querySelector('.intro').classList.add('has-setup');
        $('code').textContent = s.code;
        s.addresses.forEach(address => { const row = document.createElement('div'); row.textContent = address; $('addresses').appendChild(row); });
        if (!s.addresses.length) $('addresses').textContent = 'Połącz laptop z Wi-Fi i uruchom aplikację ponownie.';
        await pair(s.code);
        return;
      }
    }
    if (token) { await api('/ping', {}); ready(); }
    else status('Czekam na połączenie');
  } catch (e) { status('Nie udało się połączyć', 'error'); toast(e.message, true); }
})();
setInterval(ping, 2500);
setInterval(() => { if (powerState === 'countdown') renderPower(); }, 250);
document.addEventListener('visibilitychange', () => { if (!document.hidden) ping(); });

// Press-and-hold media controls: one request at a time, no delayed repeats after release.
const repeatButtons=[];
for(const key of ['volup','voldown','seek5_back','seek5_forward']){
 const button=document.querySelector('[data-key="'+key+'"]');
 repeatButtons.push(new RepeatButton(button, valid=>send({action:'key',key},'',valid||(()=>!!token)),()=>!!token,key.startsWith('seek')?350:190));
}
let previewBounds=null;
let previewActive=false,previewTimer,previewRequest,previewURL='',previewGeneration=0;
function stopPreview(){
 previewBounds=null;if($('viewer-dialog').open)$('viewer-dialog').close();$('viewer-image').hidden=true;previewActive=false;previewGeneration++;clearTimeout(previewTimer);if(previewRequest)previewRequest.abort();
 $('screen-preview').hidden=true;$('screen-image').hidden=true;$('screen-image').removeAttribute('src');
 $('preview-toggle').setAttribute('aria-expanded','false');$('preview-toggle').classList.remove('selected');
 if(previewURL){URL.revokeObjectURL(previewURL);previewURL='';}
}
async function previewFrame(g){
 if(!previewActive||g!==previewGeneration||document.hidden||!token)return;
 const controller=new AbortController();previewRequest=controller;const timeout=setTimeout(()=>controller.abort(),5000);
 try{
  const response=await fetch('/preview',{method:'POST',headers:{'Content-Type':'application/json',Authorization:'Bearer '+token},body:JSON.stringify({detail:$('viewer-dialog').open}),signal:controller.signal});
  if(response.status===401){disconnected();stopPreview();return;}
  if(!response.ok)throw Error('Ekran niedostępny. Odblokuj Windows.');
  const blob=await response.blob();if(!previewActive||g!==previewGeneration)return;
  previewBounds=JSON.parse(response.headers.get('X-Screen-Bounds')||'null');
  const next=URL.createObjectURL(blob),old=previewURL;previewURL=next;$('screen-image').src=next;$('screen-image').hidden=false;$('viewer-image').src=next;$('viewer-image').hidden=false;if(old)URL.revokeObjectURL(old);
  $('preview-error').hidden=true;$('preview-state').textContent='Na żywo';
 }catch(error){if(g===previewGeneration&&previewActive){$('preview-state').textContent='Brak obrazu';$('screen-image').hidden=true;$('viewer-image').hidden=true;previewBounds=null;$('preview-error').hidden=false;$('viewer-hint').textContent='Brak aktualnego obrazu — sprawdź połączenie.';$('preview-error').textContent=error.name==='AbortError'?'Sprawdź połączenie z laptopem.':error.message;}}
 finally{clearTimeout(timeout);if(previewActive&&g===previewGeneration)previewTimer=setTimeout(()=>previewFrame(g),1000);}
}
$('preview-toggle').onclick=()=>{
 if(previewActive)return stopPreview();if(!token)return;
 previewActive=true;const g=++previewGeneration;$('screen-preview').hidden=false;$('preview-error').hidden=true;$('preview-state').textContent='Łączenie…';
 $('preview-toggle').setAttribute('aria-expanded','true');$('preview-toggle').classList.add('selected');previewFrame(g);
};
function suspendExtras(){stopHardwareVolume();repeatButtons.forEach(b=>b.stop());stopPreview();}
window.addEventListener('blur',suspendExtras);document.addEventListener('visibilitychange',()=>{if(document.hidden)suspendExtras();});
$('preferences-open').onclick=async()=>{
 $('preferences-dialog').showModal();$('startup').disabled=true;$('idle-shutdown').disabled=true;$('startup-status').textContent='Łączenie…';
 try{const p=await api('/preferences',{});$('startup').checked=p.startup;$('startup').disabled=!p.available;$('idle-shutdown').checked=p.idle_shutdown;$('idle-shutdown').disabled=false;$('idle-status').textContent=p.idle_shutdown?'Komputer wyłączy się po 4 godzinach bez używania myszy lub klawiatury.':'Automatyczne wyłączanie jest wyłączone.';$('startup-status').textContent=p.available?'Po zalogowaniu do Windows.':'Uruchom couchpotato.exe na komputerze.';}
 catch(e){$('startup-status').textContent=e.message;}
};
$('startup').onchange=async()=>{const previous=!$('startup').checked;$('startup').disabled=true;try{const p=await api('/preferences',{startup:$('startup').checked});$('startup').checked=p.startup;$('startup-status').textContent=p.startup?'Autostart włączony.':'Autostart wyłączony.';}catch(e){$('startup').checked=previous;$('startup-status').textContent=e.message;}finally{$('startup').disabled=false;}};
$('idle-shutdown').onchange=async()=>{const previous=!$('idle-shutdown').checked;$('idle-shutdown').disabled=true;try{const p=await api('/preferences',{idle_shutdown:$('idle-shutdown').checked});$('idle-shutdown').checked=p.idle_shutdown;$('idle-status').textContent=p.idle_shutdown?'Komputer wyłączy się po 4 godzinach bez używania myszy lub klawiatury.':'Automatyczne wyłączanie jest wyłączone.';}catch(e){$('idle-shutdown').checked=previous;$('idle-status').textContent=e.message;}finally{$('idle-shutdown').disabled=false;}};
$('preferences-close').onclick=()=>$('preferences-dialog').close();

function screenClick(x,y){if(!previewBounds||!previewActive||!token)return;send({action:'screen_click',x,y,bounds:previewBounds});}
const screenViewer=new ScreenViewer($('viewer-stage'),$('viewer-image'),screenClick);
screenViewer.onzoom=scale=>$('zoom-reset').textContent=scale.toFixed(1)+'×';
$('viewer-image').onload=()=>screenViewer.render();
$('preview-expand').onclick=()=>{if(!previewActive)return;$('viewer-dialog').showModal();screenViewer.reset();$('viewer-hint').textContent='Stuknij, aby kliknąć · dwa palce powiększają · przeciągnij powiększony obraz';};
$('viewer-close').onclick=()=>$('viewer-dialog').close();
$('viewer-dialog').addEventListener('close',()=>screenViewer.reset());
$('zoom-in').onclick=()=>screenViewer.zoom(screenViewer.scale*1.5);
$('zoom-out').onclick=()=>screenViewer.zoom(screenViewer.scale/1.5);
$('zoom-reset').onclick=()=>screenViewer.reset();
window.addEventListener('resize',()=>screenViewer.render());
let inlineDown=null;
$('screen-image').onpointerdown=e=>{inlineDown={x:e.clientX,y:e.clientY,time:Date.now()};};
$('screen-image').onpointerup=e=>{if(inlineDown&&Date.now()-inlineDown.time<500&&Math.hypot(e.clientX-inlineDown.x,e.clientY-inlineDown.y)<9){const r=$('screen-image').getBoundingClientRect();screenClick((e.clientX-r.left)/r.width,(e.clientY-r.top)/r.height);}inlineDown=null;};
$('screen-image').onpointercancel=()=>{inlineDown=null;};
let hardwareTimer,hardwareGeneration=0;
function stopHardwareVolume(){hardwareGeneration++;clearTimeout(hardwareTimer);}
window.couchVolume=(key,pressed)=>{
 if(!['volup','voldown'].includes(key))return;stopHardwareVolume();if(!pressed||!token||document.hidden)return;
 const g=hardwareGeneration;send({action:'key',key});
 const pulse=async()=>{if(g!==hardwareGeneration||!token)return;await send({action:'key',key},'',()=>g===hardwareGeneration&&!!token);if(g===hardwareGeneration)hardwareTimer=setTimeout(pulse,180);};
 hardwareTimer=setTimeout(pulse,450);
};

window.stopRemoteGestures=()=>{touch.reset();repeatButtons.forEach(b=>b.stop());stopHardwareVolume();};

const youtubeRates=[1,1.25,1.5,1.75,2,3,4];let speedBusy=false,speedDragging=false;
function renderYoutube(state){
 const rate=state.pending!==null?state.pending:state.actual;
 if(rate!==null&&Number.isFinite(rate)){$('speed-value').textContent=rate+'×';const i=youtubeRates.indexOf(rate);if(i>=0&&!speedBusy&&!speedDragging)$('speed-slider').value=i;$('speed-slider').setAttribute('aria-valuetext',rate+' razy');}
 $('speed-status').textContent=state.error||(state.pending!==null?'Ustawianie…':!state.connected?'Połącz dodatek YouTube w ustawieniach.':!state.has_video?'Otwórz film na aktywnej karcie YouTube.':'Tempo potwierdzone przez odtwarzacz.');
}
async function setYoutubeSpeed(index){if(speedBusy||window.couchLayoutEditing)return;const rate=youtubeRates[index];if(rate===undefined)return;speedBusy=true;$('speed-status').textContent='Ustawianie '+rate+'×…';try{await api('/action',{action:'playback_rate',rate});$('speed-slider').value=index;}catch(e){$('speed-status').textContent=e.message;speedBusy=false;await ping();}finally{speedBusy=false;}}
$('speed-slider').oninput=()=>{$('speed-value').textContent=youtubeRates[Number($('speed-slider').value)]+'×';$('speed-status').textContent='Puść suwak, aby ustawić tempo.';};
$('speed-slider').onchange=()=>setYoutubeSpeed(Number($('speed-slider').value));
$('speed-minus').onclick=()=>setYoutubeSpeed(Math.max(0,Number($('speed-slider').value)-1));
$('speed-plus').onclick=()=>setYoutubeSpeed(Math.min(6,Number($('speed-slider').value)+1));
$('extension-folder').onclick=()=>send({action:'extension_folder'});

$('speed-slider').onpointerdown=()=>{speedDragging=true;};$('speed-slider').onpointerup=$('speed-slider').onpointercancel=()=>{speedDragging=false;};

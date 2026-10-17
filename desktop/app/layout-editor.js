'use strict';
(()=>{
 const remote=document.querySelector('.remote'),toolbar=document.getElementById('layout-toolbar'),message=document.getElementById('layout-message');
 const key='couchpotato.layout.free.v2',entries=[],counts=new Map();let editing=false,drag=null,raf=0,previous={},positions={};
 // Keep the original DOM and original flow. Only the selected element is translated.
 const selector='.remote-top>button,.search-dock,.services>.service,.screen-tools>button,#screen-preview,.nav-grid>button,.touch-wheel,.wheel-seek>button,.under-wheel>button,.media-grid>button,.volume-rocker,.speed-control,.bottom-actions>button,.bottom-actions>a,.extra-grid>button,.brand-signature';
 const layer=document.createElement('div');layer.className='free-edit-layer';layer.hidden=true;remote.appendChild(layer);
 const spacer=document.createElement('div');spacer.className='free-layout-space';remote.appendChild(spacer);
 for(const node of remote.querySelectorAll(selector)){
  const base=node.id||['service','brave','key','shortcut','action'].map(k=>node.dataset[k]?k+':'+node.dataset[k]:'').find(Boolean)||node.classList[0];
  const count=(counts.get(base)||0)+1;counts.set(base,count);const id=base+':'+count;
  const grip=document.createElement('button');grip.type='button';grip.className='free-grip';grip.dataset.layoutId=id;
  const label=node.getAttribute('aria-label')||node.title||node.textContent.trim().slice(0,40)||'Element pilota';grip.setAttribute('aria-label','Przesuń: '+label);grip.title=label;
  const entry={node,id,grip,originalTransform:node.style.transform,originalZ:node.style.zIndex};entries.push(entry);layer.appendChild(grip);
  grip.onpointerdown=e=>{if(!editing||drag)return;e.preventDefault();e.stopPropagation();grip.setPointerCapture(e.pointerId);const p=positions[id]||{x:0,y:0};drag={entry,pointer:e.pointerId,startX:e.clientX,startY:e.clientY,scroll:window.scrollY,x:e.clientX,y:e.clientY,origin:{...p}};grip.classList.add('moving');message.textContent=label+' — przesuń i puść';tick();};
  grip.onpointermove=e=>{if(!drag||e.pointerId!==drag.pointer)return;drag.x=e.clientX;drag.y=e.clientY;move();};
  grip.onpointerup=e=>{if(drag&&e.pointerId===drag.pointer){finish();message.textContent='Pozycja zmieniona. Pozostałe elementy zostają na miejscu.';}};
  grip.onpointercancel=()=>finish(true);grip.onlostpointercapture=()=>finish(true);grip.onclick=e=>{e.preventDefault();e.stopPropagation();};grip.oncontextmenu=e=>e.preventDefault();
  grip.onkeydown=e=>{if(!editing||!['ArrowUp','ArrowDown','ArrowLeft','ArrowRight'].includes(e.key))return;e.preventDefault();const p=positions[id]||{x:0,y:0},step=(e.shiftKey?10:2)/remote.clientWidth;positions[id]={x:p.x+(e.key==='ArrowRight'?step:e.key==='ArrowLeft'?-step:0),y:p.y+(e.key==='ArrowDown'?step:e.key==='ArrowUp'?-step:0)};apply(entry);measure();};
 }
 function apply(e){const p=positions[e.id]||{x:0,y:0},w=remote.clientWidth;e.node.style.transform=p.x||p.y?`translate(${p.x*w}px,${p.y*w}px) ${e.originalTransform}`:e.originalTransform;e.node.style.zIndex=p.x||p.y?'6':e.originalZ;e.node.classList.toggle('free-shifted',!!(p.x||p.y));}
 function measure(){
  spacer.style.height='0px';const root=remote.getBoundingClientRect();let bottom=0;
  for(const e of entries){const r=e.node.getBoundingClientRect(),visible=!e.node.hidden&&r.width>0&&r.height>0;e.grip.hidden=!visible;if(!visible)continue;
   const x=r.left-root.left-remote.clientLeft,y=r.top-root.top-remote.clientTop;Object.assign(e.grip.style,{left:x+'px',top:y+'px',width:r.width+'px',height:r.height+'px'});bottom=Math.max(bottom,y+r.height);
  }
  spacer.style.height=Math.max(0,bottom-remote.clientHeight+22)+'px';
 }
 function move(){if(!drag)return;const d=drag,w=remote.clientWidth;positions[d.entry.id]={x:d.origin.x+(d.x-d.startX)/w,y:Math.min(8,d.origin.y+(d.y-d.startY+window.scrollY-d.scroll)/w)};
  // Keep the item reachable inside the pilot horizontally; do not align neighbours.
  apply(d.entry);const root=remote.getBoundingClientRect(),r=d.entry.node.getBoundingClientRect();let correction=0;if(r.left<root.left+4)correction=root.left+4-r.left;if(r.right>root.right-4)correction=root.right-4-r.right;positions[d.entry.id].x+=correction/w;if(r.top<root.top+4)positions[d.entry.id].y+=(root.top+4-r.top)/w;
  apply(d.entry);measure();}
 function tick(){if(!drag)return;const y=drag.y;if(y<70)window.scrollBy(0,-7);else if(y>window.innerHeight-130)window.scrollBy(0,7);move();raf=requestAnimationFrame(tick);}
 function finish(cancel=false){cancelAnimationFrame(raf);if(drag){if(cancel){positions[drag.entry.id]=drag.origin;apply(drag.entry);}drag.entry.grip.classList.remove('moving');drag=null;measure();}}
 function end(){finish();editing=false;window.couchLayoutEditing=false;remote.classList.remove('free-editing');layer.hidden=true;toolbar.hidden=true;measure();}
 function all(){entries.forEach(apply);measure();}
 document.getElementById('layout-edit').onclick=()=>{document.getElementById('preferences-dialog').close();if(window.stopRemoteGestures)window.stopRemoteGestures();previous=JSON.parse(JSON.stringify(positions));editing=true;window.couchLayoutEditing=true;remote.classList.add('free-editing');layer.hidden=false;toolbar.hidden=false;message.textContent='Przesuwasz oryginalny pilot. Bez siatki i automatycznego wyrównywania.';measure();};
 document.getElementById('layout-save').onclick=()=>{finish();try{localStorage.setItem(key,JSON.stringify(positions));end();}catch(e){message.textContent='Nie udało się zapisać. Spróbuj ponownie lub anuluj.';}};
 document.getElementById('layout-cancel').onclick=()=>{finish();positions=previous;all();end();};
 document.getElementById('layout-reset').onclick=()=>{finish();positions={};all();message.textContent='Domyślny układ. Przesuwaj elementy lub wybierz Gotowe.';};
 window.addEventListener('blur',()=>finish(true));document.addEventListener('visibilitychange',()=>{if(document.hidden)finish(true);});window.addEventListener('resize',()=>{finish();all();});window.addEventListener('scroll',()=>{if(editing&&!drag)measure();},{passive:true});
 remote.addEventListener('toggle',measure,true);new MutationObserver(records=>{if(!drag&&records.some(r=>!layer.contains(r.target)&&r.target!==spacer))measure();}).observe(remote,{subtree:true,attributes:true,attributeFilter:['hidden']});
 try{const saved=JSON.parse(localStorage.getItem(key)||'{}');for(const e of entries){const p=saved&&saved[e.id];if(p&&Number.isFinite(p.x)&&Number.isFinite(p.y)&&Math.abs(p.x)<=1&&Math.abs(p.y)<=8)positions[e.id]={x:p.x,y:p.y};}}catch(e){}
 all();window.addEventListener('load',all);
})();

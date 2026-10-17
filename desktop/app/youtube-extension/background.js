'use strict';
chrome.runtime.onMessage.addListener((message,sender,reply)=>{
 if(message.type!=='poll'||!sender.tab||!sender.url||!sender.url.startsWith('https://www.youtube.com/'))return;
 (async()=>{
  const tabs=await chrome.tabs.query({active:true,lastFocusedWindow:true});if(!tabs.length||tabs[0].id!==sender.tab.id)return {inactive:true};
  const {token}=await chrome.storage.local.get('token');if(!token)return {unpaired:true};
  const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),3000);
  try{const r=await fetch('http://127.0.0.1:8765/extension/poll',{method:'POST',headers:{'Content-Type':'application/json',Authorization:'Bearer '+token},body:JSON.stringify(message.data),signal:controller.signal});if(!r.ok)return {unpaired:r.status===401};return await r.json();}finally{clearTimeout(timer);}
 })().then(reply,()=>reply({offline:true}));return true;
});

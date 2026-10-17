'use strict';
(()=>{
 const client=crypto.randomUUID().replaceAll('-','');let ack=0,busy=false;
 async function poll(){
  if(busy||document.hidden)return;busy=true;
  try{const video=[...document.querySelectorAll('video')].find(v=>v.getBoundingClientRect().width>0);const result=await chrome.runtime.sendMessage({type:'poll',data:{client,ack,has_video:!!video,actual:video?video.playbackRate:null}});
   const c=result&&result.command;if(c&&video&&[1,1.25,1.5,1.75,2,3,4].includes(c.rate)&&Number.isInteger(c.id)&&c.id!==ack){try{video.playbackRate=c.rate;}finally{ack=c.id;}}
  }catch(e){}finally{busy=false;}
 }
 setInterval(poll,1000);poll();document.addEventListener('visibilitychange',()=>{if(!document.hidden)poll();});
})();

'use strict';
class RepeatButton {
 constructor(button, send, enabled, delay=190) {
  this.button=button;this.send=send;this.enabled=enabled;this.delay=delay;this.generation=0;this.timer=null;this.pointer=null;
  button.onpointerdown=e=>{if(!enabled()||this.pointer!==null)return;e.preventDefault();button.setPointerCapture(e.pointerId);this.pointer=e.pointerId;button.classList.add('holding');const g=++this.generation;send();this.timer=setTimeout(()=>this.pulse(g),450);};
  const stop=e=>{if(e.pointerId===this.pointer)this.stop();};
  button.onpointerup=stop;button.onpointercancel=stop;button.onlostpointercapture=stop;
  button.onclick=e=>{if(e.detail===0&&enabled())send();};button.oncontextmenu=e=>e.preventDefault();
 }
 async pulse(g){if(g!==this.generation||!this.enabled())return this.stop();await this.send(()=>g===this.generation&&this.enabled());if(g===this.generation)this.timer=setTimeout(()=>this.pulse(g),this.delay);}
 stop(){this.generation++;clearTimeout(this.timer);this.pointer=null;this.button.classList.remove('holding');}
}
if(typeof module!=='undefined')module.exports=RepeatButton;

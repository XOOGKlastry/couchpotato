'use strict';
// Short movement impulses only: no persistent Windows key or mouse button state.
class TouchRemote {
  constructor(pad, send, enabled, clock = () => Date.now()) {
    this.pad=pad;this.send=send;this.enabled=enabled;this.clock=clock;
    this.generation=0;this.onHold=()=>{};this.speed=1;this.points=new Map();this.dx=0;this.dy=0;this.wheel=0;this.busy=false;this.multi=false;this.hold=null;
    pad.onpointerdown=e=>this.down(e);
    pad.onpointermove=e=>this.move(e);
    pad.onpointerup=e=>this.up(e);
    pad.onpointercancel=e=>this.cancelPointer(e);
    pad.onlostpointercapture=e=>{if(this.points.has(e.pointerId))this.cancelPointer(e);};
    pad.oncontextmenu=e=>e.preventDefault();
  }
  centroid(){const p=[...this.points.values()];return p.reduce((sum,v)=>sum+v.y,0)/p.length;}
  down(e){
    if(!this.enabled()||this.hold)return;
    this.pad.setPointerCapture(e.pointerId);
    this.points.set(e.pointerId,{x:e.clientX,y:e.clientY,start:this.clock(),moved:0});
    if(this.points.size>1){this.multi=true;this.dx=this.dy=0;}
    this.pad.classList.add('active');
    this.pad.classList.toggle('scrolling',this.multi);
  }
  move(e){
    const p=this.points.get(e.pointerId);if(!p)return;
    const before=this.centroid(),x=e.clientX-p.x,y=e.clientY-p.y;
    p.moved+=Math.abs(x)+Math.abs(y);p.x=e.clientX;p.y=e.clientY;
    if(this.points.size>=2){
      const delta=this.centroid()-before;
      // Faster gestures cover more distance; slow gestures stay precise.
      const gain=2.5+Math.min(2,Math.abs(delta)/8);
      this.wheel=Math.max(-2400,Math.min(2400,this.wheel+delta*gain*this.speed));
    }else if(!this.multi){
      this.dx=Math.max(-600,Math.min(600,this.dx+x*1.7));
      this.dy=Math.max(-600,Math.min(600,this.dy+y*1.7));
    }
  }
  up(e){
    const p=this.points.get(e.pointerId);if(!p)return;
    if(!this.multi&&p.moved<7&&this.clock()-p.start<400){this.dx=this.dy=0;this.send({action:'click'});}
    this.points.delete(e.pointerId);
    if(!this.points.size){this.multi=false;this.pad.classList.remove('active','scrolling');}
  }
  cancelPointer(e){this.points.delete(e.pointerId);this.dx=this.dy=this.wheel=0;if(!this.points.size){this.multi=false;this.pad.classList.remove('active','scrolling');}}
  reset(){this.generation++;this.onHold(0);if(this.hold)this.hold.button.classList.remove('holding');this.points.clear();this.dx=this.dy=this.wheel=0;this.hold=null;this.multi=false;this.pad.classList.remove('active','scrolling');}
  bindHold(button,direction){
    button.onpointerdown=e=>{
      if(!this.enabled()||this.hold||this.points.size)return;
      e.preventDefault();button.setPointerCapture(e.pointerId);
      this.generation++;this.dx=this.dy=this.wheel=0;
      this.hold={button,id:e.pointerId,direction,start:this.clock(),lastPulse:this.clock()};
      this.wheel=direction*120;this.onHold(1);button.classList.add('holding');
    };
    const stop=e=>{
      if(this.hold&&this.hold.button===button&&this.hold.id===e.pointerId){
        this.generation++;this.hold=null;this.wheel=0;this.onHold(0);button.classList.remove('holding');
      }
    };
    button.onpointerup=stop;button.onpointercancel=stop;button.onlostpointercapture=stop;
    button.onclick=e=>{if(e.detail===0)this.send({action:'scroll',delta:direction*120});};
    button.oncontextmenu=e=>e.preventDefault();
  }
  async tick(){
    if(!this.enabled()){this.reset();return;}
    if(this.hold){
      const elapsed=this.clock()-this.hold.start;
      const multiplier=Math.min(12,1+Math.floor(elapsed/1500));
      this.onHold(multiplier);
      if(!this.busy&&elapsed>=280&&this.clock()-this.hold.lastPulse>=160){
        this.wheel=this.hold.direction*60*multiplier;
        this.hold.lastPulse=this.clock();
      }
    }
    if(this.busy)return;
    const delta=Math.max(-2400,Math.min(2400,Math.round(this.wheel)));
    const dx=Math.max(-300,Math.min(300,Math.round(this.dx))),dy=Math.max(-300,Math.min(300,Math.round(this.dy)));
    if(!delta&&!dx&&!dy)return;
    this.busy=true;
    const generation=this.generation;
    const valid=()=>generation===this.generation&&this.enabled();
    try{
      if(delta){this.wheel-=delta;if(!await this.send({action:'scroll',delta},valid))this.reset();}
      else{this.dx-=dx;this.dy-=dy;if(!await this.send({action:'move',dx,dy},valid))this.reset();}
    }finally{this.busy=false;}
  }
}
if(typeof module!=='undefined')module.exports=TouchRemote;

'use strict';
class ScreenViewer {
 constructor(stage,image,click){this.stage=stage;this.image=image;this.click=click;this.points=new Map();this.scale=1;this.x=0;this.y=0;this.gesture=false;this.drag=0;this.started=0;
 stage.onpointerdown=e=>{e.preventDefault();stage.setPointerCapture(e.pointerId);this.points.set(e.pointerId,{x:e.clientX,y:e.clientY});if(this.points.size===1){this.drag=0;this.started=Date.now();this.gesture=false;}else this.gesture=true;};
 stage.onpointermove=e=>{const p=this.points.get(e.pointerId);if(!p)return;const before=[...this.points.values()];const oldDist=before.length===2?Math.hypot(before[0].x-before[1].x,before[0].y-before[1].y):0;const dx=e.clientX-p.x,dy=e.clientY-p.y;this.drag+=Math.abs(dx)+Math.abs(dy);p.x=e.clientX;p.y=e.clientY;
 if(this.points.size===2&&oldDist>0){const a=[...this.points.values()],r=stage.getBoundingClientRect();this.zoom(this.scale*Math.hypot(a[0].x-a[1].x,a[0].y-a[1].y)/oldDist,(a[0].x+a[1].x)/2-r.left-r.width/2,(a[0].y+a[1].y)/2-r.top-r.height/2);}
 else if(this.scale>1){this.x+=dx;this.y+=dy;this.render();}};
 stage.onpointerup=e=>{if(!this.points.has(e.pointerId))return;this.points.delete(e.pointerId);if(!this.points.size&&!this.gesture&&this.drag<9&&Date.now()-this.started<500){const r=image.getBoundingClientRect(),x=(e.clientX-r.left)/r.width,y=(e.clientY-r.top)/r.height;if(!image.hidden&&x>=0&&x<=1&&y>=0&&y<=1)this.click(x,y);} };
 const cancel=e=>{this.points.delete(e.pointerId);this.gesture=true;};stage.onpointercancel=cancel;stage.onlostpointercapture=cancel;stage.oncontextmenu=e=>e.preventDefault();
 }
 zoom(scale,cx=0,cy=0){const next=Math.min(6,Math.max(1,scale)),ratio=next/this.scale;this.x=cx-(cx-this.x)*ratio;this.y=cy-(cy-this.y)*ratio;this.scale=next;this.render();}
 render(){const maxX=Math.max(0,(this.image.offsetWidth*this.scale-this.stage.clientWidth)/2),maxY=Math.max(0,(this.image.offsetHeight*this.scale-this.stage.clientHeight)/2);this.x=Math.max(-maxX,Math.min(maxX,this.x));this.y=Math.max(-maxY,Math.min(maxY,this.y));this.image.style.transform=`translate(${this.x}px,${this.y}px) scale(${this.scale})`;if(this.onzoom)this.onzoom(this.scale);}
 reset(){this.points.clear();this.gesture=true;this.scale=1;this.x=this.y=0;this.render();}
}
if(typeof module!=='undefined')module.exports=ScreenViewer;

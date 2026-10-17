const assert=require('assert');
const TouchRemote=require('./KanapaTV/gestures.js');
const classes=new Set();const pad={setPointerCapture(){},classList:{add(...v){v.forEach(x=>classes.add(x))},remove(...v){v.forEach(x=>classes.delete(x))},toggle(x,b){b?classes.add(x):classes.delete(x)}}};
let now=0;const calls=[];const remote=new TouchRemote(pad,async d=>{calls.push(d);return true},()=>true,()=>now);
const e=(id,x,y)=>({pointerId:id,clientX:x,clientY:y,preventDefault(){}});
(async()=>{
 remote.down(e(1,10,10));remote.move(e(1,30,30));await remote.tick();assert.equal(calls.at(-1).action,'move');remote.up(e(1,30,30));
 const before=calls.length;remote.down(e(1,20,20));remote.down(e(2,40,20));remote.move(e(1,20,0));remote.move(e(2,40,0));await remote.tick();assert.equal(calls.at(-1).action,'scroll');assert(calls.at(-1).delta<0);remote.up(e(2,40,0));remote.move(e(1,80,80));await remote.tick();remote.up(e(1,80,80));assert.equal(calls.length,before+1,'No phantom click or cursor jump after multi-touch');
 remote.down(e(1,1,1));remote.up(e(1,1,1));assert.equal(calls.at(-1).action,'click');
 const button={setPointerCapture(){},classList:pad.classList};remote.bindHold(button,-1);
 button.onpointerdown(e(3,0,0));await remote.tick();now=500;await remote.tick();const slow=Math.abs(calls.at(-1).delta);now=2500;await remote.tick();assert(Math.abs(calls.at(-1).delta)>slow,'Holding accelerates');button.onpointerup(e(3,0,0));const end=calls.length;now=5000;await remote.tick();assert.equal(calls.length,end,'Release stops');
 button.onpointerdown(e(3,0,0));remote.reset();await remote.tick();assert.equal(calls.length,end,'Blur reset stops');
 remote.down(e(1,1,1));remote.move(e(1,20,20));remote.cancelPointer(e(1,20,20));await remote.tick();assert.equal(calls.length,end,'Cancel discards queued movement');
 console.log('PASS: cursor, two-finger direction, no phantom clicks, tap, hold acceleration, release, blur, cancel.');
})().catch(e=>{console.error(e);process.exitCode=1});

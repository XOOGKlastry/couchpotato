const assert=require('assert'),TouchRemote=require('./KanapaTV/gestures.js');
let now=0;let rate=0;const events=[],queued=[];
const ui={setPointerCapture(){},classList:{add(){},remove(){},toggle(){}}};
const r=new TouchRemote(ui,async(data,valid)=>{queued.push({data,valid});events.push(data);return true},()=>true,()=>now);
r.onHold=n=>rate=n;const button={...ui};r.bindHold(button,1);
const event={pointerId:1,preventDefault(){},detail:1};
(async()=>{
 button.onpointerdown(event);assert.equal(rate,1);await r.tick();
 for(const [t,expected]of [[1499,1],[1500,2],[3000,3],[4500,4],[9000,7],[30000,12]]){
  now=t;await r.tick();assert.equal(rate,expected);assert(events.at(-1).delta<=720);
 }
 const pending=queued.at(-1);assert(pending.valid());button.onpointerup(event);assert.equal(rate,0);assert(!pending.valid(),'Released hold must not dispatch stale queued input');
 const count=events.length;now+=1000;await r.tick();assert.equal(events.length,count);
 button.onpointerdown(event);assert.equal(rate,1);r.reset();assert.equal(rate,0);await r.tick();
 console.log('PASS: 1x/2x/3x/4x progression, upper cap, release/reset and cancellation of delayed commands.');
})().catch(e=>{console.error(e);process.exitCode=1});

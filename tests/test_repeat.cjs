const assert=require('assert'),Repeat=require('./KanapaTV/extras.js');
let tasks=[],sent=0,queued=[];
global.setTimeout=f=>{tasks.push(f);return tasks.length};global.clearTimeout=()=>{};
const b={setPointerCapture(){},classList:{add(){},remove(){}}};
const r=new Repeat(b,async valid=>{if(valid)queued.push(valid);else sent++},()=>true);
(async()=>{
 b.onpointerdown({pointerId:1,preventDefault(){}});assert.equal(sent,1);
 await tasks.shift()();assert.equal(queued.length,1);assert(queued[0]());
 b.onpointerup({pointerId:1});assert(!queued[0](),'Queued repeat must expire on release');
 while(tasks.length)await tasks.shift()();assert.equal(queued.length,1);
 b.onclick({detail:1});assert.equal(sent,1);b.onclick({detail:0});assert.equal(sent,2);
 b.onpointerdown({pointerId:2,preventDefault(){}});r.stop();while(tasks.length)await tasks.shift()();assert.equal(queued.length,1);
 console.log('PASS: media hold, release, cancellation, keyboard activation, no duplicate tap');
})();

const fs=require('fs'),vm=require('vm'),assert=require('assert');let handle;
const video={currentTime:40,duration:100,seekable:{length:1,start:()=>0,end:()=>100},getBoundingClientRect:()=>({width:1280,height:720})};
vm.runInNewContext(fs.readFileSync('KanapaTV/youtube-extension/hbo-seek.js','utf8'),{document:{addEventListener:(name,fn,capture)=>{assert(capture);handle=fn},querySelectorAll:()=>[video]}});
function press(key,extra={}){let stopped=false;handle({key,composedPath:()=>[{closest:()=>null}],preventDefault(){stopped=true},stopImmediatePropagation(){},...extra});return stopped;}
assert(press('ArrowRight'));assert.equal(video.currentTime,45);assert(press('ArrowLeft'));assert.equal(video.currentTime,40);
for(let i=0;i<3;i++)press('ArrowRight');assert.equal(video.currentTime,55);
video.currentTime=98;press('ArrowRight');assert.equal(video.currentTime,100);video.currentTime=2;press('ArrowLeft');assert.equal(video.currentTime,0);
assert(!press('ArrowRight',{composedPath:()=>[{closest:()=>({})}]}));assert.equal(video.currentTime,0);
assert(!press('ArrowRight',{ctrlKey:true}));video.duration=Infinity;assert(!press('ArrowRight'));video.duration=100;video.seekable.length=0;assert(!press('ArrowRight'));
console.log('PASS HBO: ±5 seconds, hold repetitions, boundaries, input/modifier guards, unseekable/live ignored');

const fs=require('fs'),vm=require('vm'),assert=require('assert');
const html=fs.readFileSync('KanapaTV/index.html','utf8');
const ids=[...html.matchAll(/\bid="([^"]+)"/g)].map(x=>x[1]);assert.equal(new Set(ids).size,ids.length,'Duplicate ids');
for(const m of html.matchAll(/href="#([^"]+)"/g))assert(ids.includes(m[1]),'Missing icon '+m[1]);
class Element{
 constructor(id='',dataset={}){this.id=id;this.dataset=dataset;this.hidden=false;this.disabled=false;this.value='';this.textContent='';this.open=false;this.style={};this.offsetWidth=300;this.offsetHeight=180;this.clientWidth=300;this.clientHeight=180;this.listeners={};this.classList={add(){},remove(){},toggle(){}};}
 addEventListener(name,fn){this.listeners[name]=fn;}
 showModal(){this.open=true;}close(){this.open=false;}scrollIntoView(){}setPointerCapture(){}appendChild(){}focus(){}blur(){}setAttribute(){}removeAttribute(){}
}
const elements=Object.fromEntries(ids.map(id=>[id,new Element(id)]));
const groups={};for(const [attr,key] of [['action','action'],['service','service'],['key','key'],['scroll','scroll'],['shortcut','shortcut'],['brave','brave'],['hold-scroll','holdScroll']])groups[`[data-${attr}]`]=[...html.matchAll(new RegExp(`data-${attr}="([^"]+)"`,'g'))].map(m=>new Element('',{[key]:m[1]}));
const click=new Element(),intro=new Element(),requests=[];
let state='idle',seconds=0;
const context={RepeatButton:require('./KanapaTV/extras.js'),ScreenViewer:require('./KanapaTV/viewer.js'),navigator:{userAgent:'couchpotatoAndroid/1.1'},TouchRemote:require('./KanapaTV/gestures.js'), URL, window:{addEventListener(){}}, localStorage:{getItem:()=>null,setItem(){},removeItem(){}}, document:{getElementById:id=>{assert(elements[id],id);return elements[id]},querySelectorAll:s=>groups[s]||[],querySelector:s=>s==='.intro'?intro:click,addEventListener(){},hidden:false,createElement:()=>new Element()},sessionStorage:{getItem:()=>null,setItem(){},removeItem(){}},location:{hostname:'192.168.1.10'},setTimeout:()=>1,clearTimeout(){},setInterval:()=>1,Date,Math,Error,TypeError,AbortController,console,
 fetch:async(path,options)=>{const data=JSON.parse(options.body);requests.push({path,data});if(path==='/pair')return {ok:true,json:async()=>({token:'test-token'})};if(data.action==='shutdown'){state='countdown';seconds=30;}if(data.action==='cancel_shutdown'){state='idle';seconds=0;}return {ok:true,json:async()=>({power:{state,seconds}})};}
};
vm.createContext(context);vm.runInContext(fs.readFileSync('KanapaTV/app.js','utf8'),context);
(async()=>{
 elements.pin.value='01x23';elements.pin.listeners.input();assert.equal(elements.pin.value,'0123');
 await elements.pairform.onsubmit({preventDefault(){},submitter:new Element()});
 assert.equal(requests[0].data.code,'0123');assert.equal(elements.controls.hidden,false);
 assert.equal(elements['power-button'].disabled,false);
 const before=requests.length;elements['power-button'].onclick();assert(elements['power-dialog'].open);assert.equal(requests.length,before);
 elements['keep-watching'].onclick();assert(!elements['power-dialog'].open);assert.equal(requests.length,before);
 elements['power-button'].onclick();await elements['confirm-shutdown'].onclick();
 assert(requests.some(r=>r.data.action==='shutdown'&&r.data.confirmed===true));assert(!elements['power-dialog'].open);assert.equal(elements['power-banner'].hidden,false);
 await elements['cancel-shutdown'].onclick();assert.equal(elements['power-banner'].hidden,true);
 elements.text.value='Zażółć 😀';await elements.textform.onsubmit({preventDefault(){}});
 assert(requests.some(r=>r.data.action==='text'&&r.data.text==='Zażółć 😀'));
 for(const b of groups['[data-service]'])await b.onclick();
 for(const b of groups['[data-key]'])await b.onclick();
 for(const b of groups['[data-shortcut]'])await b.onclick();
 for(const b of groups['[data-action]'])await b.onclick();assert(requests.some(r=>r.data.action==='open_link_tab'));assert(requests.some(r=>r.data.action==='right_click'));assert.equal(requests.filter(r=>r.data.action==='open').length,4);
 elements.pad.onpointerdown({pointerId:1,clientX:0,clientY:0});elements.pad.onpointerup({pointerId:1});
 await vm.runInContext('queue',context);
 assert.equal(requests.filter(r=>r.data.action==='click').length,1);
 assert(html.indexOf('id="textform"')<html.indexOf('class="services-section'));
 assert(html.includes('maxlength="4"'));
 assert.equal(requests.filter(r=>r.data.action==='shortcut').length,6);
 elements['edit-brave'].onclick();assert(elements['brave-dialog'].open);
 for(let i=0;i<3;i++){elements['brave-name-'+i].value='Serwis '+i;elements['brave-url-'+i].value='https://example.com/'+i;}
 elements['brave-form'].onsubmit({preventDefault(){}});assert(!elements['brave-dialog'].open);
 for(const b of groups['[data-brave]'])await b.onclick();
 await vm.runInContext('queue',context);assert.equal(requests.filter(r=>r.data.action==='open_brave').length,3);
 await elements['new-chrome-tab'].onclick();
 assert(requests.some(r=>r.data.action==='new_chrome_tab'));
 elements.text.value='kawa';await elements.textform.onsubmit({preventDefault(){}});
 assert(requests.some(r=>r.data.action==='chrome_search'&&r.data.text==='kawa'));
 console.log('PASS: DOM wiring, icons, 4-digit pairing, top input, all service/key/scroll buttons, touch tap, power confirmation and cancellation.');
})().catch(e=>{console.error(e);process.exitCode=1});

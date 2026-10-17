'use strict';
// HBO's own arrow handling is inconsistent. Use the existing remote's arrow
// keys, but move the media timeline by exactly five seconds when seekable.
(()=>{
 document.addEventListener('keydown',event=>{
  if(!['ArrowLeft','ArrowRight'].includes(event.key)||event.ctrlKey||event.altKey||event.metaKey||event.shiftKey)return;
  const target=event.composedPath()[0];
  if(target&&(target.isContentEditable||target.closest?.('input,textarea,select,[contenteditable="true"]')))return;
  const videos=[...document.querySelectorAll('video')].filter(v=>{const r=v.getBoundingClientRect();return r.width>0&&r.height>0;}).sort((a,b)=>{const x=a.getBoundingClientRect(),y=b.getBoundingClientRect();return y.width*y.height-x.width*x.height;});
  const video=videos[0];if(!video||!Number.isFinite(video.duration)||video.duration<=0||!video.seekable.length)return;
  const current=video.currentTime;let start,end;
  for(let i=0;i<video.seekable.length;i++){if(current>=video.seekable.start(i)&&current<=video.seekable.end(i)){start=video.seekable.start(i);end=video.seekable.end(i);break;}}
  if(start===undefined)return;
  const next=Math.max(start,Math.min(end,current+(event.key==='ArrowRight'?5:-5)));
  try{video.currentTime=next;event.preventDefault();event.stopImmediatePropagation();}catch(_){}
 },true);
})();

// Text-only contrast probe; gradients and opacity need manual inspection.
module.exports = () => {
 const rgb=s=>{const c=(s.match(/[\d.]+/g)||[]).map(Number);return s.startsWith('color(srgb ')?c.map((v,i)=>i<3?v*255:v):c;};
 const lum=c=>c.slice(0,3).map(v=>{v/=255;return v<=.04045?v/12.92:((v+.055)/1.055)**2.4}).reduce((a,v,i)=>a+v*[.2126,.7152,.0722][i],0);
 const out=[], seen=new Set();
 for(const el of document.querySelectorAll('body *')) {
  if(!el.getClientRects().length||el.closest('[hidden],[inert]')||getComputedStyle(el).visibility==='hidden'||!Array.from(el.childNodes).some(n=>n.nodeType===3&&n.textContent.trim()))continue;
  const s=getComputedStyle(el);if(el.closest('button:disabled, [aria-hidden=true]')||Number(s.opacity)<1)continue;
  let bg=[255,255,255],chain=[];for(let x=el;x;x=x.parentElement)chain.unshift(x);
  let gradient=false;for(const x of chain){const st=getComputedStyle(x),c=rgb(st.backgroundColor);if(st.backgroundImage!=='none')gradient=true;if(c.length>=3){const a=c.length===4?c[3]:1;bg=bg.map((v,i)=>c[i]*a+v*(1-a));}}
  if(gradient)continue;
  const color=rgb(s.color);if(color.length<3)continue;const alpha=color.length===4?color[3]:1;const fg=color.slice(0,3).map((v,i)=>v*alpha+bg[i]*(1-alpha));const l1=lum(fg),l2=lum(bg),ratio=(Math.max(l1,l2)+.05)/(Math.min(l1,l2)+.05);const limit=(parseFloat(s.fontSize)>=24||(parseFloat(s.fontSize)>=18.66&&parseInt(s.fontWeight)>=700))?3:4.5;
  const key=s.color+bg.join(',');if(ratio<limit-.05&&!seen.has(key)){seen.add(key);out.push({tag:el.tagName,cls:el.className,text:el.textContent.trim().slice(0,65),ratio:+ratio.toFixed(2),fg:s.color,bg});}
 }
 return out.slice(0,12);
};

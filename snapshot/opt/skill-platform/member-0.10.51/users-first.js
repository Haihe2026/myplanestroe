 'use strict';
document.addEventListener('DOMContentLoaded',()=>{
 function reorder(){const section=document.getElementById('users-directory'),summary=document.getElementById('first-use-users-directory');if(section&&summary&&summary.parentElement===section&&section.lastElementChild!==summary)section.append(summary);}
 reorder();const observer=new MutationObserver(reorder);observer.observe(document.body,{childList:true,subtree:true});
 function refreshVisible(){const section=document.getElementById('users-directory');if(document.hidden||!section||section.hidden||!section.getClientRects().length)return;const refresh=section.querySelector('.ud-controls button[type="button"]');if(refresh&&!refresh.disabled)refresh.click();}
 const interval=setInterval(refreshVisible,15000);
 document.addEventListener('visibilitychange',()=>{if(!document.hidden)refreshVisible();});
 window.addEventListener('pagehide',()=>{clearInterval(interval);observer.disconnect();},{once:true});
});

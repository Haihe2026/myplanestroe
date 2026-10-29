'use strict';
document.getElementById('copy-example').addEventListener('click',async()=>{
 const text=document.getElementById('example-text');
 const status=document.getElementById('copy-status');
 try{await navigator.clipboard.writeText(text.textContent);status.textContent='已复制。';}
 catch{const range=document.createRange();range.selectNodeContents(text);const selection=window.getSelection();selection.removeAllRanges();selection.addRange(range);status.textContent='已选中示例，请复制。';}
});

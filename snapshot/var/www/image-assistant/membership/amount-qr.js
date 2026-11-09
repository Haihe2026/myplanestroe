'use strict';
// Match the authoritative order amount in fen. Never substitute a nearby amount.
window.mpsAmountQr=function(fen,img,save){
 const codes={"500":"5.png", "12800": "128.jpg", "16600": "166.jpg", "1900": "19.jpg", "19000": "190.jpg", "19800": "198.jpg", "19900": "199.jpg", "2900": "29.jpg", "33600": "336.jpg", "36500": "365.jpg", "3900": "39.jpg", "4500": "45.jpg", "4900": "49.jpg", "8900": "89.jpg", "9800": "98.jpg", "9900": "99.jpg", "99900": "999.jpg"};
 const name=Number.isSafeInteger(fen)?codes[fen]:null;
 if(img){img.removeAttribute('src');img.hidden=true;}
 if(save){save.removeAttribute('href');save.hidden=true;}
 if(!name){const message='暂未配置 ¥'+(Number(fen)/100).toFixed(2)+' 的收款码，请联系客服。';window.alert(message);throw new Error(message);}
 const url='/membership/amount-qr/'+name+'?v=20261104';
 if(img){img.src=url;img.hidden=false;img.style.height='auto';img.style.objectFit='contain';}
 if(save){save.href=url;save.hidden=false;}
 return url;
};

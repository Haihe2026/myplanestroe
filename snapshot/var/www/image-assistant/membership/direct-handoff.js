'use strict';
function routeMembershipTicket(){
 const params=new URLSearchParams(location.hash.slice(1));
 if(params.has('ticket')){
  location.replace('/membership/gemini/'+location.hash);
  return true;
 }
 return false;
}
routeMembershipTicket();
window.addEventListener('hashchange',routeMembershipTicket);

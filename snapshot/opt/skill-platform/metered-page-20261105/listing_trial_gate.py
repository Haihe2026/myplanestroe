import metered
# Only new free-trial use requires WeChat; do not reset existing trial/paid states.
from listing_store import Listing,Error
old_enroll,old_quote,old_me=Listing.enroll,Listing.quote,Listing.me
def enroll(self,uid,key,accepted):
 if not metered.bound(self.store,uid):raise Error(403,'WECHAT_REQUIRED')
 return old_enroll(self,uid,key,accepted)
def quote(self,uid,key,scope):
 with self.store.connect() as c:r=c.execute('SELECT trial_state FROM listing_accounts WHERE account_id=?',(uid,)).fetchone()
 if r and r['trial_state']=='available' and not metered.bound(self.store,uid):raise Error(403,'WECHAT_REQUIRED')
 return old_quote(self,uid,key,scope)
def me(self,uid):
 result=old_me(self,uid)
 if result['trial_state']=='available' and not metered.bound(self.store,uid):raise Error(403,'WECHAT_REQUIRED')
 return result
Listing.enroll=enroll;Listing.quote=quote;Listing.me=me

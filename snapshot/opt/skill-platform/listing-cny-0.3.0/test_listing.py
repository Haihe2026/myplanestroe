import copy
import json
import sqlite3
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from listing_store import Listing, Error, sha, canonical


class Database:
    def __init__(self,path):self.path=path
    @contextmanager
    def connect(self):
        c=sqlite3.connect(self.path,timeout=10);c.row_factory=sqlite3.Row
        try:
            with c:yield c
        finally:c.close()


class MockDelivery:
    ready=True
    def recover_verified(self,task,evidence,scope):
        if evidence!='synthetic-valid':raise Error(409,'NO_VERIFIED_DELIVERY')
        return dict(artifact_id='synthetic-'+task,scope_hash=sha(canonical(scope)),deliveries=[dict(target=t,content=dict(title='合成标题',checks=['仅测试'])) for t in scope['targets']])


class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.db=Database(str(Path(self.tmp.name)/'synthetic.db'));self.count=0
        with self.db.connect() as c:
            c.executescript("CREATE TABLE users(id PRIMARY KEY,balance);INSERT INTO users VALUES('synthetic',77),('other',88);CREATE TABLE trade_wallets(account_id,balance_fen);INSERT INTO trade_wallets VALUES('synthetic',1234);CREATE TABLE pet_accounts(user_id,trial_photos);INSERT INTO pet_accounts VALUES('synthetic',1);")
        self.cfg=json.loads(Path(__file__).with_name('listing-config.json').read_text(encoding='utf8'))
        self.cfg.update(charging_enabled=True,delivery_adapter_confirmed=True)
        for p in self.cfg['platforms']:p.update(status='available',publicly_available=True)
        self.cfg['terms']=dict(confirmed=True,unit_scope='synthetic-one-sku-platform-country',trial_scope='same',included_revisions=0,balance_validity='synthetic-no-expiry',refund_policy='synthetic-only')
        self.api=Listing(self.db,self.cfg,MockDelivery());self.api.enroll('synthetic',self.key(),True)
    def tearDown(self):self.tmp.cleanup()
    def key(self):self.count+=1;return 'synthetic-key-'+str(self.count).zfill(8)
    def scope(self):return dict(sku='synthetic-sku',targets=[dict(platform='amazon',country='US'),dict(platform='temu',country='GB'),dict(platform='etsy',country='DE')])
    def reserve(self):
        q=self.api.quote('synthetic',self.key(),self.scope());return self.api.reserve('synthetic',self.key(),q['id'],True)['id']
    def use(self):
        tid=self.reserve();return self.api.complete('synthetic',self.key(),tid,'synthetic-valid')
    def topup(self,n):
        o=self.api.order('synthetic',self.key(),'listing_cny_'+str(n)+'_v1','synthetic-listing','workbuddy_skill')
        self.api.report('synthetic',self.key(),o['id']);self.api.confirm_receipt('synthetic',self.key(),o['id'],n*100,'synthetic-receipt-'+self.key(),'synthetic-ops',True);return o
    def test_default_closed(self):
        a=Listing(self.db)
        self.assertFalse(a.ready())
        with self.assertRaises(Error) as ctx:a.order('synthetic',self.key(),'listing_cny_39_v1','synthetic-listing','workbuddy_skill')
        self.assertEqual(ctx.exception.status,503)
    def test_only_existing_accepted_account_enrolled(self):
        with self.assertRaises(Error):self.api.enroll('missing',self.key(),True)
        with self.assertRaises(Error):self.api.enroll('other',self.key(),False)
        with self.assertRaises(Error):self.api.me('other')
    def test_trial_once_across_channels_and_reinstall(self):
        self.use();self.api.enroll('synthetic',self.key(),True)
        self.assertEqual(self.api.me('synthetic')['trial_state'],'used')
        with self.assertRaises(Error) as ctx:self.reserve()
        self.assertEqual(ctx.exception.status,402)
    def test_trial_priority_and_hold(self):
        self.topup(39);tid=self.reserve();self.assertEqual(self.api.me('synthetic')['available_fen'],3900)
        with self.assertRaises(Error) as ctx:self.reserve()
        self.assertEqual(ctx.exception.code,'TRIAL_IN_PROGRESS')
        self.api.complete('synthetic',self.key(),tid,'synthetic-valid');self.assertEqual(self.api.me('synthetic')['balance_fen'],3900)
    def test_amount_schedules_and_tail(self):
        self.use()
        for n,units,tail in [(39,130,0),(99,330,0),(190,633,10)]:
            with self.subTest(n=n):
                self.topup(n)
                for i in range(units):self.use()
                self.assertEqual(self.api.me('synthetic')['available_fen'],tail)
                with self.assertRaises(Error) as ctx:self.reserve()
                self.assertEqual(ctx.exception.status,402)
        self.topup(39);self.assertEqual(self.api.me('synthetic')['balance_fen'],3910)
    def test_report_not_paid_and_repeat_credit(self):
        k=self.key();o=self.api.order('synthetic',k,'listing_cny_39_v1','synthetic-listing','workbuddy_expert')
        self.assertEqual(o,self.api.order('synthetic',k,'listing_cny_39_v1','synthetic-listing','workbuddy_expert'))
        self.api.report('synthetic',self.key(),o['id']);self.assertEqual(self.api.me('synthetic')['balance_fen'],0)
        for i in range(2):self.api.confirm_receipt('synthetic',self.key(),o['id'],3900,'synthetic-fixed-transaction','synthetic-ops',True)
        self.assertEqual(self.api.me('synthetic')['balance_fen'],3900)
    def test_receipt_exclusion_and_amount(self):
        o=self.topup(39);other=self.api.order('synthetic',self.key(),'listing_cny_39_v1','synthetic-listing','skillhub');self.api.report('synthetic',self.key(),other['id'])
        with self.db.connect() as c:tx=c.execute('SELECT transaction_id FROM listing_orders WHERE id=?',(o['id'],)).fetchone()[0]
        for amount,transaction in [(3901,'synthetic-other'),(3900,tx)]:
            with self.assertRaises(Error):self.api.confirm_receipt('synthetic',self.key(),other['id'],amount,transaction,'synthetic-ops',True)
    def test_idem_conflict_and_ownership(self):
        key=self.key();q=self.api.quote('synthetic',key,self.scope())
        with self.assertRaises(Error):self.api.quote('synthetic',key,dict(self.scope(),sku='different'))
        tid=self.api.reserve('synthetic',self.key(),q['id'],True)['id']
        with self.assertRaises(Error):self.api.task('other',tid)
        with self.assertRaises(Error):self.api.reserve('other',self.key(),q['id'],True)
    def test_result_requires_verified_evidence_and_recovery(self):
        tid=self.reserve()
        with self.assertRaises(Error):self.api.complete('synthetic',self.key(),tid,{'success':True})
        self.assertEqual(self.api.me('synthetic')['trial_state'],'held')
        result=self.api.complete('synthetic',self.key(),tid,'synthetic-valid')
        self.assertEqual(self.api.task('synthetic',tid)['result'],result)
        self.assertEqual(self.api.complete('synthetic',self.key(),tid,'synthetic-valid'),result)
        with self.assertRaises(Error):self.api.release_confirmed_failure('synthetic',self.key(),tid,'confirmed_failure')
    def test_failure_once_unknown_holds(self):
        tid=self.reserve();self.api.release_confirmed_failure('synthetic',self.key(),tid,'unknown')
        self.assertEqual(self.api.me('synthetic')['trial_state'],'held')
        for i in range(2):self.api.release_confirmed_failure('synthetic',self.key(),tid,'confirmed_failure')
        self.assertEqual(self.api.me('synthetic')['trial_state'],'available')
        with self.assertRaises(Error):self.api.complete('synthetic',self.key(),tid,'synthetic-valid')
    def test_unrelated_balances_preserved(self):
        self.topup(39);self.use();self.use()
        with self.db.connect() as c:
            self.assertEqual(c.execute("SELECT balance FROM users WHERE id='synthetic'").fetchone()[0],77)
            self.assertEqual(c.execute('SELECT balance_fen FROM trade_wallets').fetchone()[0],1234)
            self.assertEqual(c.execute('SELECT trial_photos FROM pet_accounts').fetchone()[0],1)
    def test_price_snapshot(self):
        self.use();self.topup(39);q=self.api.quote('synthetic',self.key(),self.scope());self.api.config['unit_price_fen']=60
        t=self.api.reserve('synthetic',self.key(),q['id'],True)['id'];self.api.complete('synthetic',self.key(),t,'synthetic-valid')
        self.assertEqual(self.api.me('synthetic')['balance_fen'],3870)

    def test_all_platforms_one_paid_charge(self):
        self.use();self.topup(39)
        targets=[dict(platform=p,country='GB') for p in ['amazon','temu','tiktok-shop','etsy','ebay','shopee']]
        targets += [dict(platform='shopify',country='GB',site='synthetic.example'),dict(platform='independent-site',country='GB',site='other.example')]
        q=self.api.quote('synthetic',self.key(),dict(sku='one-sku',targets=targets))
        self.assertEqual(q['reserve_fen'],30);self.assertEqual(q['units'],1)
        t=self.api.reserve('synthetic',self.key(),q['id'],True)['id']
        result=self.api.complete('synthetic',self.key(),t,'synthetic-valid')
        self.assertEqual(len(result['deliveries']),8);self.assertEqual(self.api.me('synthetic')['balance_fen'],3870)
    def test_unlimited_same_task_revisions_keep_history_no_charge(self):
        self.topup(39);self.use();tid=self.reserve();self.api.complete('synthetic',self.key(),tid,'synthetic-valid')
        before=self.api.me('synthetic')
        for i in range(25):self.api.revise('synthetic',self.key(),tid,'synthetic-valid')
        self.assertEqual(self.api.me('synthetic'),before)
        with self.db.connect() as c:self.assertEqual(c.execute('SELECT count(*) FROM listing_artifacts WHERE task_id=?',(tid,)).fetchone()[0],26)
    def test_partial_bundle_never_settles(self):
        class Partial(MockDelivery):
            def recover_verified(self,task,evidence,scope):
                a=super().recover_verified(task,evidence,scope);a['deliveries']=a['deliveries'][:1];return a
        self.api.verifier=Partial();tid=self.reserve()
        with self.assertRaises(Error):self.api.complete('synthetic',self.key(),tid,'synthetic-valid')
        self.assertEqual(self.api.me('synthetic')['trial_state'],'held')
    def test_concurrent_trial_only_one_reservation(self):
        from concurrent.futures import ThreadPoolExecutor
        qs=[self.api.quote('synthetic',self.key(),self.scope())['id'] for _ in range(2)]
        keys=[self.key(),self.key()]
        def run(i):
            try:return self.api.reserve('synthetic',keys[i],qs[i],True)['state']
            except Error as e:return e.code
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(run,range(2)))
        self.assertEqual(results.count('reserved'),1);self.assertEqual(results.count('REQUOTE_REQUIRED'),1)
    def test_same_shopify_site_deduplicated(self):
        scope=dict(sku='one',targets=[dict(platform='shopify',country='GB',site='synthetic.example'),dict(platform='independent-site',country='GB',site='synthetic.example')])
        q=self.api.quote('synthetic',self.key(),scope);self.assertEqual(len(q['scope']['targets']),1)
        self.assertEqual(q['scope']['targets'][0]['platform'],'shopify')
    def test_no_shopee_us_or_unopened_platform(self):
        with self.assertRaises(Error):self.api.quote('synthetic',self.key(),dict(sku='one',targets=[dict(platform='shopee',country='US')]))
        self.api.config['platforms'][0]['status']='planned'
        with self.assertRaises(Error):self.api.quote('synthetic',self.key(),self.scope())
    def test_balance_does_not_expire(self):
        self.topup(190);self.api.clock=lambda:2000000000
        self.assertEqual(self.api.me('synthetic')['balance_fen'],19000)
    def test_revision_replay_and_foreign_scope_rejected(self):
        tid=self.reserve();self.api.complete('synthetic',self.key(),tid,'synthetic-valid');key=self.key()
        a=self.api.revise('synthetic',key,tid,'synthetic-valid');self.assertEqual(a,self.api.revise('synthetic',key,tid,'synthetic-valid'))
        class Wrong(MockDelivery):
            def recover_verified(self,task,evidence,scope):
                a=super().recover_verified(task,evidence,scope);a['scope_hash']='wrong';return a
        self.api.verifier=Wrong()
        with self.assertRaises(Error):self.api.revise('synthetic',self.key(),tid,'synthetic-valid')

    def test_pending_order_reused_across_browser_retries(self):
        a=self.api.order('synthetic',self.key(),'listing_cny_39_v1','synthetic-listing','workbuddy_skill')
        self.api.report('synthetic',self.key(),a['id'])
        b=self.api.order('synthetic',self.key(),'listing_cny_39_v1','synthetic-listing','workbuddy_skill')
        self.assertEqual(a['id'],b['id']);self.assertEqual(b['status'],'reported')
        with self.db.connect() as c:self.assertEqual(c.execute('SELECT count(*) FROM listing_orders').fetchone()[0],1)


if __name__=='__main__':unittest.main()

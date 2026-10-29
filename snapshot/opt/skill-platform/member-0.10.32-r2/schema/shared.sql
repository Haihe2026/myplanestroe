CREATE TABLE api_jobs(key_id TEXT NOT NULL,job_id TEXT PRIMARY KEY,day TEXT NOT NULL);

CREATE TABLE assistant_trial_grants(user_id TEXT PRIMARY KEY, units INTEGER NOT NULL, created INTEGER NOT NULL);

CREATE TABLE claim_limits(ip_hash TEXT NOT NULL, day TEXT NOT NULL, count INTEGER NOT NULL,
                PRIMARY KEY(ip_hash, day));

CREATE TABLE customer_keys(id TEXT PRIMARY KEY,user_id TEXT NOT NULL,
                hash TEXT UNIQUE NOT NULL,prefix TEXT NOT NULL,created INTEGER NOT NULL,revoked INTEGER,
                last_used INTEGER);

CREATE TABLE email_approvals(
                      order_id TEXT PRIMARY KEY,reference TEXT UNIQUE NOT NULL,
                      notification_id TEXT UNIQUE NOT NULL,reply_id TEXT UNIQUE NOT NULL,
                      reply_sha256 TEXT NOT NULL,approver TEXT NOT NULL,authentication TEXT NOT NULL,
                      amount_fen INTEGER NOT NULL,units INTEGER NOT NULL,created INTEGER NOT NULL);

CREATE TABLE gemini_personal_trial_jobs(
                    job_id TEXT PRIMARY KEY,user_id TEXT NOT NULL);

CREATE TABLE gemini_personal_trials(
                    user_id TEXT PRIMARY KEY,allowance INTEGER NOT NULL CHECK(allowance=1),created INTEGER NOT NULL);

CREATE TABLE grant_jobs(job_id TEXT PRIMARY KEY,order_id TEXT NOT NULL);

CREATE TABLE invites(hash TEXT PRIMARY KEY, expires INTEGER NOT NULL, used INTEGER NOT NULL DEFAULT 0);

CREATE TABLE job_products(job_id TEXT PRIMARY KEY,product TEXT NOT NULL);

CREATE TABLE jobs(id TEXT PRIMARY KEY, user_id TEXT NOT NULL, idem TEXT NOT NULL,
                request_hash TEXT NOT NULL, status TEXT NOT NULL, image BLOB, created INTEGER,
                UNIQUE(user_id, idem));

CREATE TABLE ledger(id INTEGER PRIMARY KEY, user_id TEXT, job_id TEXT, amount INTEGER, kind TEXT, created INTEGER);

CREATE TABLE legacy_links(product TEXT NOT NULL,legacy_uid TEXT NOT NULL,
                  user_id TEXT NOT NULL,PRIMARY KEY(product,legacy_uid),UNIQUE(product,user_id));

CREATE TABLE member_gifts(user_id TEXT NOT NULL,gift_id TEXT NOT NULL,
                      campaign TEXT NOT NULL,granted INTEGER NOT NULL,PRIMARY KEY(user_id,gift_id));

CREATE TABLE member_grants(
                  order_id TEXT PRIMARY KEY,user_id TEXT NOT NULL,
                  remaining INTEGER NOT NULL CHECK(remaining>=0),expires INTEGER);

CREATE TABLE member_orders(id TEXT PRIMARY KEY,user_id TEXT NOT NULL,plan TEXT NOT NULL,
              amount_fen INTEGER NOT NULL,units INTEGER NOT NULL,status TEXT NOT NULL,created INTEGER NOT NULL,
              provider TEXT,transaction_id TEXT UNIQUE,paid_at INTEGER, product TEXT NOT NULL DEFAULT 'gemini-image-assistant');

CREATE TABLE ops_settlements(
                order_id TEXT PRIMARY KEY,user_id TEXT NOT NULL,transaction_id TEXT NOT NULL,
                amount_fen INTEGER NOT NULL,points INTEGER NOT NULL,actor TEXT NOT NULL,
                created INTEGER NOT NULL);

CREATE TABLE ops_test_order_marks(
                order_id TEXT PRIMARY KEY,previous_status TEXT NOT NULL,
                actor TEXT NOT NULL,reason TEXT NOT NULL,marked_at INTEGER NOT NULL);

CREATE TABLE order_sources(order_id TEXT PRIMARY KEY,product TEXT NOT NULL);

CREATE TABLE paid_jobs(job_id TEXT PRIMARY KEY);

CREATE TABLE paid_wallets(user_id TEXT PRIMARY KEY,remaining INTEGER NOT NULL DEFAULT 0 CHECK(remaining>=0));

CREATE TABLE product_accounts(product TEXT NOT NULL,user_id TEXT NOT NULL,
                  created INTEGER NOT NULL,PRIMARY KEY(product,user_id));

CREATE TABLE sessions(hash TEXT PRIMARY KEY, user_id TEXT NOT NULL, expires INTEGER NOT NULL);

CREATE TABLE settlement_receipts(
                transaction_id TEXT PRIMARY KEY,product TEXT NOT NULL,order_id TEXT NOT NULL,
                amount_fen INTEGER NOT NULL,actor TEXT NOT NULL,state TEXT NOT NULL,created INTEGER NOT NULL);

CREATE TABLE skill_credentials(
                    user_id TEXT PRIMARY KEY,id TEXT UNIQUE NOT NULL,nonce TEXT NOT NULL,
                    created INTEGER NOT NULL,revoked INTEGER,bound_at INTEGER);

CREATE TABLE temu_customer_feedback(
                  user_id TEXT NOT NULL,job_id TEXT NOT NULL,feedback_id TEXT NOT NULL,
                  category TEXT NOT NULL,body TEXT NOT NULL,created INTEGER NOT NULL,
                  PRIMARY KEY(user_id,feedback_id));

CREATE TABLE temu_enterprise_trials(
                  user_id TEXT PRIMARY KEY, allowance INTEGER NOT NULL CHECK(allowance=3), created INTEGER NOT NULL);

CREATE TABLE temu_trial_jobs(job_id TEXT PRIMARY KEY,user_id TEXT NOT NULL);

CREATE TABLE temu_trial_policy(
                    user_id TEXT PRIMARY KEY, trial_total INTEGER NOT NULL CHECK(trial_total=1),
                    created INTEGER NOT NULL);

CREATE TABLE trial_claims(hash TEXT PRIMARY KEY, user_id TEXT NOT NULL, created INTEGER NOT NULL);

CREATE TABLE users(id TEXT PRIMARY KEY, balance INTEGER NOT NULL CHECK(balance >= 0));

CREATE TABLE web_sessions(hash TEXT PRIMARY KEY,user_id TEXT NOT NULL,expires INTEGER NOT NULL);

CREATE TABLE web_tickets(hash TEXT PRIMARY KEY,user_id TEXT NOT NULL,expires INTEGER NOT NULL,used INTEGER NOT NULL DEFAULT 0);

-- Schema only. No customer records.
CREATE INDEX gemini_personal_trial_user ON gemini_personal_trial_jobs(user_id);

CREATE INDEX temu_trial_jobs_user ON temu_trial_jobs(user_id);

CREATE TRIGGER paid_skill_credential_insert
                AFTER INSERT ON member_orders WHEN NEW.status='paid'
                BEGIN
                    INSERT OR IGNORE INTO skill_credentials(user_id,id,nonce,created)
                    VALUES(NEW.user_id,lower(hex(randomblob(16))),lower(hex(randomblob(32))),
                           cast(strftime('%s','now') as integer));
                END;

CREATE TRIGGER paid_skill_credential_update
                AFTER UPDATE OF status ON member_orders
                WHEN NEW.status='paid' AND OLD.status!='paid'
                BEGIN
                    INSERT OR IGNORE INTO skill_credentials(user_id,id,nonce,created)
                    VALUES(NEW.user_id,lower(hex(randomblob(16))),lower(hex(randomblob(32))),
                           cast(strftime('%s','now') as integer));
                END;

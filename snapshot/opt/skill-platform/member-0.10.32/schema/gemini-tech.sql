-- Schema only; no rows.
CREATE TABLE tech_events(
                  id INTEGER PRIMARY KEY, order_id TEXT NOT NULL,
                  kind TEXT NOT NULL, created INTEGER NOT NULL);

CREATE TABLE tech_orders(
                  id TEXT PRIMARY KEY, owner TEXT NOT NULL, task TEXT NOT NULL,
                  digest TEXT NOT NULL, amount INTEGER NOT NULL,
                  status TEXT NOT NULL, code_url TEXT, payment_code TEXT,
                  expires INTEGER, lease INTEGER NOT NULL DEFAULT 0,
                  transaction_id TEXT UNIQUE, created INTEGER NOT NULL,
                  UNIQUE(owner, task));

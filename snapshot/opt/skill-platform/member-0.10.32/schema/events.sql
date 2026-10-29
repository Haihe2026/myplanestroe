CREATE TABLE events(id INTEGER PRIMARY KEY,created INTEGER NOT NULL,
          product TEXT NOT NULL,user_id TEXT,event TEXT NOT NULL,status INTEGER NOT NULL,
          channel TEXT NOT NULL,device TEXT NOT NULL,duration_ms INTEGER NOT NULL);

CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);

-- Schema only. No customer records.
CREATE INDEX events_time ON events(created);

CREATE INDEX events_user ON events(product,user_id,created);

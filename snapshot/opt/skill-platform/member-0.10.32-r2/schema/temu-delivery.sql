-- Schema only; no rows.
CREATE TABLE delivery_jobs(
                id TEXT PRIMARY KEY,uid TEXT NOT NULL,idem TEXT NOT NULL,request_hash TEXT NOT NULL,
                state TEXT NOT NULL,payload TEXT,credential_id TEXT,source TEXT NOT NULL,channel TEXT NOT NULL,
                created INTEGER NOT NULL,updated INTEGER NOT NULL,started INTEGER,finished INTEGER,
                job_id TEXT,error_code INTEGER,image BLOB,preview BLOB,UNIQUE(uid,idem));

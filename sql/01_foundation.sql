-- Run while connected to the BankGuard database. Safe to re-run.
CREATE TABLE IF NOT EXISTS customers (
    customer_id integer PRIMARY KEY,
    full_name text NOT NULL,
    email text NOT NULL UNIQUE,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS accounts (
    account_id integer PRIMARY KEY,
    customer_id integer NOT NULL REFERENCES customers(customer_id),
    account_type text NOT NULL CHECK (account_type IN ('checking','savings','business')),
    balance numeric(14,2) NOT NULL CHECK (balance >= 0),
    status text NOT NULL DEFAULT 'active',
    opened_at timestamptz NOT NULL
);
CREATE TABLE IF NOT EXISTS transactions (
    transaction_id bigint PRIMARY KEY,
    account_id integer NOT NULL REFERENCES accounts(account_id),
    amount numeric(14,2) NOT NULL,
    transaction_type text NOT NULL CHECK (transaction_type IN ('credit','debit','transfer')),
    merchant text NOT NULL,
    occurred_at timestamptz NOT NULL,
    status text NOT NULL DEFAULT 'completed'
);
CREATE TABLE IF NOT EXISTS auditlogs (
    audit_id bigint PRIMARY KEY,
    entity_type text NOT NULL,
    entity_id bigint NOT NULL,
    action text NOT NULL,
    details jsonb NOT NULL DEFAULT '{}'::jsonb,
    logged_at timestamptz NOT NULL
);
CREATE TABLE IF NOT EXISTS fraudevents (
    fraud_event_id bigint PRIMARY KEY,
    transaction_id bigint NOT NULL REFERENCES transactions(transaction_id),
    risk_score numeric(5,2) NOT NULL CHECK (risk_score BETWEEN 0 AND 100),
    event_type text NOT NULL,
    resolved boolean NOT NULL DEFAULT false,
    detected_at timestamptz NOT NULL
);

-- Exactly 500 deterministic sample rows in each main table.
INSERT INTO customers(customer_id,full_name,email,created_at)
SELECT n, 'Customer '||lpad(n::text,4,'0'), 'customer'||n||'@example.test', now()-(n||' days')::interval
FROM generate_series(1,500) n ON CONFLICT DO NOTHING;
INSERT INTO accounts(account_id,customer_id,account_type,balance,status,opened_at)
SELECT n,n, (ARRAY['checking','savings','business'])[(n%3)+1], (1000+n*17.35)::numeric(14,2), 'active', now()-(n||' days')::interval
FROM generate_series(1,500) n ON CONFLICT DO NOTHING;
INSERT INTO transactions(transaction_id,account_id,amount,transaction_type,merchant,occurred_at,status)
SELECT n,n, (10+(n%1000)*1.25)::numeric(14,2), (ARRAY['credit','debit','transfer'])[(n%3)+1], 'Merchant '||((n%25)+1), now()-(n||' minutes')::interval, 'completed'
FROM generate_series(1,500) n ON CONFLICT DO NOTHING;
INSERT INTO auditlogs(audit_id,entity_type,entity_id,action,details,logged_at)
SELECT n, 'transaction',n, (ARRAY['created','reviewed','updated'])[(n%3)+1], jsonb_build_object('source','seed','sequence',n), now()-(n||' minutes')::interval
FROM generate_series(1,500) n ON CONFLICT DO NOTHING;
INSERT INTO fraudevents(fraud_event_id,transaction_id,risk_score,event_type,resolved,detected_at)
SELECT n,n, ((n*37)%100)::numeric(5,2), (ARRAY['unusual_location','velocity','high_amount'])[(n%3)+1], n%4=0, now()-(n||' minutes')::interval
FROM generate_series(1,500) n ON CONFLICT DO NOTHING;

CREATE TABLE IF NOT EXISTS acidaccounts (
    account_id integer PRIMARY KEY,
    owner text NOT NULL,
    balance numeric(14,2) NOT NULL CHECK(balance >= 0),
    updated_at timestamptz NOT NULL DEFAULT now()
);
INSERT INTO acidaccounts VALUES (1,'Alice',10000),(2,'Bob',10000) ON CONFLICT DO NOTHING;
CREATE TABLE IF NOT EXISTS concurrency_test (
    id bigserial PRIMARY KEY,
    worker_id integer NOT NULL,
    operation_no integer NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS nf_order (
    order_id integer PRIMARY KEY,
    customer_id integer NOT NULL REFERENCES customers(customer_id),
    customer_name text NOT NULL,
    product_id integer NOT NULL,
    product_name text NOT NULL,
    quantity integer NOT NULL CHECK(quantity>0),
    unit_price numeric(12,2) NOT NULL CHECK(unit_price>=0)
);
INSERT INTO nf_order VALUES (1,1,'Customer 0001',101,'Secure Token',2,19.99) ON CONFLICT DO NOTHING;

ANALYZE customers;
ANALYZE accounts;
ANALYZE transactions;
ANALYZE auditlogs;
ANALYZE fraudevents;

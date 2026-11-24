-- BankGuard database was created separately in pgAdmin.
-- Reference schema. Do not rerun if these tables already exist.

CREATE TABLE customers (
 customer_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 first_name VARCHAR(50) NOT NULL, last_name VARCHAR(50) NOT NULL,
 email VARCHAR(100) UNIQUE NOT NULL, phone VARCHAR(15) UNIQUE NOT NULL,
 date_of_birth DATE, address TEXT, city VARCHAR(50), state VARCHAR(50),
 postal_code VARCHAR(10), created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE accounts (
 account_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 customer_id INT NOT NULL, account_number VARCHAR(20) UNIQUE NOT NULL,
 account_type VARCHAR(20) NOT NULL, balance NUMERIC(15,2) DEFAULT 0.00,
 currency VARCHAR(5) DEFAULT 'INR', account_status VARCHAR(20) DEFAULT 'Active',
 opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
 CONSTRAINT fk_customer FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

CREATE TABLE transactions (
 transaction_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 account_id INT NOT NULL, transaction_type VARCHAR(20) NOT NULL,
 amount NUMERIC(15,2) NOT NULL, transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
 transaction_status VARCHAR(20) DEFAULT 'Completed', payment_method VARCHAR(30),
 description TEXT, reference_number VARCHAR(50) UNIQUE,
 CONSTRAINT fk_account FOREIGN KEY (account_id) REFERENCES accounts(account_id),
 CONSTRAINT chk_amount CHECK (amount > 0)
);

CREATE TABLE auditlogs (
 audit_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY, account_id INT,
 action_type VARCHAR(50) NOT NULL, entity_type VARCHAR(50), entity_id VARCHAR(50),
 description TEXT, ip_address VARCHAR(45), created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
 CONSTRAINT fk_audit_account FOREIGN KEY (account_id) REFERENCES accounts(account_id)
);

CREATE TABLE fraudevents (
 fraud_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY, account_id INT,
 transaction_id INT, fraud_type VARCHAR(100) NOT NULL, risk_level VARCHAR(20) NOT NULL,
 fraud_status VARCHAR(30) DEFAULT 'Under Review', description TEXT,
 detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, resolved_at TIMESTAMP,
 CONSTRAINT fk_fraud_account FOREIGN KEY (account_id) REFERENCES accounts(account_id),
 CONSTRAINT fk_fraud_transaction FOREIGN KEY (transaction_id) REFERENCES transactions(transaction_id),
 CONSTRAINT chk_risk_level CHECK (risk_level IN ('Low','Medium','High','Critical'))
);

CREATE TABLE acidaccounts (
 acid_account_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 account_holder VARCHAR(100) NOT NULL, account_number VARCHAR(20) UNIQUE NOT NULL,
 balance NUMERIC(15,2) NOT NULL DEFAULT 0.00, account_status VARCHAR(20) DEFAULT 'Active',
 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
 CONSTRAINT chk_acid_balance CHECK (balance >= 0)
);

CREATE TABLE concurrency_test (
 test_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY, user_id INT NOT NULL,
 operation_type VARCHAR(30) NOT NULL, account_number VARCHAR(20), amount NUMERIC(15,2),
 operation_status VARCHAR(30) DEFAULT 'Pending', execution_time_ms NUMERIC(12,3),
 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE nf_order (
 order_id INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY, customer_name VARCHAR(100) NOT NULL,
 customer_email VARCHAR(100), product_name VARCHAR(100) NOT NULL, quantity INT NOT NULL,
 unit_price NUMERIC(12,2) NOT NULL, order_date DATE DEFAULT CURRENT_DATE,
 CONSTRAINT chk_nf_quantity CHECK (quantity > 0),
 CONSTRAINT chk_nf_price CHECK (unit_price >= 0)
);

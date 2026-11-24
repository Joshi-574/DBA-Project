-- Runs only when the Docker primary's named data volume is first initialized.
INSERT INTO customers(first_name,last_name,email,phone,date_of_birth,address,city,state,postal_code)
SELECT 'Customer',lpad(n::text,4,'0'),'customer'||n||'@bankguard.test','+91'||lpad(n::text,10,'0'),
       DATE '1980-01-01' + (n % 12000), 'BankGuard Street '||n, 'Mumbai', 'Maharashtra', lpad(n::text,6,'0')
FROM generate_series(1,500) AS n;

INSERT INTO accounts(customer_id,account_number,account_type,balance,currency,account_status)
SELECT n,'BG'||lpad(n::text,8,'0'),(ARRAY['Savings','Current','Business'])[(n%3)+1],
       (5000+n*125.50)::numeric(15,2),'INR','Active'
FROM generate_series(1,500) AS n;

INSERT INTO transactions(account_id,transaction_type,amount,transaction_date,transaction_status,payment_method,description,reference_number)
SELECT n,(ARRAY['Credit','Debit','Transfer'])[(n%3)+1],(100+n*22.75)::numeric(15,2),
       now()-(n||' hours')::interval,'Completed',(ARRAY['UPI','Card','NEFT'])[(n%3)+1],
       'BankGuard sample transaction '||n,'BG-TXN-'||lpad(n::text,8,'0')
FROM generate_series(1,500) AS n;

INSERT INTO auditlogs(account_id,action_type,entity_type,entity_id,description,ip_address)
SELECT n,(ARRAY['CREATE','UPDATE','LOGIN'])[(n%3)+1],'transaction',n::text,
       'Seeded BankGuard audit event '||n,'127.0.0.1'
FROM generate_series(1,500) AS n;

INSERT INTO fraudevents(account_id,transaction_id,fraud_type,risk_level,fraud_status,description)
SELECT n,n,(ARRAY['Unusual Location','High Velocity','High Amount'])[(n%3)+1],
       (ARRAY['Low','Medium','High','Critical'])[(n%4)+1],
       (ARRAY['Under Review','Resolved'])[(n%2)+1],'Seeded BankGuard fraud event '||n
FROM generate_series(1,500) AS n;

INSERT INTO acidaccounts(account_holder,account_number,balance)
VALUES ('Rahul','ACID1001',10000),('Priya','ACID1002',10000);
INSERT INTO nf_order(customer_name,customer_email,product_name,quantity,unit_price)
VALUES ('Customer 0001','customer1@bankguard.test','Secure Token',2,19.99);

ANALYZE;

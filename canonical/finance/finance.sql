
CREATE TABLE invoices (

id UUID PRIMARY KEY,

order_id UUID,

amount DECIMAL,

currency UUID,

status VARCHAR(50)

);


CREATE TABLE payments (

id UUID PRIMARY KEY,

invoice_id UUID,

amount DECIMAL,

payment_status VARCHAR(50)

);


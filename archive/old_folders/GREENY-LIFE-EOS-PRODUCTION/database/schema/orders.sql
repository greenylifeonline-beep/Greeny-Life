
CREATE TABLE customers (

id UUID PRIMARY KEY,

name VARCHAR(255),

country UUID,

email VARCHAR(255)

);


CREATE TABLE orders (

id UUID PRIMARY KEY,

customer_id UUID,

status VARCHAR(50),

created_at TIMESTAMP

);


CREATE TABLE order_items (

order_id UUID,

product_id UUID,

quantity DECIMAL

);


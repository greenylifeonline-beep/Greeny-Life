
CREATE TABLE products (

id UUID PRIMARY KEY,

sku VARCHAR(100) UNIQUE,

name VARCHAR(255),

category_id UUID,

origin_country UUID,

description TEXT,

certification TEXT,

status VARCHAR(50),

created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

);


CREATE TABLE product_batches (

id UUID PRIMARY KEY,

product_id UUID,

batch_number VARCHAR(100),

production_date DATE,

expiry_date DATE

);



CREATE TABLE product_master (

id UUID PRIMARY KEY,
sku VARCHAR(100),
name VARCHAR(255),
category VARCHAR(100),
origin_country VARCHAR(100),
status VARCHAR(50),
created_at TIMESTAMP

);


CREATE TABLE supplier_master (

id UUID PRIMARY KEY,
company_name VARCHAR(255),
country VARCHAR(100),
quality_score INT,
status VARCHAR(50)

);


CREATE TABLE inventory_master (

id UUID PRIMARY KEY,
product_id UUID,
warehouse VARCHAR(255),
batch_number VARCHAR(100),
quantity DECIMAL

);


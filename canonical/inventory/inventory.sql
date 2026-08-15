
CREATE TABLE warehouses (

id UUID PRIMARY KEY,

name VARCHAR(255),

location VARCHAR(255)

);


CREATE TABLE inventory (

id UUID PRIMARY KEY,

product_id UUID,

warehouse_id UUID,

batch_id UUID,

quantity DECIMAL,

updated_at TIMESTAMP

);


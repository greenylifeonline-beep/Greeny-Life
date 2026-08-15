
CREATE TABLE shipments (

id UUID PRIMARY KEY,

order_id UUID,

container_number VARCHAR(100),

carrier VARCHAR(100),

customs_status VARCHAR(50),

delivery_status VARCHAR(50)

);


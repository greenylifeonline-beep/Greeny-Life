
CREATE TABLE suppliers (

id UUID PRIMARY KEY,

company_name VARCHAR(255),

country UUID,

email VARCHAR(255),

phone VARCHAR(50),

quality_score INT,

compliance_status VARCHAR(50)

);


CREATE TABLE supplier_products (

supplier_id UUID,

product_id UUID

);


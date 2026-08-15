
CREATE TABLE quality_inspections (

id UUID PRIMARY KEY,

product_id UUID,

inspection_date DATE,

result VARCHAR(50),

certificate VARCHAR(255)

);


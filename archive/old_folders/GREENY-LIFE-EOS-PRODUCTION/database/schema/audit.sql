
CREATE TABLE audit_logs (

id UUID PRIMARY KEY,

entity VARCHAR(100),

action VARCHAR(100),

user_id UUID,

created_at TIMESTAMP

);


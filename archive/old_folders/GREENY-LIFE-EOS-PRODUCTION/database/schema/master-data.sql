
CREATE TABLE countries (

id UUID PRIMARY KEY,
name VARCHAR(100),
iso_code VARCHAR(10)

);


CREATE TABLE currencies (

id UUID PRIMARY KEY,
code VARCHAR(10),
name VARCHAR(100)

);


CREATE TABLE categories (

id UUID PRIMARY KEY,
name VARCHAR(100)

);


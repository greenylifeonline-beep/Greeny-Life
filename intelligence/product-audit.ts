import fs from "fs";
import path from "path";


const ROOT = process.cwd();

const FILES = [
"data/05_master_products.json",
"data/migrated_products.json",
"data/legacy/products.json",
"lib/data/products.ts"
];


function readFile(file:string){

    const full =
    path.join(ROOT,file);


    if(!fs.existsSync(full))
        return null;


    return fs.readFileSync(full,"utf8");

}



function analyze(){

const report:any = {
    generated:new Date().toISOString(),
    sources:[]
};


for(const file of FILES){

const content = readFile(file);


if(!content){

report.sources.push({
file,
status:"MISSING"
});

continue;

}


report.sources.push({

file,

status:"FOUND",

size:content.length,

type:
file.endsWith(".json")
?"JSON"
:"TYPESCRIPT"

});

}


return report;

}



function run(){

const report = analyze();


fs.writeFileSync(

path.join(
ROOT,
"reports/product-audit.json"
),

JSON.stringify(
report,
null,
2
)

);


console.log(
"Product Audit completed"
);


}


run();
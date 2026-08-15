import fs from "fs";
import path from "path";

import {
    runDuplicateEngineV2
}
from "./engines/duplicate-engine-v2";


import {
    getProjectMemory
}
from "./memory/project-memory";



const ROOT = process.cwd();



function checkFile(file:string){

    return fs.existsSync(
        path.join(ROOT,file)
    );

}



function runTest(){


console.log("\n🧠 GL-DOS Intelligence Test\n");



console.log("1) Checking Engine Files");



const files = [

"data/migrated_products.json",

"data/legacy/products.json",

"intelligence/engines/duplicate-engine-v2.ts",

"intelligence/memory/project-memory.ts"

];



for(const file of files){

console.log(

file,

checkFile(file)
?
"✅"
:
"❌"

);

}



console.log("\n2) Running Duplicate Intelligence");



const result =
runDuplicateEngineV2();



console.log(

"Duplicates detected:",

result.length

);



const migration =
result.filter(

item =>
item.type ===
"MIGRATION_MATCH"

);



console.log(

"Migration matches:",

migration.length

);



const highConfidence =
result.filter(

item =>
item.confidence >= 90

);



console.log(

"High confidence:",

highConfidence.length

);



console.log("\n3) Checking Decisions Memory");



const memory =
getProjectMemory();



console.log(

"Saved decisions:",

memory.decisions.length

);



console.log("\n4) Final Health Status");



if(

result.length > 0
&&
migration.length > 0
&&
highConfidence.length > 0

){

console.log(
"🟢 INTELLIGENCE ENGINE HEALTHY"
);

}

else{

console.log(
"🟡 ENGINE NEEDS DATA REVIEW"
);

}



}



runTest();
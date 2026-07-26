import fs from "fs";
import path from "path";

import {
    DUPLICATE_KEYS,
    MIGRATION_PATHS
}
from "../rules/duplicate-rules";


import {
    calculateConfidence
}
from "../core/confidence";



const ROOT = process.cwd();



const SOURCES = [

"data/05_master_products.json",

"data/migrated_products.json",

"data/legacy/products.json"

];



interface RecordItem {

file:string;

data:any;

}



export interface DuplicateFinding {


key:string;

value:string;

type:
"EXACT_DUPLICATE"
|
"MIGRATION_MATCH"
|
"DATA_CONFLICT"
|
"POSSIBLE_DUPLICATE";


confidence:number;


records:RecordItem[];


differences:string[];


recommendation:string;

}

function load(file:string){


const target =
path.join(ROOT,file);


if(!fs.existsSync(target))
return [];


const json =
JSON.parse(
fs.readFileSync(
target,
"utf8"
)
);


return Array.isArray(json)
?
json
:
json.products ?? [];

}




function compare(
a:any,
b:any
){

const diff:string[]=[];


const keys =
new Set([
...Object.keys(a),
...Object.keys(b)
]);


for(const key of keys){

if(
JSON.stringify(a[key])
!==
JSON.stringify(b[key])
)
diff.push(key);

}


return diff;

}


export function runDuplicateEngineV2(){

const registry:RecordItem[]=[];


for(const source of SOURCES){


for(const item of load(source)){


registry.push({

file:source,

data:item

});

}

}

const map =
new Map<string,RecordItem[]>();



for(const record of registry){


for(const key of DUPLICATE_KEYS){


let value =
record.data[key];


if(typeof value === "object"){

    value =
    JSON.stringify(value);

}


if(!value)
continue;



const index =
`${key}:${value}`;



if(!map.has(index))
map.set(index,[]);



map.get(index)!.push(record);


}

}



const findings:DuplicateFinding[]=[];



for(
const [identity,records]
of map
){


if(records.length<2)
continue;



const differences =
compare(
records[0].data,
records[1].data
);



const migration =
records.some(
r=>r.file.includes("legacy")
)
&&
records.some(
r=>r.file.includes("migrated")
);



let type:
DuplicateFinding["type"];



if(
differences.length===0
&&
migration
)
type="MIGRATION_MATCH";


else if(
differences.length===0
)
type="EXACT_DUPLICATE";


else
type="DATA_CONFLICT";




findings.push({

key:
identity.split(":")[0],


value:
identity.split(":")[1],


type,


confidence:
calculateConfidence(
differences.length===0,
migration
),


records,


differences,


recommendation:
type==="MIGRATION_MATCH"
?
"KEEP_MIGRATED_VERSION_AFTER_VALIDATION"
:
"MANUAL_REVIEW"

});


}



return findings;

}
export {
    runDuplicateEngineV2 as runDuplicateEngine
};
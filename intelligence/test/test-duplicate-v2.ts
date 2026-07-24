import {
    runDuplicateEngineV2
}
from "../engines/duplicate-engine-v2";


const result =
runDuplicateEngineV2();



const conflicts =
result.filter(
    item =>
    item.type === "DATA_CONFLICT"
);



console.log(
"\n=== DUPLICATE ENGINE V2 REPORT ===\n"
);


console.log(
"Total Findings:",
result.length
);


console.log(
"Conflicts:",
conflicts.length
);



for(const item of conflicts){

console.log(
JSON.stringify(
{
key:item.key,

value:item.value,

confidence:item.confidence,

differences:item.differences,

records:item.records.map(
r=>({
file:r.file,
data:r.data
})
),

recommendation:item.recommendation

},
null,
2
)
);

}
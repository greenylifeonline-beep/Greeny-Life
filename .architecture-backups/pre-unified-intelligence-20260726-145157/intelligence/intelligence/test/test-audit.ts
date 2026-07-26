import {runAuditEngine}
from "../engines/audit-engine";


const result =
runAuditEngine();


console.log(

JSON.stringify(
    result,
    null,
    2
)

);
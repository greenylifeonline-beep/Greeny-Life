import {runIntegrityEngine} from "../engines/data-integrity-engine";

console.log(
    JSON.stringify(
        runIntegrityEngine(),
        null,
        2
    )
);
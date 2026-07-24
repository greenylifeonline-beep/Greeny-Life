import fs from "fs";
import path from "path";

import {
    ENGINE_REGISTRY
}
from "../core/engine-registry";


const ROOT = process.cwd();


function checkEngineFiles(){

    return ENGINE_REGISTRY.map(engine=>{

        const file =
        path.join(
            ROOT,
            "intelligence",
            engine.location
        );


        return {

            name:engine.name,

            version:engine.version,

            status:engine.status,

            exists:
            fs.existsSync(file)

        };

    });

}



export function generateHealthReport(){

    const engines =
    checkEngineFiles();


    const report={

        generated:
        new Date().toISOString(),


        system:
        "GL-DOS",


        status:
        engines.every(
            e=>e.exists
        )
        ?
        "HEALTHY"
        :
        "WARNING",


        engines

    };


    fs.writeFileSync(

        path.join(
            ROOT,
            "reports",
            "system-health.json"
        ),

        JSON.stringify(
            report,
            null,
            2
        )

    );


    return report;

}
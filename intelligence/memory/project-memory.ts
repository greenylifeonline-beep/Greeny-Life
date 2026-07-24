import fs from "fs";
import path from "path";


const ROOT = process.cwd();


const MEMORY_FILE =
path.join(
    ROOT,
    "intelligence",
    "project-memory.json"
);



export interface MemoryDecision {

    id:string;

    date:string;

    engine:string;

    source?:string;

    finding:string;

    decision:string;

    severity:
    "INFO" |
    "WARNING" |
    "CRITICAL";

    status:
    "ACTIVE" |
    "RESOLVED" |
    "ARCHIVED";

}



export interface ProjectMemory {

    project:string;

    version:string;

    decisions:MemoryDecision[];

}




function loadMemory():ProjectMemory {


    if(!fs.existsSync(MEMORY_FILE)){


        return {

            project:"GREENY LIFE",

            version:"1.0",

            decisions:[]

        };

    }


    return JSON.parse(
        fs.readFileSync(
            MEMORY_FILE,
            "utf8"
        )
    ) as ProjectMemory;


}




export function saveDecision(
    decision: Omit<MemoryDecision,"id">
){


    const memory =
    loadMemory();



    const exists =
    memory.decisions.some(
        (item:MemoryDecision) =>

            item.engine === decision.engine &&

            item.finding === decision.finding &&

            item.decision === decision.decision

    );



    if(exists){

        console.log(
            "Memory decision already exists"
        );

        return;

    }



    const newDecision:MemoryDecision={


        id:
        `DEC-${String(memory.decisions.length + 1)
        .padStart(4,"0")}`,


        ...decision

    };



    memory.decisions.push(
        newDecision
    );



    fs.writeFileSync(

        MEMORY_FILE,

        JSON.stringify(
            memory,
            null,
            2
        )

    );


}




export function getProjectMemory(){

    return loadMemory();

}
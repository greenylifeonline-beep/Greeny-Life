export type EngineStatus =
    | "ACTIVE"
    | "DISABLED"
    | "DEPRECATED";


export interface EngineDefinition {

name:string;

version:string;

status:
"ACTIVE"
|
"DISABLED"
|
"DEPRECATED";

location:string;

}


export const ENGINE_REGISTRY:EngineDefinition[]=[


{
name:"Duplicate Engine",
version:"2.0",
status:"ACTIVE",
location:"engines/duplicate-engine-v2.ts"
},


{
name:"Cleanup Engine",
version:"1.0",
status:"ACTIVE",
location:"engines/cleanup-engine.ts"
},


{
name:"Audit Engine",
version:"1.0",
status:"ACTIVE",
location:"engines/audit-engine.ts"
},


{
name:"Schema Intelligence",
version:"1.0",
status:"ACTIVE",
location:"index.ts"
},


{
name:"Product Audit",
version:"1.0",
status:"ACTIVE",
location:"product-audit.ts"
},


{
name:"Project Memory",
version:"1.0",
status:"ACTIVE",
location:"memory/project-memory.ts"
}


];


export function getActiveEngines(){

    return ENGINE_REGISTRY.filter(
        engine =>
        engine.status==="ACTIVE"
    );

}



export function findEngine(
    name:string
){

    return ENGINE_REGISTRY.find(
        engine =>
        engine.name===name
    );

}
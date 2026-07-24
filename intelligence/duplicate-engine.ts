import fs from "fs";
import path from "path";


// ===============================
// Types
// ===============================

export interface ScanRecord {

    file:string;

    data:any;

}

type ConfidenceLevel =
    | "HIGH"
    | "MEDIUM"
    | "LOW";


interface ConfidenceResult {

    score:number;

    level:ConfidenceLevel;

    reasons:string[];

}


export type DuplicateCategory =
    | "EXACT_DUPLICATE"
    | "MIGRATION_MATCH"
    | "DATA_CONFLICT"
    | "POSSIBLE_DUPLICATE";



export type DuplicateSeverity =
    | "INFO"
    | "WARNING"
    | "CRITICAL";



export type DuplicateAction =
    | "KEEP_BOTH_UNTIL_MIGRATION_COMPLETE"
    | "MERGE_RECOMMENDED"
    | "MANUAL_REVIEW";


interface DuplicateResult {


    key:string;

    value:string;


    category:DuplicateCategory;


    files:string[];


    records:ScanRecord[];


    differences:string[];


    severity:
    | "INFO"
    | "WARNING"
    | "CRITICAL";


    action:DuplicateAction;


    confidence:ConfidenceResult;


}

function calculateConfidence(
    a:any,
    b:any
):ConfidenceResult{


    let score = 0;

    const reasons:string[]=[];



    if(a.id && b.id && a.id === b.id){

        score += 40;

        reasons.push(
            "same id"
        );

    }



    if(
        a.name &&
        b.name &&
        a.name === b.name
    ){

        score += 25;

        reasons.push(
            "same name"
        );

    }



    if(
        a.category &&
        b.category &&
        a.category === b.category
    ){

        score += 20;

        reasons.push(
            "same category"
        );

    }



    if(
        a.image &&
        b.image &&
        a.image === b.image
    ){

        score += 15;

        reasons.push(
            "same image"
        );

    }



    let level:ConfidenceLevel;


    if(score >= 90){

        level="HIGH";

    }
    else if(score >=60){

        level="MEDIUM";

    }
    else{

        level="LOW";

    }



    return {

        score,

        level,

        reasons

    };


}


// ===============================
// Configuration
// ===============================


const ROOT =
process.cwd();



const DEFAULT_SOURCES = [


    "data/05_master_products.json",


    "data/migrated_products.json",


    "data/legacy/products.json"


];



const DEFAULT_KEYS = [


    "id",


    "product_code",


    "ref_id",


    "title"


];




// ===============================
// JSON Loader
// ===============================


function loadJsonFile(
    file:string
):any[]{


    const fullPath =
    path.join(
        ROOT,
        file
    );



    if(!fs.existsSync(fullPath)){

        return [];

    }



    const content =
    fs.readFileSync(
        fullPath,
        "utf8"
    );



    const json =
    JSON.parse(content);



    if(Array.isArray(json)){

        return json;

    }



    if(json.products){

        return json.products;

    }



    return [];

}




// ===============================
// Content Comparison
// ===============================


function compareContent(
    a:any,
    b:any
):string[]{


    const differences:string[]=[];



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

        ){

            differences.push(key);

        }


    }



    return differences;

}




// ===============================
// Migration Detection
// ===============================


function isMigrationPair(
    files:string[]
):boolean{


    return (

        files.some(
            f =>
            f.includes("legacy")
        )

        &&

        files.some(
            f =>
            f.includes("migrated")
        )

    );

}



// ===============================
// Classification Engine
// ===============================


function classifyDuplicate(
    records:ScanRecord[],
    differences:string[]
):DuplicateCategory{


    const migration =
    isMigrationPair(
        records.map(
            r=>r.file
        )
    );



    if(
        migration
        &&
        differences.length===0
    ){

        return "MIGRATION_MATCH";

    }



    if(
        differences.length===0
    ){

        return "EXACT_DUPLICATE";

    }



    return "DATA_CONFLICT";


}





function resolveSeverity(
    category:DuplicateCategory
):DuplicateSeverity{


    switch(category){


        case "MIGRATION_MATCH":

            return "INFO";


        case "EXACT_DUPLICATE":

            return "WARNING";


        case "DATA_CONFLICT":

            return "CRITICAL";


        default:

            return "WARNING";

    }


}
function determineAction(
 category:DuplicateCategory
):DuplicateAction{


    switch(category){


        case "MIGRATION_MATCH":

            return "KEEP_BOTH_UNTIL_MIGRATION_COMPLETE";


        case "EXACT_DUPLICATE":

            return "MERGE_RECOMMENDED";


        case "DATA_CONFLICT":

            return "MANUAL_REVIEW";


        case "POSSIBLE_DUPLICATE":

            return "MANUAL_REVIEW";


        default:

            return "MANUAL_REVIEW";

    }

}




// ===============================
// Main Engine
// ===============================


export function runDuplicateEngine(

    sources:string[] = DEFAULT_SOURCES,

    keys:string[] = DEFAULT_KEYS

):DuplicateResult[]{



    const registry:ScanRecord[]=[];



    for(const source of sources){


        const items =
        loadJsonFile(source);



        for(const item of items){


            registry.push({

                file:source,

                data:item

            });


        }


    }




    const index =
    new Map<
        string,
        ScanRecord[]
    >();




    for(const record of registry){


        for(const key of keys){



            const value =
            record.data[key];



            if(!value){

                continue;

            }



            const identifier =
            `${key}:${value}`;



            if(!index.has(identifier)){


                index.set(
                    identifier,
                    []
                );


            }



            index
            .get(identifier)!
            .push(record);



        }


    }




    const results:DuplicateResult[]=[];




    for(
        const [identifier,records]
        of index
    ){



        const uniqueFiles =

        [
            ...new Set(

                records.map(
                    r=>r.file
                )

            )

        ];




        if(uniqueFiles.length < 2){

            continue;

        }



        const differences =
        compareContent(

            records[0].data,

            records[1].data

        );



        const category =
        classifyDuplicate(
            records,
            differences
        );




        results.push({
            key: identifier.split(":")[0],



            value: identifier.split(":")[1],



            category,



            files: uniqueFiles,



            records,



            differences,



            severity: resolveSeverity(
                category
            ),



            action: resolveAction(
                category
            ),
            confidence: calculateConfidence(
                records[0].data,
                records[1].data
            )
        });



    }




    return results;

}

function resolveAction(
    category: DuplicateCategory,
    differences: string[] = []
): DuplicateAction {


    switch(category){


        case "MIGRATION_MATCH":

            return "KEEP_BOTH_UNTIL_MIGRATION_COMPLETE";


        case "EXACT_DUPLICATE":

            return "MERGE_RECOMMENDED";


        case "DATA_CONFLICT":

            return "MANUAL_REVIEW";


        case "POSSIBLE_DUPLICATE":

            if(differences.length === 0){

                return "MERGE_RECOMMENDED";

            }

            return "MANUAL_REVIEW";


        default:

            return "MANUAL_REVIEW";

    }

}
import fs from "fs";
import path from "path";


const ROOT = process.cwd();


interface IntegrityFinding {

    type:
    | "MISSING_FILE"
    | "EMPTY_FILE"
    | "INVALID_JSON"
    | "MISSING_MIGRATION"
    | "MISSING_LEGACY"
    | "DATA_CONFLICT"
    | "DUPLICATE_ID";

    severity:
    | "ERROR"
    | "WARNING";

    file?: string;

    product?: string;

    field?: string;

    message:string;

}



const FILES = {

    master:
    "data/05_master_products.json",

    migrated:
    "data/migrated_products.json",

    legacy:
    "data/legacy/products.json"

};



function readJSON(file:string){

    const target =
        path.join(ROOT,file);


    if(!fs.existsSync(target))
        return null;


    try{

        return JSON.parse(
            fs.readFileSync(
                target,
                "utf8"
            )
        );

    }

    catch{

        return null;

    }

}



function normalize(data:any){

    if(Array.isArray(data))
        return data;


    return data?.products ?? [];

}



function compareProducts(

    master:any[],

    target:any[],

    type:"MIGRATION"|"LEGACY",

    findings:IntegrityFinding[]

){


   function getIdentityKeys(product:any){

    const nameKey =
        typeof product.name === "string"
        ?
        product.name
            .toLowerCase()
            .trim()
            .replace(/\s+/g,"-")
        :
        null;


    return [

        product.id,

        product.ref_id,

        product.product_code,

        product.slug,

        product.key,

        nameKey

    ]
    .filter(
        key =>
        typeof key === "string" &&
        key.length > 0
    );

}

   function getIdentity(product:any){

    if(product.slug)
        return product.slug;


    if(product.id)
        return product.id.toLowerCase();


    if(product.name){

        const name =
        typeof product.name === "object"
        ?
        product.name.en
        :
        product.name;


        return name
        ?.toLowerCase()
        .replace(/\s+/g,"-")
        .replace("raw-","");

    }


    return null;

}

    const map = new Map();


for(const item of target){

    for(const key of getIdentityKeys(item)){

        map.set(
            key,
            item
        );

    }

}
    for(const product of master){


       const identities =
getIdentityKeys(product);


const found =
identities
.map(key=>map.get(key))
.find(Boolean);



        if(!found){


            findings.push({

                type:
                type==="MIGRATION"
                ?
                "MISSING_MIGRATION"
                :
                "MISSING_LEGACY",


                severity:
                "ERROR",

product:
getIdentity(product),


                message:
                `${product.id} missing from ${type.toLowerCase()} source`

            });


            continue;

        }



        const fields=[

            "name",
            "category",
            "image",
            "status"

        ];



        for(const field of fields){


          if(
    normalizeValue(product[field]) !==
    normalizeValue(found[field])
)
        {


                findings.push({

                    type:
                    "DATA_CONFLICT",


                    severity:"WARNING",


                    product:
                    product.id,


                    field,


                    message:
                    `${field} mismatch between sources`

                });

            }

        }

    }

}


function normalizeValue(value:any){

    if(value === undefined || value === null)
        return null;


    if(typeof value === "object"){

        if(value.en)
            return value.en.toLowerCase().trim();

        if(value.name)
            return String(value.name)
            .toLowerCase()
            .trim();

        return JSON.stringify(value)
            .toLowerCase();

    }


    return String(value)
        .toLowerCase()
        .trim();

}


export function runIntegrityEngine(){


    const findings:IntegrityFinding[]=[];


    const master =
        normalize(
            readJSON(
                FILES.master
            )
        );


    const migrated =
        normalize(
            readJSON(
                FILES.migrated
            )
        );


    const legacy =
        normalize(
            readJSON(
                FILES.legacy
            )
        );



    compareProducts(

        master,

        migrated,

        "MIGRATION",

        findings

    );



    compareProducts(

        master,

        legacy,

        "LEGACY",

        findings

    );



    return {


        system:
        "GL-DOS",


        engine:
        "Data Integrity Engine",


        version:
        "2.0",


        generated:
        new Date().toISOString(),


        summary:{


            master_products:
            master.length,


            migrated_products:
            migrated.length,


            legacy_products:
            legacy.length,


            errors:
            findings.filter(
                x=>x.severity==="WARNING"
            ).length,


            warnings:
            findings.filter(
                x=>x.severity==="WARNING"
            ).length,


            health:
            findings.length===0
            ?
            "HEALTHY"
            :
            "REVIEW_REQUIRED"


        },


        findings

    };

}
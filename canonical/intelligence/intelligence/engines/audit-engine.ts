import fs from "fs";
import path from "path";
import {normalizeProduct, ProductSource} from "../schemas/product-schema-map";

const ROOT = process.cwd();



const SOURCES = [

    {
        name:"CANONICAL_MASTER",
        file:"canonical/data/master_products.json"
    }

];



interface AuditFinding {

    source:string;

    product?:string;

    type:
    | "MISSING_FIELD"
    | "INVALID_STATUS"
    | "INVALID_STRUCTURE"
    | "DUPLICATE_ID"
    | "MISSING_REFERENCE";

    severity:
    | "ERROR"
    | "WARNING";

    field?:string;

    message:string;

}



function load(file:string){


    const target =
    path.join(
        ROOT,
        file
    );


    if(!fs.existsSync(target))
        return [];


    const raw = fs.readFileSync(target, "utf8").replace(/^\uFEFF/, "").trim();
    if (!raw) return [];
    const json = JSON.parse(raw);


    return Array.isArray(json)
    ?
    json
    :
    json.products ?? [];

}




function validateProduct(

    product:any,

    source:string

):AuditFinding[]{


    const findings:AuditFinding[]=[];


    const sourceType:ProductSource =

    source.includes("master_products")
        ?
        "master"

        : "master";



    const normalized =

        normalizeProduct(
            product,
            sourceType
        );




    const required = [

    "id",
    "name",
    "category",
] as const;


for(const field of required){


    if(!normalized[field]){


        findings.push({

            source,

            product:
            normalized.id,


            type:
            "MISSING_FIELD",


            severity:
            "ERROR",


            field,


            message:
            `Missing required field: ${field}`

        });

    }

}



    if(typeof normalized.active !== "boolean"){

    findings.push({

        source,

        product:
        normalized.id,

        type:
        "INVALID_STATUS",

        severity:
        "WARNING",

        field:
        "active",

        message:
        "Active status format is invalid"

    });

}

    return findings;

}




function checkDuplicates(

    products:any[],

    source:string

):AuditFinding[]{


    const findings:AuditFinding[]=[];


    const ids =
    new Map();



    for(const product of products){


        if(!product.id)
            continue;



        if(ids.has(product.id)){


            findings.push({

                source,


                product:
                product.id,


                type:
                "DUPLICATE_ID",


                severity:
                "ERROR",


                field:"id",


                message:
                `Duplicate product id detected: ${product.id}`

            });


        }


        ids.set(
            product.id,
            true
        );

    }



    return findings;

}





export function runAuditEngine(){


    const findings:AuditFinding[]=[];


    let totalProducts=0;



    for(const source of SOURCES){


        const products =
        load(
            source.file
        );


        totalProducts +=
        products.length;



        for(const product of products){


            findings.push(

                ...validateProduct(

                    product,

                    source.file

                )

            );


        }



        findings.push(

            ...checkDuplicates(

                products,

                source.file

            )

        );


    }



    return {


        system:
        "GL-DOS",


        engine:
        "Audit Engine",


        version:
        "1.0",


        generated:
        new Date().toISOString(),


        summary:{


            sources_checked:
            SOURCES.length,


            products_checked:
            totalProducts,


            errors:
            findings.filter(
                x=>x.severity==="ERROR"
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

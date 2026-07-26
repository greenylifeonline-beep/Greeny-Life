import fs from "fs";
import path from "path";


const ROOT = process.cwd();



export interface CleanupFinding {

    type:
    | "EMPTY_FILE"
    | "POSSIBLE_DUPLICATE_FILE"
    | "UNREGISTERED_ENGINE";

    file:string;

    related?:string[];

    severity:
    | "INFO"
    | "WARNING"
    | "CRITICAL";

    recommendation:string;

}



const IGNORE_DIRS = [

    "node_modules",
    ".next",
    ".git"

];



const ENGINE_DIR =
path.join(
    ROOT,
    "intelligence"
);



function walk(
    dir:string
):string[]{


    let files:string[]=[];


    for(const item of fs.readdirSync(dir)){


        if(
            IGNORE_DIRS.includes(item)
        )
        continue;


        const full =
        path.join(
            dir,
            item
        );


        const stat =
        fs.statSync(full);



        if(stat.isDirectory()){


            files.push(
                ...walk(full)
            );


        }
        else {


            files.push(full);


        }

    }


    return files;

}





function detectEmptyFiles(
files:string[]
){

    const result:CleanupFinding[]=[];


    for(const file of files){


        const size =
        fs.statSync(file).size;



        if(size===0){


            result.push({

                type:"EMPTY_FILE",

                file:
                path.relative(
                    ROOT,
                    file
                ),

                severity:"WARNING",

                recommendation:
                "REVIEW_EMPTY_FILE"

            });


        }


    }


    return result;

}





function detectDuplicateNames(
files:string[]
){

    const map =
    new Map<string,string[]>();


    for(const file of files){


        const name =
        path.basename(file);



        if(!map.has(name))
            map.set(name,[]);



        map.get(name)!
        .push(file);

    }



    const findings:CleanupFinding[]=[];



    for(
        const [name,items]
        of map
    ){


        if(items.length>1){


            findings.push({

                type:
                "POSSIBLE_DUPLICATE_FILE",

                file:name,

                related:
                items.map(
                    x=>path.relative(
                        ROOT,
                        x
                    )
                ),

                severity:"INFO",

                recommendation:
                "COMPARE_AND_MERGE"

            });


        }

    }



    return findings;

}




export function runCleanupEngine(){


    const files =
    walk(
        ENGINE_DIR
    );



    const findings = [

        ...detectEmptyFiles(files),

        ...detectDuplicateNames(files)

    ];



    const report = {


        generated:
        new Date()
        .toISOString(),


        scannedFiles:
        files.length,


        findings

    };



    const reportDir =
    path.join(
        ROOT,
        "reports"
    );



    if(!fs.existsSync(reportDir)){

        fs.mkdirSync(
            reportDir
        );

    }



    fs.writeFileSync(

        path.join(
            reportDir,
            "cleanup-report.json"
        ),

        JSON.stringify(
            report,
            null,
            2
        )

    );



    return report;

}
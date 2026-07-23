import {scanJsonFolder} from "../scanners/json-scanner";


console.log(
 scanJsonFolder("./data")
);
import fs from "fs";
import path from "path";


const ROOT = process.cwd();

const DATA_DIR = path.join(ROOT,"data");
const REPORT_DIR = path.join(ROOT,"reports");


function scanJsonFiles(){

    const files = fs.readdirSync(DATA_DIR,{
        recursive:true
    })
    .filter((f:any)=>String(f).endsWith(".json"));


    const result:any[]=[];


    for(const file of files){

        const full =
        path.join(DATA_DIR,String(file));


        try{

            const content =
            fs.readFileSync(full,"utf8");


            const json =
            JSON.parse(content);


            result.push({
                file,
                status:"VALID",
                keys:Object.keys(json)
            });


        }catch(error:any){

            result.push({
                file,
                status:"INVALID",
                error:error.message
            });

        }

    }


    return result;

}



function ensureReports(){

    if(!fs.existsSync(REPORT_DIR))
        fs.mkdirSync(REPORT_DIR);

}



function run(){

    ensureReports();


    const report={
        generated:new Date().toISOString(),
        json:scanJsonFiles()
    };


    fs.writeFileSync(
        path.join(
            REPORT_DIR,
            "intelligence-schema-report.json"
        ),
        JSON.stringify(
            report,
            null,
            2
        )
    );


    console.log(
        "Schema Intelligence completed"
    );

}


run();

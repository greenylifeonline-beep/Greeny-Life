import fs from "fs";
import path from "path";


const ROOT = process.cwd();

const DATA_DIR = path.join(ROOT,"data");
const REPORT_DIR = path.join(ROOT,"reports");



function collectJsonFiles(dir:string):string[]{

    let result:string[]=[];


    for(const item of fs.readdirSync(dir)){

        const full =
        path.join(dir,item);


        const stat =
        fs.statSync(full);


        if(stat.isDirectory()){

            result=[
                ...result,
                ...collectJsonFiles(full)
            ];

        }
        else if(item.endsWith(".json")){

            result.push(full);

        }

    }


    return result;

}




function scan(){

    const files =
    collectJsonFiles(DATA_DIR);


    return files.map(file=>{

        try{

            const content =
            fs.readFileSync(
                file,
                "utf8"
            );


            const json =
            JSON.parse(content);


            return {

                file:
                path.relative(
                    ROOT,
                    file
                ),

                status:"VALID",

                type:
                Array.isArray(json)
                ?"ARRAY"
                :"OBJECT",

                keys:
                Object.keys(json)

            };


        }
        catch(error:any){

            return {

                file:
                path.relative(
                    ROOT,
                    file
                ),

                status:"INVALID",

                error:error.message

            };

        }

    });

}




function run(){

    if(!fs.existsSync(REPORT_DIR))
        fs.mkdirSync(REPORT_DIR);



    const report={

        generated:
        new Date().toISOString(),

        files:
        scan()

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
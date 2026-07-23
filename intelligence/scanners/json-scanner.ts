import fs from "fs";
import path from "path";


export interface ScanResult {
  file:string;
  status:"OK"|"BAD";
  error?:string;
}


export function scanJsonFolder(folder:string):ScanResult[]{

 const results:ScanResult[]=[];

 const files=fs.readdirSync(folder);


 for(const file of files){

   if(!file.endsWith(".json"))
      continue;


   const full=path.join(folder,file);


   try{

     const content=
       fs.readFileSync(full,"utf8");


     JSON.parse(content);


     results.push({
       file:full,
       status:"OK"
     });


   }catch(e:any){

     results.push({
       file:full,
       status:"BAD",
       error:e.message
     });

   }

 }


 return results;

}
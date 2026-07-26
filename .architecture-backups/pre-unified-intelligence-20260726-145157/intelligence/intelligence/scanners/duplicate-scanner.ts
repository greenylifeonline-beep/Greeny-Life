import fs from "fs";
import crypto from "crypto";


function hash(file:string){

 const data=
 fs.readFileSync(file);


 return crypto
 .createHash("sha256")
 .update(data)
 .digest("hex");

}



export function compareFiles(a:string,b:string){

 return hash(a)===hash(b);

}
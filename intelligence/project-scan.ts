import fs from "fs";
import path from "path";


interface ScanFile {
    path:string;
    size:number;
    ext:string;
}


const ROOT = process.cwd();

const TARGETS=[
"app",
"components",
"data",
"lib",
"scripts",
"intelligence"
];

const result:{
 generated:string;
 files:ScanFile[];
 duplicates:Record<string,string[]>;
 warnings:ScanFile[];
}={
 generated:new Date().toISOString(),
 files:[],
 duplicates:{},
 warnings:[]
};



function walk(dir:string){

 if(!fs.existsSync(dir))
 return;


 for(const item of fs.readdirSync(dir)){

  const full=
  path.join(dir,item);

  const stat=
  fs.statSync(full);


  if(stat.isDirectory()){

    walk(full);

  }
  else{

    result.files.push({
      path:full.replace(ROOT,""),
      size:stat.size,
      ext:path.extname(full)
    });

  }

 }

}



for(const folder of TARGETS){

 walk(
 path.join(ROOT,folder)
 );

}



const names:any={};


for(const file of result.files){

 const name=
 path.basename(file.path);


 if(!names[name])
 names[name]=[];

 names[name].push(file.path);

}


for(const name in names){

 if(names[name].length>1){

 result.duplicates[name]=names[name];

 }

}


result.warnings =
result.files.filter(
(f:ScanFile) =>
f.path.includes("backup") ||
f.path.includes("legacy")
);


fs.writeFileSync(
"reports/project-intelligence-scan.json",
JSON.stringify(result,null,2)
);


console.log(
"Project intelligence scan completed"
);
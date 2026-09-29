const fs = require("fs");
const path = require("path");

const ROOT = process.cwd();

const IGNORE = new Set([
  "node_modules",
  ".git",
  ".next",
  "backup",
  "reports"
]);

const report = {
  generated_at: new Date().toISOString(),

  statistics: {
    folders: 0,
    files: 0
  },

  html: [],
  css: [],
  js: [],
  ts: [],
  json: [],
  images: [],
  fonts: [],
  markdown: [],
  emptyFolders: [],
  emptyFiles: [],

  reusable: [],

  tree: {}
};

function scan(dir, node) {

  report.statistics.folders++;

  const items = fs.readdirSync(dir,{withFileTypes:true});

  node.files=[];

  node.folders={};

  if(items.length===0){

      report.emptyFolders.push(
          path.relative(ROOT,dir)
      );

  }

  for(const item of items){

      if(IGNORE.has(item.name))
          continue;

      const full=path.join(dir,item.name);

      if(item.isDirectory()){

          node.folders[item.name]={};

          scan(full,node.folders[item.name]);

          continue;

      }

      report.statistics.files++;

      node.files.push(item.name);

      const ext=path.extname(item.name).toLowerCase();

      const relative=path.relative(ROOT,full);

      const size=fs.statSync(full).size;

      if(size===0){

          report.emptyFiles.push(relative);

      }

      const entry={

          path:relative,

          size:size

      };

      switch(ext){

          case ".html":
              report.html.push(entry);
              break;

          case ".css":
              report.css.push(entry);
              break;

          case ".js":
              report.js.push(entry);
              break;

          case ".ts":

          case ".tsx":

              report.ts.push(entry);

              break;

          case ".json":

              report.json.push(entry);

              break;

          case ".svg":

          case ".png":

          case ".jpg":

          case ".jpeg":

          case ".webp":

              report.images.push(entry);

              break;

          case ".ttf":

          case ".woff":

          case ".woff2":

              report.fonts.push(entry);

              break;

          case ".md":

              report.markdown.push(entry);

              break;

      }

      if(

          relative.startsWith("app/js") ||

          relative.startsWith("app/views") ||

          relative.startsWith("app/assets")

      ){

          report.reusable.push(relative);

      }

  }

}

scan(ROOT,report.tree);

if(!fs.existsSync("reports")){

    fs.mkdirSync("reports");

}

fs.writeFileSync(

    "reports/legacy-analysis.json",

    JSON.stringify(report,null,2)

);

console.log("");

console.log("================================");

console.log("GREENY LIFE Project Analyzer");

console.log("================================");

console.log("");

console.log("Folders :",report.statistics.folders);

console.log("Files   :",report.statistics.files);

console.log("");

console.log("HTML :",report.html.length);

console.log("CSS  :",report.css.length);

console.log("JS   :",report.js.length);

console.log("TS   :",report.ts.length);

console.log("JSON :",report.json.length);

console.log("Images :",report.images.length);

console.log("");

console.log("Report:");

console.log("reports/legacy-analysis.json");

console.log("");

console.log("Done.");

console.log("");
import { execSync } from "child_process";


function run(
    command:string
){

    console.log(
        "\n▶ RUN:",
        command
    );


    execSync(
        command,
        {
            stdio:"inherit"
        }
    );

}



console.log(`
================================
      GL-DOS INTELLIGENCE
      SYSTEM DIAGNOSIS
================================
`);


run(
    "npm run type-check"
);


run(
    "npm run intelligence"
);


run(
    "npm run audit"
);


run(
    "npm run test:intelligence"
);


run(
    "npm run test:health"
);


console.log(`
================================
GL-DOS COMPLETE
================================
`);
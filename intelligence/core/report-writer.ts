import fs from "fs";
import path from "path";


const ROOT =
process.cwd();


const REPORT_DIR =
path.join(
    ROOT,
    "reports"
);



function ensureReports(){

    if(
        !fs.existsSync(REPORT_DIR)
    ){

        fs.mkdirSync(
            REPORT_DIR,
            {
                recursive:true
            }
        );

    }

}



function saveReport(
    name:string,
    data:any
){

    ensureReports();


    const file =
    path.join(
        REPORT_DIR,
        name
    );


    fs.writeFileSync(

        file,

        JSON.stringify(
            data,
            null,
            2
        ),

        "utf8"

    );


    return file;

}




function summarize(
findings:any[]
){

    return {

        total_findings:
        findings.length,


        migration_matches:

        findings.filter(
            x =>
            x.type ===
            "MIGRATION_MATCH"
        ).length,


        exact_duplicates:

        findings.filter(
            x =>
            x.type ===
            "EXACT_DUPLICATE"
        ).length,


        data_conflicts:

        findings.filter(
            x =>
            x.type ===
            "DATA_CONFLICT"
        ).length,


        possible_duplicates:

        findings.filter(
            x =>
            x.type ===
            "POSSIBLE_DUPLICATE"
        ).length

    };

}




export function generateDuplicateReport(
findings:any[]
){


    return saveReport(

        "duplicate-report.json",


        {

            system:
            "GL-DOS",


            engine:
            "Duplicate Engine",


            version:
            "2.0",


            generated:
            new Date().toISOString(),


            summary:
            summarize(
                findings
            ),


            policy:{

                identity_fields:[

                    "id",

                    "ref_id",

                    "product_code"

                ],


                comparison_mode:
                "semantic"

            },


            findings:

            findings.map(

                item => ({

                    identity:{

                        field:
                        item.key,


                        value:
                        item.value

                    },


                    type:
                    item.type,


                    confidence:
                    item.confidence,


                    records:

                    item.records.map(
                        (r:any)=>({

                            file:
                            r.file,


                            id:
                            r.data?.id,

                            product_code:
                            r.data?.product_code

                        })
                    ),


                    differences:
                    item.differences,


                    recommendation:
                    item.type ===
                    "MIGRATION_MATCH"

                    ?

                    "SAFE_MIGRATION_CLEANUP"

                    :

                    "MANUAL_REVIEW"

                })

            )

        }

    );

}





export function generateCleanupPlan(
findings:any[]
){


    return saveReport(

        "cleanup-plan.json",


        {

            system:
            "GL-DOS",


            engine:
            "Cleanup Engine",


            version:
            "1.0",


            generated:
            new Date().toISOString(),


            status:
            "PENDING_APPROVAL",


            backup_required:
            true,


            rollback_available:
            true,


            actions:

            findings

            .filter(
                x =>
                x.type ===
                "MIGRATION_MATCH"
            )


            .map(

                (item:any,index:number)=>(

                {

                    id:
                    `CLEAN-${String(index+1).padStart(4,"0")}`,


                    identity:{

                        field:
                        item.key,


                        value:
                        item.value

                    },


                    source:
                    item.records[0].file,


                    target:
                    item.records[1].file,


                    action:
                    "REMOVE_LEGACY_AFTER_BACKUP",


                    confidence:
                    item.confidence

                }

                )

            )

        }

    );

}





export function generateMigrationDecision(
findings:any[]
){


    return saveReport(

        "migration-decision.json",


        {

            system:
            "GL-DOS",


            engine:
            "Migration Decision Engine",


            version:
            "1.0",


            generated:
            new Date().toISOString(),


            status:
            "APPROVAL_REQUIRED",


            decisions:

            findings

            .filter(
                x =>
                x.type ===
                "MIGRATION_MATCH"
            )


            .map(

                (item:any,index:number)=>(

                {

                    id:
                    `DEC-${String(index+1).padStart(4,"0")}`,


                    identity:{

                        field:
                        item.key,


                        value:
                        item.value

                    },


                    decision:
                    "KEEP_MIGRATED",


                    confidence:
                    item.confidence,


                    next_step:
                    "WAIT_FOR_APPROVAL"

                }

                )

            )

        }

    );

}




export function generateAllReports(
findings:any[]
){

    return {

        duplicateReport:
        generateDuplicateReport(
            findings
        ),


        cleanupPlan:
        generateCleanupPlan(
            findings
        ),


        migrationDecision:
        generateMigrationDecision(
            findings
        )

    };

}
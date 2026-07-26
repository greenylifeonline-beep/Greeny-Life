export function calculateConfidence(
    sameContent:boolean,
    migration:boolean
){

    if(sameContent && migration)
        return 100;


    if(sameContent)
        return 95;


    if(migration)
        return 85;


    return 60;

}
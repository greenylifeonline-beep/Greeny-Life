export const DUPLICATE_KEYS = [

    "id",

    "ref_id",

    "product_code"

];


export const MIGRATION_PATHS = {

    legacy:
    "data/legacy/products.json",

    migrated:
    "data/migrated_products.json",

    master:
    "data/05_master_products.json"

};


export const CONFIDENCE = {

    EXACT_DUPLICATE:100,

    MIGRATION_MATCH:100,

    DATA_CONFLICT:60,

    POSSIBLE_DUPLICATE:40

};


export const DUPLICATE_POLICY = {

    identityPriority:[

        "id",

        "ref_id",

        "product_code"

    ],


    comparisonMode:

    "semantic",


    autoCleanupConfidence:

    100

};
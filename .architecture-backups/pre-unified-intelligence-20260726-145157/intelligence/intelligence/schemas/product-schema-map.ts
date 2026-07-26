/**
 * GL-DOS Product Schema Intelligence Map
 *
 * مسؤول عن توحيد وفهم جميع مصادر المنتجات:
 *
 * 1. Legacy Products
 *    data/legacy/products.json
 *
 * 2. Migrated Products
 *    data/migrated_products.json
 *
 * 3. Master Products
 *    data/05_master_products.json
 *
 * الهدف:
 * - منع أخطاء Audit بسبب اختلاف البنية
 * - توحيد المقارنة
 * - دعم Migration Engine
 * - دعم Duplicate Engine
 */


export type ProductSource =
    | "legacy"
    | "migrated"
    | "master";



/**
 * الحقول الأساسية للهوية
 */
export const PRODUCT_IDENTITY_FIELDS = [

    "id",

    "product_code",

    "ref_id"

] as const;



/**
 * كل المنتجات الرسمية في النظام
 */
export const MASTER_PRODUCTS = {


    honey:[

        "wildflower-honey",

        "citrus-honey",

        "clover-honey"

    ],


    bee_products:[

        "royal-jelly",

        "raw-propolis",

        "bee-pollen",

        "pure-beeswax"

    ],


    spices:[

        "garlic-powder",

        "onion-powder",

        "turmeric-powder",

        "sweet-paprika",

        "roasted-cumin",

        "seven-spices-blend"

    ],


    herbs:[

        "hibiscus-flowers"

    ],


    oils:[

        "black-seed-oil"

    ]


} as const;



/**
 * العدد المتوقع للمنتجات
 */
export const EXPECTED_PRODUCT_COUNT = 15;



/**
 * Mapping لكل مصدر بيانات
 */
export const PRODUCT_SCHEMA_MAP = {



    legacy:{


        id:
        "id",


        name:
        "name",


        category:
        "category",


        image:
        "image",


        status:
        "status"



    },




    migrated:{


        id:
        "id",


        name:
        "name",


        category:
        "category",


        image:
        "image",


        status:
        "status"



    },






    master:{


        id:
        "id",


        name:
        "name.en",


        name_ar:
        "name.ar",


        category:
        "collection",


        image:
        "media.profile",


        status:
        "status.active"



    }



} as const;





/**
 * تحويل أي قيمة اسم إلى اسم موحد
 */
export function resolveProductName(
    product:any,
    source:ProductSource
):string {


    const map =
    PRODUCT_SCHEMA_MAP[source];


    const value =
    getNestedValue(
        product,
        map.name
    );


    if(typeof value === "string")
        return value;



    return "";

}





/**
 * استخراج التصنيف
 */
export function resolveCategory(
    product:any,
    source:ProductSource
):string {


    const map =
    PRODUCT_SCHEMA_MAP[source];


    const value =
    getNestedValue(
        product,
        map.category
    );


    if(typeof value==="string")
        return value;


    return "";

}





/**
 * توحيد حالة المنتج
 */
export function resolveStatus(
    product:any,
    source:ProductSource
):boolean {


    const map =
    PRODUCT_SCHEMA_MAP[source];


    const value =
    getNestedValue(
        product,
        map.status
    );



    if(typeof value==="boolean")
        return value;



    if(typeof value==="string"){

        return [

            "active",

            "published",

            "enabled"

        ]
        .includes(
            value.toLowerCase()
        );

    }



    return false;

}





/**
 * استخراج الصورة
 */
export function resolveImage(
    product:any,
    source:ProductSource
):string {


    const map =
    PRODUCT_SCHEMA_MAP[source];


    const value =
    getNestedValue(
        product,
        map.image
    );


    if(typeof value==="string")
        return value;


    return "";

}






/**
 * استخراج ID
 */
export function resolveId(
    product:any
):string {


    return (

        product?.id ??

        product?.product_code ??

        product?.ref_id ??

        ""

    );

}





/**
 * مقارنة منتج موحد
 */
export function normalizeProduct(
    product:any,
    source:ProductSource
){

    return {


        id:
        resolveId(product),



        name:
        resolveProductName(
            product,
            source
        ),



        category:
        resolveCategory(
            product,
            source
        ),



        image:
        resolveImage(
            product,
            source
        ),



        active:
        resolveStatus(
            product,
            source
        )


    };

}





/**
 * قراءة مسار داخلي مثل:
 *
 * status.active
 *
 * name.en
 */
function getNestedValue(
    object:any,
    path:string
):any {


    return path
        .split(".")
        .reduce(

            (current,key)=>
            current?.[key],

            object

        );

}
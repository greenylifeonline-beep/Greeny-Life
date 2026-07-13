async function loadProducts() {

    try {

        const response = await fetch("../../data/products.json");

        const products = await response.json();

        alert("Products count = " + products.length);

    }

    catch(error){

        alert(error);

    }

}

loadProducts();
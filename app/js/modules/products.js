async function loadProducts() {

    try {

        const response = await fetch("../../data/products.json");

        const products = await response.json();

        alert("Products loaded: " + products.length);

        console.log(products);

    } catch (error) {

        alert("ERROR: " + error);

    }

}

loadProducts();
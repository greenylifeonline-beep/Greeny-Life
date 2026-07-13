async function loadProducts() {

    try {

        const response = await fetch("../../data/products.json");

        alert("Status: " + response.status);

    } catch (error) {

        alert("ERROR: " + error);

    }

}

loadProducts();
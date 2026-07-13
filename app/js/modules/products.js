async function loadProducts() {

    const response = await fetch("../data/products.json");

    const products = await response.json();

    console.log(products);

}

loadProducts();
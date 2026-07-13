async function loadProducts() {

    try {

        const response = await fetch("../../data/products.json");

        if (!response.ok) {
            throw new Error("Failed to load products.json");
        }

        const products = await response.json();

        console.log("Products Loaded:");
        console.log(products);

    } catch (error) {

        console.error("Error:", error);

    }

}

loadProducts();
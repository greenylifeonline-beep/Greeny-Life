async function loadProducts() {

    try {

        const params = new URLSearchParams(window.location.search);
        const selectedCategory = params.get("category");

        const response = await fetch("../../data/products.json");
        const products = await response.json();

        let filteredProducts = products;

        if (selectedCategory) {
            filteredProducts = products.filter(product =>
                product.category === selectedCategory
            );
        }

        const container = document.getElementById("products");

        if (!container) {
            console.error("Products container not found.");
            return;
        }

        container.innerHTML = "";

        filteredProducts.forEach(product => {

            const card = document.createElement("a");

            card.className = "card product-card";

            card.href = `product.html?id=${product.id}`;

            card.innerHTML = `
                <img
                    src="${product.image}"
                    alt="${product.name}"
                    class="product-image">

                <div class="product-content">

                    <h3>${product.name}</h3>

                    <p>${product.shortDescription || ""}</p>

                    <span class="explore-btn">
                        View Product →
                    </span>

                </div>
            `;

            container.appendChild(card);

        });

        const title = document.getElementById("page-title");

        if (title) {

            if (selectedCategory) {
                title.textContent = selectedCategory;
            } else {
                title.textContent = "All Products";
            }

        }

    }

    catch (error) {

        console.error(error);

    }

}

loadProducts();
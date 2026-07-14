async function loadCategories() {

    const imageMap = {
    "Honey": "../assets/images/categories/honey.jpg",
    "Bee Products": "../assets/images/categories/bee-products.jpg",
    "Premium Spices": "../assets/images/categories/spices.jpg",
    "Natural Oils": "../assets/images/categories/oils.jpg"
};

    const linkMap = {
        "Honey": "honey.html",
        "Bee Products": "bee-products.html",
        "Premium Spices": "spices.html",
        "Natural Oils": "natural-oils.html"
    };

    const response = await fetch("../../data/products.json");
    const products = await response.json();

    const container = document.getElementById("collections");

    const categories = {};

    products.forEach(product => {

        if (!categories[product.category]) {
            categories[product.category] = [];
        }

        categories[product.category].push(product);

    });

    container.innerHTML = "";

    for (const category in categories) {

        const card = document.createElement("a");

        card.className = "card category-card";

        card.href = linkMap[category] || "#";

        card.innerHTML = `
            <img src="${imageMap[category]}" alt="${category}" class="category-image">

            <div class="category-content">

                <h3>${category}</h3>

                <p>${categories[category].length} Products</p>

                <span class="explore-btn">
                    Explore Collection →
                </span>

            </div>
        `;

        container.appendChild(card);

    }

}

loadCategories();
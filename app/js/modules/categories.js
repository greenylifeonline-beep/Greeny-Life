const imageMap = {
    "Honey": "../assets/images/categories/Honey.jpg",
    "Bee Products": "../assets/images/categories/BeeProducts.jpg",
    "Premium Spices": "../assets/images/categories/Spices.jpg",
    "Natural Oils": "../assets/images/categories/Oils.jpg"
};

const linkMap = {
    "Honey": "honey.html",
    "Bee Products": "bee-products.html",
    "Premium Spices": "spices.html",
    "Natural Oils": "natural-oils.html"
};

for (const category in categories) {

    const card = document.createElement("a");

    card.className = "card category-card";

    card.href = linkMap[category] || "#";

    card.innerHTML = `
        <img
            src="${imageMap[category]}"
            alt="${category}"
            class="category-image">

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
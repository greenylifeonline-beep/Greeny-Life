console.log("GREENY LIFE Packaging System Started");

document.addEventListener("DOMContentLoaded", () => {

    console.log("System Ready");

    const cards = document.querySelectorAll(".card");

    cards.forEach(card => {

        card.addEventListener("click", () => {

            card.style.transform = "scale(1.03)";

            setTimeout(() => {

                card.style.transform = "";

            },200);

        });

    });

});

/* ===========================
   GL-DOS Product Engine v1.0
=========================== */

async function loadProducts() {
    try {

        const response = await fetch("data/master/products.json");

        const products = await response.json();

        console.log("GL-DOS Products Loaded:", products);

    } catch (error) {

        console.error("Failed to load products", error);

    }
}

document.addEventListener("DOMContentLoaded", loadProducts);

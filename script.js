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

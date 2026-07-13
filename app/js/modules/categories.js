async function loadCategories() {

    try {

        const response = await fetch("../../data/categories.json");

        const categories = await response.json();

        console.log(categories);

    } catch (error) {

        console.error(error);

    }

}

loadCategories();
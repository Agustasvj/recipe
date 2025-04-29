document.addEventListener('DOMContentLoaded', () => {
    const images = [
        '/static/main_meal.jpg',
        '/static/baking.jpg',
        '/static/desert.jpg'
    ];
    images.forEach(src => {
        const img = new Image();
        img.src = src;
    });

    const themeSwitcher = document.querySelector('.theme-switcher');
    const body = document.body;

    if (!localStorage.getItem('theme')) {
        body.classList.add('dark-theme');
        themeSwitcher.textContent = '🌓';
        localStorage.setItem('theme', 'dark');
    } else if (localStorage.getItem('theme') === 'light') {
        body.classList.remove('dark-theme');
        themeSwitcher.textContent = '🌙';
    } else {
        body.classList.add('dark-theme');
        themeSwitcher.textContent = '🌓';
    }

    themeSwitcher.addEventListener('click', () => {
        if (body.classList.contains('dark-theme')) {
            body.classList.remove('dark-theme');
            themeSwitcher.textContent = '🌙';
            localStorage.setItem('theme', 'light');
        } else {
            body.classList.add('dark-theme');
            themeSwitcher.textContent = '🌓';
            localStorage.setItem('theme', 'dark');
        }
    });

    const navToggle = document.querySelector('.nav-toggle');
    const navMenu = document.querySelector('.nav-menu');
    const navClose = document.querySelector('.nav-close');

    if (navToggle && navMenu) {
        navToggle.addEventListener('click', () => {
            navMenu.classList.toggle('active');
            navToggle.classList.toggle('open');
        });
    }

    if (navClose && navMenu) {
        navClose.addEventListener('click', () => {
            navMenu.classList.remove('active');
            navToggle.classList.remove('open');
        });
    }

    const navLinks = document.querySelectorAll('.nav-link');
    const currentPath = window.location.pathname;
    navLinks.forEach(link => {
        const linkPath = new URL(link.href).pathname;
        if (linkPath === currentPath || (linkPath === '/' && currentPath === '')) {
            link.classList.add('active');
        }
    });
});

async function addRecipe() {
    const name = document.getElementById('recipeName').value;
    const type = document.getElementById('recipeType').value;
    const ingredients = document.getElementById('recipeIngredients').value.split('\n').filter(i => i.trim());
    const instructions = document.getElementById('recipeInstructions').value;
    const remarks = document.getElementById('recipeRemarks').value;
    const image = document.getElementById('recipeImage').value || 'https://via.placeholder.com/150';

    if (name && type && ingredients.length > 0 && instructions) {
        const recipe = { name, type, ingredients, instructions, remarks, image };
        try {
            const response = await fetch('/add_recipe', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(recipe)
            });
            if (response.ok) {
                alert('Recipe added!');
                clearForm();
            } else {
                alert('Failed, try again!');
            }
        } catch (error) {
            alert('Network error: ' + error.message);
        }
    } else {
        alert('Fill in all the required fields!');
    }
}

async function editRecipe(id) {
    const name = document.getElementById('recipeName').value;
    const type = document.getElementById('recipeType').value;
    const ingredients = document.getElementById('recipeIngredients').value.split('\n').filter(i => i.trim());
    const instructions = document.getElementById('recipeInstructions').value;
    const remarks = document.getElementById('recipeRemarks').value;
    const image = document.getElementById('recipeImage').value || 'https://via.placeholder.com/150';

    if (name && type && ingredients.length > 0 && instructions) {
        const recipe = { name, type, ingredients, instructions, remarks, image };
        try {
            const response = await fetch(`/edit_recipe/${id}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(recipe)
            });
            if (response.ok) {
                alert('Recipe updated!');
                const routeMap = {
                    'main_meal': '/main_meals',
                    'baking': '/baking',
                    'desert': '/desert'
                };
                window.location.href = routeMap[type] || '/';
            } else {
                alert('Update failed, try again!');
            }
        } catch (error) {
            alert('Network error: ' + error.message);
        }
    } else {
        alert('Fill in all the required fields!');
    }
}

async function deleteRecipe(id) {
    if (confirm('You sure you wanna remove recipe?')) {
        try {
            const response = await fetch(`/delete_recipe/${id}`, {
                method: 'DELETE'
            });
            if (response.ok) {
                alert('Recipe deleted!');
                location.reload();
            } else {
                alert('Deletion failed, try again!');
            }
        } catch (error) {
            alert('Network error: ' + error.message);
        }
    }
}

function clearForm() {
    document.getElementById('recipeName').value = '';
    document.getElementById('recipeType').value = '';
    document.getElementById('recipeIngredients').value = '';
    document.getElementById('recipeInstructions').value = '';
    document.getElementById('recipeRemarks').value = '';
    document.getElementById('recipeImage').value = '';
}

function searchRecipes() {
    const input = document.querySelector('.search-bar').value.toLowerCase();
    const cards = document.querySelectorAll('.recipe-card');
    cards.forEach(card => {
        const name = card.querySelector('h3').textContent.toLowerCase();
        const ingredients = card.querySelectorAll('ol')[0].textContent.toLowerCase();
        if (name.includes(input) || ingredients.includes(input)) {
            card.style.display = '';
        } else {
            card.style.display = 'none';
        }
    });
}
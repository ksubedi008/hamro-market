const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');

// Cart State Management
let cart = JSON.parse(localStorage.getItem('bn_cart')) || [];

function updateCartCount() {
    const count = cart.reduce((sum, item) => sum + item.quantity, 0);
    const counter = document.getElementById('cart-count');
    if (counter) counter.innerText = count;
}

function saveCart() {
    localStorage.setItem('bn_cart', JSON.stringify(cart));
    updateCartCount();
    renderCartDropdown();
}

function addToCart(productId, name, price, image) {
    if (window.isLoggedIn === false) {
        window.location.href = '/login';
        return;
    }
    const existing = cart.find(i => i.productId == productId);
    if (existing) {
        existing.quantity += 1;
    } else {
        cart.push({ productId, name, price, image, quantity: 1 });
    }
    saveCart();
    showAddedToCartModal(productId);
}

function removeFromCart(productId) {
    cart = cart.filter(i => i.productId != productId);
    saveCart();
}

function updateCartItemQuantity(productId, change, fromModal = false) {
    const item = cart.find(i => i.productId == productId);
    if (item) {
        if (change < 0 && item.quantity <= 1) return;
        item.quantity += change;
        saveCart();
        if (fromModal) {
            // Re-render modal to reflect new quantity
            showAddedToCartModal(productId);
        }
    }
}

// UI Interactions - Modal & Dropdown
function showAddedToCartModal(productId) {
    const item = cart.find(i => i.productId == productId);
    if (!item) return;

    const detailsEl = document.getElementById('modal-product-details');
    if (!detailsEl) return;
    
    detailsEl.innerHTML = `
        <img src="${item.image}" alt="${item.name}" style="width: 100px; height: 100px; object-fit: cover; border-radius: 8px;">
        <div style="flex: 1;">
            <h4 style="margin: 0 0 10px 0;">${item.name}</h4>
            <div style="color: var(--color-primary); font-weight: bold; margin-bottom: 10px;">Rs ${item.price.toFixed(2)}</div>
            <div class="quantity-stepper">
                <button class="stepper-btn" onclick="updateCartItemQuantity(${item.productId}, -1, true)" ${item.quantity <= 1 ? 'disabled' : ''}>-</button>
                <span class="stepper-val">${item.quantity}</span>
                <button class="stepper-btn" onclick="updateCartItemQuantity(${item.productId}, 1, true)">+</button>
            </div>
        </div>
    `;
    
    document.getElementById('added-to-cart-modal').style.display = 'flex';
}

function closeCartModal() {
    const modal = document.getElementById('added-to-cart-modal');
    if (modal) modal.style.display = 'none';
}

function renderCartDropdown() {
    const container = document.getElementById('cart-dropdown-items');
    const totalEl = document.getElementById('cart-total');
    if (!container || !totalEl) return;
    
    container.innerHTML = '';
    let total = 0;
    
    if (cart.length === 0) {
        container.innerHTML = '<div style="text-align: center; color: #888;">Your cart is empty</div>';
    } else {
        cart.forEach(item => {
            const itemTotal = item.price * item.quantity;
            total += itemTotal;
            container.innerHTML += `
                <div class="cart-item" style="padding-bottom: 10px; margin-bottom: 10px;">
                    <div style="flex: 1;">
                        <strong>${item.name}</strong><br>
                        <div style="display: flex; align-items: center; margin-top: 5px; justify-content: space-between;">
                            <span>Rs ${item.price} x </span>
                            <div class="quantity-stepper" style="margin-left: 5px;">
                                <button class="stepper-btn" onclick="updateCartItemQuantity(${item.productId}, -1)" ${item.quantity <= 1 ? 'disabled' : ''}>-</button>
                                <span class="stepper-val">${item.quantity}</span>
                                <button class="stepper-btn" onclick="updateCartItemQuantity(${item.productId}, 1)">+</button>
                            </div>
                        </div>
                    </div>
                    <div style="text-align: right; margin-left: 15px;">
                        <span style="font-weight: bold;">Rs ${itemTotal.toFixed(2)}</span><br>
                        <a href="#" onclick="removeFromCart(${item.productId}); return false;" style="color: red; font-size: 0.8rem; margin-top: 5px; display: inline-block;">Remove</a>
                    </div>
                </div>
            `;
        });
    }
    totalEl.innerText = `Rs ${total.toFixed(2)}`;
}

// Product Fetching
async function fetchProducts(category = 'all', searchQuery = '') {
    const container = document.getElementById('products-container');
    if (!container) return;
    
    try {
        let url = `/api/products?category=${category}`;
        if (searchQuery) url += `&search=${encodeURIComponent(searchQuery)}`;
        const res = await fetch(url);
        const products = await res.json();
        
        container.innerHTML = '';
        products.forEach(p => {
            container.innerHTML += `
                <div class="product-card">
                    <a href="/product/${p.slug}">
                        <img src="${p.image_url}" alt="${p.name}" class="product-img">
                    </a>
                    <div class="product-info">
                        <h3>${p.name}</h3>
                        <div class="rating" style="margin-bottom: 5px;">
                            ${p.review_count > 0 ? `<span style="color: #E67E22; font-weight: bold;">${p.avg_rating} ⭐</span> <span style="font-size: 0.8rem; color: #666;">(${p.review_count})</span>` : `<span style="color: #999; font-size: 0.9rem;">No reviews yet</span>`}
                        </div>
                        <div class="price">Rs ${p.price.toFixed(2)}</div>
                        <button class="btn add-to-cart" onclick="addToCart(${p.id}, '${p.name}', ${p.price}, '${p.image_url}')">Add to Cart</button>
                    </div>
                </div>
            `;
        });
    } catch (e) {
        console.error("Error fetching products", e);
    }
}

// Init
document.addEventListener('DOMContentLoaded', () => {
    updateCartCount();
    renderCartDropdown();
    
    if (document.getElementById('products-container')) {
        fetchProducts();
        
        const searchBtn = document.getElementById('search-btn');
        const searchInput = document.getElementById('search-input');
        if (searchBtn && searchInput) {
            searchBtn.addEventListener('click', () => {
                const activeFilter = document.querySelector('.filter-btn.active');
                const category = activeFilter ? activeFilter.dataset.category : 'all';
                fetchProducts(category, searchInput.value);
            });
            searchInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') searchBtn.click();
            });
        }
    }
    
    const filterBtns = document.querySelectorAll('.filter-btn');
    filterBtns.forEach(btn => {
        btn.addEventListener('click', (e) => {
            filterBtns.forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');
            const searchInput = document.getElementById('search-input');
            const sq = searchInput ? searchInput.value : '';
            fetchProducts(e.target.dataset.category, sq);
        });
    });
    
    // Star Rating Initialization
    const starInputs = document.querySelectorAll('.star-rating-input');
    starInputs.forEach(input => {
        const targetId = input.getAttribute('data-target');
        const hiddenInput = document.getElementById(targetId);
        const stars = input.querySelectorAll('.star');
        
        function updateStars(value) {
            stars.forEach(s => {
                if (parseInt(s.getAttribute('data-value')) <= value) {
                    s.classList.add('active');
                } else {
                    s.classList.remove('active');
                }
            });
        }
        
        stars.forEach(star => {
            star.addEventListener('mouseover', () => {
                updateStars(parseInt(star.getAttribute('data-value')));
            });
            star.addEventListener('mouseout', () => {
                updateStars(parseInt(hiddenInput.value));
            });
            star.addEventListener('click', () => {
                hiddenInput.value = star.getAttribute('data-value');
                updateStars(parseInt(hiddenInput.value));
            });
        });
    });
});

// Reviews
async function submitReview(event, productId) {
    event.preventDefault();
    const rating = document.getElementById('review-rating').value;
    const comment = document.getElementById('review-comment').value;
    
    try {
        const res = await fetch(`/api/reviews/${productId}`, {
            method: 'POST',
            headers: { 'X-CSRFToken': csrfToken, 'Content-Type': 'application/json' },
            body: JSON.stringify({ rating, comment })
        });
        
        const data = await res.json();
        if (data.success) {
            window.location.reload();
        } else {
            alert('Failed to submit review: ' + (data.message || 'Unknown error'));
        }
    } catch (e) {
        alert('Error submitting review');
    }
}

function openEditModal(reviewId, currentRating, currentComment) {
    document.getElementById('edit-review-id').value = reviewId;
    document.getElementById('edit-review-rating').value = currentRating;
    document.getElementById('edit-review-comment').value = currentComment;
    
    // Update stars visually
    const input = document.querySelector('.star-rating-input[data-target="edit-review-rating"]');
    if (input) {
        const stars = input.querySelectorAll('.star');
        stars.forEach(s => {
            if (parseInt(s.getAttribute('data-value')) <= currentRating) {
                s.classList.add('active');
            } else {
                s.classList.remove('active');
            }
        });
    }
    
    document.getElementById('edit-review-modal').style.display = 'flex';
}

function closeEditModal() {
    document.getElementById('edit-review-modal').style.display = 'none';
}

async function saveReviewEdit(event) {
    event.preventDefault();
    const reviewId = document.getElementById('edit-review-id').value;
    const rating = document.getElementById('edit-review-rating').value;
    const comment = document.getElementById('edit-review-comment').value;
    
    try {
        const res = await fetch(`/api/review_action/${reviewId}`, {
            method: 'PUT',
            headers: { 'X-CSRFToken': csrfToken, 'Content-Type': 'application/json' },
            body: JSON.stringify({ rating, comment })
        });
        
        const data = await res.json();
        if (data.success) {
            window.location.reload();
        } else {
            alert('Failed to update review: ' + (data.message || 'Unknown error'));
        }
    } catch (e) {
        alert('Error updating review');
    }
}

async function deleteReview(reviewId) {
    if (!confirm('Are you sure you want to delete this review?')) return;
    
    try {
        const res = await fetch(`/api/review_action/${reviewId}`, {
            method: 'DELETE',
            headers: { 'X-CSRFToken': csrfToken }
        });
        
        const data = await res.json();
        if (data.success) {
            window.location.reload();
        } else {
            alert('Failed to delete review: ' + (data.message || 'Unknown error'));
        }
    } catch (e) {
        alert('Error deleting review');
    }
}

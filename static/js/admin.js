const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');

document.addEventListener('DOMContentLoaded', () => {
    
    const loginForm = document.getElementById('admin-login-form');
    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;
            
            try {
                const res = await fetch('/api/admin/login', {
                    method: 'POST',
                    headers: { 'X-CSRFToken': csrfToken, 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username, password })
                });
                const data = await res.json();
                
                if (data.success) {
                    window.location.href = '/admin/dashboard';
                } else {
                    alert('Login failed: ' + data.message);
                }
            } catch (err) {
                console.error(err);
            }
        });
    }

    const metricsContainer = document.getElementById('admin-metrics');
    if (metricsContainer) {
        fetchAdminData();
        fetchCategories();
        fetchProductsAdmin();
        fetchOrdersAdmin();
        fetchCustomersAdmin();
    }
});

function escapeHTML(str) {
    if (str === null || str === undefined) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function showSection(section) {
    document.getElementById('overview-section').style.display = 'none';
    document.getElementById('products-section').style.display = 'none';
    document.getElementById('categories-section').style.display = 'none';
    document.getElementById('orders-section').style.display = 'none';
    document.getElementById('customers-section').style.display = 'none';
    
    document.getElementById('nav-overview').style.background = '';
    document.getElementById('nav-products').style.background = '';
    document.getElementById('nav-categories').style.background = '';
    document.getElementById('nav-orders').style.background = '';
    document.getElementById('nav-customers').style.background = '';
    
    document.getElementById(section + '-section').style.display = 'block';
    document.getElementById('nav-' + section).style.background = '#E2E8F0';
}

async function fetchAdminData() {
    try {
        const res = await fetch('/api/admin/metrics');
        if (res.status === 401 || res.status === 403) {
            window.location.href = '/admin/login.html';
            return;
        }
        const data = await res.json();
        
        document.getElementById('total-orders').innerText = data.total_orders;
        document.getElementById('total-revenue').innerText = 'Rs ' + data.total_revenue.toFixed(2);
        document.getElementById('low-stock').innerText = data.low_stock_alerts;
        
        const tableBody = document.getElementById('recent-orders');
        tableBody.innerHTML = '';
        data.recent_orders.forEach(order => {
            tableBody.innerHTML += `
                <tr>
                    <td>${escapeHTML(order.order_number)}</td>
                    <td>${escapeHTML(order.customer_name)}</td>
                    <td>Rs ${order.total_amount.toFixed(2)}</td>
                    <td>${escapeHTML(order.payment_status)}</td>
                    <td>${escapeHTML(order.order_status)}</td>
                </tr>
            `;
        });
        
    } catch (err) {
        console.error("Error fetching admin metrics", err);
    }
}

let categories = [];

async function fetchCategories() {
    try {
        const res = await fetch('/api/categories');
        categories = await res.json();
        const select = document.getElementById('p-category');
        select.innerHTML = categories.map(c => `<option value="${escapeHTML(c.id)}">${escapeHTML(c.name)}</option>`).join('');
        
        const tbody = document.getElementById('categories-table-body');
        tbody.innerHTML = categories.map(c => `
            <tr>
                <td>${escapeHTML(c.id)}</td>
                <td>${escapeHTML(c.name)}</td>
                <td>${escapeHTML(c.slug)}</td>
                <td>
                    <button class="btn btn-secondary" style="color: #2563EB; border: 1px solid #2563EB; background: transparent; padding: 4px 8px; margin-right: 5px;" onclick="openEditCategoryModal(${escapeHTML(c.id)}, '${escapeHTML(c.name)}', '${escapeHTML(c.slug)}')">Edit</button>
                    <button class="btn btn-secondary" style="color: #DC2626; border: 1px solid #DC2626; background: transparent; padding: 4px 8px;" onclick="deleteCategory(${escapeHTML(c.id)}, '${escapeHTML(c.name)}')">Delete</button>
                </td>
            </tr>
        `).join('');
    } catch (e) {
        console.error(e);
    }
}

async function fetchProductsAdmin() {
    try {
        const res = await fetch('/api/products');
        const products = await res.json();
        
        const tbody = document.getElementById('products-table-body');
        tbody.innerHTML = products.map(p => `
            <tr>
                <td>${escapeHTML(p.id)}</td>
                <td><img src="${escapeHTML(p.image_url)}" style="width: 50px; height: 50px; object-fit: cover;"></td>
                <td>${escapeHTML(p.name)}</td>
                <td>${escapeHTML(p.category_name)}</td>
                <td>Rs ${p.price.toFixed(2)}</td>
                <td>${escapeHTML(p.stock)}</td>
                <td>
                    <button class="btn btn-secondary" style="padding: 5px 10px; font-size: 0.8rem;" onclick='editProduct(${JSON.stringify(p).replace(/'/g, "&#39;")})'>Edit</button>
                    <button class="btn btn-danger" style="padding: 5px 10px; font-size: 0.8rem;" onclick="deleteProduct(${p.id})">Delete</button>
                </td>
            </tr>
        `).join('');
    } catch (e) {
        console.error(e);
    }
}

function openProductModal() {
    document.getElementById('product-form').reset();
    document.getElementById('p-id').value = '';
    document.getElementById('product-modal-title').innerText = 'Add Product';
    document.getElementById('product-modal').style.display = 'flex';
}
function closeProductModal() {
    document.getElementById('product-modal').style.display = 'none';
}

function editProduct(p) {
    document.getElementById('p-id').value = p.id;
    document.getElementById('p-name').value = p.name;
    document.getElementById('p-slug').value = p.slug;
    document.getElementById('p-category').value = p.category_id;
    document.getElementById('p-price').value = p.price;
    document.getElementById('p-stock').value = p.stock;
    document.getElementById('p-image').value = ''; // Clear file input
    document.getElementById('p-desc').value = p.description;
    document.getElementById('product-modal-title').innerText = 'Edit Product';
    document.getElementById('product-modal').style.display = 'flex';
}

async function saveProduct(e) {
    e.preventDefault();
    const id = document.getElementById('p-id').value;
    const url = id ? `/api/admin/products/${id}` : '/api/admin/products/add';
    const method = id ? 'PUT' : 'POST';
    
    const formData = new FormData();
    formData.append('name', document.getElementById('p-name').value);
    formData.append('slug', document.getElementById('p-slug').value);
    formData.append('category_id', document.getElementById('p-category').value);
    formData.append('price', document.getElementById('p-price').value);
    formData.append('stock', document.getElementById('p-stock').value);
    formData.append('description', document.getElementById('p-desc').value);
    
    const fileInput = document.getElementById('p-image');
    if (fileInput.files.length > 0) {
        formData.append('image_file', fileInput.files[0]);
    }
    
    const res = await fetch(url, {
        method,
        headers: { 'X-CSRFToken': csrfToken },
        body: formData
    });
    const data = await res.json();
    if (data.success) {
        closeProductModal();
        fetchProductsAdmin();
    } else {
        alert('Error: ' + data.message);
    }
}

async function deleteProduct(id) {
    if (!confirm('Are you sure you want to delete this product?')) return;
    const res = await fetch(`/api/admin/products/${id}`, { method: 'DELETE', headers: { 'X-CSRFToken': csrfToken } });
    const data = await res.json();
    if (data.success) {
        fetchProductsAdmin();
    } else {
        alert('Error: ' + data.message);
    }
}

function openCategoryModal() {
    document.getElementById('category-form').reset();
    document.getElementById('category-modal').style.display = 'flex';
}
function closeCategoryModal() {
    document.getElementById('category-modal').style.display = 'none';
}

async function saveCategory(e) {
    e.preventDefault();
    const name = document.getElementById('c-name').value;
    const slug = document.getElementById('c-slug').value;
    
    const res = await fetch('/api/admin/categories/add', {
        method: 'POST',
        headers: { 'X-CSRFToken': csrfToken, 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, slug })
    });
    const data = await res.json();
    if (data.success) {
        closeCategoryModal();
        fetchCategories();
    } else {
        alert('Error: ' + data.message);
    }
}

function openEditCategoryModal(id, name, slug) {
    document.getElementById('edit-c-id').value = id;
    document.getElementById('edit-c-name').value = name;
    document.getElementById('edit-c-slug').value = slug;
    document.getElementById('edit-category-modal').style.display = 'flex';
}

function closeEditCategoryModal() {
    document.getElementById('edit-category-modal').style.display = 'none';
}

async function updateCategory(e) {
    e.preventDefault();
    const id = document.getElementById('edit-c-id').value;
    const name = document.getElementById('edit-c-name').value;
    const slug = document.getElementById('edit-c-slug').value;
    
    const res = await fetch(`/api/admin/categories/edit/${id}`, {
        method: 'PUT',
        headers: { 'X-CSRFToken': csrfToken, 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, slug })
    });
    const data = await res.json();
    if (data.success) {
        closeEditCategoryModal();
        fetchCategories();
    } else {
        alert('Error: ' + data.message);
    }
}

async function deleteCategory(id, name) {
    if (!confirm(`Are you sure you want to delete the category '${name}'?`)) return;
    const res = await fetch(`/api/admin/categories/delete/${id}`, { method: 'DELETE', headers: { 'X-CSRFToken': csrfToken } });
    const data = await res.json();
    if (data.success) {
        fetchCategories();
    } else {
        alert('Error: ' + data.message);
    }
}

async function fetchOrdersAdmin() {
    try {
        const res = await fetch('/api/admin/orders');
        const orders = await res.json();
        
        const tbody = document.getElementById('all-orders-table-body');
        tbody.innerHTML = orders.map(o => `
            <tr>
                <td>${escapeHTML(o.order_number)}</td>
                <td>${escapeHTML(new Date(o.created_at).toLocaleDateString())}</td>
                <td>${escapeHTML(o.customer_name)}</td>
                <td>Rs ${o.total_amount.toFixed(2)}</td>
                <td>${escapeHTML(o.payment_status)}</td>
                <td>${escapeHTML(o.order_status)}</td>
            </tr>
        `).join('');
    } catch (e) {
        console.error(e);
    }
}

async function fetchCustomersAdmin() {
    try {
        const res = await fetch('/api/admin/customers');
        const customers = await res.json();
        
        const tbody = document.getElementById('customers-table-body');
        tbody.innerHTML = customers.map(c => `
            <tr>
                <td>${escapeHTML(c.id)}</td>
                <td>${escapeHTML(c.username)}</td>
                <td>${escapeHTML(c.name)}</td>
                <td>${escapeHTML(c.email)}</td>
                <td>${escapeHTML(c.phone)}</td>
                <td>
                    <button class="btn btn-secondary" style="padding: 5px 10px; font-size: 0.8rem;" onclick="viewCustomerDetails(${escapeHTML(c.id)})">View Details</button>
                </td>
            </tr>
        `).join('');
    } catch (e) {
        console.error(e);
    }
}

async function viewCustomerDetails(id) {
    try {
        const res = await fetch(`/api/admin/customers/${id}`);
        const data = await res.json();
        
        if (data.error) {
            alert(data.error);
            return;
        }
        
        const c = data.customer;
        document.getElementById('customer-info').innerHTML = `
            <strong>Name:</strong> ${escapeHTML(c.name)} <br>
            <strong>Username:</strong> ${escapeHTML(c.username)} <br>
            <strong>Email:</strong> ${escapeHTML(c.email)} <br>
            <strong>Phone:</strong> ${escapeHTML(c.phone)}
        `;
        
        const tbody = document.getElementById('customer-orders-body');
        tbody.innerHTML = data.orders.map(o => `
            <tr>
                <td>${escapeHTML(o.order_number)}</td>
                <td>${escapeHTML(new Date(o.created_at).toLocaleDateString())}</td>
                <td>Rs ${o.total_amount.toFixed(2)}</td>
                <td>${escapeHTML(o.payment_status)}</td>
                <td>${escapeHTML(o.order_status)}</td>
            </tr>
        `).join('');
        
        document.getElementById('customer-modal').style.display = 'flex';
    } catch (e) {
        console.error(e);
    }
}

function closeCustomerModal() {
    document.getElementById('customer-modal').style.display = 'none';
}

// Slug Generator Logic
function generateSlug(text) {
    return text.toString().toLowerCase()
        .replace(/\s+/g, '-')           // Replace spaces with hyphens (-)
        .replace(/&/g, '-and-')         // Replace ampersands (&) with '-and-'
        .replace(/[^\w\-]+/g, '')       // Remove all non-word characters (except hyphens)
        .replace(/\-\-+/g, '-')         // Replace multiple continuous hyphens with a single hyphen
        .replace(/^-+/, '')             // Trim leading hyphens
        .replace(/-+$/, '');            // Trim trailing hyphens
}

function updateSlug(sourceId, targetId) {
    const slugInput = document.getElementById(targetId);
    // Only mirror the text if the slug input is currently locked (readonly)
    if (slugInput.hasAttribute('readonly')) {
        const nameText = document.getElementById(sourceId).value;
        slugInput.value = generateSlug(nameText);
    }
}

function toggleSlugLock(targetId) {
    const slugInput = document.getElementById(targetId);
    if (slugInput.hasAttribute('readonly')) {
        slugInput.removeAttribute('readonly');
        slugInput.style.backgroundColor = 'white';
        slugInput.focus();
    } else {
        slugInput.setAttribute('readonly', 'true');
        slugInput.style.backgroundColor = '#f3f4f6';
    }
}

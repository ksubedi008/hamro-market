const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');

let nepalAddressData = {};

document.addEventListener('DOMContentLoaded', async () => {
    const cart = JSON.parse(localStorage.getItem('bn_cart')) || [];
    const summaryContainer = document.getElementById('checkout-summary');
    const totalEl = document.getElementById('checkout-total');
    
    if (cart.length === 0) {
        alert("Your cart is empty!");
        window.location.href = '/';
        return;
    }

    let total = 0;
    summaryContainer.innerHTML = '';
    cart.forEach(item => {
        const itemTotal = item.price * item.quantity;
        total += itemTotal;
        summaryContainer.innerHTML += `
            <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                <span>${item.name} (x${item.quantity})</span>
                <span>Rs ${itemTotal.toFixed(2)}</span>
            </div>
        `;
    });
    const deliveryCharge = 100.0;
    const grandTotal = total + deliveryCharge;

    summaryContainer.innerHTML += `
        <div style="display: flex; justify-content: space-between; margin-top: 15px; border-top: 1px solid #ccc; padding-top: 15px; color: #666;">
            <span>Subtotal</span>
            <span>Rs ${total.toFixed(2)}</span>
        </div>
        <div style="display: flex; justify-content: space-between; margin-top: 5px; color: #666;">
            <span>Delivery Charge</span>
            <span>Rs ${deliveryCharge.toFixed(2)}</span>
        </div>
    `;
    
    totalEl.innerText = grandTotal.toFixed(2);

    const provinceSelect = document.getElementById('province');
    const districtSelect = document.getElementById('district');
    const municipalitySelect = document.getElementById('municipality');

    try {
        const response = await fetch('/static/js/locations.json');
        nepalAddressData = await response.json();
        
        // Populate Provinces
        Object.keys(nepalAddressData).forEach(prov => {
            const opt = document.createElement('option');
            opt.value = prov;
            opt.textContent = prov;
            provinceSelect.appendChild(opt);
        });
    } catch (e) {
        console.error("Failed to load locations dataset", e);
    }

    provinceSelect.addEventListener('change', (e) => {
        const prov = e.target.value;
        districtSelect.innerHTML = '<option value="" disabled selected>Select District</option>';
        municipalitySelect.innerHTML = '<option value="" disabled selected>Select Municipality</option>';
        municipalitySelect.disabled = true;
        
        if (prov && nepalAddressData[prov]) {
            Object.keys(nepalAddressData[prov].districts).forEach(dist => {
                const opt = document.createElement('option');
                opt.value = dist;
                opt.textContent = dist;
                districtSelect.appendChild(opt);
            });
            districtSelect.disabled = false;
        } else {
            districtSelect.disabled = true;
        }
    });

    districtSelect.addEventListener('change', (e) => {
        const prov = provinceSelect.value;
        const dist = e.target.value;
        municipalitySelect.innerHTML = '<option value="" disabled selected>Select Municipality</option>';
        
        if (prov && dist && nepalAddressData[prov].districts[dist]) {
            nepalAddressData[prov].districts[dist].municipalities.forEach(mun => {
                const opt = document.createElement('option');
                opt.value = mun;
                opt.textContent = mun;
                municipalitySelect.appendChild(opt);
            });
            municipalitySelect.disabled = false;
        } else {
            municipalitySelect.disabled = true;
        }
    });

    const form = document.getElementById('checkout-form');
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        // Basic Regex Validation
        const phone = document.getElementById('phone').value;
        const phoneRegex = /^[0-9]{10}$/;
        if (!phoneRegex.test(phone)) {
            alert("Please enter a valid 10-digit phone number.");
            return;
        }

        const payload = {
            fullName: document.getElementById('fullName').value,
            email: document.getElementById('email').value,
            phone: phone,
            province: document.getElementById('province').value,
            district: document.getElementById('district').value,
            municipality: document.getElementById('municipality').value,
            ward_tol: document.getElementById('ward_tol').value,
            landmark: document.getElementById('landmark').value,
            totalAmount: total,
            items: cart
        };

        try {
            const res = await fetch('/api/orders/create', {
                method: 'POST',
                headers: { 'X-CSRFToken': csrfToken, 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            
            if (data.success && data.esewa_payload) {
                // Clear cart
                localStorage.removeItem('bn_cart');
                
                // Create a hidden form and submit it to eSewa
                const form = document.createElement('form');
                form.method = 'POST';
                form.action = data.esewa_url;
                
                for (const key in data.esewa_payload) {
                    if (data.esewa_payload.hasOwnProperty(key)) {
                        const hiddenField = document.createElement('input');
                        hiddenField.type = 'hidden';
                        hiddenField.name = key;
                        hiddenField.value = data.esewa_payload[key];
                        form.appendChild(hiddenField);
                    }
                }
                
                document.body.appendChild(form);
                form.submit();
                
            } else {
                alert("Order creation failed: " + (data.message || 'Unknown error'));
            }
        } catch (err) {
            console.error(err);
            alert("Error processing order.");
        }
    });
});

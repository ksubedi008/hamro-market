# Product Requirements Document (PRD)
**Project Name:** Hamro Market
**Version:** 1.0
**Date:** August 28, 2026

---

## 1. Executive Summary
Hamro Market is a custom-coded e-commerce web application designed for buying and selling certified organic groceries, pure honey, natural juices, and sustainable pantry items. The system operates on a lightweight Python backend using Flask, a local SQLite database, and vanilla HTML/CSS/JS for the frontend. It features a fully integrated checkout flow with a simulated eSewa payment gateway interface and a hidden administrative dashboard for inventory and order management.

---

## 2. Technology Stack
*   **Frontend:** HTML5, Custom CSS3 (Flexbox/Grid), Vanilla JavaScript (ES6, Fetch API, LocalStorage).
*   **Backend:** Python 3.x, Flask (Microframework).
*   **Database:** SQLite3.
*   **Payment Integration:** Custom eSewa sandbox simulation (UI clone of EPAYTEST).

---

## 3. UI/UX Design System
The design system utilizes a grounded, organic theme to reflect sustainability and health.

*   **Primary Deep Tone:** `#1E2D24` (Deep Forest Green — Headings, navbar, primary structure)
*   **Brand Primary / CTA:** `#2E7D32` (Leaf Green — Buttons, active navigation, badges)
*   **Surface Background:** `#F9F7F1` (Soft Oatmeal Cream — Body backdrop, product card fills)
*   **Amber Accent:** `#E67E22` (Honey Amber — Price highlights, sale badges, rating stars)
*   **Base White:** `#FFFFFF` (Card surfaces, input boxes, modal containers)
*   **Neutral Slate:** `#E2E8F0` (Input outlines, dividing lines, table borders)

---

## 4. Directory Structure
```text
hamro-market/
│
├── app.py                     # Main Flask Application & API Routes
├── database.py                # SQLite schema creation & seed data
├── bn_organic.db              # SQLite Database file
│
├── static/
│   ├── css/
│   │   ├── style.css          # Main storefront CSS 
│   │   ├── admin.css          # Custom Admin Dashboard styling
│   │   └── esewa.css          # eSewa mock interface styles
│   ├── js/
│   │   ├── main.js            # Product rendering, filter, cart management
│   │   ├── checkout.js        # Checkout validation & payment redirect
│   │   └── admin.js           # Admin CRUD AJAX calls & auth
│   └── images/                # Product assets
│
└── templates/
    ├── index.html             # Storefront (Hero, Catalog, Filters)
    ├── product-details.html   # Dedicated product detail view
    ├── checkout.html          # Order details & Billing address form
    ├── esewa-mock.html        # Simulated EPAYTEST payment screen
    ├── invoice.html           # Post-payment printable confirmation bill
    └── admin/
        ├── login.html         # Custom secret login (/sdmin/login.html)
        └── dashboard.html     # Custom Admin Console (CRUD & MIS Reports)
## 5. Database Schema (SQLite)

### 5.1 `categories`
*   `id` (INTEGER, PK, AUTOINCREMENT)
*   `name` (TEXT, NOT NULL, UNIQUE)
*   `slug` (TEXT, NOT NULL, UNIQUE)

### 5.2 `products`
*   `id` (INTEGER, PK, AUTOINCREMENT)
*   `category_id` (INTEGER, FK -> categories.id)
*   `name` (TEXT, NOT NULL)
*   `slug` (TEXT, NOT NULL, UNIQUE)
*   `price` (REAL, NOT NULL)
*   `stock` (INTEGER, NOT NULL, DEFAULT 10)
*   `description` (TEXT, NOT NULL)
*   `image_url` (TEXT, NOT NULL)
*   `rating` (REAL, DEFAULT 5.0)

### 5.3 `orders`
*   `id` (INTEGER, PK, AUTOINCREMENT)
*   `order_number` (TEXT, NOT NULL, UNIQUE)
*   `customer_name` (TEXT, NOT NULL)
*   `email` (TEXT, NOT NULL)
*   `phone` (TEXT, NOT NULL)
*   `street_address` (TEXT, NOT NULL)
*   `city` (TEXT, NOT NULL)
*   `state` (TEXT, NOT NULL)
*   `postal_code` (TEXT, NOT NULL)
*   `total_amount` (REAL, NOT NULL)
*   `payment_status` (TEXT, NOT NULL, DEFAULT 'PENDING')
*   `order_status` (TEXT, NOT NULL, DEFAULT 'PROCESSING')
*   `created_at` (TIMESTAMP, DEFAULT CURRENT_TIMESTAMP)

### 5.4 `order_items`
*   `id` (INTEGER, PK, AUTOINCREMENT)
*   `order_id` (INTEGER, FK -> orders.id)
*   `product_id` (INTEGER, FK -> products.id)
*   `quantity` (INTEGER, NOT NULL)
*   `unit_price` (REAL, NOT NULL)

### 5.5 `admins`
*   `id` (INTEGER, PK, AUTOINCREMENT)
*   `username` (TEXT, NOT NULL, UNIQUE)
*   `password_hash` (TEXT, NOT NULL)

---

## 6. Functional Modules

### 6.1 Storefront Module (`/`)
*   **Hero Section:** Banner with promotional text and call-to-action button.
*   **Product Catalog:** Grid layout displaying products with images, titles, prices, and ratings.
*   **Filtering:** Client-side category filtering (e.g., Groceries, Honey, Juice).
*   **Shopping Cart:** Stateful cart managed via `localStorage`. Slide-out drawer or dedicated page to adjust quantities and view subtotals.

### 6.2 Checkout Module (`/checkout`)
*   **Billing Form:** Captures customer details (Name, Address, City, Phone, Email) with client-side regex validation.
*   **Order Summary:** Displays itemized list of cart contents and total amount.
*   **Submission:** Creates a `PENDING` order in the database and redirects the user to the payment gateway simulation.

### 6.3 Payment Gateway Simulation (`/esewa-payment`)
*   **UI Matching:** Visually replicates the eSewa EPAYTEST sandbox environment.
*   **Functionality:** Accepts dummy eSewa credentials. Upon successful submission, updates the order's `payment_status` to `PAID` and redirects the user to a success/invoice page (`/invoice/<order_number>`).

### 6.4 Administrative Module (`/sdmin/login.html`)
*   **Authentication:** Secret login route bypassing standard directories. Uses Flask session cookies for authorization.
*   **Dashboard:**
    *   **Metrics:** Displays total revenue, order count, and low-stock alerts.
    *   **Inventory Management (CRUD):** Interface to add, edit, or remove products.
    *   **Order Management:** Ledger of all orders with the ability to update fulfillment status (Processing, Shipped, Delivered).

---

## 7. API Endpoints Specification

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/products` | Retrieves all active products. | No |
| `POST` | `/api/orders/create` | Validates cart data and creates a new order in the database. | No |
| `POST` | `/api/esewa/verify` | Simulates payment confirmation; updates order to PAID. | No |
| `POST` | `/api/admin/login` | Authenticates admin credentials and sets session. | No |
| `GET` | `/api/admin/metrics` | Retrieves dashboard summary statistics. | Yes |
| `POST` | `/api/admin/products/add` | Inserts a new product into the database. | Yes |
| `PUT` | `/api/admin/products/<id>` | Updates existing product details. | Yes |
| `DELETE` | `/api/admin/products/<id>` | Removes a product from the database. | Yes |
| `PUT` | `/api/admin/orders/<id>` | Updates the status of an order. | Yes |
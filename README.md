# 🏍️ Stratos Garage

> **Premium motorcycle performance & riding gear ecommerce platform**

[![Django](https://img.shields.io/badge/Django-092E20?style=for-the-badge&logo=django&logoColor=white)](https://www.djangoproject.com/)
[![React](https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)](https://reactjs.org/)
[![Postgres](https://img.shields.io/badge/postgres-%23316192.svg?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)

---

## 🌟 Features

*   **Product Variants:** Advanced catalog management supporting variants and inventory attributes.
*   **Inventory Management:** Real-time stock tracking and SKU handling.
*   **JWT Authentication:** Secure user authentication using JSON Web Tokens.
*   **Seller System:** Comprehensive multi-vendor architecture and dashboard.
*   **Orders & Payments:** End-to-end checkout processing with transaction integrity.
*   **Wishlist:** Users can save their favorite products.
*   **Reviews:** Rich product rating and feedback system.
*   **Razorpay Integration:** Seamless, secure checkout via Razorpay APIs.
*   **Docker Deployment:** Containerized ecosystem for instant spinning up.
*   **Redis + Celery:** Asynchronous task processing and reliable queueing.
*   **Production-Ready Backend:** Highly resilient API architected with DRF.
*   **React Frontend:** Fast, modern SPA.

---

## 💻 Tech Stack

### Backend
*   **Django** & **Django REST Framework (DRF)**
*   **PostgreSQL**
*   **Redis**
*   **Celery**

### Frontend
*   **React** & **Vite**
*   **Tailwind CSS**
*   **TanStack Start**

### Deployment
*   **Docker** & **Docker Compose**
*   **Nginx**
*   **Gunicorn**

---

## 📂 Project Structure

```text
Stratos Garage/
├── backend/                        # Django Backend Environment
│   ├── Stratosgarage/              # Django Settings & Core Configurations
│   ├── inventory/                  # Inventory & Stock Management App
│   ├── orders/                     # Order Processing & Cart App
│   ├── payments/                   # Payment Gateways (Razorpay) App
│   ├── products/                   # Catalog & Product Variants App
│   ├── sellers/                    # Multi-Vendor / Seller Dashboard App
│   ├── users/                      # JWT Auth & Accounts App
│   ├── wishlist/                   # User Wishlist App
│   ├── tests/                      # Pytest Test Suite
│   ├── nginx/                      # Production Reverse Proxy Configs
│   ├── Dockerfile                  # API Container Configuration
│   └── docker-compose.yml          # Container Orchestration
│
└── frontend/                       # React + Vite Frontend
    ├── public/                     # Static Assets
    ├── src/                        # Component Architecture
    └── package.json                # Frontend Dependencies
```

---

## 🚀 Installation Steps

### Backend Setup

1. **Create and Activate Virtual Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install Dependencies**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

3. **Database Migrations**
   ```bash
   python manage.py migrate
   ```

4. **Run Development Server**
   ```bash
   python manage.py runserver
   ```

### Frontend Setup

1. **Install Dependencies**
   ```bash
   cd frontend
   npm install
   ```

2. **Run Development Server**
   ```bash
   npm run dev
   ```

---

## 🔐 Environment Variables

Create a `.env` file in the backend directory (`backend/.env`) based on `.env.example`:

*   `SECRET_KEY`: Django Secret Key
*   **DB Configs**: `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`
*   **Razorpay Keys**: `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, `RAZORPAY_WEBHOOK_SECRET`
*   **Redis URL**: Message broker endpoint for Celery

---

## 🐳 Docker Deployment

To deploy the full production-ready stack (Django, Postgres, Redis, Celery, React, Nginx):

```bash
cd backend
docker-compose up --build
```

---

## 🧪 Testing

The backend test suite is powered by `pytest`. To run all tests:

```bash
cd backend
pytest
```

---

## 📸 UI Preview

> *[Placeholder for future frontend screenshots (Home, Catalog, Checkout, Seller Dashboard)]*

---

## 🔮 Future Improvements

*   **Mobile App:** Expanding the ecosystem to iOS & Android.
*   **Analytics:** Advanced reporting dashboard for sellers and platform admins.
*   **AI Recommendations:** Machine learning-driven personalized gear and accessory suggestions.
*   **Advanced Search:** Elasticsearch/Typesense integration for ultra-fast full-text querying.

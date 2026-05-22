# 🏍️ Stratos Garage

> **Premium motorcycle performance & riding gear e-commerce platform**

[![Django](https://img.shields.io/badge/Django-092E20?style=for-the-badge&logo=django&logoColor=white)](https://www.djangoproject.com/)
[![React](https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)](https://reactjs.org/)
[![Postgres](https://img.shields.io/badge/postgres-%23316192.svg?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/redis-%23DD0031.svg?style=for-the-badge&logo=redis&logoColor=white)](https://redis.io/)
[![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)
[![Celery](https://img.shields.io/badge/Celery-37814A?style=for-the-badge&logo=celery&logoColor=white)](https://docs.celeryq.dev/)

---

## 🌟 Features

| Feature | Description |
|---|---|
| 🛒 **Cart & Checkout** | Full multi-step checkout with shipping autofill via India Post API |
| 💰 **COD & Razorpay** | Cash on Delivery + UPI QR payment modal with animated countdown |
| 📦 **Order Management** | Order tracking timeline, history, and seller order dashboard |
| 🏪 **Multi-Vendor** | Seller registration, product management & revenue analytics |
| 🔐 **JWT Auth + OTP** | Secure authentication with OTP email verification flow |
| 📬 **Email Notifications** | Async buyer/seller emails via Celery (order confirmation, login alerts) |
| 🗃️ **Product Variants** | SKU-level variants with attribute types (size, color, etc.) |
| 📊 **Inventory System** | Real-time stock reservations with `select_for_update` thread safety |
| ❤️ **Wishlist** | Save and manage favourite products |
| 🧪 **Test Suite** | Comprehensive Pytest backend test coverage |
| 🐳 **Docker Ready** | Full containerised stack: Django, Postgres, Redis, Celery, Nginx |

---

## 💻 Tech Stack

### Backend
- **Django 5** & **Django REST Framework**
- **PostgreSQL** — Primary relational database
- **Redis** — Celery broker & cache
- **Celery** — Async email & background task queue
- **SimpleJWT** — JWT-based authentication
- **Gunicorn** — Production WSGI server

### Frontend
- **React 18** & **Vite**
- **TanStack Query** — Server state management
- **Zustand** — Global client state (auth, cart)
- **Tailwind CSS** — Utility-first styling
- **Framer Motion** — Animations & transitions
- **Lucide React** — Icon library

### Deployment
- **Docker** & **Docker Compose**
- **Nginx** — Reverse proxy & static file serving
- **GitHub Actions** — CI pipeline

---

## 📂 Project Structure

```
Stratos Garage/
├── backend/                        # Django API
│   ├── Stratosgarage/              # Core Settings (base/dev/prod)
│   ├── inventory/                  # Stock Management & Reservations
│   ├── orders/                     # Cart, Orders, COD & Checkout API
│   ├── payments/                   # Razorpay Payment Gateway
│   ├── products/                   # Catalog & Product Variants
│   ├── sellers/                    # Multi-Vendor Seller System
│   ├── users/                      # JWT Auth, OTP & Email Tasks
│   ├── wishlist/                   # User Wishlist
│   ├── tests/                      # Pytest Test Suite
│   ├── nginx/                      # Nginx Reverse Proxy Config
│   ├── Dockerfile
│   └── docker-compose.yml
│
└── frontend/                       # React + Vite SPA
    ├── public/images/categories/   # Category Banner Images
    └── src/
        ├── components/             # Layout, UI, Payment Modal
        ├── pages/                  # All Route Pages
        │   ├── auth/               # Login, Register, OTP, Reset
        │   ├── cart/               # Cart, Checkout, OrderSuccess
        │   ├── dashboard/          # Profile, Orders, Wishlist
        │   ├── products/           # ProductList, ProductDetail
        │   ├── shop/               # ShopCategory (/shop/:slug)
        │   └── seller/             # Seller Dashboard
        ├── services/api.js         # Axios Instance & Interceptors
        ├── store/                  # Zustand Stores (auth, cart)
        └── utils/currency.js       # INR Formatter
```

> Full detailed tree: [`tree_final.txt`](./tree_final.txt)

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL
- Redis

### Backend Setup

```bash
# 1. Clone and enter project
git clone https://github.com/Ajay-araj/Stratos-Garage.git
cd "Stratos Garage"

# 2. Create and activate virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# 3. Install dependencies
cd backend
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env with your DB, Redis, Razorpay, and email credentials

# 5. Run migrations
python manage.py migrate

# 6. Create superuser (optional)
python manage.py createsuperuser

# 7. Start development server
python manage.py runserver
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

App runs at: `http://localhost:5173`  
API runs at: `http://localhost:8000`

---

## 🔐 Environment Variables

Create `backend/.env` based on `backend/.env.example`:

```env
# Django
SECRET_KEY=your-secret-key
DEBUG=True
DJANGO_SETTINGS_MODULE=Stratosgarage.settings.development

# Database (PostgreSQL)
DB_NAME=stratos_garage
DB_USER=postgres
DB_PASSWORD=yourpassword
DB_HOST=localhost
DB_PORT=5432

# Redis & Celery
REDIS_URL=redis://localhost:6379/0

# Razorpay
RAZORPAY_KEY_ID=rzp_test_...
RAZORPAY_KEY_SECRET=...
RAZORPAY_WEBHOOK_SECRET=...

# Email (SMTP)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your@email.com
EMAIL_HOST_PASSWORD=your-app-password
```

---

## 🐳 Docker Deployment

Deploy the full production stack (Django + Postgres + Redis + Celery + Nginx):

```bash
cd backend
docker-compose up --build
```

Services started:
- `web` — Django API via Gunicorn
- `db` — PostgreSQL
- `redis` — Message broker
- `celery` — Background task worker
- `nginx` — Reverse proxy

---

## 🛒 Checkout Flow

```
User fills Shipping Form
  └─ Postal Code typed (6 digits)
       └─ India Post API auto-fills City / District / State / Country

User selects Payment Method
  ├─ Cash on Delivery  →  Place Order  →  Order Confirmed  →  /orders
  └─ Razorpay (UPI)    →  QR Modal  →  Scan & Pay  →  Mark Paid  →  /orders/success
```

---

## 🧪 Testing

```bash
cd backend
pytest                    # Run full test suite
pytest -v                 # Verbose output
pytest tests/test_auth.py # Run specific module
```

Test modules cover: `auth`, `products`, `orders`, `inventory`, `payments`, `sellers`, `wishlist`, `models`, `permissions`.

---

## 📸 Pages & Routes

| Route | Page |
|---|---|
| `/` | Home — Hero, Featured Products |
| `/products` | Product Catalog |
| `/products/:id` | Product Detail + Add to Cart |
| `/shop/:categorySlug` | Category Browse Page |
| `/cart` | Shopping Cart |
| `/checkout` | Checkout (Shipping + Payment) |
| `/orders` | Order History & Tracking |
| `/orders/success` | Order Confirmation Screen |
| `/dashboard` | User Profile |
| `/seller` | Seller Dashboard & Analytics |
| `/admin` | Admin Panel |

---

## 🔮 Future Improvements

- **Mobile App** — React Native iOS & Android client
- **Advanced Search** — Elasticsearch / Typesense full-text search
- **AI Recommendations** — Personalised gear suggestions via ML
- **Analytics Dashboard** — Extended seller and admin reporting
- **Push Notifications** — Real-time order status updates

---

## 👤 Author

**Ajay Araj**  
GitHub: [@Ajay-araj](https://github.com/Ajay-araj)

---

*Built as a DBMS mini-project — demonstrating full-stack e-commerce architecture with Django, React, PostgreSQL, Redis & Celery.*

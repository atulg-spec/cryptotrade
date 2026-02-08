# 🚀 TradeHub – Open Source Trading & Portfolio Tracking Web App

TradeHub is a modern, secure, and fully responsive web application designed for traders and investors to track portfolios, analyze performance, manage trades, and handle subscriptions/payments.

This project is open-source to help the community find bugs, improve the system, and identify potential issues.  
**Issues, discussions, and pull requests are welcome!**

---

## 📌 Overview

TradeHub provides a complete trading utility dashboard built using Django and Tailwind CSS.  
Originally developed for demo/learning purposes, it includes:

- Portfolio tracking  
- Performance analytics  
- Secure authentication  
- Admin panel  
- Promo & referral systems  
- Payment integration  

---

## 🛠️ Tech Stack

| Component | Technology |
|----------|------------|
| **Backend** | Django (Python) |
| **Frontend** | Tailwind CSS |
| **Database** | PostgreSQL |
| **Authentication** | Django AllAuth |
| **Admin Panel** | Custom Django Admin |
| **Payments** | Manual UPI verification |
---

## 🎯 Features

### 🌐 Public Website
- Home page (hero section, features, testimonials)
- About page
- FAQ & Disclaimer
- Contact page with form
- Clean footer with links

### 🔐 Authentication & Security
- User registration with email/phone verification  
- Login / Logout  
- Forgot password  
- CSRF protection  
- Secure password hashing  

### 📊 User Dashboard
- Portfolio summary (P/L, holdings, value)
- Order history page
- Performance charts (returns, win/loss ratio)
- Profile edit section
- Referral system (codes, tracking)
- Promo code application

### 🛠️ Admin Panel
- User & staff management (CRUD)
- Payment management + manual UPI verification
- Promo code management
- Referral management
- Site settings (logo, name, colors)
- Activity logs
- Admin-controlled chart settings

### 📱 Additional Features
- Fully mobile responsive  
- Logging for tracking user/admin activity  
- VPS deployment support  

---

## 🚀 Installation & Setup

### 1️⃣ Clone the Repository
```bash
git clone https://github.com/yourusername/tradehub.git
cd tradehub
````

### 2️⃣ Create Virtual Environment

```bash
python -m venv env
source env/bin/activate   # Linux/Mac
env\Scripts\activate      # Windows
```

### 3️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

### 4️⃣ Run Migrations

```bash
python manage.py migrate
```

### 5️⃣ Start Development Server

```bash
python manage.py runserver
```

---

## 🧪 Contributing & Bug Reporting

Since this project is public for testing:

* Report bugs in **Issues**
* Suggest new features in **Discussions**
* Make improvements via **Pull Requests**

We appreciate every contribution!

---

## ⚠️ Misuse Disclaimer

TradeHub is developed **for educational and demo purposes**.
The developer is **not responsible** for misuse after deployment.

Misuse includes:

* Fake accounts, referral abuse
* Payment manipulation
* Unauthorized access attempts
* Tampering with backend systems

The project owner is responsible for monitoring and enforcement.

---

## 📬 Contact

**Developer:** Atul Gupta
📞 +91 8423990159
📧 [atulg0736@gmail.com](mailto:atulg0736@gmail.com)
🌐 [https://startmarket.in](https://startmarket.in)

---

## ⭐ Support

If you find this useful, please:

* ⭐ Star the repository
* 🐞 Report issues
* 🚀 Contribute code

---
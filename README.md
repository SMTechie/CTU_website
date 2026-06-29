# CTU Training Solutions Portal

A web portal built with Flask, PostgreSQL, and Docker for CTU Training Solutions. The application provides user authentication, email functionality, multi-factor authentication (MFA), and a ticketing system.

---

# Features

* User authentication
* Multi-Factor Authentication (MFA)
* Email notifications
* Ticket management system
* PostgreSQL database
* Dockerized deployment
* Multiple web application instances

---

# Technologies Used

* Python 3
* Flask
* PostgreSQL
* Nginx
* Docker & Docker Compose
* HTML5
* CSS3
* JavaScript

---

# Prerequisites

Before running the project, ensure you have installed:

* Docker Desktop (or Docker Engine + Docker Compose)
* Git

---

# Setup

## 1. Clone the repository

```bash
git clone <repository-url>
cd <repository-folder>
```

## 2. Create a `.env` file

Copy the example environment file into your `.env` file

Or simply duplicate `env.example` and rename it to `.env`.

Fill in the following values:

```env
EMAIL_USERNAME_ENV=your-email@example.com
EMAIL_PASSWORD_ENV=your-email-app-password

FLASK_SECRET_KEY_ENV=your-generated-secret-key

DB_USER_ENV=portaluser
DB_PASSWORD_ENV=your-database-password

```

Generate a Flask secret key using:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## 3. Build and start the containers

```bash
docker compose up --build
```

To run in the background:

```bash
docker compose up -d --build
```

---

## 4. Stop the application

```bash
docker compose down
```

To also remove the PostgreSQL database volume:

```bash
docker compose down -v
```

---

# Project Structure

```
.
├── docker-compose.yml
├── Dockerfile
├── .env
├── env.example
├── nginx/ contains the nginx config
├── postgres/ contains the postgress database
├── templates/ contains the html files
├── website/ contains css and assets
└── webapp/ contains python files to run the app
```

---

# Notes

* Never commit your `.env` file. Use `.gitignore` to put the `.env` file in the list of files for git to ignore
* The database credentials in `.env` must match the PostgreSQL container credentials.
* If using Gmail, create an App Password rather than using your normal account password.

# Solvia Authentication System

SEO on AI Autopilot - User Authentication with Google Sheets Database

## 🚀 Overview

Solvia is a SaaS platform for SEO automation. This repository contains the authentication system built with FastAPI and Google Sheets as the database.

## 🏗️ Architecture

- **Framework**: FastAPI
- **Database**: Google Sheets (for alpha version)
- **Authentication**: JWT tokens
- **Password Hashing**: bcrypt
- **Email**: SMTP (Gmail)

## 📁 Project Structure

```
solvia/
├── app/
│   ├── __init__.py
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── models.py          # Pydantic models
│   │   ├── routes.py          # API endpoints
│   │   └── utils.py           # Auth utilities
│   ├── config.py              # Configuration
│   ├── database.py            # Google Sheets operations
│   └── main.py                # FastAPI app
├── requirements.txt
├── env.example
└── README.md
```

## 🛠️ Setup Instructions

### 1. Prerequisites

- Python 3.8+
- Google Cloud Project with Sheets API enabled
- Service account credentials
- Gmail account for sending emails

### 2. Install Dependencies

```bash
# Activate virtual environment
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Install packages
pip install -r requirements.txt
```

### 3. Google Sheets Setup

1. Create a Google Cloud Project
2. Enable Google Sheets API
3. Create a service account
4. Download the JSON credentials file
5. Create two Google Sheets:
   - `users` sheet with columns: email, password_hash, created_at, last_login, is_verified, verification_token, reset_token
   - `sessions` sheet with columns: user_email, session_token, created_at, expires_at
6. Share both sheets with your service account email

### 4. Environment Configuration

1. Copy `env.example` to `.env`
2. Update the following variables:
   - `USERS_SHEET_ID`: Your users sheet ID
   - `SESSIONS_SHEET_ID`: Your sessions sheet ID
   - `SECRET_KEY`: Generate a secure secret key
   - `EMAIL_USERNAME`: Your Gmail address
   - `EMAIL_PASSWORD`: Your Gmail app password

### 5. Place Credentials

Put your Google service account JSON file in the root directory as `credentials.json`

## 🚀 Running the Application

### Development Server

```bash
# Run with auto-reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Or run directly
python -m app.main
```

### Production Server

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 📚 API Documentation

Once the server is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🔐 API Endpoints

### Authentication

- `POST /auth/register` - Register new user
- `POST /auth/login` - Login user
- `POST /auth/verify-email` - Verify email address
- `POST /auth/forgot-password` - Request password reset
- `POST /auth/reset-password` - Reset password
- `POST /auth/logout` - Logout user
- `GET /auth/profile` - Get user profile

### Health Check

- `GET /` - Root endpoint
- `GET /health` - Health check

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `USERS_SHEET_ID` | Google Sheets ID for users | Required |
| `SESSIONS_SHEET_ID` | Google Sheets ID for sessions | Required |
| `SECRET_KEY` | JWT secret key | Required |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT token expiration | 30 |
| `EMAIL_USERNAME` | SMTP username | Required |
| `EMAIL_PASSWORD` | SMTP password | Required |

## 🧪 Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=app
```

## 🔒 Security Features

- Password hashing with bcrypt
- JWT token authentication
- Email verification
- Password reset functionality
- Rate limiting (TODO)
- Input validation
- CORS protection

## 📧 Email Templates

The system supports email verification and password reset emails. Templates need to be implemented in the email utility functions.

## 🚨 Important Notes

### Alpha Version Limitations

- Google Sheets has API rate limits
- Not suitable for high-traffic applications
- No built-in connection pooling
- Limited concurrent access

### Production Considerations

- Migrate to a proper database (PostgreSQL, MongoDB)
- Implement proper email service (SendGrid, AWS SES)
- Add rate limiting middleware
- Implement proper logging
- Add monitoring and alerting
- Use environment-specific configurations

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is proprietary software for Solvia.

## 🆘 Support

For support, contact the development team or create an issue in the repository. 
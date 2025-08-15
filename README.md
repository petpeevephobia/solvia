# Solvia SEO Audit Tool

SEO on AI Autopilot - Google Search Console Integration with Supabase

## 🚀 Overview

Solvia is a SaaS platform for SEO automation that provides real-time SEO audits powered by Google Search Console data. This repository contains the complete application built with FastAPI, Supabase, and Google OAuth integration.

## 🏗️ Architecture

- **Framework**: FastAPI
- **Database**: Supabase (PostgreSQL with Row Level Security)
- **Authentication**: Google OAuth2 + JWT tokens
- **SEO Data**: Google Search Console API
- **AI**: OpenAI GPT-4o-mini for intelligent insights
- **Frontend**: Static HTML/CSS/JavaScript

## 📁 Project Structure

```
solvia/
├── app/
│   ├── __init__.py
│   ├── ai/
│   │   └── agent_instructions.py    # AI agent instructions
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── models.py                # Pydantic models
│   │   ├── routes.py                # API endpoints
│   │   ├── utils.py                 # Auth utilities
│   │   └── google_oauth.py          # Google OAuth handler
│   ├── database/
│   │   ├── __init__.py
│   │   ├── supabase_client.py       # Supabase client
│   │   └── supabase_db.py           # Database operations
│   ├── static/                      # Frontend assets
│   │   ├── dashboard.html
│   │   ├── dashboard.css
│   │   ├── settings.html
│   │   ├── settings.css
│   │   ├── js/
│   │   └── images/
│   ├── config.py                    # Configuration
│   └── main.py                      # FastAPI app
├── core/
├── requirements.txt
├── setup_supabase.sql               # Database schema
├── env.example
└── README.md
```

## 🛠️ Setup Instructions

### 1. Prerequisites

- Python 3.11+
- Supabase account and project
- Google Cloud Project with OAuth2 and Search Console API enabled
- OpenAI API key

### 2. Install Dependencies

```bash
# Activate virtual environment
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Install packages
pip install -r requirements.txt
```

### 3. Supabase Setup

1. Create a Supabase project at https://supabase.com
2. Run the SQL commands from `setup_supabase.sql` in your Supabase SQL editor
3. Get your Supabase URL and anon key from the project settings

### 4. Google OAuth Setup

1. Create a Google Cloud Project
2. Enable Google OAuth2 API and Search Console API
3. Create OAuth2 credentials (Web application type)
4. Add authorized redirect URIs (e.g., `http://localhost:8000/auth/google/callback`)
5. Download the client credentials

### 5. Environment Configuration

1. Copy `env.example` to `.env`
2. Update the following variables:
   - `SUPABASE_URL`: Your Supabase project URL
   - `SUPABASE_KEY`: Your Supabase anon key
   - `GOOGLE_CLIENT_ID`: Your Google OAuth client ID
   - `GOOGLE_CLIENT_SECRET`: Your Google OAuth client secret
   - `GOOGLE_REDIRECT_URI`: Your OAuth redirect URI
   - `SECRET_KEY`: Generate a secure secret key
   - `OPENAI_API_KEY`: Your OpenAI API key

## 🚀 Running the Application

### Quick Start (Recommended)

**Windows Users:**
```bash
# Double-click or run in Command Prompt
run.bat

# Or in PowerShell
.\run.ps1
```

**Manual Setup:**
```bash
# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Install dependencies (simplified)
pip install -r requirements_simple.txt

# Run the application
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

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

- `GET /auth/google/authorize` - Generate Google OAuth URL
- `GET /auth/google/callback` - Handle OAuth callback
- `POST /auth/logout` - Logout user
- `GET /auth/me` - Get current user info

### Google Search Console

- `GET /auth/gsc/properties` - Get user's GSC properties
- `POST /auth/gsc/select-property` - Select GSC property
- `GET /auth/gsc/selected-website` - Get selected website
- `GET /auth/gsc/metrics` - Get GSC metrics with caching

### Chat/AI

- `POST /auth/chat/send` - Send chat message and get AI response
- `GET /auth/chat/history` - Get chat history

### UI Routes

- `GET /` - Root endpoint
- `GET /ui` - Main UI
- `GET /dashboard` - Dashboard
- `GET /settings` - Settings page
- `GET /health` - Health check

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SUPABASE_URL` | Supabase project URL | Required |
| `SUPABASE_KEY` | Supabase anon key | Required |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID | Required |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret | Required |
| `GOOGLE_REDIRECT_URI` | OAuth redirect URI | `http://localhost:8000/auth/google/callback` |
| `SECRET_KEY` | JWT secret key | Required |
| `OPENAI_API_KEY` | OpenAI API key | Required |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT token expiration | 30 |

## 🧪 Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=app
```

## 🔒 Security Features

- Google OAuth2 authentication
- JWT token authentication
- Row Level Security (RLS) in Supabase
- CORS protection
- Input validation with Pydantic
- Secure environment variable management

## 🚨 Important Notes

### Alpha Version Features

- Real-time Google Search Console data integration
- AI-powered SEO insights with OpenAI
- User session management with Supabase
- GSC metrics caching for performance
- Responsive web interface

### Production Considerations

- Implement proper email service (SendGrid, AWS SES)
- Add rate limiting middleware
- Implement proper logging
- Add monitoring and alerting
- Use environment-specific configurations
- Consider CDN for static assets

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
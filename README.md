# Solvia - Google OAuth Authentication

A simple and clean Google OAuth authentication system built with FastAPI and Supabase.

## Features

- ✅ **Google OAuth Login** - Sign in with your Google account
- ✅ **JWT Token Management** - Secure session handling
- ✅ **Session Storage** - Lightweight user session tracking
- ✅ **Modern UI** - Clean, responsive login and welcome pages
- ✅ **Minimal Dependencies** - Lightweight and fast

## Quick Start

### 1. Set up Environment Variables

Copy `env.example` to `.env` and configure your settings:

```bash
cp env.example .env
```

Edit `.env` with your credentials:

```env
# Google OAuth Configuration
GOOGLE_CLIENT_ID=your_google_client_id_here
GOOGLE_CLIENT_SECRET=your_google_client_secret_here
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback

# Supabase Configuration
SUPABASE_URL=your_supabase_url_here
SUPABASE_KEY=your_supabase_anon_key_here

# JWT Settings
SECRET_KEY=your-super-secret-key-change-this-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Application Settings
DEBUG=False
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Set up Google OAuth

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable the Google+ API
4. Go to "Credentials" → "Create Credentials" → "OAuth 2.0 Client IDs"
5. Set up OAuth consent screen
6. Add authorized redirect URI: `http://localhost:8000/auth/google/callback`
7. Copy Client ID and Client Secret to your `.env` file

### 4. Set up Supabase

1. Create a Supabase project at [supabase.com](https://supabase.com)
2. Create a `user_sessions` table with the following columns:
   ```sql
   CREATE TABLE user_sessions (
     id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
     email TEXT UNIQUE NOT NULL,
     name TEXT,
     picture TEXT,
     last_login TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
     is_active BOOLEAN DEFAULT TRUE,
     created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
   );
   ```
3. Copy your Supabase URL and anon key to `.env`

### 5. Run the Application

```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 6. Access the Application

- **Login Page**: http://localhost:8000/ui
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## API Endpoints

- `GET /ui` - Login page
- `GET /welcome` - Welcome page (after login)
- `GET /auth/google/authorize` - Start Google OAuth flow
- `GET /auth/google/callback` - Handle OAuth callback
- `GET /auth/me` - Get current user info
- `POST /auth/logout` - Logout user

## Project Structure

```
solvia/
├── app/
│   ├── auth/
│   │   ├── routes.py      # OAuth routes
│   │   ├── google_oauth.py # Google OAuth handler
│   │   ├── utils.py        # JWT utilities
│   │   └── models.py       # Pydantic models
│   ├── database/
│   │   └── supabase_db.py  # Session storage
│   ├── static/
│   │   ├── index.html      # Login page
│   │   └── welcome.html    # Welcome page
│   ├── config.py           # Settings
│   └── main.py            # FastAPI app
├── requirements.txt        # Dependencies
├── setup_supabase.sql     # Database setup
└── README.md             # This file
```

## Development

The application is built with:
- **FastAPI** - Modern web framework
- **Supabase** - Database and auth backend
- **Google OAuth** - Authentication provider
- **JWT** - Session management

## License

MIT License 
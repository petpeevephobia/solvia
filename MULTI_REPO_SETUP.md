# Solvia Multi-Repository Architecture

## Overview
Solvia is now split into two separate repositories for better separation of concerns:

1. **Landing Page** (Marketing Site): `https://github.com/solviasg/solvia-site.git`
2. **Dashboard/Admin** (Main App): `git@github.com:petpeevephobia/solvia.git`

## Directory Structure
```
/Users/jarotekosaputra/Documents/SOLVIA/App/
├── solvia/           # Dashboard/Admin repository
│   ├── app/          # FastAPI application
│   ├── docker-compose.multi.yml
│   ├── Caddyfile.multi
│   └── deploy-multi.sh
└── solvia-site/      # Landing page repository
    ├── index.html
    ├── product.html
    └── assets/
```

## Local Development

### Prerequisites
```bash
# Clone both repositories
cd /Users/jarotekosaputra/Documents/SOLVIA/App
git clone git@github.com:petpeevephobia/solvia.git
git clone https://github.com/solviasg/solvia-site.git
```

### Running Locally

#### Option 1: Docker (Recommended)
```bash
cd solvia
./run-multi.sh docker
```

#### Option 2: Native Python
```bash
cd solvia
./run-multi.sh native
```

### Access Points
- **Landing Page**: http://localhost/ (Docker) or http://localhost:3000 (Native)
- **Dashboard**: http://localhost/spa (Docker) or http://localhost:8000/spa (Native)
- **API Docs**: http://localhost/docs

## Production Deployment

### Server Setup
The production server runs both services using Docker Compose with Caddy as reverse proxy.

### Deploy Command
```bash
./deploy-multi.sh
```

### Production URLs
- **Landing Page**: https://solvia.sg/
- **Dashboard**: https://solvia.sg/spa
- **API**: https://solvia.sg/api/*

## Architecture Benefits

### 1. **Separation of Concerns**
- Landing page team can work independently
- Dashboard updates don't affect marketing site
- Different deployment schedules possible

### 2. **Performance**
- Landing page served by lightweight Nginx
- Static files cached aggressively
- No Python overhead for marketing content

### 3. **Security**
- Landing page has no access to API or database
- Reduced attack surface
- Separate update cycles for security patches

### 4. **Development Workflow**
- Marketing team can update landing without backend knowledge
- Backend team focuses on application logic
- Parallel development possible

## Routing Configuration

### Caddy Routes (Production)
```
/ → Landing Page (solvia-landing:80)
/product → Landing Page
/assets/* → Landing Page
/css/* → Landing Page
/js/* → Landing Page

/spa* → Dashboard (solvia-dashboard:8000)
/api/* → Dashboard
/auth/* → Dashboard
/agent/* → Dashboard
/static/* → Dashboard
/docs → Dashboard
/health → Dashboard
```

## Updating Each Repository

### Landing Page Updates
```bash
cd /Users/jarotekosaputra/Documents/SOLVIA/App/solvia-site
git pull origin main
# Make changes
git add .
git commit -m "Update landing page"
git push origin main
```

### Dashboard Updates
```bash
cd /Users/jarotekosaputra/Documents/SOLVIA/App/solvia
git pull origin main
# Make changes
git add .
git commit -m "Update dashboard"
git push origin main
```

### Deploy After Updates
```bash
cd /Users/jarotekosaputra/Documents/SOLVIA/App/solvia
./deploy-multi.sh
```

## Docker Services

### Service Names
- `solvia-caddy`: Reverse proxy
- `solvia-dashboard`: Main application
- `solvia-landing`: Landing page server
- `solvia-redis`: Cache and sessions

### Commands
```bash
# View logs
docker-compose -f docker-compose.multi.yml logs -f

# Restart services
docker-compose -f docker-compose.multi.yml restart

# Stop all services
docker-compose -f docker-compose.multi.yml down

# Rebuild and start
docker-compose -f docker-compose.multi.yml up --build -d
```

## Troubleshooting

### Landing page not showing
1. Check if solvia-site repo exists
2. Verify Nginx configuration
3. Check Caddy routing rules

### Dashboard not accessible
1. Verify .env file exists
2. Check database connection
3. Review API logs

### Deployment fails
1. Ensure SSH keys are configured
2. Check server disk space
3. Verify Docker is installed on server

## Migration from Single Repo

The migration involved:
1. ✅ Removing `/landing` route from main app
2. ✅ Deleting `app/static/landing/` directory
3. ✅ Creating multi-service Docker Compose
4. ✅ Configuring Caddy for dual routing
5. ✅ Setting up deployment scripts

## Future Improvements

- [ ] Add CI/CD pipelines for both repos
- [ ] Implement blue-green deployments
- [ ] Add monitoring and alerting
- [ ] Set up automated backups
- [ ] Configure CDN for landing page
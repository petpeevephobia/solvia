# Solvia Dashboard Guide

## Overview
The Solvia Dashboard provides real-time SEO insights by integrating with Google Search Console (GSC) and PageSpeed Insights (PSI). This guide covers setup, usage, troubleshooting, and data loading issues.

## Dashboard Features
- **SEO Score**: Overall website performance score
- **Visibility Metrics**: Impressions, clicks, CTR, average position
- **Performance Metrics**: Core Web Vitals from PageSpeed Insights
- **Keyword Analysis**: Top performing keywords and opportunities
- **Mobile Usability**: Mobile-friendly status and issues
- **Technical Health**: Indexing status and sitemap validation

## Data Loading Troubleshooting

### Common Issues and Solutions

#### 1. Data Not Loading Despite Successful API Fetches

**Symptoms:**
- API endpoints return 200 status with data
- Dashboard shows loading states or empty data
- Console shows successful data fetches but UI not updating

**Troubleshooting Steps:**

1. **Open Browser Developer Tools**
   - Press F12 or right-click > Inspect
   - Go to Console tab
   - Look for JavaScript errors

2. **Run Debug Script**
   ```javascript
   // Copy and paste this into the browser console:
   console.log('=== DASHBOARD DEBUG ===');
   console.log('Auth token:', localStorage.getItem('auth_token') ? 'Present' : 'Missing');
   console.log('Metrics data:', window.metricsData);
   
   // Test API endpoints
   const token = localStorage.getItem('auth_token');
   const headers = { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' };
   
   fetch('/auth/gsc/metrics', { headers })
     .then(r => r.json())
     .then(data => console.log('GSC Data:', data))
     .catch(e => console.error('GSC Error:', e));
   ```

3. **Check Dashboard Initialization**
   ```javascript
   // Check if dashboard functions are available
   console.log('Dashboard functions:');
   console.log('- initDashboard:', typeof window.initDashboard);
   console.log('- loadRealMetrics:', typeof window.loadRealMetrics);
   console.log('- updateDashboardMetricsWithRealData:', typeof window.updateDashboardMetricsWithRealData);
   
   // Manually trigger data loading
   if (typeof window.loadRealMetrics === 'function') {
     window.loadRealMetrics();
   }
   ```

#### 2. Authentication Issues

**Symptoms:**
- 401 Unauthorized errors
- Redirect to login page
- Missing auth token

**Solutions:**
1. Check if user is logged in: `localStorage.getItem('auth_token')`
2. If token is missing, log in again
3. Check token expiration in Network tab

#### 3. GSC Connection Issues

**Symptoms:**
- GSC banner showing when it shouldn't
- No GSC properties found
- 404 errors on GSC endpoints

**Solutions:**
1. **Re-authorize GSC Access**
   - Go to `/setup` page
   - Complete OAuth flow again
   - Select property in setup wizard

2. **Check GSC Property Selection**
   ```javascript
   // Check if property is selected
   fetch('/auth/website', { 
     headers: { 'Authorization': `Bearer ${localStorage.getItem('auth_token')}` }
   })
   .then(r => r.json())
   .then(data => console.log('Selected website:', data));
   ```

#### 4. API Response Structure Issues

**Symptoms:**
- Data fetched but dashboard shows zeros
- Console errors about missing properties
- Incorrect data types

**Solutions:**
1. **Validate API Response Structure**
   ```javascript
   // Check GSC metrics structure
   fetch('/auth/gsc/metrics', { 
     headers: { 'Authorization': `Bearer ${localStorage.getItem('auth_token')}` }
   })
   .then(r => r.json())
   .then(data => {
     console.log('Response structure check:');
     console.log('- Has summary:', !!data.summary);
     console.log('- Has time_series:', !!data.time_series);
     if (data.summary) {
       console.log('- Impressions:', data.summary.total_impressions);
       console.log('- Clicks:', data.summary.total_clicks);
       console.log('- CTR:', data.summary.avg_ctr);
       console.log('- Position:', data.summary.avg_position);
     }
   });
   ```

#### 5. DOM Element Issues

**Symptoms:**
- Console errors about missing elements
- Data updates but UI doesn't change

**Solutions:**
1. **Check Required DOM Elements**
   ```javascript
   const requiredElements = [
     'seoScore', 'impressionsValue', 'clicksValue', 
     'ctrValue', 'avgPositionValue'
   ];
   
   requiredElements.forEach(id => {
     const element = document.getElementById(id);
     console.log(`${id}:`, element ? 'Found' : 'MISSING');
   });
   ```

### Data Flow Debugging

1. **Check API Endpoints Individually**
   - `/auth/gsc/properties` - Should return array of GSC properties
   - `/auth/gsc/metrics` - Should return summary and time_series data
   - `/auth/pagespeed/metrics` - Should return PSI performance data
   - `/auth/keyword/metrics` - Should return keyword analysis

2. **Monitor Network Tab**
   - Open DevTools > Network tab
   - Refresh dashboard
   - Look for failed requests (red entries)
   - Check response data for each successful request

3. **Check Console for Errors**
   - Look for JavaScript errors
   - Check for data validation warnings
   - Monitor debug output from dashboard functions

### Manual Data Loading

If automatic loading fails, you can manually trigger data loading:

```javascript
// Manual dashboard initialization
async function manualInit() {
  try {
    console.log('Starting manual dashboard init...');
    
    // Check GSC connection
    const hasGSC = await window.checkGSCConnection();
    console.log('GSC connected:', hasGSC);
    
    if (hasGSC) {
      // Load metrics
      await window.loadRealMetrics();
      console.log('Metrics loaded successfully');
    } else {
      console.log('GSC not connected - showing empty state');
    }
  } catch (error) {
    console.error('Manual init failed:', error);
  }
}

// Run manual initialization
manualInit();
```

### Performance Monitoring

Monitor dashboard performance with these checks:

```javascript
// Performance timing
console.time('Dashboard Load Time');

// Track API response times
const apiTimes = {};
const originalFetch = window.fetch;
window.fetch = function(...args) {
  const url = args[0];
  const start = performance.now();
  
  return originalFetch.apply(this, args).then(response => {
    const duration = performance.now() - start;
    apiTimes[url] = duration;
    console.log(`API ${url}: ${duration.toFixed(2)}ms`);
    return response;
  });
};

// End timing after dashboard loads
setTimeout(() => {
  console.timeEnd('Dashboard Load Time');
  console.log('API Response Times:', apiTimes);
}, 5000);
```

### Quick Fixes

1. **Clear Browser Cache**
   - Hard refresh: Ctrl+Shift+R (Windows) or Cmd+Shift+R (Mac)
   - Clear localStorage: `localStorage.clear()`

2. **Re-authenticate**
   - Log out and log back in
   - Complete GSC setup again

3. **Check Environment Variables**
   - Ensure all API keys are configured
   - Verify Google Sheets credentials

4. **Backend Health Check**
   - Visit `/health` endpoint
   - Check server logs for errors

### Getting Additional Help

If issues persist:

1. **Collect Debug Information**
   ```javascript
   // Run complete diagnostic
   console.log('=== COMPLETE DIAGNOSTIC ===');
   console.log('User Agent:', navigator.userAgent);
   console.log('Timestamp:', new Date().toISOString());
   console.log('Auth Token:', localStorage.getItem('auth_token') ? 'Present' : 'Missing');
   console.log('Current URL:', window.location.href);
   console.log('Metrics Data:', window.metricsData);
   console.log('DOM Ready:', document.readyState);
   ```

2. **Export Dashboard State**
   ```javascript
   // Export current state for support
   const diagnosticData = {
     timestamp: new Date().toISOString(),
     userAgent: navigator.userAgent,
     url: window.location.href,
     hasAuthToken: !!localStorage.getItem('auth_token'),
     metricsData: window.metricsData,
     domReady: document.readyState
   };
   
   console.log('Diagnostic Data:', JSON.stringify(diagnosticData, null, 2));
   ```

## Contact Support

If you continue experiencing issues, please provide:
- Browser and version
- Console errors/logs
- Diagnostic data output
- Steps to reproduce the issue

## Key Features

### 1. Overall SEO Score
- **What it shows**: A comprehensive score (0-100) based on all available metrics
- **Calculation**: Weighted average of visibility, engagement, mobile usability, and indexing metrics
- **Growth indicator**: Shows change compared to exactly 30 days ago

### 2. Visibility Performance
- **Impressions**: Total search impressions from Google Search Console
- **Clicks**: Total clicks from search results
- **CTR (Click-Through Rate)**: Percentage of impressions that resulted in clicks
- **Average Position**: Average ranking position in search results
- **Growth indicators**: All compare today's data vs exactly 30 days ago

### 3. Engagement & UX
- **Performance Score**: PageSpeed Insights performance score (0-100)
- **LCP (Largest Contentful Paint)**: Time until main content loads
- **FCP (First Contentful Paint)**: Time until first content appears
- **CLS (Cumulative Layout Shift)**: Visual stability score
- **Growth indicators**: All compare current PageSpeed data vs exactly 30 days ago

### 4. Mobile Usability
- **Mobile Friendly**: Whether your site passes mobile-friendly tests
- **Issues**: Count of mobile usability issues detected
- **Growth indicators**: Show changes in mobile performance over time

### 5. Indexing & Crawlability
- **Sitemap Status**: Status of your XML sitemap in Google Search Console
- **Index Status**: Whether your pages are being indexed properly

## Growth Indicators System

All growth indicators in the dashboard now use a consistent **30-day comparison system**:

- **Green (+)**: Positive change (improvement)
- **Red (-)**: Negative change (decline)
- **Gray (0)**: No change

### How 30-Day Comparison Works

1. **GSC Metrics**: Compares today's data (minus 2 days for data delay) with exactly 30 days ago
2. **PageSpeed Metrics**: Stores current data and compares with data from 30 days ago
3. **Other Metrics**: Use fallback calculation when backend comparison isn't available

### Data Sources

The dashboard automatically detects and uses available data sources:

- **Google Search Console**: Real search performance data when connected
- **PageSpeed Insights**: Real performance data when API key is configured
- **Baseline Data**: Default values when real data isn't available

## Setup Requirements

### Google Search Console Connection
1. Click "Connect GSC" in the banner
2. Authorize Solvia to access your GSC data
3. Select the property you want to track

### PageSpeed Insights (Optional)
- Configured automatically with API key
- Provides real Core Web Vitals data

## Data Refresh

- **Manual Refresh**: Click the refresh button in the dashboard header
- **Automatic Updates**: Data refreshes when you reload the page
- **Cache**: Some data is cached for performance (cleared on manual refresh)

## Troubleshooting

### No GSC Data Showing
- Ensure your website is verified in Google Search Console
- Check that you have the correct property type (domain vs URL prefix)
- New websites may take time to accumulate search data

### Growth Indicators Show Zero
- This is normal for the first 30 days after setup
- Growth indicators need historical data to calculate changes
- After 30 days, you'll see meaningful comparisons

### Performance Data Missing
- PageSpeed data requires a valid API key
- Some websites may not have sufficient data for all metrics
- Mobile usability requires both PageSpeed and GSC data

## SEO Fixes Integration

The dashboard includes a "SEO Fixes" link in the mobile menu that provides:
- Prioritized SEO recommendations
- Action plan with implementation steps
- Business context for each recommendation
- Quick wins vs long-term improvements

## Tips for Best Results

1. **Connect GSC Early**: The sooner you connect, the more historical data you'll have
2. **Monitor Trends**: Focus on trends over time rather than single-day fluctuations
3. **Use Mobile Menu**: Access SEO Fixes for actionable recommendations
4. **Regular Monitoring**: Check dashboard weekly for consistent SEO improvement

## Technical Notes

- **Data Delay**: GSC data is typically delayed by 2-3 days
- **Comparison Logic**: All growth indicators compare single-day snapshots exactly 30 days apart
- **Storage**: Historical data is stored in Google Sheets for reliable comparisons
- **Fallbacks**: System gracefully handles missing data with appropriate defaults

## Features

### 🔐 Authentication Flow
- Users register/login through the authentication UI (`/ui`)
- Upon successful login, users are automatically redirected to the dashboard (`/dashboard`)
- The dashboard checks for valid authentication tokens
- Users can logout and return to the login page

### 📊 Dashboard Components

#### 1. Navigation Bar
- **Brand**: Solvia logo/name
- **User Info**: User avatar, email, and logout button
- **Responsive**: Adapts to mobile devices

#### 2. Performance Stats
- **SEO Score**: Overall website SEO performance (85/100)
- **Organic Traffic**: Monthly organic visitors (12.5K)
- **Keywords Ranking**: Number of ranking keywords (247)
- **Backlinks**: Total backlinks count (1,234)

#### 3. SEO Analysis
- **Page Speed**: Website loading performance
- **Mobile Optimization**: Mobile-friendliness score
- **Content Quality**: Content optimization status
- **Technical SEO**: Technical implementation score
- **User Experience**: UX optimization metrics

#### 4. Quick Actions
- **Run SEO Analysis**: Analyze website SEO performance
- **Generate Report**: Create detailed SEO reports
- **Keyword Research**: Find new keyword opportunities
- **Competitor Analysis**: Analyze competitor strategies

#### 5. Recent Activity
- **Activity Feed**: Shows recent actions and updates
- **Timestamps**: When activities occurred
- **Icons**: Visual indicators for different activity types

## Technical Implementation

### Routes
- `/ui` - Authentication interface
- `/dashboard` - Main dashboard interface
- `/api/auth/*` - Authentication API endpoints

### Authentication
- JWT tokens stored in localStorage as `auth_token`
- Automatic token validation on dashboard load
- Redirect to login if token is invalid/expired

### File Structure
```
app/
├── static/
│   ├── index.html      # Authentication UI
│   └── dashboard.html  # Dashboard interface
├── auth/
│   ├── routes.py       # Authentication endpoints
│   ├── models.py       # User models
│   └── utils.py        # Authentication utilities
└── main.py            # Main application with routes
```

## Usage Instructions

### 1. Start the Server
```bash
cd solvia
python -m app.main
```

### 2. Access the Application
- Open `http://localhost:8000/ui` in your browser
- Register a new account or login with existing credentials

### 3. Dashboard Access
- After successful login, you'll be automatically redirected to `/dashboard`
- The dashboard will display your user information and SEO metrics
- Use the quick actions to perform SEO tasks

### 4. Testing
Run the test script to verify the flow:
```bash
python test_dashboard_flow.py
```

## Customization

### Adding New Features
1. **New Quick Actions**: Add buttons to the quick actions section
2. **Additional Metrics**: Extend the stats grid with new performance indicators
3. **Custom Analysis**: Implement new SEO analysis components
4. **API Integration**: Connect to real SEO APIs for live data

### Styling
- The dashboard uses CSS Grid and Flexbox for responsive design
- Color scheme: Purple gradient (#667eea to #764ba2)
- Modern card-based layout with shadows and rounded corners
- Mobile-responsive design

### JavaScript Functions
- `checkAuth()`: Validates user authentication
- `logout()`: Handles user logout
- Action functions: Placeholder functions for future features

## Security Considerations

- JWT tokens are validated on both client and server side
- Automatic redirect to login for unauthenticated users
- Secure token storage in localStorage
- CORS configuration for API access

## Future Enhancements

1. **Real SEO Data**: Integrate with Google Search Console, Google Analytics
2. **Interactive Charts**: Add charts and graphs for data visualization
3. **Real-time Updates**: WebSocket integration for live data
4. **User Preferences**: Allow users to customize dashboard layout
5. **Advanced Analytics**: Deep dive into SEO performance metrics
6. **Automated Reports**: Scheduled report generation and email delivery

## Troubleshooting

### Common Issues
1. **Dashboard not loading**: Check if server is running and accessible
2. **Authentication errors**: Verify JWT token is valid and not expired
3. **Redirect loops**: Clear browser cache and localStorage
4. **CORS errors**: Ensure proper CORS configuration in main.py

### Debug Steps
1. Check browser console for JavaScript errors
2. Verify API endpoints are responding correctly
3. Test authentication flow with the provided test script
4. Check server logs for backend errors 
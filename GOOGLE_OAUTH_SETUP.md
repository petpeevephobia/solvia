# Google OAuth Setup for Solvia

This guide will help you set up Google OAuth to enable Google Search Console integration in Solvia.

## Prerequisites

1. A Google account
2. Access to Google Cloud Console
3. A website verified in Google Search Console

## Step 1: Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click "Select a project" → "New Project"
3. Enter a project name (e.g., "Solvia SEO")
4. Click "Create"

## Step 2: Enable Required APIs

1. In your Google Cloud project, go to "APIs & Services" → "Library"
2. Search for and enable these APIs:
   - **Google Search Console API**
   - **Google Analytics API** (optional, for future use)

## Step 3: Create OAuth 2.0 Credentials

1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "OAuth 2.0 Client IDs"
3. If prompted, configure the OAuth consent screen:
   - **User Type**: External
   - **App name**: Solvia
   - **User support email**: Your email
   - **Developer contact information**: Your email
   - **Scopes**: Add these scopes:
     - `https://www.googleapis.com/auth/webmasters.readonly`
     - `https://www.googleapis.com/auth/indexing`

4. Create the OAuth 2.0 Client ID:
   - **Application type**: Web application
   - **Name**: Solvia Web Client
   - **Authorized redirect URIs**: 
     - `http://localhost:8000/auth/google/callback` (for development)
     - `https://yourdomain.com/auth/google/callback` (for production)

5. Click "Create"
6. **Save the Client ID and Client Secret** - you'll need these for the environment variables

## Step 4: Configure Environment Variables

1. Copy `env_template.txt` to `.env`
2. Fill in your Google OAuth credentials:

```env
GOOGLE_CLIENT_ID=your_client_id_here
GOOGLE_CLIENT_SECRET=your_client_secret_here
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback
```

## Step 5: Verify Your Website in Google Search Console

1. Go to [Google Search Console](https://search.google.com/search-console)
2. Click "Add Property"
3. Enter your website URL (e.g., `https://example.com`)
4. Choose a verification method:
   - **HTML file** (recommended for beginners)
   - **HTML tag**
   - **DNS record**
   - **Google Analytics**
5. Follow the verification steps
6. Wait for Google to verify your ownership

## Step 6: Test the Integration

1. Start your Solvia application:
   ```bash
   python solvia.py
   ```

2. Register/login to your Solvia account

3. You should be redirected to the setup wizard at `/setup`

4. Click "Connect Google Search Console"

5. Grant permissions to Solvia

6. Select your website from the list

7. Your SEO data should now appear on the dashboard!

## Troubleshooting

### "No Google Search Console properties found"

**Cause**: Your website isn't verified in Google Search Console or you don't have the right permissions.

**Solution**:
1. Make sure your website is verified in Google Search Console
2. Ensure you're using the same Google account for both GSC and OAuth
3. Wait 24-48 hours after verification for data to appear

### "Failed to get authorization URL"

**Cause**: Incorrect OAuth credentials or missing environment variables.

**Solution**:
1. Check that `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are set correctly
2. Verify the redirect URI matches exactly
3. Make sure the Google Search Console API is enabled

### "Access denied" or "Invalid credentials"

**Cause**: OAuth consent screen not configured properly.

**Solution**:
1. Go to Google Cloud Console → "OAuth consent screen"
2. Add your email as a test user
3. Make sure all required scopes are added
4. Publish the app if needed

### "No data available"

**Cause**: Your website doesn't have enough data in Google Search Console.

**Solution**:
1. Wait for Google to collect data (can take 2-4 weeks for new sites)
2. Make sure your site is indexed by Google
3. Check that you have organic search traffic

## Security Considerations

1. **Never commit your `.env` file** to version control
2. **Use environment variables** in production
3. **Rotate credentials** regularly
4. **Monitor OAuth usage** in Google Cloud Console
5. **Use HTTPS** in production

## Production Deployment

For production deployment:

1. Update the redirect URI to your production domain
2. Set up proper SSL certificates
3. Use environment variables for all sensitive data
4. Consider using Google Cloud IAM for better security
5. Set up monitoring and logging

## API Quotas and Limits

Google Search Console API has the following limits:
- **Queries per day**: 2,000 requests per user per day
- **Queries per 100 seconds per user**: 5 requests
- **Queries per 100 seconds per site**: 1,200 requests

For most users, these limits are sufficient. If you need higher limits, contact Google support.

## Support

If you encounter issues:

1. Check the browser console for error messages
2. Review the server logs for detailed error information
3. Verify your Google Cloud Console configuration
4. Ensure your website is properly verified in Google Search Console

## Next Steps

Once Google OAuth is working:

1. **Real-time data**: Your dashboard will show actual SEO metrics
2. **Automated updates**: Data will refresh automatically
3. **Historical data**: Access to up to 16 months of historical data
4. **Advanced features**: Search queries, page performance, and more

Congratulations! You've successfully integrated Google Search Console with Solvia! 🎉 
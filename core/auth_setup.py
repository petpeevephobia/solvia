import os
import pickle
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# If modifying these scopes, delete the token.pickle file.
SCOPES = [
    'https://www.googleapis.com/auth/webmasters.readonly',
    'https://www.googleapis.com/auth/webmasters'
]

def get_gsc_credentials():
    """
    Gets valid user credentials from storage or initiates OAuth2 flow.
    
    Returns:
        Credentials: The obtained credentials.
    """
    creds = None
    # The file token.pickle stores the user's access and refresh tokens
    if os.path.exists('config/token.pickle'):
        with open('config/token.pickle', 'rb') as token:
            creds = pickle.load(token)
    
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save the credentials for the next run
        os.makedirs('config', exist_ok=True)
        with open('config/token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    return creds

def check_gsc_access(service):
    """
    Verifies if the service has proper access to Google Search Console.
    
    Args:
        service: The Google Search Console service object
        
    Returns:
        bool: True if access is verified, False otherwise
    """
    try:
        # Try to list sites to verify access
        service.sites().list().execute()
        return True
    except Exception as e:
        print(f"Error checking GSC access: {str(e)}")
        return False

def get_gsc_service():
    """
    Creates and returns a Google Search Console service object.
    
    Returns:
        service: The Google Search Console service object
    """
    creds = get_gsc_credentials()
    service = build('searchconsole', 'v1', credentials=creds)
    return service 
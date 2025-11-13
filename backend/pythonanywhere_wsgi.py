"""
PythonAnywhere WSGI Configuration File
Copy this entire file content to your WSGI configuration file on PythonAnywhere
(Web tab > WSGI configuration file)
"""

import os
import sys

# ============================================================================
# IMPORTANT: Replace 'YOUR_USERNAME' with your actual PythonAnywhere username
# ============================================================================
USERNAME = 'catalysts'  # Replace with your PythonAnywhere username

# Add your project directory to the sys.path
project_home = f'/home/{USERNAME}/Catalysts_Project/backend'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Set the Django settings module
os.environ['DJANGO_SETTINGS_MODULE'] = 'carb_backend.settings'

# Load environment variables from .env file
def load_env_file():
    """Load environment variables from .env file"""
    env_path = os.path.join(project_home, '.env')
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    # Only set if not already set (allows PythonAnywhere env vars to take precedence)
                    os.environ.setdefault(key.strip(), value.strip())

# Load the environment variables
load_env_file()

# Initialize Django WSGI application
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

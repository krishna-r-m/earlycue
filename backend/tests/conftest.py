import os

os.environ["DATABASE_URL"]="sqlite:///./test_marketpulse.db"
os.environ["USE_FINBERT"]="false"
os.environ["SPACY_MODEL"]="none"
os.environ["REDIS_URL"]="redis://127.0.0.1:1/0"
os.environ["GOOGLE_CLIENT_ID"]="test-client-id.apps.googleusercontent.com"
os.environ["SECRET_KEY"]="test-secret"
os.environ["QUOTE_INTERVAL_SECONDS"]="0"

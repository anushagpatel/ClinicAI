import os
from dotenv import load_dotenv
load_dotenv()
REGION = os.getenv('AWS_REGION', 'us-east-1')
MODEL = os.getenv('BEDROCK_MODEL_ID', 'amazon.nova-micro-v1:0')
BUCKET = os.getenv('S3_BUCKET', '')
PREFIX = os.getenv('DDB_PREFIX', 'ClinicalDemo')
LANGUAGE = os.getenv('TRANSCRIBE_LANGUAGE', 'en-US')

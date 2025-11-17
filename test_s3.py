"""
Test script to verify S3 bucket configuration and permissions.
Run this after setting up your S3 bucket to ensure everything works.

Usage:
    python test_s3.py
"""
import boto3
from botocore.exceptions import ClientError
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get S3 configuration from environment
bucket_name = os.getenv("S3_BUCKET_NAME")
region = os.getenv("S3_REGION")
aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")

print("=" * 60)
print("S3 Configuration Test")
print("=" * 60)

# Check if environment variables are set
if not bucket_name:
    print("❌ ERROR: S3_BUCKET_NAME not found in .env file")
    exit(1)

if not region:
    print("❌ ERROR: S3_REGION not found in .env file")
    exit(1)

print(f"✅ Bucket Name: {bucket_name}")
print(f"✅ Region: {region}")

# Initialize S3 client
if aws_access_key and aws_secret_key:
    print("✅ Using Access Keys for authentication")
    s3 = boto3.client(
        "s3",
        region_name=region,
        aws_access_key_id=aws_access_key,
        aws_secret_access_key=aws_secret_key
    )
else:
    print("✅ Using IAM Role/Default credentials")
    s3 = boto3.client("s3", region_name=region)

# Test 1: Check if bucket exists
print("\n[Test 1] Checking if bucket exists...")
try:
    s3.head_bucket(Bucket=bucket_name)
    print(f"✅ Bucket '{bucket_name}' exists and is accessible")
except ClientError as e:
    error_code = e.response['Error']['Code']
    if error_code == '404':
        print(f"❌ ERROR: Bucket '{bucket_name}' does not exist")
    elif error_code == '403':
        print(f"❌ ERROR: Access denied to bucket '{bucket_name}' (check IAM permissions)")
    else:
        print(f"❌ ERROR: {e}")
    exit(1)

# Test 2: Upload a test file
print("\n[Test 2] Testing file upload...")
test_content = b"This is a test file for S3 configuration verification."
test_key = "reports/test/test-upload.txt"

try:
    s3.put_object(
        Bucket=bucket_name,
        Key=test_key,
        Body=test_content,
        ContentType="text/plain"
    )
    print(f"✅ Upload successful! File uploaded to: {test_key}")
except ClientError as e:
    print(f"❌ ERROR: Failed to upload file: {e}")
    exit(1)

# Test 3: Generate public URL and verify format
print("\n[Test 3] Generating public URL...")
public_url = f"https://{bucket_name}.s3.{region}.amazonaws.com/{test_key}"
print(f"✅ Public URL: {public_url}")
print("   (This URL should be accessible if bucket policy is configured correctly)")

# Test 4: List objects in reports folder
print("\n[Test 4] Listing objects in 'reports/' folder...")
try:
    response = s3.list_objects_v2(Bucket=bucket_name, Prefix="reports/")
    if 'Contents' in response:
        print(f"✅ Found {len(response['Contents'])} object(s) in reports/")
        for obj in response['Contents'][:5]:  # Show first 5
            print(f"   - {obj['Key']} ({obj['Size']} bytes)")
    else:
        print("✅ Reports folder is empty (this is normal for a new setup)")
except ClientError as e:
    print(f"⚠️  Warning: Could not list objects: {e}")

# Test 5: Clean up test file
print("\n[Test 5] Cleaning up test file...")
try:
    s3.delete_object(Bucket=bucket_name, Key=test_key)
    print(f"✅ Test file deleted: {test_key}")
except ClientError as e:
    print(f"⚠️  Warning: Could not delete test file: {e}")
    print(f"   Please manually delete: {test_key} from S3 console")

# Summary
print("\n" + "=" * 60)
print("✅ S3 Configuration Test PASSED!")
print("=" * 60)
print("\nYour S3 bucket is ready to use!")
print(f"Bucket: {bucket_name}")
print(f"Region: {region}")
print("\nNext steps:")
print("1. Make sure your backend .env file has these values:")
print(f"   S3_BUCKET_NAME={bucket_name}")
print(f"   S3_REGION={region}")
print("2. Proceed with DynamoDB setup")
print("=" * 60)


# Lambda Function - Monthly Expense Reports

This folder contains the AWS Lambda function that automatically generates and emails monthly expense reports to all users.

## Files

- `lambda_ses_scheduler.py` - Main Lambda handler function

## Functionality

The Lambda function:
1. Scans all users from DynamoDB
2. Queries expenses for the current month for each user
3. Generates financial analysis using `finance_analyzer_lib`
4. Creates CSV reports and uploads them to S3
5. Logs report details to CloudWatch Logs

## Dependencies

- `finance_analyzer_lib` - Custom financial analysis library (included in this folder)
- `boto3` - AWS SDK (included in Lambda runtime)
- `botocore` - AWS SDK core (included in Lambda runtime)

## Folder Structure

All Lambda-related files are now in this folder:

```
backend/lambda/
├── lambda_ses_scheduler.py      # Lambda handler
├── finance_analyzer_lib/        # Custom library (dependency)
│   ├── __init__.py
│   └── analyzer.py
├── package.sh                    # Packaging script (Linux/Mac)
├── package.ps1                   # Packaging script (Windows)
└── README.md                     # This file
```

## Deployment

### Creating the Lambda Package

**All files needed for Lambda are in this folder!** Simply run the packaging script:

**Windows PowerShell:**
```powershell
cd backend/lambda
.\package.ps1
```

**Linux/Mac/Git Bash:**
```bash
cd backend/lambda
chmod +x package.sh
./package.sh
```

**Manual packaging (alternative):**
```bash
cd backend/lambda
zip -r ../lambda.zip lambda_ses_scheduler.py finance_analyzer_lib/
```

**The resulting zip structure:**
```
lambda.zip
├── lambda_ses_scheduler.py
└── finance_analyzer_lib/
    ├── __init__.py
    └── analyzer.py
```

### Upload to Lambda

```bash
aws lambda create-function \
  --function-name smart-expense-monthly-reports \
  --runtime python3.11 \
  --role <iam-role-arn> \
  --handler lambda_ses_scheduler.lambda_handler \
  --zip-file fileb://lambda.zip \
  --timeout 120 \
  --memory-size 256
```

## Environment Variables

The Lambda function requires these environment variables:

- `DYNAMO_REGION` - AWS region for DynamoDB
- `DYNAMO_TABLE_USERS` - DynamoDB users table name
- `DYNAMO_TABLE_EXPENSES` - DynamoDB expenses table name
- `S3_BUCKET_NAME` - S3 bucket for storing reports
- `S3_REGION` - AWS region for S3

## Scheduling

The function is triggered monthly via CloudWatch Events (EventBridge) with the schedule:
- Cron: `cron(0 6 1 * ? *)` (runs at 6 AM on the 1st of every month)

## IAM Permissions Required

The Lambda execution role needs:
- `dynamodb:Query` and `dynamodb:Scan` on users and expenses tables
- `s3:PutObject` on the reports bucket
- `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents` for CloudWatch Logs

## Testing

Test the Lambda function locally or via AWS Console:

```bash
aws lambda invoke \
  --function-name smart-expense-monthly-reports \
  --payload '{}' \
  response.json
```


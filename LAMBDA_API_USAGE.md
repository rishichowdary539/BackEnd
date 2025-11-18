# Lambda Function API Gateway Usage

## Overview

The Lambda function for monthly expense reports is exposed via AWS API Gateway, allowing you to trigger it directly using an HTTP POST request.

## API Gateway Endpoint Structure

After deployment via Jenkins pipeline, the API Gateway endpoint will be:

```
https://{API_ID}.execute-api.{REGION}.amazonaws.com/prod/lambda/reports
```

**Example:**
```
https://uunr59c9a3.execute-api.eu-west-1.amazonaws.com/prod/lambda/reports
```

## How to Get Your API Gateway URL

### Method 1: AWS Console
1. Go to AWS API Gateway Console
2. Find your API: `smart-expense-api` (or `smart-expense-monthly-reports-api`)
3. Click on the API → Stages → `prod`
4. Copy the **Invoke URL**
5. Append `/lambda/reports` to the URL

### Method 2: AWS CLI
```bash
# Get API ID
aws apigateway get-rest-apis --region eu-west-1 --query "items[?name=='smart-expense-api'].id" --output text

# Construct URL (replace {API_ID} with the output above)
# https://{API_ID}.execute-api.eu-west-1.amazonaws.com/prod/lambda/reports
```

### Method 3: Jenkins Pipeline Output
The Jenkins pipeline prints the final API Gateway URL in the post-build success message.

## Making API Calls

### Using cURL

```bash
# Basic POST request
curl -X POST \
  https://{API_ID}.execute-api.eu-west-1.amazonaws.com/prod/lambda/reports \
  -H "Content-Type: application/json" \
  -d '{}'
```

### Using Python (requests)

```python
import requests

api_url = "https://{API_ID}.execute-api.eu-west-1.amazonaws.com/prod/lambda/reports"

response = requests.post(api_url, json={})
print(response.json())
```

### Using JavaScript (fetch)

```javascript
const apiUrl = 'https://{API_ID}.execute-api.eu-west-1.amazonaws.com/prod/lambda/reports';

fetch(apiUrl, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({})
})
.then(response => response.json())
.then(data => console.log(data))
.catch(error => console.error('Error:', error));
```

## Response Format

### Success Response (200)

```json
{
  "statusCode": 200,
  "body": "{\"status\":\"success\",\"month\":\"2025-11\",\"users_processed\":5,\"total_users\":5,\"results\":[...]}"
}
```

**Parsed body:**
```json
{
  "status": "success",
  "month": "2025-11",
  "users_processed": 5,
  "total_users": 5,
  "results": [
    {
      "user_id": "user123",
      "email": "user@example.com",
      "total_spent": 1500.50,
      "report_url": "https://smart-expense-reports-2025.s3.eu-west-1.amazonaws.com/reports/user123/user123_2025-11_abc123.csv"
    }
  ]
}
```

### Error Response (500)

```json
{
  "statusCode": 500,
  "body": "{\"status\":\"error\",\"message\":\"Error description\"}"
}
```

## Integration with Backend

The FastAPI backend also provides endpoints to trigger the Lambda function:

### Via Backend API (Recommended for internal use)

```
POST /api/lambda/trigger
```

This endpoint:
- Invokes the Lambda function via AWS SDK (boto3)
- Returns a formatted response
- Handles errors gracefully
- Requires backend to have AWS credentials configured

### Direct API Gateway (Recommended for external triggers)

```
POST https://{API_ID}.execute-api.eu-west-1.amazonaws.com/prod/lambda/reports
```

This endpoint:
- Directly invokes Lambda via API Gateway
- No backend dependency
- Can be called from anywhere (webhooks, external services, etc.)
- Requires API Gateway to have proper permissions

## Authentication & Security

Currently, the API Gateway endpoint is configured with:
- **Authorization**: NONE (public endpoint)
- **CORS**: Not configured (may need to add if calling from browser)

**For production, consider:**
1. Adding API Key authentication
2. Adding IAM authentication
3. Adding CORS configuration
4. Adding rate limiting

## Monthly Cron Job

The backend also automatically triggers this Lambda function monthly via APScheduler:
- **Default schedule**: 1st of month at 6:00 AM UTC
- **Configurable**: Set `MONTHLY_REPORTS_CRON` environment variable
- **Format**: `"day hour minute"` (e.g., `"1 6 0"`)

The cron job uses the backend's `/api/lambda/trigger` endpoint internally.

## Troubleshooting

### 403 Forbidden
- Check API Gateway permissions
- Verify Lambda function has permission for API Gateway to invoke it

### 500 Internal Server Error
- Check CloudWatch logs for Lambda function
- Verify DynamoDB tables exist and are accessible
- Verify S3 bucket exists and Lambda has write permissions

### 404 Not Found
- Verify the API Gateway endpoint path: `/lambda/reports`
- Check that the API is deployed to `prod` stage
- Verify API Gateway deployment was successful

## Example: Complete Workflow

1. **Deploy via Jenkins** → Creates API Gateway endpoint
2. **Get API URL** → From Jenkins output or AWS Console
3. **Test manually** → `curl -X POST {API_URL}`
4. **Set up monitoring** → CloudWatch alarms for Lambda errors
5. **Configure cron** → Backend scheduler triggers monthly automatically


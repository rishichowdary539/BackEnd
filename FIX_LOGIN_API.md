# Fix Login API - Add Form Data Support

## Problem
Login API requires `application/x-www-form-urlencoded` but API Gateway integration doesn't handle it.

## Quick Fix

### Step 0: Set Variables

```bash
REGION="eu-west-1"
API_NAME="smart-expense-monthly-reports-api"
EC2_IP="34.248.251.253"
EC2_PORT="8000"
```

### Step 1: Get IDs

```bash
API_ID=$(aws apigateway get-rest-apis --region $REGION --query "items[?name=='${API_NAME}'].id" --output text)
PROXY_RESOURCE_ID=$(aws apigateway get-resources --rest-api-id $API_ID --region $REGION --query 'items[?path==`/api/{proxy+}`].id' --output text)

echo "API ID: $API_ID"
echo "Proxy Resource ID: $PROXY_RESOURCE_ID"
```

### Step 2: Update Integration to Support Form Data

```bash
aws apigateway put-integration \
  --rest-api-id $API_ID \
  --resource-id $PROXY_RESOURCE_ID \
  --http-method ANY \
  --type HTTP \
  --integration-http-method ANY \
  --uri "http://${EC2_IP}:${EC2_PORT}/api/{proxy}" \
  --region $REGION \
  --request-parameters '{"integration.request.path.proxy": "method.request.path.proxy"}' \
  --request-templates '{"application/json": "$input.json()", "application/x-www-form-urlencoded": "$input.body"}' \
  --passthrough-behavior WHEN_NO_MATCH \
  --content-handling CONVERT_TO_TEXT
```

### Step 3: Deploy

```bash
aws apigateway create-deployment \
  --rest-api-id $API_ID \
  --stage-name prod \
  --region $REGION \
  --description "Fixed: Added form data support for login API"
```

---

## What Changed

Added `"application/x-www-form-urlencoded": "$input.body"` to request templates so form data is passed through correctly.

---

## Test

```bash
curl -X POST \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test@example.com&password=test123" \
  "https://${API_ID}.execute-api.${REGION}.amazonaws.com/prod/api/auth/login"
```

Should return: `{"access_token": "...", "token_type": "bearer"}`


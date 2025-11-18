# Troubleshooting Login API

## Issue
Login API is not working after API Gateway proxy recreation.

## Login Endpoint Details

- **Path:** `/api/auth/login`
- **Method:** POST
- **Content-Type:** `application/x-www-form-urlencoded` (required for OAuth2)
- **Body:** `username=email&password=password`

---

## Quick Checks

### 1. Test Direct EC2 Backend

```bash
curl -X POST \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=your@email.com&password=yourpassword" \
  http://34.248.251.253:8000/api/auth/login
```

**Expected:** Should return `{"access_token": "...", "token_type": "bearer"}`

If this works, the backend is fine - issue is with API Gateway.

---

### 2. Test API Gateway Endpoint

```bash
curl -X POST \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=your@email.com&password=yourpassword" \
  https://YOUR_API_ID.execute-api.eu-west-1.amazonaws.com/prod/api/auth/login
```

**Check:** Does it return 200 or an error?

---

## Common Issues

### Issue 1: Content-Type Not Preserved

The HTTP integration might not be preserving the `Content-Type` header for form data.

**Fix:** Update integration to handle form data:

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
  --request-templates '{
    "application/json": "$input.json()",
    "application/x-www-form-urlencoded": "$input.body"
  }' \
  --passthrough-behavior WHEN_NO_MATCH \
  --content-handling CONVERT_TO_TEXT
```

Then deploy:
```bash
aws apigateway create-deployment \
  --rest-api-id $API_ID \
  --stage-name prod \
  --region $REGION \
  --description "Fixed: Added form data support"
```

---

### Issue 2: Check API Gateway Logs

Enable CloudWatch logs to see what's happening:

```bash
# Get the API Gateway account ID (for log group)
aws apigateway get-account --region $REGION

# Check CloudWatch logs
aws logs tail /aws/apigateway/YOUR_API_ID --follow --region $REGION
```

---

### Issue 3: Verify Integration Configuration

Check current integration:

```bash
aws apigateway get-integration \
  --rest-api-id $API_ID \
  --resource-id $PROXY_RESOURCE_ID \
  --http-method ANY \
  --region $REGION
```

**Check:**
- `type` should be `HTTP` (not `HTTP_PROXY`)
- `uri` should point to EC2: `http://34.248.251.253:8000/api/{proxy}`
- `passthroughBehavior` should be `WHEN_NO_MATCH`

---

## Quick Fix: Update Integration for Form Data

Run these commands to ensure form data is handled:

```bash
# Set variables
REGION="eu-west-1"
API_NAME="smart-expense-monthly-reports-api"
EC2_IP="34.248.251.253"
EC2_PORT="8000"

# Get IDs
API_ID=$(aws apigateway get-rest-apis --region $REGION --query "items[?name=='${API_NAME}'].id" --output text)
PROXY_RESOURCE_ID=$(aws apigateway get-resources --rest-api-id $API_ID --region $REGION --query 'items[?path==`/api/{proxy+}`].id' --output text)

# Update integration with form data support
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

# Deploy
aws apigateway create-deployment \
  --rest-api-id $API_ID \
  --stage-name prod \
  --region $REGION \
  --description "Fixed: Added form data support for login"
```

---

## Test After Fix

```bash
curl -X POST \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test@example.com&password=test123" \
  "https://${API_ID}.execute-api.${REGION}.amazonaws.com/prod/api/auth/login"
```

**Expected:** `{"access_token": "...", "token_type": "bearer"}`

---

## Debug Steps

1. **Check if backend is running:**
   ```bash
   curl http://34.248.251.253:8000/api/health
   ```

2. **Check API Gateway integration:**
   ```bash
   aws apigateway get-integration --rest-api-id $API_ID --resource-id $PROXY_RESOURCE_ID --http-method ANY --region $REGION
   ```

3. **Check browser console** for error messages

4. **Check Network tab** in browser DevTools to see:
   - Request URL
   - Request headers
   - Response status
   - Response body

---

## Notes

- Login endpoint requires `application/x-www-form-urlencoded` content type
- OAuth2PasswordRequestForm expects `username` and `password` form fields
- Frontend sends email as `username` field (correct)
- API Gateway must preserve Content-Type header


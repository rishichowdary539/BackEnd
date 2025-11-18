# API Gateway Fix: HTTP_PROXY to HTTP Integration

## Problem
API Gateway is using `HTTP_PROXY` which causes 307 redirects. Browsers don't preserve Authorization headers in redirects, causing 401 errors.

## Solution
Change integration type from `HTTP_PROXY` to `HTTP` to forward requests directly without redirects.

---

## Step-by-Step Commands

### Step 0: Set Variables (Run This First!)

**For PowerShell:**
```powershell
$REGION = "eu-west-1"
$API_NAME = "smart-expense-monthly-reports-api"
$EC2_IP = "34.248.251.253"
$EC2_PORT = "8000"
```

**For Bash/Linux/Mac:**
```bash
export REGION="eu-west-1"
export API_NAME="smart-expense-monthly-reports-api"
export EC2_IP="34.248.251.253"
export EC2_PORT="8000"
```

---

### Step 1: Get API Gateway ID

**PowerShell:**
```powershell
$API_ID = aws apigateway get-rest-apis --region $REGION --query "items[?name=='${API_NAME}'].id" --output text
Write-Host "API ID: $API_ID"
```

**Bash:**
```bash
API_ID=$(aws apigateway get-rest-apis --region $REGION --query "items[?name=='${API_NAME}'].id" --output text)
echo "API ID: $API_ID"
```

**Save the output** - This is your `API_ID` (e.g., `uunr59c9a3`)

---

### Step 2: Get /api/{proxy+} Resource ID

**PowerShell:**
```powershell
$PROXY_RESOURCE_ID = aws apigateway get-resources --rest-api-id $API_ID --region $REGION --query 'items[?path==`/api/{proxy+}`].id' --output text
Write-Host "Proxy Resource ID: $PROXY_RESOURCE_ID"
```

**Bash:**
```bash
PROXY_RESOURCE_ID=$(aws apigateway get-resources --rest-api-id $API_ID --region $REGION --query 'items[?path==`/api/{proxy+}`].id' --output text)
echo "Proxy Resource ID: $PROXY_RESOURCE_ID"
```

**Save the output** - This is your `PROXY_RESOURCE_ID`

---

### Step 3: Update Integration from HTTP_PROXY to HTTP

**PowerShell:**
```powershell
aws apigateway put-integration `
  --rest-api-id $API_ID `
  --resource-id $PROXY_RESOURCE_ID `
  --http-method ANY `
  --type HTTP `
  --integration-http-method ANY `
  --uri "http://${EC2_IP}:${EC2_PORT}/api/{proxy}" `
  --region $REGION `
  --request-parameters '{\"integration.request.path.proxy\": \"method.request.path.proxy\"}' `
  --request-templates '{\"application/json\": \"$input.json()\"}' `
  --passthrough-behavior WHEN_NO_MATCH `
  --content-handling CONVERT_TO_TEXT
```

**Bash:**
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
  --request-templates '{"application/json": "$input.json()"}' \
  --passthrough-behavior WHEN_NO_MATCH \
  --content-handling CONVERT_TO_TEXT
```

**Expected output:** JSON response with integration details

---

### Step 4: Update Integration Response

**PowerShell:**
```powershell
aws apigateway put-integration-response `
  --rest-api-id $API_ID `
  --resource-id $PROXY_RESOURCE_ID `
  --http-method ANY `
  --status-code 200 `
  --region $REGION `
  --response-templates '{\"application/json\": \"$input.json()\"}' `
  --response-parameters '{\"method.response.header.Access-Control-Allow-Origin\": \"'\''*'\''\"}'
```

**Bash:**
```bash
aws apigateway put-integration-response \
  --rest-api-id $API_ID \
  --resource-id $PROXY_RESOURCE_ID \
  --http-method ANY \
  --status-code 200 \
  --region $REGION \
  --response-templates '{"application/json": "$input.json()"}' \
  --response-parameters '{"method.response.header.Access-Control-Allow-Origin": "'\''*'\''"}'
```

**Expected output:** JSON response with integration response details

---

### Step 5: Update Method Response

**PowerShell:**
```powershell
aws apigateway put-method-response `
  --rest-api-id $API_ID `
  --resource-id $PROXY_RESOURCE_ID `
  --http-method ANY `
  --status-code 200 `
  --region $REGION `
  --response-parameters '{\"method.response.header.Access-Control-Allow-Origin\": true}'
```

**Bash:**
```bash
aws apigateway put-method-response \
  --rest-api-id $API_ID \
  --resource-id $PROXY_RESOURCE_ID \
  --http-method ANY \
  --status-code 200 \
  --region $REGION \
  --response-parameters '{"method.response.header.Access-Control-Allow-Origin": true}'
```

**Expected output:** JSON response with method response details

---

### Step 6: Deploy API Gateway

**PowerShell:**
```powershell
aws apigateway create-deployment `
  --rest-api-id $API_ID `
  --stage-name prod `
  --region $REGION `
  --description "Fixed: Changed HTTP_PROXY to HTTP integration"
```

**Bash:**
```bash
aws apigateway create-deployment \
  --rest-api-id $API_ID \
  --stage-name prod \
  --region $REGION \
  --description "Fixed: Changed HTTP_PROXY to HTTP integration"
```

**Expected output:** JSON response with deployment details

---

## Verification

### Test the API Gateway endpoint:

**PowerShell:**
```powershell
curl -X POST `
  -H "Authorization: Bearer YOUR_TOKEN" `
  -H "Content-Type: application/json" `
  -d '{\"category\":\"Food\",\"amount\":100,\"description\":\"Test\"}' `
  "https://${API_ID}.execute-api.${REGION}.amazonaws.com/prod/api/expenses/"
```

**Bash:**
```bash
curl -X POST \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"category":"Food","amount":100,"description":"Test"}' \
  "https://${API_ID}.execute-api.${REGION}.amazonaws.com/prod/api/expenses/"
```

**Expected:** Should return 200 OK (not 307 redirect)

---

## What Changed

- **Before:** `--type HTTP_PROXY` → Causes 307 redirects
- **After:** `--type HTTP` → Forwards requests directly

**Result:** Authorization headers are now preserved, no more 401 errors!

---

## Troubleshooting

If you get errors:

1. **"Resource not found"** → Check API ID and Resource ID are correct
2. **"Method not found"** → Run Step 5 first, then Step 3
3. **"Permission denied"** → Check AWS credentials and IAM permissions
4. **"Invalid integration"** → Verify EC2 IP and port are correct

---

## Notes

- The change takes effect immediately after deployment
- No downtime required
- All existing routes will continue to work
- Authorization headers will now be preserved


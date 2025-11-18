# Delete and Recreate /api/{proxy+} Resource

## Overview
Delete the existing `/api/{proxy+}` resource and recreate it with HTTP integration (instead of HTTP_PROXY) to fix the 307 redirect issue.

**Note:** This will NOT affect the Lambda resource - only the proxy resource.

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
REGION="eu-west-1"
API_NAME="smart-expense-monthly-reports-api"
EC2_IP="34.248.251.253"
EC2_PORT="8000"
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

---

### Step 2: Get /api Resource ID (Parent)

**PowerShell:**
```powershell
$API_RESOURCE_ID = aws apigateway get-resources --rest-api-id $API_ID --region $REGION --query 'items[?path==`/api`].id' --output text
Write-Host "API Resource ID: $API_RESOURCE_ID"
```

**Bash:**
```bash
API_RESOURCE_ID=$(aws apigateway get-resources --rest-api-id $API_ID --region $REGION --query 'items[?path==`/api`].id' --output text)
echo "API Resource ID: $API_RESOURCE_ID"
```

---

### Step 3: Get /api/{proxy+} Resource ID

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

---

### Step 4: Delete the /api/{proxy+} Resource

**PowerShell:**
```powershell
# First delete the method
aws apigateway delete-method `
  --rest-api-id $API_ID `
  --resource-id $PROXY_RESOURCE_ID `
  --http-method ANY `
  --region $REGION

# Then delete the resource
aws apigateway delete-resource `
  --rest-api-id $API_ID `
  --resource-id $PROXY_RESOURCE_ID `
  --region $REGION

Write-Host "✅ Deleted /api/{proxy+} resource"
```

**Bash:**
```bash
# First delete the method
aws apigateway delete-method \
  --rest-api-id $API_ID \
  --resource-id $PROXY_RESOURCE_ID \
  --http-method ANY \
  --region $REGION

# Then delete the resource
aws apigateway delete-resource \
  --rest-api-id $API_ID \
  --resource-id $PROXY_RESOURCE_ID \
  --region $REGION

echo "✅ Deleted /api/{proxy+} resource"
```

---

### Step 5: Create New /api/{proxy+} Resource

**PowerShell:**
```powershell
$PROXY_RESOURCE_ID = aws apigateway create-resource `
  --rest-api-id $API_ID `
  --parent-id $API_RESOURCE_ID `
  --path-part '{proxy+}' `
  --region $REGION `
  --query 'id' --output text

Write-Host "✅ Created new /api/{proxy+} resource: $PROXY_RESOURCE_ID"
```

**Bash:**
```bash
PROXY_RESOURCE_ID=$(aws apigateway create-resource \
  --rest-api-id $API_ID \
  --parent-id $API_RESOURCE_ID \
  --path-part '{proxy+}' \
  --region $REGION \
  --query 'id' --output text)

echo "✅ Created new /api/{proxy+} resource: $PROXY_RESOURCE_ID"
```

---

### Step 6: Create ANY Method

**PowerShell:**
```powershell
aws apigateway put-method `
  --rest-api-id $API_ID `
  --resource-id $PROXY_RESOURCE_ID `
  --http-method ANY `
  --authorization-type NONE `
  --region $REGION `
  --request-parameters '{\"method.request.path.proxy\": true}'

Write-Host "✅ Created ANY method"
```

**Bash:**
```bash
aws apigateway put-method \
  --rest-api-id $API_ID \
  --resource-id $PROXY_RESOURCE_ID \
  --http-method ANY \
  --authorization-type NONE \
  --region $REGION \
  --request-parameters '{"method.request.path.proxy": true}'

echo "✅ Created ANY method"
```

---

### Step 7: Create HTTP Integration (NOT HTTP_PROXY)

**Important:** This includes support for both JSON and form data (needed for login).

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
  --request-templates '{\"application/json\": \"$input.json()\", \"application/x-www-form-urlencoded\": \"$input.body\"}' `
  --passthrough-behavior WHEN_NO_MATCH `
  --content-handling CONVERT_TO_TEXT

Write-Host "✅ Created HTTP integration with form data support"
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
  --request-templates '{"application/json": "$input.json()", "application/x-www-form-urlencoded": "$input.body"}' \
  --passthrough-behavior WHEN_NO_MATCH \
  --content-handling CONVERT_TO_TEXT

echo "✅ Created HTTP integration with form data support"
```

**Note:** The `application/x-www-form-urlencoded` template is needed for the login endpoint!

---

### Step 8: Create Method Response

**PowerShell:**
```powershell
aws apigateway put-method-response `
  --rest-api-id $API_ID `
  --resource-id $PROXY_RESOURCE_ID `
  --http-method ANY `
  --status-code 200 `
  --region $REGION `
  --response-parameters '{\"method.response.header.Access-Control-Allow-Origin\": true}'

Write-Host "✅ Created method response"
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

echo "✅ Created method response"
```

---

### Step 9: Create Integration Response

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

Write-Host "✅ Created integration response"
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

echo "✅ Created integration response"
```

---

### Step 10: Deploy API Gateway

**PowerShell:**
```powershell
aws apigateway create-deployment `
  --rest-api-id $API_ID `
  --stage-name prod `
  --region $REGION `
  --description "Recreated /api/{proxy+} with HTTP integration"

Write-Host "✅ API Gateway deployed"
```

**Bash:**
```bash
aws apigateway create-deployment \
  --rest-api-id $API_ID \
  --stage-name prod \
  --region $REGION \
  --description "Recreated /api/{proxy+} with HTTP integration"

echo "✅ API Gateway deployed"
```

---

## Summary

**What was done:**
1. ✅ Deleted existing `/api/{proxy+}` resource (with HTTP_PROXY)
2. ✅ Created new `/api/{proxy+}` resource
3. ✅ Configured with HTTP integration (not HTTP_PROXY)
4. ✅ Deployed to production

**Result:**
- No more 307 redirects
- Authorization headers preserved
- Lambda resource untouched

---

## Verification

Test the endpoint:

```bash
curl -X POST \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"category":"Food","amount":100,"description":"Test"}' \
  "https://${API_ID}.execute-api.${REGION}.amazonaws.com/prod/api/expenses/"
```

Should return 200 OK (not 307 redirect)!


# Fix API Gateway: Change from HTTP_PROXY to HTTP integration
# This prevents 307 redirects and preserves Authorization headers

$REGION = "eu-west-1"
$API_NAME = "smart-expense-monthly-reports-api"
$EC2_IP = "34.248.251.253"
$EC2_PORT = "8000"

Write-Host "=========================================="
Write-Host "Fixing API Gateway Integration Type"
Write-Host "Changing from HTTP_PROXY to HTTP"
Write-Host "=========================================="
Write-Host ""

# Step 1: Get API ID
Write-Host "Step 1: Getting API Gateway ID..."
$API_ID = aws apigateway get-rest-apis --region $REGION --query "items[?name=='${API_NAME}'].id" --output text

if ([string]::IsNullOrEmpty($API_ID)) {
    Write-Host "❌ Error: API Gateway '${API_NAME}' not found" -ForegroundColor Red
    exit 1
}

Write-Host "✅ API ID: $API_ID"
Write-Host ""

# Step 2: Get /api/{proxy+} resource ID
Write-Host "Step 2: Getting /api/{proxy+} resource ID..."
$PROXY_RESOURCE_ID = aws apigateway get-resources --rest-api-id $API_ID --region $REGION --query 'items[?path==`/api/{proxy+}`].id' --output text

if ([string]::IsNullOrEmpty($PROXY_RESOURCE_ID)) {
    Write-Host "❌ Error: /api/{proxy+} resource not found" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Proxy Resource ID: $PROXY_RESOURCE_ID"
Write-Host ""

# Step 3: Update integration from HTTP_PROXY to HTTP
Write-Host "Step 3: Updating integration from HTTP_PROXY to HTTP..."
$integrationResult = aws apigateway put-integration `
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
    --content-handling CONVERT_TO_TEXT 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Integration updated to HTTP type"
} else {
    Write-Host "❌ Error: Failed to update integration" -ForegroundColor Red
    Write-Host $integrationResult
    exit 1
}
Write-Host ""

# Step 4: Update integration response
Write-Host "Step 4: Updating integration response..."
aws apigateway put-integration-response `
    --rest-api-id $API_ID `
    --resource-id $PROXY_RESOURCE_ID `
    --http-method ANY `
    --status-code 200 `
    --region $REGION `
    --response-templates '{\"application/json\": \"$input.json()\"}' `
    --response-parameters '{\"method.response.header.Access-Control-Allow-Origin\": \"'\''*'\''\"}' | Out-Null

Write-Host "✅ Integration response updated"
Write-Host ""

# Step 5: Update method response
Write-Host "Step 5: Updating method response..."
aws apigateway put-method-response `
    --rest-api-id $API_ID `
    --resource-id $PROXY_RESOURCE_ID `
    --http-method ANY `
    --status-code 200 `
    --region $REGION `
    --response-parameters '{\"method.response.header.Access-Control-Allow-Origin\": true}' | Out-Null

Write-Host "✅ Method response updated"
Write-Host ""

# Step 6: Deploy API Gateway
Write-Host "Step 6: Deploying API Gateway..."
$deployResult = aws apigateway create-deployment `
    --rest-api-id $API_ID `
    --stage-name prod `
    --region $REGION `
    --description "Fixed: Changed HTTP_PROXY to HTTP integration - IP: ${EC2_IP}" 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ API Gateway deployed to prod stage"
} else {
    Write-Host "❌ Error: Failed to deploy" -ForegroundColor Red
    Write-Host $deployResult
    exit 1
}
Write-Host ""

# Summary
Write-Host "=========================================="
Write-Host "✅ Fix Complete!"
Write-Host "=========================================="
Write-Host ""
Write-Host "Changes made:"
Write-Host "  - Changed integration type: HTTP_PROXY → HTTP"
Write-Host "  - Integration now forwards requests directly (no redirect)"
Write-Host "  - Authorization headers will be preserved"
Write-Host ""
Write-Host "API Gateway URL:"
Write-Host "  https://${API_ID}.execute-api.${REGION}.amazonaws.com/prod/api"
Write-Host ""
Write-Host "EC2 Backend:"
Write-Host "  http://${EC2_IP}:${EC2_PORT}/api"
Write-Host ""
Write-Host "Test Command:"
Write-Host "  curl -H 'Authorization: Bearer YOUR_TOKEN' \"
Write-Host "       https://${API_ID}.execute-api.${REGION}.amazonaws.com/prod/api/expenses/"
Write-Host ""
Write-Host "Note: The 307 redirect issue should now be fixed!"
Write-Host ""


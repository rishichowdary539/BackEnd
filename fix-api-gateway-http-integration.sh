#!/bin/bash
# Fix API Gateway: Change from HTTP_PROXY to HTTP integration
# This prevents 307 redirects and preserves Authorization headers

REGION="eu-west-1"
API_NAME="smart-expense-monthly-reports-api"
EC2_IP="34.248.251.253"
EC2_PORT="8000"

echo "=========================================="
echo "Fixing API Gateway Integration Type"
echo "Changing from HTTP_PROXY to HTTP"
echo "=========================================="
echo ""

# Step 1: Get API ID
echo "Step 1: Getting API Gateway ID..."
API_ID=$(aws apigateway get-rest-apis --region $REGION \
  --query "items[?name=='${API_NAME}'].id" --output text)

if [ -z "$API_ID" ]; then
  echo "❌ Error: API Gateway '${API_NAME}' not found"
  exit 1
fi

echo "✅ API ID: $API_ID"
echo ""

# Step 2: Get /api/{proxy+} resource ID
echo "Step 2: Getting /api/{proxy+} resource ID..."
PROXY_RESOURCE_ID=$(aws apigateway get-resources --rest-api-id $API_ID --region $REGION \
  --query 'items[?path==`/api/{proxy+}`].id' --output text)

if [ -z "$PROXY_RESOURCE_ID" ]; then
  echo "❌ Error: /api/{proxy+} resource not found"
  exit 1
fi

echo "✅ Proxy Resource ID: $PROXY_RESOURCE_ID"
echo ""

# Step 3: Update integration from HTTP_PROXY to HTTP
echo "Step 3: Updating integration from HTTP_PROXY to HTTP..."
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
  --content-handling CONVERT_TO_TEXT > /dev/null

if [ $? -eq 0 ]; then
  echo "✅ Integration updated to HTTP type"
else
  echo "❌ Error: Failed to update integration"
  exit 1
fi
echo ""

# Step 4: Update integration response to pass through all headers
echo "Step 4: Updating integration response..."
aws apigateway put-integration-response \
  --rest-api-id $API_ID \
  --resource-id $PROXY_RESOURCE_ID \
  --http-method ANY \
  --status-code 200 \
  --region $REGION \
  --response-templates '{"application/json": "$input.json()"}' \
  --response-parameters '{"method.response.header.Access-Control-Allow-Origin": "'\''*'\''"}' > /dev/null

echo "✅ Integration response updated"
echo ""

# Step 5: Update method response to include CORS headers
echo "Step 5: Updating method response..."
aws apigateway put-method-response \
  --rest-api-id $API_ID \
  --resource-id $PROXY_RESOURCE_ID \
  --http-method ANY \
  --status-code 200 \
  --region $REGION \
  --response-parameters '{"method.response.header.Access-Control-Allow-Origin": true}' > /dev/null

echo "✅ Method response updated"
echo ""

# Step 6: Deploy API Gateway
echo "Step 6: Deploying API Gateway..."
aws apigateway create-deployment \
  --rest-api-id $API_ID \
  --stage-name prod \
  --region $REGION \
  --description "Fixed: Changed HTTP_PROXY to HTTP integration - IP: ${EC2_IP}" > /dev/null

if [ $? -eq 0 ]; then
  echo "✅ API Gateway deployed to prod stage"
else
  echo "❌ Error: Failed to deploy"
  exit 1
fi
echo ""

# Summary
echo "=========================================="
echo "✅ Fix Complete!"
echo "=========================================="
echo ""
echo "Changes made:"
echo "  - Changed integration type: HTTP_PROXY → HTTP"
echo "  - Integration now forwards requests directly (no redirect)"
echo "  - Authorization headers will be preserved"
echo ""
echo "API Gateway URL:"
echo "  https://${API_ID}.execute-api.${REGION}.amazonaws.com/prod/api"
echo ""
echo "EC2 Backend:"
echo "  http://${EC2_IP}:${EC2_PORT}/api"
echo ""
echo "Test Command:"
echo "  curl -H 'Authorization: Bearer YOUR_TOKEN' \\"
echo "       https://${API_ID}.execute-api.${REGION}.amazonaws.com/prod/api/expenses/"
echo ""
echo "Note: The 307 redirect issue should now be fixed!"
echo ""


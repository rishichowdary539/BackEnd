#!/bin/bash
# Step-by-step cleanup and setup - deletes proxy and health, keeps Lambda

REGION="eu-west-1"
API_NAME="smart-expense-monthly-reports-api"
NEW_IP="34.248.251.253"
EC2_PORT="8000"

echo "=========================================="
echo "Step-by-Step Cleanup and Setup"
echo "=========================================="
echo ""

# Step 1: Get API ID
echo "Step 1: Getting API ID..."
API_ID=$(aws apigateway get-rest-apis --region $REGION \
  --query "items[?name=='${API_NAME}'].id" --output text)

if [ -z "$API_ID" ]; then
  echo "❌ Error: API Gateway not found"
  exit 1
fi

echo "✅ API ID: $API_ID"
echo ""
read -p "Press Enter to continue..."
echo ""

# Step 2: Get all resource IDs
echo "Step 2: Getting resource IDs..."
ROOT_RESOURCE_ID=$(aws apigateway get-resources --rest-api-id $API_ID --region $REGION \
  --query 'items[?path==`/`].id' --output text)

API_RESOURCE_ID=$(aws apigateway get-resources --rest-api-id $API_ID --region $REGION \
  --query 'items[?path==`/api`].id' --output text)

PROXY_RESOURCE_ID=$(aws apigateway get-resources --rest-api-id $API_ID --region $REGION \
  --query 'items[?path==`/api/{proxy+}`].id' --output text)

HEALTH_RESOURCE_ID=$(aws apigateway get-resources --rest-api-id $API_ID --region $REGION \
  --query 'items[?path==`/health`].id' --output text)

LAMBDA_RESOURCE_ID=$(aws apigateway get-resources --rest-api-id $API_ID --region $REGION \
  --query 'items[?path==`/lambda`].id' --output text)

echo "Root Resource ID: $ROOT_RESOURCE_ID"
echo "API Resource ID: $API_RESOURCE_ID"
echo "Proxy Resource ID: $PROXY_RESOURCE_ID"
echo "Health Resource ID: $HEALTH_RESOURCE_ID"
echo "Lambda Resource ID: $LAMBDA_RESOURCE_ID (KEEPING THIS)"
echo ""
read -p "Press Enter to continue with deletion..."
echo ""

# Step 3: Delete /api/{proxy+} resource (if exists)
if [ -n "$PROXY_RESOURCE_ID" ] && [ "$PROXY_RESOURCE_ID" != "None" ]; then
  echo "Step 3: Deleting /api/{proxy+} resource..."
  echo "  Resource ID: $PROXY_RESOURCE_ID"
  
  # Delete method first
  aws apigateway delete-method \
    --rest-api-id $API_ID \
    --resource-id $PROXY_RESOURCE_ID \
    --http-method ANY \
    --region $REGION 2>/dev/null || echo "  No method to delete"
  
  # Delete resource
  aws apigateway delete-resource \
    --rest-api-id $API_ID \
    --resource-id $PROXY_RESOURCE_ID \
    --region $REGION
  
  echo "✅ Deleted /api/{proxy+} resource"
else
  echo "Step 3: /api/{proxy+} resource doesn't exist, skipping"
fi
echo ""
read -p "Press Enter to continue..."
echo ""

# Step 4: Delete /health resource (if exists)
if [ -n "$HEALTH_RESOURCE_ID" ] && [ "$HEALTH_RESOURCE_ID" != "None" ]; then
  echo "Step 4: Deleting /health resource..."
  echo "  Resource ID: $HEALTH_RESOURCE_ID"
  
  # Delete method first
  aws apigateway delete-method \
    --rest-api-id $API_ID \
    --resource-id $HEALTH_RESOURCE_ID \
    --http-method GET \
    --region $REGION 2>/dev/null || echo "  No method to delete"
  
  # Delete resource
  aws apigateway delete-resource \
    --rest-api-id $API_ID \
    --resource-id $HEALTH_RESOURCE_ID \
    --region $REGION
  
  echo "✅ Deleted /health resource"
else
  echo "Step 4: /health resource doesn't exist, skipping"
fi
echo ""
read -p "Press Enter to continue with setup..."
echo ""

# Step 5: Recreate /api resource if needed
echo "Step 5: Setting up /api resource..."
if [ -z "$API_RESOURCE_ID" ] || [ "$API_RESOURCE_ID" == "None" ]; then
  API_RESOURCE_ID=$(aws apigateway create-resource \
    --rest-api-id $API_ID \
    --parent-id $ROOT_RESOURCE_ID \
    --path-part api \
    --region $REGION \
    --query 'id' --output text)
  echo "✅ Created /api resource: $API_RESOURCE_ID"
else
  echo "✅ /api resource exists: $API_RESOURCE_ID"
fi
echo ""

# Step 6: Create /api/{proxy+} resource
echo "Step 6: Creating /api/{proxy+} resource..."
PROXY_RESOURCE_ID=$(aws apigateway create-resource \
  --rest-api-id $API_ID \
  --parent-id $API_RESOURCE_ID \
  --path-part '{proxy+}' \
  --region $REGION \
  --query 'id' --output text)

echo "✅ Created /api/{proxy+} resource: $PROXY_RESOURCE_ID"
echo ""

# Step 7: Setup /api/{proxy+} method and integration
echo "Step 7: Setting up /api/{proxy+} method and integration..."
aws apigateway put-method \
  --rest-api-id $API_ID \
  --resource-id $PROXY_RESOURCE_ID \
  --http-method ANY \
  --authorization-type NONE \
  --region $REGION \
  --request-parameters '{"method.request.path.proxy": true}' > /dev/null

aws apigateway put-integration \
  --rest-api-id $API_ID \
  --resource-id $PROXY_RESOURCE_ID \
  --http-method ANY \
  --type HTTP_PROXY \
  --integration-http-method ANY \
  --uri "http://${NEW_IP}:${EC2_PORT}/api/{proxy}" \
  --region $REGION \
  --request-parameters '{"integration.request.path.proxy": "method.request.path.proxy}' > /dev/null

aws apigateway put-method-response \
  --rest-api-id $API_ID \
  --resource-id $PROXY_RESOURCE_ID \
  --http-method ANY \
  --status-code 200 \
  --region $REGION > /dev/null

aws apigateway put-integration-response \
  --rest-api-id $API_ID \
  --resource-id $PROXY_RESOURCE_ID \
  --http-method ANY \
  --status-code 200 \
  --region $REGION > /dev/null

echo "✅ /api/{proxy+} configured"
echo ""

# Step 8: Create /health resource
echo "Step 8: Creating /health resource..."
HEALTH_RESOURCE_ID=$(aws apigateway create-resource \
  --rest-api-id $API_ID \
  --parent-id $ROOT_RESOURCE_ID \
  --path-part health \
  --region $REGION \
  --query 'id' --output text)

echo "✅ Created /health resource: $HEALTH_RESOURCE_ID"
echo ""

# Step 9: Setup /health method and integration
echo "Step 9: Setting up /health method and integration..."
aws apigateway put-method \
  --rest-api-id $API_ID \
  --resource-id $HEALTH_RESOURCE_ID \
  --http-method GET \
  --authorization-type NONE \
  --region $REGION > /dev/null

aws apigateway put-integration \
  --rest-api-id $API_ID \
  --resource-id $HEALTH_RESOURCE_ID \
  --http-method GET \
  --type HTTP_PROXY \
  --integration-http-method GET \
  --uri "http://${NEW_IP}:${EC2_PORT}/health" \
  --region $REGION > /dev/null

aws apigateway put-method-response \
  --rest-api-id $API_ID \
  --resource-id $HEALTH_RESOURCE_ID \
  --http-method GET \
  --status-code 200 \
  --region $REGION > /dev/null

aws apigateway put-integration-response \
  --rest-api-id $API_ID \
  --resource-id $HEALTH_RESOURCE_ID \
  --http-method GET \
  --status-code 200 \
  --region $REGION > /dev/null

echo "✅ /health configured"
echo ""

# Step 10: Deploy
echo "Step 10: Deploying API Gateway..."
aws apigateway create-deployment \
  --rest-api-id $API_ID \
  --stage-name prod \
  --region $REGION \
  --description "Recreated proxy and health endpoints - IP: ${NEW_IP}"

echo "✅ Deployed!"
echo ""

# Summary
echo "=========================================="
echo "✅ Setup Complete!"
echo "=========================================="
echo ""
echo "API Gateway URLs:"
echo "  Health: https://${API_ID}.execute-api.${REGION}.amazonaws.com/prod/health"
echo "  API:    https://${API_ID}.execute-api.${REGION}.amazonaws.com/prod/api/*"
echo "  Lambda: https://${API_ID}.execute-api.${REGION}.amazonaws.com/prod/lambda/reports"
echo ""
echo "Test Commands:"
echo "  curl https://${API_ID}.execute-api.${REGION}.amazonaws.com/prod/health"
echo "  curl https://${API_ID}.execute-api.${REGION}.amazonaws.com/prod/api/"
echo ""


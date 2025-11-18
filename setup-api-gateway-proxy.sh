#!/bin/bash
# Complete API Gateway proxy setup for EC2 backend

REGION="eu-west-1"
API_NAME="smart-expense-monthly-reports-api"
NEW_IP="34.248.251.253"
EC2_PORT="8000"

echo "=========================================="
echo "API Gateway Proxy Setup for EC2 Backend"
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

# Step 2: Get Root Resource ID
echo "Step 2: Getting root resource ID..."
ROOT_RESOURCE_ID=$(aws apigateway get-resources --rest-api-id $API_ID --region $REGION \
  --query 'items[?path==`/`].id' --output text)

echo "✅ Root Resource ID: $ROOT_RESOURCE_ID"
echo ""

# Step 3: Check if /api resource exists, create if not
echo "Step 3: Checking /api resource..."
API_RESOURCE_ID=$(aws apigateway get-resources --rest-api-id $API_ID --region $REGION \
  --query 'items[?path==`/api`].id' --output text)

if [ -z "$API_RESOURCE_ID" ]; then
  echo "   Creating /api resource..."
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

# Step 4: Check if /api/{proxy+} resource exists, create if not
echo "Step 4: Checking /api/{proxy+} resource..."
PROXY_RESOURCE_ID=$(aws apigateway get-resources --rest-api-id $API_ID --region $REGION \
  --query 'items[?path==`/api/{proxy+}`].id' --output text)

if [ -z "$PROXY_RESOURCE_ID" ]; then
  echo "   Creating /api/{proxy+} resource..."
  PROXY_RESOURCE_ID=$(aws apigateway create-resource \
    --rest-api-id $API_ID \
    --parent-id $API_RESOURCE_ID \
    --path-part '{proxy+}' \
    --region $REGION \
    --query 'id' --output text)
  echo "✅ Created /api/{proxy+} resource: $PROXY_RESOURCE_ID"
else
  echo "✅ /api/{proxy+} resource exists: $PROXY_RESOURCE_ID"
fi
echo ""

# Step 5: Check if ANY method exists, create or update
echo "Step 5: Setting up ANY method..."
METHOD_EXISTS=$(aws apigateway get-method \
  --rest-api-id $API_ID \
  --resource-id $PROXY_RESOURCE_ID \
  --http-method ANY \
  --region $REGION 2>/dev/null)

if [ $? -eq 0 ]; then
  echo "   Method exists, updating to add request parameters..."
  aws apigateway update-method \
    --rest-api-id $API_ID \
    --resource-id $PROXY_RESOURCE_ID \
    --http-method ANY \
    --patch-ops 'op=add,path=/requestParameters/method.request.path.proxy,value=true' \
    --region $REGION > /dev/null
  echo "✅ Updated ANY method with request parameters"
else
  echo "   Creating ANY method..."
  aws apigateway put-method \
    --rest-api-id $API_ID \
    --resource-id $PROXY_RESOURCE_ID \
    --http-method ANY \
    --authorization-type NONE \
    --region $REGION \
    --request-parameters '{"method.request.path.proxy": true}' > /dev/null
  echo "✅ Created ANY method with request parameters"
fi
echo ""

# Step 6: Set up HTTP_PROXY integration
echo "Step 6: Setting up HTTP_PROXY integration..."
aws apigateway put-integration \
  --rest-api-id $API_ID \
  --resource-id $PROXY_RESOURCE_ID \
  --http-method ANY \
  --type HTTP_PROXY \
  --integration-http-method ANY \
  --uri "http://${NEW_IP}:${EC2_PORT}/api/{proxy}" \
  --region $REGION \
  --request-parameters '{"integration.request.path.proxy": "method.request.path.proxy}' > /dev/null

echo "✅ HTTP_PROXY integration configured"
echo ""

# Step 7: Configure method response
echo "Step 7: Configuring method response..."
aws apigateway put-method-response \
  --rest-api-id $API_ID \
  --resource-id $PROXY_RESOURCE_ID \
  --http-method ANY \
  --status-code 200 \
  --region $REGION > /dev/null

echo "✅ Method response configured"
echo ""

# Step 8: Configure integration response
echo "Step 8: Configuring integration response..."
aws apigateway put-integration-response \
  --rest-api-id $API_ID \
  --resource-id $PROXY_RESOURCE_ID \
  --http-method ANY \
  --status-code 200 \
  --region $REGION > /dev/null

echo "✅ Integration response configured"
echo ""

# Step 9: Deploy API Gateway
echo "Step 9: Deploying API Gateway..."
aws apigateway create-deployment \
  --rest-api-id $API_ID \
  --stage-name prod \
  --region $REGION \
  --description "EC2 backend proxy setup - IP: ${NEW_IP}" > /dev/null

echo "✅ API Gateway deployed to prod stage"
echo ""

# Summary
echo "=========================================="
echo "✅ Setup Complete!"
echo "=========================================="
echo ""
echo "API Gateway URL:"
echo "  https://${API_ID}.execute-api.${REGION}.amazonaws.com/prod/api"
echo ""
echo "EC2 Backend:"
echo "  http://${NEW_IP}:${EC2_PORT}/api"
echo ""
echo "Test Commands:"
echo "  curl https://${API_ID}.execute-api.${REGION}.amazonaws.com/prod/api/health"
echo "  curl https://${API_ID}.execute-api.${REGION}.amazonaws.com/prod/api/"
echo ""


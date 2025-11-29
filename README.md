# Smart Expense Tracker - Backend

FastAPI-based backend application for the Smart Expense Tracker system.

## Quick Start

### Prerequisites

- Python 3.8 or higher
- AWS Account with DynamoDB access
- AWS CLI configured

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp env.example .env

# Edit .env with your configuration
```

### Running Locally

```bash
# Start the server
uvicorn app.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`

API documentation available at:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Project Structure

```
BackEnd/
├── app/
│   ├── core/           # Core configuration and security
│   ├── db/             # Database layer (DynamoDB)
│   ├── models/         # Pydantic models
│   ├── routers/       # API route handlers
│   └── utils/         # Utility functions
├── lambda/            # AWS Lambda functions
├── config/            # Configuration files
├── requirements.txt   # Python dependencies
└── env.example        # Environment variables template
```

## Configuration

### Environment Variables

Create a `.env` file based on `env.example`:

- `JWT_SECRET_KEY` - Secret key for JWT token generation
- `JWT_ALGORITHM` - JWT algorithm (default: HS256)
- `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` - Token expiration time
- `AWS_REGION` - AWS region for DynamoDB
- `DYNAMODB_TABLE_NAME` - DynamoDB table name

## API Endpoints

### Authentication

- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login and get access token

### Expenses

- `GET /api/expenses/monthly/{month}` - Get expenses for a month
- `POST /api/expenses/` - Add new expense
- `PUT /api/expenses/{expense_id}` - Update expense
- `DELETE /api/expenses/{expense_id}` - Delete expense

### Reports

- `GET /api/reports/monthly/{month}` - Get monthly report

### Health

- `GET /health` - Health check endpoint

## Authentication

The API uses JWT token-based authentication:

- Login endpoint returns `access_token`
- Include token in requests: `Authorization: Bearer <token>`
- Token expires after configured time

## Database

Uses AWS DynamoDB for data storage:

- User data stored in DynamoDB table
- Expenses stored per user with month-based queries
- Automatic table creation on first use

## Deployment

### AWS EC2 Deployment

1. Deploy application to EC2 instance
2. Configure API Gateway to proxy to EC2
3. Set up environment variables on EC2
4. Run with uvicorn or systemd service

### API Gateway Configuration

The backend is configured to work with AWS API Gateway:

- HTTP integration (not HTTP_PROXY) to preserve headers
- Supports both JSON and form-urlencoded requests
- CORS headers configured

## Development

### Running Tests

```bash
# Run tests
pytest tests/
```

### Code Style

Follow PEP 8 style guidelines.

## License

Private project - All rights reserved

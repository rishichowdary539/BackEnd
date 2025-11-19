# How to Test Email Functionality

## Option 1: Test Lambda Email Service Directly (Simplest)

Test the email service that Lambda uses:

```bash
cd BackEnd
python test_lambda_email.py your-email@example.com
```

This will send a test email using the Lambda email service.

---

## Option 2: Test via Backend API (Full Flow)

### Step 1: Make sure you have:
- Backend server running
- At least one user with expenses in the current month
- User has scheduler enabled

### Step 2: Trigger monthly reports via API

**Using curl:**
```bash
# First, login and get your JWT token
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "your-email@example.com", "password": "your-password"}'

# Then trigger Lambda (this will send emails to all users with scheduler enabled)
curl -X POST http://localhost:8000/api/lambda/trigger \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Using Postman:**
1. POST to `/api/lambda/trigger` with your Bearer token
2. This will trigger Lambda which sends emails to all enabled users

---

## Option 3: Test by Manually Triggering Scheduler

### Step 1: Enable scheduler for a user
- Login to frontend
- Go to Settings page
- Click "Start" to enable scheduler

### Step 2: Manually trigger the scheduler job

**Option A: Via Python (if backend is running):**
```python
from app.utils.lambda_scheduler import trigger_monthly_reports
result = trigger_monthly_reports()
print(result)
```

**Option B: Via API:**
```bash
# Trigger the monthly reports (same as Option 2)
curl -X POST http://localhost:8000/api/lambda/trigger \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

## What to Check:

1. **Email received?** Check inbox (and spam folder)
2. **Email content:**
   - Monthly spending summary
   - Budget alerts (if any)
   - Download link for CSV report
3. **Backend logs:** Check for "Email sent successfully" messages
4. **Lambda logs:** Check CloudWatch logs for email sending status

---

## Troubleshooting:

- **No email received?**
  - Check spam folder
  - Verify email address in user account
  - Check backend/Lambda logs for errors
  - Verify SMTP credentials are correct

- **SMTP errors?**
  - Make sure Gmail app password is correct
  - Check if "Less secure app access" is enabled (if needed)
  - Verify SMTP host and port are correct


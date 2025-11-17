# Lambda Function Verification Checklist

## ✅ Pre-Deployment Verification

### 1. Folder Structure
- [x] `lambda_ses_scheduler.py` - Lambda handler exists
- [x] `finance_analyzer_lib/` - Dependency folder exists
- [x] `finance_analyzer_lib/__init__.py` - Required for imports
- [x] `finance_analyzer_lib/analyzer.py` - Core library code
- [x] `package.sh` - Linux/Mac packaging script
- [x] `package.ps1` - Windows packaging script

### 2. Import Verification
- [x] Lambda handler imports: `from finance_analyzer_lib import FinanceAnalyzer`
- [x] This import will work when both files are at zip root level

### 3. Packaging Scripts
- [x] `package.sh` includes both `lambda_ses_scheduler.py` and `finance_analyzer_lib/`
- [x] `package.ps1` includes both `lambda_ses_scheduler.py` and `finance_analyzer_lib/`
- [x] Scripts exclude packaging files but include required `__init__.py` files

### 4. Expected Zip Structure
```
lambda.zip
├── lambda_ses_scheduler.py          (at root)
└── finance_analyzer_lib/             (at root)
    ├── __init__.py                   (required!)
    └── analyzer.py
```

### 5. Lambda Configuration
- Handler: `lambda_ses_scheduler.lambda_handler`
- Runtime: `python3.11` (or `python3.12`)
- Timeout: 120 seconds
- Memory: 256 MB (minimum)

### 6. Environment Variables Required
- `DYNAMO_REGION`
- `DYNAMO_TABLE_USERS`
- `DYNAMO_TABLE_EXPENSES`
- `S3_BUCKET_NAME`
- `S3_REGION`

## 🚀 Quick Test

### Test Packaging:
```bash
# Linux/Mac
cd backend/lambda
chmod +x package.sh
./package.sh

# Windows
cd backend/lambda
.\package.ps1
```

### Verify Zip Contents:
```bash
# Linux/Mac
unzip -l ../lambda.zip | grep -E "(lambda_ses_scheduler|finance_analyzer_lib|__init__)"

# Windows PowerShell
Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip = [System.IO.Compression.ZipFile]::OpenRead("../lambda.zip")
$zip.Entries | Select-Object FullName
$zip.Dispose()
```

### Expected Output Should Show:
- `lambda_ses_scheduler.py`
- `finance_analyzer_lib/__init__.py`
- `finance_analyzer_lib/analyzer.py`

## ✅ Everything is Ready!

All Lambda-related files are in `backend/lambda/` folder and ready for deployment.


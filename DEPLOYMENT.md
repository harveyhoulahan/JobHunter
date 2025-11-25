# Deployment Guide for JobHunter

## Deployment Options

### Option 1: Local Machine (Recommended for Testing)

**Best for**: Testing, development, personal use

1. **Setup**:
   ```bash
   chmod +x setup.sh
   ./setup.sh
   ```

2. **Configure**:
   - Edit `.env` with your credentials
   - Edit `config/settings.yaml` with preferences

3. **Run**:
   ```bash
   # Single run
   python src/main.py
   
   # Continuous (every 3 hours)
   python src/scheduler/run.py
   ```

4. **Cron Setup** (runs in background):
   ```bash
   crontab -e
   ```
   
   Add this line:
   ```
   0 */3 * * * cd /Users/harveyhoulahan/Desktop/JobHunter && /Users/harveyhoulahan/Desktop/JobHunter/venv/bin/python src/main.py >> logs/cron.log 2>&1
   ```

---

### Option 2: AWS Lambda (Serverless)

**Best for**: Production, cost-effective, hands-off operation

#### Architecture
- **AWS Lambda**: Runs the job hunter code
- **EventBridge**: Triggers every 3 hours
- **DynamoDB**: Stores job data (alternative to SQLite)
- **SES**: Sends email alerts
- **SNS**: Sends SMS alerts (optional)

#### Setup Steps

1. **Prepare Lambda package**:
   ```bash
   # Install dependencies to a package directory
   pip install -r requirements.txt -t lambda_package/
   
   # Copy source code
   cp -r src lambda_package/
   
   # Create zip
   cd lambda_package
   zip -r ../jobhunter-lambda.zip .
   ```

2. **Create Lambda function**:
   - Go to AWS Lambda Console
   - Create new function: `jobhunter`
   - Runtime: Python 3.11
   - Upload `jobhunter-lambda.zip`
   - Set timeout: 5 minutes
   - Set memory: 512 MB

3. **Configure environment variables** in Lambda:
   ```
   DATABASE_URL=dynamodb://jobhunter-table
   SENDGRID_API_KEY=your_key
   ALERT_EMAIL=harvey@example.com
   ENABLE_EMAIL_ALERTS=true
   ```

4. **Create EventBridge rule**:
   - Schedule: `rate(3 hours)`
   - Target: Lambda function `jobhunter`

5. **Create DynamoDB table** (if using DynamoDB):
   - Table name: `jobhunter-jobs`
   - Partition key: `url` (String)
   - Sort key: `created_at` (String)

#### Lambda Handler
Create `lambda_function.py`:
```python
from src.main import JobHunter

def lambda_handler(event, context):
    hunter = JobHunter()
    stats = hunter.run()
    
    return {
        'statusCode': 200,
        'body': stats
    }
```

---

### Option 3: Docker Container on Cloud VM

**Best for**: Full control, easy deployment

1. **Create Dockerfile** (already in project)

2. **Build image**:
   ```bash
   docker build -t jobhunter .
   ```

3. **Run container**:
   ```bash
   docker run -d \
     --name jobhunter \
     -v $(pwd)/data:/app/data \
     -v $(pwd)/config:/app/config \
     --env-file .env \
     jobhunter
   ```

4. **Deploy to cloud**:
   - **AWS ECS**: Use Fargate for serverless containers
   - **Digital Ocean**: Deploy to droplet with Docker
   - **Google Cloud Run**: Serverless container deployment

---

### Option 4: GitHub Actions (Free Tier)

**Best for**: Completely free automation

1. **Create `.github/workflows/jobhunter.yml`**:
   ```yaml
   name: Job Hunter
   
   on:
     schedule:
       - cron: '0 */3 * * *'  # Every 3 hours
     workflow_dispatch:  # Manual trigger
   
   jobs:
     hunt:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v3
         
         - name: Set up Python
           uses: actions/setup-python@v4
           with:
             python-version: '3.11'
         
         - name: Install dependencies
           run: |
             pip install -r requirements.txt
             python -m spacy download en_core_web_sm
         
         - name: Run JobHunter
           env:
             SENDGRID_API_KEY: ${{ secrets.SENDGRID_API_KEY }}
             ALERT_EMAIL: ${{ secrets.ALERT_EMAIL }}
           run: python src/main.py
         
         - name: Commit database changes
           run: |
             git config --global user.name 'JobHunter Bot'
             git config --global user.email 'bot@jobhunter.com'
             git add data/jobhunter.db
             git commit -m "Update job database" || exit 0
             git push
   ```

2. **Add secrets** in GitHub repo settings:
   - `SENDGRID_API_KEY`
   - `ALERT_EMAIL`

---

## Email Configuration

### Option A: SendGrid (Recommended)

1. Sign up at https://sendgrid.com
2. Create API key with "Mail Send" permissions
3. Add to `.env`:
   ```
   EMAIL_PROVIDER=sendgrid
   SENDGRID_API_KEY=SG.xxxxx
   ALERT_EMAIL=harvey@example.com
   ```

### Option B: Gmail SMTP

1. Enable 2FA on Gmail
2. Generate app password: https://myaccount.google.com/apppasswords
3. Add to `.env`:
   ```
   EMAIL_PROVIDER=smtp
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USERNAME=your-email@gmail.com
   SMTP_PASSWORD=your-app-password
   ALERT_EMAIL=harvey@example.com
   ```

---

## SMS Configuration (Optional)

1. Sign up at https://twilio.com
2. Get phone number and credentials
3. Add to `.env`:
   ```
   ENABLE_SMS_ALERTS=true
   TWILIO_ACCOUNT_SID=ACxxxx
   TWILIO_AUTH_TOKEN=your_token
   TWILIO_FROM_NUMBER=+1234567890
   ALERT_SMS=+1234567890
   ```

---

## Monitoring

### Logs
- **Local**: `logs/jobhunter.log`
- **Lambda**: CloudWatch Logs
- **Docker**: `docker logs jobhunter`

### Database
```bash
# View jobs
sqlite3 data/jobhunter.db "SELECT title, company, fit_score FROM jobs ORDER BY fit_score DESC LIMIT 10;"

# View statistics
sqlite3 data/jobhunter.db "SELECT source, COUNT(*) as count FROM jobs GROUP BY source;"
```

---

## Troubleshooting

### No jobs found
- Check if scrapers are being blocked (use VPN)
- Verify search terms in `config/settings.yaml`
- Check logs for errors

### No alerts received
- Verify `.env` credentials
- Check spam folder
- Review `logs/jobhunter.log`

### Rate limiting
- Increase `REQUEST_DELAY_SECONDS` in `.env`
- Reduce number of search terms
- Use rotating proxies (advanced)

---

## Cost Estimates

### Local/Cron
- **Cost**: $0 (uses your computer)
- **Pros**: Free, full control
- **Cons**: Requires computer running

### AWS Lambda
- **Cost**: ~$1-2/month
  - Lambda: 720 executions/month @ 5min = ~$0.20
  - DynamoDB: On-demand = ~$1
  - SES: First 62k emails free
- **Pros**: Serverless, reliable, scalable
- **Cons**: Requires AWS setup

### GitHub Actions
- **Cost**: $0 (free tier: 2000 min/month)
- **Pros**: Completely free, no infrastructure
- **Cons**: Public repo required for free tier

---

## Next Steps

1. Choose deployment option
2. Configure credentials
3. Test with single run: `python src/main.py`
4. Deploy to production
5. Monitor alerts and refine search terms

For questions or issues, check the logs first!

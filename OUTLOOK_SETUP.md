# Outlook Email Setup Guide

## Quick Setup for harveyhoulahan@outlook.com

### Step 1: Edit your `.env` file

```bash
cd /Users/harveyhoulahan/Desktop/JobHunter
nano .env
```

### Step 2: Add these exact settings

```bash
# Email Configuration
EMAIL_PROVIDER=smtp
SMTP_HOST=smtp-mail.outlook.com
SMTP_PORT=587
SMTP_USERNAME=harveyhoulahan@outlook.com
SMTP_PASSWORD=your_password_here
ENABLE_EMAIL_ALERTS=true

# Alert Recipient
ALERT_EMAIL=harveyhoulahan@outlook.com

# Other settings (leave as default)
DATABASE_URL=sqlite:///data/jobhunter.db
USER_AGENT=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36
REQUEST_DELAY_SECONDS=2
MAX_RETRIES=3
LOG_LEVEL=INFO
LOG_FILE=logs/jobhunter.log
ENABLE_SMS_ALERTS=false
ENABLE_DEDUPLICATION=true
ENABLE_VISA_FILTERING=true
```

### Step 3: Get your Outlook password

You have two options:

#### Option A: Use your regular Outlook password (Simpler)
Just use your normal Outlook login password. This works if you don't have 2FA enabled.

#### Option B: Use an App Password (More secure, required if you have 2FA)

1. Go to: https://account.microsoft.com/security
2. Sign in with your Outlook account
3. Click on **"Advanced security options"**
4. Scroll down to **"App passwords"**
5. Click **"Create a new app password"**
6. A password will be generated (looks like: `abcd-efgh-ijkl-mnop`)
7. Copy this password
8. Paste it in the `.env` file as `SMTP_PASSWORD`

**Note**: Don't include the dashes when you paste it.

### Step 4: Save and test

```bash
# Save the file (in nano: Ctrl+X, then Y, then Enter)

# Activate virtual environment
source venv/bin/activate

# Test it
python src/main.py
```

You should receive an email if any jobs are found!

---

## Troubleshooting

### "Authentication failed" error

**Try this:**
1. Make sure you're using the correct email: `harveyhoulahan@outlook.com`
2. If you have 2-factor authentication (2FA) enabled, you MUST use an app password
3. If using app password, remove the dashes: use `abcdefghijklmnop` not `abcd-efgh-ijkl-mnop`

### "Connection refused" error

**Check:**
```bash
# Test connection
python -c "
import smtplib
try:
    server = smtplib.SMTP('smtp-mail.outlook.com', 587)
    server.starttls()
    print('✓ Connection successful!')
    server.quit()
except Exception as e:
    print(f'✗ Error: {e}')
"
```

### Test email manually

```bash
python << 'EOF'
from src.alerts.notifications import EmailAlerter

email = EmailAlerter()
result = email.send_immediate_alert({
    'title': 'Test Job - ML Engineer',
    'company': 'Test Company',
    'url': 'https://example.com/job',
    'fit_score': 85,
    'matches': {
        'tech': ['Python', 'ML', 'AWS'],
        'industry': ['AI/ML'],
        'role': ['ML Engineer'],
        'visa_keywords': ['E-3 visa']
    },
    'reasoning': 'This is a test email from JobHunter',
    'visa_status': 'explicit',
    'location': 'New York, NY',
    'posted_date': 'Today'
}, 'harveyhoulahan@outlook.com')

if result:
    print('✓ Test email sent! Check your inbox.')
else:
    print('✗ Email failed. Check logs/jobhunter.log for errors.')
EOF
```

---

## Alternative: Using Outlook's SMTP without App Password

If you don't want to set up an app password, you can also:

1. **Disable 2FA temporarily** (not recommended for security)
2. **Enable "Less secure app access"** in Outlook settings
3. **Use a different email service** (Gmail with app password is very reliable)

---

## Your Complete `.env` File Should Look Like:

```bash
# Email Configuration
EMAIL_PROVIDER=smtp
SMTP_HOST=smtp-mail.outlook.com
SMTP_PORT=587
SMTP_USERNAME=harveyhoulahan@outlook.com
SMTP_PASSWORD=YourActualPasswordHere
ENABLE_EMAIL_ALERTS=true

# Alert Recipient
ALERT_EMAIL=harveyhoulahan@outlook.com

# Database
DATABASE_URL=sqlite:///data/jobhunter.db

# Scraping Configuration
USER_AGENT=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36
REQUEST_DELAY_SECONDS=2
MAX_RETRIES=3

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/jobhunter.log

# Feature Flags
ENABLE_SMS_ALERTS=false
ENABLE_DEDUPLICATION=true
ENABLE_VISA_FILTERING=true
```

Just replace `YourActualPasswordHere` with your real password!

---

**Once configured, run:**
```bash
source venv/bin/activate
python src/main.py
```

You should start receiving job alerts at **harveyhoulahan@outlook.com**! 🎉

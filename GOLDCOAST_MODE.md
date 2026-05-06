# Gold Coast Lifestyle Job Hunter

## Overview
JobHunter now has **two modes** to support your different job hunting needs:

1. **Tech Jobs Mode** (default) - NYC tech jobs with AI/ML focus
2. **Gold Coast Lifestyle Mode** - Casual/part-time wellness, hospitality, and lifestyle jobs

## How to Switch Modes

### In the Dashboard
Click the mode switcher buttons in the header:
- **Tech Jobs** - Shows tech jobs (Greenhouse, Lever, LinkedIn, etc.)
- **Gold Coast Lifestyle** - Shows Gold Coast casual/part-time jobs from Seek.com.au

Your mode preference is saved and persists across sessions.

## Gold Coast Mode Features

### Specialized Scoring (0-100 points)
Unlike tech jobs that focus on skills and semantic matching, Gold Coast jobs are scored based on:

1. **Venue Match (25 points)** - Priority venues:
   - Wellness retreats: Gwinganna, Golden Door, GAIA Retreat
   - Boutique hotels: Halcyon House, Versace Hotel
   - Upscale cafes: Paddock Bakery, Rick Shores, Hellenika
   - Fitness studios: F45, Barry's Bootcamp, Pilates studios

2. **Role Match (30 points)** - Ideal positions:
   - Retreat coordinator, wellness coordinator
   - Barista, bartender, sommelier
   - Yoga instructor, personal trainer, surf instructor
   - Concierge, guest services, host
   - Gallery assistant, social media coordinator

3. **Vibe Match (20 points)** - Culture keywords:
   - Boutique, upscale, artisan, experiential
   - Beachside, hinterland, wellness, luxury
   - Community-focused, creative, sustainable

4. **Work Style (15 points)** - Employment type:
   - Casual, part-time, flexible roster = 15 points
   - Full-time = 5 points (still possible but not ideal)

5. **Location Bonus (10 points)**
   - Gold Coast, Burleigh, Currumbin, Tallebudgera
   - Coolangatta, Broadbeach, Surfers Paradise
   - Main Beach, Miami, Mermaid Beach, Hinterland

6. **Red Flag Penalty (-30 points)** - Avoid:
   - Corporate, KPIs, sales targets/quotas
   - Night shift, franchise, casino
   - Telemarketing, cold calling

### Job Categories
Gold Coast jobs are categorized as:
- **Wellness & Retreats** - Spa, yoga, meditation, wellness coordination
- **Boutique Hospitality** - Upscale hotels, resorts, guest services
- **Food & Beverage** - Cafes, restaurants, bars (upscale/boutique)
- **Fitness & Movement** - Personal training, pilates, yoga, surf
- **Outdoor & Adventure** - Surf schools, adventure tourism, eco-tours
- **Creative & Retail** - Galleries, boutiques, artisan shops
- **Events & Social** - Event coordination, community engagement
- **General Hospitality** - Other hospitality roles

### Scraping Sources
Gold Coast mode scrapes from:
- **Seek.com.au** with targeted search queries:
  - Wellness retreat coordinator
  - Barista Gold Coast casual
  - Boutique hotel
  - Yoga/fitness instructor
  - Personal trainer
  - Gallery assistant
  - Events coordinator

### Scoring Example
```
Job: Wellness Retreat Coordinator at Gwinganna Lifestyle Retreat
Company: Gwinganna
Location: Gold Coast Hinterland
Type: Part-time, flexible

Score Breakdown:
• Venue match: 25/25 (priority venue: Gwinganna)
• Role match: 30/30 (retreat coordinator, wellness)
• Vibe match: 20/20 (luxury, wellness, retreat, hinterland)
• Work style: 15/15 (part-time, flexible)
• Location bonus: 10/10 (Gold Coast Hinterland)
• Red flags: 0 (none detected)

Total: 95/100
Category: Wellness & Retreats
Recommended: Yes ✅

Reasoning: "Excellent wellness & retreats opportunity at 95% - matches priority 
venue (gwinganna). Work style suits: part-time, flexible, casual. Vibe indicators: 
luxury, wellness, retreat, hinterland. Strong match for Gold Coast lifestyle priorities."
```

## Using Gold Coast Mode

### 1. Switch to Gold Coast Mode
Click the "Gold Coast Lifestyle" button in the header

### 2. Run Scrape
Click "Run scrape now" - it will scrape Seek.com.au for Gold Coast jobs

### 3. Review Jobs
Jobs are ranked by fit score (just like tech jobs):
- **Top Matches** (70-100%) - Priority venues, ideal roles
- **Great Matches** (60-69%) - Good fit, minor compromises
- **Good Matches** (50-59%) - Decent options

### 4. Apply
Same workflow as tech jobs:
- Generate cover letter (adapted for hospitality/lifestyle)
- Review and edit
- Export PDF
- Manual apply (most Gold Coast jobs don't support auto-submit)

## Cover Letters for Gold Coast Jobs
Cover letters in Gold Coast mode will emphasize:
- Genuine interest in wellness/hospitality/lifestyle work
- Alignment with venue's values (sustainability, wellness, luxury)
- Relevant experience in customer service, hospitality, fitness
- Work permit status (if applicable)
- Availability for casual/part-time work

## Differences from Tech Mode

| Feature | Tech Mode | Gold Coast Mode |
|---------|-----------|-----------------|
| **Scoring focus** | Tech stack, AI/ML semantic, seniority | Venue prestige, vibe, work-life balance |
| **Job sources** | LinkedIn, Greenhouse, Lever, Wellfound | Seek.com.au (Gold Coast filtered) |
| **Auto-submit** | Supported for Greenhouse, Lever, Workday | Manual apply (Seek requires it) |
| **Cover letter style** | Technical, metric-driven for ML roles | Hospitality-focused, genuine interest |
| **Red flags** | No visa sponsorship, wrong seniority | Corporate culture, KPIs, night shifts |
| **Priorities** | Remote, NYC, E-3 visa, AI/ML focus | Casual hours, beachside, wellness, upscale |

## Priority Venues (pre-configured)
The Gold Coast scorer knows about 50+ priority venues including:
- Gwinganna Lifestyle Retreat, Golden Door Health Retreat
- GAIA Retreat & Spa, Byron Bay Wellness Sanctuary
- Halcyon House, Versace Hotel, QT Gold Coast
- Paddock Bakery, Rick Shores, Hellenika, Bam Bam Bakehouse
- F45 Training, Barry's Bootcamp, Pilates studios
- The Atlantic, Burleigh Pavilion, Justin Lane

## Tips for Best Results

### Maximize Your Score
1. **Target priority venues** - Jobs at known boutique venues score higher
2. **Look for casual/part-time** - Full-time jobs score lower
3. **Avoid corporate chains** - Red flags: franchise, KPIs, quotas
4. **Beachside > CBD** - Location matters for lifestyle fit
5. **Wellness/upscale keywords** - Boutique, artisan, luxury boost scores

### Customization
Want to add your own priority venues or roles? Edit:
```python
src/scoring/goldcoast_scorer.py
```
- `priority_venues` list - Add venues you want to work at
- `ideal_roles` list - Add job titles you're interested in
- `desirable_keywords` - Add culture/vibe keywords
- `red_flags` - Add dealbreakers

### Cover Letter Style
For Gold Coast jobs, your cover letters will:
- Skip technical jargon (no PyTorch, AWS, microservices)
- Emphasize customer service, hospitality experience
- Show genuine interest in wellness/lifestyle industry
- Mention relevant certifications (yoga, barista, first aid)
- Highlight availability for casual/flexible hours

## Technical Details

### Files Created
- `src/scoring/goldcoast_scorer.py` - Gold Coast job scoring algorithm
- `src/scrapers/goldcoast_scraper.py` - Seek.com.au scraper for Gold Coast jobs

### Files Modified
- `templates/dashboard.html` - Added mode switcher UI
- `static/style.css` - Mode switcher styling
- `web_app.py` - Mode-aware job filtering and scraping

### Database
Gold Coast jobs are stored in the same database with:
- `source = 'seek_goldcoast'` - Identifies Gold Coast jobs
- `location` contains "Gold Coast" - Additional filter
- `fit_score` - Scored with Gold Coast algorithm
- `reasoning` - Gold Coast-specific reasoning

## Next Steps
1. Switch to Gold Coast mode
2. Run your first scrape
3. Review the jobs and scores
4. Fine-tune priority venues if needed
5. Start applying to your ideal lifestyle jobs!

Enjoy the Gold Coast job hunting! 🌊☀️

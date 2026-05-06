# Quick Start: Gold Coast Lifestyle Mode

## What's New?
JobHunter now supports **two separate job hunting modes**:

1. **Tech Jobs** - Your existing NYC tech job hunter (AI/ML, Python, remote work)
2. **Gold Coast Lifestyle** - NEW! Casual/part-time Gold Coast jobs (wellness retreats, boutique hotels, upscale cafes)

---

## How to Use

### Step 1: Open Dashboard
Visit: **http://localhost:5002**

### Step 2: Switch Modes
Look for the **mode switcher** at the top of the page:
```
[Tech Jobs] [Gold Coast Lifestyle]
```

Click **"Gold Coast Lifestyle"** to switch modes.

### Step 3: Run Scrape
Click **"Run scrape now"**

In Gold Coast mode, this will:
- Search Seek.com.au for Gold Coast jobs
- Look for: wellness retreat roles, barista jobs, boutique hotels, fitness instructors, etc.
- Score each job based on: venue prestige, work-life balance, vibe, casual hours
- Show you the top matches first

### Step 4: Review Jobs
Jobs are scored 0-100 based on Gold Coast lifestyle priorities:

**Top Matches (70-100%)**
- Priority venues: Gwinganna, Halcyon House, Paddock Bakery
- Ideal roles: retreat coordinator, barista, yoga instructor
- Casual/part-time hours
- Boutique/upscale vibe

**What Gets High Scores:**
✅ Gwinganna Lifestyle Retreat - Wellness Coordinator (95%)
✅ Halcyon House - Guest Services (88%)
✅ Paddock Bakery - Barista (Part-time) (82%)
✅ F45 Training - Fitness Coach (78%)

**What Gets Low Scores:**
❌ Corporate hotel chains with KPIs
❌ Night shift roles
❌ Full-time only with rigid schedules
❌ Franchise/chain operations

### Step 5: Apply
Same as tech jobs:
1. Click job card to expand details
2. "Generate Cover Letter" → Review → Edit
3. "Download PDF"
4. Click "Apply Myself" to open Seek listing
5. Submit application manually (Seek requires it)

---

## Scoring Breakdown

### What Makes a Job Score High?

**Venue Match (25 points)**
- Priority venues we know are good: Gwinganna, Golden Door, Halcyon House, Paddock Bakery, Rick Shores, etc.
- Boutique hotels, wellness retreats, upscale cafes

**Role Match (30 points)**
- Retreat coordinator, wellness coordinator
- Barista, bartender, sommelier
- Yoga instructor, personal trainer, surf instructor
- Concierge, guest services, host
- Gallery assistant, events coordinator

**Vibe Match (20 points)**
- Keywords: boutique, upscale, artisan, experiential
- Beachside, hinterland, wellness, sustainable
- Community-focused, creative, luxury

**Work Style (15 points)**
- Casual/part-time/flexible = 15 points
- Full-time = 5 points (still okay, just not ideal)

**Location Bonus (10 points)**
- Gold Coast, Burleigh, Currumbin, Coolangatta
- Broadbeach, Surfers Paradise, Hinterland

**Red Flags (-30 points)**
- Corporate culture, KPIs, sales quotas
- Night shift, franchise, casino
- Telemarketing, cold calling

---

## Example Jobs

### 95% Match - Gwinganna Wellness Retreat Coordinator
```
Company: Gwinganna Lifestyle Retreat
Location: Gold Coast Hinterland
Type: Part-time, flexible roster

Why it scores high:
• Priority venue (Gwinganna) - 25 pts
• Perfect role (retreat coordinator, wellness) - 30 pts
• Great vibe (luxury, wellness, retreat, hinterland) - 20 pts
• Casual hours - 15 pts
• Gold Coast location - 10 pts
• No red flags - 0 pts

Total: 95/100
Category: Wellness & Retreats
```

### 82% Match - Paddock Bakery Barista
```
Company: Paddock Bakery
Location: Burleigh Heads
Type: Casual

Why it scores high:
• Priority venue (Paddock Bakery) - 25 pts
• Good role (barista) - 30 pts
• Vibe keywords (artisan, beachside) - 15 pts
• Casual hours - 15 pts
• Burleigh location - 10 pts
• No red flags - 0 pts

Total: 82/100
Category: Food & Beverage
```

### 35% Match - Big Box Electronics Sales
```
Company: JB Hi-Fi
Location: Robina
Type: Full-time

Why it scores low:
• No venue match - 0 pts
• No ideal role match - 0 pts
• No vibe keywords - 0 pts
• Full-time (not ideal) - 5 pts
• Gold Coast location - 10 pts
• Red flags: KPIs, sales quotas, corporate - (-30 pts)

Total: 35/100
Category: General Hospitality
```

---

## Tips for Success

### 1. Customize Priority Venues
Edit `src/scoring/goldcoast_scorer.py` to add venues you want to work at:
```python
self.priority_venues = [
    'gwinganna', 'golden door', 'halcyon house',
    'your favorite cafe here',  # Add your own!
]
```

### 2. Run Scrapes Regularly
Gold Coast jobs fill fast. Run scrapes daily to catch new listings.

### 3. Focus on Top Matches
70%+ scores are your best bets. These align with your lifestyle priorities.

### 4. Customize Cover Letters
Mention:
- Why you're drawn to wellness/hospitality/lifestyle work
- Your availability for casual/part-time hours
- Alignment with venue's values (sustainability, wellness, community)
- Relevant experience (customer service, barista, yoga cert, first aid)

### 5. Manual Apply
Unlike tech jobs (Greenhouse, Lever), Seek requires manual applications:
1. Generate your cover letter in JobHunter
2. Download PDF
3. Click "Apply Myself" → opens Seek listing
4. Upload cover letter + CV on Seek
5. Mark as applied in JobHunter

---

## Switching Back to Tech Mode

Click **"Tech Jobs"** in the mode switcher.

This will:
- Show your NYC tech jobs (LinkedIn, Greenhouse, Lever)
- Use tech scoring (AI/ML semantic, tech stack matching)
- Enable auto-submit for supported platforms
- Use technical cover letter style

Your mode preference is saved, so it'll remember next time you visit.

---

## Need Help?

See full documentation: `GOLDCOAST_MODE.md`

**Common Questions:**

Q: Can I see both tech and Gold Coast jobs at once?
A: Not yet - switch modes to see each separately. We keep them separate because the scoring systems are completely different.

Q: Will Gold Coast jobs auto-submit?
A: No - Seek.com.au requires manual applications. Use "Apply Myself" button.

Q: Can I customize the scoring?
A: Yes! Edit `src/scoring/goldcoast_scorer.py` to adjust weights, add venues, change red flags.

Q: What if I want to add more job sources?
A: Edit `src/scrapers/goldcoast_scraper.py` to add more search queries or different job boards.

---

## Current Status

✅ Gold Coast scorer created (50+ priority venues)
✅ Seek.com.au scraper implemented
✅ Mode switcher UI added
✅ Separate scoring for lifestyle jobs
✅ Docker containers rebuilt and running

**Ready to use!** Switch to Gold Coast mode and run your first scrape.

Good luck finding your ideal Gold Coast lifestyle job! 🌊☀️🥑

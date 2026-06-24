"""
Harvey Houlahan — JobHunter profile
Drop-in replacement for src/profile.py

Updated: 2026-05-02
Targets: AU, US, EU/UK, Remote/Freelance
"""

HARVEY_PROFILE = {
    # ── identity ──────────────────────────────────────────────
    "name": "Harvey Houlahan",
    "email": "harveyhoulahan@outlook.com",
    "phone": "+61 408 839 119",
    "portfolio": "https://hjhportfolio.com",
    "linkedin": "https://linkedin.com/in/harveyhoulahan",

    # ── summary (used by AI scorer for semantic matching) ─────
    "summary": (
        "ML engineer and software engineer who grew up on a cotton farm in rural "
        "Queensland — the interest in climate, land management, and sustainability "
        "is personal, not a CV keyword. Currently building geospatial tools at "
        "ArborMeta that inform Australian carbon credit policy, and shipping "
        "e-commerce features at Step One. Monash Advanced CS grad (HD GPA, AI/ML "
        "and algorithms concentrations, 99.4 ATAR). Production experience across "
        "React, TypeScript, Python, PostgreSQL, Swift, and C/C++. Thinks in "
        "systems and architecture, builds clean and modular code, and cares about "
        "making technology that connects to something physical and real. Open to "
        "full-time, contract, and freelance work globally."
    ),

    # ── extended bio (for AI scorer semantic context) ─────────
    #    Gives the LLM gate richer signal about what makes a role exciting
    "extended_context": (
        "Background in agriculture and rural Australia. Deferred a medical degree "
        "to pursue CS. Driven by sustainability, ecological systems, and building "
        "things that matter — not just shipping features. Strong product instincts "
        "and design sensibility; interested in industrial design, woodworking, and "
        "physical products alongside software. Long-term goal is opening a "
        "bouldering gym in regional NSW. Thrives in small teams, greenfield "
        "projects, and roles where engineering connects directly to real-world "
        "outcomes. Not interested in enterprise bureaucracy or pure consulting."
    ),

    # ── skills (semantic + keyword matching) ──────────────────
    #    Split into tiers so the scorer can weight core vs familiar
    "skills": {
        "core": [
            "Python", "TypeScript", "JavaScript", "React", "Node.js",
            "PostgreSQL", "SQL", "Git", "REST APIs", "Docker",
            "Machine Learning", "Data Pipelines", "FastAPI",
            "Tailwind CSS", "HTML", "CSS",
        ],
        "strong": [
            "Swift", "SwiftUI", "iOS Development",
            "MapLibre GL JS", "Geospatial", "GIS", "PMTiles",
            "Shopify", "Liquid", "E-commerce",
            "Selenium", "Playwright", "Web Scraping",
            "Pandas", "NumPy", "Jupyter",
            "Sentence Transformers", "Embeddings", "NLP",
            "AWS", "Linux", "SSH", "Nginx",
            "C", "C++", "Rust",
        ],
        "familiar": [
            "Java", "MATLAB", "C#", ".NET",
            "Core ML", "visionOS", "ARKit",
            "Spring Boot", "Android Studio",
            "Terraform", "Kubernetes",
            "GraphQL", "Redis", "MongoDB",
            "Figma", "Adobe Suite",
        ],
    },

    # ── target roles (matched against job titles) ─────────────
    #    Ordered roughly by preference; scorer can use position as weight
    #    PRIMARY FOCUS = Machine Learning / AI. General SWE roles come after so the
    #    role scorer and ML-first search ordering surface ML work first.
    "roles": [
        # ── primary: ML / AI (junior-friendly variants first) ──
        "Machine Learning Engineer",
        "ML Engineer",
        "Junior Machine Learning Engineer",
        "Junior ML Engineer",
        "Graduate Machine Learning Engineer",
        "Associate Machine Learning Engineer",
        "Machine Learning Engineer I",
        "AI Engineer",
        "Junior AI Engineer",
        "Applied Scientist",
        "Applied ML Engineer",
        "MLOps Engineer",
        "Research Engineer",
        "Data Engineer",
        "Junior Data Engineer",
        "Data Scientist",
        "Junior Data Scientist",
        "NLP Engineer",
        # ── secondary: general software (junior variants included) ──
        "Software Engineer",
        "Junior Software Engineer",
        "Graduate Software Engineer",
        "Associate Software Engineer",
        "Software Engineer I",
        "Backend Engineer",
        "Junior Backend Engineer",
        "Python Developer",
        "Junior Python Developer",
        "Full Stack Engineer",
        "Full Stack Developer",
        "Backend Developer",
        "React Developer",
        "Frontend Engineer",
        # ── mobile ──
        "iOS Engineer",
        "iOS Developer",
        "Mobile Engineer",
        # ── domain-specific ──
        "Geospatial Engineer",
        "GIS Developer",
        "Climate Tech Engineer",
        "Sustainability Tech",
        # ── contract / freelance signals ──
        "Contract Software Engineer",
        "Freelance Developer",
        "Remote Software Engineer",
    ],

    # ── industries (boost score when job desc mentions these) ──
    "industries": [
        "Climate Tech", "Carbon", "Sustainability", "Clean Energy",
        "GreenTech", "Environmental", "Ecology", "Conservation",
        "Geospatial", "Remote Sensing", "Earth Observation",
        "E-commerce", "Retail Tech", "DTC",
        "FinTech", "Energy", "Utilities",
        "Developer Tools", "SaaS", "Startups",
        "Health Tech", "AgTech", "PropTech",
        "Fashion Tech", "Supply Chain",
    ],

    # ── work experience (fed directly to AI scorer as bullet context) ─────────
    #    Ordered most-recent first. Add up to 3 bullets per role — be specific.
    #    The AI scorer uses the first 4 roles and first 2 bullets each.
    "experience": [
        {
            "title": "ML Engineer",
            "company": "ArborMeta",
            "period": "2026 – present",
            "location": "Remote (Byron Bay, NSW)",
            "bullets": [
                "Architected geospatial web apps (React, MapLibre GL JS, PostGIS, PMTiles) visualising ecological carbon-farming survey data across Australia, directly informing federal and state government carbon-credit accreditation policy.",
                "Engineered multi-LOD spatial data pipelines — Fulcrum field survey parsing, rainforest transect analysis, PMTiles tile generation — reducing data processing time and enabling real-time government stakeholder dashboards.",
                "Conducted primary ML research into carbon sequestration measurement and verification, producing analytical outputs that consult Australian government bodies; work presents a pathway into doctoral research in computational ecology.",
            ],
        },
        {
            "title": "Software Engineer (Contract)",
            "company": "Step One Clothing",
            "period": "2025 – present",
            "location": "Remote",
            "bullets": [
                "Built an AI-powered natural-language search engine matching user intent to product attributes, materially increasing discoverability and purchase conversion on a high-traffic Shopify storefront.",
                "Engineered a schema-driven Shopify mega-menu end-to-end (Liquid, TypeScript) with built-in analytics and editorial feedback loop, cutting merchandising change lead time and reducing content errors.",
                "Delivered an accessible navigation system with live analytics instrumentation, enabling the merchandising team to iterate on live content without engineering involvement.",
            ],
        },
        {
            "title": "iOS Engineer",
            "company": "FibreTrace",
            "period": "2025",
            "location": "Remote (Moree, NSW)",
            "bullets": [
                "Conceived, pitched, and built end-to-end a SwiftUI product-passport app for the world's first fibre-level supply-chain verification platform — QR/NFC scan, signed deep-link journey, offline-first caching, App Clip with <3s time-to-passport.",
                "Shipped on-device ML: local JWT/HMAC checks via Keychain and App Attest to flag spoofed tags, plus anomaly detection on chain-of-custody and ETA predictions — secured CEO buy-in and a partner-brand pilot via TestFlight demo.",
            ],
        },
        {
            "title": "AI / Backend Engineer (Contract)",
            "company": "Friday Technologies",
            "period": "2025",
            "location": "Melbourne (Hybrid)",
            "bullets": [
                "Designed and deployed scalable ML infrastructure and backend systems for Apple-recognised projects leveraging Core ML and visionOS.",
                "Built production data pipelines and API integrations for intelligent applications; contributed to projects that received direct Apple recognition for innovation.",
            ],
        },
    ],

    # ── seniority (controls _assess_seniority filtering) ──────
    #    ~6 months full-time experience → target junior + mid; senior is a soft
    #    penalty (not excluded — the ArborMeta title is "ML Engineer"), and
    #    management/staff/principal stay hard-excluded.
    "seniority": {
        "target": ["junior", "graduate", "associate", "entry", "mid"],
        "exclude": ["director", "vp", "chief", "head of", "principal", "staff engineer"],
        "years_experience": 1,
    },

    # ── education (for keyword matching) ──────────────────────
    "education": {
        "degree": "B.S. Advanced Computer Science",
        "university": "Monash University",
        "graduation": "Nov 2025",
        "gpa": "3.6/4.0 (High Distinction)",
        "concentrations": [
            "Artificial Intelligence / Machine Learning",
            "Advanced Algorithms and Data Structures",
        ],
        "prior": "Direct admittance M.B.B.S., James Cook University (deferred)",
        "atar": 99.4,
    },

    # ── location + work arrangement ───────────────────────────
    #    This drives _assess_location and locations.json alignment
    "location": {
        "current": "Byron Bay, NSW, Australia",
        "primary_market": "GLOBAL",  # US jobs shown but lower priority; AU/EU/Remote = focus
        "preferred_regions": [
            # tier 1 — no score penalty
            {"region": "Australia", "cities": [
                "Sydney", "Byron Bay", "Gold Coast", "Brisbane", "Melbourne",
            ]},
            {"region": "Remote", "cities": ["Remote", "Anywhere", "Freelance", "Digital Nomad"]},
            # tier 1 — EU (AU-EU Free Trade Agreement signed Mar 2026, live ~2027)
            {"region": "Europe", "cities": [
                "London", "Berlin", "Amsterdam", "Dublin", "Lisbon",
                "Barcelona", "Stockholm", "Copenhagen", "Vienna", "Zurich",
            ]},
            # tier 2 — Middle East
            {"region": "Middle East", "cities": [
                "Dubai", "Abu Dhabi", "Tel Aviv",
            ]},
            # tier 2 — Latin America
            {"region": "Latin America", "cities": [
                "Mexico City", "Medellin", "Buenos Aires", "Montevideo", "Bogota", "Oaxaca",
            ]},
            # tier 2 — Asia Pacific
            {"region": "Asia Pacific", "cities": [
                "Singapore", "Tokyo", "Bali",
            ]},
            # tier 3 — United States (still tracked, lower priority; remote/freelance US = ok)
            {"region": "United States", "cities": [
                "New York", "San Francisco", "Los Angeles", "Austin",
                "Seattle", "Boston", "Denver", "Chicago",
            ]},
        ],
        "open_to_relocation": True,
        "open_to_remote": True,
        "open_to_freelance": True,
        "open_to_contract": True,
    },

    # ── visa / work authorization ─────────────────────────────
    #    Fixes the US-only sponsorship assumption from the original
    "visa": {
        "citizenship": "AU",
        "us_eligible_visas": ["E-3"],  # AU-specific US work visa
        "eu_status": "free_trade_deal_2026",
        # AU-EU Free Trade Agreement signed March 2026
        # Innovation Mobility Pathway covers engineers/researchers under 45
        # No employer sponsorship required — self-sponsored mobility visa ~2027 activation
        # Scope: 4-year landmark deal covering digital/tech workers bilaterally
        "uk_status": "requires_sponsorship",
        "au_status": "citizen",
        "ae_status": "visa_on_arrival_available",   # UAE — AU passport holders
        "il_status": "visa_on_arrival_available",   # Israel — AU passport
        "sg_status": "visa_on_arrival_available",   # Singapore
        "latam_status": "tourist_visa_work_remotely", # Most LATAM countries
        # when primary_market=GLOBAL, flag sponsorship requirements but don't auto-exclude
        "sponsorship_keywords_positive": [
            "e-3", "e3", "visa sponsorship", "sponsor visa",
            "will sponsor", "sponsorship available", "visa support",
            "relocation support", "relocation package",
        ],
        "sponsorship_keywords_negative": [
            "no sponsorship", "no visa", "must be authorized",
            "us citizens only", "permanent resident required",
            "security clearance required",
        ],
    },

    # ── compensation (optional, for filtering) ────────────────
    "compensation": {
        "min_salary_aud": 90_000,
        "min_salary_usd": 70_000,
        "min_hourly_freelance_aud": 80,
        "min_hourly_freelance_usd": 60,
        "currency_preference": "AUD",  # display preference
    },

    # ── job description keywords to boost / penalise ──────────
    "keywords": {
        "boost": [
            "react", "typescript", "python", "node", "postgresql",
            "machine learning", "geospatial", "climate", "carbon",
            "sustainability", "ios", "swift", "shopify", "startup",
            "remote", "flexible", "contract", "freelance",
            "fast-paced", "small team", "greenfield",
            "data pipeline", "full stack", "api",
        ],
        "penalise": [
            # seniority / scope
            "10+ years", "15+ years", "20+ years",
            "director", "vp", "chief", "principal",
            # legacy/irrelevant stacks
            "mainframe", "cobol", "sap", "oracle erp",
            "abap", "salesforce", "servicenow",
            "unity", "game developer",
            "php",
            # security / clearance
            "security clearance", "top secret", "sc cleared", "dv cleared",
            "copilot m365",
            # internships / trainee (non-English terms also)
            "internship", "apprenticeship", "trainee",
            "stage", "alternance", "stagiaire",
            "praktikum", "werkstudent",
            "unpaid", "stipend",
            # roles clearly outside Harvey's domain
            "special agent",
        ],
    },

    # ── hard title-exclude (checked BEFORE description fetch to save requests) ──
    "hard_exclude_title_keywords": [
        "abap", "salesforce", "servicenow", "game developer", "unity",
        "special agent", "security clearance", "sc cleared",
        "stage ", "alternance", "praktikum", "werkstudent", "stagiaire",
        "internship", "apprenticeship", "trainee",
        "designer",
        "mechanical engineer", "electrical engineer", "civil engineer",
        "structural engineer", "chemical engineer",
        "qa tester", "test engineer", "qa engineer",
        "scrum master", "project manager", "product owner",
        "data entry", "customer support", "customer service",
        "sales representative", "account executive", "account manager",
        "recruiter", "hr manager", "hr generalist",
    ],

    # ── auto-apply preferences ────────────────────────────────
    "auto_apply": {
        "enabled": False,  # alerts-only by default, as the plan recommends
        "min_score_for_auto_apply": 0.85,
        "require_human_review_above": 0.75,
        "cover_letter_style": "concise_technical",
    },

    # ── alerting thresholds (0–100 scale, matches fit_score output) ──────
    "alert_thresholds": {
        "immediate": 78,   # SMS/push for strong matches (~top 2-3% per run)
        "digest": 62,      # include in daily email digest (~top 10%)
        "store_only": 40,  # save to DB but don't alert; drop anything below this
    },

    # ── culture / environment fit (for LLM gate scoring) ─────
    "culture_signals": {
        "boost": [
            "small team", "startup", "seed", "series a", "series b",
            "greenfield", "0 to 1", "zero to one", "founding engineer",
            "hands-on", "ownership", "autonomy", "impact",
            "sustainability", "climate", "environment", "ecology",
            "open source", "maker", "builder",
            "remote-first", "async", "distributed team",
            "design-minded", "product engineering",
            "digital nomad", "visa sponsorship", "global team",
            "work from anywhere", "international",
        ],
        "penalise": [
            "enterprise sales", "fortune 500 client",
            "waterfall", "itil", "bureaucratic",
            "must work on-site 5 days",
            "large cross-functional org", "matrix organization",
            "big 4 consulting", "management consulting",
        ],
    },
}

# ── User profile MERGE ─────────────────────────────────────────────────────────
# If config/user_profile.json exists (created by the /setup onboarding wizard),
# we MERGE it over the rich defaults above — we do NOT replace wholesale.
#
# Why merge: the setup wizard's Kimi extraction produces a thin profile (identity,
# summary, experience, a few roles/skills/industries, search_terms). It does NOT
# include the scoring-critical config — seniority targeting, culture_signals,
# keyword boost/penalise lists, hard_exclude_title_keywords, the visa sponsorship
# keyword sets, or the tiered location regions. A full replace silently drops all
# of that and cripples scoring (role=0 for ML titles, culture flat at 50, empty
# visa keyword lists, no title pre-filter). Merging keeps the user's real, current
# data while falling back to the rich defaults for everything they didn't provide.
#
# Merge rules:
#   • roles / industries  → UNION (defaults first to preserve ML-first ordering,
#                           then any user additions not already present)
#   • skills              → per-category UNION
#   • location (string)   → keep the rich location dict (tiers/regions) and record
#                           the user's stated city as location["current"]
#   • everything else     → user value wins (name, email, summary, experience,
#                           search_terms, alert_thresholds, min_salary, …)
import json as _json, os as _os
_user_profile_path = _os.path.join(
    _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))),
    "config", "user_profile.json"
)


def _merge_user_profile(default: dict, user: dict) -> dict:
    merged = dict(default)

    def _union_list(base, extra):
        out, seen = [], set()
        for item in list(base) + list(extra):
            key = item.lower() if isinstance(item, str) else id(item)
            if key not in seen:
                seen.add(key)
                out.append(item)
        return out

    for k, v in user.items():
        if k in ("roles", "industries") and isinstance(v, list):
            merged[k] = _union_list(default.get(k, []), v)
        elif k == "skills" and isinstance(v, dict):
            ms = {cat: list(lst) for cat, lst in default.get("skills", {}).items()}
            for cat, lst in v.items():
                ms[cat] = _union_list(ms.get(cat, []), lst or [])
            merged[k] = ms
        elif k == "location" and isinstance(v, str) and isinstance(default.get("location"), dict):
            loc = dict(default["location"])
            loc["current"] = v
            merged[k] = loc
        elif v not in (None, "", [], {}):
            merged[k] = v  # user value wins when they actually provided one
    return merged


if _os.path.exists(_user_profile_path):
    try:
        with open(_user_profile_path, encoding="utf-8") as _f:
            _user_profile = _json.load(_f)
        HARVEY_PROFILE = _merge_user_profile(HARVEY_PROFILE, _user_profile)
    except Exception:
        pass  # silently keep the rich default if the file is missing/corrupt

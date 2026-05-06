"""
AI-powered job scoring using Kimi K2.5 (Moonshot AI).
Replaces sentence-transformers with a proper LLM that understands context deeply.

Kimi K2.5 is OpenAI-compatible — base URL: https://api.moonshot.cn/v1
Model: moonshot-v1-8k  (fast + cheap for scoring)
"""
import os
import sys
import json
import time
from typing import Dict, Any, Tuple
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# ── Kimi / Moonshot client setup ──────────────────────────────────────────────
try:
    from openai import OpenAI
    KIMI_API_KEY = os.getenv("KIMI_API_KEY", "")
    if not KIMI_API_KEY:
        raise ValueError("KIMI_API_KEY not set in .env")

    _kimi_client = OpenAI(
        api_key=KIMI_API_KEY,
        base_url="https://api.moonshot.ai/v1",
    )
    KIMI_AVAILABLE = True
    print("✓ Kimi K2.5 (api.moonshot.ai) AI scorer ready")
except Exception as e:
    _kimi_client = None
    KIMI_AVAILABLE = False
    print(f"✗ Kimi AI scorer not available: {e}")

# ── Load Harvey's profile ─────────────────────────────────────────────────────
HARVEY_PROFILE = None
try:
    import importlib.util
    _profile_path = os.path.abspath(
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "profile.py")
    )
    _spec = importlib.util.spec_from_file_location("harvey_profile", _profile_path)
    if _spec and _spec.loader:
        _mod = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_mod)  # type: ignore[arg-type]
        HARVEY_PROFILE = _mod.HARVEY_PROFILE
        print(f"✓ Profile loaded from {_profile_path}")
except Exception as e:
    print(f"✗ Could not load profile: {e}")

if HARVEY_PROFILE is None:
    HARVEY_PROFILE = {
        "name": "Harvey J. Houlahan",
        "summary": "ML Engineer at ArborMeta (geospatial, carbon sequestration). Also contracting at Step One Clothing. Previously iOS Engineer at FibreTrace, AI/Backend at Friday Technologies, intern at AEMO.",
        "skills": {"ai_ml": ["Python", "ML", "PyTorch", "React", "MapLibre", "PostgreSQL"]},
        "industries": ["Climate Tech", "Geospatial", "Carbon Markets", "iOS"],
        "roles": ["ML Engineer", "Software Engineer", "iOS Engineer"],
        "achievements": [],
    }
    print("⚠ Using fallback profile")


# ── Profile summary (built once, reused per run) ───────────────────────────────
def _build_profile_summary() -> str:
    if not HARVEY_PROFILE:
        return "ML Engineer with Python, React, geospatial, and iOS experience."

    lines = []
    lines.append(f"Candidate: {HARVEY_PROFILE.get('name', 'Harvey J. Houlahan')}")

    # Handle location as dict (new profile) or string (legacy)
    loc = HARVEY_PROFILE.get('location', 'Byron Bay, NSW, Australia')
    if isinstance(loc, dict):
        lines.append(f"Location: {loc.get('current', 'Byron Bay, NSW, Australia')}")
    else:
        lines.append(f"Location: {loc}")

    # Core summary — the primary semantic context for the model
    if HARVEY_PROFILE.get("summary"):
        lines.append(f"\nSummary: {HARVEY_PROFILE['summary']}")

    # Extended context — what makes a role genuinely exciting to Harvey
    if HARVEY_PROFILE.get("extended_context"):
        lines.append(f"\nPersonal context (use this to score culture/mission fit): {HARVEY_PROFILE['extended_context']}")

    # Current + recent experience
    if HARVEY_PROFILE.get("experience"):
        lines.append("\nExperience (most recent first):")
        for exp in HARVEY_PROFILE["experience"][:4]:
            lines.append(f"  • {exp['title']} at {exp['company']} ({exp.get('period','')}) — {exp['location']}")
            for b in exp.get("bullets", [])[:2]:
                lines.append(f"      {b[:120]}")

    # Key skills — flatten core + strong (top 40)
    if HARVEY_PROFILE.get("skills"):
        all_skills: list = []
        skills_cfg = HARVEY_PROFILE["skills"]
        if isinstance(skills_cfg, dict):
            for cat_skills in skills_cfg.values():
                all_skills.extend(cat_skills)
        lines.append(f"\nSkills: {', '.join(all_skills[:40])}")

    # Industries
    if HARVEY_PROFILE.get("industries"):
        lines.append(f"Industries: {', '.join(HARVEY_PROFILE['industries'][:20])}")

    # Achievements (if present)
    if HARVEY_PROFILE.get("achievements"):
        lines.append("\nKey achievements:")
        for a in HARVEY_PROFILE["achievements"][:4]:
            lines.append(f"  • {a[:140]}")

    # Culture signals — what to boost / penalise beyond tech keywords
    culture = HARVEY_PROFILE.get("culture_signals", {})
    if culture.get("boost"):
        lines.append(f"\nEnvironment/culture boosts (score higher if present): {', '.join(culture['boost'][:15])}")
    if culture.get("penalise"):
        lines.append(f"Environment/culture negatives (score lower if present): {', '.join(culture['penalise'][:8])}")

    return "\n".join(lines)


_PROFILE_SUMMARY = _build_profile_summary()

# System prompt — sent once per API call (cached by Kimi context caching)
_SYSTEM_PROMPT = f"""You are an expert technical recruiter evaluating job fit for a specific candidate.

CANDIDATE PROFILE:
{_PROFILE_SUMMARY}

Your job is to score how well a given job posting fits this candidate on a scale of 0–100.

Scoring criteria:
- 85–100: Near-perfect match — role, tech stack, domain, seniority all align with candidate's current work
- 70–84: Strong match — most dimensions align, minor gaps
- 55–69: Good match — solid transferable skills, some domain stretch
- 40–54: Moderate match — relevant background but meaningful gaps
- 25–39: Weak match — limited overlap, significant upskilling needed
- 0–24: Poor match — wrong domain, wrong seniority, or excluded (e.g. no sponsorship for US role)

IMPORTANT rules:
- The candidate is an Australian citizen based in Byron Bay. For AU/EU/CA/SG/Remote roles, visa is NOT an issue.
- For US roles: E-3 visa applies (Australian-only). "No sponsorship" = score 0–15 maximum.
- Do NOT penalise for "Senior" title — candidate has ~4 years and works as ML Engineer already.
- DO penalise heavily for Engineering Manager / Director / VP / Staff / Principal (not what candidate wants).
- The candidate's CURRENT role is ML Engineer at ArborMeta (geospatial + carbon). Roles in that space score highest.

Respond ONLY with a valid JSON object — no markdown, no explanation outside the JSON:
{{
  "score": <integer 0-100>,
  "confidence": "<high|medium|low>",
  "top_matches": ["<skill or domain match 1>", "<skill or domain match 2>", "<skill or domain match 3>"],
  "gaps": ["<gap 1>", "<gap 2>"],
  "reasoning": "<one sentence explaining the score>"
}}"""


class AIJobScorer:
    """
    AI job scorer backed by Kimi K2.5 (Moonshot AI).
    Falls back to 0.0 with is_fallback=True when the API is unavailable, so the
    engine can detect the failure and redistribute weights to keyword components
    instead of injecting a fake neutral 50 that compresses the score distribution.
    """

    def __init__(self):
        self.available = KIMI_AVAILABLE
        self._cache: Dict[str, Tuple[float, Dict]] = {}  # url/title → (score, details)
        if self.available:
            print("✓ AI scorer initialized — using kimi-k2.5 (api.moonshot.ai)")
        else:
            print("⚠ AI scorer unavailable — weight redistribution will activate")

    def score_job_ai(self, job_data: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
        """
        Score a job posting using Kimi K2.5.
        Returns (score_0_to_100, details_dict).
        """
        if not self.available or not _kimi_client:
            return 0.0, {"method": "kimi_unavailable", "is_fallback": True}

        title = job_data.get("title", "Unknown")
        company = job_data.get("company", "Unknown")
        location = job_data.get("location", "")
        description = (job_data.get("description") or "").strip()

        if len(description) < 40:
            return 0.0, {"method": "insufficient_text", "is_fallback": True}

        # Cache by title+company (avoids re-scoring duplicates in same run)
        cache_key = f"{title}|{company}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Truncate very long descriptions to keep costs low (~3k chars is plenty)
        description_trimmed = description[:3000]

        user_message = (
            f"Job title: {title}\n"
            f"Company: {company}\n"
            f"Location: {location}\n\n"
            f"Job description:\n{description_trimmed}"
        )

        raw = ""
        for attempt in range(2):  # 1 retry on failure
            try:
                response = _kimi_client.chat.completions.create(
                    model="moonshot-v1-8k",
                    messages=[
                        {"role": "system", "content": _SYSTEM_PROMPT},
                        {"role": "user", "content": user_message},
                    ],
                    temperature=0.3,
                    max_tokens=400,
                )
                raw = response.choices[0].message.content or ""
                raw = raw.strip()

                # Strip markdown fences if present
                if raw.startswith("```"):
                    raw = raw.split("```")[1]
                    if raw.startswith("json"):
                        raw = raw[4:]
                raw = raw.strip()

                parsed = json.loads(raw)
                score = float(max(0, min(100, parsed.get("score", 50))))
                details = {
                    "method": "kimi_k2.5",
                    "model": "kimi-k2.5",
                    "is_fallback": False,
                    "confidence": parsed.get("confidence", "medium"),
                    "top_matches": parsed.get("top_matches", []),
                    "gaps": parsed.get("gaps", []),
                    "ai_reasoning": parsed.get("reasoning", ""),
                }
                self._cache[cache_key] = (score, details)
                return score, details

            except json.JSONDecodeError as e:
                logger.warning(f"Kimi returned non-JSON (attempt {attempt+1}): {e} — raw: {raw[:200]}")
                if attempt == 0:
                    time.sleep(1)
                    continue
                return 0.0, {"method": "kimi_parse_error", "is_fallback": True, "raw": raw[:200]}
            except Exception as e:
                logger.warning(f"Kimi API error (attempt {attempt+1}): {e}")
                if attempt == 0:
                    time.sleep(2)
                    continue
                return 0.0, {"method": "kimi_api_error", "is_fallback": True, "error": str(e)}

        return 0.0, {"method": "kimi_failed", "is_fallback": True}


# ── Global singleton ──────────────────────────────────────────────────────────
_ai_scorer_instance = None


def get_ai_scorer() -> AIJobScorer:
    global _ai_scorer_instance
    if _ai_scorer_instance is None:
        _ai_scorer_instance = AIJobScorer()
    return _ai_scorer_instance


# ── Quick test ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    scorer = AIJobScorer()

    jobs = [
        {
            "title": "ML Engineer",
            "company": "Pachama",
            "location": "Sydney NSW",
            "description": (
                "Build geospatial ML pipelines for carbon sequestration mapping. "
                "React, MapLibre GL JS, PostgreSQL, Python, PMTiles, carbon credits, "
                "ecological research. 2–4 years experience required."
            ),
        },
        {
            "title": "iOS Engineer",
            "company": "Canva",
            "location": "Remote",
            "description": (
                "SwiftUI, CoreML, App Clip, NFC, offline-first iOS app. "
                "2–4 years Swift experience."
            ),
        },
        {
            "title": "Engineering Manager",
            "company": "Atlassian",
            "location": "Sydney NSW",
            "description": "Lead a team of 6 engineers. Python backend, Agile. 5+ years.",
        },
    ]

    for job in jobs:
        score, details = scorer.score_job_ai(job)
        print(f"\n{job['title']} @ {job['company']} ({job['location']})")
        print(f"  Score: {score:.0f}/100  confidence={details.get('confidence')}")
        print(f"  Matches: {details.get('top_matches')}")
        print(f"  Reasoning: {details.get('ai_reasoning')}")



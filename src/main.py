"""
Main orchestration - brings everything together
"""
import os
import sys
import re
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from loguru import logger
from dotenv import load_dotenv

# Disable tokenizers parallelism warning
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# ── Language detection (graceful fallback if not installed) ───────────────────
try:
    from langdetect import detect as _detect_lang
    _LANGDETECT_AVAILABLE = True
except ImportError:
    _LANGDETECT_AVAILABLE = False
    logger.warning("langdetect not installed — language filter disabled. pip install langdetect")


def _is_english(text: str) -> bool:
    """Return True if text appears to be English. Fail-open on any error."""
    if not _LANGDETECT_AVAILABLE or not text or len(text.strip()) < 20:
        return True
    try:
        if _LANGDETECT_AVAILABLE:
            from langdetect import detect as _dl
            return _dl(text[:300]) == 'en'
        return True
    except Exception:
        return True  # fail open — don't drop a job due to detection error


def _estimate_posted_age_days(text: str) -> "float | None":
    """
    Best-effort age (in days) of a job posting from its free-text `posted_date`.

    Scrapers return wildly different formats: ISO dates ("2026-06-15"), relative
    phrases ("2 days ago", "3 weeks ago", "yesterday"), vague labels ("Recently",
    "Just posted"), and "30+ days ago". Returns the estimated age in days, or
    None when the text gives no usable signal (caller should then KEEP the job —
    fail-open, never drop a job just because its date is unparseable).
    """
    if not text:
        return None
    t = str(text).strip().lower()
    if not t:
        return None

    # Vague-but-fresh labels → treat as brand new
    if any(k in t for k in ('just posted', 'just now', 'today', 'recently',
                            'new', 'moments ago', 'hours ago', 'hour ago',
                            'minute ago', 'minutes ago')):
        return 0.0
    if 'yesterday' in t:
        return 1.0

    # Relative phrases: "2 days ago", "3 weeks ago", "1 month ago", "30+ days ago"
    m = re.search(r'(\d+)\s*\+?\s*(day|week|month|year|hour|minute)s?', t)
    if m:
        n = int(m.group(1))
        unit = m.group(2)
        mult = {'minute': 1 / 1440, 'hour': 1 / 24, 'day': 1,
                'week': 7, 'month': 30, 'year': 365}[unit]
        return n * mult

    # ISO / common date formats
    iso = t.replace('z', '').strip()
    for fmt in (None, '%Y-%m-%d', '%Y/%m/%d', '%d %b %Y', '%d %B %Y', '%b %d, %Y', '%B %d, %Y'):
        try:
            if fmt is None:
                dt = datetime.fromisoformat(iso[:19]) if 'T' in iso or '-' in iso else None
                if dt is None:
                    continue
            else:
                dt = datetime.strptime(t, fmt)
            if dt.tzinfo is not None:
                dt = dt.replace(tzinfo=None)
            return max(0.0, (datetime.utcnow() - dt).total_seconds() / 86400.0)
        except (ValueError, TypeError):
            continue

    return None


from src.database.models import Database
from src.profile import HARVEY_PROFILE
from src.scoring.engine import JobScorer
from src.scrapers.linkedin import LinkedInScraper
from src.scrapers.builtin import BuiltInNYCScraper
from src.scrapers.seek import SeekScraper
from src.scrapers.eurotoptech import EuroTopTechScraper
from src.scrapers.berlinstartupjobs import BerlinStartupJobsScraper
from src.scrapers.relocateme import RelocateMeScraper
from src.scrapers.getonboard import GetOnBrdScraper
from src.scrapers.zerotaxjobs import ZeroTaxJobsScraper
from src.scrapers.bayt import BaytScraper
from src.scrapers.remoteok import RemoteOKScraper
from src.scrapers.weworkremotely import WeWorkRemotelyScraper
from src.alerts.notifications import AlertManager
from src.applying.applicator import JobApplicator
from src.config_loader import load_scraping_locations, get_active_countries, should_activate_job_board, get_active_regions


class JobHunter:
    """Main application orchestrator"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        # Load environment variables
        load_dotenv()
        
        # Initialize components
        self.db = Database()
        self.db.create_tables()
        
        self.scorer = JobScorer()
        self.alert_manager = AlertManager(db=self.db)
        self.applicator = JobApplicator()  # Auto-apply for high-scoring jobs
        
        # Initialize scrapers based on active countries
        self.scrapers = {}
        
        # LinkedIn - works globally
        if should_activate_job_board('linkedin'):
            self.scrapers['linkedin'] = LinkedInScraper()
            logger.info("LinkedIn scraper activated")
        
        # BuiltIn - US only
        if should_activate_job_board('builtin'):
            self.scrapers['builtin'] = BuiltInNYCScraper()
            logger.info("BuiltIn scraper activated for US locations")

        # Seek - Australia & NZ (DISABLED: Cloudflare blocking all requests)
        # if should_activate_job_board('seek'):
        #     self.scrapers['seek'] = SeekScraper()
        #     logger.info("Seek scraper activated for Australian locations")

        # --- New regional scrapers ---
        active_regions = get_active_regions()

        # Europe scrapers
        if 'Europe' in active_regions:
            try:
                self.scrapers['eurotoptech'] = EuroTopTechScraper()
                logger.info("EuroTopTech scraper activated")
            except Exception as exc:
                logger.warning(f"EuroTopTech scraper failed to init: {exc}")
            try:
                self.scrapers['berlinstartupjobs'] = BerlinStartupJobsScraper()
                logger.info("BerlinStartupJobs scraper activated")
            except Exception as exc:
                logger.warning(f"BerlinStartupJobs scraper failed to init: {exc}")
            try:
                self.scrapers['relocateme'] = RelocateMeScraper()
                logger.info("RelocateMe scraper activated")
            except Exception as exc:
                logger.warning(f"RelocateMe scraper failed to init: {exc}")

        # Latin America scrapers
        if 'Latin America' in active_regions:
            try:
                self.scrapers['getonboard'] = GetOnBrdScraper()
                logger.info("GetOnBrd scraper activated")
            except Exception as exc:
                logger.warning(f"GetOnBrd scraper failed to init: {exc}")

        # Middle East scrapers
        if 'Middle East' in active_regions:
            try:
                self.scrapers['zerotaxjobs'] = ZeroTaxJobsScraper()
                logger.info("ZeroTaxJobs scraper activated")
            except Exception as exc:
                logger.warning(f"ZeroTaxJobs scraper failed to init: {exc}")
            try:
                self.scrapers['bayt'] = BaytScraper()
                logger.info("Bayt scraper activated")
            except Exception as exc:
                logger.warning(f"Bayt scraper failed to init: {exc}")

        # Global remote scrapers — always active
        try:
            self.scrapers['remoteok'] = RemoteOKScraper()
            logger.info("RemoteOK scraper activated")
        except Exception as exc:
            logger.warning(f"RemoteOK scraper failed to init: {exc}")
        try:
            self.scrapers['weworkremotely'] = WeWorkRemotelyScraper()
            logger.info("WeWorkRemotely scraper activated")
        except Exception as exc:
            logger.warning(f"WeWorkRemotely scraper failed to init: {exc}")
        
        # Configuration
        self.config = config or self._default_config()
        
        # Log active locations
        active_locations = self.config.get('locations', [])
        logger.info(f"Active scraping locations ({len(active_locations)}): {', '.join(active_locations)}")
        
        # Log active countries
        active_countries = get_active_countries()
        logger.info(f"Active countries: {', '.join(active_countries)}")
        
        logger.info("JobHunter initialized")
    
    def _default_config(self) -> Dict[str, Any]:
        """Configuration driven by the user profile (config/user_profile.json if present)."""
        return {
            'thresholds': {
                'immediate': 78,
                'digest': 62,
                'store_only': 40,
            },
            'auto_apply': {
                'enabled': False,  # CVs are generated on-demand only (via dashboard button)
                'tier_1_score': 60.0,
                'tier_2_score': 45.0,
                'tier_3_score': 40.0,
                'max_per_run': 50
            },
            'search_terms': self._build_search_terms(),
            'locations': load_scraping_locations(),
            'exclude_keywords': [
                'unpaid', 'volunteer', 'contractor only', 'contract only',
                'no benefits', 'commission only', 'equity only', 'intern', 'internship'
            ],
            'max_jobs_per_source': 50
        }

    def _build_search_terms(self) -> Dict[str, List[str]]:
        """
        Build CLEAN, role-only search-term lists from the user profile.

        Location is ALWAYS passed to scrapers as a separate parameter, so terms
        here must be pure role keywords. We deliberately do NOT append location
        strings (the old code produced junk like "Software Engineer (US)" and
        "Backend Engineer Anywhere", which LinkedIn returns zero results for).

        Terms are ML/AI-first to match the candidate's target focus, then general
        software roles. Falls back to generic terms if no profile is saved yet.
        """
        # Try to load search terms saved by the setup wizard
        profile_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'config', 'user_profile.json'
        )
        raw_terms: List[str] = []
        if os.path.exists(profile_path):
            try:
                with open(profile_path, encoding='utf-8') as fh:
                    prof = json.load(fh)
                raw_terms = prof.get('search_terms') or prof.get('roles') or []
            except Exception:
                pass

        if not raw_terms:
            # ML/AI-first defaults for a junior ML engineer; general SWE as a net.
            raw_terms = HARVEY_PROFILE.get('roles', []) or [
                'Machine Learning Engineer', 'ML Engineer', 'AI Engineer',
                'Data Engineer', 'MLOps Engineer', 'Python Developer',
                'Software Engineer', 'Backend Engineer', 'Full Stack Engineer',
            ]

        # Strip any accidental location fragments and dedupe, preserving order.
        seen: set = set()
        clean_terms: List[str] = []
        for t in raw_terms:
            t = re.sub(r'\s*\([^)]*\)\s*', ' ', t).strip()  # drop "(US)", "(Global)"
            t = re.sub(r'\s+', ' ', t)
            key = t.lower()
            if t and key not in seen:
                seen.add(key)
                clean_terms.append(t)

        # ML/AI roles bubble to the front so they're searched first under the
        # per-location term cap (LINKEDIN_TERMS_PER_LOCATION).
        ml_tokens = ('machine learning', 'ml ', ' ml', 'ai ', ' ai', 'mlops',
                     'data engineer', 'data scientist', 'research engineer', 'nlp')
        ml_first = sorted(
            clean_terms,
            key=lambda t: 0 if any(tok in f' {t.lower()} ' for tok in ml_tokens) else 1
        )

        return {
            'linkedin': ml_first,
            'builtin': [t.lower() for t in ml_first],
            'seek': ml_first,
        }

    def run(self) -> Dict[str, Any]:
        """
        Main execution flow:
        1. Scrape jobs from all sources
        2. Score each job
        3. Store in database
        4. Send alerts for high matches
        """
        logger.info("Starting job hunt cycle...")
        start_time = datetime.now()
        
        stats: Dict[str, Any] = {
            'jobs_found': 0,
            'jobs_new': 0,
            'jobs_duplicate': 0,
            'high_matches': 0,
            'alerts_sent': 0
        }
        
        try:
            # 1. Scrape jobs
            all_jobs = self._scrape_all_sources()
            stats['jobs_found'] = len(all_jobs)
            logger.info(f"Scraped {stats['jobs_found']} total jobs from all sources (before deduplication)")
            
            # 2. Filter out duplicates BEFORE fetching descriptions (saves time!)
            logger.info("Filtering duplicates before fetching descriptions...")
            # Recency: drop anything older than MAX_JOB_AGE_DAYS (configurable).
            # Default 14 days — for an active job hunt, fresh postings convert best.
            # Uses a robust relative-date parser; jobs with an UNKNOWN date are KEPT
            # (fail-open) so we never lose a good role to a missing/odd date string.
            _MAX_JOB_AGE_DAYS = float(os.getenv("MAX_JOB_AGE_DAYS", "14"))
            _stale_dropped = 0
            new_job_candidates = []
            for job_data in all_jobs:
                # Staleness check via robust parser (handles "2 weeks ago", ISO, etc.)
                posted_raw = job_data.get('posted_date') or job_data.get('date') or ''
                age_days = _estimate_posted_age_days(posted_raw)
                if age_days is not None and age_days > _MAX_JOB_AGE_DAYS:
                    logger.debug(f"Skipping stale job (~{age_days:.0f}d, '{posted_raw}'): {job_data.get('title')}")
                    stats['jobs_duplicate'] += 1
                    _stale_dropped += 1
                    continue

                source_id = job_data.get('source_id')
                url = job_data.get('url')
                title = job_data.get('title', '').lower()
                company = job_data.get('company')
                location = job_data.get('location')
                description = job_data.get('description', '').lower()
                
                # NEGATIVE KEYWORD FILTERING - skip time-wasters early
                combined_text = f"{title} {description}"
                exclude_keywords = self.config.get('exclude_keywords', [])
                should_skip = False
                for keyword in exclude_keywords:
                    if keyword.lower() in combined_text:
                        logger.debug(f"Skipping job due to keyword '{keyword}': {job_data.get('title')}")
                        stats['jobs_duplicate'] += 1  # Count as filtered
                        should_skip = True
                        break
                
                if should_skip:
                    continue
                
                # Check for duplicates by URL, source_id, AND company+title+location (catches reposts)
                if self.db.job_exists(
                    url=url or "",
                    source_id=source_id or "",
                    title=job_data.get('title') or "",
                    company=company or "",
                    location=location or ""
                ):
                    stats['jobs_duplicate'] += 1
                    continue
                
                # This is a new job - keep it for processing
                new_job_candidates.append(job_data)
            
            logger.info(f"✓ After deduplication: {len(new_job_candidates)} NEW jobs to process, "
                        f"{stats['jobs_duplicate']} duplicates/stale skipped "
                        f"({_stale_dropped} dropped as older than {_MAX_JOB_AGE_DAYS:.0f} days)")

            # 2b. Hard title-exclude: drop clearly irrelevant roles before
            #     fetching descriptions (saves HTTP requests)
            hard_excl_kws = [k.lower() for k in HARVEY_PROFILE.get("hard_exclude_title_keywords", [])]
            if hard_excl_kws:
                before = len(new_job_candidates)
                filtered = []
                for jd in new_job_candidates:
                    jt = (jd.get('title') or '').lower()
                    hit = next((kw for kw in hard_excl_kws if kw in jt), None)
                    if hit:
                        logger.debug(f"Hard-excluded (title): '{jd.get('title')}' matched '{hit}'")
                    else:
                        filtered.append(jd)
                new_job_candidates = filtered
                dropped = before - len(new_job_candidates)
                if dropped:
                    logger.info(f"Hard title-exclude dropped {dropped} jobs before description fetch")
            
            # 2c. CHEAP TITLE PRE-FILTER (title + company only — no HTTP, no AI).
            #     Drops obviously-irrelevant roles BEFORE the expensive description
            #     fetch and AI scoring. This is the single biggest speed win:
            #     previously every candidate got a full description fetch (~3s on
            #     LinkedIn) and a Kimi call even when the title was clearly off-target.
            prefilter_floor = float(os.getenv("TITLE_PREFILTER_FLOOR", "0.15"))
            before = len(new_job_candidates)
            kept = []
            for jd in new_job_candidates:
                if self.scorer.score_title_only(jd) >= prefilter_floor:
                    kept.append(jd)
                else:
                    logger.debug(f"Title pre-filter dropped: {jd.get('title')} @ {jd.get('company')}")
            new_job_candidates = kept
            prefiltered = before - len(new_job_candidates)
            if prefiltered:
                logger.info(f"Title pre-filter dropped {prefiltered} low-relevance jobs "
                            f"before fetch/score ({len(new_job_candidates)} remain)")

            # 3. Fetch descriptions for the survivors — IN PARALLEL (was sequential,
            #    the main cause of multi-hour runs). Only jobs missing a substantial
            #    description and whose source supports single-job fetch are fetched.
            max_fetch_workers = int(os.getenv("FETCH_WORKERS", "8"))
            _scraper_for = {
                'linkedin': 'linkedin', 'builtin_nyc': 'builtin', 'yc_jobs': 'yc_jobs',
            }

            def _fetch_one(job_data: Dict[str, Any]) -> Dict[str, Any]:
                if len(job_data.get('description') or '') >= 200:
                    return job_data  # already have a usable description
                scraper = self.scrapers.get(_scraper_for.get(job_data.get('source') or '', ''))
                url = job_data.get('url')
                if scraper and url and hasattr(scraper, 'fetch_single_job_description'):
                    try:
                        job_data['description'] = scraper.fetch_single_job_description(url) or ''
                    except Exception as e:
                        logger.debug(f"Error fetching description for {url}: {e}")
                        job_data.setdefault('description', '')
                return job_data

            logger.info(f"Fetching descriptions for {len(new_job_candidates)} jobs "
                        f"({max_fetch_workers} workers)...")
            jobs_with_descriptions: List[Dict[str, Any]] = []
            from concurrent.futures import ThreadPoolExecutor, as_completed
            with ThreadPoolExecutor(max_workers=max_fetch_workers) as pool:
                futures = [pool.submit(_fetch_one, jd) for jd in new_job_candidates]
                for n, fut in enumerate(as_completed(futures), 1):
                    try:
                        jobs_with_descriptions.append(fut.result())
                    except Exception as e:
                        logger.debug(f"Fetch worker error: {e}")
                    if n % 50 == 0:
                        logger.info(f"  ...fetched {n}/{len(new_job_candidates)}")
            logger.info(f"Fetched descriptions for {len(jobs_with_descriptions)} jobs")

            # 4. Score — IN PARALLEL — then save sequentially on the main thread
            #    (SQLite writes are not thread-safe; scoring/AI calls are I/O-bound).
            lang_dropped = 0
            to_score: List[Dict[str, Any]] = []
            for job_data in jobs_with_descriptions:
                lang_text = f"{job_data.get('title', '')} {(job_data.get('description') or '')[:300]}"
                if not _is_english(lang_text):
                    logger.debug(f"Dropped (non-English): {job_data.get('title')} @ {job_data.get('company')}")
                    lang_dropped += 1
                else:
                    to_score.append(job_data)

            max_score_workers = int(os.getenv("SCORE_WORKERS", "6"))
            logger.info(f"Scoring {len(to_score)} jobs ({max_score_workers} workers)...")
            scored: List[tuple] = []  # (job_data, score_result)
            with ThreadPoolExecutor(max_workers=max_score_workers) as pool:
                fut_map = {pool.submit(self.scorer.score_job, jd): jd for jd in to_score}
                for fut in as_completed(fut_map):
                    jd = fut_map[fut]
                    try:
                        scored.append((jd, fut.result()))
                    except Exception as e:
                        logger.error(f"Scoring error for {jd.get('title')}: {e}")

            # Save sequentially (highest score first so DB ordering is sensible)
            new_jobs = []
            store_floor = self.config['thresholds'].get('store_only', 50)
            scored.sort(key=lambda x: x[1].get('fit_score', 0), reverse=True)
            for job_data, score_result in scored:
                job_score = score_result['fit_score']
                if job_score < store_floor:
                    logger.debug(
                        f"Dropped (below floor {store_floor}): "
                        f"{job_data.get('title')} @ {job_data.get('company')} (score={job_score})"
                    )
                    stats['jobs_duplicate'] += 1  # reuse filtered counter
                    continue

                bd = score_result.get('breakdown', {})
                job_record = {
                    **job_data,
                    'fit_score': job_score,
                    'reasoning': score_result['reasoning'],
                    'score_breakdown': bd,
                    'tech_matches': score_result['matches']['tech'],
                    'industry_matches': score_result['matches']['industry'],
                    'role_matches': score_result['matches']['role'],
                    'visa_status': score_result['visa_status'],
                    'visa_keywords_found': score_result['matches'].get('visa_keywords', [])
                }
                try:
                    saved_job = self.db.add_job(job_record)
                    job_record['id'] = saved_job.id
                    new_jobs.append(job_record)
                    stats['jobs_new'] += 1
                except Exception as e:
                    logger.error(f"Error saving job: {e}")

            logger.info(f"Processed {stats['jobs_new']} new jobs ({stats['jobs_duplicate']} duplicates/filtered, {lang_dropped} non-English dropped)")
            
            # 5. Send alerts for high matches
            if new_jobs:
                high_matches = [j for j in new_jobs if j['fit_score'] >= self.config['thresholds']['immediate']]
                stats['high_matches'] = len(high_matches)
                
                alert_stats = self.alert_manager.send_alerts(new_jobs, self.config['thresholds'])
                stats['alerts_sent'] = alert_stats['immediate']
                
                logger.info(f"Found {stats['high_matches']} high-match jobs, sent {stats['alerts_sent']} alerts")
            
            # 6. Auto-apply with TIERED scoring approach
            applications_prepared = []
            if self.config.get('auto_apply', {}).get('enabled', False):
                try:
                    logger.info("Processing jobs for tiered auto-apply...")
                    
                    # Get thresholds for 3 tiers
                    tier_1_score = self.config['auto_apply'].get('tier_1_score', 60.0)
                    tier_2_score = self.config['auto_apply'].get('tier_2_score', 45.0)
                    tier_3_score = self.config['auto_apply'].get('tier_3_score', 40.0)
                    max_per_run = self.config['auto_apply'].get('max_per_run', 50)
                    
                    # Separate jobs into tiers
                    tier_1_jobs = [j for j in new_jobs if j.get('fit_score', 0) >= tier_1_score]
                    tier_2_jobs = [j for j in new_jobs if tier_2_score <= j.get('fit_score', 0) < tier_1_score]
                    tier_3_jobs = [j for j in new_jobs if tier_3_score <= j.get('fit_score', 0) < tier_2_score]
                    
                    # Combine tiers (prioritize high scores, but limit total)
                    eligible_jobs = (tier_1_jobs + tier_2_jobs + tier_3_jobs)[:max_per_run]
                    
                    logger.info(
                        f"Tiered breakdown: Tier 1 (≥{tier_1_score}%): {len(tier_1_jobs)}, "
                        f"Tier 2 ({tier_2_score}-{tier_1_score}%): {len(tier_2_jobs)}, "
                        f"Tier 3 ({tier_3_score}-{tier_2_score}%): {len(tier_3_jobs)}"
                    )
                    
                    if eligible_jobs:
                        logger.info(f"Processing top {len(eligible_jobs)} jobs for auto-apply (max: {max_per_run})")
                        
                        # Prepare score results dict for applicator
                        score_results = {}
                        for job in eligible_jobs:
                            job_key = job.get('url') or job.get('source_id')
                            if job_key:
                                # Determine tier for metadata
                                score = job.get('fit_score', 0)
                                if score >= tier_1_score:
                                    tier = 'tier_1_high_priority'
                                elif score >= tier_2_score:
                                    tier = 'tier_2_medium_priority'
                                else:
                                    tier = 'tier_3_broader_net'
                                
                                score_results[job_key] = {
                                    'fit_score': score,
                                    'tier': tier,
                                    'visa_status': job.get('visa_status', 'none'),
                                    'seniority_ok': True,  # Already filtered during scoring
                                    'location_ok': True,   # Already filtered during scoring
                                    'reasoning': job.get('reasoning', ''),
                                    'tech_matches': job.get('tech_matches', []),
                                    'role_matches': job.get('role_matches', []),
                                    'industry_matches': job.get('industry_matches', [])
                                }
                        
                        # Process applications
                        apply_results = self.applicator.process_jobs(
                            jobs=eligible_jobs,
                            score_results=score_results
                        )
                        
                        stats['cvs_generated'] = apply_results.get('applications_prepared', 0)
                        stats['jobs_skipped'] = apply_results.get('total_jobs', 0) - stats['cvs_generated']
                        applications_prepared = apply_results.get('applications', [])
                        
                        logger.info(
                            f"Auto-apply: Generated {stats['cvs_generated']} CVs, "
                            f"skipped {stats['jobs_skipped']} jobs"
                        )
                    else:
                        logger.info("No jobs with score >= 50% found for auto-apply")
                        stats['cvs_generated'] = 0
                        stats['jobs_skipped'] = 0
                except Exception as e:
                    logger.error(f"Error in auto-apply: {e}")
                    stats['cvs_generated'] = 0
            
            # 7. Email CVs to user if any were generated
            if applications_prepared:
                try:
                    from src.applying.email_sender import ApplicationEmailer
                    
                    # Add total_jobs count to stats for email
                    stats['total_jobs'] = self.db.get_application_stats()['total_jobs']
                    
                    emailer = ApplicationEmailer()
                    email_sent = emailer.send_application_batch(
                        applications=applications_prepared,
                        summary_stats=stats
                    )
                    
                    if email_sent:
                        logger.info(f"✓ Emailed {len(applications_prepared)} CVs to user")
                        stats['email_sent'] = True
                    else:
                        logger.info("CV email disabled or failed")
                        stats['email_sent'] = False
                except Exception as e:
                    logger.error(f"Error sending CV email: {e}")
                    stats['email_sent'] = False
                    stats['jobs_skipped'] = 0
        
        except Exception as e:
            # Catch any errors in the main run loop
            logger.error(f"Error in job hunt cycle: {e}", exc_info=True)
            stats['error'] = str(e)
        
        finally:
            # 8. Log search history (ALWAYS log, even if there were errors)
            try:
                duration = (datetime.now() - start_time).total_seconds()
                total_in_db = self.db.get_application_stats()['total_jobs']
                
                self.db.add_search_history({
                    'source': 'all',
                    'jobs_found': stats['jobs_found'],
                    'jobs_new': stats['jobs_new'],
                    'jobs_duplicate': stats['jobs_duplicate'],
                    'duration_seconds': duration,
                    'success': 'error' not in stats
                })
                
                logger.info("=" * 80)
                logger.info(f"✓ Job hunt cycle complete in {duration:.1f}s")
                logger.info(f"  Scraped: {stats['jobs_found']} jobs from all sources")
                logger.info(f"  New: {stats['jobs_new']} jobs added to database")
                logger.info(f"  Duplicates: {stats['jobs_duplicate']} jobs already in database")
                logger.info(f"  Total in database: {total_in_db} jobs")
                if 'cvs_generated' in stats:
                    logger.info(f"  CVs generated: {stats.get('cvs_generated', 0)} for high-scoring jobs")
                if 'error' in stats:
                    logger.info(f"  ⚠️  Error occurred: {stats['error']}")
                logger.info("=" * 80)
            except Exception as e:
                logger.error(f"Error logging search history: {e}")
        
        return stats
    
    def _scrape_all_sources(self) -> List[Dict[str, Any]]:
        """Scrape jobs with source-specific run strategy for efficiency."""
        all_jobs = []
        seen_job_ids = set()  # Track unique jobs by source_id or URL
        
        locations = self.config.get('locations', ['New York, NY'])  # Default to NYC if not specified

        # Collapse interchangeable remote labels (Remote / Remote (Global) / Anywhere /
        # Freelance all resolve to the same worldwide LinkedIn pass). Keep the first
        # remote label + the first country-tagged remote (e.g. "Remote (US)"), drop the
        # rest so we don't run the identical remote search 5× per run.
        collapsed: List[str] = []
        seen_remote_geo: set = set()
        for loc in locations:
            low = (loc or '').lower()
            is_remote = any(tok in low for tok in
                            ('remote', 'anywhere', 'freelance', 'work from home', 'wfh'))
            if is_remote:
                m = re.search(r'\(([^)]+)\)', low)
                geo_tag = m.group(1).strip() if m else 'global'
                if geo_tag in seen_remote_geo:
                    continue
                seen_remote_geo.add(geo_tag)
            collapsed.append(loc)
        if len(collapsed) != len(locations):
            logger.info(f"Collapsed {len(locations)} locations → {len(collapsed)} "
                        f"(deduped interchangeable remote passes)")
        locations = collapsed

        def _add_jobs(jobs: List[Dict[str, Any]]) -> int:
            """Deduplicate within this scrape run and append unique jobs."""
            unique_jobs_count = 0
            for job in jobs:
                job_id = job.get('source_id') or job.get('url')
                if job_id and job_id not in seen_job_ids:
                    seen_job_ids.add(job_id)
                    all_jobs.append(job)
                    unique_jobs_count += 1
            return unique_jobs_count

        def _safe_source_key(source_name: str, scope: str) -> str:
            normalized = scope.replace(', ', '_').replace(' ', '_')
            return f"{source_name}_{normalized}"

        # Strategy groups:
        # 1) LinkedIn runs per location
        # 2) BuiltIn runs once for all locations (it handles location filtering internally)
        # 3) All other scrapers run once per job hunt (global / region-aware internally)
        per_location_scrapers = {'linkedin'}
        single_run_scrapers = set(self.scrapers.keys()) - per_location_scrapers

        # Run per-location scrapers
        for location in locations:
            logger.info(f"Scraping per-location sources for: {location}")
            for source_name in per_location_scrapers:
                scraper = self.scrapers.get(source_name)
                if not scraper:
                    continue
                try:
                    logger.info(f"  → {source_name} ({location})...")
                    search_terms = self.config['search_terms'].get(source_name, [])
                    jobs = scraper.search_jobs(search_terms, location)
                    unique_jobs_count = _add_jobs(jobs)
                    logger.info(
                        f"    Got {len(jobs)} jobs from {source_name} in {location} ({unique_jobs_count} unique)"
                    )
                    self.db.add_search_history({
                        'source': _safe_source_key(source_name, location),
                        'jobs_found': len(jobs),
                        'success': True
                    })
                except Exception as e:
                    logger.error(f"  ✗ Error scraping {source_name} ({location}): {e}")
                    self.db.add_search_history({
                        'source': _safe_source_key(source_name, location),
                        'jobs_found': 0,
                        'success': False,
                        'errors': str(e)
                    })

        # Run all other scrapers once
        all_locations_str = ", ".join(locations) if locations else "global"
        for source_name in sorted(single_run_scrapers):
            scraper = self.scrapers.get(source_name)
            if not scraper:
                continue
            try:
                logger.info(f"  → {source_name} (single-run across locations)...")
                search_terms = self.config['search_terms'].get(source_name, [])
                jobs = scraper.search_jobs(search_terms, all_locations_str)
                unique_jobs_count = _add_jobs(jobs)
                logger.info(
                    f"    Got {len(jobs)} jobs from {source_name} (single-run) ({unique_jobs_count} unique)"
                )
                self.db.add_search_history({
                    'source': _safe_source_key(source_name, "single_run"),
                    'jobs_found': len(jobs),
                    'success': True
                })
            except Exception as e:
                logger.error(f"  ✗ Error scraping {source_name} (single-run): {e}")
                self.db.add_search_history({
                    'source': _safe_source_key(source_name, "single_run"),
                    'jobs_found': 0,
                    'success': False,
                    'errors': str(e)
                })
        
        logger.info(f"Total jobs scraped across all locations: {len(all_jobs)} unique jobs from {len(seen_job_ids)} total")
        return all_jobs
    
    def get_top_matches(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top matching jobs from database"""
        session = self.db.get_session()
        try:
            from database.models import Job
            jobs = session.query(Job).order_by(Job.fit_score.desc()).limit(limit).all()
            
            return [{
                'id': j.id,
                'title': j.title,
                'company': j.company,
                'fit_score': j.fit_score,
                'url': j.url,
                'reasoning': j.reasoning
            } for j in jobs]
        finally:
            session.close()


def main():
    """Main entry point"""
    # Configure logging
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
        level="INFO"
    )
    logger.add(
        "logs/jobhunter.log",
        rotation="10 MB",
        retention="1 month",
        level="DEBUG"
    )
    
    # Create logs directory
    os.makedirs('logs', exist_ok=True)
    
    # Run the job hunter
    hunter = JobHunter()
    stats = hunter.run()
    
    # Print summary
    print("\n" + "="*50)
    print("JobHunter Run Summary")
    print("="*50)
    print(f"Jobs found:       {stats['jobs_found']}")
    print(f"New jobs:         {stats['jobs_new']}")
    print(f"Duplicates:       {stats['jobs_duplicate']}")
    print(f"High matches:     {stats['high_matches']}")
    print(f"Alerts sent:      {stats['alerts_sent']}")
    print("="*50)
    
    # Show top matches
    if stats['jobs_new'] > 0:
        print("\nTop 5 Matches:")
        top = hunter.get_top_matches(5)
        for i, job in enumerate(top, 1):
            print(f"{i}. [{job['fit_score']}/100] {job['title']} at {job['company']}")


if __name__ == "__main__":
    main()

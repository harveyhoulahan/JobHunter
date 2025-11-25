"""
__init__.py for scrapers package
"""
from .base import BaseScraper, JobListing
from .indeed import IndeedScraper
from .linkedin import LinkedInScraper
from .ziprecruiter import ZipRecruiterScraper

__all__ = [
    'BaseScraper',
    'JobListing',
    'IndeedScraper',
    'LinkedInScraper',
    'ZipRecruiterScraper'
]

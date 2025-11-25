"""
AI Automated Job Application Module

This module handles:
- Parsing the base resume (PDF)
- Generating customized CVs for specific jobs
- Automating the job application process
"""

from .cv_generator import CVGenerator
from .applicator import JobApplicator

__all__ = ['CVGenerator', 'JobApplicator']

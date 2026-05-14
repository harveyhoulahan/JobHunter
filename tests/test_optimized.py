#!/usr/bin/env python3
"""
Test script for optimized JobHunter
Run this to see the performance improvements
"""
import os
import time
from src.main import JobHunter

# Disable tokenizers parallelism warning
os.environ["TOKENIZERS_PARALLELISM"] = "false"

print("=" * 60)
print("Testing Optimized JobHunter")
print("=" * 60)
print("\nKey improvements:")
print("✓ Check database BEFORE fetching descriptions")
print("✓ Only fetch descriptions for NEW jobs")
print("✓ Track applications with CV versions")
print("✓ Job progression tracking\n")

start = time.time()

hunter = JobHunter()
hunter.run()

elapsed = time.time() - start

print("\n" + "=" * 60)
print(f"⏱️  Total execution time: {elapsed:.1f} seconds")
print("=" * 60)
print("\nDatabase features now available:")
print("• Track which CV/cover letter you used per application")
print("• Mark jobs as: applied, phone_screen, interview, offer, rejected")
print("• Add interview notes and offer details")
print("• Get application statistics")
print("\nSee src/database/models.py for all tracking methods!")

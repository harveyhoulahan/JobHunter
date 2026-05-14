#!/usr/bin/env python3
"""
Regenerate all cover letters with the improved personalized template
"""
import os
import json
from src.applying.applicator import JobApplicator
from src.database.models import Database

def regenerate_cover_letters():
    """Regenerate cover letters for all existing application metadata files"""
    
    applications_dir = "applications"
    if not os.path.exists(applications_dir):
        print("❌ Applications directory not found")
        return
    
    # Initialize the applicator (it will load the updated cover letter generator)
    applicator = JobApplicator(min_fit_score=0)  # Set min_score to 0 to process all
    
    # Find all metadata files
    metadata_files = [f for f in os.listdir(applications_dir) if f.endswith('_metadata.json')]
    
    print(f"Found {len(metadata_files)} application metadata files")
    print("Regenerating cover letters with personalized template...\n")
    
    regenerated = 0
    for metadata_file in metadata_files:
        metadata_path = os.path.join(applications_dir, metadata_file)
        
        try:
            # Load the metadata
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            
            job_data = metadata.get('job', {})
            score_data = metadata.get('score', {})
            
            if not job_data or not score_data:
                print(f"⚠️  Skipping {metadata_file} - missing job or score data")
                continue
            
            # Generate new cover letter using the improved method
            new_cover_letter = applicator._generate_cover_letter(job_data, score_data)
            
            # Save the new cover letter
            cover_letter_file = metadata_path.replace('_metadata.json', '_cover_letter.txt')
            with open(cover_letter_file, 'w') as f:
                f.write(new_cover_letter)
            
            company = job_data.get('company', 'Unknown')
            title = job_data.get('title', 'Unknown')
            print(f"✓ Regenerated: {company} - {title}")
            regenerated += 1
            
        except Exception as e:
            print(f"❌ Error processing {metadata_file}: {e}")
            continue
    
    print(f"\n{'='*60}")
    print(f"✓ Successfully regenerated {regenerated} cover letters")
    print(f"{'='*60}")

if __name__ == '__main__':
    regenerate_cover_letters()

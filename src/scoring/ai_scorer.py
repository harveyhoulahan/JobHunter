"""
AI-based job scoring using sentence transformers
Provides semantic understanding of job descriptions vs Harvey's profile
"""
import sys
import os
from typing import Dict, Any, Tuple

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Try to import sentence transformers
TRANSFORMERS_AVAILABLE = False
try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
    TRANSFORMERS_AVAILABLE = True
    print("✓ sentence-transformers library loaded successfully")
except ImportError as e:
    print(f"✗ sentence-transformers not available: {e}")
except Exception as e:
    print(f"✗ Unexpected error loading sentence-transformers: {e}")

# Import profile - avoid built-in 'profile' module conflict
HARVEY_PROFILE = None
try:
    # Direct file import to avoid built-in 'profile' module
    import importlib.util
    profile_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'profile.py')
    profile_path = os.path.abspath(profile_path)
    
    spec = importlib.util.spec_from_file_location("harvey_profile", profile_path)
    if spec and spec.loader:
        profile_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(profile_module)
        HARVEY_PROFILE = profile_module.HARVEY_PROFILE
        print(f"✓ Profile loaded successfully from {profile_path}")
except Exception as e:
    print(f"✗ Could not load profile: {e}")
    HARVEY_PROFILE = None

# Fallback profile if loading failed
if HARVEY_PROFILE is None:
    HARVEY_PROFILE = {
        'skills': {'ai_ml': ['Machine Learning', 'Python', 'PyTorch']},
        'experience': [],
        'industries': [],
        'roles': [],
        'summary': 'Machine Learning Engineer'
    }
    print("⚠ Using fallback profile")


class AIJobScorer:
    """
    AI-powered job scoring using semantic similarity
    Uses sentence transformers to understand meaning, not just keywords
    """
    
    def __init__(self):
        self.model = None
        self.profile_embedding = None
        
        if TRANSFORMERS_AVAILABLE:
            try:
                # Use a lightweight but effective model
                print("Loading sentence transformer model...")
                self.model = SentenceTransformer('all-MiniLM-L6-v2')
                
                # Create Harvey's profile embedding once
                self.profile_embedding = self._create_profile_embedding()
                print("✓ AI scorer initialized successfully")
            except Exception as e:
                print(f"✗ Failed to initialize AI scorer: {e}")
                self.model = None
        else:
            print("⚠ AI scoring not available - sentence-transformers library issue")
    
    def _create_profile_embedding(self) -> Any:
        """Create semantic embedding of Harvey's entire profile"""
        if not self.model or not HARVEY_PROFILE:
            return None
        
        # Combine all profile information into text
        profile_text = []
        
        # Add achievements FIRST (most important for impact-based matching)
        if 'achievements' in HARVEY_PROFILE and HARVEY_PROFILE['achievements']:
            profile_text.append("Key Achievements:")
            profile_text.extend(HARVEY_PROFILE['achievements'])
        
        # Add skills
        if 'skills' in HARVEY_PROFILE:
            for category, skills in HARVEY_PROFILE['skills'].items():
                if skills:
                    profile_text.append(f"{category}: {', '.join(skills)}")
        
        # Add experience summary
        if 'experience' in HARVEY_PROFILE:
            for exp in HARVEY_PROFILE['experience'][:3]:  # Top 3 experiences
                profile_text.append(f"Experience: {exp['title']} at {exp['company']}")
                if exp.get('highlights'):
                    profile_text.extend(exp['highlights'][:2])  # Top 2 highlights
        
        # Add industries
        if 'industries' in HARVEY_PROFILE and HARVEY_PROFILE['industries']:
            profile_text.append(f"Industries: {', '.join(HARVEY_PROFILE['industries'])}")
        
        # Add target roles
        if 'roles' in HARVEY_PROFILE and HARVEY_PROFILE['roles']:
            profile_text.append(f"Target roles: {', '.join(HARVEY_PROFILE['roles'])}")
        
        # Combine and embed
        combined_profile = ". ".join(profile_text)
        if not combined_profile:
            print("Warning: Empty profile text, using default")
            combined_profile = "Software Engineer with ML and backend experience"
        
        return self.model.encode(combined_profile, convert_to_tensor=False)
    
    def score_job_ai(self, job_data: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
        """
        Score job using AI semantic similarity
        
        Returns:
            (ai_score, details) where ai_score is 0-100
        """
        if not self.model or self.profile_embedding is None:
            return 50.0, {'method': 'ai_unavailable'}
        
        try:
            # Extract job text
            title = job_data.get('title', '')
            description = job_data.get('description', '')
            company = job_data.get('company', '')
            
            if not description or len(description) < 50:
                return 50.0, {'method': 'insufficient_text'}
            
            # Create job embedding
            job_text = f"{title}. {description}. Company: {company}"
            job_embedding = self.model.encode(job_text, convert_to_tensor=False)
            
            # Calculate cosine similarity
            similarity = self._cosine_similarity(self.profile_embedding, job_embedding)
            
            # Convert similarity (-1 to 1) to score (0 to 100)
            # Similarity typically ranges from 0.1 to 0.6 for jobs
            # Map 0.1 = 0 points, 0.6 = 100 points
            if similarity < 0.1:
                score = 0
            elif similarity > 0.6:
                score = 100
            else:
                score = (similarity - 0.1) / 0.5 * 100
            
            return score, {
                'method': 'sentence_transformer',
                'similarity': round(float(similarity), 3),
                'model': 'all-MiniLM-L6-v2'
            }
            
        except Exception as e:
            print(f"Error in AI scoring: {e}")
            return 50.0, {'method': 'error', 'error': str(e)}
    
    @staticmethod
    def _cosine_similarity(vec1, vec2) -> float:
        """Calculate cosine similarity between two vectors"""
        try:
            import numpy as np
            vec1 = np.array(vec1)
            vec2 = np.array(vec2)
            
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            return float(dot_product / (norm1 * norm2))
        except Exception as e:
            print(f"Error calculating cosine similarity: {e}")
            return 0.0


# Global instance for reuse
_ai_scorer_instance = None


def get_ai_scorer() -> AIJobScorer:
    """Get or create global AI scorer instance"""
    global _ai_scorer_instance
    if _ai_scorer_instance is None:
        _ai_scorer_instance = AIJobScorer()
    return _ai_scorer_instance


if __name__ == "__main__":
    # Test the AI scorer
    scorer = AIJobScorer()
    
    test_job = {
        'title': 'Machine Learning Engineer',
        'company': 'HealthTech Startup',
        'description': '''
        We're looking for an ML Engineer to build predictive models for patient outcomes.
        You'll work with Python, TensorFlow, and AWS to deploy production ML systems.
        Experience with healthcare data and NLP is a plus.
        
        Requirements:
        - 3-5 years experience with Python and machine learning
        - Strong understanding of deep learning and transformers
        - Experience deploying models to production
        - AWS or GCP experience
        '''
    }
    
    score, details = scorer.score_job_ai(test_job)
    print(f"AI Score: {score:.1f}/100")
    print(f"Details: {details}")

"""
Harvey's profile - skills, experience, and preferences
This data is used for matching jobs and auto-applying
Based on actual resume: NY RESUME.pdf
"""

HARVEY_PROFILE = {
    "name": "Harvey J. Houlahan",
    "email": "harveyhoulahan@outlook.com",
    "linkedin": "https://www.linkedin.com/in/harvey-houlahan-245642225/",
    "portfolio": "www.hjhportfolio.com",
    "location": "New York, NY",
    "citizenship": ["Australian Citizen", "USA"],
    
    # Professional Summary
    "summary": """Australian engineer pioneering traceability tech trusted by Target and Cargill. At FibreTrace, 
    my frontline industry knowledge shapes luminescent-pigment solutions tracking cotton supply chains, blending 
    real-time provenance with AI-powered analytics. Also employed by Friday Technologies, an Apple-recognized 
    consultancy, crafting iOS, visionOS, and macOS innovations with Core ML and generative models. This fusion 
    of rural roots and computer engineering expertise equips me to connect real-world challenges with tech that 
    delivers transparency and impact at scale.""",
    
    # Education
    "education": [
        {
            "degree": "B.S. in Advanced Computer Science",
            "institution": "Monash University",
            "location": "Melbourne, Australia",
            "graduation": "Nov 2025",
            "gpa": "3.6/4.0 (High Distinction)",
            "concentrations": ["Artificial Intelligence/Machine Learning", "Advanced Algorithms and Data Structures"],
            "coursework": [
                "Neural Networks & Deep Learning", "Machine Learning", "Artificial Intelligence",
                "Data Structures & Algorithms", "Computer Architecture", "Data Science",
                "Object-Oriented Programming", "Statistics & Applications"
            ]
        },
        {
            "degree": "Bachelor of Medicine, Bachelor of Surgery (MBBS)",
            "institution": "James Cook University",
            "location": "Townsville, Australia",
            "status": "Direct Admittance 2022 (Deferred after 6 months)",
            "note": "Deferred to pursue Computer Science"
        }
    ],
    
    # Core technical skills (FROM ACTUAL RESUME)
    "skills": {
        # AI/ML - ACTUAL SKILLS FROM RESUME
        "ai_ml": [
            "RAG", "Retrieval Augmented Generation",
            "LLM", "Large Language Models", "GPT",
            "NLP", "Natural Language Processing", "Semantic Search",
            "CoreML", "Machine Learning", "ML", "On-device ML",
            "Predictive Analytics", "Deep Learning", "Neural Networks",
            "PyTorch", "TensorFlow", "Transformers",
            "Computer Vision", "OCR",
            "Data Pipelines", "MLOps", "Model Evaluation",
            "Agentic Systems", "Agent-style workflows",
            "Embedding Search", "Vector Databases", "FAISS", "Pinecone",
            "Prompt Engineering", "Anomaly Detection",
            "Predictive Modeling", "Inference Flows"
        ],
        
        # Backend engineering - ACTUAL SKILLS
        "backend": [
            "Python", "C", "C++", "C#", "Java", "Rust",
            "SQL", "PostgreSQL", "MySQL", "DynamoDB",
            "AWS", "Lambda", "S3", "EC2", "API Gateway",
            "Serverless", "High-throughput systems",
            "REST API", "GraphQL", "API Design",
            "Microservices", "ETL/ELT Pipelines",
            "Real-time Data Processing", "Distributed Systems",
            "Data Modeling", "Snowflake"
        ],
        
        # Full-stack development - ACTUAL SKILLS
        "fullstack": [
            "Swift", "SwiftUI", "iOS", "visionOS", "macOS",
            "React", "React Native", "TypeScript", "JavaScript",
            "Next.js", "Node.js",
            "Shopify", "Liquid",
            "HTML", "CSS", "Frontend", "Backend"
        ],
        
        # Cloud & Infrastructure - ACTUAL SKILLS
        "cloud": [
            "AWS", "Cloud Engineering", "Cloud-Native",
            "Docker", "CI/CD", "Agile",
            "Git", "GitHub"
        ],
        
        # Data Engineering - ACTUAL SKILLS  
        "data": [
            "Data Pipelines", "ETL/ELT", "Data Ingestion",
            "Terabyte-scale datasets", "Streaming",
            "Binary Ingest", "mmap-based I/O",
            "Real-time Analytics", "Data Transformation"
        ],
        
        # Tools - ACTUAL SKILLS
        "tools": [
            "Jupyter", "VSCode", "PyCharm", "Xcode",
            "QR/NFC", "Deep Links", "App Clips",
            "Haptics", "Offline-first caching",
            "CI/CD", "DevOps", "Git", "GitHub"
        ]
    },
    
    # Industry experience & interests (PRIORITY ORDER - top industries weighted higher)
    "industries": [
        # TOP PRIORITY - Med Tech, Ag Tech, Fashion Tech
        "Medical Technology", "MedTech", "Healthcare", "HealthTech", "Health Tech",
        "Digital Health", "Clinical", "Medical Device", "Diagnostics",
        
        "Agriculture Tech", "AgTech", "Ag Tech", "Agricultural Technology", 
        "Precision Agriculture", "Farm Tech", "Livestock Tech", "Smart Farming",
        
        "Fashion Tech", "Fashion Technology", "Apparel Tech", "FashionTech",
        "Textile Tech", "Retail Tech", "E-commerce Fashion", "Fashion AI",
        "Fashion Industry", "Fashion", "Apparel", "Garment", "Clothing",
        "Fashion Design", "Sustainable Fashion", "Fashion Manufacturing",
        "Fashion Brands", "Fashion Marketplace", "Wearables", "Textile",
        
        # HIGH PRIORITY - Sustainability & Impact
        "Sustainability", "Climate Tech", "ESG", "Carbon Tech",
        "Supply Chain", "Supply Chain Transparency", "Ethical Sourcing",
        "Circular Economy", "Environmental Tech",
        
        # RELEVANT - AI/ML & IoT
        "Artificial Intelligence", "AI/ML", "Machine Learning",
        "IoT", "Internet of Things", "Embedded Systems", "Sensors",
        
        # ACCEPTABLE - Tech Platforms
        "Consumer Apps", "Marketplace", "Platform", "SaaS",
        "iOS Engineering", "Mobile First",
        "Startups", "0-to-1", "Early Stage", "Seed Stage",
        
        # BONUS - High Performance
        "High-Performance Systems", "Real-time Systems", "Data Pipelines"
    ],
    
    # Target roles
    "roles": [
        "Machine Learning Engineer", "ML Engineer",
        "AI Engineer", "Artificial Intelligence Engineer",
        "Software Engineer",
        "Full Stack Engineer", "Full-Stack Engineer", "Fullstack Engineer",
        "iOS Engineer", "Mobile Engineer",
        "Backend Engineer",
        "Data Engineer", "Analytics Engineer", "Data and Analytics Engineer",
        "ML Platform Engineer", "MLOps Engineer",
        "Product Engineer",
        "Founding Engineer"
    ],
    
    # Companies/projects of interest (from resume)
    "notable_companies": [
        "Pickle", "Finch", "Moda Labs", "MSKCC",
        "FibreTrace", "Modaics", "Step One Clothing",
        "AgrIQ"
    ],
    
    # Location preferences
    "location": {
        "preferred": ["New York City", "NYC", "New York, NY", "Manhattan", "Brooklyn"],
        "remote": True,
        "remote_keywords": ["Remote", "Remote-friendly", "Remote OK", "Work from home", "WFH"]
    },
    
    # Seniority level (Harvey has 3-4 years experience - Mid-level)
    "seniority": {
        "years_experience": "3-4",  # Harvey's actual experience
        "target": [
            # Ideal levels for Harvey (3-4 years)
            "Mid", "Mid-level", "Mid Level", "Intermediate", 
            "Software Engineer II", "Engineer II", "SWE II", "ML Engineer II",
            "Associate", "Associate Engineer",
            # Also acceptable
            "Junior", "Junior Engineer", "Junior Developer",  # Can mentor/lead
            "Software Engineer", "Engineer", "Developer",  # Generic titles
            # Experience requirements that match
            "2-5 years", "3+ years", "3-5 years", "2-4 years", "1-4 years"
        ],
        "exclude": [
            # Too senior for 3-4 years experience
            "Senior", "Sr.", "Sr ", "Staff", "Principal", "Distinguished",
            "Lead", "Tech Lead", "Team Lead", "Engineering Lead",
            "Director", "VP", "CTO", "Head of", "Chief",
            "Manager", "Engineering Manager", "EM",
            # Experience requirements too high
            "5+ years", "7+ years", "10+ years", 
            "senior level", "6+ years experience"
        ]
    },
    
    # Visa requirements
    "visa": {
        "required": True,
        "type": "E-3",
        "positive_keywords": [
            "E-3", "E3", "E-3 visa", "E3 visa",
            "visa sponsorship", "sponsor visa", "sponsorship available",
            "will sponsor", "can sponsor",
            "H1B", "H-1B",  # Also acceptable
            "LCA", "Labor Condition Application",
            "work authorization", "authorized to work",
            "open to sponsorship"
        ],
        "negative_keywords": [
            "no sponsorship", "cannot sponsor", "will not sponsor",
            "must be authorized", "US citizen only", "citizens only",
            "no visa sponsorship now or in future",
            "require current work authorization",
            # NEW: Exclude local-only / no relocation jobs
            "local candidates only", "only local candidates", 
            "no relocation", "no relocation assistance",
            "must be local", "local only", "tri-state only",
            "no 3rd party", "no third party", "no third-party",
            "direct hire only", "w2 only",
            "already authorized to work", "currently authorized",
            "authorized to work in the us without sponsorship",
            "must already have work authorization"
        ]
    },
    
    # Company size preferences
    "company_size": {
        "preferred": ["Startup", "Early-stage", "Small", "Scale-up"],
        "acceptable": ["Medium", "Mid-size"],
        "less_preferred": ["Enterprise", "Large", "Fortune 500"]
    },
    
    # Key projects from resume (for context matching)
    "projects": {
        "ai_ml": [
            "LLM-powered document processing",
            "CoreML iOS models",
            "Predictive analytics",
            "NLP extraction"
        ],
        "iot": [
            "AgrIQ smart ear tag system",
            "Embedded sensor integration",
            "Real-time data collection"
        ],
        "supply_chain": [
            "FibreTrace sustainability tracking",
            "Supply chain transparency"
        ],
        "marketplace": [
            "Modaics fashion marketplace",
            "Step One Clothing e-commerce"
        ],
        "healthcare": [
            "Medical research systems",
            "Clinical data platforms"
        ]
    }
}


def get_all_skills_flat():
    """Get all skills as a flat list"""
    skills = []
    for category in HARVEY_PROFILE["skills"].values():
        skills.extend(category)
    return list(set(skills))  # Remove duplicates


def get_all_industry_keywords():
    """Get all industry keywords"""
    return HARVEY_PROFILE["industries"]


def get_all_role_keywords():
    """Get all role keywords"""
    return HARVEY_PROFILE["roles"]


def get_visa_keywords():
    """Get visa-related keywords"""
    return {
        "positive": HARVEY_PROFILE["visa"]["positive_keywords"],
        "negative": HARVEY_PROFILE["visa"]["negative_keywords"]
    }


if __name__ == "__main__":
    print("Harvey's Profile Summary:")
    print(f"Total unique skills: {len(get_all_skills_flat())}")
    print(f"Industries: {len(HARVEY_PROFILE['industries'])}")
    print(f"Target roles: {len(HARVEY_PROFILE['roles'])}")

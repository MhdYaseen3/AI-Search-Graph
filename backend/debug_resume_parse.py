#!/usr/bin/env python3
"""Debug script to trace resume parsing."""

from app.services.resume_parser_service import ResumeParserService

# Sample resume with education, experience, and summary
sample_resume = """
John Smith
john.smith@email.com
(555) 123-4567

PROFESSIONAL SUMMARY
Experienced software engineer with 5+ years developing full-stack web applications using Python and React. 
Specialized in building scalable microservices and optimizing database performance. Strong leader with proven 
ability to mentor junior developers and deliver projects on time.

EXPERIENCE

Senior Developer — Tech Company Inc
Jan 2022 - Present
Led team of 3 engineers in redesigning payment system, reducing latency by 40%. 
Implemented automated testing reducing bugs by 60%. Mentored 2 junior developers.

Software Engineer — StartUp Co
Jun 2019 - Dec 2021
Built REST APIs using FastAPI handling 1M+ requests daily. 
Designed PostgreSQL schemas optimizing query performance. Deployed services to AWS EKS.

Intern — Web Dev Agency
May 2018 - May 2019
Developed React components for client websites. Fixed bugs and optimized frontend performance.
Assisted senior developers with database optimization tasks.

EDUCATION

Bachelor of Science in Computer Science
State University, 2018

SKILLS
Python, JavaScript, React, FastAPI, PostgreSQL, Docker, AWS, Git
"""

parser = ResumeParserService()
result = parser.parse(sample_resume)

print("\n=== PARSED RESUME ===")
print(f"Name: {result.candidate_name}")
print(f"Email: {result.email}")
print(f"Phone: {result.phone}")
print(f"\nSummary: {result.summary}")
print(f"\nEducation items: {len(result.education)}")
for edu in result.education:
    print(f"  - {edu.degree} from {edu.institution}")
print(f"\nExperience items: {len(result.experiences)}")
for exp in result.experiences:
    print(f"  - {exp.role} at {exp.company} ({exp.start_date} - {exp.end_date})")
    if exp.description:
        print(f"    Description: {exp.description[:100]}...")

print(f"\nSkills: {result.skills}")
print(f"Technologies: {result.technologies}")

import regex as re
from bs4 import BeautifulSoup
from jobspy.model import JobType, Location, Country

def parse_net_empregos_job_type(title: str, description: str) -> list[JobType]:
    """
    Infers job types using structural keywords commonly found in Net-Empregos text strings.
    """
    text = f"{title} {description}".lower()
    job_types = []
    
    if any(k in text for k in ["full-time", "full time", "tempo inteiro", "8h"]):
        job_types.append(JobType.FULL_TIME)
    if any(k in text for k in ["part-time", "part time", "meio tempo"]):
        job_types.append(JobType.PART_TIME)
    if any(k in text for k in ["estágio", "estagio", "internship"]):
        job_types.append(JobType.INTERNSHIP)
    if any(k in text for k in ["contrato", "prestação", "freelance"]):
        job_types.append(JobType.CONTRACT)
        
    return job_types if job_types else [JobType.FULL_TIME]

def is_job_remote(title: str, description: str, location_str: str) -> bool:
    """
    Scans elements for English or Portuguese telecommuting variations.
    """
    remote_keywords = ["remote", "work from home", "wfh", "teletrabalho", "remoto", "casa"]
    full_string = f"{title} {description} {location_str}".lower()
    return any(keyword in full_string for keyword in remote_keywords)

def clean_html_text(text: str) -> str:
    """
    Removes structural anomalies from text blocks.
    """
    if not text:
        return "N/A"
    return re.sub(r'\s+', ' ', text).strip()
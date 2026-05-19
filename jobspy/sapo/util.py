import regex as re
from jobspy.model import JobType

def parse_sapo_job_type(description: str) -> list[JobType]:
    """
    Infers job types from Sapo listing text.
    """
    text = description.lower()
    job_types = []
    
    if any(k in text for k in ["full-time", "tempo inteiro"]):
        job_types.append(JobType.FULL_TIME)
    if any(k in text for k in ["part-time", "meio tempo"]):
        job_types.append(JobType.PART_TIME)
    if any(k in text for k in ["estágio", "estagio", "internship"]):
        job_types.append(JobType.INTERNSHIP)
    if any(k in text for k in ["contrato", "freelance"]):
        job_types.append(JobType.CONTRACT)
        
    return job_types if job_types else [JobType.FULL_TIME]

def is_sapo_job_remote(description: str) -> bool:
    """
    Scans description for remote work variations.
    """
    remote_keywords = ["remoto", "teletrabalho", "remote", "híbrido", "hybrid"]
    text = description.lower()
    return any(keyword in text for keyword in remote_keywords)

def clean_sapo_text(text: str) -> str:
    """
    Cleans extracted Sapo HTML content.
    """
    if not text:
        return "N/A"
    return re.sub(r'\s+', ' ', text).replace('\xa0', ' ').strip()
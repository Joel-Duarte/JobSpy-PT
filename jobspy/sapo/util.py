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

def is_sapo_job_remote(badge_text: str) -> bool:
    """
    Returns True ONLY if the specific workhome badge identifies as full telecommuting.
    """
    return "teletrabalho" in badge_text.lower()

def parse_sapo_work_model(badge_text: str) -> str | None:
    """
    Maps the workhome badge text directly to localized Portuguese string values.
    """
    text = badge_text.lower().strip()
    
    if "hibrido" in text or "híbrido" in text or "hybrid" in text:
        return "Híbrido"
        
    if "teletrabalho" in text or "remoto" in text or "remote" in text:
        return "Teletrabalho"
        
    if "presencial" in text or "on-site" in text:
        return "Presencial"
        
    return None

def clean_sapo_text(text: str) -> str:
    """
    Cleans extracted Sapo HTML content.
    """
    if not text:
        return "N/A"
    return re.sub(r'\s+', ' ', text).replace('\xa0', ' ').strip()
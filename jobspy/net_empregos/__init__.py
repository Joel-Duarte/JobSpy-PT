from __future__ import annotations
import math
import random
import time
import unicodedata
from datetime import datetime
from typing import Optional

import requests
from bs4 import BeautifulSoup
from bs4.element import Tag

# Import centralized mappings alongside your existing headers config
from jobspy.net_empregos.constant import (
    headers, 
    NET_EMPREGOS_DISTRICTS, 
    NET_EMPREGOS_CATEGORIES
)
from jobspy.net_empregos.util import (
    parse_net_empregos_job_type,
    is_job_remote,
    clean_html_text
)
from jobspy.model import (
    JobPost,
    Location,
    JobResponse,
    Country,
    DescriptionFormat,
    Scraper,
    ScraperInput,
    Site,
)
from jobspy.util import (
    extract_emails_from_text,
    markdown_converter,
    plain_converter,
    create_session,
    create_logger,
)

log = create_logger("NetEmpregos")


def clean_parameter_string(text: str) -> str:
    """
    Helper function to lowercase, strip accents, and remove messy formatting 
    symbols to ensure accurate dictionary lookups.
    """
    if not text:
        return ""
    text = unicodedata.normalize('NFKD', text)
    text = "".join([c for c in text if not unicodedata.combining(c)])
    return text.lower().strip()


class NetEmpregos(Scraper):
    base_url = "https://www.net-empregos.com"
    delay = 4       
    band_delay = 4  

    def __init__(
        self, proxies: list[str] | str | None = None, ca_cert: str | None = None, user_agent: str | None = None
    ):
        """
        Initializes NetEmpregos scraper with session safety and pre-flight hydration
        """
        super().__init__(Site.NET_EMPREGOS, proxies=proxies, ca_cert=ca_cert)
        
        self.session = create_session(
            proxies=self.proxies,
            ca_cert=ca_cert,
            is_tls=False,
        )
        if user_agent:
            self.session.headers.update({"User-Agent": user_agent})
        else:
            self.session.headers.update(headers)
            
        self.scraper_input: Optional[ScraperInput] = None
        
        # Prime session cookie state
        try:
            self.session.get(self.base_url, timeout=10)
        except Exception as e:
            log.warning(f"Failed to prime session token array: {str(e)}")

    def scrape(self, scraper_input: ScraperInput) -> JobResponse:
        self.scraper_input = scraper_input
        job_list: list[JobPost] = []
        
        # 1. Map Location parameters safely
        raw_location = scraper_input.location or ""
        mapped_location_id = NET_EMPREGOS_DISTRICTS.get(clean_parameter_string(raw_location), "0")
        
        # 2. Extract pipeline configurations and map categories
        parts = scraper_input.search_term.split("|")
        keyword = parts[0].strip()
        
        raw_category = parts[1].strip() if len(parts) > 1 else "0"
        if raw_category.isdigit():
            category_id = raw_category
        else:
            category_id = NET_EMPREGOS_CATEGORIES.get(clean_parameter_string(raw_category), "0")
            
        raw_tipo = parts[2].strip() if len(parts) > 2 else "0"
        tipo_id = raw_tipo if raw_tipo.isdigit() else "0"
        
        page_num = 1
        processed_count = 0
        
        while processed_count < scraper_input.results_wanted:
            # Build query matching exact target parameters linked by ampersands
            search_url = (
                f"{self.base_url}/pesquisa-empregos.asp"
                f"?chaves={keyword}&categoria={category_id}&zona={mapped_location_id}"
                f"&tipo={tipo_id}&page={page_num}"
            )
            
            try:
                response = self.session.get(search_url, timeout=10)
                response.raise_for_status()
            except Exception as e:
                log.error(f"Network processing drop at page {page_num}: {str(e)}")
                break
                
            soup = BeautifulSoup(response.text, "html.parser")
            job_rows = soup.find_all("div", class_="oferta") or soup.find_all("div", class_="job-item")
            
            if not job_rows:
                log.info(f"No job layout structures found on this page index context. Stopping pagination loop.")
                break
                
            for row in job_rows:
                if processed_count >= scraper_input.results_wanted:
                    break
                    
                # Identify detail hyperlinks
                link_tag = row.find("a", href=True)
                if not link_tag:
                    continue
                    
                job_path = link_tag["href"]
                job_id = job_path.split("-")[-1].replace(".asp", "").strip()
                
                # Deep dive fetch for description text structures
                details = self._get_job_details(job_path)
                description = details.get("description", "")
                
                # Extract descriptive metadata from row anchors
                title_el = row.find("h2") or row.find(class_="title")
                title = clean_html_text(title_el.get_text()) if title_el else "N/A"
                
                company_el = row.find("div", class_="empresa") or row.find("span", class_="company")
                company = clean_html_text(company_el.get_text()) if company_el else "N/A"
                
                location_el = row.find("div", class_="local") or row.find("span", class_="location")
                location_str = clean_html_text(location_el.get_text()) if location_el else raw_location
                
                # Supply positional variable specifications expected by util.py
                job_types = parse_net_empregos_job_type(title, description)
                is_remote = is_job_remote(title, description, location_str)
                
                job_post = JobPost(
                    id=f"ne-{job_id}",
                    title=title,
                    company_name=company,
                    location=Location(city=location_str, country=Country.PORTUGAL),
                    is_remote=is_remote,
                    date_posted=datetime.now().date(),
                    job_url=f"{self.base_url}/{job_path}" if not job_path.startswith("http") else job_path,
                    job_type=job_types,
                    description=description,
                    emails=extract_emails_from_text(description),
                )
                
                job_list.append(job_post)
                processed_count += 1
                
                # Respect anti-throttle request pacing
                time.sleep(random.uniform(self.delay, self.delay + self.band_delay))
                
            page_num += 1
            
        return JobResponse(jobs=job_list)

    def _get_job_details(self, job_path: str) -> dict:
        """
        Navigates into the target listing view page to pull raw description payloads
        """
        full_url = f"{self.base_url}/{job_path}" if not job_path.startswith("http") else job_path
        try:
            response = self.session.get(full_url, timeout=5)
            response.raise_for_status()
        except:
            return {}

        soup = BeautifulSoup(response.text, "html.parser")
        
        # Unconstrained class search covers variations in container tags across different layouts
        desc_div = soup.find(class_="description") or soup.find(class_="job-description") or soup.find(id="oferta-desc")
        
        description = ""
        if desc_div is not None:
            description = desc_div.prettify(formatter="html")
            
            desc_format = DescriptionFormat.PLAIN
            if self.scraper_input is not None:
                desc_format = self.scraper_input.description_format
                
            if desc_format == DescriptionFormat.MARKDOWN:
                description = markdown_converter(description)
            elif desc_format == DescriptionFormat.PLAIN:
                description = plain_converter(description)
                
        return {"description": description}
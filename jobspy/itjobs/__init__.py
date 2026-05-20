from __future__ import annotations
import time
import math
from datetime import datetime
from typing import Optional
from bs4 import BeautifulSoup
from bs4.element import Tag
from playwright.sync_api import sync_playwright

from jobspy.model import JobPost, Location, JobResponse, Country, Scraper, ScraperInput, Site, JobType
from jobspy.util import extract_emails_from_text, create_logger
from jobspy.itjobs.util import clean_sapo_text, clean_parameter_string
from jobspy.itjobs.constant import ITJOBS_LOCATIONS, ITJOBS_WORK_MODELS, ITJOBS_DATES, headers

log = create_logger("ITJobs")

class ITJobs(Scraper):
    base_url = "https://www.itjobs.pt"

    def __init__(self, proxies=None, ca_cert=None, user_agent=None):
        super().__init__(Site.ITJOBS, proxies=proxies, ca_cert=ca_cert)

    def scrape(self, scraper_input: ScraperInput) -> JobResponse:
        # Default date setting
        # ITJobs supports these filter strings:
        # "24h" -> Últimas 24 horas
        # "7d"  -> Últimos 7 dias
        # "15d" -> Últimos 15 dias
        DEFAULT_DATE_FILTER = "7d"
        
        job_list = []
        seen_ids = set()
        
        keyword = scraper_input.search_term.replace(" ", "+") if scraper_input.search_term else ""
        
        loc_id = ITJOBS_LOCATIONS.get(clean_parameter_string(scraper_input.location), "")
        loc_param = f"&location={loc_id}" if loc_id else ""
        
        model_id = ITJOBS_WORK_MODELS.get(clean_parameter_string(str(scraper_input.job_type)), "")
        model_param = f"&work_model={model_id}" if model_id != "" else ""
        
        # Hardcoded default: ITJobs supports "24h", "7d", or "15d"
        date_param = f"&date={DEFAULT_DATE_FILTER}"

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            page_num = 1
            while len(job_list) < scraper_input.results_wanted and page_num <= 5:
                url = f"{self.base_url}/emprego?q={keyword}{loc_param}{model_param}{date_param}&page={page_num}"
                log.info(f"Navigating ITJobs: {url}")
                page.goto(url)
                
                soup = BeautifulSoup(page.content(), "html.parser")
                
                # Multi-target selector: captures .promoted-content blocks and standard list items
                job_rows = soup.select(".promoted-content, ul.listing li")
                
                if not job_rows: break

                for row in job_rows:
                    link_tag = row.select_one("div.list-title a.title") or row.select_one("a.title")
                    if not link_tag or "/oferta/" not in link_tag["href"]: continue
                    
                    job_id = link_tag["href"].split("/oferta/")[1].split("/")[0]
                    if job_id in seen_ids: continue
                    seen_ids.add(job_id)
                    
                    post = self._process_row(row, job_id, f"{self.base_url}{link_tag['href']}", page)
                    if post: job_list.append(post)
                
                page_num += 1
                time.sleep(1)
            browser.close()
        return JobResponse(jobs=job_list)

    def _process_row(self, row: Tag, job_id: str, url: str, page) -> Optional[JobPost]:
        page.goto(url)
        soup = BeautifulSoup(page.content(), "html.parser")
        
        title = clean_sapo_text(soup.find("h1").text) if soup.find("h1") else "N/A"
        company = clean_sapo_text(soup.select_one(".company-name").text) if soup.select_one(".company-name") else "N/A"
        desc = clean_sapo_text(soup.select_one(".job-body").text) if soup.select_one(".job-body") else ""
        
        work_model = None
        for li in soup.select(".item-details ul li"):
            title_span = li.find("span", class_="title")
            if title_span and "Modelo de trabalho" in title_span.text:
                field_span = li.find("span", class_="field")
                work_model = clean_sapo_text(field_span.text) if field_span else None
                break
                
        return JobPost(
            id=f"it-{job_id}", 
            title=title, 
            company_name=company, 
            location=Location(city="Portugal", country=Country.PORTUGAL),
            is_remote=work_model == "Remoto" if work_model else False, 
            work_model=work_model,
            date_posted=datetime.now().date(), 
            job_url=url, 
            job_type=[JobType.FULL_TIME], 
            description=desc, 
            emails=extract_emails_from_text(desc)
        )
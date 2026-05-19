from __future__ import annotations

import time
import math
from datetime import datetime
from typing import Optional

from bs4 import BeautifulSoup
from bs4.element import Tag
from playwright.sync_api import sync_playwright

from jobspy.sapo.constant import BASE_URL, HEADERS, DISTRICT_SLUGS, CATEGORY_SLUGS
from jobspy.sapo.util import (
    parse_sapo_job_type,
    is_sapo_job_remote,
    clean_sapo_text
)
from jobspy.model import (
    JobPost,
    Location,
    JobResponse,
    Country,
    Scraper,
    ScraperInput,
    Site,
)
from jobspy.util import (
    extract_emails_from_text,
    create_logger,
)

log = create_logger("Sapo")


class Sapo(Scraper):
    base_url = BASE_URL

    def __init__(
        self, proxies: list[str] | str | None = None, ca_cert: str | None = None, user_agent: str | None = None
    ):
        super().__init__(Site.SAPO, proxies=proxies, ca_cert=ca_cert)
        self.scraper_input = None

    def scrape(self, scraper_input: ScraperInput) -> JobResponse:
        self.scraper_input = scraper_input
        job_list: list[JobPost] = []
        seen_ids = set()
        
        # Expects: "Keyword|Category|Model"
        parts = scraper_input.search_term.split("|")
        keyword = parts[0].strip()
        cat_key = parts[1].strip() if len(parts) > 1 else ""
        work_model = parts[2].strip() if len(parts) > 2 else ""
        
        # Lookups
        category_slug = CATEGORY_SLUGS.get(cat_key.lower(), cat_key)
        loc_param = DISTRICT_SLUGS.get(scraper_input.location.lower(), scraper_input.location.lower().replace(" ", "-"))
        regime_param = f"&regime={work_model}" if work_model in ["presencial", "teletrabalho", "hibrido"] else ""
        
        page_num = 1
        max_pages = math.ceil(scraper_input.results_wanted / 20) + 1

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_extra_http_headers(HEADERS)
            
            while len(job_list) < scraper_input.results_wanted and page_num <= max_pages:
                url = f"{self.base_url}/offers?categoria={category_slug}&local={loc_param}&pesquisa={keyword}{regime_param}&pagina={page_num}&ordem=mais-recentes"
                
                log.info(f"Navigating to page {page_num}: {url}")
                page.goto(url)
                
                try:
                    page.wait_for_selector("li.all-100 article", timeout=10000)
                except Exception:
                    log.info("No more jobs found.")
                    break

                html = page.content()
                soup = BeautifulSoup(html, "html.parser")
                job_rows = soup.select("li.all-100 article")
                
                if not job_rows:
                    break

                for row in job_rows:
                    link_tag = row.find("a", href=True)
                    if not link_tag or "id=" not in link_tag["href"]:
                        continue
                        
                    job_id = link_tag["href"].split("id=")[-1]
                    if job_id in seen_ids:
                        continue
                        
                    seen_ids.add(job_id)
                    job_post = self._process_row(row, job_id, link_tag["href"])
                    if job_post:
                        job_list.append(job_post)
                        
                    if len(job_list) >= scraper_input.results_wanted:
                        break
                
                page_num += 1
                time.sleep(1)

            browser.close()

        return JobResponse(jobs=job_list)

    def _process_row(self, row: Tag, job_id: str, job_url: str) -> Optional[JobPost]:
        title_el = row.find("h3")
        title = clean_sapo_text(title_el.get_text()) if title_el else "N/A"
        
        company_el = row.select_one("li.name")
        company = clean_sapo_text(company_el.get_text()) if company_el else "N/A"
        
        location_el = row.select_one("li.location")
        location_str = clean_sapo_text(location_el.get_text()) if location_el else "N/A"
        
        desc_element = row.find("p", class_="quarter-bottom-space")
        description = clean_sapo_text(desc_element.get_text()) if desc_element else ""

        return JobPost(
            id=f"sap-{job_id}",
            title=title,
            company_name=company,
            location=Location(city=location_str, country=Country.PORTUGAL),
            is_remote=is_sapo_job_remote(description),
            date_posted=datetime.now().date(),
            job_url=job_url,
            job_type=parse_sapo_job_type(description),
            description=description,
            emails=extract_emails_from_text(description),
        )
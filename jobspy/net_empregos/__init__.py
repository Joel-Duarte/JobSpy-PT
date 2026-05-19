from __future__ import annotations
import requests
import math
import random
import time
from datetime import datetime
from typing import Optional

from bs4 import BeautifulSoup
from bs4.element import Tag

from jobspy.net_empregos.constant import headers
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
            has_retry=True,
            delay=5,
            clear_cookies=False,
        )
        self.session.headers.update(headers)
        self.scraper_input = None

        # PRE-FLIGHT HYDRATION:
        # Request the homepage first to inherit valid session tokens before querying search routes
        try:
            log.info("Establishing authentic pre-flight session tokens...")
            self.session.get(self.base_url, timeout=10)
            self.session.headers.update({"Referer": f"{self.base_url}/"})
        except Exception as e:
            log.warning(f"Failed to prime session token array: {str(e)}")

    def scrape(self, scraper_input: ScraperInput) -> JobResponse:
        """
        Scrapes Net-Empregos for jobs matching criteria using explicit numerical IDs
        """
        self.scraper_input = scraper_input
        job_list: list[JobPost] = []
        seen_ids = set()
        
        page_num = 1
        request_count = 0
        
        continue_search = (
            lambda: len(job_list) < scraper_input.results_wanted and page_num <= 10
        )

        #Expects stringified integers like "2" for Porto
        zone_id = "0"
        if scraper_input.location:
            loc_input = scraper_input.location.strip()
            zone_id = loc_input if loc_input.isdigit() else "0"

        #Expects "Keyword|CategoryID" format like "Python|5"
        search_keyword = ""
        category_id = "0"
        tipo_id = "0"

        if scraper_input.search_term:
            term_input = scraper_input.search_term.strip()
            if "|" in term_input:
                parts = term_input.split("|", 1)
                search_keyword = parts[0].strip()
                category_id = parts[1].strip() if parts[1].strip().isdigit() else "0"
                tipo_id = parts[2].strip() if len(parts) > 2 and parts[2].strip().isdigit() else "0"
            else:
                search_keyword = term_input

        while continue_search():
            request_count += 1
            log.info(
                f"search page: {request_count} / {math.ceil(scraper_input.results_wanted / 10)}"
            )
            
            params = {
                "chaves": search_keyword,
                "cidade": "",
                "categoria": category_id,
                "zona": zone_id,
                "tipo": 0,
                "page": page_num
            }

            full_request_url = self.session.prepare_request(
                requests.Request("GET", f"{self.base_url}/pesquisa-empregos.asp", params=params)
            ).url
            log.info(f"Targeting URL: {full_request_url}")
            
            try:
                response = self.session.get(
                    f"{self.base_url}/pesquisa-empregos.asp",
                    params=params,
                    timeout=10,
                )
                if response.status_code not in range(200, 400):
                    log.error(f"Net-Empregos status error code: {response.status_code}")
                    return JobResponse(jobs=job_list)
            except Exception as e:
                log.error(f"Net-Empregos connection error: {str(e)}")
                return JobResponse(jobs=job_list)

            soup = BeautifulSoup(response.text, "html.parser")
            
            job_rows = soup.find_all("div", class_="oferta") or soup.find_all("div", class_="job-item")
            if not job_rows:
                job_rows = [div for div in soup.find_all("div") if div.get("id") and div["id"].startswith("oferta-")]
                
            if len(job_rows) == 0:
                log.info("No job layout structures found on this page. Stopping pagination.")
                break

            new_jobs_on_page = 0

            for row in job_rows:
                link_tag = row.find("a", href=True)
                if link_tag:
                    href = link_tag["href"]
                    
                    if "pesquisa-emprego" in href or "anunciar-emprego" in href or href == "#":
                        continue
                        
                    try:
                        job_id_match = href.split("-")[-1].replace(".asp", "")
                    except:
                        continue
                    
                    if job_id_match in seen_ids:
                        continue
                    seen_ids.add(job_id_match)
                    new_jobs_on_page += 1

                    try:
                        job_post = self._process_row(row, job_id_match, href)
                        if job_post:
                            job_list.append(job_post)
                        if not continue_search():
                            break
                    except Exception as e:
                        log.error(f"Row processing error: {str(e)}")

            if new_jobs_on_page == 0:
                log.info("Page contains duplicate items or default trending metrics. Halting pagination loop.")
                break

            if continue_search():
                base_sleep = random.uniform(self.delay, self.delay + self.band_delay)
                if random.random() < 0.15:
                    human_break = random.uniform(6.0, 12.0)
                    time.sleep(base_sleep + human_break)
                else:
                    time.sleep(base_sleep)
                page_num += 1

        job_list = job_list[: scraper_input.results_wanted]
        return JobResponse(jobs=job_list)

    def _process_row(self, row: Tag, job_id: str, job_path: str) -> Optional[JobPost]:
        title_element = row.find("a", class_="titulo") or row.find("h2") or row.find("a")
        if not title_element:
            return None
            
        title = clean_html_text(title_element.get_text())

        company_element = row.find("a", class_="empresa") or row.find("span", class_="empresa")
        company = clean_html_text(company_element.get_text()) if company_element else "N/A"
        
        location_element = row.find("span", class_="local") or row.find("div", class_="local")
        location_name = clean_html_text(location_element.get_text()) if location_element else "Portugal"

        location = Location(
            city=location_name,
            country=Country.from_string("portugal")
        )

        description = ""
        try:
            job_details = self._get_job_details(job_path)
            if job_details:
                description = job_details.get("description", "")
        except Exception as detail_err:
            log.warning(f"Could not pull full description for job {job_id}: {detail_err}")

        is_remote = is_job_remote(title, description, location_name)
        job_types = parse_net_empregos_job_type(title, description)

        return JobPost(
            id=f"ne-{job_id}",
            title=title,
            company_name=company,
            location=location,
            is_remote=is_remote,
            date_posted=datetime.now().date(),
            job_url=f"{self.base_url}/{job_path}" if not job_path.startswith("http") else job_path,
            job_type=job_types,
            description=description,
            emails=extract_emails_from_text(description),
        )

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
        desc_div = soup.find("div", class_="description") or soup.find("div", class_="job-description")
        
        description = None
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
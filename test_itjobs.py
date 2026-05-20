# test_itjobs.py
from jobspy.model import ScraperInput, Site
from jobspy.itjobs import ITJobs
import json

def test_itjobs_scraper():
    print("--- Initializing ITJobs Scraper Test ---")
    
    scraper_input = ScraperInput(
        site_type=[Site.ITJOBS],
        search_term="", 
        location="Braga",
        results_wanted=3
    )
    
    scraper = ITJobs()
    
    try:
        print("Running scrape operation...")
        response = scraper.scrape(scraper_input)
        
        print(f"Successfully retrieved {len(response.jobs)} jobs.\n")
        
        for i, job in enumerate(response.jobs, 1):
            print(f"--- Job Entry #{i} ---")
            print(f"ID: {job.id}")
            print(f"Title: {job.title}")
            print(f"Company: {job.company_name}")
            print(f"Work Model: {job.work_model}")
            print(f"URL: {job.job_url}")
            print("-" * 20)
            
    except Exception as e:
        print(f"Test failed with error: {e}")

if __name__ == "__main__":
    test_itjobs_scraper()
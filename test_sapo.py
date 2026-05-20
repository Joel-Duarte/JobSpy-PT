from jobspy.sapo import Sapo
from jobspy.model import ScraperInput, DescriptionFormat, Site

def run_test():
    print("Initializing Sapo Scraper...")
    scraper = Sapo()
    
    test_input = ScraperInput(
        site_type=[Site.SAPO],
        search_term="Python|informatica",
        location="Porto",
        results_wanted=10,
        description_format=DescriptionFormat.PLAIN,
        job_type=None,
        hours_old=None
    )

    try:
        print(f"Executing scrape for term: '{test_input.search_term}' in '{test_input.location}'...")
        response = scraper.scrape(test_input)
        
        print("\n--- TEST RESULTS ---")
        print(f"Total jobs found: {len(response.jobs)}")
        
        for idx, job in enumerate(response.jobs, 1):
            print(f"\n[{idx}] {job.title}")
            print(f"    Company:  {job.company_name}")
            print(f"    Location: {job.location.city if job.location else 'N/A'}")
            print(f"    URL:      {job.job_url}")
            print(f"    Model:     {job.work_model}")
            if job.description:
                print(f"    Desc Snippet: {job.description[:100]}...")
                
    except Exception as e:
        print(f"\nExecution failed with error:\n{e}")

if __name__ == "__main__":
    run_test()
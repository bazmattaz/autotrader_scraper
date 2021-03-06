import requests, json, csv, traceback, cloudscraper, sys, time, os.path, logging
from time import sleep
from bs4 import BeautifulSoup
from datetime import datetime
from pathlib import Path

def get_cars(make="BMW", model="5 SERIES", postcode="SW1A 0AA", radius=1500, min_year=1995, max_year=2021, include_writeoff="include", max_attempts_per_page=5, verbose=False, fueltype="Petrol", transmission="Automatic", maximummileage=90000, pricefrom=5000, priceto=8000, minimumbadgeenginesize=1.0, maximumbadgeenginesize=2.0, annual_tax_cars="TO_500"):

    # Setup a custom log with the username in the filename
    logname = Path(__file__).parent / "data/automated_scraper.log"
    logging.basicConfig(filename=logname, level=logging.DEBUG, format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')

    # Set the output filename and set it's path to the data folder
    filepartial = "data/" + str(make) + "_" + str(model) + ".csv"
    filename = Path(__file__).parent / filepartial

    def check_car(car_ID):
        csv_file = csv.reader(open(filename, "r"), delimiter=",")
        #loop through the csv list and see if the car has already been scraped
        for row in csv_file:
            if str(car_ID) == row[0]:
                return True
        return False

    # Check if a CSV has been created for this make and model, if not, create one
    if os.path.isfile(filename) == False:
        csv_columns = ["ID", "name", "link", "price", "mileage", "BHP", "transmission", "fuel", "owners", "body", "ULEZ", "engine", "year", "date_scraped"]
        with open(filename, "w", newline='') as f:
            writer = csv.DictWriter(f, fieldnames=csv_columns)
            writer.writeheader()
    
    # To bypass Cloudflare protection
    scraper = cloudscraper.create_scraper()

    # Basic variables

    results = []
    n_this_year_results = 0

    url = "https://www.autotrader.co.uk/results-car-search"

    keywords = {}
    keywords["mileage"] = ["miles"]
    keywords["BHP"] = ["BHP"]
    keywords["transmission"] = ["Automatic", "Manual"]
    keywords["fuel"] = ["Petrol", "Diesel", "Electric", "Hybrid – Diesel/Electric Plug-in", "Hybrid – Petrol/Electric", "Hybrid – Petrol/Electric Plug-in"]
    keywords["owners"] = ["owners"]
    keywords["body"] = ["Coupe", "Convertible", "Estate", "Hatchback", "MPV", "Pickup", "SUV", "Saloon"]
    keywords["ULEZ"] = ["ULEZ"]
    keywords["year"] = [" reg)"]
    keywords["engine"] = ["engine"]

    # Set up parameters for query to autotrader.co.uk

    params = {
        "sort": "datedesc",
        "postcode": postcode,
        "radius": radius,
        "make": make,
        "model": model,
        "search-results-price-type": "total-price",
        "search-results-year": "select-year",
        "fuel-type": fueltype,
        "transmission":transmission,
        "maximum-mileage":maximummileage,
        "price-from":pricefrom,
        "price-to":priceto,
        "minimum-badge-engine-size":minimumbadgeenginesize,
        "maximum-badge-engine-size":maximumbadgeenginesize,
        "annual-tax-cars":annual_tax_cars,
    }

    if (include_writeoff == "include"):
        params["writeoff-categories"] = "on"
    elif (include_writeoff == "exclude"):
        params["exclude-writeoff-categories"] = "on"
    elif (include_writeoff == "writeoff-only"):
        params["only-writeoff-categories"] = "on"
        
    year = min_year
    page = 1
    attempt = 1


    try:

        while year <= max_year:

            params["year-from"] = year
            params["year-to"] = year
            params["page"] = page

            r = scraper.get(url, params=params)

            if verbose:
                print("Year:     ", year)
                print("Page:     ", page)
                print("Response: ", r)

            try:

                if r.status_code == 404:  
                    logging.error("Error: 404 error returned")
                    break

                elif r.status_code != 200 and r.status_code != 404: # if not successful (e.g. due to bot protection), log as an attempt
                    attempt = attempt + 1
                    if attempt <= max_attempts_per_page:
                        if verbose:
                            logging.info("Exception. Starting attempt #", attempt, "and keeping at page #", page)
                    else:
                        page = page + 1
                        attempt = 1
                        if verbose:
                            logging.info("Exception. All attempts exhausted for this page. Skipping to next page #", page)

                else:

                    j = r.json()
                    s = BeautifulSoup(j["html"], features="html.parser")

                    articles = s.find_all("article", attrs={"data-standout-type":""})

                    # if no results or reached end of results...
                    if len(articles) == 0 or r.url[r.url.find("page=")+5:] != str(page):
                        if verbose:
                            print("Found total", n_this_year_results, "results for year", year, "across", page-1, "pages")
                            if year+1 <= max_year:
                                print("Moving on to year", year + 1)
                                print("---------------------------------")

                        # Increment year and reset relevant variables
                        year = year + 1
                        page = 1
                        attempt = 1
                        n_this_year_results = 0
                    else:
                        for article in articles:
                            
                            car_url = "https://www.autotrader.co.uk" + article.find("a", {"class": "tracking-standard-link"})["href"][: article.find("a", {"class": "tracking-standard-link"})["href"].find("?")]
                            car_ID = int(car_url.strip("https://www.autotrader.co.uk/car-details/"))
                            
                            # Check if the ID of this car is present in the CSV 
                            if check_car(car_ID) == False:
                                # Car hasn't been found in the CSV so scrape it
                                car = {}
                                car["ID"] = car_ID
                                car_title = article.find("h3", {"class": "product-card-details__title"}).text.strip()
                                car_subtitle = article.find("p", {"class": "product-card-details__subtitle"}).text.strip()
                                car["name"] = car_title + " " + car_subtitle
                                car["link"] = car_url
                                car["price"] = int((article.find("div", {"class": "product-card-pricing__price"}).text.strip()).replace(',','').strip('£'))

                                key_specs_bs_list = article.find("ul", {"class": "listing-key-specs"}).find_all("li")
                                
                                for key_spec_bs_li in key_specs_bs_list:

                                    key_spec_bs = key_spec_bs_li.text

                                    if any(keyword in key_spec_bs for keyword in keywords["mileage"]):
                                        car["mileage"] = int(key_spec_bs[:key_spec_bs.find(" miles")].replace(",",""))
                                    elif any(keyword in key_spec_bs for keyword in keywords["BHP"]):
                                        car["BHP"] = int(key_spec_bs[:key_spec_bs.find("BHP")])
                                    elif any(keyword in key_spec_bs for keyword in keywords["transmission"]):
                                        car["transmission"] = key_spec_bs
                                    elif any(keyword in key_spec_bs for keyword in keywords["fuel"]):
                                        car["fuel"] = key_spec_bs
                                    elif any(keyword in key_spec_bs for keyword in keywords["owners"]):
                                        car["owners"] = int(key_spec_bs[:key_spec_bs.find(" owners")])
                                    elif any(keyword in key_spec_bs for keyword in keywords["body"]):
                                        car["body"] = key_spec_bs
                                    elif any(keyword in key_spec_bs for keyword in keywords["ULEZ"]):
                                        car["ULEZ"] = key_spec_bs
                                    elif any(keyword in key_spec_bs for keyword in keywords["year"]):
                                        car["year"] = key_spec_bs
                                    elif key_spec_bs[1] == "." and key_spec_bs[3] == "L":
                                        car["engine"] = key_spec_bs
                                
                                car["date_scraped"] = datetime.now().strftime("%d/%m/%Y, %H:%M:%S")
                                results.append(car)
                            
                            n_this_year_results = n_this_year_results + 1

                        page = page + 1
                        attempt = 1

                        if verbose:
                            print("Car count: ", len(results))
                            print("---------------------------------")

            except KeyboardInterrupt:
                break

            except:
                traceback.print_exc()
                attempt = attempt + 1
                if attempt <= max_attempts_per_page:
                    if verbose:
                        print("Exception. Starting attempt #", attempt, "and keeping at page #", page)
                else:
                    page = page + 1
                    attempt = 1
                    if verbose:
                        print("Exception. All attempts exhausted for this page. Skipping to next page #", page)

    except KeyboardInterrupt:
        pass
  
    # Write the results to the CSV
    csv_columns = ["ID", "name", "link", "price", "mileage", "BHP", "transmission", "fuel", "owners", "body", "ULEZ", "engine", "year", "date_scraped"]
    with open(filename, "a+", newline='') as f:
        writer = csv.DictWriter(f, fieldnames=csv_columns)
        #writer.writeheader()
        for data in results:
            writer.writerow(data)

    # Return the number of updates
    logging.info(str(len(results)) + " new cars found and added to existing CSV")
    return len(results)

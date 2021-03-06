import requests, json, csv, traceback, cloudscraper, sys, time
from time import sleep
from bs4 import BeautifulSoup

def get_cars(make="BMW", model="5 SERIES", postcode="SW1A 0AA", radius=1500, min_year=1995, max_year=2021, include_writeoff="include", max_attempts_per_page=5, verbose=False, fueltype="Petrol", transmission="Automatic", maximummileage=90000, pricefrom=5000, priceto=8000, minimumbadgeenginesize=1.0, maximumbadgeenginesize=2.0, annual_tax_cars="TO_500"):

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
        "sort": "relevance",
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

                if r.status_code != 200: # if not successful (e.g. due to bot protection), log as an attempt
                    # Add a check to see if it's a 404 message
                    if r.status_code == 404:
                        print("Warning: 404 error returned. Sleeping for 30 seconds.")
                        time.sleep(30)
                    else: 
                        attempt = attempt + 1
                        if attempt <= max_attempts_per_page:
                            if verbose:
                                print("Exception. Starting attempt #", attempt, "and keeping at page #", page)
                        else:
                            page = page + 1
                            attempt = 1
                            if verbose:
                                print("Exception. All attempts exhausted for this page. Skipping to next page #", page)

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
                            car_title = article.find("h3", {"class": "product-card-details__title"}).text.strip()
                            car_subtitle = article.find("p", {"class": "product-card-details__subtitle"}).text.strip()
                            car = {}
                            car["name"] = car_title + " " + car_subtitle
                            #car["name"] = article.find("h1", {"class": "advert-heading__title atc-type-insignia atc-type-insignia--medium"}).text.strip()
                            car["link"] = "https://www.autotrader.co.uk" + article.find("a", {"class": "tracking-standard-link"})["href"][: article.find("a", {"class": "tracking-standard-link"})["href"].find("?")]
                            car["ID"] = int(car["link"].strip("https://www.autotrader.co.uk/car-details/"))
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
    
    print("-----------------------------")
    print(len(results), " cars found in this search", )
    print("-----------------------------")
    return results

### Output functions ###

def save_csv(results = [], filename = "scraper_output.csv"):
    csv_columns = ["name", "link", "ID", "price", "mileage", "BHP", "transmission", "fuel", "owners", "body", "ULEZ", "engine", "year"]

    with open(filename, "w", newline='') as f:
        writer = csv.DictWriter(f, fieldnames=csv_columns)
        writer.writeheader()
        for data in results:
            writer.writerow(data)

def save_json(results = [], filename = "scraper_output.json"):
    with open(filename, 'w') as f:
        json.dump(results, f, sort_keys=True, indent=4, separators=(',', ': '))
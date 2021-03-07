"""
Search for a car to harvest the data from. This script is intended to be run at an interval (daily weekly....etc)

what ths script is used for:
- Enter the search query you have want to harvest
- It calls the automated_scraper.py to do a search and scrae new cars into a csv
- The automated_scraper.py script will check to see if a CSV has been created already - if not it will crete one in the /data folder
"""
import automated_scraper
from automated_scraper import get_cars

# List all the make and models to search for - a seperate CSV will be created for each car within the /data folder
cars = [{ "make":"MAZDA",
        "model":"MAZDA6"
        },
        { "make":"FORD",
        "model":"MONDEO"
        },
        { "make":"NISSAN",
        "model":"QASHQAI"
        },
        { "make":"VOLKSWAGEN",
        "model":"PASSAT"
        },
        { "make":"SKODA",
        "model":"OCTAVIA"
        },
        { "make":"SKODA",
        "model":"SUPERB"
        },
]

# Loop through the cars above and call the scraper
for item in cars:
    results = get_cars(  # Note: If you comment out these search params the defualt values in the automated_scraper.py will be used
            make = item["make"],
            model = item["model"],
            postcode = "SW1A 0AA",
            radius = 1500,
            min_year = 2010,
            max_year = 2020,
            include_writeoff = "exclude",
            max_attempts_per_page = 5,
            fueltype = "Petrol",
            transmission = "Automatic",
            maximummileage = "500000",
            pricefrom = 5000,
            priceto = 12000,
            minimumbadgeenginesize = 1.0,
            maximumbadgeenginesize = 2.0,
            annual_tax_cars = "TO_500",  #Options include: TO_20, TO_30, TO_130, TO_145, TO_185, TO_210... 
            verbose = False,
        )

    print(str(results) + " new cars found and added to the " + item["make"] + " " + item["model"] + " CSV")
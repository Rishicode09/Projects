"""Generate realistic synthetic used-car listings.

Why synthetic data instead of scraping? Scraping listing sites raises legal
and terms-of-service issues, and scraped data changes daily so results are not
reproducible. A generator with a fixed random seed gives us a realistic,
reproducible dataset -- and forces us to understand what drives car prices,
because we have to model it: cars lose value exponentially with age, high
mileage cuts the price further, and dealers charge more than private sellers.
"""

import random
from datetime import date, timedelta

# Rough new prices (GBP) and typical engine sizes for popular UK models.
CATALOGUE: dict[tuple[str, str], dict] = {
    ("Ford", "Fiesta"): {"new_price": 19000, "engines": [1.0, 1.1]},
    ("Ford", "Focus"): {"new_price": 26000, "engines": [1.0, 1.5]},
    ("Ford", "Puma"): {"new_price": 26000, "engines": [1.0]},
    ("Volkswagen", "Polo"): {"new_price": 21000, "engines": [1.0, 1.2]},
    ("Volkswagen", "Golf"): {"new_price": 28000, "engines": [1.4, 1.5, 2.0]},
    ("Volkswagen", "Tiguan"): {"new_price": 34000, "engines": [1.5, 2.0]},
    ("BMW", "1 Series"): {"new_price": 31000, "engines": [1.5, 2.0]},
    ("BMW", "3 Series"): {"new_price": 40000, "engines": [2.0, 3.0]},
    ("Audi", "A3"): {"new_price": 30000, "engines": [1.5, 2.0]},
    ("Audi", "A4"): {"new_price": 38000, "engines": [2.0]},
    ("Mercedes-Benz", "A-Class"): {"new_price": 33000, "engines": [1.3, 2.0]},
    ("Mercedes-Benz", "C-Class"): {"new_price": 43000, "engines": [1.5, 2.0]},
    ("Toyota", "Yaris"): {"new_price": 22000, "engines": [1.5]},
    ("Toyota", "Corolla"): {"new_price": 30000, "engines": [1.8, 2.0]},
    ("Nissan", "Qashqai"): {"new_price": 28000, "engines": [1.3]},
    ("Vauxhall", "Corsa"): {"new_price": 19000, "engines": [1.2]},
    ("Vauxhall", "Astra"): {"new_price": 25000, "engines": [1.2, 1.6]},
    ("Kia", "Sportage"): {"new_price": 28000, "engines": [1.6]},
    ("Hyundai", "i10"): {"new_price": 16000, "engines": [1.0, 1.2]},
    ("Tesla", "Model 3"): {"new_price": 40000, "engines": [0.0]},
}

REGIONS = [
    "London",
    "South East",
    "Midlands",
    "North West",
    "Yorkshire",
    "Scotland",
    "Wales",
    "South West",
]

DEPRECIATION_RATE = 0.16  # cars lose roughly 16% of their value per year
MILES_PER_YEAR = 9000  # UK average annual mileage


def generate_listings(count: int = 5000, seed: int = 42) -> list[dict]:
    """Return `count` listing dicts, identical every run for the same seed."""
    rng = random.Random(seed)
    today = date.today()
    listings = []

    for _ in range(count):
        (make, model), spec = rng.choice(list(CATALOGUE.items()))
        age = rng.randint(0, 15)
        year = today.year - age

        # Mileage grows with age, with plenty of individual variation.
        mileage = max(0, int(age * MILES_PER_YEAR * rng.uniform(0.5, 1.5)))

        engine_size = rng.choice(spec["engines"])
        if make == "Tesla":
            fuel_type = "Electric"
        else:
            fuel_type = rng.choices(["Petrol", "Diesel", "Hybrid"], weights=[60, 25, 15])[0]
        transmission = rng.choices(["Manual", "Automatic"], weights=[55, 45])[0]
        seller_type = rng.choices(["Dealer", "Private"], weights=[70, 30])[0]

        # Price model: exponential depreciation by age, then a penalty for
        # above-average mileage, small premiums for dealers/automatics, and
        # random noise so the data is not perfectly predictable.
        price = spec["new_price"] * (1 - DEPRECIATION_RATE) ** age
        expected_miles = age * MILES_PER_YEAR
        price *= 1 - 0.000002 * (mileage - expected_miles)
        if seller_type == "Dealer":
            price *= 1.05
        if transmission == "Automatic":
            price *= 1.03
        price *= rng.uniform(0.9, 1.1)

        listings.append(
            {
                "make": make,
                "model": model,
                "year": year,
                "mileage": mileage,
                "fuel_type": fuel_type,
                "transmission": transmission,
                "engine_size": engine_size,
                "price": max(500, int(round(price, -1))),
                "region": rng.choice(REGIONS),
                "seller_type": seller_type,
                "listed_date": today - timedelta(days=rng.randint(0, 180)),
            }
        )

    return listings

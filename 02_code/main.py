import os
import argparse

import pandas as pd
from loguru import logger as lg

from scraper.scraper_core import JaapScraper, ParariusScraper


def filter_data(df: pd.DataFrame, max_price: int = 1450, min_rooms: int = 3, min_size_m2: int = 60,
                max_dist_to_station: int = 2) -> pd.DataFrame:
    """
    Filters the data based on some criteria (e.g. max_price, min_rooms etc)

    Args:
        df (pd.DataFrame): The dataframe to filter
        max_price (int): The maximum price of the listing
        min_rooms (int): The minimum number of rooms of the listing
        min_size_m2 (int): The minimum size of the listing in m2
        max_dist_to_station (int): The maximum distance to the nearest station in km

    Returns:
        pd.DataFrame: The filtered dataframe
    """
    # Set columns
    df['price'] = pd.to_numeric(df['price'], errors='coerce')
    df['nr_rooms'] = pd.to_numeric(df['nr_rooms'], errors='coerce')
    df['size_m2'] = pd.to_numeric(df['size_m2'], errors='coerce')

    # Filter data
    df = df[df['price'] <= max_price]
    df = df[df['nr_rooms'] >= min_rooms]
    df = df[df['dist_to_station'] <= max_dist_to_station]
    df = df[df['size_m2'] >= min_size_m2]
    return df


def final_cleaning(df: pd.DataFrame) -> pd.DataFrame:
    """
    Cleans the final data by adding the price per m2, settings correct column order and sorting by price

    Args:
        df (pd.DataFrame): The dataframe to clean

    Returns:
        pd.DataFrame: The cleaned dataframe
    """
    # Add price per m2
    df['price_per_m2'] = df['price'] / df['size_m2']

    # Set column order
    correct_col_order = ['ad_title', 'ad_descr', 'address', 'price', 'size_m2', 'price_per_m2', 'nr_rooms',
                         'dist_to_station',
                         'build_year', 'scrape_date', 'website', 'ad_url']
    df = df[correct_col_order]

    # Sort by price
    df = df.sort_values(by='price')
    return df


def main(scrape_all=True, scrape_jaap=False, scrape_pararius=False, debug_mode=True):
    """
    Main function that runs the scraper and saves the data to a CSV file

    Args:
        scrape_all (bool): Whether to scrape all websites or not (overrides scrape_jaap and scrape_pararius)
        scrape_jaap (bool): Whether to scrape Jaap.nl or
        scrape_pararius (bool): Whether to scrape Pararius.nl or not
        debug_mode (bool): Whether to run in debug mode or not
    """
    if scrape_all:
        scrape_jaap = True
        scrape_pararius = True
    elif not scrape_jaap and not scrape_pararius:
        raise AttributeError("No scraping selected")

    # Initialize scrapers
    scrapers = {}
    if scrape_jaap:
        scrapers['jaap'] = JaapScraper(debug_mode=debug_mode)
    if scrape_pararius:
        scrapers['pararius'] = ParariusScraper(debug_mode=debug_mode)

    lg.info("Starting scraping")
    for scraper_name, scraper in scrapers.items():
        lg.info(f"Starting scraping for {scraper_name}")
        scraper.scrape_all_pages()

    lg.info("Loading data")
    data_path = list(scrapers.values())[0].scrape_data_path
    df = pd.read_csv(data_path)

    lg.info("Adjusting and filtering data")
    df = filter_data(df)
    lg.debug("Remaining rows: %s" % len(df))

    # Add descriptions for Jaap (only for filtered ads, so less scraping needed)
    if scrape_jaap:
        lg.info("Adding descriptions for Jaap")
        df = scrapers['jaap'].add_jaap_ad_descriptions(df)

    lg.info("Final cleaning of data")
    df = final_cleaning(df)

    # Write data
    outdir = os.path.dirname(data_path)
    outpath = os.path.join(outdir, "scrape_data_filtered.csv")
    lg.info("Writing to :%s" % outpath)
    df.to_csv(outpath, index=False)
    df.to_excel(outpath + ".xlsx", index=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Rental house scraper')
    parser.add_argument('--scrape_all', default=True, type=bool, help='Scrape all websites (override other options)')
    parser.add_argument('--scrape_jaap', default=False, type=bool,
                        help='whether to scrape Jaap')
    parser.add_argument('--scrape_pararius', default=False, type=bool,
                        help='whether to scrape Pararius')
    parser.add_argument('--debug', default=False, type=bool,
                        help='whether to enable debug mode (only scrapes one page per scraper)')

    args = parser.parse_args()
    main(args.scrape_all, args.scrape_jaap, args.scrape_pararius, args.debug)

import datetime
import os
import pickle
import random
import shutil
import time
from abc import ABC
from typing import Dict, Any, List
from urllib.parse import urlparse

import pandas as pd
import tldextract
from fake_useragent import UserAgent
from loguru import logger as lg
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.remote.webelement import WebElement

import chromedriver_autoinstaller
from tqdm import tqdm_pandas, tqdm

from distance.calculators import calculate_distance_addrs


def load_non_empty_driver(cookie_path: str = None) -> WebDriver:
    """
    Load a driver with cookies

    Args:
        cookie_path (str): Path to the cookie file

    Returns:
        WebDriver: The webdriver with cookies
    """
    # The following options should fix robot blocks
    #    see: https://stackoverflow.com/questions/53039551/selenium-webdriver-modifying-navigator-webdriver-flag-to-prevent-selenium-detec/53040904#53040904)
    options = webdriver.ChromeOptions()
    options.add_argument("start-maximized")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    ua = UserAgent()
    user_agent = ua.random
    options.add_argument(f'user-agent={user_agent}')

    cookies_ext_path = './01_data/cookies_extension.crx'
    if os.path.exists(cookies_ext_path):
        lg.debug("Adding ignore cookies banner extension")
        options.add_extension('./01_data/cookies_extension.crx')

    driver = webdriver.Chrome(options=options)

    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    driver.execute_cdp_cmd('Network.setUserAgentOverride', {
        "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.53 Safari/537.36'})
    lg.debug(driver.execute_script("return navigator.userAgent;"))
    driver.get('https://www.httpbin.org/headers')

    if cookie_path:
        lg.debug("Adding cookies")
        cookies = pickle.load(open(cookie_path, "rb"))
        for cookie in cookies:
            driver.add_cookie(cookie)

    return driver


class Scraper(ABC):
    def __init__(self, website_url: str, ad_obj_mapping: dict, web_obj_mapping: dict, data_path: str = "./01_data",
                 driver: WebDriver = None, cookie_path: str = None, debug_mode: str = False):
        """
        Abstract class for all scrapers defining general methods and attributes

        Args:
            website_url (str): The url of the website to scrape
            ad_obj_mapping (dict): The mapping of the ad objects to the xpaths of the ad objects
            web_obj_mapping (dict): The mapping of the website objects to the xpaths of the website objects
            data_path (str, optional): The path to the data folder
            driver (WebDriver): The webdriver to use for scraping
            cookie_path (str, optional): The path to the cookie file
            debug_mode (str, optional): If True, the scraper will not click on the next button
        """
        if not driver:
            driver = self.load_driver(cookie_path)
        self.driver = driver

        self.website_url = website_url
        self.root_url = urlparse(website_url).netloc
        self.domain_name = tldextract.extract(self.root_url).domain
        self.cookie_path = cookie_path

        # todo: check whether all objects are included
        self.ad_obj_mapping = ad_obj_mapping
        self.web_obj_mapping = web_obj_mapping

        # Set data paths
        self.data_path = data_path
        lg.debug("Data path: %s" % data_path)
        self.scrape_time_str = datetime.datetime.now().strftime("%Y%m%d_%H%M")
        filename = self.domain_name + "_" + self.scrape_time_str
        self.raw_scrape_data_path = os.path.join(data_path, "raw", "raw_scrape_data_" + filename + ".csv")
        self.cleaned_scrape_data_path = os.path.join(data_path, "cleaned", "cleaned_scrape_data_" + filename + ".csv")
        self.enriched_scrape_data_path = os.path.join(data_path, "enriched",
                                                      "enriched_scrape_data_" + filename + ".csv")
        self.scrape_data_path = os.path.join(data_path, "scrape_data.csv")
        self.cache_distances_data_path = os.path.join(data_path, "cache_distances_data.csv")

        # Create directories
        os.makedirs(os.path.dirname(self.data_path), exist_ok=True)
        os.makedirs(os.path.dirname(self.raw_scrape_data_path), exist_ok=True)
        os.makedirs(os.path.dirname(self.cleaned_scrape_data_path), exist_ok=True)
        os.makedirs(os.path.dirname(self.enriched_scrape_data_path), exist_ok=True)
        os.makedirs(os.path.dirname(self.scrape_data_path), exist_ok=True)

        self.debug_mode = debug_mode

    @staticmethod
    def load_driver(cookie_path: str) -> WebDriver:
        """
        Load a driver with cookies (automatically installs chromedriver)

        Args:
            cookie_path (str): Path to the cookie file

        Returns:
            WebDriver: The webdriver with cookies
        """
        lg.debug("Using default (Chrome) webdriver, as no driver was passed as an argument")
        chromedriver_autoinstaller.install()
        return load_non_empty_driver(cookie_path)

    def get_next_button_el(self) -> WebElement:
        """
        Get the next button element

        Returns:
            selenium.webdriver.remote.webelement.WebElement: The next button element
        """
        next_page_button_els = self.driver.find_elements_by_xpath(self.web_obj_mapping['next_button'])
        if len(next_page_button_els) == 0:
            lg.debug("No next button found")
            return None
        elif self.debug_mode:
            lg.debug("Debug mode on, not clicking on next button")
            return None
        else:
            return next_page_button_els[0]

    def click_next_button(self, current_retry: int = 0, max_retries: int = 5, wait_time: int = 2):
        """
        Clicks the next button

        Currently implemented as a recursive function. May be improved in the future
        Args:
            current_retry (int, optional): The current retry
            max_retries (int, optional): The maximum number of retries
            wait_time (int, optional): The time to wait between retries

        """
        old_url = self.driver.current_url
        lg.debug("Old url: %s" % old_url)

        try:
            wait_el = WebDriverWait(self.driver, 20).until(
                EC.element_to_be_clickable((By.XPATH, self.web_obj_mapping['next_button'])))

            wait_el.click()

            time.sleep(wait_time)  # wait for page to change
            new_url = self.driver.current_url
            # Check if new url is different than old url, otherwise try to click again
            if new_url == old_url:
                lg.debug("Old url: %s" % old_url)
                lg.debug("New url: %s" % new_url)
                raise RuntimeError("Site did not change after clicking next button")
            if urlparse(new_url).netloc != self.root_url:
                raise RuntimeError("New URL goes to another website: %s" % new_url)
        except (AttributeError, RuntimeError, TimeoutException) as e:
            lg.error(e)
            lg.warning("Clicking next button went wrong, trying again in %s, retry: (%i/%i)" % (
                wait_time, current_retry + 1, max_retries))
            time.sleep(wait_time)

            if current_retry + 1 <= max_retries:
                return self.click_next_button(current_retry=current_retry + 1)
            else:
                raise RuntimeError("Max retries reached for clicking next button")

        lg.debug("New url: %s" % new_url)
        lg.info("Succesfully clicked next button!")

    def scrape_page(self) -> Dict[str, List[str]]:
        """
        Scrapes the current page

        Returns:
            dict: dictionary with scraped data
        """
        result_dict = {}
        ad_els = self.driver.find_elements_by_xpath(self.web_obj_mapping['ad_elements'])
        ad_els = [el for el in ad_els if el.text != ""]  # filter empty ad elements
        lg.debug("Found nr ad elements: %s" % len(ad_els))
        if len(ad_els) == 0:
            raise RuntimeError("No ad elements found")

        # Get relevant sub elements such as title etc.
        for element, xpath_str in self.ad_obj_mapping.items():
            try:
                ad_sub_elements = [el.find_element_by_xpath(xpath_str) for el in ad_els]
                if element == "ad_url":
                    result_dict[element] = [el.get_attribute('href') for el in ad_sub_elements]
                else:
                    result_dict[element] = [el.text for el in ad_sub_elements]
            except NoSuchElementException as e:
                lg.warning("Could not find element for: %s" % element)
                result_dict[element] = [None] * len(ad_els)

        # Check results
        check_values = [len(val) for key, val in result_dict.items()]
        assert len(set(check_values)) == 1, "Not all lists have the same lengths"
        return result_dict

    def backup_data(self):
        """
        Backup the data to a csv file
        """
        if not os.path.exists(self.scrape_data_path):
            lg.debug("No data exists yet")
        else:
            backup_dir = os.path.join(self.data_path, "backups")
            filename, file_ext = os.path.splitext(os.path.basename(self.scrape_data_path))
            new_path = os.path.abspath(os.path.join(backup_dir, filename + "_" + self.scrape_time_str + file_ext))

            # Create directory if it does not exist
            os.makedirs(os.path.dirname(new_path), exist_ok=True)

            lg.debug("Copying data to backup: %s" % new_path)
            shutil.copyfile(self.scrape_data_path, new_path)

    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Cleans the data by converting price, nr_rooms and size_m2 to numeric values

        Args:
            df (pd.DataFrame): The dataframe to clean

        Returns:
            pd.DataFrame: The cleaned dataframe
        """
        df['price'] = pd.to_numeric(df['price'], errors='coerce')
        df['nr_rooms'] = pd.to_numeric(df['price'], errors='coerce')
        df['size_m2'] = pd.to_numeric(df['size_m2'], errors='coerce')
        return df

    def enrich_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Enriches the data by adding some extra columns (e.g. distance to central station)

        Args:
            df (pd.DataFrame): The dataframe to enrich

        Returns:
            pd.DataFrame: The enriched dataframe
        """
        lg.info("Enriching data...")
        # Can be supplemented per individual SubScraper
        station_adres = "Utrecht Centraal Station"
        df['dist_to_station'] = df['address'].apply(
            lambda addr: calculate_distance_addrs(station_adres, addr, cache_filepath=self.cache_distances_data_path))

        df['website'] = self.root_url
        df['scrape_date'] = datetime.datetime.now().isoformat()
        return df

    def append_final_data(self, df, rel_cols=None):
        """
        Appends the data to the final dataframe

        Args:
            df: (pd.DataFrame): The dataframe to append
            rel_cols (List[str], optional): The columns to select for dropping duplicates
        """
        if not rel_cols:
            rel_cols = ["ad_title", "price", "ad_url", "website"]
        if os.path.exists(self.scrape_data_path):
            lg.info("Checking old data and appending new data")
            old_df = pd.read_csv(self.scrape_data_path)
            new_df = pd.concat([old_df, df], axis=0)
            new_df = new_df.drop_duplicates(subset=rel_cols)  # drop any duplicates
        else:
            new_df = df

        lg.info("Writing data to: %s" % self.scrape_data_path)

        new_df.to_csv(self.scrape_data_path, index=False)
        new_df.to_excel(self.scrape_data_path + ".xlsx", index=False)

    def store_data(self, dic: Dict[str, Any]):
        """
        Stores data as a csv file

        Args:
            dic (Dict[str, Any]): The data to store
        """
        df = pd.DataFrame.from_dict(dic)
        df.to_csv(self.raw_scrape_data_path, index=False)

        # Clean data
        df = self.clean_data(df)
        df.to_csv(self.cleaned_scrape_data_path, index=False)

        # Enrich data
        df = self.enrich_data(df)
        df.to_csv(self.enriched_scrape_data_path, index=False)

        self.backup_data()
        # Write final results
        self.append_final_data(df)

    def scrape_all_pages(self, wait_time: int = 2):
        """
        Scrapes all pages on the website

        Args:
            wait_time (int, optional): The time (in seconds) to wait between each page
        """
        lg.info("Going to: %s" % self.website_url)
        self.driver.get(self.website_url)
        all_results = {}
        current_page = 0
        new_button_exists = True
        while new_button_exists:
            lg.debug("Waiting %s seconds, for page to load" % wait_time)
            time.sleep(wait_time)
            lg.debug("Current website: %s" % self.driver.current_url)

            # Scroll to bottom
            html = self.driver.find_element_by_tag_name('html')
            html.send_keys(Keys.END)

            # Update results
            lg.debug("\t Updating results for page: %s" % current_page)
            current_results = self.scrape_page()
            for key, val in current_results.items():
                all_results[key] = all_results.get(key, []) + current_results[key]

            # Go to next website
            new_button_exists = self.get_next_button_el()
            if new_button_exists:
                self.click_next_button()
                current_page += 1

            lg.debug("-----------------------------------------------")

        self.store_data(all_results)


def convert_mappings_to_xpath_class(mapping_dict: Dict[str, str]) -> Dict[str, str]:
    """
    Converts a mapping dict to an xpath class

    Args:
        mapping_dict (Dict[str, str]): The mapping dict to convert

    Returns:
        Dict[str, str]: The converted mapping dict
    """
    for mapping_title, mapping_str in mapping_dict.items():
        mapping_dict[mapping_title] = ".//*[@class='%s']" % mapping_str
    return mapping_dict


class ParariusScraper(Scraper):
    # xpaths to advertisement objects (update this if site is updated)
    AD_OBJECT_MAPPINGS = {'ad_title': ".//*[@class='listing-search-item__link listing-search-item__link--title']",
                          'ad_descr': ".//*[@class='listing-search-item__description']",
                          'ad_url': ".//*[@class='listing-search-item__link listing-search-item__link--title']",
                          'address': ".//*[@class='listing-search-item__location']",
                          'price': ".//*[@class='listing-search-item__price']",
                          'specs': ".//*[@class='illustrated-features illustrated-features--list']"}
    # xpaths to web objects (update this if site is updated)
    WEB_OBJECT_MAPPINGS = {
        'ad_elements': ".//*[@class='listing-search-item listing-search-item--list listing-search-item--for-rent']",
        'next_button': ".//*[@class='pagination__link pagination__link--next']"}

    def __init__(self, debug_mode: bool = False):
        """
        Initializes the ParariusScraper class with custom clean and enrich functions

        Args:
            debug_mode (bool, optional): If True, the scraper will not write to the final dataframe
        """
        website_url = "https://www.pararius.nl/huurwoningen/utrecht/"
        super().__init__(website_url, self.AD_OBJECT_MAPPINGS, self.WEB_OBJECT_MAPPINGS, debug_mode=debug_mode)

    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Cleans the data by fixing columns such as price, size_m2, nr_rooms etc.

        Args:
            df (pd.DataFrame): The dataframe to clean

        Returns:
            pd.DataFrame: The cleaned dataframe
        """
        lg.info("Cleaning data..")
        df['address'] = df['address'].str.lstrip("nieuw ")  # some ads show the 'New' status before the price
        df['price'] = df['price'].str.lstrip("€ ")  # remove euro
        df['price'] = df['price'].str.rstrip(" per maand")
        df['price'] = df['price'].str.replace(".", "")
        df['price'] = pd.to_numeric(df['price'])

        df['specs'] = df['specs'].str.replace("\n", " ")
        df['size_m2'] = df['specs'].str.extract(r'woonopp\. ([0-9]+)')
        df['nr_rooms'] = df['specs'].str.extract(r'kamers ([0-9]+)')
        df['build_year'] = df['specs'].str.extract(r'bouwjaar ([0-9]+)')
        del df['specs']

        df = super().clean_data(df)
        return df


class FundaScraper(Scraper):
    # xpaths to advertisement objects (update this if site is updated)
    AD_OBJECT_MAPPINGS = {'ad_title': ".//*[@class='search-result__header-title fd-m-none']",
                          'ad_url': ".//*[@data-object-url-tracking='resultlist']",
                          'address': ".//*[@class='search-result__header-subtitle fd-m-none']",
                          'price': ".//*[@class='search-result-price']",
                          'specs': ".//*[@class='search-result-kenmerken ']"}
    # xpaths to web objects (update this if site is updated)
    WEB_OBJECT_MAPPINGS = {'ad_elements': ".//*[@class='search-result']",
                           'next_button': ".//*[@rel='next']"}

    def __init__(self, driver: webdriver = None, cookie_path: str = None, debug_mode: bool = False):
        """
        Initializes the FundaScraper class with custom clean and enrich functions

        Args:
            driver (WebDriver, optional): The webdriver to use for scraping
            cookie_path (str, optional): The path to the cookie file to use for scraping
            debug_mode (bool, optional): If True, the scraper will not write to the final dataframe
        """
        lg.warning("THIS SCRAPER DOES NOT WORK WELL, SOLVE BOT CAPTCHA ISSUE")
        if not cookie_path:
            cookie_path = "./01_data/driver_cookies.pkl"
        website_url = "https://www.funda.nl/huur/utrecht/"
        self.website_url = website_url
        if not driver:
            # lg.debug("Using default (Chrome) webdriver, as no driver was passed as an argument")
            self.load_driver(cookie_path=cookie_path)
            # self.load_simple_driver(None)
        self.click_cookie_banner()

        super().__init__(website_url, self.AD_OBJECT_MAPPINGS, self.WEB_OBJECT_MAPPINGS, driver=self.driver,
                         cookie_path=cookie_path, debug_mode=debug_mode)

    def click_cookie_banner(self):
        """
        Clicks the cookie banner if it exists
        """
        lg.info("Accepting cookies first..")
        self.driver.get(self.website_url)
        time.sleep(5)
        button_el = self.driver.find_element_by_xpath(".//*[@id='onetrust-accept-btn-handler']")
        # Scroll to bottom
        html = self.driver.find_element_by_tag_name('html')
        html.send_keys(Keys.END)
        time.sleep(2)
        button_el.click()

    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Cleans the dataframe by fixing price columns and some other columns

        Args:
            df (pd.DataFrame): The dataframe to clean

        Returns:
            pd.DataFrame: The cleaned dataframe

        """
        lg.info("Cleaning data..")
        df['price'] = df['price'].str.lstrip("€ ")  # remove euro
        df['price'] = df['price'].str.rstrip(" /mnd")
        df['price'] = df['price'].str.replace(".", "")
        df['price'] = pd.to_numeric(df['price'])

        df['specs'] = df['specs'].str.replace("\n", " ")
        df['size_m2'] = df['specs'].str.extract(r'([0-9]+) m²')
        df['nr_rooms'] = df['specs'].str.extract(r'([0-9]+) kamers')
        del df['specs']

        df = super().clean_data(df)
        return df


class JaapScraper(Scraper):
    AD_OBJECT_MAPPINGS = {'ad_title': ".//*[@class='property-address-street']",
                          'ad_url': ".//*[@class='property-inner']",
                          'address': ".//*[@class='property-address-zipcity']",
                          'price': ".//*[@class='property-price']",
                          'specs': ".//*[@class='property-features']"}
    WEB_OBJECT_MAPPINGS = {'ad_elements': ".//*[@class='property ']",
                           'next_button': ".//*[@class ='navigation-button ' and @rel='next']"}

    def __init__(self, cookie_path: str = None, debug_mode: str = False):
        """
        Initializes the JaapScraper class with custom clean and enrich functions

        Args:
            cookie_path (str, optional): The path to the cookie file to use for scraping
            debug_mode (bool, optional): If True, the scraper will not write to the final dataframe
        """
        website_url = "https://www.jaap.nl/huurhuizen/utrecht/"
        self.website_url = website_url

        super().__init__(website_url, self.AD_OBJECT_MAPPINGS, self.WEB_OBJECT_MAPPINGS,
                         cookie_path=cookie_path, debug_mode=debug_mode)

    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Cleans the dataframe by fixing price columns and some other columns

        Args:
            df(pd.DataFrame): The dataframe to clean

        Returns:
            pd.DataFrame: The cleaned dataframe
        """
        lg.info("Cleaning data..")
        df['price'] = df['price'].str.lstrip("€ ")  # remove euro
        df['price'] = df['price'].str.rstrip("k.k.")  # remove euro
        df['price'] = df['price'].str.replace(".", "")

        df['specs'] = df['specs'].str.replace("\n", " ")
        df['size_m2'] = df['specs'].str.extract(r'([0-9]+) m²')
        df['nr_rooms'] = df['specs'].str.extract(r'([0-9]+) kamers')
        del df['specs']

        df['ad_url'] = df['ad_url'].str.replace(r'\?.+', '', regex=True)  # fix suffices of urls
        error_row_mask = df['address'] == 'Utrecht'
        df.loc[error_row_mask, 'address'] = df.loc[error_row_mask, 'ad_title']  # fix where the address is only Utrecht

        df = super().clean_data(df)
        return df

    def get_jaap_ad_description(self, url: str, sleep_time: int = 1) -> str:
        """
        Gets the description from a Jaap ad page

        Args:
            url (str): The url of the ad page
            sleep_time (int, optional): The time to sleep between requests

        Returns:
            str: The description of the ad
        """
        self.driver.get(url)
        sleep_time = sleep_time + random.random() * sleep_time  # add randomness to requests
        time.sleep(sleep_time)
        try:
            el = self.driver.find_element_by_xpath(".//*[@class='short-description']")
        except NoSuchElementException as e:
            return None
        return el.text

    def add_jaap_ad_descriptions(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Adds the description of the ad to the dataframe

        Args:
            df (pd.DataFrame): The dataframe to add the descriptions to

        Returns:
            pd.DataFrame: The dataframe with the ad_descr column added
        """
        jaap_ads_mask = df['website'] == 'www.jaap.nl'
        tqdm_pandas(tqdm())
        df.loc[jaap_ads_mask, 'ad_descr'] = df.loc[jaap_ads_mask, 'ad_url'].progress_apply(
            lambda url: self.get_jaap_ad_description(url))
        return df


if __name__ == '__main__':
    scraper = ParariusScraper(debug_mode=True)
    scraper.scrape_all_pages()

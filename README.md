# Rental houses scraper

### Introduction

This code repository contains code to scrape two of the largest dutch rental house platforms.

The goal is to scrape the data, enrich the data (with distances to nearest point of interests such as train stations)
and store it in a database. The data can then be used to quickly filter on the most interesting houses (e.g. low price
per m2, close to train station, etc.).

### Installation

To install the required packages, run the following command:

```
pip install -r requirements.txt
```

### Usage

To run the scraper, run the following command:

```
python 02_code/main.py --scrape_all
```

### License

This code is licensed under the CreativeCommons BY-NC-SA 4.0 license. See the file LICENSE for more information.

## Disclaimer

_This code has been written as part of a hobby project. It is not intended for commercial use. The author is not
responsible for any damage caused by the use of this code. Also, the author is not in any way affiliated with the rental
house platforms that are scraped by this code. Please use this code responsibly._
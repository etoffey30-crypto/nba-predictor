# Bet365 API Scraper

This project is a scraper of the Bet365 API to collect data from live matches, matches and future games using Python. The necessary headers and cookies are configured through a file `.env` for easy customization.

## Table of Contents

-   [Installation](#installation)
-   [Configuration](#configuration)
-   [Usage](#usage)
-   [Files](#files)
-   [Dependencies](#dependencies)
-   [Contributing](#contributing) 
-   [License](#license)

## Installation

1. Clone the repository:

    ```bash
    git clone https://github.com/yourusername/bet365-inplay-api.git
    cd bet365-inplay-api
    ```

2. Create a virtual environment and activate it:

    ```bash
    python -m venv venv
    source venv/bin/activate   # On Windows, use `venv\Scripts\activate`
    ```

3. Install the required dependencies:
    ```bash
    pip install -r requirements.txt
    ```

## Configuration

1. Create a `.env` file in the project root directory and populate it with the following environment variables:

    ```plaintext
    INPLAYDIARYAPI='https://mobile.bet365.com/inplaydiaryapi/schedule?timezone=16&lid=33&zid=0'
    ACCEPT='text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7'
    ACCEPT_ENCODING='gzip, deflate, br, zstd'
    ACCEPT_LANGUAGE='pt-BR,pt;q=0.9,en-GB;q=0.8,en;q=0.7,es-ES;q=0.6,es;q=0.5'
    CACHE_CONTROL='max-age=0'
    CONNECTION='keep-alive'
    COOKIE='your_cookie_here'
    HOST='mobile.bet365.com'
    ORIGIN='https://www.bet365.com'
    PRAGMA='no-cache'
    REFERER='https://www.bet365.com/'
    SEC_CH_UA='"Opera GX";v="109", "Not:A-Brand";v="8", "Chromium";v="123"'
    SEC_CH_UA_MOBILE='?0'
    SEC_CH_UA_PLATFORM='macOS'
    SEC_FETCH_DEST='document'
    SEC_FETCH_MODE='navigate'
    SEC_FETCH_SITE='none'
    SEC_FETCH_USER='?1'
    UPGRADE_INSECURE_REQUESTS='1'
    USER_AGENT='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 OPR/109.0.0.0'
    ```

    Replace `your_cookie_here` with the actual cookie value.

## Usage

1. Run the `api.py` script to fetch live football match data from the Bet365 InPlay API:

    ```bash
    python api.py
    ```

2. The script will print the fetched data to the console.

## Files

-   `inplaydiaryapi.py`: Contains the main class for fetching data from the Bet365 InPlay API.
-   `api.py`: The entry point script to run the data fetching process.
-   `.env`: Configuration file for environment variables.
-   `requirements.txt`: Lists the dependencies required for the project.

## Dependencies

-   `requests`: HTTP library for making requests to the API.
-   `urllib3`: HTTP library for handling retries.
-   `python-dotenv`: Library to load environment variables from a `.env` file.

## Contributing

1. Fork the repository.
2. Create a new branch (`git checkout -b feature-branch`).
3. Make your changes and commit them (`git commit -am 'Add new feature'`).
4. Push to the branch (`git push origin feature-branch`).
5. Create a new Pull Request.

## Licence

This project is licensed under the Attribution 4.0 International License - see the [CC-BY-4.0](CC-BY-4.0) file for details.

## Donations

If this script has been helpful for you, consider making a donation to support our work:

-   $USDT (TRC-20): TP6zpvjt2ZNGfWKPevfp65ZrcbKMWSQXDi

Your donations help us continue developing useful and innovative tools.

## Takk™ Innovate Studio

Leading the Digital Revolution as the Pioneering 100% Artificial Intelligence Team.

-   Copyright (c)
-   Licence: Attribution 4.0 International (CC BY 4.0)
-   Author: David C Cavalcante
-   LinkedIn: https://www.linkedin.com/in/hellodav/
-   Medium: https://medium.com/@davcavalcante/
-   Positive results, rapid innovation
-   URL: https://takk.ag/
-   X: https://twitter.com/takk8is/
-   Medium: https://takk8is.medium.com/

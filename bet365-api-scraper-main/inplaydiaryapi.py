import os
import requests
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

class InPlays:
    def __init__(self):
        # Configura a URL da API e os cabeçalhos necessários para a solicitação
        self.api_url = os.getenv('INPLAYDIARYAPI')
        if not self.api_url:
            raise ValueError("INPLAYDIARYAPI URL must be set in the .env file")

        self.headers = {
            'Accept': os.getenv('ACCEPT'),
            'Accept-Encoding': os.getenv('ACCEPT_ENCODING'),
            'Accept-Language': os.getenv('ACCEPT_LANGUAGE'),
            'Cache-Control': os.getenv('CACHE_CONTROL'),
            'Connection': os.getenv('CONNECTION'),
            'Cookie': os.getenv('COOKIE'),
            'Host': os.getenv('HOST'),
            'Origin': os.getenv('ORIGIN'),
            'Pragma': os.getenv('PRAGMA'),
            'Referer': os.getenv('REFERER'),
            'Sec-Ch-Ua': os.getenv('SEC_CH_UA'),
            'Sec-Ch-Ua-Mobile': os.getenv('SEC_CH_UA_MOBILE'),
            'Sec-Ch-Ua-Platform': os.getenv('SEC_CH_UA_PLATFORM'),
            'Sec-Fetch-Dest': os.getenv('SEC_FETCH_DEST'),
            'Sec-Fetch-Mode': os.getenv('SEC_FETCH_MODE'),
            'Sec-Fetch-Site': os.getenv('SEC_FETCH_SITE'),
            'Sec-Fetch-User': os.getenv('SEC_FETCH_USER'),
            'Upgrade-Insecure-Requests': os.getenv('UPGRADE_INSECURE_REQUESTS'),
            'User-Agent': os.getenv('USER_AGENT'),
            'Sec-WebSocket-Extensions': os.getenv('HEADERS_SEC_WEBSOCKET_EXTENSIONS'),
            'Sec-WebSocket-Protocol': os.getenv('HEADERS_SEC_WEBSOCKET_PROTOCOL'),
            'Sec-WebSocket-Version': os.getenv('HEADERS_SEC_WEBSOCKET_VERSION'),
        }
        # Configura a sessão com tentativas de reconexão
        self.session = requests.Session()
        retries = Retry(total=5, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
        self.session.mount('https://', HTTPAdapter(max_retries=retries))

    def on(self):
        print("Initiating request to bet365 API...")
        try:
            # Realiza a solicitação GET para a API
            response = self.session.get(self.api_url or "", headers=self.headers, timeout=60)
            response.raise_for_status()  # Levanta um erro para códigos de status HTTP >= 400
            print("Received response from bet365 API.")

            # Processa a resposta da API
            data = response.text.split('EV')
            set_array = []
            for item in data:
                if 'Futebol' in item and 'Ao-Vivo' in item:
                    format_data = {
                        'CL': self.extract_data(item, 'CL', 'CI'),
                        'CI': self.extract_data(item, 'CI', 'NA'),
                        'NA': self.extract_data(item, 'NA', 'VI'),
                        'SM': self.extract_data(item, 'SM', 'CN'),
                        'CB': self.extract_data(item, 'CB', 'C1'),
                        'C1': self.extract_data(item, 'C1', 'C2'),
                        'C2': self.extract_data(item, 'C2', 'C3'),
                        'C3': self.extract_data(item, 'C3', 'T1'),
                        'T1': self.extract_data(item, 'T1', 'T2'),
                        'T2': self.extract_data(item, 'T2', 'T3'),
                        'T3': self.extract_data(item, 'T3', 'CR')
                    }
                    set_array.append(format_data)
            print("Data processed successfully.")
            return set_array
        except requests.exceptions.HTTPError as http_err:
            print(f'HTTP error occurred: {http_err}')
            return None
        except requests.exceptions.ConnectionError as conn_err:
            print(f'Connection error occurred: {conn_err}')
            return None
        except requests.exceptions.Timeout as timeout_err:
            print(f'Timeout error occurred: {timeout_err}')
            return None
        except requests.exceptions.RequestException as req_err:
            print(f'Error occurred: {req_err}')
            return None

    @staticmethod
    def extract_data(item, start, end):
        try:
            # Extrai dados entre os índices fornecidos
            start_idx = item.index(start) + len(start) + 1
            end_idx = item.index(end) - 1
            return item[start_idx:end_idx]
        except ValueError:
            print(f"Failed to extract data between {start} and {end}")
            return None

if __name__ == "__main__":
    # Executa o processo principal
    in_plays = InPlays()
    print("Starting inPlays process...")
    result = in_plays.on()
    print("Result:", result)

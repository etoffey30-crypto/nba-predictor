import os
import urllib3
from urllib3.util.retry import Retry
from urllib3.exceptions import HTTPError, MaxRetryError, NewConnectionError
from dotenv import load_dotenv

load_dotenv()

class WebSockets:
    _URLS_CONNECTION = os.getenv('URLS_CONNECTION')
    _URLS_SESSION_ID = os.getenv('URLS_SESSION_ID')

    _HEADERS = {
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

    _DELIMITERS_RECORD = '\x01'
    _DELIMITERS_FIELD = '\x02'
    _DELIMITERS_HANDSHAKE = '\x03'
    _DELIMITERS_MESSAGE = '\x08'

    _ENCODINGS_NONE = '\x00'

    _TYPES_TOPIC_LOAD_MESSAGE = '\x14'
    _TYPES_DELTA_MESSAGE = '\x15'
    _TYPES_SUBSCRIBE = '\x16'
    _TYPES_PING_CLIENT = '\x19'
    _TYPES_TOPIC_STATUS_NOTIFICATION = '\x23'

    _TOPICS = [
        '__host',
        'CONFIG_1_3',
        'LHInPlay_1_3',
        'Media_l1_Z3',
        'XI_1_3',
    ]

    _MESSAGES_SESSION_ID = '%s%sP%s__time,S_%%s%s' % (
        _TYPES_TOPIC_STATUS_NOTIFICATION,
        _DELIMITERS_HANDSHAKE,
        _DELIMITERS_RECORD,
        _ENCODINGS_NONE,
    )

    _MESSAGES_SUBSCRIPTION = '%s%s%%s%s' % (
        _TYPES_SUBSCRIBE,
        _ENCODINGS_NONE,
        _DELIMITERS_RECORD,
    )

    def __init__(self):
        filtered_headers = {k: v for k, v in self._HEADERS.items() if v is not None}
        self.http = urllib3.PoolManager(
            headers=filtered_headers,
            retries=Retry(total=5, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504], raise_on_redirect=False, raise_on_status=False),
            timeout=urllib3.Timeout(connect=5.0, read=5.0)
        )

    def connect(self):
        print('opening connection...')
        self.session_id = self._fetch_session_id()
        if not self.session_id:
            self.disconnect()
            return
        print('session id:', self.session_id)

    def disconnect(self):
        print('closing connection...')

    def _fetch_session_id(self):
        print('fetching session id...')
        if self._URLS_SESSION_ID is None:
            print('URL for session ID is not configured.')
            return None
        try:
            # Alterar a URL para uma mais específica
            session_url = 'https://www.bet365.com/defaultapi/sports-configuration'
            response = self.http.request('GET', session_url, redirect=True)
            print('Response status:', response.status)
            print('Response headers:', response.headers)
            if response.status != 200:
                print('session id: N/A')
                return None
            cookies = response.headers.get('Set-Cookie', '')
            print('Cookies:', cookies)
            session_id = cookies.split('pstk=')[1].split(';')[0] if 'pstk=' in cookies else None
            return session_id
        except (HTTPError, MaxRetryError, NewConnectionError) as e:
            print('Error occurred:', e)
            return None

    def send_message(self, message):
        print('sending message:', repr(message))
        if self._URLS_CONNECTION is None:
            print('URL for connection is not configured.')
            return None
        try:
            response = self.http.request('POST', self._URLS_CONNECTION, body=message.encode('utf-8'), redirect=True)
            print('Response status:', response.status)
            return response.data.decode('utf-8')
        except (HTTPError, MaxRetryError, NewConnectionError) as e:
            print('Error occurred:', e)
            return None

    def subscribe_topics(self):
        if not self.session_id:
            return
        message = self._MESSAGES_SESSION_ID % self.session_id
        self.send_message(message)
        for topic in self._TOPICS:
            subscription_message = self._MESSAGES_SUBSCRIPTION % topic
            self.send_message(subscription_message)

if __name__ == '__main__':
    web_sockets = WebSockets()
    try:
        web_sockets.connect()
        web_sockets.subscribe_topics()
    except KeyboardInterrupt:
        web_sockets.disconnect()

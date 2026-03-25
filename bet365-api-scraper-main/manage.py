import os
import urllib3
from urllib3.util.retry import Retry
from urllib3.exceptions import HTTPError, MaxRetryError, NewConnectionError
from dotenv import load_dotenv
from pprint import pprint
import requests
from websocket import WebSocketApp

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

class WebSockets(WebSocketApp):

    _URLS_CONNECTION = 'wss://premws-pt1.365lpodds.com/zap/'
    _URLS_SESSION_ID = 'https://www.bet365.com/#/IP/B1/'

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
        super(WebSockets, self).__init__(url=self._URLS_CONNECTION, header=self._HEADERS)
        print('WebSockets initialized.')

    def connect(self):
        print('opening connection...')
        self.run_forever()

    def disconnect(self):
        print('closing connection...')
        self.close()

    def on_open(self):
        print('opened connection')
        session_id = self._fetch_session_id()
        print('attempting to fetch session id...')
        if not session_id:
            print('No session id found, disconnecting...')
            self.disconnect()
            return
        message = self._MESSAGES_SESSION_ID % session_id
        self._send(message)

    def on_close(self, ws, close_status_code, close_msg):
        print('closed connection')
        print('code:', close_status_code)
        print('reason:', close_msg)

    def on_message(self, message):
        print('processing received message...')
        message = str(message)
        print('received message:', message)
        message = message.split(self._DELIMITERS_MESSAGE)
        while len(message):
            a = message.pop()
            b = a[0]
            if b == '1':
                print('subscribing to topics...')
                for topic in self._TOPICS:
                    m = self._MESSAGES_SUBSCRIPTION % topic
                    self._send(m)
                continue
            if b in [self._TYPES_TOPIC_LOAD_MESSAGE, self._TYPES_DELTA_MESSAGE]:
                print('processing topic load or delta message...')
                matches = a.split(self._DELIMITERS_RECORD)
                path_config = matches[0].split(self._DELIMITERS_FIELD)
                pair = path_config.pop()
                read_it_message = pair[1:]
                l = a[(len(matches[0]) + 1):]
                pprint([read_it_message, l], width=1)
                continue

    def _send(self, message):
        print('sending message:', repr(message))
        self.send(message)

    def _fetch_session_id(self):
        print('fetching session id...')
        response = None
        try:
            response = requests.get(self._URLS_SESSION_ID)
        except Exception as e:
            print('Error fetching session id:', str(e))
        if not response:
            print('session id: N/A')
            return None
        session_id = response.cookies.get('pstk', None)
        print('session id:', session_id)
        return session_id

if __name__ == '__main__':
    web_sockets = WebSockets()
    try:
        web_sockets.connect()
    except KeyboardInterrupt:
        print('Interrupt received, disconnecting...')
        web_sockets.disconnect()

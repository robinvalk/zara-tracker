import time
import json
import requests

from zara_tracker.settings import TG_TOKEN, TG_CHAT_ID, TG_THREAD_W, TG_THREAD_M, TG_THREAD_K, TG_THREAD_B, TG_THREAD_Z

def send_telegram_message(market, images, message):
    print("Sending message on telegram")

    url = f'https://api.telegram.org/bot{TG_TOKEN}/sendMediaGroup'
    params = {
        'chat_id': TG_CHAT_ID,
        'message_thread_id': determine_thread_id(market),
        'media': [],
    }

    for path in images:
        params['media'].append({'type': 'photo', 'media': path, 'parse_mode': 'HTML'})

    params['media'][0]['caption'] = message
    params['media'][0]['parse_mode'] = 'Markdown'
    params['media'] = json.dumps(params['media'])

    r = requests.post(url, data=params)
    if r.status_code != 200:
        data = r.json()
        time_to_sleep = data['parameters']['retry_after']
        time.sleep(time_to_sleep)
        send_telegram_message(market, images, message)

def determine_thread_id(market: str):
    return {
        "WOMAN": TG_THREAD_W,
        "MAN": TG_THREAD_M,
        "KID": TG_THREAD_K,
        "BEAUTY": TG_THREAD_B,
        "ZARA ORIGINS": TG_THREAD_Z,
    }[market]


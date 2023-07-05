import time
import pickle
import requests
from os import path
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException


IS_DEBUG = False
LOGIN_URL = 'https://login.taobao.com'
COOKIE_FILE = 'cookies.pkl'
COOKIE_EXPIRED_FILE = 'cookie_expired_time.pkl'

config = {
    'targetUrl': 'https://cart.taobao.com/cart.htm?from=btop', # 购物车地址
    'targetTime': '2023-07-05 20:00:00', # 抢购时间
    'maxRetry': 3, # 没抢到时的最大重试次数
    'leadTime': 150, # 提前多少毫秒开始抢购
}


def create_webdriver():
    options = webdriver.ChromeOptions()

    if not IS_DEBUG:
        options.add_experimental_option("detach", True)
    
    options.add_experimental_option('excludeSwitches', ['enable-logging', 'enable-automation'])
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument("--disable-images")
    options.add_argument("--disable-background-timer-throttling")
    options.add_experimental_option(
        'prefs',
        {
            'credientials_enable_service': False,
            'profile.password_manager_enabled': False
        }
    )

    wd = webdriver.Chrome(options=options)
    stealth = open('stealth.min.js', encoding='utf-8').read()
    wd.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                       'source': stealth})
    wd.implicitly_wait(10)
    wd.maximize_window()
    
    return wd


wd = create_webdriver()


def main():
    login()

    wd.get(config['targetUrl'])
    
    scheduler()

    if IS_DEBUG:
        wd.quit()



def login():
    wd.get(LOGIN_URL)

    if path.exists(COOKIE_EXPIRED_FILE):
        cookie_expired_time = pickle.load(open(COOKIE_EXPIRED_FILE, 'rb'))

    if path.exists(COOKIE_FILE) and cookie_expired_time and datetime.now() < cookie_expired_time:
        login_by_cookies()
    else:
        login_by_manual()
    print('登录成功...')


def login_by_manual():
    print('请手动登录...')
    while True:
        if not LOGIN_URL in wd.current_url:
            break
    
    pickle.dump(wd.get_cookies(), open(COOKIE_FILE, 'wb'))
    set_cookie_expired_time()


def login_by_cookies():
    print('正在使用缓存登录...')
    for cookie in pickle.load(open(COOKIE_FILE, 'rb')):
        wd.add_cookie({
            'domain': cookie['domain'],
            'name': cookie['name'],
            'value': cookie['value'],
        })
        

def set_cookie_expired_time():
    expired_time = datetime.now() + timedelta(minutes=15)
    pickle.dump(expired_time, open(COOKIE_EXPIRED_FILE, 'wb'))


def check_all_goods():
    try:
        check_all = wd.find_element(By.XPATH, '//*[@id="J_SelectAll1"]/div/label')
    except NoSuchElementException:
        print('购物车空空如也，请添加商品后重新运行脚本...')
        wd.quit()
        return
    else:
        check_all.click()


def buy(retry = config['maxRetry']):
    wd.find_element(By.XPATH, '//a[@class="submit-btn"]').click()

    if IS_DEBUG:
        return
    
    wd.find_element(By.CSS_SELECTOR, '.go-btn').click()

    if '支付宝' in wd.title:
        print('抢购成功...')
    else:
        print('抢购失败...')


def scheduler():
    now = get_taobao_time()
    target_time = datetime.strptime(config['targetTime'], '%Y-%m-%d %H:%M:%S')
    
    if now >= target_time:
        print('开始抢购...')
        check_all_goods()
        buy()
    else:
        wake_up_time = 60 * 10
        diff = (target_time - now).total_seconds()
        print(f'距离抢购时间还有 {diff} 秒')
        
        if diff > wake_up_time:
            time.sleep(wake_up_time)
            wd.refresh()
            scheduler()
            set_cookie_expired_time()
            return
        
        check_all_goods()
        print('等待抢购...')
        time.sleep(diff)
        print('开始抢购...')
        buy()
        set_cookie_expired_time()



def get_taobao_time():
    taobao_time_url = 'http://api.m.taobao.com/rest/api3.do?api=mtop.common.getTimestamp'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.5005.61 Safari/537.36'
    }
    start_time = datetime.now()
    taobao_time_stamp = requests.get(url=taobao_time_url, headers=headers).json()['data']['t']
    req_time = (datetime.now() - start_time).total_seconds()
    
    return datetime.fromtimestamp(int(taobao_time_stamp) / 1000 + req_time)


if __name__ == '__main__':
    main()
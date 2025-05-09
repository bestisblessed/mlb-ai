import os
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

today = datetime.now().strftime("%Y-%m-%d")
os.makedirs(f'data/{today}', exist_ok=True)

options = webdriver.ChromeOptions()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
driver = webdriver.Chrome(options=options)

try:
    driver.get("https://www.bovada.lv/sports/baseball/mlb")
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='/mlb/']")))
    time.sleep(2)
    links = {
        l.get_attribute('href') 
        for l in driver.find_elements(By.CSS_SELECTOR, "a[href*='/mlb/']")
        if l.get_attribute('href').split('-')[-1].isdigit()
    }
    with open(f'data/{today}/bovada_game_links.csv', 'w') as f:
        f.writelines([f'{url}\n' for url in links])
    print(f"Saved {len(links)} game links to data/{today}/bovada_game_links.csv")
finally:
    driver.quit()
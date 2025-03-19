from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from datetime import datetime
import time
import json

class Hypermarket:
    def __init__(self, name, link):
        self.name = name
        self.link = link

class BrochureParser:

    URL = "https://www.prospektmaschine.de/hypermarkte"

    def __init__(self, output_file = "data.json"):
        self.output_file = output_file
        
        self.chrome_options = Options()
        self.chrome_options.add_argument("--disable-extensions")
        self.chrome_options.add_argument("--disable-gpu")
        self.chrome_options.add_argument("--no-sandbox")
        self.chrome_options.add_argument("--disable-dev-shm-usage")

        self.driver = webdriver.Chrome(options=self.chrome_options)
    
    def openPage(self, url):
        self.driver.get(url)
        WebDriverWait(self.driver, 10).until(
            lambda driver: self.driver.execute_script('return document.readyState') == 'complete'
        )
        time.sleep(2) # just in case if the page is taking longer to load

    def loadHypermarkets(self):
        print("Opening provided link...")
        self.openPage(self.URL)

        # load hypermarkets
        a_elements = self.driver.find_elements(By.XPATH, '//*[@id="left-category-shops"]/li/a')
        hypermarkets = []
        for i in a_elements:
            text = i.get_attribute("innerText").strip()
            link = i.get_attribute("href")
            hypermarkets.append(Hypermarket(text, link))
        
        print(f"Found {len(hypermarkets)} hypermarkets")
        
        return hypermarkets
    
    def parseBrochureDate(self, date):
        if " - " in date:
            data = date.split(" - ")
            valid_from = datetime.strptime(data[0].strip(), "%d.%m.%Y").date()
            valid_to = datetime.strptime(data[1].strip(), "%d.%m.%Y").date()
        else:
            data = date.split()[-1]
            valid_from = datetime.strptime(data.strip(), "%d.%m.%Y").date()
            valid_to = None
        
        return valid_from, valid_to

    def processBrochures(self, hypermarket):
        self.openPage(hypermarket.link)

        # get all brochures from hypermarket
        brochures = self.driver.find_elements(By.CSS_SELECTOR, "div.clearfix.skeleton-loader.done div div a p small:first-of-type")
        print(f"Found {len(brochures)} brochures")

        today = datetime.now().date()
        count = 0

        for i, brochure in enumerate(brochures):
            text = brochure.get_attribute("innerText")
            print(f"Brochure {i+1}: {text}")
            
            if text is None or text == "":
                print(f"Brochure {i+1} does not contain date: {hypermarket.name}")
                continue

            try:
                # fill other info
                title = self.driver.find_elements(By.CSS_SELECTOR, 'div.clearfix.skeleton-loader.done div div a p strong')[i].get_attribute("innerText")
                shop_name = hypermarket.name
                thumbnail = self.driver.find_elements(By.CSS_SELECTOR, 'div.clearfix.skeleton-loader.done div div a div picture img')[i].get_attribute("src")

                valid_from, valid_to = self.parseBrochureDate(text)

                # check if brochure is currently active
                is_active = False
                if valid_from and valid_to:
                    is_active = valid_from <= today and today <= valid_to
                elif valid_from:
                    is_active = valid_from <= today

                # add it to json
                if is_active:
                    date_range = f"{valid_from} to {valid_to}" if valid_to else f"from {valid_from}"
                    print(f"VALID: {date_range} (Currently active)")
                    self.addToJSON(title, thumbnail, shop_name, valid_from, valid_to)
                    count += 1
            except Exception as e:
                print(f"Error processing brochure {i+1}: {e}")
        
        return count

    def addToJSON(self, title, thumbnail, shop_name, valid_from, valid_to):
        try:
            with open(self.output_file, "r", encoding="utf-8") as file:
                data = json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            data = []

        new_item = {
            "title": f"{title}",
            "thumbnail": f"{thumbnail}",
            "shop_name": f"{shop_name}",
            "valid_from": f"{valid_from}",
            "valid_to": f"{valid_to}",
            "parsed_time": f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        }
        data.append(new_item)

        with open(self.output_file, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=4)

        print("Data added successfully.")

    def run(self):
        try:
            print("Starting brochure parsing...")
            hypermarkets = self.loadHypermarkets()

            total_brochures = 0
            for i, hypermarket in enumerate(hypermarkets):
                print(f"\nProcessing {i+1}/{len(hypermarkets)}: {hypermarket.name}")
                brochures_added = self.processBrochures(hypermarket)
                total_brochures += brochures_added

            print(f"\nParsing complete. Added {total_brochures} active brochures to {self.output_file}")
        except Exception as e:
            print(f"Error during parsing: {e}")
        finally:
            print("\nClosing the browser...")
            self.driver.quit()

if __name__ == "__main__":
    parser = BrochureParser()
    parser.run()
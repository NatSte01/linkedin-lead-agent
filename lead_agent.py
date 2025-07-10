# lead_agent.py

import os
import time
import csv
import json
import random
import logging
import traceback

import ollama
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- Configuration ---
load_dotenv()

# Required: Set these in your .env file
LINKEDIN_EMAIL = os.getenv("LINKEDIN_EMAIL")
LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD")

# Agent & LLM Configuration
AGENT_GOAL = "Find 20 qualified leads for a Virtual Assistant business and save a direct link to the post. A qualified lead is someone asking for VA recommendations or stating a need for admin help."
OLLAMA_MODEL_NAME = "deepseek-r1:8b" # Or "llama3", "mistral", etc.
LEAD_GOAL_COUNT = 20
OUTPUT_FILE = "linkedin_leads.csv"

# Search & Scraping Configuration
WEBDRIVER_TIMEOUT = 20
MAX_SCROLLS_PER_SEARCH = 15
DATE_FILTER = "past-24h" # Options: "past-24h", "past-week", "past-month", "any"

SEARCH_QUERIES = [
    '"looking for a virtual assistant"',
    '"virtual assistant recommendation"',
    '"seeking administrative support"',
    '"need help with admin tasks"',
    '"hiring a VA"'
]

# --- End of Configuration ---


SELECTORS = {
    "login_username_field": (By.ID, "username"),
    "login_password_field": (By.ID, "password"),
    "login_submit_button": (By.XPATH, "//button[@type='submit']"),
    "search_bar": (By.XPATH, "//input[contains(@class, 'search-global-typeahead__input')]"),
    "posts_filter_button": (By.XPATH, "//button[text()='Posts']"),
    "post_container": (By.XPATH, "//div[contains(@class, 'feed-shared-update-v2') and @data-urn]"),
    "post_text_content": (By.XPATH, ".//div[contains(@class, 'update-components-text')]//span[@dir='ltr']"),
    "see_more_button": (By.XPATH, ".//button[contains(@class, 'feed-shared-inline-show-more-text__see-more-less-toggle')]"),
    "captcha_page_identifier": (By.ID, "captcha-internal"),
    "post_author_name": (By.XPATH, ".//span[contains(@class, 'feed-shared-actor__name')]//span[@aria-hidden='true']"),
    "date_filter_button": (By.XPATH, "//button[text()='Date posted']"),
    "date_filter_option_template": (By.XPATH, f"//label[contains(@for, 'date-posted-{DATE_FILTER}')]"),
    "date_filter_apply_button": (By.XPATH, "//div[contains(@class,'reusables-filters-modal-artdeco-modal__action-bar')]/button[contains(@class, 'artdeco-button--primary')]")
}

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')

class LinkedInLeadAgent:
    def __init__(self, email, password, ollama_model):
        self.email = email
        self.password = password
        self.ollama_model = ollama_model
        self.driver = self._setup_driver()
        self.actions = ActionChains(self.driver) if self.driver else None
        self.ollama_client = self._get_ollama_client()
        self.leads_found = 0
        self.seen_post_links = set()
        self._load_previous_leads()

    def _load_previous_leads(self):
        if not os.path.exists(OUTPUT_FILE):
            logging.info(f"Output file '{OUTPUT_FILE}' not found. Starting fresh.")
            return

        try:
            with open(OUTPUT_FILE, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if 'link' in row:
                        self.seen_post_links.add(row['link'])

            self.leads_found = len(self.seen_post_links)
            logging.info(f"Resuming session. Loaded {self.leads_found} previously found leads.")
        except Exception as e:
            logging.error(f"Could not load previous leads from '{OUTPUT_FILE}'. Starting fresh. Error: {e}")
            self.leads_found = 0
            self.seen_post_links = set()

    def _setup_driver(self):
        logging.info("Setting up new Chrome WebDriver instance...")
        options = webdriver.ChromeOptions()
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        options.add_argument(f'user-agent={user_agent}')
        options.add_argument("--start-maximized")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        options.add_experimental_option('useAutomationExtension', False)

        try:
            chrome_service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=chrome_service, options=options)
            logging.info("WebDriver setup complete.")
            return driver
        except Exception as e:
            logging.error(f"Failed to setup WebDriver: {e}")
            logging.error(traceback.format_exc())
            return None

    def _get_ollama_client(self):
        try:
            client = ollama.Client(host='http://localhost:11434', timeout=60)
            client.list()
            logging.info("Successfully connected to Ollama server.")
            return client
        except Exception as e:
            logging.critical(f"Could not connect to the Ollama server. Please ensure Ollama is running. Error: {e}")
            return None

    def _human_like_pause(self, min_seconds=0.5, max_seconds=1.5):
        time.sleep(random.uniform(min_seconds, max_seconds))

    def _human_like_click(self, element):
        self.actions.move_to_element(element).pause(random.uniform(0.2, 0.6)).click().perform()

    def _human_like_scroll(self):
        scroll_height = f"window.innerHeight * {random.uniform(0.7, 0.9)}"
        self.driver.execute_script(f"window.scrollBy(0, {scroll_height});")

    def _handle_captcha(self):
        try:
            self.driver.find_element(*SELECTORS["captcha_page_identifier"])
            logging.warning("\n---! CAPTCHA DETECTED !---")
            input("Please solve the CAPTCHA and press Enter in this console to continue...")
            logging.info("Resuming script...")
        except NoSuchElementException:
            pass

    def run(self):
        if not all([self.driver, self.ollama_client, self.actions, self.email, self.password]):
            logging.error("Agent cannot run due to setup failure. Exiting.")
            return
        try:
            self._login()
            self._search_for_leads()
        except Exception as e:
            logging.error(f"The agent encountered a fatal error: {e}")
            logging.error(traceback.format_exc())
        finally:
            self._cleanup()

    def _login(self):
        logging.info("Navigating to LinkedIn login page...")
        self.driver.get("https://www.linkedin.com/login")
        self._handle_captcha()
        logging.info("Entering credentials...")
        WebDriverWait(self.driver, WEBDRIVER_TIMEOUT).until(EC.presence_of_element_located(SELECTORS["login_username_field"])).send_keys(self.email)
        self.driver.find_element(*SELECTORS["login_password_field"]).send_keys(self.password)
        logging.info("Submitting login form...")
        self.driver.find_element(*SELECTORS["login_submit_button"]).click()
        self._handle_captcha()
        WebDriverWait(self.driver, WEBDRIVER_TIMEOUT * 2).until(EC.url_contains("feed"))
        logging.info("Login successful.")

    def _search_for_leads(self):
        for query in SEARCH_QUERIES:
            if self.leads_found >= LEAD_GOAL_COUNT: break
            logging.info(f"\n--- Starting new search for: {query} ---")
            try:
                self._perform_search(query)
                self._filter_by_posts()
                self._filter_by_date()
                self._scan_and_process_posts()
            except Exception as e:
                logging.error(f"Failed to process search query '{query}'. Moving to next one. Error: {e}")
                self.driver.get("https://www.linkedin.com/feed/")
                self._human_like_pause(3, 5)
                continue
        if self.leads_found < LEAD_GOAL_COUNT:
            logging.info(f"All searches processed. Found {self.leads_found}/{LEAD_GOAL_COUNT} total leads.")

    def _perform_search(self, query):
        try:
            search_bar = WebDriverWait(self.driver, WEBDRIVER_TIMEOUT).until(EC.element_to_be_clickable(SELECTORS["search_bar"]))
            self._human_like_click(search_bar)
            search_bar.clear()
            for char in query:
                search_bar.send_keys(char)
                time.sleep(random.uniform(0.08, 0.2))
            search_bar.send_keys(Keys.ENTER)
            WebDriverWait(self.driver, WEBDRIVER_TIMEOUT).until(EC.url_contains("search"))
            logging.info(f"Search for '{query}' executed.")
        except TimeoutException:
            logging.error("Could not find or interact with the search bar. Skipping query.")
            raise

    def _filter_by_posts(self):
        try:
            logging.info("Applying 'Posts' filter...")
            posts_button = WebDriverWait(self.driver, WEBDRIVER_TIMEOUT).until(EC.element_to_be_clickable(SELECTORS["posts_filter_button"]))
            self._human_like_click(posts_button)
            WebDriverWait(self.driver, WEBDRIVER_TIMEOUT).until(EC.url_contains("results/content"))
            logging.info("Filtered by 'Posts'.")
            self._human_like_pause(2, 3)
        except TimeoutException:
            logging.error("Could not click 'Posts' filter button.")
            raise

    def _filter_by_date(self):
        if not DATE_FILTER or DATE_FILTER == "any":
            logging.info("No date filter specified or set to 'any'. Skipping.")
            return

        try:
            logging.info(f"Applying date filter: '{DATE_FILTER}'...")
            date_button = WebDriverWait(self.driver, WEBDRIVER_TIMEOUT).until(
                EC.element_to_be_clickable(SELECTORS["date_filter_button"])
            )
            self._human_like_click(date_button)
            self._human_like_pause(1, 2)

            option_radio = WebDriverWait(self.driver, WEBDRIVER_TIMEOUT).until(
                EC.element_to_be_clickable(SELECTORS["date_filter_option_template"])
            )
            self._human_like_click(option_radio)
            self._human_like_pause(0.5, 1)

            apply_button = self.driver.find_element(*SELECTORS["date_filter_apply_button"])
            self._human_like_click(apply_button)

            WebDriverWait(self.driver, WEBDRIVER_TIMEOUT).until(lambda d: "datePosted" in d.current_url)
            logging.info(f"Successfully applied date filter '{DATE_FILTER}'.")
            self._human_like_pause(2, 3)

        except TimeoutException:
            logging.error("Could not apply date filter. The selectors might need updating. Continuing without it.")
        except Exception as e:
            logging.error(f"An unexpected error occurred while filtering by date: {e}")

    def _scan_and_process_posts(self):
        scroll_count = 0
        last_height = self.driver.execute_script("return document.body.scrollHeight")

        while scroll_count < MAX_SCROLLS_PER_SEARCH and self.leads_found < LEAD_GOAL_COUNT:
            posts = self.driver.find_elements(*SELECTORS["post_container"])
            logging.info(f"Found {len(posts)} potential post containers on screen.")

            new_posts_processed = 0
            for post_container in posts:
                if self.leads_found >= LEAD_GOAL_COUNT: break

                try:
                    urn = post_container.get_attribute('data-urn')
                    if not urn:
                        logging.warning("Found a post-like container without a 'data-urn'. Skipping.")
                        continue

                    post_link = f"https://www.linkedin.com/feed/update/{urn}/"

                    if post_link in self.seen_post_links:
                        continue

                    new_posts_processed += 1
                    self.seen_post_links.add(post_link)
                    logging.info(f"Processing new post: {post_link}")

                    try:
                        see_more = post_container.find_element(*SELECTORS["see_more_button"])
                        if see_more.is_displayed():
                            self._human_like_click(see_more)
                            self._human_like_pause(0.5, 1)
                    except NoSuchElementException:
                        pass

                    full_text = "Not found"
                    try:
                        text_container = post_container.find_element(*SELECTORS["post_text_content"])
                        full_text = text_container.text.strip().replace('\n', ' ')
                    except NoSuchElementException:
                        logging.warning(f"Could not find text for post {post_link}. Skipping text content.")

                    author_name = "Not found"
                    try:
                        author_element = post_container.find_element(*SELECTORS["post_author_name"])
                        author_name = author_element.text.strip()
                    except NoSuchElementException:
                        logging.warning(f"Could not find author for post {post_link}.")

                    if not full_text or full_text == "Not found":
                        logging.info(f"Skipping post ({post_link}) due to empty text.")
                        continue

                    qualification = self._qualify_post_with_llm(full_text)
                    if qualification.get("is_lead"):
                        self.leads_found += 1
                        reason = qualification.get("reason", "No reason provided.")
                        logging.info(f"[LEAD FOUND!] ({self.leads_found}/{LEAD_GOAL_COUNT}) Author: {author_name}, Reason: {reason}")
                        self._save_lead_to_csv(link=post_link, reason=reason, author=author_name, text=full_text)
                    else:
                        logging.info(f"Post is not a lead. Reason: {qualification.get('reason')}")

                    self._human_like_pause(1, 2)

                except Exception as e:
                    logging.warning(f"Could not fully process a post element. Skipping. Error: {e}")
                    continue

            scroll_count += 1
            if self.leads_found >= LEAD_GOAL_COUNT: break

            logging.info(f"Scroll {scroll_count}/{MAX_SCROLLS_PER_SEARCH}. Scrolling down...")
            self._human_like_scroll()
            self._human_like_pause(2, 4)

            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height and new_posts_processed == 0:
                logging.info("Scrolled, but no new posts were loaded. Reached the end of results for this query.")
                break
            last_height = new_height

    def _qualify_post_with_llm(self, post_text):
        logging.debug(f"Qualifying post: '{post_text[:100]}...'")
        prompt = f"""You are a lead qualification expert for a Virtual Assistant business. A qualified lead is a LinkedIn post where an individual or small business owner is EXPLICITLY asking for recommendations for a Virtual Assistant, looking to hire a VA, or stating a clear, direct need for administrative help.
        CRITICAL: Ignore posts that are just promotions FROM a VA or VA company. Ignore general business advice. Ignore posts from large corporate recruiters. Focus only on direct requests for help from potential clients.
        Analyze the following post text. Is it a qualified lead?
        Post: "{post_text}"
        Respond ONLY in JSON with two keys: "is_lead" (boolean) and "reason" (a brief string justification). Example: {{"is_lead": true, "reason": "The user is asking for VA recommendations."}}"""
        try:
            response = self.ollama_client.chat(model=self.ollama_model, messages=[{'role': 'user', 'content': prompt}], format='json')
            return json.loads(response['message']['content'])
        except Exception as e:
            logging.error(f"LLM qualification failed: {e}")
            return {"is_lead": False, "reason": "LLM Error"}

    def _save_lead_to_csv(self, link, reason, author, text):
        try:
            file_exists = os.path.isfile(OUTPUT_FILE)
            fieldnames = ["link", "author", "ai_reason", "post_text"]
            with open(OUTPUT_FILE, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                if not file_exists: writer.writeheader()
                writer.writerow({
                    "link": link,
                    "author": author,
                    "ai_reason": reason,
                    "post_text": text
                })
            logging.info(f"Lead data saved to {OUTPUT_FILE}")
        except IOError as e:
            logging.error(f"Could not write to file {OUTPUT_FILE}: {e}")

    def _cleanup(self):
        if self.driver:
            logging.info("Cleaning up and closing WebDriver.")
            self.driver.quit()

if __name__ == "__main__":
    if not all([LINKEDIN_EMAIL, LINKEDIN_PASSWORD]):
        logging.critical("CRITICAL: Set LINKEDIN_EMAIL and LINKEDIN_PASSWORD in your .env file.")
    else:
        logging.info(f"--- Starting LinkedIn Lead Agent ---")
        logging.info(f"Goal: {AGENT_GOAL}")
        agent = LinkedInLeadAgent(
            email=LINKEDIN_EMAIL,
            password=LINKEDIN_PASSWORD,
            ollama_model=OLLAMA_MODEL_NAME
        )
        agent.run()
        logging.info("--- Agent Session Finished ---")

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.service import Service
from selenium.common.exceptions import NoSuchAttributeException, TimeoutException
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.firefox_profile import FirefoxProfile
import tempfile
import shutil
import time
import os
import requests
import sys
invalid_chars = '/\\:*?"<>|'

service = Service('./geckodriver')

#Using firefox profile so it is logged in to site.
# prompting user for firefox profile ID
user_prof = open("firefox_profile.txt").read()
if user_prof == "":
    print("hint: Go to about:profiles in firefox.")
    print("example where fgybejjt is the profile ID: fgybejjt.default")
    print("You have to be logged into Pixiv on the profile!")
    user_prof = input("Enter your firefox non-release profile ID:\n").strip()
    open("firefox_profile.txt", "w").write(str(user_prof))
else:
    print(f"Running on profile: {user_prof}")
#find the first partof the profile path and the cache path based on OS
if os.name == "nt":
    path = os.path.join(os.environ['APPDATA'], 'Mozilla', 'Firefox', 'Profiles')
    profile_path=os.path.join(path, f"{user_prof}.default")
    cache = os.path.join(os.environ['LOCALAPPDATA'], 'Temp', 'selenium_firefox_cache')
elif os.name == "posix":
    profile_path=os.path.expanduser(f"~/.mozilla/firefox/{user_prof}.default")
    cache = os.path.expanduser('~/.cache/selenium_firefox_cache')

#delete cached files from last use if they were not deleted
if os.path.exists(cache):
    shutil.rmtree(cache)
    os.makedirs(cache, exist_ok=True)
else:
    os.makedirs(cache, exist_ok=True)

#set up the profile
profile = FirefoxProfile(profile_path)
options = Options()
options.profile = profile
profile.set_preference("browser.cache.disk.enable", True)
profile.set_preference("browser.cache.disk.parent_directory", cache)
driver = webdriver.Firefox(service=service, options=options)
wait = WebDriverWait(driver, 20)
driver.implicitly_wait(10)

#get user input
try:
    choice = int(input("Would you like to scrape from a creator's page, or your own bookmarked posts?\n1. Creator's page  2. My bookmarks\n\n"))
except ValueError:
    print("\n\nThat isn't a valid option.\n\n")
    try:
        choice = int(input("Would you like to scrape from a creator's page, or your own bookmarked posts?\n1. Creator's page  2. My bookmarks\n\n"))
    except:
        choice = None
        driver.quit()
        shutil.rmtree(cache)
        sys.exit()
if choice == 1:
    print("Example where 113849413 is the ID: https://www.pixiv.net/en/users/113849413")
    user_id = input("Enter pixiv creator ID:\n").strip()
    url = f"https://www.pixiv.net/en/users/{user_id}/illustrations"
elif choice == 2:
    print("Example where 113849413 is the ID: https://www.pixiv.net/en/users/113849413")
    user_id = input("Provide your pixiv user ID:\n").strip()
    url = f"https://www.pixiv.net/en/users/{user_id}/bookmarks/artworks"
else:
    url = None
    print("\n\nThat isn't a valid option.\n\n")
    driver.quit()
    shutil.rmtree(cache)
    sys.exit()
tag = input("Enter tag to filter by below (leave blank for no filter):\n")
print("Please wait...")

#start
MAIN_URL = url
driver.get(MAIN_URL)
time.sleep(3)

#get the name of the user
creator_name = None
try:
    creator_name_element = driver.find_element(By.CLASS_NAME, "zmLZa")
except NoSuchElementException:
    creator_name_element = None
if creator_name_element:
    creator_name = creator_name_element.get_attribute("innerHTML")
    if creator_name:
        os.makedirs(creator_name, exist_ok=True)
    else:
        os.makedirs(user_id, exist_ok=True)

#try to find names of the tags until a match
#The tag element is different if there is japanese translation alongside it
def identify_tag(tags):
    for item in tags:
        tag_href = item.get_attribute("href")
        if tag_href:
            if f"{tag}".lower() in tag_href.lower():
                driver.get(tag_href)
                time.sleep(2)
                return True

#find tag
if tag:
    tags = driver.find_elements(By.CLASS_NAME, "nXebZ")
    find = None
    while not find:
        find = identify_tag(tags)
        if not find:
            tag = input("Could not find tag (note: translated tags won't work). Try again (leave blank to skip):\n")
            if not tag:
                find = True

#get elements for navigation
#Gets list of links for the posts
def list_posts():
    try:
        fNOdSq_elements = driver.find_elements(By.CLASS_NAME, "fNOdSq")
    except NoSuchElementException:
        fNOdSq_elements = None
    if fNOdSq_elements:
        fNOdSq_hrefs = []
        for item in fNOdSq_elements:
            href = item.get_attribute("href")
            fNOdSq_hrefs.append(href)
    else:
        fNOdSq_hrefs = None
    return fNOdSq_hrefs
#Gets list of links for the next page buttons
try:
    buYbfM_elements = driver.find_elements(By.CLASS_NAME, "buYbfM")
except NoSuchElementException:
    buYbfM_elements = None
if buYbfM_elements:
    buYbfM_hrefs = []
    for item in buYbfM_elements:
        href = item.get_attribute("href")
        buYbfM_hrefs.append(href)
else:
    buYbfM_hrefs = None

#functions
counter = 0 #count downloads
#downloads the image, making server think the request comes from a context menu aciton
def get_image(src, title, i):
    print("getting image...")
    global counter
    headers = {
        "User-Agent": driver.execute_script("return navigator.userAgent;"),
        "Referer": driver.current_url
    }
    try:
        response = requests.get(src, headers=headers, stream=True, timeout=20)
    except requests.exceptions.ConnectionError:
        print("Pausing scraping for 5 mins due to server complaint")
        time.sleep(5*60)
        response = requests.get(src, headers=headers, stream=True, timeout=20)
    if creator_name:
        file = f"{creator_name}/{title}_{i}.png"
        if not os.path.exists(file):
            with open(file, "wb") as image:
                image.write(response.content)
            counter += 1
        elif os.path.exists(file):
            print("Image exists; skipping...")
    else:
        file = f"{user_id}/{title}_{i}.png"
        if not os.path.exists(file):
            with open(f"{user_id}/{title}_{i}.png", "wb") as image:
                image.write(response.content)
            counter += 1
        elif os.path.exists(file):
            print("Image exists; skipping...")
#navigate from post to post, zoom in on image after expanding, and then on to next post
def navigate(href):
    print("navigating...")
    global counter
    #goes to the post
    driver.get(href)
    time.sleep(2)
    #some posts have multiple images and 'show all' button needs pressing
    try:
        show_all = driver.find_element(By.CLASS_NAME, "eVaEhv")
    except NoSuchElementException:
        show_all = None
    if show_all:
        show_all.click()
        time.sleep(3)
    #get the name of the post (some posts dont have names though; the fNOdSq button says untitled)
    try:
        title_element = driver.find_element(By.CLASS_NAME, "hLsLTc")
    except NoSuchElementException:
        title_element = None
    if title_element:
        title_raw = title_element.get_attribute("innerHTML")
        if title_raw:
            title = ''.join(char for char in title_raw if char not in invalid_chars)
        else:
            title = "untitled"
    else:
        title = "untitled"
    #the image elemetns
    try:
        feuJAv_elements = driver.find_elements(By.CLASS_NAME, "feuJAv")
    except NoSuchElementException:
        feuJAv_elements = None
    #zoom in on the images
    if feuJAv_elements:
        for i in range(len(feuJAv_elements)):
            time.sleep(2)
            if i == 0:
                feuJAv_elements[0].click()
            time.sleep(2)
            #get the zoomed image's source
            try:
                all_images = driver.find_elements(By.TAG_NAME, "img")
            except:
                all_images = None
            if all_images:
                for item in all_images:
                    if item.get_attribute("src"):
                        link = item.get_attribute("src")
                        if link:
                            if link.startswith("https://i.pximg.net/img-original/") and f"p{i}" in link :
                                get_image(link, title, i)
                            elif link.startswith("https://i.pximg.net/img-original/") and f"p{i}" not in link:
                                print("Error: issue getting next image")

            time.sleep(1)
            #clicks the down arrow to go to next image
            try:
                next_image = driver.find_element(By.CLASS_NAME, "lcgCGY")
            except NoSuchElementException:
                next_image = None
                print("Error: Could not move to next image in post!")
            if next_image:
                next_image.click()
                time.sleep(4)
            time.sleep(1)

    #take break every x downloads
    if counter >= 49:
         print("50 images reached, pausing scraping for 5 minutes to avoid server complaint")
         time.sleep(5*60)
         counter = 0
#go to next page
def next_page(href):
    #moves to next page of posts
    driver.get(href)
    time.sleep(3)

#if there are posts iterate through them calling navigate
fNOdSq_hrefs = list_posts()
if fNOdSq_hrefs:
    for item in fNOdSq_hrefs:
        navigate(item)
#when post iteration is done, go to next page
if buYbfM_hrefs:
    for item in buYbfM_hrefs:
        next_page(item)
        #Gets list of links for the posts (again)
        fNOdSq_hrefs = list_posts()
        if fNOdSq_hrefs:
            for item in fNOdSq_hrefs:
                navigate(item)

driver.quit()
shutil.rmtree(cache)
sys.exit()

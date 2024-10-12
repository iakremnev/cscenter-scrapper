# pip install requests beautifulsoup4
# all stuff is going to be saved in the current dir

import os
import re
import warnings

from bs4 import BeautifulSoup, GuessedAtParserWarning
import requests

warnings.simplefilter("ignore", GuessedAtParserWarning)

USERNAME = ""
PASSWORD = ""

session = requests.Session()


def make_dirs(course_name, page_name, page_type):
    course_name = course_name.replace("/", "_")
    page_name = page_name.replace("/", "_")
    dir = os.path.join(course_name, page_type, page_name)
    os.makedirs(dir, exist_ok=True)
    return dir

def save_page(course_name, page_name, page_type, html):
    dir = make_dirs(course_name, page_name, page_type)
    basename = "page.html"
    path = os.path.join(dir, basename)
    with open(path, "w") as f:
        f.write(html)
    return path

def save_attachment(dir, basename, content):
    print("INFO: Attachment", basename)
    with open(os.path.join(dir, basename), "wb") as f:
        f.write(content)

def login(username, password):
    resp = session.get("https://my.compscicenter.ru/login")  # get CSRF cookie
    csrfmiddlewaretoken_pattern = r'<input type="hidden" name="csrfmiddlewaretoken" value="(\w+)">'
    csrfmiddlewaretoken = re.search(csrfmiddlewaretoken_pattern, resp.text).group(1)
    resp = session.post(
        "https://my.compscicenter.ru/login/",
        headers={
            "Referer": "https://my.compscicenter.ru/login/",
            },
        data={"username": username, "password": password, "csrfmiddlewaretoken": csrfmiddlewaretoken}
    )
    resp.raise_for_status()
    if '<span class="error-message">' in resp.text:
        raise RuntimeError("Incorrect username and password")

def parse_learning_courses():
    resp = session.get("https://my.compscicenter.ru/learning/courses/")
    soup = BeautifulSoup(resp.text)

    course_table = soup.find("table", class_="table _archive")
    for atag in course_table.find_all("a"):
        course_link = atag.attrs["href"]
        if not course_link.startswith("https://my.compscicenter.ru/"):
            print("WARNING: Can't parse course", course_link)
            continue

        parse_course(course_link)

def parse_table_page(link, table_id):
    resp = session.get(link)
    soup = BeautifulSoup(resp.text)

    table = soup.find("div", id=table_id)
    for atag in table.find_all("a"):
        link = atag.attrs["href"]
        if not link.endswith("/"):
            # these are anchors to class pages or files that will be scrapped from the assignment page
            continue
        parse_class_or_assignment(link)

def parse_course(course_link):
    print("INFO: Course", course_link)
    # Parse classes
    parse_table_page(course_link + "classes/", "course-classes")
    parse_table_page(course_link + "assignments/", "course-assignments")

def parse_class_or_assignment(link):
    print("INFO: Page", link)
    resp = session.get(link)
    soup = BeautifulSoup(resp.text)

    # save page
    page_name, course_name = soup.find("h2").stripped_strings
    page_type = link.split("/")[-3]  # HACK: assignments or classes
    saved_page_path = save_page(course_name, page_name, page_type, resp.text)

    # save attachments that need CS authorization
    for atag in soup.find_all("a"):
        att_link = atag.attrs["href"]

        if att_link.startswith("https://my.compscicenter.ru/attachments/"):
            resp = session.get(att_link)
            if not resp.ok:
                print("WARNING: Can't download attachment", att_link, "from", link)
                continue

            save_attachment(os.path.dirname(saved_page_path), att_link.split("/")[-1], resp.content)

login(USERNAME, PASSWORD)
print("INFO: Login Successful")
parse_learning_courses()
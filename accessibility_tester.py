"""This module includes the accessibility tester and all its functionality"""

import time
import sys
import urllib.parse
import os
import argparse
from pathlib import Path

import validators
from bs4 import BeautifulSoup, Comment, Doctype
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.opera.options import Options as OperaOptions
from selenium.webdriver.safari.options import Options as SafariOptions

class AccessibilityTester:
    """
    An instance of the Accessibility Tester

    Attributes
    ----------
    url : str
        The url of the page that should be tested
    required_degree : float
        The required accessibility degree for success, must be a value between 0 and 1
    chosen_driver : str
        The name of the chosen browser, must be 'chrome', 'firefox', 'edge', 'opera' or 'safari'
    headless : bool
        Defines if the test should be run in headless mode
    screenshots : bool
        Defines if the test should take screenshots on every page it visits
    browser_height : int
        The height of the browser window
    browser_width : int
        The width of the browser window
    follow : bool
        Defines if the test should also test subpages that are linked on the main page
    """
    def __init__(self, url, required_degree=0, chosen_driver="chrome", headless=True,
            screenshots=False, browser_height=1080, browser_width=1920, follow=False):
        self.url = url
        self.required_degree = required_degree
        self.chosen_driver = chosen_driver
        self.headless = headless
        self.screenshots = screenshots
        self.browser_height = browser_height
        self.browser_width = browser_width
        self.follow = follow
        self.driver = None
        self.page = None
        self.correct = {"doc_language":0, "alt_texts":0, "input_labels":0, "empty_buttons":0, "empty_links":0, "color_contrast":0}
        self.wrong = {"doc_language":0, "alt_texts":0, "input_labels":0, "empty_buttons":0, "empty_links":0, "color_contrast":0}

        self.visited_links = []


    def start_driver(self):
        """This function starts the webdriver with the set configuration of the instance"""
        if self.chosen_driver == "chrome":
            options = ChromeOptions()
            options.headless = self.headless
            options.add_argument("--log-level=3")

            self.driver = webdriver.Chrome(options=options)
        elif self.chosen_driver == "firefox":
            options = FirefoxOptions()
            options.headless = self.headless
            options.add_argument("--log-level=3")

            self.driver = webdriver.Firefox(options=options)
        elif self.chosen_driver == "edge":
            options = EdgeOptions()
            options.use_chromium = True
            options.headless = self.headless
            options.add_argument("--log-level=3")

            self.driver = webdriver.Edge(options=options)
        elif self.chosen_driver == "opera":
            options = OperaOptions()
            options.headless = self.headless
            options.add_argument("--log-level=3")
            options.add_experimental_option('w3c', True)

            self.driver = webdriver.Opera(options=options)
        elif self.chosen_driver == "safari":
            options = SafariOptions()
            options.headless = self.headless
            options.add_argument("--log-level=3")

            self.driver = webdriver.Safari(options=options)
        else:
            raise Exception("Webdriver must be one of: Chrome, Firefox, Edge, Opera, Safari")

        self.driver.set_window_size(self.browser_width, self.browser_height)
        self.driver.get(self.url)
        self.page = BeautifulSoup(self.driver.page_source, "html.parser")

        # make sure that the screenshots directory exists when screenshots are enabled
        if self.screenshots:
            Path("./screenshots").mkdir(parents=True, exist_ok=True)


    def test_page(self):
        """This function executes the tests for the current page. If tests for subpages are enabled, it will also test all subpages"""
        self.page = BeautifulSoup(self.driver.page_source, "html.parser")
        print("\n\n" + self.driver.current_url + "\n---------------------")
        self.check_doc_language()
        self.check_alt_texts()
        self.check_input_labels()
        self.check_buttons()
        self.check_links()
        self.check_color_contrast()

        if self.screenshots:
            dir_path = os.path.dirname(os.path.realpath(__file__))
            hostname = urllib.parse.urlparse(self.driver.current_url).hostname
            self.driver.get_screenshot_as_file(dir_path + "/screenshots/" + hostname + "-" + str(time.time()) + ".png")

        if self.follow:
            self.visited_links.append(self.driver.current_url)

            # get all links on the page and iterate over the list of links
            link_list = self.driver.find_elements(by="tag name", value="a")
            for i in range(len(link_list)):
                self.driver.execute_script("elements = document.getElementsByTagName('a'); \
                                            for (var element of elements) {element.setAttribute('target', '')}")
                link = link_list[i]

                # get the full link and check if it needs to be visited
                full_link = str(urllib.parse.urljoin(self.url, link.get_attribute("href")))
                if not link.is_displayed() or link.get_attribute("href") == "" or link.get_attribute("href") is None \
                        or full_link == self.driver.current_url or full_link in self.visited_links:
                    continue
                link_url = link.get_attribute("href")

                # open the link in a new browser window
                self.driver.execute_script("window.open('');")
                self.driver.switch_to.window(self.driver.window_handles[len(self.driver.window_handles)-1])
                self.driver.get(link_url)

                # get back to the previous window when the link should not be tested
                if self.driver.current_url in self.visited_links or not urllib.parse.urlparse(self.url).hostname in self.driver.current_url:
                    self.driver.switch_to.window(self.driver.window_handles[self.driver.window_handles.index(self.driver.current_window_handle)-1])
                    continue

                self.test_page()

            self.driver.switch_to.window(self.driver.window_handles[self.driver.window_handles.index(self.driver.current_window_handle)-1])


    def check_doc_language(self):
        """This function checks if the doc language is set (3.1.1 H57)"""
        # check if language attribute exists and is not empty
        lang_attr = self.page.find("html").get_attribute_list("lang")[0]
        if not lang_attr is None and not lang_attr == "":
            print("  Document language is set")
            self.correct["doc_language"] += 1
        elif not lang_attr is None:
            print("x Document language is empty")
            self.wrong["doc_language"] += 1
        else:
            print("x Document language is missing")
            self.wrong["doc_language"] += 1


    def check_alt_texts(self):
        """This function checks if all images on the page have an alternative text (1.1.1 H37)"""
        # get all img elements
        img_elements = self.page.find_all("img")
        for img_element in img_elements:
            # check if img element has an alternative text that is not empty
            alt_text = img_element.get_attribute_list('alt')[0]
            if not alt_text is None and not alt_text == "":
                print("  Alt text is correct", xpath_soup(img_element))
                self.correct["alt_texts"] += 1
            elif not alt_text is None:
                print("x Alt text is empty", xpath_soup(img_element))
                self.wrong["alt_texts"] += 1
            else:
                print("x Alt text is missing", xpath_soup(img_element))
                self.wrong["alt_texts"] += 1


    def check_input_labels(self):
        """This function checks if all input elements on the page have some form of label (1.3.1 H44 & ARIA16)"""
        # get all input and label elements
        input_elements = self.page.find_all("input")
        label_elements = self.page.find_all("label")
        for input_element in input_elements:
            # exclude input element of type hidden, submit, reset and button
            if ("type" in input_element.attrs and not input_element['type'] == "hidden" and not input_element['type'] == "submit" \
                    and not input_element['type'] == "reset" and not input_element['type'] == "button") or "type" not in input_element.attrs:
                # check if input is of type image and has a alt text that is not empty
                if "type" in input_element.attrs and input_element['type'] == "image" and "alt" in input_element.attrs \
                        and not input_element['alt'] == "":
                    print("  Input of type image labelled with alt text", xpath_soup(input_element))
                    self.correct["input_labels"] += 1
                # check if input element uses aria-label
                elif "aria-label" in input_element.attrs and not input_element['aria-label'] == "":
                    print("  Input labelled with aria-label attribute", xpath_soup(input_element))
                    self.correct["input_labels"] += 1
                # check if input element uses aria-labelledby
                elif "aria-labelledby" in input_element.attrs and not input_element['aria-labelledby'] == "":
                    label_element = self.page.find(id=input_element['aria-labelledby'])
                    if not label_element is None:
                        texts_in_label_element = label_element.findAll(text=True)
                        if not texts_in_label_element == []:
                            print("  Input labelled with aria-labelledby attribute", xpath_soup(input_element))
                            self.correct["input_labels"] += 1
                        else:
                            print("x Input labelled with aria-labelledby attribute, but related label has no text", xpath_soup(input_element))
                            self.wrong["input_labels"] += 1
                    else:
                        print("x Input labelled with aria-labelledby attribute, but related label does not exist", xpath_soup(input_element))
                        self.wrong["input_labels"] += 1
                else:
                    # check if input element has a corresponding label element
                    label_correct = False
                    for label_element in label_elements:
                        # check if "for" attribute of label element is identical to "id" of input element
                        if "for" in label_element.attrs and "id" in input_element.attrs and label_element['for'] == input_element['id']:
                            label_correct = True
                    if label_correct:
                        print("  Input labelled with label element", xpath_soup(input_element))
                        self.correct["input_labels"] += 1
                    else:
                        print("x Input not labelled at all", xpath_soup(input_element))
                        self.wrong["input_labels"] += 1


    def check_buttons(self):
        """This function checks if all buttons and input elements of the types submit, button and reset have some form of content (1.1.1 & 2.4.4)"""
        # get all buttons and input elements of the types submit, button and reset
        input_elements = self.page.find_all("input", type=["submit", "button", "reset"])
        button_elements = self.page.find_all("button")

        for input_element in input_elements:
            # check if input element has a value attribute that is not empty
            if "value" in input_element.attrs and not input_element['value'] == "":
                print("  Button has content", xpath_soup(input_element))
                self.correct["empty_buttons"] += 1
            else:
                print("x Button is empty", xpath_soup(input_element))
                self.wrong["empty_buttons"] += 1

        for button_element in button_elements:
            # check if the button has content or a title
            texts = button_element.findAll(text=True)
            if not texts == [] or ("title" in button_element.attrs and not button_element["title"] == ""):
                print("  Button has content", xpath_soup(button_element))
                self.correct["empty_buttons"] += 1
            else:
                print("x Button is empty", xpath_soup(button_element))
                self.wrong["empty_buttons"] += 1


    def check_links(self):
        """This function checks if all links on the page have some form of content (2.4.4 G91 & H30)"""
        # get all a elements
        link_elements = self.page.find_all("a")
        for link_element in link_elements:
            # check if link has content
            texts_in_link_element = link_element.findAll(text=True)
            img_elements = link_element.findChildren("img", recursive=False)
            all_alt_texts_set = True
            for img_element in img_elements:
                alt_text = img_element.get_attribute_list('alt')[0]
                if alt_text is None or alt_text == "":
                    all_alt_texts_set = False
            if not texts_in_link_element == [] or (not img_elements == [] and all_alt_texts_set):
                print("  Link has content", xpath_soup(link_element))
                self.correct["empty_links"] += 1
            else:
                print("x Link is empty", xpath_soup(link_element))
                self.wrong["empty_links"] += 1


    def check_color_contrast(self):
        """This function checks if all texts on the page have high enough contrast to the color of the background (1.4.3 G18 & G145 (& 148))"""
        # exclude script, style, title and empty elements as well as doctype and comments
        texts_on_page = extract_texts(self.page)
        input_elements = self.page.find_all("input")
        elements_with_text = texts_on_page + input_elements
        for text in elements_with_text:
            selenium_element = self.driver.find_element(by="xpath", value=xpath_soup(text))
            # exclude invisible texts
            element_visible = selenium_element.value_of_css_property('display')
            if not element_visible == "none" and (not text.name == "input" or (text.name == "input" \
                    and "type" in text.attrs and not text['type'] == "hidden")):
                text_color = convert_to_rgba_value(selenium_element.value_of_css_property('color'))
                background_color = get_background_color(self.driver, text)

                # calculate contrast between text color and background color
                contrast = get_contrast_ratio(eval(text_color[4:]), eval(background_color[4:]))

                # get font size and font weight
                font_size = selenium_element.value_of_css_property('font-size')
                font_weight = selenium_element.value_of_css_property('font-weight')


                if not font_size is None and font_size.__contains__("px") and \
                        (int(''.join(filter(str.isdigit, font_size))) >= 18 or ((font_weight == "bold" or font_weight == "700" \
                        or font_weight == "800" or font_weight == "900" or text.name == "strong") \
                        and int(''.join(filter(str.isdigit, font_size))) >= 14)):
                    if contrast >= 3:
                        print("  Contrast meets minimum requirements", xpath_soup(text), text_color, background_color)
                        self.correct["color_contrast"] += 1
                    else:
                        print("x Contrast does not meet minimum requirements", xpath_soup(text), text_color, background_color)
                        self.wrong["color_contrast"] += 1
                else:
                    if contrast >= 4.5:
                        print("  Contrast meets minimum requirements", xpath_soup(text), text_color, background_color)
                        self.correct["color_contrast"] += 1
                    else:
                        print("x Contrast does not meet minimum requirements", xpath_soup(text), text_color, background_color)
                        self.wrong["color_contrast"] += 1


    def calculate_result(self):
        """This function calculates the result of the test and prints it to the console"""
        # calculate correct and false implementations
        correct = sum(self.correct.values())
        false = sum(self.wrong.values())
        if correct == 0 and false == 0:
            print("Nothing found")
            return
        print("\nResult")
        print("---------------------")
        print("Correct:", correct)
        for category, value in self.correct.items():
            print(" ", category + ":", value)
        print("Errors:", false)
        for category, value in self.wrong.items():
            print(" ", category + ":", value)
        print("Ratio (correct to total):", round(correct/(correct+false), 2), "\n")

        # check if ratio correct/total reaches wanted minimum value
        if correct/(correct+false) >= self.required_degree:
            print("Accessibility test successful - can deploy")
        else:
            sys.tracebacklimit = 0
            raise Exception("Too many accessibility errors - try fix them!")


# src: https://gist.github.com/ergoithz/6cf043e3fdedd1b94fcf
def xpath_soup(element):
    # pylint: disable=consider-using-f-string
    """This function calculates the xpath of an element"""
    if element is None:
        return '/html'
    components = []
    child = element if element.name else element.parent
    for parent in child.parents:  # type: bs4.element.Tag
        siblings = parent.find_all(child.name, recursive=False)
        components.append(
            child.name if 1 == len(siblings) else '%s[%d]' % (
                child.name,
                next(i for i, s in enumerate(siblings, 1) if s is child)
                )
            )
        child = parent
    components.reverse()
    if not components:
        return '/html'
    return '/%s' % '/'.join(components)

def extract_texts(soup):
    """This function extracts all texts from a page"""
    soup2 = soup

    # remove script, style and title elements
    for invisible_element in soup2(["script", "style", "title", "noscript"]):
        invisible_element.extract()

    # remove comments
    comments = soup2.findAll(text=lambda text:isinstance(text, Comment))
    for comment in comments:
        comment.extract()

    # remove doctype
    doctype = soup2.find(text=lambda text:isinstance(text, Doctype))
    if not doctype is None:
        doctype.extract()

    # get all elements with text
    texts = []
    texts_on_page = soup2.findAll(text=True)
    for text in texts_on_page:
        if not text.strip() == "" and not text == "\n":
            texts.append(text.parent)

    return texts

def get_background_color(driver, text):
    """This function returns the background color of a given text"""
    if text is None:
        return "rgba(255,255,255,1)"

    selenium_element = driver.find_element(by="xpath", value=xpath_soup(text))
    background_color = convert_to_rgba_value(selenium_element.value_of_css_property('background-color'))

    if eval(background_color[4:])[3] == 0:
        return get_background_color(driver, text.parent)

    return background_color

def convert_to_rgba_value(color):
    """This function converts a color value to the rgba format"""
    if color[:4] != "rgba":
        rgba_tuple = eval(color[3:]) + (1,)
        color = "rgba" + str(rgba_tuple)

    return color

def get_contrast_ratio(text_color, background_color):
    """This function calculates the contrast ratio between text color and background color"""
    # preparing the RGB values
    r_text = convert_rgb_8bit_value(text_color[0])
    g_text = convert_rgb_8bit_value(text_color[1])
    b_text = convert_rgb_8bit_value(text_color[2])
    r_background = convert_rgb_8bit_value(background_color[0])
    g_background = convert_rgb_8bit_value(background_color[1])
    b_background = convert_rgb_8bit_value(background_color[2])

    # calculating the relative luminance
    luminance_text = 0.2126 * r_text + 0.7152 * g_text + 0.0722 * b_text
    luminance_background = 0.2126 * r_background + 0.7152 * g_background + 0.0722 * b_background

    # check if luminance_text or luminance_background is lighter
    if luminance_text > luminance_background:
        # calculating contrast ration when luminance_text is the relative luminance of the lighter colour
        contrast_ratio = (luminance_text + 0.05) / (luminance_background + 0.05)
    else:
        # calculating contrast ration when luminance_background is the relative luminance of the lighter colour
        contrast_ratio = (luminance_background + 0.05) / (luminance_text + 0.05)

    return contrast_ratio

def convert_rgb_8bit_value(single_rgb_8bit_value):
    """This function converts an rgb value to the needed format"""
    # dividing the 8-bit value through 255
    srgb = single_rgb_8bit_value / 255

    # check if the srgb value is lower than or equal to 0.03928
    if srgb <= 0.03928:
        return srgb / 12.92

    return ((srgb + 0.055) / 1.055) ** 2.4

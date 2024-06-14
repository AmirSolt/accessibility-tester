
import argparse
import validators


def main():
    """The main function that reads the arguments from the command line and executes the tests with the given configuration"""
    parser = argparse.ArgumentParser(
        usage = "%(prog)s [OPTION] WEBPAGE",
        description = "A command line tool to test webpages for accessibility")

    parser.add_argument("webpage",
                        help = "the webpage for which the test should be run")
    parser.add_argument("-l", "--level", type=float,
                        help = "the required accessibility level as a number between 0 and 1 with 1 not allowing any failures, default is 1",
                        required = False, default = 1.0)
    parser.add_argument("-d", "--driver", type=str,
                        help = "the driver to use for testing (possible values: Chrome, Firefox, Edge, Opera, Safari), default is Chrome",
                        required = False, default = "Chrome")
    parser.add_argument("--headless",
                        help = "defines if the webdriver should run in headless mode, default is False",
                        required = False, action = "store_true")
    parser.add_argument("-s", "--screenshots",
                        help = "defines if the program should take screenshots of every page it visits, default is False",
                        required = False, action = "store_true")
    parser.add_argument("--height", type=int,
                        help = "the height value of the window size the browser should use, default is 1080",
                        required = False, default = 1080)
    parser.add_argument("--width", type=int,
                        help = "the width value of the window size the browser should use, default is 1920",
                        required = False, default = 1920)
    parser.add_argument("-f", "--follow",
                        help = "defines if the program should also test subpages that are linked on the main page, default is False",
                        required = False, action = "store_true")

    argument = parser.parse_args()

    url = argument.webpage
    required_degree = argument.level
    driver = str(argument.driver).lower()
    run_headless = argument.headless
    take_screenshots = argument.screenshots
    browser_height = argument.height
    browser_width = argument.width
    should_follow = argument.follow

    # validate values of url, required_degree and driver
    if not validators.url(url):
        raise Exception("Invalid URL")

    if not 0 <= required_degree <= 1:
        raise Exception("Accessibility level must be between 0 and 1")

    if driver not in ["chrome", "firefox", "edge", "opera", "safari"]:
        raise Exception("Webdriver must be one of: Chrome, Firefox, Edge, Opera, Safari")

    accessibility_tester = AccessibilityTester(url, required_degree, driver, run_headless, take_screenshots,
                                               browser_height, browser_width, should_follow)

    accessibility_tester.start_driver()

    accessibility_tester.test_page()

    accessibility_tester.driver.quit()

    accessibility_tester.calculate_result()

if __name__ == "__main__":
    main()
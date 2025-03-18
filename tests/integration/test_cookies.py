import os
import pickle
import time

from open_webdriver import open_webdriver  # type: ignore

with open_webdriver() as driver:
    URL = "https://youtube.com"
    driver.get(URL)
    time.sleep(10)
    if os.path.exists("cookies.pkl"):
        cookies = pickle.load(open("cookies.pkl", "rb"))
        for cookie in cookies:
            driver.add_cookie(cookie)
        driver.refresh()
        time.sleep(5)
    # check if still need login
    # if yes:
    # write login code
    # when login success save cookies using
    pickle.dump(driver.get_cookies(), open("cookies.pkl", "wb"))

# driver = webdriver.Chrome(executable_path="chromedriver.exe")
# URL = "https://youtube.com"
# driver.get(URL)
# time.sleep(10)
# if os.path.exists('cookies.pkl'):
#     cookies = pickle.load(open("cookies.pkl", "rb"))
#     for cookie in cookies:
#         driver.add_cookie(cookie)
#     driver.refresh()
#     time.sleep(5)
# # check if still need login
# # if yes:
# # write login code
# # when login success save cookies using
# pickle.dump(driver.get_cookies(), open("cookies.pkl", "wb"))

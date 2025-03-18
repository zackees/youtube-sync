from youtube_sync.cookies import Cookies

cookies: Cookies = Cookies.from_browser("https://youtube.com")
print(f"Found {len(cookies)} cookies.")

for cookie in cookies:
    print(cookie)


print(f"Generated cookies.txt:\n{cookies.cookies_txt}")
print("done")

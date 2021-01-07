from bs4 import BeautifulSoup
import requests
import re

# real estate should delete itself based on expiry date
#
# update databases every day: if nothing new do nothing else add new entry(s)
# 	some form of index to check what exists in database
#
# check if there are more than 1 pages of ads and pull from those others
from Apartment import Apartment

PATH = "./chromedriver"
url = 'http://gleanerclassifieds.com/showads/ad/search/section_id/10100/menu_id//category_id/12518/keyword//title' \
      '//start_rec/0/page_size/50/sort/3'

html_text = requests.get(url).text
soup = BeautifulSoup(html_text, 'lxml')
ads = soup.find_all('td')

rental_ads = []
count = 0
extracted_data = []


def extract_phone_number(text):
    phone_number = re.findall(r'\(?([0-9]{3})\)?([ .-]?)([0-9]{3})\2([0-9]{4})', text)
    if not phone_number:
        phone_number = re.findall(r'([0-9]{3})([ .-]?)([0-9]{4})', text)
    return phone_number


def extract_price(text):
    price = re.findall(r'\$ ?[ ,.]?[0-9,]{1,}[kK]?', text)
    return price


for ad in ads:
    new_ad = ad.find('a')
    if new_ad is not None:
        if new_ad.text != "" and "Clear Search" not in new_ad.text:
            if "Banker" not in str(new_ad) and "Accomodation" not in str(new_ad):
                count = count + 1
                rental_ads.append(new_ad)
                links = re.findall(r'"(.*?)"', str(new_ad))
                if "thickbox" not in links[0]:
                    ad_page = requests.get(links[0]).text
                else:
                    ad_page = requests.get(links[1]).text
                ad_page_html = BeautifulSoup(ad_page, 'lxml')
                ad_page_html_rental_paragraph = ad_page_html.find_all('p')
                for rental_paragraph in ad_page_html_rental_paragraph:
                    paragraph = rental_paragraph.find_all("font")
                    for font in paragraph:
                        if font.text != "" and not re.findall(r'Moving', font.text) \
                                and not re.findall(r'BOX', font.text) and not re.findall(r'Removal', font.text):
                            print(font.text)
                            # pull out data
                            found_phone_number = extract_phone_number(font.text)
                            found_price = extract_price(font.text)
                            data = Apartment(found_phone_number, found_price, font.text)
                            extracted_data.append(data)
                            print("Price", data.price)
                            print("\n")

for item in extracted_data:
    print(str(item))

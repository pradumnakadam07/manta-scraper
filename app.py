import time
import re
import urllib.parse
import pandas as pd
from bs4 import BeautifulSoup
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
import streamlit as st
import io
import zipfile

# ---------------- STREAMLIT UI ----------------
st.title("Manta.com Business Scraper")
st.markdown("Enter search details to scrape business listings from Manta.com")

city = st.text_input("City", "Dallas")
state = st.text_input("State", "TX")
search_query = st.text_input("Service to Search", "Plumber")
total_pages = st.number_input("Number of pages to scrape", min_value=1, max_value=50, value=1, step=1)

if st.button("Start Scraping"):
    st.info("Launching Chrome... Please wait and solve CAPTCHA if shown.")

    options = uc.ChromeOptions()
    options.binary_location = "/usr/bin/chromium"  # <-- path inside container
    options.add_argument("--headless")  # optional for headless scraping
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = uc.Chrome(options=options, version_main=140)



    start_url = f"https://www.manta.com/search?search_source=business&search={urllib.parse.quote(search_query)}&city={city}&state={state}"
    driver.get(start_url)
    time.sleep(15)  # Give time for CAPTCHA solving

    URLS = [f"{start_url}&pg={i}" for i in range(1, total_pages + 1)]

    Name, Address, Phone, Website, Email = [], [], [], [], []

    for page_num, page_url in enumerate(URLS, start=1):
        st.write(f"[INFO] Scraping page {page_num}/{total_pages} ...")
        driver.get(page_url)
        time.sleep(3)

        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)

        soup = BeautifulSoup(driver.page_source, 'lxml')
        listings = soup.find_all('div', class_=re.compile(r"flex.*w-full.*text-gray-800"))

        if not listings:
            st.warning(f"No listings found on page {page_num}")
            continue

        for listing in listings:
            # name
            name_tag = listing.find('a', class_=re.compile(r"cursor-pointer"))
            name = name_tag.get_text(strip=True) if name_tag else ''

            detail_url = ""
            if name_tag and name_tag.get("href"):
                detail_url = urllib.parse.urljoin("https://www.manta.com", name_tag["href"])

            # address
            address_tag = listing.find('div', class_=re.compile(r"hidden.*md:block"))
            address = address_tag.get_text(strip=True) if address_tag else ''

            # phone
            phone_tag = listing.find('i', class_=re.compile(r"fa-phone"))
            if phone_tag:
                phone_div = phone_tag.find_next('div')
                phone = phone_div.get_text(strip=True) if phone_div else ''
            else:
                phone = ''

            # website
            website_tag = listing.find('a', string=re.compile("Visit Website", re.I))
            if website_tag:
                raw_link = website_tag.get('href', '')
                if "redirect=" in raw_link:
                    website = urllib.parse.unquote(raw_link.split("redirect=")[1].split("&")[0])
                else:
                    website = raw_link
            else:
                website = ''

            # email
            email = ''
            if detail_url:
                try:
                    driver.get(detail_url)
                    time.sleep(2)
                    detail_soup = BeautifulSoup(driver.page_source, "lxml")
                    email_tag = detail_soup.find("a", href=re.compile(r"^mailto:"))
                    if email_tag:
                        email = email_tag.get("href").replace("mailto:", "").strip()
                except Exception as e:
                    st.error(f"Could not fetch email from {detail_url}: {e}")
                    email = ''

            Name.append(name)
            Address.append(address)
            Phone.append(phone)
            Website.append(website)
            Email.append(email)

    driver.quit()

    df = pd.DataFrame(zip(Name, Address, Phone, Website, Email),
                      columns=['Name', "Address", "Phone", "Website", "Email"])
    df.drop_duplicates(subset=("Name"), keep='first', inplace=True)

    df_with_email = df[df['Email'].str.strip() != ""]
    df_without_email = df[df['Email'].str.strip() == ""]

    st.success("Scraping complete!")
    st.write(f"✅ Data with emails: {len(df_with_email)} records")
    st.write(f"❌ Data without emails: {len(df_without_email)} records")

    # Show preview
    st.subheader("Preview of Results")
    st.dataframe(df.head(20))

    # -------- SINGLE DOWNLOAD (ZIP with both CSVs) --------
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr("data_with_emails.csv", df_with_email.to_csv(index=False, encoding="utf-8-sig"))
        zf.writestr("data_without_emails.csv", df_without_email.to_csv(index=False, encoding="utf-8-sig"))
    buffer.seek(0)

    st.download_button(
        label="📦 Download Both CSVs (ZIP)",
        data=buffer,
        file_name="manta_scraped_data.zip",
        mime="application/zip"
    )

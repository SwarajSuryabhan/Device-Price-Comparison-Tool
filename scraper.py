import re
import time
from difflib import SequenceMatcher
from urllib.parse import urlparse, parse_qs, unquote

from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager


def normalize_text(text):
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text


def parse_price(text):
    if not text:
        return None
    digits = re.sub(r"[^0-9]", "", text)
    return int(digits) if digits else None


def similarity(a, b):
    return SequenceMatcher(None, normalize_text(a), normalize_text(b)).ratio()


def keyword_score(query, title):
    q_words = normalize_text(query).split()
    t = normalize_text(title)

    if not q_words:
        return 0

    matched = sum(1 for word in q_words if word in t)
    return matched / len(q_words)


def combined_score(query, title):
    sim = similarity(query, title)
    key = keyword_score(query, title)
    return round((0.65 * sim) + (0.35 * key), 3)


def extract_model_tokens(text):
    tokens = normalize_text(text).split()
    important = []

    important_words = {
        "iphone", "ipad", "galaxy", "oneplus", "pixel", "redmi", "realme",
        "black", "blue", "white", "green", "silver", "gold", "pink", "teal",
        "gray", "grey", "orange", "purple", "yellow",
        "gb", "tb", "pro", "plus", "ultra", "max", "air", "mini",
        "wifi", "5g", "lte", "ryzen", "intel", "ssd", "ram"
    }

    for token in tokens:
        if re.search(r"\d", token):
            important.append(token)
        elif token in important_words:
            important.append(token)

    return important


def strict_match(query, title, min_score=0.50):
    score = combined_score(query, title)
    q_tokens = extract_model_tokens(query)
    t = normalize_text(title)

    if q_tokens:
        matched = sum(1 for token in q_tokens if token in t)
        required = max(1, int(len(q_tokens) * 0.7 + 0.5))
        if matched < required:
            return False, score

    return score >= min_score, score


def price_closeness_score(reference_price, candidate_price):
    if not reference_price or not candidate_price:
        return 0

    diff = abs(reference_price - candidate_price)
    ratio = diff / reference_price
    return round(max(0, 1 - ratio), 3)


def combined_match_with_price(query, title, candidate_price, reference_price):
    text_score = combined_score(query, title)
    price_score = price_closeness_score(reference_price, candidate_price)
    final = round((0.7 * text_score) + (0.3 * price_score), 3)
    return final, text_score, price_score


def is_valid_product_domain(url, domain):
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        netloc = parsed.netloc.lower()
        return netloc == domain or netloc.endswith("." + domain)
    except Exception:
        return False


def is_likely_product_url(url, domain):
    try:
        parsed = urlparse(url)
        netloc = parsed.netloc.lower()
        path = parsed.path.lower()

        if not (netloc == domain or netloc.endswith("." + domain)):
            return False

        if domain == "amazon.in":
            return "/dp/" in path or "/gp/" in path or "/product/" in path

        if domain == "flipkart.com":
            return "/p/" in path or "/product/" in path or "/itm" in path

        if domain == "croma.com":
            return "/p/" in path

        return True
    except Exception:
        return False


def clean_google_redirect_url(href, domain):
    if not href:
        return None

    href = href.strip()

    if not href.startswith("http"):
        return None

    try:
        parsed = urlparse(href)
        netloc = parsed.netloc.lower()

        if (
            is_valid_product_domain(href, domain)
            and "google." not in netloc
            and is_likely_product_url(href, domain)
        ):
            return href

        if "google." in netloc:
            query_params = parse_qs(parsed.query)

            for key in ["q", "url"]:
                if key in query_params and query_params[key]:
                    real_url = unquote(query_params[key][0]).strip()
                    if (
                        real_url.startswith("http")
                        and is_valid_product_domain(real_url, domain)
                        and is_likely_product_url(real_url, domain)
                    ):
                        return real_url

        return None
    except Exception:
        return None


def clean_product_title(title, query):
    if not title:
        return query

    title = re.sub(r"\s+", " ", title).strip()
    title = re.sub(r"https?://\S+", "", title).strip()
    title = re.sub(r"\b(Amazon|Flipkart|Croma)\b.*$", "", title, flags=re.IGNORECASE).strip()

    bad_patterns = [
        "google maps", "maps", "directions", "images", "news",
        "shopping", "videos", "ai mode", "untitled"
    ]

    low = title.lower()
    if any(word in low for word in bad_patterns):
        return query

    if len(title) < 5:
        return query

    return title


def create_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )

    driver = webdriver.Chrome(
        service=ChromeService(ChromeDriverManager().install()),
        options=options
    )

    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )

    return driver


def get_price_from_product_page(driver, url, site):
    try:
        driver.get(url)

        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        time.sleep(4)

        if site == "Amazon":
            selectors = [
                ".a-price .a-offscreen",
                "#corePrice_feature_div .a-offscreen",
                "#price_inside_buybox",
                "#tp_price_block_total_price_ww .a-offscreen",
                "span.a-price-whole"
            ]

        elif site == "Flipkart":
            selectors = [
                "div.Nx9bqj.CxhGGd",
                "div.Nx9bqj",
                "div._30jeq3._16Jk6d",
                "div._30jeq3",
                "div[class*='Nx9bqj']",
                "div[class*='_30jeq3']",
                "span[class*='Nx9bqj']",
                "span[class*='price']",
                "div._16Jk6d",
                "div._25b18c"
            ]

        elif site == "Croma":
            selectors = [
                "span.amount",
                "div.amount",
                "[class*='amount']"
            ]

        else:
            selectors = []

        for selector in selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for el in elements:
                    txt = el.text.strip()
                    value = parse_price(txt)
                    if value and value > 100:
                        print(f"{site} product page price FOUND by selector {selector}: {value}")
                        return value
            except Exception:
                continue

        if site == "Flipkart":
            try:
                body_text = driver.find_element(By.TAG_NAME, "body").text
                matches = re.findall(r"₹\s?[\d,]+", body_text)
                for m in matches[:20]:
                    value = parse_price(m)
                    if value and value > 100:
                        print(f"{site} product page price FOUND from body text: {value}")
                        return value
            except Exception:
                pass

        print(f"{site} product page price NOT FOUND")
        return None

    except Exception as e:
        print(f"{site} product page error:", e)
        return None


def google_fallback(driver, query, domain, site_name):
    try:
        search_url = f"https://www.google.com/search?q=site:{domain} {query.replace(' ', '+')}"
        driver.get(search_url)

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        time.sleep(2)

        candidate_links = []
        selectors = ["div.yuRUbf a", "a[href]"]

        for selector in selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    candidate_links.extend(elements)
            except Exception:
                pass

        print(f"{site_name} fallback links found:", len(candidate_links))

        seen = set()

        for a in candidate_links:
            try:
                href = a.get_attribute("href")
                text = a.text.strip()

                cleaned_href = clean_google_redirect_url(href, domain)
                if not cleaned_href:
                    continue

                if cleaned_href in seen:
                    continue
                seen.add(cleaned_href)

                low_link = cleaned_href.lower()
                if any(x in low_link for x in ["/search", "/maps", "google.com", "support.google.com"]):
                    continue

                cleaned_title = clean_product_title(text, query)
                price = get_price_from_product_page(driver, cleaned_href, site_name)

                return {
                    "website": site_name,
                    "product_name": cleaned_title,
                    "price": price if price else 0,
                    "rating": "N/A",
                    "link": cleaned_href,
                    "score": 0.30,
                    "fallback_only": True
                }

            except Exception:
                continue

        return None

    except Exception as e:
        print(f"{site_name} fallback error:", e)
        return None


def search_croma(driver, query):
    try:
        url = f"https://www.croma.com/searchB?q={query.replace(' ', '%20')}:relevance"
        driver.get(url)

        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        time.sleep(2)

        cards = driver.find_elements(
            By.CSS_SELECTOR,
            "li.product-item, div.product-item, div.cp-product, li[class*='product']"
        )
        print("Croma cards found:", len(cards))

        best = None
        best_score = 0

        for card in cards[:20]:
            try:
                title = None
                link = None

                for selector in ["h3 a", "a.product-title", "h3", "a[title]"]:
                    els = card.find_elements(By.CSS_SELECTOR, selector)
                    for el in els:
                        txt = el.text.strip()
                        if txt and len(txt) > 5:
                            title = txt
                            if el.tag_name.lower() == "a":
                                link = el.get_attribute("href")
                            break
                    if title:
                        break

                if not title:
                    continue

                if link and link.startswith("/"):
                    link = "https://www.croma.com" + link

                price = None
                for selector in ["span.amount", "div.amount", "[class*='amount']"]:
                    els = card.find_elements(By.CSS_SELECTOR, selector)
                    for el in els:
                        value = parse_price(el.text)
                        if value and value > 100:
                            price = value
                            break
                    if price:
                        break

                if not price:
                    continue

                ok, score = strict_match(query, title, min_score=0.60)
                print("Croma candidate:", title, "score:", score, "price:", price)

                if not ok:
                    continue

                if score > best_score:
                    best_score = score
                    best = {
                        "website": "Croma",
                        "product_name": title,
                        "price": price,
                        "rating": "N/A",
                        "link": link if link else "https://www.croma.com/",
                        "score": score
                    }

            except Exception:
                continue

        return best

    except Exception as e:
        print("Croma error:", e)
        return None


def search_amazon(driver, query, reference_price=None):
    try:
        url = f"https://www.amazon.in/s?k={query.replace(' ', '+')}"
        driver.get(url)

        WebDriverWait(driver, 12).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        time.sleep(2)

        cards = driver.find_elements(By.CSS_SELECTOR, "div[data-component-type='s-search-result']")
        print("Amazon cards found:", len(cards))

        best = None
        best_score = 0

        for card in cards[:12]:
            try:
                title = None
                title_elements = card.find_elements(By.CSS_SELECTOR, "h2 span, h2 a span")
                for el in title_elements:
                    txt = el.text.strip()
                    if txt:
                        title = txt
                        break

                if not title:
                    continue

                link = None
                link_elements = card.find_elements(By.CSS_SELECTOR, "h2 a")
                for el in link_elements:
                    href = el.get_attribute("href")
                    if href:
                        link = href
                        break

                if not link:
                    continue

                if link.startswith("/"):
                    link = "https://www.amazon.in" + link

                price = None
                for selector in [
                    "span.a-price span.a-offscreen",
                    "span.a-price-whole",
                    ".reinventPricePriceToPayMargin .a-offscreen"
                ]:
                    els = card.find_elements(By.CSS_SELECTOR, selector)
                    for el in els:
                        value = parse_price(el.text)
                        if value and value > 100:
                            price = value
                            break
                    if price:
                        break

                ok, text_only_score = strict_match(query, title, min_score=0.45)
                if not ok:
                    continue

                if price and reference_price:
                    score, text_score, price_score = combined_match_with_price(
                        query, title, price, reference_price
                    )
                else:
                    score = text_only_score
                    text_score = text_only_score
                    price_score = 0

                print(
                    "Amazon candidate:",
                    title,
                    "final:", score,
                    "text:", text_score,
                    "price_score:", price_score,
                    "price:", price
                )

                if score > best_score:
                    best_score = score
                    best = {
                        "website": "Amazon",
                        "product_name": title,
                        "price": price if price else 0,
                        "rating": "N/A",
                        "link": link,
                        "score": score
                    }

            except Exception:
                continue

        if best and best.get("link"):
            best["price"] = get_price_from_product_page(driver, best["link"], "Amazon") or best.get("price", 0)
            return best

        return google_fallback(driver, query, "amazon.in", "Amazon")

    except Exception as e:
        print("Amazon error:", e)
        return google_fallback(driver, query, "amazon.in", "Amazon")


def search_flipkart(driver, query, reference_price=None):
    try:
        url = f"https://www.flipkart.com/search?q={query.replace(' ', '%20')}"
        driver.get(url)

        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        time.sleep(3)

        try:
            close_btn = driver.find_element(By.XPATH, "//button[contains(text(),'✕')]")
            close_btn.click()
            time.sleep(1)
        except Exception:
            pass

        cards = driver.find_elements(By.CSS_SELECTOR, "div._1AtVbE, div[data-id]")
        print("Flipkart cards found:", len(cards))

        best = None
        best_score = 0

        for card in cards[:20]:
            try:
                title = None
                link = None

                title_selectors = [
                    "div.KzDlHZ",
                    "div._4rR01T",
                    "a.s1Q9rs",
                    "a.IRpwTa",
                    "a[title]"
                ]

                for selector in title_selectors:
                    els = card.find_elements(By.CSS_SELECTOR, selector)
                    for el in els:
                        txt = el.text.strip()
                        if txt and len(txt) > 5:
                            title = txt
                            if el.tag_name.lower() == "a":
                                link = el.get_attribute("href")
                            break
                    if title:
                        break

                if not title:
                    continue

                if not link:
                    links = card.find_elements(By.CSS_SELECTOR, "a")
                    for a in links:
                        href = a.get_attribute("href")
                        if href and ("/p/" in href or "/itm" in href):
                            link = href
                            break

                if link and link.startswith("/"):
                    link = "https://www.flipkart.com" + link

                if not link:
                    continue

                price = None
                price_selectors = [
                    "div.Nx9bqj.CxhGGd",
                    "div.Nx9bqj",
                    "div._30jeq3",
                    "div[class*='Nx9bqj']",
                    "div[class*='_30jeq3']"
                ]

                for selector in price_selectors:
                    els = card.find_elements(By.CSS_SELECTOR, selector)
                    for el in els:
                        value = parse_price(el.text)
                        if value and value > 100:
                            price = value
                            break
                    if price:
                        break

                ok, text_only_score = strict_match(query, title, min_score=0.45)
                if not ok:
                    continue

                if price and reference_price:
                    score, text_score, price_score = combined_match_with_price(
                        query, title, price, reference_price
                    )
                else:
                    score = text_only_score
                    text_score = text_only_score
                    price_score = 0

                print(
                    "Flipkart candidate:",
                    title,
                    "final:", score,
                    "text:", text_score,
                    "price_score:", price_score,
                    "price:", price,
                    "link:", link
                )

                if score > best_score:
                    best_score = score
                    best = {
                        "website": "Flipkart",
                        "product_name": title,
                        "price": price if price else 0,
                        "rating": "N/A",
                        "link": link,
                        "score": score
                    }

            except Exception:
                continue

        if best and best.get("link"):
            final_price = get_price_from_product_page(driver, best["link"], "Flipkart")
            if final_price:
                best["price"] = final_price
            return best

        return google_fallback(driver, query, "flipkart.com", "Flipkart")

    except Exception as e:
        print("Flipkart error:", e)
        return google_fallback(driver, query, "flipkart.com", "Flipkart")


def search_reliance_digital(driver, query):
    try:
        url = f"https://www.reliancedigital.in/search?q={query.replace(' ', '%20')}"
        driver.get(url)

        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        cards = driver.find_elements(By.CSS_SELECTOR, "a[href*='/product/'], li, div")
        print("Reliance cards found:", len(cards))

        best = None
        best_score = 0

        for card in cards[:60]:
            try:
                text = card.text.strip()
                href = card.get_attribute("href") if card.tag_name.lower() == "a" else None

                if not text or len(text) < 8:
                    continue

                if not href:
                    links = card.find_elements(By.CSS_SELECTOR, "a[href*='/product/']")
                    for a in links:
                        href = a.get_attribute("href")
                        if href:
                            break

                if not href:
                    continue

                price = None
                price_elements = card.find_elements(
                    By.XPATH, ".//*[contains(text(),'₹') or contains(text(),'Rs.')]"
                )
                for el in price_elements:
                    value = parse_price(el.text)
                    if value and value > 100:
                        price = value
                        break

                if not price:
                    continue

                title = text.split("\n")[0].strip()
                ok, score = strict_match(query, title, min_score=0.50)
                if not ok:
                    continue

                if score > best_score:
                    best_score = score
                    best = {
                        "website": "Reliance Digital",
                        "product_name": title,
                        "price": price,
                        "rating": "N/A",
                        "link": href,
                        "score": score
                    }

            except Exception:
                continue

        return best

    except Exception as e:
        print("Reliance error:", e)
        return None


def search_bajaj(driver, query):
    try:
        url = f"https://www.bajajelectronics.com/search?q={query.replace(' ', '%20')}"
        driver.set_page_load_timeout(45)
        driver.get(url)

        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        cards = driver.find_elements(By.CSS_SELECTOR, "a, div, li")
        print("Bajaj cards found:", len(cards))

        best = None
        best_score = 0

        for card in cards[:70]:
            try:
                text = card.text.strip()
                href = card.get_attribute("href") if card.tag_name.lower() == "a" else None

                if not text or len(text) < 8:
                    continue

                if not href:
                    links = card.find_elements(By.CSS_SELECTOR, "a")
                    for a in links:
                        link = a.get_attribute("href")
                        if link:
                            href = link
                            break

                if not href:
                    continue

                price = None
                price_elements = card.find_elements(
                    By.XPATH, ".//*[contains(text(),'₹') or contains(text(),'Rs')]"
                )
                for el in price_elements:
                    value = parse_price(el.text)
                    if value and value > 100:
                        price = value
                        break

                if not price:
                    continue

                title = text.split("\n")[0].strip()
                ok, score = strict_match(query, title, min_score=0.45)
                if not ok:
                    continue

                if score > best_score:
                    best_score = score
                    best = {
                        "website": "Bajaj Electronics",
                        "product_name": title,
                        "price": price,
                        "rating": "N/A",
                        "link": href,
                        "score": score
                    }

            except Exception:
                continue

        return best

    except Exception as e:
        print("Bajaj error:", e)
        return None


def search_snapdeal(driver, query):
    try:
        url = f"https://www.snapdeal.com/search?keyword={query.replace(' ', '%20')}"
        driver.get(url)

        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        cards = driver.find_elements(By.CSS_SELECTOR, "div.product-tuple-listing, div[data-js-pos]")
        print("Snapdeal cards found:", len(cards))

        best = None
        best_score = 0

        for card in cards[:25]:
            try:
                title = None
                link = None

                title_els = card.find_elements(By.CSS_SELECTOR, "p.product-title, a.dp-widget-link, a")
                for el in title_els:
                    txt = el.text.strip()
                    if txt and len(txt) > 5:
                        title = txt
                        if el.tag_name.lower() == "a":
                            link = el.get_attribute("href")
                        break

                if not title:
                    continue

                if not link:
                    links = card.find_elements(By.CSS_SELECTOR, "a")
                    for a in links:
                        href = a.get_attribute("href")
                        if href:
                            link = href
                            break

                price = None
                for selector in ["span.product-price", "span.lfloat.product-price", "[class*='price']"]:
                    els = card.find_elements(By.CSS_SELECTOR, selector)
                    for el in els:
                        value = parse_price(el.text)
                        if value and value > 100:
                            price = value
                            break
                    if price:
                        break

                if not price:
                    continue

                ok, score = strict_match(query, title, min_score=0.40)
                if not ok:
                    continue

                if score > best_score:
                    best_score = score
                    best = {
                        "website": "Snapdeal",
                        "product_name": title,
                        "price": price,
                        "rating": "N/A",
                        "link": link if link else "https://www.snapdeal.com/",
                        "score": score
                    }

            except Exception:
                continue

        return best

    except Exception as e:
        print("Snapdeal error:", e)
        return None


def compare_prices(query):
    driver = create_driver()
    results = []
    debug = []

    try:
        reference_price = None

        debug.append({"site": "Croma", "status": "Checking"})
        croma = search_croma(driver, query)
        if croma:
            debug[-1]["status"] = "Found"
            results.append(croma)
            reference_price = croma.get("price")
        else:
            debug[-1]["status"] = "Not Found"

        debug.append({"site": "Amazon", "status": "Checking"})
        amazon = search_amazon(driver, query, reference_price=reference_price)
        if amazon:
            debug[-1]["status"] = "Found"
            results.append(amazon)
        else:
            debug[-1]["status"] = "Not Found"

        debug.append({"site": "Flipkart", "status": "Checking"})
        flipkart = search_flipkart(driver, query, reference_price=reference_price)
        if flipkart:
            debug[-1]["status"] = "Found"
            results.append(flipkart)
        else:
            debug[-1]["status"] = "Not Found"

        debug.append({"site": "Reliance Digital", "status": "Checking"})
        reliance = search_reliance_digital(driver, query)
        if reliance:
            debug[-1]["status"] = "Found"
            results.append(reliance)
        else:
            debug[-1]["status"] = "Not Found"

        debug.append({"site": "Bajaj Electronics", "status": "Checking"})
        bajaj = search_bajaj(driver, query)
        if bajaj:
            debug[-1]["status"] = "Found"
            results.append(bajaj)
        else:
            debug[-1]["status"] = "Not Found"

        debug.append({"site": "Snapdeal", "status": "Checking"})
        snapdeal = search_snapdeal(driver, query)
        if snapdeal:
            debug[-1]["status"] = "Found"
            results.append(snapdeal)
        else:
            debug[-1]["status"] = "Not Found"

        print("DEBUG:", debug)
        print("RESULTS:", results)

        if len(results) == 0:
            return {"status": "not_found", "debug": debug, "results": []}

        priced_results = [item for item in results if item.get("price", 0) > 0]

        if len(priced_results) == 0:
            results[0]["best_deal"] = True
            return {"status": "single", "debug": debug, "results": results}

        if len(priced_results) == 1:
            best_link = priced_results[0]["link"]
            for item in results:
                item["best_deal"] = item["link"] == best_link
            return {"status": "single", "debug": debug, "results": results}

        priced_results.sort(key=lambda x: x["price"])
        best_link = priced_results[0]["link"]

        for item in results:
            item["best_deal"] = item["link"] == best_link

        return {"status": "compare", "debug": debug, "results": results}

    except Exception as e:
        print("SCRAPER ERROR:", e)
        return {
            "status": "error",
            "error": str(e),
            "debug": debug,
            "results": []
        }

    finally:
        driver.quit()
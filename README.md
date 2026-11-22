# 🛒 Device Price Comparison Tool

> A Final Year Project — Web application that compares product prices across multiple Indian e-commerce platforms in real time using web scraping.

---

## 📌 Table of Contents

- [About the Project](#about-the-project)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installation & Setup](#installation--setup)
- [Running the Application](#running-the-application)
- [How It Works](#how-it-works)
- [Supported Platforms](#supported-platforms)
- [Authors](#authors)

---

## 📖 About the Project

The **Device Price Comparison Tool** is a web-based application that allows users to search for any electronic device and instantly compare its price across major Indian e-commerce platforms like Amazon, Flipkart, Croma, Reliance Digital, and Bajaj Electronics.

The tool uses **Selenium** for browser automation to scrape live product prices, a **Flask** backend to serve the API and UI, and **SQLite** to store search history.

---

## ✨ Features

- 🔍 **Real-Time Price Scraping** — Fetches live prices from multiple e-commerce websites
- 🤖 **Smart Product Matching** — Uses NLP-based text similarity and keyword scoring to match the exact product across different platforms
- 💡 **Google Fallback Search** — If direct site search fails, falls back to a Google `site:` search to find the product URL
- 📊 **Side-by-Side Comparison** — Displays all results in a clean grid layout for easy comparison
- 🕐 **Search History** — Stores the last 20 searches in a local SQLite database
- ⚡ **Background Status Log** — Live status panel shows the scraping process in real time
- 📱 **Responsive UI** — Works on desktop and mobile browsers

---

## 🛠️ Tech Stack

| Layer       | Technology                          |
|-------------|-------------------------------------|
| Backend     | Python 3.x, Flask                   |
| Scraping    | Selenium, WebDriver Manager         |
| Database    | SQLite (via Python `sqlite3`)        |
| Frontend    | HTML5, CSS3, Vanilla JavaScript     |
| Browser     | Google Chrome (headless mode)       |

---

## 📁 Project Structure

```
device-price-comparison/
│
├── app.py               # Flask application — routes and API endpoints
├── scraper.py           # Selenium-based web scraper for all platforms
├── database.py          # SQLite database setup and query functions
├── requirements.txt     # Python dependencies
│
├── templates/
│   └── index.html       # Main frontend HTML page
│
└── static/
    ├── style.css        # Styling for the UI
    └── script.js        # Frontend JavaScript logic
```

---

## ✅ Prerequisites

Before running this project, make sure you have the following installed:

- **Python 3.8+** → [Download Python](https://www.python.org/downloads/)
- **Google Chrome Browser** → [Download Chrome](https://www.google.com/chrome/)
- **pip** (comes with Python)
- **Git** → [Download Git](https://git-scm.com/)

> ⚠️ Chrome must be installed on your system. The `webdriver-manager` package automatically downloads the matching ChromeDriver — no manual setup needed.

---

## 🚀 Installation & Setup

Follow these steps to set up the project locally:

### Step 1 — Clone the Repository

```bash
git clone https://github.com/SwarajSuryabhan/device-price-comparison-tool.git
cd device-price-comparison-tool
```

### Step 2 — Create a Virtual Environment (Recommended)

```bash
# On Windows
python -m venv venv
venv\Scripts\activate

# On macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### Step 3 — Install Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- `Flask` — Web framework
- `selenium` — Browser automation for scraping
- `webdriver-manager` — Automatically manages ChromeDriver

---

## ▶️ Running the Application

### Step 1 — Start the Flask Server

```bash
python app.py
```

You should see output like:

```
* Running on http://127.0.0.1:5000
* Debug mode: on
```

### Step 2 — Open in Browser

Open your browser and go to:

```
http://127.0.0.1:5000
```

### Step 3 — Search for a Product

1. Type a product name in the search box
   - Example: `Apple iPhone 16 128GB Black`
   - Example: `Samsung Galaxy S24 Ultra`
   - Example: `OnePlus 12 256GB`
2. Click **Compare Prices**
3. Wait for the scraper to fetch results (may take 30–60 seconds)
4. View the price comparison results side by side

---

## ⚙️ How It Works

```
User enters product name
        ↓
Flask /compare endpoint receives the query
        ↓
Selenium launches headless Chrome
        ↓
Searches Amazon → Flipkart → Croma → Reliance Digital → Bajaj Electronics
        ↓
For each site:
  ├── Fetches search results page
  ├── Scores each listing using text similarity + keyword matching
  ├── Selects the best-matching product
  └── Navigates to product page to fetch the exact price
        ↓
Google fallback if direct search fails
        ↓
Results returned as JSON → Displayed in UI
        ↓
Search query saved to SQLite database
```

### Matching Algorithm

The scraper uses a **combined scoring system**:

| Component         | Weight | Description                                      |
|-------------------|--------|--------------------------------------------------|
| Text Similarity   | 65%    | SequenceMatcher ratio between query and title    |
| Keyword Score     | 35%    | Fraction of query keywords found in product title |
| Price Closeness   | 30%    | Used as tiebreaker when reference price exists   |

Products are only shown if they pass a **strict token match** — important tokens like model numbers, storage sizes (128GB, 256GB), and color must be present in the product title.

---

## 🌐 Supported Platforms

| Platform          | URL                              | Search Method         |
|-------------------|----------------------------------|-----------------------|
| Amazon India      | amazon.in                        | Direct + Google fallback |
| Flipkart          | flipkart.com                     | Direct + Google fallback |
| Croma             | croma.com                        | Direct search         |
| Reliance Digital  | reliancedigital.in               | Direct search         |
| Bajaj Electronics | bajajelectronics.com             | Direct search         |

---

## 👨‍💻 Authors

This project was created as a **Final Year Project** by:

| Name                   |
|------------------------|
| Swaraj Suryabhan       |
| Apurva Deshpande       |
| Vyankatesh Chandekar   |

---

## 📝 Notes

- Scraping results depend on website structure — if a site redesigns its HTML, selectors may need to be updated in `scraper.py`
- The tool uses headless Chrome and simulates human-like behaviour to avoid bot detection
- Search results may vary based on product availability and current stock on each platform
- Average comparison time: **30–90 seconds** per search (due to navigating multiple websites)

---

## 📄 License

This project is for **educational purposes** as part of a Final Year Project submission.

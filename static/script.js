async function comparePrices() {
  const query = document.getElementById("query").value.trim();
  const resultsDiv = document.getElementById("results");
  const messageDiv = document.getElementById("message");
  const loadingDiv = document.getElementById("loading");
  const debugDiv = document.getElementById("debug");

  resultsDiv.innerHTML = "";
  messageDiv.innerHTML = "";
  debugDiv.innerHTML = "";

  if (!query) {
    messageDiv.innerHTML = "Enter product name";
    return;
  }

  loadingDiv.classList.remove("hidden");

  try {
    const res = await fetch("/compare", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query }),
    });

    let data;
    try {
      data = await res.json();
    } catch (jsonError) {
      loadingDiv.classList.add("hidden");
      messageDiv.innerHTML = "Server did not return valid JSON.";
      return;
    }

    loadingDiv.classList.add("hidden");

    if (!res.ok) {
      messageDiv.innerHTML = data.error || "Server error occurred.";
      loadHistory();
      return;
    }

    const debugItems = Array.isArray(data.debug) ? data.debug : [];
    debugItems.forEach((site) => {
      const p = document.createElement("p");
      p.innerHTML = `Checking ${site.site} → ${site.status}`;
      debugDiv.appendChild(p);
    });

    const items = Array.isArray(data.results) ? data.results : [];

    if (data.status === "not_found") {
      messageDiv.innerHTML = "Product not found on any website.";
    } else if (data.status === "single") {
      const onlyItem = items.find((i) => i.best_deal) || items[0];
      if (onlyItem && onlyItem.price && onlyItem.price > 0) {
        messageDiv.innerHTML = `Best available result found on <b>${onlyItem.website}</b> at ₹${onlyItem.price}.`;
      } else if (onlyItem) {
        messageDiv.innerHTML = `Product link found on <b>${onlyItem.website}</b>, but price could not be scraped.`;
      }
    } else if (data.status === "compare") {
      const best = items.find((i) => i.best_deal);
      if (best) {
        messageDiv.innerHTML = `Lowest price on <b>${best.website}</b> ₹${best.price}`;
      }
    } else if (data.status === "error") {
      messageDiv.innerHTML = data.error || "Scraper error occurred.";
    }

    items.forEach((item) => {
      const card = document.createElement("div");
      card.className = item.best_deal ? "result-card best-deal" : "result-card";

      card.innerHTML = `
                <h3>${item.website}</h3>
                <p><strong>Product:</strong> ${item.product_name}</p>
                <p><strong>Price:</strong> ${item.price && item.price > 0 ? "₹" + item.price : "Not available"}</p>
                <p><strong>Rating:</strong> ${item.rating || "N/A"}</p>
                <p><a href="${item.link}" target="_blank">Open Product</a></p>
                ${data.status === "compare" && item.best_deal ? "<p class='best-tag'>Lowest Price</p>" : ""}
                ${data.status === "single" && item.best_deal ? "<p class='best-tag'>Available Here</p>" : ""}
            `;

      resultsDiv.appendChild(card);
    });

    loadHistory();
  } catch (e) {
    loadingDiv.classList.add("hidden");
    messageDiv.innerHTML = `Error fetching data: ${e.message}`;
    console.error("Fetch error:", e);
    loadHistory();
  }
}

async function loadHistory() {
  const historyDiv = document.getElementById("history");
  historyDiv.innerHTML = "";

  try {
    const res = await fetch("/history");
    const data = await res.json();

    if (!Array.isArray(data) || data.length === 0) {
      historyDiv.innerHTML = "<p>No search history yet.</p>";
      return;
    }

    data.forEach((item, index) => {
      const row = document.createElement("div");
      row.className = "history-item";
      row.innerHTML = `
                <p><strong>${index + 1}. ${item.query}</strong></p>
                <p class="history-time">${item.searched_at}</p>
            `;
      historyDiv.appendChild(row);
    });
  } catch (e) {
    historyDiv.innerHTML = "<p>Could not load history.</p>";
  }
}

window.onload = loadHistory;

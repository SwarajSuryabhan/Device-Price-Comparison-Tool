from flask import Flask, render_template, request, jsonify
from scraper import compare_prices
from database import init_db, save_search, get_search_history

app = Flask(__name__)
init_db()


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/compare", methods=["POST"])
def compare():
    try:
        data = request.get_json(silent=True) or {}
        query = data.get("query", "").strip()

        if not query:
            return jsonify({"error": "Enter product name"}), 400

        save_search(query)
        result = compare_prices(query)

        if not isinstance(result, dict):
            return jsonify({"error": "Invalid response from scraper"}), 500

        return jsonify(result)

    except Exception as e:
        print("APP ERROR:", e)
        return jsonify({"error": f"Server error: {str(e)}"}), 500


@app.route("/history", methods=["GET"])
def history():
    try:
        history_data = get_search_history()
        return jsonify(history_data)
    except Exception as e:
        print("HISTORY ERROR:", e)
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
    
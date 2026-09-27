from flask import Flask, jsonify, render_template, request
from gnf import convert_to_gnf, analyze_grammar

app = Flask(__name__)

@app.get("/")
def home():
    return render_template("index.html")

@app.post("/api/analyze")
def analyze():
    data = request.get_json(silent=True) or {}
    return jsonify(analyze_grammar(data.get("grammar", "")))

@app.post("/api/convert")
def convert():
    data = request.get_json(silent=True) or {}
    try:
        result = convert_to_gnf(data.get("grammar", ""))
        return jsonify(result)
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"ok": False, "error": f"Conversion error: {exc}"}), 500

if __name__ == "__main__":
    app.run(debug=True)

from flask import Flask, request, jsonify
import requests
import json

app = Flask(__name__)

# --- Configuration ---
HALFBLOOD_URL = "https://halfblood.famapp.in/vpa/verifyExt"
RAZORPAY_IFSC_URL = "https://ifsc.razorpay.com/"
HEADERS = {
    'User-Agent': "A015 | Android 15 | Dalvik/2.1.0 | Tetris | 318D0D6589676E17F88CCE03A86C2591C8EBAFBA |  (Build -1) | 3DB5HIEMMG",
    'Accept': "application/json",
    'Content-Type': "application/json",
    'authorization': "Token eyJlbmMiOiJBMjU2Q0JDLUhTNTEyIiwiZXBrIjp7Imt0e..."
}

ALLOWED_KEYS = {
    "notfirnkanshs": "Free User",
    "456": "Premium User",
    "keyNever019191": "Admin"
}

def check_api_key(req):
    api_key = req.headers.get("x-api-key") or req.args.get("key")
    if not api_key:
        return False, "Missing API key"
    if api_key not in ALLOWED_KEYS:
        return False, "Invalid API key"
    return True, ALLOWED_KEYS[api_key]


def fetch_and_chain(upi_id):
    vpa_payload = {"upi_string": f"upi://pay?pa={upi_id}"}
    try:
        response_vpa = requests.post(HALFBLOOD_URL, data=json.dumps(vpa_payload), headers=HEADERS, timeout=10)
        response_vpa.raise_for_status()
        vpa_info = response_vpa.json().get("data", {}).get("verify_vpa_resp", {})
        if not vpa_info:
            return {"error": "No VPA data found"}, 400
        vpa_details = {
            "name": vpa_info.get("name"),
            "vpa": vpa_info.get("vpa"),
            "ifsc": vpa_info.get("ifsc")
        }

        result = {"vpa_details": vpa_details, "bank_details_raw": None}
        if vpa_details.get("ifsc"):
            ifsc_code = vpa_details["ifsc"]
            r = requests.get(f"https://ifsc.razorpay.com/{ifsc_code}", timeout=10)
            result["bank_details_raw"] = r.json() if r.status_code == 200 else {"error": "IFSC lookup failed"}
        return result, 200
    except Exception as e:
        return {"error": str(e)}, 500


@app.route("/api/upi", methods=["GET"])
def api_upi_lookup():
    is_valid, message = check_api_key(request)
    if not is_valid:
        return jsonify({"error": message}), 403

    upi_id = request.args.get("upi_id")
    if not upi_id:
        return jsonify({"error": "Missing required parameter: upi_id"}), 400

    result, status = fetch_and_chain(upi_id)
    return jsonify(result), status


# ✅ For Vercel handler
def handler(request, *args, **kwargs):
    return app(request.environ, lambda status, headers: (status, headers))

import os
import cloudinary
import cloudinary.uploader
import requests
from flask import Flask, request, jsonify, render_template
import time
from flask import send_from_directory
import json

app = Flask(__name__)

cloudinary.config(
    cloud_name="dnw0kasdu",
    api_key="133831713626296",
    api_secret="NyFc9HLUksOPFFKGaeX5RG4z4Vs"
)

ENHANCOR_API_KEY = "92c74fb31ede7aafc43e5d179967fa929c0e8de5078ca64a71d8c208132b17dc"
ENHANCOR_URL = "https://api.enhancor.ai/api/realistic-skin/v1/queue"
ENHANCOR_STATUS_URL = "https://api.enhancor.ai/api/realistic-skin/v1/status"
WEBHOOK_URL = "https://your-webhook-url.com"  


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(OUTPUT_FOLDER, filename)

@app.route('/enhance', methods=['POST'])
def enhance_images():
    if 'images' not in request.files:
        return jsonify({"error": "No images provided"}), 400

    images = request.files.getlist('images')
    # Get enhancement parameters from request.form
    params = request.form

    # Parse enhancement parameters with defaults
    enhancementMode = params.get("enhancementMode", "standard")
    portrait_upscale = params.get("portrait_upscale", "true").lower() == "true"
    portrait_depth = float(params.get("portrait_depth", 0.3))
    skin_texture_level = float(params.get("skin_texture_level", 0.30))
    skin_realism_Level = float(params.get("skin_realism_Level", 1.5))

    nose = params.get("nose", "true").lower() == "true"
    eye_g = params.get("eye_g", "false").lower() == "true"
    l_brow = params.get("l_brow", "false").lower() == "true"
    r_brow = params.get("r_brow", "false").lower() == "true"
    mouth = params.get("mouth", "true").lower() == "true"
    u_lip = params.get("u_lip", "true").lower() == "true"
    l_lip = params.get("l_lip", "true").lower() == "true"
    l_eye = params.get("l_eye", "true").lower() == "true"
    r_eye = params.get("r_eye", "true").lower() == "true"

    results = []

    for image in images:
        try:
            upload_result = cloudinary.uploader.upload(image)
            image_url = upload_result['secure_url']

            payload = {
                "img_url": image_url,
                "webhookUrl": WEBHOOK_URL,
                "enhancementMode": enhancementMode,
                "portrait_upscale": portrait_upscale,
                "portrait_depth": portrait_depth,
                "skin_texture_level": skin_texture_level,
                "skin_realism_Level": skin_realism_Level,
                "nose": nose,
                "eye_g": eye_g,
                "l_brow": l_brow,
                "r_brow": r_brow,
                "mouth": mouth,
                "u_lip": u_lip,
                "l_lip": l_lip,
                "l_eye": l_eye,
                "r_eye": r_eye
            }

            response = requests.post(
                ENHANCOR_URL,
                headers={
                    "x-api-key": ENHANCOR_API_KEY,
                    "Content-Type": "application/json"
                },
                json=payload
            )

            if response.status_code == 200:
                data = response.json()
                results.append({
                    "filename": image.filename,
                    "request_id": data.get("requestId"),
                    "status": "queued"
                })
                print("Enhancor API Response:", response.json())
            else:
                results.append({
                    "filename": image.filename,
                    "status": "failed",
                    "error": response.text
                })
        except Exception as e:
            results.append({
                "filename": image.filename,
                "status": "error",
                "error": str(e)
            })

    return jsonify({"results": results})


@app.route('/status/batch', methods=['POST'])
def check_multiple_statuses():
    data = request.json
    request_ids = data.get("request_ids")

    if not request_ids or not isinstance(request_ids, list):
        return jsonify({"error": "request_ids must be a list"}), 400

    headers = {
        "x-api-key": ENHANCOR_API_KEY,
        "Content-Type": "application/json"
    }

    results = []
    for rid in request_ids:
        try:
            res = requests.post(
                ENHANCOR_STATUS_URL,
                headers=headers,
                json={"request_id": rid}
            )
            if res.status_code == 200:
                result = res.json()
                result["request_id"] = rid  
                results.append(result)
            else:
                results.append({
                    "request_id": rid,
                    "error": "Failed to fetch status",
                    "details": res.text,
                    "status_code": res.status_code
                })
        except Exception as e:
            results.append({
                "request_id": rid,
                "error": "Exception occurred",
                "details": str(e)
            })

    return jsonify({"results": results})

OUTPUT_FOLDER = "downloaded_images"

request_ids = [
    "6875614c2a6c74eca35e64dc",
    "6875614e2a6c74eca35e64e0"
]

headers = {
    "x-api-key": ENHANCOR_API_KEY,
    "Content-Type": "application/json"
}

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

for rid in request_ids:
    print(f"Checking status for {rid}...")
    while True:
        response = requests.post(
            ENHANCOR_STATUS_URL,
            headers=headers,
            json={"request_id": rid}
        )
        if response.status_code == 200:
            result = response.json()
            status = result.get("status")
            print(f"Status for {rid}: {status}")
            
            if status == "COMPLETED":
                image_url = result.get("result")
                if image_url:
                    image_data = requests.get(image_url).content
                    filename = os.path.join(OUTPUT_FOLDER, f"{rid}.png")
                    with open(filename, "wb") as f:
                        f.write(image_data)
                    print(f"Downloaded: {filename}")
                break
            elif status == "FAILED":
                print(f"Request {rid} failed.")
                break
            else:
                time.sleep(5) 
        else:
            print(f"Failed to check status for {rid}: {response.status_code}")
            break

@app.route('/download_ready', methods=['POST'])
def download_ready_images():
    request_ids = request.json.get("request_ids")

    if not request_ids or not isinstance(request_ids, list):
        return jsonify({"error": "request_ids must be a list"}), 400

    headers = {
        "x-api-key": ENHANCOR_API_KEY,
        "Content-Type": "application/json"
    }

    results = []

    for rid in request_ids:
        status_res = requests.post(ENHANCOR_STATUS_URL, headers=headers, json={"request_id": rid})
        if status_res.status_code == 200:
            status_data = status_res.json()
            status = status_data.get("status")
            if status == "COMPLETED":
                result_url = status_data.get("result")
                if result_url:
                    image_data = requests.get(result_url).content
                    filename = f"{OUTPUT_FOLDER}/{rid}.png"
                    with open(filename, "wb") as f:
                        f.write(image_data)
                    results.append({"request_id": rid, "status": "COMPLETED", "file": filename})
            else:
                results.append({"request_id": rid, "status": status})
        else:
            results.append({
                "request_id": rid,
                "error": status_res.text,
                "status_code": status_res.status_code
            })

    return jsonify({"results": results})

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)


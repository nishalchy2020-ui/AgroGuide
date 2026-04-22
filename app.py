import sqlite3
from pathlib import Path
import requests
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "agroguide_secret_key"
DATABASE = "database.db"


def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    if not Path(DATABASE).exists():
        conn = get_db_connection()
        with open("schema.sql", "r", encoding="utf-8") as f:
            conn.executescript(f.read())
        conn.commit()
        conn.close()


def save_history(user_id, module_name, input_data, result_data):
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO history (user_id, module_name, input_data, result_data) VALUES (?, ?, ?, ?)",
        (user_id, module_name, input_data, result_data)
    )
    conn.commit()
    conn.close()


def get_crop_recommendation(soil_type, season, water_availability):
    if soil_type == "Loamy" and season == "Summer" and water_availability == "Medium":
        return ["Maize", "Tomato", "Sunflower"]
    elif soil_type == "Clay" and season == "Rainy" and water_availability == "High":
        return ["Rice", "Sugarcane", "Jute"]
    elif soil_type == "Sandy" and season == "Winter" and water_availability == "Low":
        return ["Peanut", "Millet", "Potato"]
    elif soil_type == "Loamy" and season == "Winter" and water_availability == "Medium":
        return ["Wheat", "Mustard", "Peas"]
    else:
        return ["Spinach", "Onion", "Beans"]


def get_weather_description(weather_code):
    weather_map = {
        0: "Clear sky",
        1: "Mainly clear",
        2: "Partly cloudy",
        3: "Overcast",
        45: "Fog",
        48: "Depositing rime fog",
        51: "Light drizzle",
        53: "Moderate drizzle",
        55: "Dense drizzle",
        61: "Slight rain",
        63: "Moderate rain",
        65: "Heavy rain",
        71: "Slight snow",
        73: "Moderate snow",
        75: "Heavy snow",
        80: "Rain showers",
        81: "Moderate rain showers",
        82: "Violent rain showers",
        95: "Thunderstorm"
    }
    return weather_map.get(weather_code, "Unknown weather")


def get_farming_advice(temperature, wind_speed, weather_description):
    advice = []

    if "rain" in weather_description.lower() or "drizzle" in weather_description.lower():
        advice.append("Rain is expected. Avoid overwatering crops.")
    else:
        advice.append("No significant rain detected. Check if irrigation is needed.")

    if temperature >= 30:
        advice.append("High temperature detected. Water crops early morning or evening.")
    elif temperature <= 10:
        advice.append("Low temperature detected. Protect sensitive crops from cold stress.")
    else:
        advice.append("Temperature is moderate for most crops.")

    if wind_speed >= 20:
        advice.append("Strong wind detected. Protect young plants if necessary.")
    else:
        advice.append("Wind conditions are generally manageable.")

    return advice


def get_irrigation_advice(crop, growth_stage):
    irrigation_data = {
        "Wheat": {
            "Seedling": "Water lightly every 5-7 days. Avoid waterlogging.",
            "Vegetative": "Maintain moderate soil moisture. Irrigate every 7-10 days.",
            "Flowering": "Provide regular watering. This stage is sensitive to water stress.",
            "Harvesting": "Reduce irrigation to avoid crop damage before harvest."
        },
        "Rice": {
            "Seedling": "Keep field moist with shallow standing water.",
            "Vegetative": "Maintain regular flooding or wet soil conditions.",
            "Flowering": "Ensure steady water supply. Do not let field dry out.",
            "Harvesting": "Drain water 1-2 weeks before harvest."
        },
        "Tomato": {
            "Seedling": "Water lightly and regularly to support root establishment.",
            "Vegetative": "Irrigate every 3-5 days depending on soil moisture.",
            "Flowering": "Consistent watering is important to support fruit set.",
            "Harvesting": "Reduce excess watering to improve fruit quality."
        },
        "Maize": {
            "Seedling": "Light irrigation every 4-6 days.",
            "Vegetative": "Water regularly, especially during active growth.",
            "Flowering": "Critical stage. Ensure adequate moisture.",
            "Harvesting": "Reduce watering as cobs mature."
        }
    }

    return irrigation_data.get(crop, {}).get(
        growth_stage,
        "General advice: monitor soil moisture and irrigate based on crop condition."
    )


def get_fertilizer_advice(crop, growth_stage):
    fertilizer_data = {
        "Wheat": {
            "Seedling": "Apply a balanced starter fertilizer with nitrogen and phosphorus.",
            "Vegetative": "Top-dress with nitrogen fertilizer to support leaf growth.",
            "Flowering": "Use moderate nitrogen if needed and monitor crop health.",
            "Harvesting": "No major fertilizer needed at harvesting stage."
        },
        "Rice": {
            "Seedling": "Apply basal fertilizer rich in phosphorus before or during planting.",
            "Vegetative": "Use nitrogen fertilizer in split doses.",
            "Flowering": "Apply potassium-rich fertilizer to support grain formation.",
            "Harvesting": "Stop fertilizer application near harvest."
        },
        "Tomato": {
            "Seedling": "Apply compost or a mild balanced fertilizer.",
            "Vegetative": "Use nitrogen-rich fertilizer for healthy plant growth.",
            "Flowering": "Use phosphorus and potassium fertilizer for flowering and fruiting.",
            "Harvesting": "Apply light compost if needed, avoid excess nitrogen."
        },
        "Maize": {
            "Seedling": "Use starter fertilizer with phosphorus for root development.",
            "Vegetative": "Apply nitrogen-rich fertilizer for stem and leaf growth.",
            "Flowering": "Use balanced fertilizer and maintain nutrient availability.",
            "Harvesting": "No additional major fertilizer needed."
        }
    }

    return fertilizer_data.get(crop, {}).get(
        growth_stage,
        "General advice: use a balanced fertilizer and adjust based on soil condition."
    )


def get_pest_disease_help(crop, symptom):
    pest_data = {
        "Tomato": {
            "Yellow Leaves": {
                "issue": "Possible nutrient deficiency or early blight",
                "advice": "Check nitrogen levels, remove affected leaves, and use a suitable fungicide if needed."
            },
            "Leaf Spots": {
                "issue": "Possible fungal leaf spot disease",
                "advice": "Remove infected leaves, avoid overhead watering, and apply fungicide if the spread continues."
            },
            "Wilting": {
                "issue": "Possible root rot or bacterial wilt",
                "advice": "Check soil drainage, avoid overwatering, and remove severely affected plants."
            },
            "Holes in Leaves": {
                "issue": "Possible caterpillar or insect attack",
                "advice": "Inspect the underside of leaves and use appropriate insect control methods."
            }
        },
        "Rice": {
            "Yellow Leaves": {
                "issue": "Possible nitrogen deficiency or rice blast stress",
                "advice": "Apply balanced fertilizer and inspect plants for disease symptoms."
            },
            "Leaf Spots": {
                "issue": "Possible rice blast or brown spot disease",
                "advice": "Use disease-resistant varieties and apply recommended fungicide if necessary."
            },
            "Wilting": {
                "issue": "Possible water stress or root damage",
                "advice": "Maintain proper water level and inspect roots and soil condition."
            },
            "Holes in Leaves": {
                "issue": "Possible stem borer or leaf feeder attack",
                "advice": "Monitor pest activity and use recommended pest management practices."
            }
        },
        "Wheat": {
            "Yellow Leaves": {
                "issue": "Possible nutrient deficiency or rust disease",
                "advice": "Check nitrogen supply and inspect leaves for rust pustules."
            },
            "Leaf Spots": {
                "issue": "Possible leaf blight or fungal infection",
                "advice": "Remove infected plant debris and consider fungicide treatment if severe."
            },
            "Wilting": {
                "issue": "Possible root stress or poor soil moisture",
                "advice": "Check irrigation schedule and root health."
            },
            "Holes in Leaves": {
                "issue": "Possible insect feeding damage",
                "advice": "Inspect plants closely and apply insect control where needed."
            }
        },
        "Maize": {
            "Yellow Leaves": {
                "issue": "Possible nitrogen deficiency",
                "advice": "Apply nitrogen-rich fertilizer and monitor plant recovery."
            },
            "Leaf Spots": {
                "issue": "Possible fungal leaf disease",
                "advice": "Remove badly affected leaves and apply recommended fungicide if needed."
            },
            "Wilting": {
                "issue": "Possible drought stress or root damage",
                "advice": "Improve watering and inspect root zone condition."
            },
            "Holes in Leaves": {
                "issue": "Possible fall armyworm or insect attack",
                "advice": "Inspect leaf whorls and apply appropriate pest control quickly."
            }
        }
    }

    crop_info = pest_data.get(crop, {})
    result = crop_info.get(symptom)

    if result:
        return result

    return {
        "issue": "General crop stress or unidentified issue",
        "advice": "Inspect watering, soil condition, and visible pest activity. Consider expert diagnosis if symptoms continue."
    }


def get_crop_suitability_data(soil_type, season, water_availability, farm_size, farming_goal):
    if soil_type == "Loamy" and season == "Winter" and water_availability == "Medium":
        return {
            "best_crop": "Wheat",
            "alternatives": ["Mustard", "Peas"],
            "reason": "Loamy soil with moderate water in winter is highly suitable for wheat and other seasonal crops.",
            "guide": [
                "Prepare well-drained fertile soil before sowing.",
                "Maintain moderate irrigation during growth.",
                "Use balanced fertilizer in early growth stages.",
                "Monitor crop regularly for nutrient deficiency and disease signs."
            ],
            "chart_data": {
                "Wheat": 50,
                "Mustard": 30,
                "Peas": 20
            }
        }
    elif soil_type == "Clay" and season == "Rainy" and water_availability == "High":
        return {
            "best_crop": "Rice",
            "alternatives": ["Sugarcane", "Jute"],
            "reason": "Clay soil with high water availability during rainy season supports water-tolerant crops very well.",
            "guide": [
                "Maintain proper standing water for rice during active growth.",
                "Apply nitrogen fertilizer in split doses.",
                "Control weed growth early.",
                "Inspect regularly for leaf disease and pest attack."
            ],
            "chart_data": {
                "Rice": 55,
                "Sugarcane": 25,
                "Jute": 20
            }
        }
    elif soil_type == "Sandy" and season == "Summer" and water_availability == "Low":
        return {
            "best_crop": "Millet",
            "alternatives": ["Peanut", "Sunflower"],
            "reason": "Sandy soil and low water conditions are better suited for drought-tolerant crops.",
            "guide": [
                "Use organic matter to improve moisture retention.",
                "Irrigate carefully and avoid water waste.",
                "Choose drought-resistant crop varieties if possible.",
                "Monitor soil nutrients because sandy soil loses nutrients quickly."
            ],
            "chart_data": {
                "Millet": 45,
                "Peanut": 30,
                "Sunflower": 25
            }
        }
    elif soil_type == "Loamy" and season == "Summer" and water_availability == "Medium":
        return {
            "best_crop": "Tomato",
            "alternatives": ["Maize", "Sunflower"],
            "reason": "Loamy soil in summer with moderate water is suitable for both vegetable and field crops.",
            "guide": [
                "Maintain regular irrigation without waterlogging.",
                "Use compost and balanced fertilizer for better growth.",
                "Provide pest monitoring during flowering and fruiting stage.",
                "Keep field clean and manage weeds properly."
            ],
            "chart_data": {
                "Tomato": 40,
                "Maize": 35,
                "Sunflower": 25
            }
        }
    else:
        return {
            "best_crop": "Beans",
            "alternatives": ["Spinach", "Onion"],
            "reason": "These crops are generally suitable under mixed or moderate farming conditions.",
            "guide": [
                "Check soil moisture before irrigation.",
                "Use balanced fertilizer depending on growth stage.",
                "Observe crop leaves regularly for stress symptoms.",
                "Maintain proper spacing and weed control."
            ],
            "chart_data": {
                "Beans": 40,
                "Spinach": 35,
                "Onion": 25
            }
        }


def get_crop_cultivation_guide(crop):
    guides = {
        "Wheat": {
            "season": "Winter",
            "soil": "Well-drained loamy soil",
            "duration": "110 to 130 days",
            "steps": [
                {
                    "stage": "Land Preparation",
                    "time": "7 to 10 days before sowing",
                    "details": "Plough the field properly, remove weeds, and prepare fine level soil."
                },
                {
                    "stage": "Sowing",
                    "time": "Day 0",
                    "details": "Use healthy seeds and sow them evenly with proper spacing."
                },
                {
                    "stage": "First Irrigation",
                    "time": "20 to 25 days after sowing",
                    "details": "Give first proper irrigation depending on soil moisture."
                },
                {
                    "stage": "Fertilizer Application",
                    "time": "Base dose at sowing, nitrogen after 25 to 30 days",
                    "details": "Apply phosphorus at sowing and nitrogen during vegetative growth."
                },
                {
                    "stage": "Weed Control",
                    "time": "20 to 30 days after sowing",
                    "details": "Remove weeds early to reduce competition for nutrients and water."
                },
                {
                    "stage": "Pest and Disease Care",
                    "time": "Inspect every 7 days",
                    "details": "Monitor regularly for rust disease, aphids, and nutrient deficiency."
                },
                {
                    "stage": "Harvesting",
                    "time": "110 to 130 days after sowing",
                    "details": "Harvest when the crop turns golden yellow and grains become hard."
                },
                {
                    "stage": "Storage",
                    "time": "Immediately after drying",
                    "details": "Dry grains properly and store in a cool, dry place."
                }
            ],
            "chart_data": {
                "Land Preparation": 10,
                "Sowing": 5,
                "Irrigation & Fertilizer": 25,
                "Weed Control": 10,
                "Pest Care": 15,
                "Harvesting": 20,
                "Storage": 15
            }
        },
        "Rice": {
            "season": "Rainy",
            "soil": "Clay or clay-loam soil with good water retention",
            "duration": "100 to 150 days",
            "steps": [
                {
                    "stage": "Land Preparation",
                    "time": "7 to 12 days before transplanting",
                    "details": "Prepare puddled field and level the land properly for standing water."
                },
                {
                    "stage": "Nursery and Transplanting",
                    "time": "Nursery first, transplant around 20 to 30 days later",
                    "details": "Raise seedlings in nursery first, then transplant healthy seedlings into the field."
                },
                {
                    "stage": "Irrigation",
                    "time": "Continuous shallow water after transplanting",
                    "details": "Maintain shallow standing water during vegetative growth."
                },
                {
                    "stage": "Fertilizer Application",
                    "time": "Base dose before planting, nitrogen in split doses after 20 to 25 days",
                    "details": "Apply basal fertilizer first, then nitrogen in split doses."
                },
                {
                    "stage": "Weed Control",
                    "time": "15 to 25 days after transplanting",
                    "details": "Control weeds early using manual or chemical methods."
                },
                {
                    "stage": "Pest and Disease Care",
                    "time": "Inspect every 7 days",
                    "details": "Watch for blast disease, stem borer, and leaf folder."
                },
                {
                    "stage": "Harvesting",
                    "time": "100 to 150 days after planting",
                    "details": "Harvest when grains are mature and the panicles turn yellow."
                },
                {
                    "stage": "Storage",
                    "time": "Immediately after drying",
                    "details": "Dry paddy well before storage to avoid moisture damage."
                }
            ],
            "chart_data": {
                "Land Preparation": 10,
                "Transplanting": 10,
                "Irrigation & Fertilizer": 30,
                "Weed Control": 10,
                "Pest Care": 15,
                "Harvesting": 15,
                "Storage": 10
            }
        },
        "Tomato": {
            "season": "Warm season / Summer",
            "soil": "Fertile loamy soil with good drainage",
            "duration": "90 to 120 days",
            "steps": [
                {
                    "stage": "Land Preparation",
                    "time": "7 to 10 days before transplanting",
                    "details": "Prepare fine soil and mix organic compost before planting."
                },
                {
                    "stage": "Sowing / Nursery",
                    "time": "Day 0 in nursery",
                    "details": "Raise seedlings first in nursery trays or seed bed."
                },
                {
                    "stage": "Transplanting",
                    "time": "20 to 25 days after sowing",
                    "details": "Transplant healthy seedlings with proper spacing."
                },
                {
                    "stage": "Irrigation",
                    "time": "First light watering immediately after transplanting, then every 3 to 5 days",
                    "details": "Water regularly but avoid waterlogging."
                },
                {
                    "stage": "Fertilizer Application",
                    "time": "Base dose at transplanting, flowering dose after 25 to 35 days",
                    "details": "Use balanced fertilizer at planting, then phosphorus and potassium during flowering."
                },
                {
                    "stage": "Weed Control",
                    "time": "15 to 20 days after transplanting, then as needed",
                    "details": "Remove weeds regularly and keep the field clean."
                },
                {
                    "stage": "Pest and Disease Care",
                    "time": "Inspect every 5 to 7 days",
                    "details": "Inspect for leaf spot, wilting, aphids, and fruit borer."
                },
                {
                    "stage": "Harvesting",
                    "time": "70 to 90 days after transplanting",
                    "details": "Harvest fruits when they are mature and reach the proper color."
                },
                {
                    "stage": "Storage",
                    "time": "Immediately after harvest",
                    "details": "Store in a cool, dry place and avoid rough handling."
                }
            ],
            "chart_data": {
                "Land Preparation": 10,
                "Nursery/Transplanting": 15,
                "Irrigation": 15,
                "Fertilizer": 15,
                "Weed Control": 10,
                "Pest Care": 15,
                "Harvesting": 10,
                "Storage": 10
            }
        },
        "Maize": {
            "season": "Summer / Rainy",
            "soil": "Well-drained fertile loamy soil",
            "duration": "90 to 120 days",
            "steps": [
                {
                    "stage": "Land Preparation",
                    "time": "7 to 10 days before sowing",
                    "details": "Plough and level the field well before sowing."
                },
                {
                    "stage": "Sowing",
                    "time": "Day 0",
                    "details": "Use healthy seeds and plant with proper row spacing."
                },
                {
                    "stage": "Irrigation",
                    "time": "At seedling stage, vegetative stage, and especially flowering stage",
                    "details": "Irrigate regularly according to crop stage and soil moisture."
                },
                {
                    "stage": "Fertilizer Application",
                    "time": "Base dose at sowing, nitrogen after 20 to 30 days",
                    "details": "Apply phosphorus at sowing and nitrogen during active growth."
                },
                {
                    "stage": "Weed Control",
                    "time": "15 to 25 days after sowing",
                    "details": "Control weeds early, especially in the first few weeks."
                },
                {
                    "stage": "Pest and Disease Care",
                    "time": "Inspect every 7 days",
                    "details": "Watch for fall armyworm, stem borer, and leaf disease."
                },
                {
                    "stage": "Harvesting",
                    "time": "90 to 120 days after sowing",
                    "details": "Harvest when cobs are mature and kernels are fully developed."
                },
                {
                    "stage": "Storage",
                    "time": "Immediately after drying",
                    "details": "Dry cobs or grains properly before storage."
                }
            ],
            "chart_data": {
                "Land Preparation": 10,
                "Sowing": 5,
                "Irrigation": 20,
                "Fertilizer": 15,
                "Weed Control": 10,
                "Pest Care": 15,
                "Harvesting": 15,
                "Storage": 10
            }
        }
    }

    return guides.get(crop, {
        "season": "General",
        "soil": "Moderately fertile and well-drained soil",
        "duration": "Depends on crop type",
        "steps": [
            {
                "stage": "Land Preparation",
                "time": "Before planting",
                "details": "Prepare the field properly before sowing."
            },
            {
                "stage": "Sowing",
                "time": "Day 0",
                "details": "Use healthy seeds and proper spacing."
            },
            {
                "stage": "Irrigation",
                "time": "As needed",
                "details": "Irrigate according to soil moisture and crop condition."
            },
            {
                "stage": "Fertilizer",
                "time": "Base dose and later growth stages",
                "details": "Use balanced fertilizer based on crop stage."
            },
            {
                "stage": "Weed Control",
                "time": "Regularly",
                "details": "Remove weeds regularly."
            },
            {
                "stage": "Pest and Disease Care",
                "time": "Weekly inspection",
                "details": "Inspect the crop regularly for pests and diseases."
            },
            {
                "stage": "Harvesting",
                "time": "At maturity",
                "details": "Harvest at proper maturity stage."
            },
            {
                "stage": "Storage",
                "time": "After drying",
                "details": "Store produce in a clean and dry place."
            }
        ],
        "chart_data": {
            "Land Preparation": 10,
            "Sowing": 10,
            "Irrigation": 20,
            "Fertilizer": 15,
            "Weed Control": 10,
            "Pest Care": 15,
            "Harvesting": 10,
            "Storage": 10
        }
    })


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        full_name = request.form["full_name"].strip()
        email = request.form["email"].strip()
        password = request.form["password"]

        if not full_name or not email or not password:
            flash("Please fill in all fields.")
            return render_template("register.html")

        password_hash = generate_password_hash(password)

        try:
            conn = get_db_connection()
            conn.execute(
                "INSERT INTO users (full_name, email, password) VALUES (?, ?, ?)",
                (full_name, email, password_hash)
            )
            conn.commit()
            conn.close()
            flash("Registration successful. You can now log in.")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("This email is already registered.")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip()
        password = request.form["password"]

        if not email or not password:
            flash("Please enter both email and password.")
            return render_template("login.html")

        conn = get_db_connection()
        user = conn.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,)
        ).fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["user_name"] = user["full_name"]
            flash("Login successful.")
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid email or password.")

    return render_template("login.html")


@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        flash("Please log in first.")
        return redirect(url_for("login"))

    conn = get_db_connection()
    rows = conn.execute("""
        SELECT module_name, COUNT(*) as total
        FROM history
        WHERE user_id = ?
        GROUP BY module_name
    """, (session["user_id"],)).fetchall()
    conn.close()

    module_counts = {
        "Crop Recommendation": 0,
        "Weather": 0,
        "Irrigation": 0,
        "Fertilizer": 0,
        "Pest Help": 0,
        "Crop Suitability": 0,
        "Crop Cultivation": 0
    }

    for row in rows:
        if row["module_name"] in module_counts:
            module_counts[row["module_name"]] = row["total"]

    return render_template(
        "dashboard.html",
        user_name=session["user_name"],
        module_counts=module_counts
    )


@app.route("/crop-recommendation", methods=["GET", "POST"])
def crop_recommendation():
    if "user_id" not in session:
        flash("Please log in first.")
        return redirect(url_for("login"))

    recommendations = None

    if request.method == "POST":
        soil_type = request.form["soil_type"]
        season = request.form["season"]
        water_availability = request.form["water_availability"]

        recommendations = get_crop_recommendation(soil_type, season, water_availability)

        input_data = f"Soil: {soil_type}, Season: {season}, Water: {water_availability}"
        result_data = ", ".join(recommendations)
        save_history(session["user_id"], "Crop Recommendation", input_data, result_data)

    return render_template("crop_recommendation.html", recommendations=recommendations)


@app.route("/crop-suitability", methods=["GET", "POST"])
def crop_suitability():
    if "user_id" not in session:
        flash("Please log in first.")
        return redirect(url_for("login"))

    result = None

    if request.method == "POST":
        soil_type = request.form["soil_type"]
        season = request.form["season"]
        water_availability = request.form["water_availability"]
        farm_size = request.form["farm_size"]
        farming_goal = request.form["farming_goal"]

        result = get_crop_suitability_data(
            soil_type,
            season,
            water_availability,
            farm_size,
            farming_goal
        )

        input_data = (
            f"Soil: {soil_type}, Season: {season}, Water: {water_availability}, "
            f"Farm Size: {farm_size}, Goal: {farming_goal}"
        )
        result_data = f"Best Crop: {result['best_crop']} | Alternatives: {', '.join(result['alternatives'])}"

        save_history(session["user_id"], "Crop Suitability", input_data, result_data)

    return render_template("crop_suitability.html", result=result)


@app.route("/weather", methods=["GET", "POST"])
def weather():
    if "user_id" not in session:
        flash("Please log in first.")
        return redirect(url_for("login"))

    weather_data = None
    advice = None
    city = None

    if request.method == "POST":
        city = request.form["city"].strip()

        if not city:
            flash("Please enter a city name.")
            return render_template("weather.html", weather_data=None, advice=None, city=city)

        try:
            geocode_url = "https://geocoding-api.open-meteo.com/v1/search"
            geocode_params = {
                "name": city,
                "count": 1,
                "language": "en",
                "format": "json"
            }
            geo_response = requests.get(geocode_url, params=geocode_params, timeout=10)
            geo_data = geo_response.json()

            if "results" not in geo_data or not geo_data["results"]:
                flash("City not found. Please try again.")
                return render_template("weather.html", weather_data=None, advice=None, city=city)

            latitude = geo_data["results"][0]["latitude"]
            longitude = geo_data["results"][0]["longitude"]
            resolved_name = geo_data["results"][0]["name"]
            country = geo_data["results"][0].get("country", "")

            weather_url = "https://api.open-meteo.com/v1/forecast"
            weather_params = {
                "latitude": latitude,
                "longitude": longitude,
                "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code"
            }
            weather_response = requests.get(weather_url, params=weather_params, timeout=10)
            weather_json = weather_response.json()

            current = weather_json.get("current", {})
            temperature = current.get("temperature_2m")
            humidity = current.get("relative_humidity_2m")
            wind_speed = current.get("wind_speed_10m")
            weather_code = current.get("weather_code")

            description = get_weather_description(weather_code)
            advice = get_farming_advice(temperature, wind_speed, description)

            weather_data = {
                "city": resolved_name,
                "country": country,
                "temperature": temperature,
                "humidity": humidity,
                "wind_speed": wind_speed,
                "description": description
            }

            input_data = f"City: {city}"
            result_data = f"{resolved_name}, {country} | Temp: {temperature}°C | Humidity: {humidity}% | Wind: {wind_speed} km/h | Condition: {description}"
            save_history(session["user_id"], "Weather", input_data, result_data)

        except Exception:
            flash("Unable to fetch weather data right now. Please try again.")

    return render_template("weather.html", weather_data=weather_data, advice=advice, city=city)


@app.route("/irrigation", methods=["GET", "POST"])
def irrigation():
    if "user_id" not in session:
        flash("Please log in first.")
        return redirect(url_for("login"))

    advice = None

    if request.method == "POST":
        crop = request.form["crop"]
        growth_stage = request.form["growth_stage"]
        advice = get_irrigation_advice(crop, growth_stage)

        input_data = f"Crop: {crop}, Stage: {growth_stage}"
        result_data = advice
        save_history(session["user_id"], "Irrigation", input_data, result_data)

    return render_template("irrigation.html", advice=advice)


@app.route("/fertilizer", methods=["GET", "POST"])
def fertilizer():
    if "user_id" not in session:
        flash("Please log in first.")
        return redirect(url_for("login"))

    advice = None

    if request.method == "POST":
        crop = request.form["crop"]
        growth_stage = request.form["growth_stage"]
        advice = get_fertilizer_advice(crop, growth_stage)

        input_data = f"Crop: {crop}, Stage: {growth_stage}"
        result_data = advice
        save_history(session["user_id"], "Fertilizer", input_data, result_data)

    return render_template("fertilizer.html", advice=advice)


@app.route("/pest-help", methods=["GET", "POST"])
def pest_help():
    if "user_id" not in session:
        flash("Please log in first.")
        return redirect(url_for("login"))

    result = None

    if request.method == "POST":
        crop = request.form["crop"]
        symptom = request.form["symptom"]
        result = get_pest_disease_help(crop, symptom)

        input_data = f"Crop: {crop}, Symptom: {symptom}"
        result_data = f"Issue: {result['issue']} | Advice: {result['advice']}"
        save_history(session["user_id"], "Pest Help", input_data, result_data)

    return render_template("pest_help.html", result=result)


@app.route("/history")
def history():
    if "user_id" not in session:
        flash("Please log in first.")
        return redirect(url_for("login"))

    conn = get_db_connection()
    records = conn.execute(
        "SELECT * FROM history WHERE user_id = ? ORDER BY created_at DESC, id DESC",
        (session["user_id"],)
    ).fetchall()
    conn.close()

    return render_template("history.html", records=records)


@app.route("/crop-cultivation", methods=["GET", "POST"])
def crop_cultivation():
    if "user_id" not in session:
        flash("Please log in first.")
        return redirect(url_for("login"))

    guide = None
    selected_crop = None

    if request.method == "POST":
        selected_crop = request.form["crop"]
        guide = get_crop_cultivation_guide(selected_crop)

        input_data = f"Crop: {selected_crop}"
        result_data = f"Season: {guide['season']} | Soil: {guide['soil']} | Duration: {guide['duration']}"
        save_history(session["user_id"], "Crop Cultivation", input_data, result_data)

    return render_template("crop_cultivation.html", guide=guide, selected_crop=selected_crop)


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.")
    return redirect(url_for("home"))


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
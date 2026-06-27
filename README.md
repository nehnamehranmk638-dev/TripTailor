# ✈️ TripTailor

<p align="center">

![Python](https://img.shields.io/badge/Python-3.10+-blue?style=for-the-badge&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-336791?style=for-the-badge&logo=postgresql)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-red?style=for-the-badge)
![Groq](https://img.shields.io/badge/Groq-LLM-orange?style=for-the-badge)

</p>

<p align="center">
An <b>AI-powered Travel Itinerary Planner</b> that generates intelligent, geographically optimized, day-by-day travel plans and allows users to modify them naturally using an integrated AI chat assistant.
</p>

---

# 📖 Table of Contents

- [About The Project](#-about-the-project)
- [Key Features](#-key-features)
- [Tech Stack](#-tech-stack)
- [Project Architecture](#-project-architecture)
- [Getting Started](#-getting-started)
- [Installation](#-installation)
- [Usage](#-usage)
- [Future Improvements](#-future-improvements)
- [Contact](#-contact)

---

# 🌍 About The Project

Planning a vacation often involves switching between multiple websites to search for tourist attractions, hotels, restaurants, routes, travel costs, and schedules. This process is time-consuming and makes it difficult to build an optimized travel plan.

**TripTailor** simplifies this experience by generating a complete itinerary from a simple natural-language prompt.

Simply describe your trip like:

> **"Plan a 5-day trip to Goa with a budget of ₹20,000. I enjoy beaches, cafés, nightlife, and adventure sports."**

TripTailor automatically generates:

- 📅 Day-wise itinerary
- 📍 Optimized travel route
- 🚗 Travel time between locations
- 🏨 Nearby hotel recommendations
- 🍽️ Restaurant suggestions
- 💸 Budget estimation
- 📝 Trip notes

Unlike traditional itinerary generators, TripTailor also includes an **AI-powered chat assistant**, allowing users to modify their itinerary using natural language without rebuilding the trip from scratch.

---

# ✨ Key Features

## 🗺️ Intelligent Itinerary Generation

- Creates realistic multi-day travel plans
- Groups nearby attractions together
- Minimizes unnecessary travel
- Generates optimized schedules

---

## 🚗 Real Road Distance Calculation

Instead of estimating straight-line distances, TripTailor uses **OSRM** to calculate:

- Actual road distance
- Estimated travel duration
- Better daily planning

---

## 🤖 AI Chat Assistant

Modify your itinerary simply by chatting.

Examples:

> "Replace the museum on Day 2 with a beach."

> "Add a famous café."

> "Suggest a vegetarian restaurant."

> "Move the waterfall visit to Day 3."

The assistant automatically updates the itinerary.

---

## 💰 Smart Budget Planning

Automatically estimates:

- Hotel expenses
- Food costs
- Transportation
- Entry fees

and compares them with the user's budget.

---

## 🏨 Hotel Recommendations

Provides nearby hotels based on:

- Planned attractions
- Travel convenience
- Daily itinerary

---

## 🍽️ Restaurant Recommendations

Suggests nearby restaurants for every day's schedule.

---

## 📝 Trip Management

Users can:

- Save trips
- Revisit previous itineraries
- Add personal notes
- Continue editing anytime

---

# 🛠 Tech Stack

## Backend

- FastAPI
- Python 3.10+

## Frontend

- Streamlit

## Database

- PostgreSQL
- SQLAlchemy ORM

## AI

- Groq API
- Llama 3.3 70B


---

# 🏗 Project Architecture

```
User Prompt
      │
      ▼
 AI (Groq + Llama)
      │
Extract Trip Details
      │
      ▼
Database
(Hotels • Attractions • Restaurants)
      │
      ▼
Route Optimization (OSRM)
      │
      ▼
Budget Calculation
      │
      ▼
Generate Day-wise Itinerary
      │
      ▼
 Streamlit Frontend
      │
      ▼
Chat Assistant Updates
```

---

# 🚀 Getting Started

## Prerequisites

- Python 3.10+
- PostgreSQL
- Groq API Key

---

# ⚙️ Installation

Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/TripTailor.git
```

Move into the project directory

```bash
cd TripTailor
```

Create a virtual environment

```bash
python -m venv venv
```

Activate it

### Windows

```bash
venv\Scripts\activate
```

### macOS/Linux

```bash
source venv/bin/activate
```

Install dependencies

```bash
pip install -r requirements.txt
```

---

Create a `.env` file

```env
GROQ_API_KEY=your_api_key

DB_HOST=localhost
DB_PORT=5432
DB_NAME=triptailor
DB_USER=postgres
DB_PASSWORD=your_password
```

---

# ▶️ Usage

Start the backend

```bash
uvicorn backend.main:app --reload
```

Start the frontend

```bash
streamlit run frontend/app.py
```

Open

```
http://localhost:8501
```

Describe your dream trip in natural language and let TripTailor build the perfect itinerary.

---

# 📌 Example Prompt

```
Plan a 4-day trip to Kerala.

Budget: ₹18,000

Interests:
• Nature
• Waterfalls
• Local Food
• Boating
• Photography

Avoid:
• Long hikes
```

TripTailor automatically generates:

- ✅ Day-wise schedule
- ✅ Hotels
- ✅ Restaurants
- ✅ Route planning
- ✅ Budget summary

---

# 🚀 Future Improvements

- Google Maps Integration
- Weather Forecast Integration
- Flight Recommendations
- Train & Bus Booking
- Multi-city Trip Planning
- Collaborative Trip Planning
- Mobile Application
- PDF Export
- Calendar Integration
- Offline Trip Access

---


# 👩‍💻 Contact


GitHub: https://github.com/nehnamehranmk638-dev

Email: nehnamehranmk17@gmail.com

Project Repository:
https://github.com/nehnamehranmk638-dev/TripTailor


---



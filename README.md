# 🏫 NNRG Campus Navigator

NNRG Campus Navigator is an AI-powered virtual assistant designed specifically for students, faculty, and visitors of **Nalla Narasimha Reddy Education Society's Group of Institutions (NNRG)**. 

The chatbot handles queries regarding admissions, HOD directories, canteen menus, transport schedules, sports facilities, and upcoming events using a hybrid AI-search engine.

---

## 🚀 Key Features

* **Dual Engine Search**: Combines the power of the Gemini API (for generative chat) with a localized knowledge base fallback to handle quota limitations (such as `429 RESOURCE_EXHAUSTED` errors).
* **Smart Local Search**: Word-boundary aware search with TF-IDF style inverse frequency weighting to accurately match questions (e.g., distinguishing between "bus route" and "driver names").
* **Dynamic Transportation Lookup**: Retrieves detailed driver contacts, bus numbers, timings, and stops dynamically for all **12 official NNRG bus routes**.
* **Direct Faculty Contacts**: Instant directory details for HODs (CSE, AIML, DS, ECE, Civil, Mech, MBA), the Dean, and the Director of the college.
* **Canteen & Campus Store Guides**: Up-to-date canteen menu pricing, timings, and information about the adjacent 'READERS' stationery store.
* **Off-Domain Guardrail**: Safely intercepts and declines off-topic questions (e.g., general programming, recipes) with the customized message: `"I'm sorry. I can answer to nnrg related questions only."`

---

## 🛠️ Tech Stack

* **Backend**: Python, Flask, Flask-CORS
* **Frontend**: HTML5, Vanilla CSS3, JavaScript
* **AI Model**: Google Gemini API (`gemini-2.5-flash`)
* **Data Sources**: Pre-parsed Markdown documentation and JSON QA-pairs stored under `/knowledge_base`

---

## 📂 Project Structure

```text
├── knowledge_base/               # NNRG Institutional Database
│   ├── pdf_documents/            # Handbooks, summaries, and SSR files
│   ├── questions_answers.json    # Local Q&A pair index
│   └── *.md                      # Module-specific college data (Admissions, Canteen, etc.)
├── public/                       # Frontend assets
│   ├── index.html                # Web app interface
│   ├── app.js                    # Chat UI logic
│   └── style.css                 # Custom styles
├── app.py                        # Flask server, route matching, and Gemini client
├── .env.example                  # Environment variables template
├── requirements.txt              # Project dependencies
└── README.md                     # Project documentation
```

---

## 💻 Setup & Installation

### 1. Clone the Repository
```bash
git clone https://github.com/vujjiniramya7-byte/nnrg-campus-navigator.git
cd nnrg-campus-navigator
```

### 2. Set Up a Virtual Environment
```bash
python -m venv venv
# On Windows
venv\Scripts\activate
# On macOS/Linux
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Create a file named `.env` in the root directory and add your Gemini API Key:
```env
PORT=3000
GEMINI_API_KEY=your_gemini_api_key_here
```

### 5. Run the Server
```bash
python app.py
```
Open your browser and navigate to `http://127.0.0.1:3000`.

# SciCheck Agent 🧪🔍

**SciCheck Agent** is a lightweight AI-powered web app that helps users verify scientific claims they encounter online. With one click, it allows users to validate selected text from articles or posts using language models and academic research.

---

## 🚀 Features

- **Claim extraction** from selected web text  
- **Scientific claim verification** via OpenRouter AI models  
- **Evidence-based research** suggestions  
- **PDF report generation**  
- **CrossRef and CORE academic sources**  
- Clean mobile-first UI  
- PWA-ready (with manifest and service worker)

---

## 📦 Installation

1. **Clone the repository or unzip the files:**

```bash
git clone https://github.com/yourusername/scicheckagent.git
cd scicheckagent

2. Create a virtual environment and activate it:



python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

3. Install required packages:



pip install -r requirements.txt


---

▶️ Running the App

Run the Flask app locally:

python flask_app.py

The app will be available at http://localhost:5000


---

🧠 Tech Stack

Frontend: HTML5, Bootstrap/Tailwind (CSS inlined), PWA support

Backend: Python, Flask

AI Models: OpenRouter (e.g., Mistral-7B)

Data Sources: CrossRef, CORE, internal evidence mapping



---

📁 Project Structure

scicheckagent/
├── flask_app.py           # Flask backend logic
├── index.html             # Frontend UI
├── requirements.txt       # Dependencies
├── icon-*.png             # PWA icons
├── logo.png               # Site logo
├── manifest.json          # Web manifest
└── service-worker.js      # PWA offline support


---

📝 License

MIT License — add your license details here.


---

👥 Team

Alis Grave Nil
"We build the Future"


---

🌐 Live Demo (Optional)

https://scicheckagent.pythonanywhere.com — example deployment link

#  SAFESPHERE

SafeSphere is a statistically grounded, AI-powered disaster intelligence platform that predicts risk, detects anomalies, forecasts impact, prioritizes emergencies, and manages shelters and resources .


---


## Live Website:

<a href="https://edushala.vercel.a" target="_blank" >![Image](https://github.com/user-attachments/assets/00c0deb9-de02-4480-8058-c54dae53e2cc) edushala.vercel.app</a> OR <a href="https://www.edushala.th" target="_blank" >www.edushala.tech</a>

---

## Youtube Video:

<a href="https://youtu.be/_jCDPb56rGI?si=iBfP1QvtxJJlPeb_" target="_blank" >![Image](https://github.com/user-attachments/assets/f584d4b1-9605-4759-9748-f95a93a7ef5f) https://youtu.be/_jCDPb56rGI?si=iBfP1QvtxJJlPeb_</a>

---

## Developers:

- Matrika Regmi
- Ayaan 
- Qayad
- Nashra
- Alisha

---

## Tech Stack

##  **Tech Stack**

| **Category** | **Technologies** | **Purpose** |
|--------------|------------------|-------------|
| **Backend** | Flask 3.x, Jinja2 | REST API + Server-rendered templates |
| **Database** | MySQL, SQLite (fallback) | Users, Disasters, NGOs data |
| **Frontend** | HTML/CSS/JS, Leaflet.js | 7 mobile templates + interactive maps |
| **APIs** | Open-Meteo, IP-API, Overpass OSM, NDMA SACHET | Weather, GPS, NGOs, Live Alerts |
| **Analytics** | CountUp.js, Custom JS | Live stats + dashboards |
| **Styling** | Tailwind CSS (CDN), Custom CSS | Responsive + glassmorphism design |
| **Deployment** | Vercel/Netlify ready | Single-command live deploy |

### ** Python Dependencies (21 total)**

---

## Database Schema

Built on MySQL with the following core tables:

- regions — id, name, population, climate_factor
- disaster_history — region_id, year, frequency, severity, loss
- risk_predictions — risk_index, probability, std_dev, anomaly
- emergency_requests — priority, probability, status
- shelters — capacity, occupancy
- resources — quantity, threshold
- clusters — region_id, cluster_group
- users — role, credentials

---

## ✨ ** Features**:

- Online & offline SOS system with exact geolocation

- Real-time nearby disaster alerts

- Fetches live disaster data from authoritative sources

- Offline fallback mechanism for network disruptions

- Disaster analysis: severity, duration, and frequency

- Connects with NGOs and organizations for emergency aid

- Maintains data records of available aid and shelter capacity

- Manual disaster reporting by users

- Admin verification for reports and user authenticity

- Visual disaster analysis via interactive dashboards

- AI-powered hazard risk prediction

- AI-based impact estimation for potential disasters

- Live weather updates integrated with disaster risk
 
- priority classification for emergency services and aid allocation

### **📊 Data Export**
- Disaster analytics reports
- User + incident CSV exports

---

## Steps to run this project:

**Note:** Make sure you have installed Git, VS Code, and Node.js in your system

### 1. Clone the repository:

```bash
git clone https://github.com/your-username/safesphere.git
```

### 2. Open the cloned folder in VS Code

### 3. Install dependencies and run

```bash
cd backend
npm install
npm start
```

```bash
cd frontend
npm install
npm start
```

### 4. Access website at: http://localhost:3000

---

## Preview

Coming Soon

---

## License

Creative Commons BY-NC 4.0
# 🔎 AI Mystery Detective

> A 15-level mystery investigation and atmospheric horror game built with Python and Pygame.

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Pygame](https://img.shields.io/badge/Pygame-2.6+-00A86B?style=for-the-badge)](https://www.pygame.org/)
[![Tests](https://img.shields.io/badge/Tests-626%20passing-2EA44F?style=for-the-badge)](#testing)
[![Status](https://img.shields.io/badge/Status-Active%20Development-8A2BE2?style=for-the-badge)](https://github.com/KhushiTanwar1720/AI-Mystery-Detective-game)

---

## 🕵️ About the Project

**AI Mystery Detective** is a Python + Pygame detective mystery game built around a complete **15-level horror-tinged campaign**.

Players investigate cases by exploring locations, discovering evidence and clues, examining suspects, conducting interrogations, consulting an AI analyzer, and making a final accusation.

The campaign is designed as a connected progression: early cases introduce detective mechanics and atmosphere, while later cases become increasingly intense and connect earlier mysteries into a larger campaign throughline.

### What makes the project interesting

- 🎮 Complete 15-level playable campaign
- 🔎 Evidence-driven detective gameplay
- 🧩 Clues with deliberate red herrings
- 🕵️ Unique suspects, motives, and alibis
- 💬 Suspect interrogation
- 🤖 Deterministic AI-assisted analysis
- 🎯 Scoring and detective ranking
- 🏆 Achievement system
- 📍 Multiple connected locations per case
- 💾 Persistent save/load progression
- 🌑 Progressive horror atmosphere
- 🧱 UI-independent modular backend
- 🧪 626 automated tests

---

## ✨ Key Features

### 🔎 Investigation System

Explore case locations and investigate the environment to uncover information needed to solve each mystery.

The investigation system tracks discoveries and connects locations with available evidence and clues.

### 🧾 Evidence & Clue System

Each case contains physical, documentary, or digital evidence together with deducible clues and intentional red herrings.

The player must interpret the information rather than simply receiving the answer.

### 🕵️ Suspects & Interrogation

Every case contains named suspects with their own information, motives, and alibis.

Players can investigate suspects and conduct interrogations before making the final accusation.

### 🤖 AI Analyzer

The AI Analyzer works over **actually discovered evidence, clues, and suspect statements** to surface contradictions and useful hints.

It does **not** simply reveal the correct suspect.

> Runtime AI/LLM APIs are not required; the analyzer is a deterministic reasoning module over structured case data.

### 🎯 Scoring & Ranking

Investigation performance is converted into a score and detective rank, making accuracy and investigation quality part of the gameplay.

### 🏆 Achievements

The project includes achievements such as:

- First Case
- Evidence Hunter
- Clue Collector
- Master Investigator
- No-Hint Detective
- Speed Detective
- Perfect Investigation
- Master Detective

### 💾 Save & Load

Save data covers:

- Current case and level
- Visited locations
- Discovered evidence and clues
- Interrogation history
- Score
- Achievements
- Campaign progression

Older single-slot saves remain loadable across the added campaign content.

### 📍 Location System

Locations support:

- Visiting and leaving
- Connected locations
- Available evidence
- Available clues
- Persistent location state
- JSON-based loading

### 🌑 Progressive Horror Atmosphere

Every campaign level has a data-driven **horror rating from 1–10**.

That rating drives visual atmosphere such as:

- Background darkness
- Fog
- Vignette
- Light flicker
- Location-specific rendering

The atmosphere becomes progressively more intense instead of relying on a single black theme.

---

## 🎮 Game Flow

```text
Main Menu
    ↓
Case Selection
    ↓
Investigation Dashboard
    ↓
Explore Locations
    ↓
Discover Evidence & Clues
    ↓
Investigate Suspects
    ↓
Interrogation
    ↓
AI Analysis
    ↓
Final Accusation
    ↓
Results
    ↓
Score & Rank
    ↓
Achievements
    ↓
Next Case / Level
```

---

# 📚 15-Level Campaign

Every level contains a real, solvable mystery with its own setting, suspects, evidence, clues, and locations.

| # | Title | Setting | Horror | Difficulty |
|---:|---|---|:---:|:---:|
| 1 | **The Missing Necklace** | Blackwood Mansion | 1/10 | Easy |
| 2 | **Whispers in the Old Hotel** | Grand Meridian Hotel | 2/10 | Easy |
| 3 | **The Empty School** | Roosevelt Middle School | 3/10 | Easy |
| 4 | **Footsteps in the Forest** | Whitmore National Forest | 4/10 | Medium |
| 5 | **The House at the End of the Road** | The Calder House | 5/10 | Medium |
| 6 | **The Silent Hospital** | St. Agnes Hospital | 6/10 | Medium |
| 7 | **The Forgotten Asylum** | Blackgate Asylum | 7/10 | Hard |
| 8 | **The Underground Station** | Millbrook Station | 7/10 | Hard |
| 9 | **The Village That Sleeps** | Hollow Fen Village | 8/10 | Hard |
| 10 | **The Lighthouse** | Cormorant Point Lighthouse | 8/10 | Hard |
| 11 | **The Manor Beneath the Fog** | Thorncastle Manor | 8.5/10 | Hard |
| 12 | **The Frozen Research Facility** | Kestrel Research Facility | 9/10 | Hard |
| 13 | **The Town Beneath the Lake** | The Sunken Town of Merrow | 9/10 | Hard |
| 14 | **The Blackwood Underground** | Beneath Blackwood Mansion | 9.5/10 | Hard |
| 15 | **THE FINAL CASE** | The Architect's Chamber | 10/10 | Hard / Final |

### Campaign Progression

Levels unlock sequentially as cases are solved.

The campaign progression is derived from existing backend state rather than introducing a separate duplicate progression system.

Levels 14 and 15 connect earlier cases into a broader campaign-spanning throughline.

---

# 🖥️ Game Interface

The Pygame interface covers the complete investigation flow:

| Screen | Purpose |
|---|---|
| 🏠 **Main Menu** | Start, continue, and navigate the game |
| 📁 **Case Selection** | Select and progress through the 15 cases |
| 🧭 **Investigation Dashboard** | Track the current investigation |
| 📍 **Location Exploration** | Explore connected case locations |
| 🧾 **Evidence** | Review discovered evidence |
| 🧩 **Clue Board** | Review and organize clues |
| 🕵️ **Suspects** | Investigate suspect profiles |
| 💬 **Interrogation** | Question suspects |
| 🤖 **AI Analyzer** | Analyze discovered information |
| ⚖️ **Final Accusation** | Make the final decision |
| 🏆 **Results** | Review case outcome and performance |
| 🎖️ **Achievements** | Track unlocked achievements |
| 👤 **Detective Profile** | View detective progression |
| 💾 **Save / Load** | Manage saved investigations |
| ⚙️ **Settings** | Configure the game |

---

# 🌍 Environment & Horror Progression

The visual system uses a shared, data-driven palette rather than creating a separate hardcoded UI for every level.

Different settings have their own environmental identity, including themes such as:

- 🏛️ Mansion interiors
- 🏨 Hotels
- 🏫 Schools
- 🌲 Forests
- 🏚️ Isolated houses
- 🏥 Hospitals
- 🏚️ Asylums
- 🚇 Underground stations
- 🌫️ Villages
- 🗼 Lighthouses
- 🏰 Fog-covered manors
- 🧪 Research facilities
- 🌊 Sunken locations
- ⬛ Underground Blackwood
- 🌑 The Architect's Chamber

The horror progression moves from subtle mystery toward an increasingly intense final case.

> The project uses atmospheric horror rather than graphic gore.

---

# 🧱 Architecture

The project follows a modular, object-oriented architecture with a UI-independent backend.

```text
                         GameController
                                │
             ┌──────────────────┼──────────────────┐
             │                  │                  │
             ▼                  ▼                  ▼
           Case              Player          Investigation
                                                   │
                                      ┌────────────┼────────────┐
                                      ▼            ▼            ▼
                                   Evidence       Clues      Suspects
                                                               │
                                                               ▼
                                                         Interrogation
                                                               │
                                                               ▼
                                                          AI Analyzer
                                                               │
                                                               ▼
                                                          ScoreManager
                                                               │
                                                               ▼
                                                          Final Result

Supporting Systems:
Location • GameState • SaveManager • AchievementManager
```

### Backend modules

- `Case`
- `Player`
- `Suspect`
- `Evidence`
- `Clue`
- `Location`
- `Investigation`
- `Interrogation`
- `AIAnalyzer`
- `ScoreManager`
- `GameState`
- `SaveManager`
- `AchievementManager`
- `GameController`

The UI remains a thin Pygame layer over the shared `GameController` and uses public game APIs for actions such as loading cases, exploring locations, discovering evidence, asking questions, running analysis, concluding cases, and saving/loading.

---

# 🗂️ Project Structure

```text
AI-Mystery-Detective/
│
├── main.py                     # CLI entry point
├── play.py                     # Pygame entry point
├── requirements.txt
│
├── data/
│   └── campaign.json           # 15-level campaign manifest
│
├── cases/
│   ├── case_001.json ...       # Case definitions
│   ├── suspects/               # Suspect data
│   ├── evidence/               # Evidence data
│   ├── clues/                  # Clue data
│   └── locations/              # Location data
│
├── game/                       # UI-independent backend
│
├── ui/
│   ├── app.py                  # Pygame application
│   ├── theme.py                # Theme & horror-tier styling
│   ├── campaign.py             # Campaign resolver
│   ├── state_manager.py        # Screen navigation
│   ├── components/             # Reusable UI components
│   └── screens/                # Game screens
│
├── ai/                         # AI-related expansion area
├── database/                   # Database expansion area
├── assets/                     # Optional assets/placeholders
├── tools/                      # Campaign authoring/validation tools
└── tests/                      # Automated tests
```

---

# 🛠️ Tech Stack

| Technology | Purpose |
|---|---|
| **Python 3.10+** | Core programming language |
| **Pygame 2.6+** | Graphical game interface |
| **JSON** | Case and campaign data |
| **OOP** | Modular game architecture |
| **Unittest / Pytest** | Automated testing |
| **Procedural Rendering** | Environment and atmosphere |
| **Git & GitHub** | Version control |

### Runtime AI

The current **AI Analyzer does not require an external AI/LLM API at runtime**.

It is implemented as a deterministic reasoning module over structured case data.

---

# 🚀 Installation & Setup

## Prerequisites

- Python 3.10+
- Git
- Windows, macOS, or Linux

## 1. Clone the repository

```bash
git clone https://github.com/KhushiTanwar1720/AI-Mystery-Detective-game.git
cd AI-Mystery-Detective-game
```

## 2. Create a virtual environment

### Windows

```powershell
python -m venv venv
.env\Scripts\Activate.ps1
```

### macOS / Linux

```bash
python3 -m venv venv
source venv/bin/activate
```

## 3. Install dependencies

```bash
python -m pip install -r requirements.txt
```

Pygame is the only third-party runtime dependency listed by the project.

## 4. Launch the graphical game

```bash
python play.py
```

## 5. Run the backend CLI

```bash
python main.py
```

The CLI allows the backend/game systems to be exercised without launching the graphical interface.

---

# 🧪 Testing

The project currently contains **626 automated tests** covering backend systems, campaign resolution, UI-related pygame-free logic, and campaign-content validation.

Run with:

```bash
python -m pytest
```

Or, without pytest:

```bash
python -m unittest discover -s tests
```

### Campaign validation

The project also contains content-authoring/validation tools:

```bash
python tools/generate_cases.py
python tools/validate_cases.py
```

The validation workflow loads and exercises the campaign content across all 15 levels.

---

# 💾 Save / Load

The save system preserves important investigation state, including:

- Current case
- Current level
- Visited locations
- Discovered evidence
- Discovered clues
- Interrogation history
- Score
- Achievements
- Campaign progression

The system also maintains compatibility with older single-slot save data.

---

# 🔐 Design Principles

### Separation of Concerns
Gameplay logic is kept outside the UI layer.

### Object-Oriented Design
Core systems are represented through dedicated classes and managers.

### Data-Driven Content
Campaign and case content are stored in structured data rather than being hardcoded into individual screens.

### Extensibility
New cases, suspects, evidence, clues, locations, and achievements can be added without rebuilding the entire game.

### Testability
Core systems have automated tests and campaign-level validation.

### Persistent Progression
Game state, investigation progress, scoring, achievements, and campaign progression are integrated with save/load.

---

# 🎯 What the Player Actually Does

A successful investigation requires the player to:

1. Select a case
2. Explore locations
3. Discover evidence
4. Find clues
5. Investigate suspects
6. Interrogate suspects
7. Analyze discovered information
8. Identify contradictions and useful connections
9. Determine the most likely suspect
10. Make a final accusation
11. Receive a score and rank
12. Unlock achievements
13. Progress to the next case

The game is designed so that the player must **investigate and reason**, rather than simply selecting an answer from a predetermined quiz.

---

# 🔮 Future Improvements

Planned or possible improvements include:

- 🎨 Replace procedural location art with richer illustrated backgrounds
- 🧑‍🎨 Add character portraits and visual storytelling
- 🎵 Add music and ambient sound per horror tier
- 💾 Surface multiple save slots directly in the UI
- 🤖 Expand optional AI Analyzer hint/difficulty mechanics
- 🌫️ Further atmospheric animation and environmental effects
- 🧩 Expand the campaign with additional cases
- 🎮 Continue gameplay and UI polish

---

# 👩‍💻 Author

## Khushi Tanwar

**B.Tech Computer Science Engineering Student**

**Interests:**  
`Python` • `Java` • `Web Development` • `Game Development` • `AI`

GitHub: [KhushiTanwar1720](https://github.com/KhushiTanwar1720)

---

# 📌 Project Status

**AI Mystery Detective** is an active major project developed with Python and Pygame.

It combines:

**Software Engineering + OOP + Game Development + Investigation Mechanics + UI Design + Procedural Rendering + Persistence + Automated Testing**

into one complete application.

---

## ⭐ Support

If you find the project interesting, consider giving the repository a ⭐ on GitHub.

> **Every clue matters. Every suspect has a story. Make the right accusation.**

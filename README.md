# Micc

## Prerequisites

- `uv` (Python package manager)

## First Time Setup

1. Clone the repository:
```
git clone <repository url>
```

2. Install dependencies:
```
cd micc
uv sync
```

## Running the Application

1. First terminal
```
uv run uvicorn backend.main:app --reload --port 8000
```

2. Second terminal
```
uv run streamlit run frontend/app.py --server.port 8501
```

And then visit `http://localhost:8501` in your browser to view the app.

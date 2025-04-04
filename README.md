# Deep Research Assistant

A Python application that connects to Ollama to perform deep research on any topic using internet sources and user context. The assistant generates comprehensive research reports with AI-powered analysis and can export them as downloadable PDF files.

## Features

- Connects to Ollama for LLM capabilities
- Performs parallel internet research on any topic
- Searches multiple engines (Google, DuckDuckGo, Tavily)
- Interacts with users to gather context and refine research
- Generates comprehensive research reports
- Exports reports as downloadable PDF files
- Provides both CLI and web interfaces

## Requirements

- Python 3.8 or higher
- Ollama installed and running (locally or on a remote server)
- Internet connection

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd deep-research-new

# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On Unix/macOS:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Configuration

The application can be configured using environment variables or a `.env` file in the project root:

```
# Ollama API settings
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama2

# Research settings
MAX_PARALLEL_SEARCHES=5
MAX_SOURCES_PER_TOPIC=10
SEARCH_TIMEOUT=30

# PDF generation settings
PDF_AUTHOR="Deep Research Assistant"
PDF_TITLE_PREFIX="Research Report: "
PDF_OUTPUT_DIR=reports
```

## Usage

### Command Line Interface

To start the application with the command line interface:

```bash
python main.py
```

Follow the interactive prompts to enter your research topic and any additional context.

### Web Interface

To start the application with the web interface:

```bash
python main.py --web
```

By default, the web server runs on `http://localhost:5000`. You can specify a different port:

```bash
python main.py --web --port 8080
```

Access the web interface by opening the URL in your browser. From there, you can:

1. Enter a research topic
2. Provide additional context (optional)
3. Monitor research progress in real-time
4. View and download the generated research report as a PDF

## Project Structure

```
.
├── README.md
├── main.py                  # Entry point for the application
├── requirements.txt         # Project dependencies
├── config.py                # Configuration settings
├── research/                # Research module
│   ├── __init__.py
│   ├── engine.py            # Core research functionality
│   ├── web_search.py        # Web search and scraping utilities
│   └── ollama_client.py     # Ollama API integration
├── utils/                   # Utility functions
│   ├── __init__.py
│   ├── pdf_generator.py     # PDF report generation
│   └── text_processor.py    # Text processing utilities
└── ui/                      # User interface
    ├── __init__.py
    ├── cli.py               # Command-line interface
    ├── web.py               # Web interface initialization
    └── web/                 # Web interface components
        ├── __init__.py
        ├── app.py           # Flask application
        ├── static/          # Static assets (CSS, JS, images)
        ├── templates/       # HTML templates
        └── uploads/         # User uploaded files
```

## License

MIT
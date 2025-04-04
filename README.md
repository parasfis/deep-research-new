# Deep Research Assistant

A Python application that connects to Ollama to perform deep research on any topic using internet sources and user context. The assistant generates comprehensive research reports with AI-powered analysis and can export them as downloadable PDF files.

## Features

- Connects to Ollama for LLM capabilities (supports llama3.2)
- Performs parallel internet research on any topic
- Searches multiple engines (Google, DuckDuckGo, Tavily, SearX)
- Interacts with users to gather context and refine research
- Generates comprehensive research reports
- Exports reports as downloadable PDF files
- Provides both CLI and web interfaces
- Real-time progress tracking with accurate progress bar
- Markdown formatting in reports with clickable links
- Error handling and detailed error reporting

## Requirements

- Python 3.11 or higher
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
OLLAMA_MODEL=llama3.2
OLLAMA_TIMEOUT=240

# Search engine API keys
TAVILY_API_KEY=your_tavily_api_key_here
SERPAPI_KEY=your_serpapi_key_here
SEARX_INSTANCE=https://searx.thegpm.org

# Research settings
MAX_PARALLEL_SEARCHES=4
MAX_SOURCES_PER_TOPIC=10
SEARCH_TIMEOUT=30
MAX_RESULTS_PER_ENGINE=10

# PDF generation settings
PDF_AUTHOR="Deep Research Assistant"
PDF_TITLE_PREFIX="Deep Research Report: "
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

## Recent Improvements

- **Enhanced Web Interface**: Improved research status tracking with accurate progress indicator
- **Better Error Handling**: Detailed error messages and recovery mechanisms for better user experience
- **PDF Improvements**: Fixed PDF generation and download, with proper markdown rendering
- **Markdown Support**: Proper rendering of markdown content in web reports with clickable links
- **Performance Enhancements**: Optimized search engine utilization and concurrent research execution
- **Mobile Responsiveness**: Better display on mobile devices and tablets
- **UI Enhancements**: Cleaner report layout with better typography and spacing

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
    ├── web_interface.py     # Web interface initialization
    └── web/                 # Web interface components
        ├── __init__.py
        ├── app.py           # Flask application
        ├── static/          # Static assets (CSS, JS, images)
        │   ├── css/         # Stylesheets
        │   └── js/          # JavaScript files
        ├── templates/       # HTML templates
        └── uploads/         # User uploaded files
```

## Troubleshooting

### Common Issues

- **PDF Download Issues**: If you encounter PDF download problems, ensure the `reports` directory exists and has write permissions.
- **Connection Errors**: Check that Ollama is running and accessible at the configured host/port.
- **Search Engine Errors**: Some search engines may require API keys or have usage limits. Configure fallback options in `config.py`.

### Search Engine Configuration

The application supports multiple search engines:

- **Tavily**: Requires an API key from [tavily.com](https://tavily.com). Set the `TAVILY_API_KEY` environment variable.
- **SerpAPI (Google)**: Requires an API key from [serpapi.com](https://serpapi.com). Set the `SERPAPI_KEY` environment variable.
- **DuckDuckGo**: No API key required, but may have usage limitations.
- **SearX**: Uses public or private SearX instances. Set the `SEARX_INSTANCE` environment variable to use a custom instance.

The search engines are tried in the order specified in `config.py`. If a search engine fails or returns no results, the system falls back to the next engine in the list.

### Debug Mode

Run the application in debug mode for more detailed logs:

```bash
python main.py --web --debug
```
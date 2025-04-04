"""Flask web application for Deep Research Assistant.

This module provides a web interface for interacting with the research engine.
"""

import os
import time
import logging
from typing import Dict, Any, Optional
from pathlib import Path
from threading import Thread
import datetime  # Add this import
import re  # Add this import for markdown conversion

from flask import Flask, render_template, request, jsonify, send_from_directory, session, redirect, url_for, send_file
from werkzeug.utils import secure_filename

from research.engine import ResearchEngine
from utils.pdf_generator import PDFGenerator
import config

logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.urandom(24)  # for session management
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size

# Add the now() function to the Jinja2 environment
@app.context_processor
def inject_now():
    return {'now': datetime.datetime.now}

# Add markdown filter for Jinja templates
@app.template_filter('markdown')
def markdown_filter(text):
    """Convert markdown to HTML for templates."""
    if not text:
        return ''
    
    # Convert headers
    text = re.sub(r'^### (.+)$', r'<h3>\1</h3>', text, flags=re.MULTILINE)
    text = re.sub(r'^## (.+)$', r'<h2>\1</h2>', text, flags=re.MULTILINE)
    text = re.sub(r'^# (.+)$', r'<h1>\1</h1>', text, flags=re.MULTILINE)
    
    # Convert bold and italic
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
    
    # Convert links [text](url)
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" target="_blank">\1</a>', text)
    
    # Convert lists
    text = re.sub(r'^\* (.+)$', r'<li>\1</li>', text, flags=re.MULTILINE)
    text = re.sub(r'^\d+\. (.+)$', r'<li>\1</li>', text, flags=re.MULTILINE)
    
    # Group list items
    def replace_list_items(match):
        return '<ul>' + match.group(0) + '</ul>'
    
    text = re.sub(r'(<li>.+?</li>(\n|$))+', replace_list_items, text, flags=re.DOTALL)
    
    # Convert paragraphs (lines that don't start with HTML tags)
    text = re.sub(r'^(?!<[a-z]).+$', r'<p>\g<0></p>', text, flags=re.MULTILINE)
    
    # Convert line breaks to <br>
    text = re.sub(r'\n\n', r'<br>', text)
    
    return text

# Error handling middleware
@app.errorhandler(500)
def internal_error(error):
    logger.exception(f"Internal Server Error: {error}")
    return render_template('error.html', 
                         message="Internal Server Error - The application encountered an unexpected condition"), 500

@app.errorhandler(404)
def not_found_error(error):
    return render_template('error.html', 
                         message="Page Not Found - The requested URL was not found"), 404

@app.errorhandler(400)
def bad_request_error(error):
    return render_template('error.html', 
                         message="Bad Request - The server cannot process the request"), 400

# Ensure the reports and uploads directories exist
Path(config.PDF_OUTPUT_DIR).mkdir(exist_ok=True)
Path(app.config['UPLOAD_FOLDER']).mkdir(exist_ok=True)

# Initialize research engine and PDF generator
research_engine = None  # This will be set by web_interface.py
pdf_generator = PDFGenerator()

# Store active research tasks
active_research_tasks = {}


class ResearchTask:
    """Class to manage a research task in a separate thread."""
    
    def __init__(self, topic: str, context: Optional[str] = None):
        """Initialize the research task.
        
        Args:
            topic: The research topic.
            context: Additional context for the research.
        """
        self.topic = topic
        self.context = context
        self.status = "initializing"
        self.progress = 0
        self.result = None
        self.start_time = time.time()
        self.end_time = None
        self.thread = Thread(target=self._execute_research)
        self.thread.daemon = True
    
    def start(self):
        """Start the research task."""
        self.thread.start()
    
    def _execute_research(self):
        """Execute the research task."""
        try:
            if research_engine is None:
                logger.error("Research engine not initialized")
                self.status = "error"
                self.result = {"error": "Research engine not initialized"}
                self.end_time = time.time()
                return
                
            logger.info(f"Starting research planning for topic: {self.topic}")
            self.status = "planning"
            
            try:
                # Start research planning
                research_plan = research_engine.start_research(self.topic, self.context)
                logger.info(f"Research plan generated for topic: {self.topic}")
            except Exception as plan_error:
                logger.exception(f"Error in research planning: {plan_error}")
                self.status = "error"
                self.result = {"error": f"Error in research planning: {str(plan_error)}"}
                self.end_time = time.time()
                return
            
            logger.info(f"Starting research execution for topic: {self.topic}")
            self.status = "researching"
            
            try:
                # Execute research
                self.result = research_engine.execute_research(self.topic, self.context)
                logger.info(f"Research completed for topic: {self.topic}")
            except Exception as research_error:
                logger.exception(f"Error in research execution: {research_error}")
                self.status = "error"
                self.result = {"error": f"Error in research execution: {str(research_error)}"}
                self.end_time = time.time()
                return
            
            self.status = "completed"
            self.progress = 100
            self.end_time = time.time()
            logger.info(f"Research task completed for topic: {self.topic}")
        except Exception as e:
            logger.exception(f"Unexpected error in research task: {e}")
            self.status = "error"
            self.result = {"error": f"Unexpected error: {str(e)}"}
            self.end_time = time.time()
    
    def get_status(self) -> Dict[str, Any]:
        """Get the status of the research task.
        
        Returns:
            Dictionary containing the status of the research task.
        """
        # Calculate progress based on status and time elapsed
        if self.status == "initializing":
            self.progress = 5
        elif self.status == "planning":
            # Planning phase: 0-20%
            elapsed = time.time() - self.start_time
            # Assume planning takes ~10 seconds
            planning_progress = min(20, int(elapsed / 10 * 20))
            self.progress = planning_progress
        elif self.status == "researching" and research_engine is not None:
            # Research phase: 20-90%
            elapsed_since_planning = time.time() - self.start_time
            if elapsed_since_planning < 15:  # Early research
                # Scale from 20-50% over first 15 seconds
                self.progress = 20 + min(30, int((elapsed_since_planning / 15) * 30))
            else:  # Later research
                # Scale from 50-90% for the remainder (assumes ~45 seconds total)
                remaining_time = max(0, 45 - elapsed_since_planning)
                progress_left = max(0, 40 - int((remaining_time / 30) * 40))
                self.progress = min(90, 50 + progress_left)
                
            # Check actual research engine status if available
            try:
                status = research_engine.get_research_status()
                if status.get("status") == "in_progress":
                    # If we have duration info, use it for better estimates
                    if "duration" in status:
                        # Research typically takes ~60 seconds total
                        expected_duration = 60
                        progress_percent = min(0.9, status["duration"] / expected_duration)
                        self.progress = int(20 + (progress_percent * 70))
            except Exception as e:
                logger.warning(f"Error getting research status: {e}")
        elif self.status == "completed":
            self.progress = 100
        elif self.status == "error":
            # Keep the last progress value, don't jump to 100%
            pass
        
        return {
            "topic": self.topic,
            "status": self.status,
            "progress": self.progress,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": (self.end_time or time.time()) - self.start_time
        }


@app.route('/')
def index():
    """Render the home page."""
    return render_template('index.html')


@app.route('/research', methods=['GET', 'POST'])
def research():
    """Handle research requests."""
    if request.method == 'POST':
        # Get research topic and context from form
        topic = request.form.get('topic')
        context = request.form.get('context')
        
        if not topic:
            return jsonify({"error": "Research topic is required"}), 400
        
        # Generate a unique task ID
        task_id = str(int(time.time()))
        
        # Create and start a new research task
        task = ResearchTask(topic, context)
        active_research_tasks[task_id] = task
        task.start()
        
        # Store task ID in session
        session['current_task_id'] = task_id
        
        return redirect(url_for('research_status', task_id=task_id))
    
    return render_template('research.html')


@app.route('/research/<task_id>')
def research_status(task_id):
    """Show the status of a research task."""
    task = active_research_tasks.get(task_id)
    if not task:
        return render_template('error.html', message="Research task not found"), 404
    
    return render_template('research_status.html', task_id=task_id)


@app.route('/api/research/<task_id>/status')
def api_research_status(task_id):
    """Get the status of a research task."""
    task = active_research_tasks.get(task_id)
    if not task:
        return jsonify({"error": "Research task not found"}), 404
    
    return jsonify(task.get_status())


@app.route('/api/research/<task_id>/result')
def api_research_result(task_id):
    """Get the result of a research task."""
    task = active_research_tasks.get(task_id)
    if not task:
        return jsonify({"error": "Research task not found"}), 404
    
    if task.status == "completed":
        return jsonify(task.result)
    elif task.status == "error":
        # Return error information
        return jsonify(task.result), 200  # Return 200 so the client can display the error
    else:
        return jsonify({"error": "Research task not completed"}), 400


@app.route('/research/<task_id>/report')
def research_report(task_id):
    """Show the research report."""
    task = active_research_tasks.get(task_id)
    if not task:
        return render_template('error.html', message="Research task not found"), 404
    
    if task.status != "completed":
        return redirect(url_for('research_status', task_id=task_id))
    
    return render_template('report.html', task_id=task_id, result=task.result)


@app.route('/research/<task_id>/pdf')
def generate_pdf(task_id):
    """Generate a PDF report for a research task."""
    logger.info(f"PDF generation requested for task: {task_id}")
    
    task = active_research_tasks.get(task_id)
    if not task:
        logger.error(f"Task not found: {task_id}")
        return render_template('error.html', message="Research task not found"), 404
    
    if task.status != "completed":
        logger.warning(f"Task not completed: {task_id}, status: {task.status}")
        return redirect(url_for('research_status', task_id=task_id))
    
    try:
        # Properly structure the research data for PDF generation
        # Avoid double nesting of 'results'
        research_data = {
            "topic": task.topic,
            "context": task.context,
            "results": {
                "report": task.result["results"]["report"],
                "analyzed_sources": task.result["results"]["analyzed_sources"]
            }
        }
        
        logger.info(f"PDF research data structure: {research_data.keys()}")
        logger.info(f"Results keys: {research_data['results'].keys()}")
        
        # Generate PDF report
        logger.info(f"Generating PDF for task: {task_id}")
        pdf_path = pdf_generator.generate_pdf(research_data)
        logger.info(f"PDF generated at path: {pdf_path}")
        
        # Get absolute directory and filename
        directory = os.path.abspath(os.path.dirname(pdf_path))
        filename = os.path.basename(pdf_path)
        logger.info(f"Serving PDF from directory: {directory}, filename: {filename}")
        
        # Ensure directory exists and is accessible
        if not os.path.exists(directory):
            logger.error(f"PDF directory does not exist: {directory}")
            return render_template('error.html', message="PDF directory not found"), 500
            
        # Ensure file exists
        full_path = os.path.join(directory, filename)
        if not os.path.exists(full_path):
            logger.error(f"PDF file does not exist: {full_path}")
            return render_template('error.html', message="PDF file not found"), 500
            
        # Use send_file instead of send_from_directory for absolute paths
        return send_file(full_path, as_attachment=True, download_name=filename)
    except Exception as e:
        logger.exception(f"Error generating PDF for task {task_id}: {e}")
        return render_template('error.html', message=f"Error generating PDF: {str(e)}"), 500


@app.route('/about')
def about():
    """Show the about page."""
    return render_template('about.html')


def start_web_server(host='0.0.0.0', port=5000, debug=False):
    """Start the Flask web server.
    
    Args:
        host: Host to bind the server to.
        port: Port to bind the server to.
        debug: Whether to run the server in debug mode.
    """
    # This function is now deprecated - app.run() is called directly from web_interface.py
    pass


if __name__ == '__main__':
    # For direct testing from app.py
    research_engine = ResearchEngine()
    app.run(debug=True)
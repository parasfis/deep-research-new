"""Flask web application for Deep Research Assistant.

This module provides a web interface for interacting with the research engine.
"""

import os
import time
import logging
from typing import Dict, Any, Optional
from pathlib import Path
from threading import Thread

from flask import Flask, render_template, request, jsonify, send_from_directory, session, redirect, url_for
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
research_engine = ResearchEngine()
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
            self.status = "planning"
            # Start research planning
            research_plan = research_engine.start_research(self.topic, self.context)
            
            self.status = "researching"
            # Execute research
            self.result = research_engine.execute_research(self.topic, self.context)
            
            self.status = "completed"
            self.progress = 100
            self.end_time = time.time()
        except Exception as e:
            logger.exception(f"Error in research task: {e}")
            self.status = "error"
            self.result = {"error": str(e)}
            self.end_time = time.time()
    
    def get_status(self) -> Dict[str, Any]:
        """Get the status of the research task.
        
        Returns:
            Dictionary containing the status of the research task.
        """
        if self.status == "researching":
            # Update progress based on research engine status
            status = research_engine.get_research_status()
            if status.get("status") == "in_progress":
                # Estimate progress based on time elapsed
                elapsed = time.time() - self.start_time
                # Rough estimate: 10% for planning, 80% for research, 10% for report generation
                if elapsed < 5:  # First 5 seconds for planning
                    self.progress = min(10, int(elapsed / 5 * 10))
                else:  # Rest for research and report generation
                    remaining_progress = 90
                    estimated_research_time = 30  # seconds
                    research_progress = min(remaining_progress, 
                                          int((elapsed - 5) / estimated_research_time * remaining_progress))
                    self.progress = 10 + research_progress
        
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
    
    if task.status != "completed":
        return jsonify({"error": "Research task not completed"}), 400
    
    return jsonify(task.result)


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
    task = active_research_tasks.get(task_id)
    if not task:
        return render_template('error.html', message="Research task not found"), 404
    
    if task.status != "completed":
        return redirect(url_for('research_status', task_id=task_id))
    
    # Generate PDF report
    pdf_path = pdf_generator.generate_pdf(task.result)
    
    # Send the PDF file
    directory = os.path.dirname(pdf_path)
    filename = os.path.basename(pdf_path)
    return send_from_directory(directory, filename, as_attachment=True)


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
    app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    start_web_server(debug=True)
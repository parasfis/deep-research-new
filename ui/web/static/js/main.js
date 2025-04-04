/* Deep Research Assistant - Main JavaScript */

// Format timestamps to readable format
function formatTimestamp(timestamp) {
    if (!timestamp) return 'N/A';
    const date = new Date(timestamp * 1000);
    return date.toLocaleString();
}

// Format duration in seconds to readable format
function formatDuration(seconds) {
    if (!seconds) return '0s';
    
    if (seconds < 60) {
        return Math.floor(seconds) + 's';
    } else if (seconds < 3600) {
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = Math.floor(seconds % 60);
        return `${minutes}m ${remainingSeconds}s`;
    } else {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        return `${hours}h ${minutes}m`;
    }
}

// Convert markdown to HTML (simple implementation)
function markdownToHtml(markdown) {
    if (!markdown) return '';
    
    // Replace headers
    let html = markdown
        .replace(/^### (.+)$/gm, '<h3>$1</h3>')
        .replace(/^## (.+)$/gm, '<h2>$1</h2>')
        .replace(/^# (.+)$/gm, '<h1>$1</h1>');
    
    // Replace bold and italic
    html = html
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.+?)\*/g, '<em>$1</em>');
    
    // Replace lists
    html = html
        .replace(/^\* (.+)$/gm, '<li>$1</li>')
        .replace(/^\d+\. (.+)$/gm, '<li>$1</li>');
    
    // Wrap lists
    html = html
        .replace(/(<li>.+<\/li>\n)+/g, function(match) {
            return '<ul>' + match + '</ul>';
        });
    
    // Replace paragraphs
    html = html
        .replace(/^(?!<[hou]).+$/gm, function(match) {
            return '<p>' + match + '</p>';
        });
    
    return html;
}

// Initialize tooltips and popovers if Bootstrap is available
document.addEventListener('DOMContentLoaded', function() {
    // Check if Bootstrap's tooltip functionality exists
    if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function(tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }
    
    // Check if Bootstrap's popover functionality exists
    if (typeof bootstrap !== 'undefined' && bootstrap.Popover) {
        const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
        popoverTriggerList.map(function(popoverTriggerEl) {
            return new bootstrap.Popover(popoverTriggerEl);
        });
    }
    
    // Convert any markdown content to HTML
    const markdownElements = document.querySelectorAll('.markdown-content');
    markdownElements.forEach(function(element) {
        const markdown = element.textContent;
        element.innerHTML = markdownToHtml(markdown);
    });
});
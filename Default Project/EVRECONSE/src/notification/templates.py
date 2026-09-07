"""
EVRECONSE Notification - Templates.

Message templates for different notification types.
"""

from __future__ import annotations

from typing import Any


class TemplateEngine:
    """
    Simple template engine for rendering notification templates.
    
    Supports basic variable substitution with {{variable}} syntax.
    """
    
    def __init__(self, template_dir: str | None = None) -> None:
        self._templates: dict[str, str] = {}
        if template_dir:
            self._load_templates(template_dir)
    
    def _load_templates(self, template_dir: str) -> None:
        """Load templates from directory."""
        import os
        for filename in os.listdir(template_dir):
            if filename.endswith(('.txt', '.md', '.html', '.j2')):
                key = filename.rsplit('.', 1)[0]
                with open(os.path.join(template_dir, filename), 'r', encoding='utf-8') as f:
                    self._templates[key] = f.read()
    
    def add_template(self, name: str, content: str) -> None:
        """Add or override a template."""
        self._templates[name] = content
    
    def remove_template(self, name: str) -> bool:
        """Remove a template."""
        if name in self._templates:
            del self._templates[name]
            return True
        return False
    
    def render(self, template_name: str, context: dict[str, Any]) -> str:
        """
        Render a template with the given context.
        
        Args:
            template_name: Name of template to render
            context: Dictionary of variables to substitute
            
        Returns:
            Rendered template string
            
        Raises:
            TemplateError: If template not found or rendering fails
        """
        from .exceptions import TemplateError
        
        template = self._templates.get(template_name)
        if template is None:
            raise TemplateError(f"Template not found: {template_name}", template_name=template_name)
        
        return self._render_template(template, context)
    
    def render_string(self, template: str, context: dict[str, Any]) -> str:
        """Render a template string directly."""
        return self._render_template(template, context)
    
    def _render_template(self, template: str, context: dict[str, Any]) -> str:
        """Render template with context variables."""
        import re
        
        def replace_var(match):
            key = match.group(1).strip()
            if key in context:
                value = context[key]
                if value is None:
                    return ""
                return str(value)
            return match.group(0)  # Keep placeholder if not found
        
        # Replace {{variable}} patterns
        pattern = r'\{\{\s*(\w+)\s*\}\}'
        result = re.sub(pattern, replace_var, template)
        return result
    
    def has_template(self, name: str) -> bool:
        """Check if template exists."""
        return name in self._templates
    
    def list_templates(self) -> list[str]:
        """List all available template names."""
        return list(self._templates.keys())


# Pre-built templates for common notification types
DEFAULT_TEMPLATES = {
    "trade_signal": """🚀 *Trade Signal: {{symbol}}*

📊 *Signal*: {{signal_type}}
💰 *Price*: {{price}}
📈 *Timeframe*: {{timeframe}}
🎯 *Confidence*: {{confidence}}%
⏰ *Time*: {{timestamp}}

{{#if strategy}}
📋 *Strategy*: {{strategy}}
{{/if}}

{{#if explanation}}
📝 *Reason*: {{explanation}}
{{/if}}""",
    
    "trade_closed": """
{{#if profit > 0}}
✅ *Position Closed - Profit*
{{else}}
❌ *Position Closed - Loss*
{{/if}}

📊 *Symbol*: {{symbol}}
💰 *Entry*: {{entry_price}}
💰 *Exit*: {{exit_price}}
💰 *PnL*: {{pnl}} ({{pnl_pct}}%)
⏰ *Duration*: {{duration}}""",
    
    "risk_alert": """⚠️ *Risk Alert*

🔔 *Type*: {{alert_type}}
📊 *Symbol*: {{symbol}}
💰 *Current Risk*: {{current_risk}}%
⚠️ *Threshold*: {{threshold}}%
📝 *Details*: {{details}}
⏰ *Time*: {{timestamp}}""",
    
    "system_alert": """🔔 *System Alert*

{{#if severity == 'critical'}}
🔴 *CRITICAL*
{{elif severity == 'warning'}}
🟡 *WARNING*
{{else}}
🔵 *INFO*
{{/if}}

*Component*: {{component}}
*Message*: {{message}}
⏰ *Time*: {{timestamp}}

{{#if details}}
*Details*: {{details}}
{{/if}}""",
    
    "error_notification": """❌ *Error*

*Component*: {{component}}
*Error*: {{error_type}}: {{message}}
*Severity*: {{severity}}
⏰ *Time*: {{timestamp}}

{{#if traceback}}
*Traceback*:
{{traceback}}
{{/if}}""",
    
    "daily_summary": """📊 *Daily Summary - {{date}}*

📈 *Total Signals*: {{total_signals}}
✅ *Qualified*: {{qualified}}
❌ *Rejected*: {{rejected}}
💰 *Total PnL*: {{total_pnl}}
📊 *Win Rate*: {{win_rate}}%

*Top Performers*:
{{#each top_symbols}}
  • {{symbol}}: {{pnl}} ({{win_rate}}%)
{{/if}}""",
    
    "heartbeat": """💚 *Heartbeat*

*Service*: {{service}}
*Status*: {{status}}
*Uptime*: {{uptime}}
*Messages Processed*: {{messages_processed}}
⏰ *Time*: {{timestamp}}""",
    
    "startup": """🚀 *Service Started*

*Service*: {{service}}
*Version*: {{version}}
*Environment*: {{environment}}
*Config*: {{config_summary}}
⏰ *Time*: {{timestamp}}""",
    
    "shutdown": """🛑 *Service Shutdown*

*Service*: {{service}}
*Reason*: {{reason}}
*Uptime*: {{uptime}}
*Messages Processed*: {{messages_processed}}
⏰ *Time*: {{timestamp}}""",
}


def get_default_template(name: str) -> str:
    """Get a default template by name."""
    return DEFAULT_TEMPLATES.get(name, "")


def get_all_template_names() -> list[str]:
    """Get list of all available template names."""
    return list(DEFAULT_TEMPLATES.keys())
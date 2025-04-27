import os
import json
from datetime import datetime
from typing import Dict, Any, List, Optional

from src.models.test_result import TestSuiteResult
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ReportGenerator:
    """Generates test reports from test results."""
    
    def __init__(self, output_dir: str = "reports", ai_client=None):
        self.output_dir = output_dir
        self.ai_client = ai_client
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
    
    def generate_report(self, test_suite_result: TestSuiteResult) -> Dict[str, Any]:
        """
        Generate a report from test results
        
        Args:
            test_suite_result: The test suite result to generate a report from
            
        Returns:
            Dictionary containing the report data
        """
        logger.info(f"Generating report for test suite: {test_suite_result.name}")
        
        # Basic empty report structure
        report = {
            "name": test_suite_result.name,
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_tests": 0,
                "success_count": 0,
                "failure_count": 0,
                "error_count": 0,
                "skipped_count": 0,
                "success_rate": 0
            },
            "results_by_endpoint": {},
            "insights": [],
            "recommendations": []
        }
        
        # Save report to file
        report_path = os.path.join(self.output_dir, f"api_test_report_{self._get_timestamp()}.json")
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Report saved to {report_path}")
        
        return report
    
    def generate_html_report(self, report: Dict[str, Any]) -> str:
        """
        Generate an HTML report from the JSON report
        
        Args:
            report: The JSON report data
            
        Returns:
            Path to the generated HTML report
        """
        # Simple HTML template
        html_content = f"<html><body><h1>API Test Report</h1><p>{report['name']}</p></body></html>"
        
        # Save HTML report to file
        html_path = os.path.join(self.output_dir, f"api_test_report_{self._get_timestamp()}.html")
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"HTML report saved to {html_path}")
        
        return html_path
    
    def _get_timestamp(self) -> str:
        """Get a timestamp string for file names"""
        return datetime.now().strftime("%Y%m%d_%H%M%S") 
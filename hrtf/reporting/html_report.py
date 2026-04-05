import json
import base64
import io
import matplotlib.pyplot as plt
from pathlib import Path

HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
    <title>HRTF Run Report: {run_id}</title>
    <style>
        body {{ font-family: sans-serif; margin: 40px; color: #333; }}
        h1 {{ border-bottom: 2px solid #eee; padding-bottom: 10px; }}
        .summary {{ background: #f9f9f9; padding: 20px; border-radius: 5px; margin-bottom: 30px; }}
        .scenario {{ border: 1px solid #ddd; border-radius: 5px; padding: 20px; margin-bottom: 20px; }}
        .pass {{ color: green; font-weight: bold; }}
        .fail {{ color: red; font-weight: bold; }}
        .error {{ color: orange; font-weight: bold; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
        th, td {{ border: 1px solid #eee; padding: 8px; text-align: left; }}
        th {{ background-color: #f5f5f5; }}
    </style>
</head>
<body>
    <h1>HRTF Run Report</h1>

    <div class="summary">
        <p><strong>Run ID:</strong> {run_id}</p>
        <p><strong>Date:</strong> {timestamp}</p>
        <p><strong>Overall Verdict:</strong> <span class="{verdict_class}">{verdict}</span></p>
        <p><strong>Total Duration:</strong> {duration:.2f}s</p>
    </div>

    <h2>Scenarios</h2>
    {scenarios_html}

</body>
</html>
"""

SCENARIO_TEMPLATE = """
    <div class="scenario">
        <h3>{name} <span class="{verdict_class}">[{verdict}]</span></h3>
        <p><strong>Duration:</strong> {sim_duration}s sim / {wall_duration:.2f}s real</p>
        {error_message}

        <h4>Assertions</h4>
        <table>
            <tr>
                <th>Type</th>
                <th>Signal</th>
                <th>Expected Bound</th>
                <th>Verdict</th>
            </tr>
            {assertions_html}
        </table>

        <h4>Signal Plots</h4>
        {plots_html}
    </div>
"""

ASSERTION_TEMPLATE = """
            <tr>
                <td>{type}</td>
                <td>{signal}</td>
                <td>{expected}</td>
                <td class="{verdict_class}">{verdict}</td>
            </tr>
"""

PLOT_TEMPLATE = """
    <div style="margin-top: 20px;">
        <p><strong>Signal:</strong> {signal_name}</p>
        <img src="data:image/png;base64,{base64_img}" alt="Plot for {signal_name}" style="max-width: 100%; border: 1px solid #ddd;" />
    </div>
"""

class ReportGenerator:
    """Generates HTML reports from RunResult JSON."""

    def _generate_plot(self, signal_name: str, summary: dict) -> str:
        """Generate a simple summary plot as base64."""
        plt.figure(figsize=(8, 4))
        # Since we only have summaries in the RunResult JSON and not full raw timeseries,
        # we'll plot a bar chart of the summary statistics to represent the signal
        # For a full implementation, we'd need access to the SignalLog raw data
        metrics = ['mean', 'min', 'max', 'final']
        values = [
            summary.get('mean', 0),
            summary.get('min', 0),
            summary.get('max', 0),
            summary.get('final_value', 0)
        ]

        plt.bar(metrics, values, color=['blue', 'red', 'green', 'purple'])
        plt.title(f"Summary for {signal_name}")
        plt.ylabel("Value")

        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        plt.close()
        buf.seek(0)
        return base64.b64encode(buf.read()).decode('utf-8')

    def generate(self, run_id: str, results_dir: Path = Path("results"), output_dir: Path = Path("results")) -> Path:
        run_file = results_dir / f"{run_id}.json"
        if not run_file.exists():
            raise FileNotFoundError(f"Run result not found: {run_file}")

        data = json.loads(run_file.read_text())

        scenarios_html = ""
        for s in data.get("scenarios", []):
            assertions_html = ""
            for a in s.get("assertion_results", []):
                assertions_html += ASSERTION_TEMPLATE.format(
                    type=a.get("assertion_type", "unknown"),
                    signal=a.get("signal_name", "unknown"),
                    expected=str(a.get("expected_bound", "N/A")),
                    verdict=a.get("verdict", "UNKNOWN"),
                    verdict_class=a.get("verdict", "UNKNOWN").lower()
                )

            error_msg = ""
            if s.get("error_message"):
                error_msg = f"<p class='error'>Error: {s['error_message']}</p>"

            plots_html = ""
            for sig_name, summ in s.get("signal_summaries", {}).items():
                b64_img = self._generate_plot(sig_name, summ)
                plots_html += PLOT_TEMPLATE.format(
                    signal_name=sig_name,
                    base64_img=b64_img
                )

            scenarios_html += SCENARIO_TEMPLATE.format(
                name=s.get("scenario_name", "Unknown"),
                verdict=s.get("verdict", "UNKNOWN"),
                verdict_class=s.get("verdict", "UNKNOWN").lower(),
                sim_duration=s.get("sim_duration", 0),
                wall_duration=s.get("wall_clock_duration", 0),
                error_message=error_msg,
                assertions_html=assertions_html,
                plots_html=plots_html
            )

        html = HTML_TEMPLATE.format(
            run_id=data.get("run_id", run_id),
            timestamp=data.get("timestamp", ""),
            verdict=data.get("overall_verdict", "UNKNOWN"),
            verdict_class=data.get("overall_verdict", "UNKNOWN").lower(),
            duration=data.get("total_wall_clock", 0),
            scenarios_html=scenarios_html
        )

        out_path = output_dir / f"{run_id}_report.html"
        out_path.write_text(html)
        return out_path

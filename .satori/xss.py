import os
import sys
import json
import time
import urllib.request
import urllib.error

from selenium import webdriver
from selenium.webdriver.common.by import By

TOKEN = os.environ.get("TOKEN", "")
URL = os.environ.get("URL", "")

if not TOKEN or not URL:
    print("ERROR: TOKEN and URL environment variables are required", file=sys.stderr)
    sys.exit(1)

# Extract report ID from URL
report_id = URL.rstrip("/").split("/")[-1]
print(f"Report ID: {report_id}")

# Step 1: Fetch report data and output from the API
headers = {"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}

api_url = f"https://api.satori.ci/reports/{report_id}"
req = urllib.request.Request(api_url, headers=headers)
try:
    with urllib.request.urlopen(req) as resp:
        report_data = json.loads(resp.read().decode())
    print(f"Fetched report: {report_data.get('name', 'Untitled')}")
except urllib.error.HTTPError as e:
    print(f"ERROR: API returned {e.code}", file=sys.stderr)
    sys.exit(1)

# Fetch output data (stdout/stderr from test execution)
output_data = []
try:
    out_url = f"https://api.satori.ci/outputs/{report_id}"
    req = urllib.request.Request(out_url, headers=headers)
    with urllib.request.urlopen(req) as resp:
        output_data = json.loads(resp.read().decode())
    print(f"Fetched {len(output_data)} output line(s)")
except urllib.error.HTTPError:
    print("No output data available")

# Step 2: Build HTML that renders report data exactly like template-report.php
# This replicates every vulnerable rendering path in the WordPress theme
html_template = """<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>XSS Check</title>
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
</head>
<body>
<script>
window.__xss_triggered = [];
window.alert = function(m) { window.__xss_triggered.push('alert(' + m + ')'); };
window.prompt = function(m) { window.__xss_triggered.push('prompt(' + m + ')'); };
window.confirm = function(m) { window.__xss_triggered.push('confirm(' + m + ')'); };
window.onerror = function(msg) { window.__xss_triggered.push('onerror: ' + msg); };
</script>

<div id="results"></div>
<script>
var report_data = __REPORT_DATA__;

// LINE 163: <div class="alert-description"><?php echo $report_data["user_warnings"]; ?></div>
if (report_data.user_warnings) {
    var d = document.createElement('div');
    d.innerHTML = report_data.user_warnings;
    document.body.appendChild(d);
}

// LINE 172: document.write(marked.parse(description.text))
if (report_data.description) {
    var d = document.createElement('div');
    d.innerHTML = marked.parse(report_data.description);
    document.body.appendChild(d);
}

// LINE 235: <div>satori <?php echo $report_data["run_params"]; ?></div>
if (report_data.run_params) {
    var d = document.createElement('div');
    d.innerHTML = 'satori ' + report_data.run_params;
    document.body.appendChild(d);
}

// LINE 107: uses esc_html (safe in PHP) but test innerHTML rendering
if (report_data.name) {
    var d = document.createElement('div');
    d.innerHTML = report_data.name;
    document.body.appendChild(d);
}

// LINES 268-312: Delta section uses raw <?= ?> with no escaping
if (report_data.delta) {
    var delta = report_data.delta;
    var d = document.createElement('div');
    var h = '';
    h += '<li>' + (delta.previous_time || '') + '</li>';
    h += '<li>' + (delta.delta_time || '') + '</li>';
    if (delta.delta_time_percentage) h += '<li>' + delta.delta_time_percentage + '</li>';
    if (delta.tests) {
        delta.tests.forEach(function(test) {
            h += '<h4>' + test.name + ' <span>' + test.status + '</span></h4>';
            if (test.asserts) {
                test.asserts.forEach(function(a) {
                    h += '<td>' + a.name + '</td>';
                    h += '<td>' + a.expected + '</td>';
                    h += '<td>' + a.status + '</td>';
                });
            }
        });
    }
    d.innerHTML = h;
    document.body.appendChild(d);
}

// LINE 74: code.innerHTML = res.playbook
if (report_data.playbook) {
    var d = document.createElement('code');
    d.innerHTML = report_data.playbook;
    document.body.appendChild(d);
}

// report-output.php LINE 94: stdoutSpan.innerHTML = decodedStdout (via ansi_to_html which does NOT sanitize)
// report-output.php LINE 116: stderrSpan.innerHTML = decodedStderr
var output_data = __OUTPUT_DATA__;
if (output_data && Array.isArray(output_data)) {
    output_data.forEach(function(line) {
        if (line.output) {
            if (line.output.stdout) {
                var d = document.createElement('span');
                d.innerHTML = line.output.stdout;
                document.body.appendChild(d);
            }
            if (line.output.stderr) {
                var d = document.createElement('span');
                d.innerHTML = line.output.stderr;
                document.body.appendChild(d);
            }
            if (line.output.os_error) {
                var d = document.createElement('span');
                d.innerHTML = line.output.os_error;
                document.body.appendChild(d);
            }
        }
    });
}
</script>
</body>
</html>"""

html = html_template.replace("__REPORT_DATA__", json.dumps(report_data))
html = html.replace("__OUTPUT_DATA__", json.dumps(output_data))

html_path = "/tmp/xss_check.html"
with open(html_path, "w") as f:
    f.write(html)

# Step 3: Open in headless Chrome and check for XSS
options = webdriver.ChromeOptions()
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")
options.binary_location = "/usr/bin/chromium"

driver = webdriver.Chrome(options=options)

try:
    driver.get(f"file://{html_path}")
    time.sleep(3)

    # Check 1: alert/prompt/confirm intercepted
    triggered = driver.execute_script("return window.__xss_triggered || []")
    for t in triggered:
        print(f"XSS_TRIGGERED: JS function called: {t}")

    # Check 2: Injected iframes
    iframes = driver.execute_script("return document.querySelectorAll('iframe').length")
    if iframes > 0:
        print(f"XSS_TRIGGERED: {iframes} iframe(s) injected")

    # Check 3: Event handler attributes
    dangerous = driver.execute_script("""
        var results = [];
        ['onerror','onload','onmouseover','onfocus','onclick'].forEach(function(attr) {
            document.querySelectorAll('[' + attr + ']').forEach(function(el) {
                results.push(attr + ' on <' + el.tagName.toLowerCase() + '>: ' + el.outerHTML.substring(0, 80));
            });
        });
        return results;
    """)
    for d in dangerous:
        print(f"XSS_TRIGGERED: Event handler: {d}")

    # Check 4: Injected script tags beyond our own
    injected_scripts = driver.execute_script("""
        var results = [];
        document.querySelectorAll('script').forEach(function(s) {
            var src = s.src || '';
            var txt = s.textContent || '';
            if (src.includes('marked') || txt.includes('__xss_triggered') || txt.includes('__REPORT_DATA__')) return;
            if (txt.length > 0 || src.length > 0) results.push(src || txt.substring(0, 100));
        });
        return results;
    """)
    for s in injected_scripts:
        print(f"XSS_TRIGGERED: Injected script: {s}")

    # Check 5: javascript:/data: links
    bad_links = driver.execute_script("""
        var r = [];
        document.querySelectorAll('a[href^="javascript:"],a[href^="data:"]').forEach(function(a) {
            r.push(a.href.substring(0, 100));
        });
        return r;
    """)
    for link in bad_links:
        print(f"XSS_TRIGGERED: Dangerous link: {link}")

    # Summary
    total = len(triggered) + (1 if iframes > 0 else 0) + len(dangerous) + len(injected_scripts) + len(bad_links)
    if total == 0:
        print(f"CLEAN: No XSS indicators detected for report {report_id}")
    else:
        print(f"TOTAL: {total} XSS indicator(s) found")

except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)
finally:
    driver.quit()

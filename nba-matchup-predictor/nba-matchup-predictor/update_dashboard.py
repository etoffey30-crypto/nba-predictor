import os

filepath = r'c:\Users\EDTOFFEY\OneDrive\Desktop\telosyne\project\nba_api-master\nba_api-master\nba-matchup-predictor\nba-matchup-predictor\dashboard.js'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Replacement logic for date grouping
target = '        // League grouping (NBA for now)\n        const league = "NBA League"; \n        if (league !== currentLeague) {\n            html += `<div class="league-group">${league}</div>`;\n            currentLeague = league;\n        }'

replacement = """        const date = new Date(match.matchTime * 1000);
        
        // Categorize by date for better UX
        const matchDateStr = date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
        const todayObj = new Date();
        const todayStr = todayObj.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
        
        const tomorrowObj = new Date();
        tomorrowObj.setDate(tomorrowObj.getDate() + 1);
        const tomorrowStr = tomorrowObj.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
        
        let dateLabel = "";
        if (matchDateStr === todayStr) {
            dateLabel = "Today's Matchups";
        } else if (matchDateStr === tomorrowStr) {
            dateLabel = "Tomorrow's Matchups";
        } else {
            dateLabel = date.toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' });
        }

        if (dateLabel !== currentDateLabel) {
            html += `<div class="league-group" style="grid-column: 1 / -1; margin-top: 1.5rem; margin-bottom: 0.5rem; border-left: 3px solid var(--accent-primary); padding-left: 0.8rem; font-size: 0.9rem; letter-spacing: 1px;">${dateLabel}</div>`;
            currentDateLabel = dateLabel;
        }"""

if target in content:
    new_content = content.replace(target, replacement)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("SUCCESS: Updated dashboard.js")
else:
    # Try with \r\n if \n failed
    target_rn = target.replace('\n', '\r\n')
    if target_rn in content:
        new_content = content.replace(target_rn, replacement.replace('\n', '\r\n'))
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print("SUCCESS: Updated dashboard.js (with CRLF)")
    else:
        print("ERROR: Target content not found in dashboard.js")

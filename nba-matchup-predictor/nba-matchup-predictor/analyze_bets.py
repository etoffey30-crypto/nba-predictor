import json
import math

with open("data.js", "r") as f:
    js_content = f.read()

json_str = js_content.replace("const analyticsData = ", "").rstrip(";")
data = json.loads(json_str)

output = []

for match in data.get("upcoming_matches", []):
    home = match["homeTeam"]
    away = match["awayTeam"]
    m_out = {"matchup": f"{away} @ {home}"}
    
    last_home = next((t for t in data["latest_metrics"] if t["team"] == home), None)
    last_away = next((t for t in data["latest_metrics"] if t["team"] == away), None)
    
    if last_home and last_away:
        pace = (last_home["adj_pace_5"] + last_away["adj_pace_5"]) / 2
        ortg_home = (last_home["adj_ortg_5"] + (100 - last_away["adj_drtg_5"])) / 2
        ortg_away = (last_away["adj_ortg_5"] + (100 - last_home["adj_drtg_5"])) / 2
        
        pts_home = pace * (ortg_home / 100)
        pts_away = pace * (ortg_away / 100)
        
        spread = pts_away - pts_home # Positive means home is favored by that much
        total = pts_home + pts_away
        
        win_prob_home = 1 / (1 + math.exp(-(pts_home - pts_away) / 5)) * 100
        
        m_out["projected_score"] = f"{home} {pts_home:.1f} - {away} {pts_away:.1f}"
        m_out["spread"] = f"{home} {'+' if spread > 0 else ''}{spread:.1f}"
        m_out["total"] = f"{total:.1f}"
        m_out["win_prob_home"] = f"{win_prob_home:.1f}%"
        
        home_form_w = sum(1 for g in last_home["last5_form"] if g["result"] == "W")
        away_form_w = sum(1 for g in last_away["last5_form"] if g["result"] == "W")
        m_out["form"] = f"{home} {home_form_w}-W, {away} {away_form_w}-W"
        
        shap = match.get("shap_explanation", {})
        if shap:
            m_out["key_shap"] = sorted(shap.items(), key=lambda x: abs(x[1]), reverse=True)[:3]
            
    output.append(m_out)

with open("bets_output.txt", "w", encoding="utf-8") as f:
    for m in output:
        f.write(json.dumps(m, indent=2) + "\n")

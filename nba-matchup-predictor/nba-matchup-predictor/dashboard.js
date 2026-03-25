const teamCityMap = {
    'Atlanta Hawks': 'ATL', 'Boston Celtics': 'BOS', 'Brooklyn Nets': 'BKN', 'Charlotte Hornets': 'CHA',
    'Chicago Bulls': 'CHI', 'Cleveland Cavaliers': 'CLE', 'Dallas Mavericks': 'DAL', 'Denver Nuggets': 'DEN',
    'Detroit Pistons': 'DET', 'Golden State Warriors': 'GSW', 'Houston Rockets': 'HOU', 'Indiana Pacers': 'IND',
    'LA Clippers': 'LAC', 'Los Angeles Clippers': 'LAC', 'Los Angeles Lakers': 'LAL', 'Memphis Grizzlies': 'MEM', 'Miami Heat': 'MIA',
    'Milwaukee Bucks': 'MIL', 'Minnesota Timberwolves': 'MIN', 'New Orleans Pelicans': 'NOP', 'New York Knicks': 'NYK',
    'Oklahoma City Thunder': 'OKC', 'Orlando Magic': 'ORL', 'Philadelphia 76ers': 'PHI', 'Phoenix Suns': 'PHX',
    'Portland Trail Blazers': 'POR', 'Sacramento Kings': 'SAC', 'San Antonio Spurs': 'SAS', 'Toronto Raptors': 'TOR',
    'Utah Jazz': 'UTA', 'Washington Wizards': 'WAS'
};

const FEATURE_LABELS = {
    'ADJ_ORTG_10': 'Offensive Rating',
    'ADJ_DRTG_10': 'Defensive Strength',
    'ADJ_PACE_10': 'Game Tempo',
    'NET_RATING': 'Net Efficiency',
    'ROLL_EFG_PCT_10': 'Shooting Efficiency',
    'ROLL_TOV_PCT_10': 'Ball Security',
    'ROLL_ORB_PCT_10': 'Rebound Control',
    'ROLL_FT_RATE_10': 'Free Throw Aggression',
    'SOS_10': 'Strength of Schedule',
    'IS_B2B': 'Fatigue (Back-to-Back)',
    'P_PTS': 'Star Scoring Influence',
    'P_REB': 'Star Rebounding Influence',
    'P_AST': 'Star Playmaking Influence',
    'OPP_ADJ_ORTG_10': 'Opponent Offense',
    'OPP_ADJ_DRTG_10': 'Opponent Defense',
    'OPP_SOS_10': 'Opponent Schedule',
    'OPP_IS_B2B': 'Opponent Fatigue',
    'P_STL': 'Defensive Disruptions',
    'P_BLK': 'Rim Protection',
    'P_TOV': 'Star Mistake Rate',
    'P_PF': 'Star Foul Rate',
    'P_PM': 'Star Impact (+/-)'
};

let eloChart = null;
let efficiencyChart = null;
let radarChart = null;
let currentTab = 'main';
let matchFilter = 'upcoming';

async function initDashboard() {
    try {
        if (typeof analyticsData === 'undefined' || analyticsData === null) {
            throw new Error('Analytics data not found. Please run python predictor.py first.');
        }

        populateTeamSelects();
        renderEloChart();
        renderEfficiencyChart();
        renderUpcomingMatches();
        setupEventListeners();

    } catch (error) {
        console.error('Error loading analytics data:', error);
        const container = document.querySelector('.container');
        if (container) {
            container.innerHTML += `<div class="error" style="color: #f87171; text-align: center; margin-top: 2rem;">${error.message}</div>`;
        }
    }
}

function setupEventListeners() {
    const teamASelect = document.getElementById('teamA');
    const teamBSelect = document.getElementById('teamB');

    if (teamASelect) teamASelect.addEventListener('change', updatePrediction);
    if (teamBSelect) teamBSelect.addEventListener('change', updatePrediction);

    const helpBtn = document.getElementById('helpBtn');
    const helpModal = document.getElementById('helpModal');
    const closeBtn = document.querySelector('.close-btn');

    if (helpBtn && helpModal) {
        helpBtn.addEventListener('click', () => {
            renderHelpGuide();
            helpModal.style.display = 'block';
        });
    }

    if (closeBtn && helpModal) {
        closeBtn.addEventListener('click', () => {
            helpModal.style.display = 'none';
        });
    }

    if (helpModal) {
        window.addEventListener('click', (event) => {
            if (event.target === helpModal) {
                helpModal.style.display = 'none';
            }
        });
    }

    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');
            currentTab = e.target.dataset.tab;
            updatePrediction();
        });
    });

    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');
            matchFilter = e.target.dataset.filter;
            renderUpcomingMatches();
        });
    });

    updatePrediction();
}

function updatePrediction() {
    const teamA = document.getElementById('teamA').value;
    const teamB = document.getElementById('teamB').value;
    const resultDiv = document.getElementById('predictionResult');

    if (teamA === teamB) {
        resultDiv.innerHTML = '<div class="placeholder-text">Please select two different teams</div>';
        return;
    }

    const lastA = analyticsData.latest_metrics.find(m => m.team === teamA);
    const lastB = analyticsData.latest_metrics.find(m => m.team === teamB);

    if (!lastA || !lastB) {
        resultDiv.innerHTML = '<div class="placeholder-text">Insufficient 2025-26 data for one of these teams. Please try another matchup.</div>';
        return;
    }

    // 1. CALCULATE MAIN PROJECTION
    const pace = ((lastA.adj_pace_10 || 100) + (lastB.adj_pace_10 || 100)) / 2;
    // Standard normalization: Avg of Offense and Opponent Defense
    const ortg_A = ((lastA.adj_ortg_10 || 110) + (lastB.adj_drtg_10 || 110)) / 2;
    const ortg_B = ((lastB.adj_ortg_10 || 110) + (lastA.adj_drtg_10 || 110)) / 2;

    // 2. EXTRACT ADVANCED METRICS (IF AVAILABLE)
    const matchData = analyticsData.upcoming_matches.find(m => (m.homeTeam === teamA && m.awayTeam === teamB) || (m.homeTeam === teamB && m.awayTeam === teamA));
    const advA = matchData?.prediction?.advanced || {};
    const mainA = matchData?.prediction?.main || {};
    const factorsA = matchData?.prediction?.factors?.teamA || lastA;
    const factorsB = matchData?.prediction?.factors?.teamB || lastB;

    // Apply Fatigue/Rest adjustments (Matching predictor.py)
    const fatigueA = (factorsA.is_b2b === 1) ? -2.0 : (factorsA.rest >= 3 ? 1.5 : 0);
    const fatigueB = (factorsB.is_b2b === 1) ? -2.0 : (factorsB.rest >= 3 ? 1.5 : 0);

    const ptsA = pace * ((ortg_A + fatigueA) / 100);
    const ptsB = pace * ((ortg_B + fatigueB) / 100);
    const spread = ptsB - ptsA;
    const total = ptsA + ptsB;
    const winProbA = (1 / (1 + Math.exp(-(ptsA - ptsB) / 6)) * 100);

    // 2. RENDER BY TAB
    const renderFormDots = (form) => {
        return `<div class="form-container">
            ${form.slice(-10).map(g => `<span class="form-dot ${g.result}" title="${g.date} vs ${g.opponent}: ${g.score}"></span>`).join('')}
        </div>`;
    };

    // 2. RENDER BY TAB

    const mcWinA = mainA.mc_win_A !== undefined ? mainA.mc_win_A * 100 : winProbA;
    const recommendedBet = advA.recommended_bet || 0;
    const latentA = lastA.latent_strength || 0;
    const latentB = lastB.latent_strength || 0;

    const getFormBadge = (state) => {
        const states = { 0: { l: 'COLD', c: '#f87171' }, 1: { l: 'STABLE', c: '#cbd5e1' }, 2: { l: 'HOT', c: 'var(--success)' } };
        const s = states[state] || states[1];
        return `<span class="badge" style="background: ${s.c}22; color: ${s.c}; border: 1px solid ${s.c}44;">${s.l}</span>`;
    };

    if (currentTab === 'main') {
        const mlA = mainA.ml_prob_A || (winProbA / 100);
        const mlPerc = mlA * 100;
        const market = mainA.market || {};

        const isRestA = (factorsA.is_b2b === 0);
        const isRestB = (factorsB.is_b2b === 0);
        
        // Use full names if available from upcoming_matches
        const nameA = matchData?.homeName || teamA;
        const nameB = matchData?.awayName || teamB;

        resultDiv.innerHTML = `
            <div class="responsive-flex-stack fade-in" style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 2rem; width: 100%;">
                <div class="pred-team" style="text-align: left; flex: 1.5;">
                    <div class="name">${nameA} <span style="font-size: 0.8rem; font-weight: 400; color: var(--text-secondary);">(${lastA.wins}-${lastA.losses})</span></div>
                    <div style="display: flex; gap: 0.5rem; align-items: center; margin-bottom: 0.2rem; flex-wrap: wrap;">
                        ${renderFormDots(lastA.last10_form)}
                        ${getFormBadge(lastA.form_state)}
                        <span class="badge ${isRestA ? 'success' : 'warning'}" style="font-size: 0.6rem; padding: 2px 6px;">
                            ${isRestA ? 'Rested' : 'Fatigued (B2B)'}
                        </span>
                        <div style="font-size: 0.65rem; color: var(--text-secondary); width: 100%; margin-top: 4px;">
                            Power Index: ${latentA.toFixed(2)} | Rest Days: ${factorsA.rest}
                        </div>
                    </div>
                    <div class="score">${ptsA.toFixed(1)}</div>
                </div>
                <div style="flex: 2; text-align: center; padding: 0 1rem;">
                    <div class="ml-confidence" style="font-size: 0.9rem; font-weight: 600;">AI Consensus: ${(mlPerc > 50 ? mlPerc : (100 - mlPerc)).toFixed(1)}% | Sim Win: ${mcWinA.toFixed(1)}%</div>
                    <div class="win-prob-bar" style="height: 10px; border-radius: 5px;"><div class="win-prob-fill" style="width: ${mcWinA}%; border-radius: 5px;"></div></div>
                    <div class="market-label" style="font-size: 0.75rem;">${mcWinA.toFixed(1)}% vs ${(100 - mcWinA).toFixed(1)}% (Advanced AI Analysis)</div>
                </div>
                <div class="pred-team" style="text-align: right; flex: 1.5;">
                    <div class="name">${nameB} <span style="font-size: 0.8rem; font-weight: 400; color: var(--text-secondary);">(${lastB.wins}-${lastB.losses})</span></div>
                    <div style="display: flex; gap: 0.5rem; align-items: center; justify-content: flex-end; margin-bottom: 0.2rem; flex-wrap: wrap;">
                        <span class="badge ${isRestB ? 'success' : 'warning'}" style="font-size: 0.6rem; padding: 2px 6px;">
                            ${isRestB ? 'Rested' : 'Fatigued (B2B)'}
                        </span>
                        ${getFormBadge(lastB.form_state)}
                        ${renderFormDots(lastB.last10_form)}
                        <div style="font-size: 0.65rem; color: var(--text-secondary); width: 100%; margin-top: 4px; text-align: right;">
                            Power Index: ${latentB.toFixed(2)} | Rest Days: ${factorsB.rest}
                        </div>
                    </div>
                    <div class="score">${ptsB.toFixed(1)}</div>
                </div>
            </div>

            ${renderBestBet(teamA, teamB, winProbA, spread, mlPerc, total, ptsA, ptsB, recommendedBet, advA.blowout_risk)}

            <div class="responsive-grid-stack" style="width: 100%; display: grid; grid-template-columns: 1fr 1.5fr; gap: 2rem; margin-top: 1rem;">
                <div class="radar-box glass" style="padding: 1.5rem; height: 350px;">
                    <canvas id="matchupRadar"></canvas>
                </div>
                <div class="table-container">
                    <table class="sportsbook-table">
                    <thead>
                        <tr>
                            <th>Team</th>
                            <th>Moneyline Prediction</th>
                            <th>Spread (Line)</th>
                            <th>Total (Over/Under)</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td><strong>${nameA}</strong></td>
                            <td>
                                <div class="market-cell">
                                    <span class="market-val">${winProbA.toFixed(1)}%</span>
                                    <span class="market-label">AI Win Probability</span>
                                    ${market.ml?.away ? `<span class="market-bookie" title="DraftKings">DraftKings: ${market.ml.away}</span>` : ''}
                                </div>
                            </td>
                            <td>
                                <div class="market-cell">
                                    <span class="market-val">${spread < 0 ? spread.toFixed(1) : '+' + spread.toFixed(1)}</span>
                                    <span class="market-label">AI Projected Spread</span>
                                    ${market.spread?.hdp !== undefined ? `
                                        <span class="market-bookie">DraftKings: ${market.spread.hdp > 0 ? '+' + market.spread.hdp : market.spread.hdp}</span>
                                        <span style="font-size: 0.65rem; font-weight: 800; color: ${Math.abs(spread) > Math.abs(market.spread.hdp) ? 'var(--success)' : 'var(--text-secondary)'}">
                                            (${Math.abs(spread) > Math.abs(market.spread.hdp) ? 'COVERS' : 'NO VALUE'})
                                        </span>
                                    ` : ''}
                                </div>
                            </td>
                            <td>
                                <div class="market-cell">
                                    <span class="market-val">${total.toFixed(1)}</span>
                                    <span class="market-label">AI Projected Total</span>
                                    ${market.total?.hdp ? `
                                        <span class="market-bookie">DraftKings: ${market.total.hdp}</span>
                                        <span style="font-size: 0.65rem; font-weight: 800; color: ${total > market.total.hdp ? 'var(--success)' : 'var(--danger)'}">
                                            (${total > market.total.hdp ? 'OVER' : 'UNDER'})
                                        </span>
                                    ` : ''}
                                </div>
                            </td>
                        </tr>
                        <tr>
                            <td><strong>${nameB}</strong></td>
                            <td>
                                <div class="market-cell">
                                    <span class="market-val">${(100 - winProbA).toFixed(1)}%</span>
                                    <span class="market-label">AI Win Probability</span>
                                    ${market.ml?.home ? `<span class="market-bookie" title="DraftKings">DraftKings: ${market.ml.home}</span>` : ''}
                                </div>
                            </td>
                            <td>
                                <div class="market-cell">
                                    <span class="market-val">${spread > 0 ? '-' + spread.toFixed(1) : '+' + Math.abs(spread).toFixed(1)}</span>
                                    <span class="market-label">AI Projected Spread</span>
                                    ${market.spread?.hdp !== undefined ? `
                                        <span class="market-bookie">DraftKings: ${market.spread.hdp < 0 ? '+' + Math.abs(market.spread.hdp) : '-' + market.spread.hdp}</span>
                                        <span style="font-size: 0.65rem; font-weight: 800; color: ${Math.abs(spread) > Math.abs(market.spread.hdp) ? 'var(--success)' : 'var(--text-secondary)'}">
                                            (${Math.abs(spread) > Math.abs(market.spread.hdp) ? 'COVERS' : 'NO VALUE'})
                                        </span>
                                    ` : ''}
                                </div>
                            </td>
                            <td>
                                <div class="market-cell">
                                    <span class="market-val">${total.toFixed(1)}</span>
                                    <span class="market-label">AI Projected Total</span>
                                    ${market.total?.hdp ? `
                                        <span class="market-bookie">DraftKings: ${market.total.hdp}</span>
                                        <span style="font-size: 0.65rem; font-weight: 800; color: ${total > market.total.hdp ? 'var(--success)' : 'var(--danger)'}">
                                            (${total > market.total.hdp ? 'OVER' : 'UNDER'})
                                        </span>
                                    ` : ''}
                                </div>
                            </td>
                        </tr>
                    </tbody>
                </table>
                </div>
            </div>
            
            <div class="glass fade-in" style="width: 100%; margin-top: 2rem; padding: 1.5rem;">
                <h3 style="margin-bottom: 1rem; color: var(--accent-primary); border-bottom: 1px solid var(--glass-border); padding-bottom: 0.5rem;">AI Model Explanation (Game Theory / SHAP)</h3>
                <p style="font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 1.5rem;">This chart shows the exact mathematical influence of each feature on the AI's prediction. Positive values push the prediction toward ${teamA}, negative toward ${teamB}.</p>
                
                <div style="display: flex; flex-direction: column; gap: 0.5rem;">
                    ${renderShapExplanation(teamA, teamB)}
                </div>
            </div>
        `;
        renderMatchupRadar(teamA, teamB, lastA, lastB);

    } else if (currentTab === 'factors') {
        const factorsA = lastA.factors;
        const factorsB = lastB.factors;

        const compareRow = (label, valA, valB, format = 'pct') => {
            const isBetterA = label === 'TOV%' ? valA < valB : valA > valB;
            const displayA = format === 'pct' ? (valA * 100).toFixed(1) + '%' : valA.toFixed(2);
            const displayB = format === 'pct' ? (valB * 100).toFixed(1) + '%' : valB.toFixed(2);

            return `
                <tr>
                    <td>${label}</td>
                    <td style="color: ${isBetterA ? 'var(--success)' : 'var(--text-primary)'}; font-weight: ${isBetterA ? '700' : '400'}">${displayA}</td>
                    <td style="color: ${!isBetterA ? 'var(--success)' : 'var(--text-primary)'}; font-weight: ${!isBetterA ? '700' : '400'}">${displayB}</td>
                </tr>
            `;
        };

        resultDiv.innerHTML = `
            <div class="glass fade-in" style="width: 100%; padding: 2rem;">
                <h3 style="color: var(--accent-primary); margin-bottom: 1.5rem; border-bottom: 1px solid var(--glass-border); padding-bottom: 0.5rem;">Scientific "Four Factors" Analysis</h3>
                <p style="font-size: 0.9rem; color: var(--text-secondary); margin-bottom: 2rem;">These four statistics decide 95% of all NBA games. Green indicates the statistically superior team in that category.</p>
                
                <div class="table-container">
                <table class="sportsbook-table" style="margin-top: 0;">
                    <thead>
                        <tr>
                            <th>Factor</th>
                            <th>${teamA}</th>
                            <th>${teamB}</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${compareRow('Shooting (eFG%)', factorsA.efg, factorsB.efg)}
                        ${compareRow('Turnovers (TOV%)', factorsA.tov, factorsB.tov)}
                        ${compareRow('Rebounding (ORB%)', factorsA.orb, factorsB.orb)}
                        ${compareRow('Free Throws (FT Rate)', factorsA.ftr, factorsB.ftr, 'decimal')}
                        <tr style="border-top: 2px solid var(--glass-border)">
                            <td><strong>Strength of Schedule</strong></td>
                            <td>${lastA.sos_10.toFixed(1)}</td>
                            <td>${lastB.sos_10.toFixed(1)}</td>
                        </tr>
                    </tbody>
                </table>
                </div>
                
                <div style="margin-top: 2rem; padding: 1rem; background: rgba(56, 189, 248, 0.05); border-radius: 12px; font-size: 0.85rem; color: var(--text-secondary);">
                    <strong>Scientific Note:</strong> The Four Factors model shows that ${factorsA.efg > factorsB.efg ? teamA : teamB} has the shooting advantage, while ${factorsA.tov < factorsB.tov ? teamA : teamB} protects the ball better.
                </div>
            </div>
        `;

    } else if (currentTab === 'quarters') {
        const h1A = (ptsA * lastA.q_shares[0]) + (ptsA * lastA.q_shares[1]);
        const h1B = (ptsB * lastB.q_shares[0]) + (ptsB * lastB.q_shares[1]);
        const h2A = (ptsA * lastA.q_shares[2]) + (ptsA * lastA.q_shares[3]);
        const h2B = (ptsB * lastB.q_shares[2]) + (ptsB * lastB.q_shares[3]);

        let html = `
            <div class="stats-comparison fade-in" style="width: 100%">
                <div class="table-container">
                <table class="sportsbook-table">
                    <thead>
                        <tr>
                            <th>Period</th>
                            <th>${teamA} Proj.</th>
                            <th>${teamB} Proj.</th>
                            <th>Winner</th>
                        </tr>
                    </thead>
                    <tbody>`;

        for (let i = 0; i < 4; i++) {
            const qA = ptsA * lastA.q_shares[i];
            const qB = ptsB * lastB.q_shares[i];
            html += `
                <tr>
                    <td>Quarter ${i + 1}</td>
                    <td>${qA.toFixed(1)}</td>
                    <td>${qB.toFixed(1)}</td>
                    <td style="color: ${qA > qB ? 'var(--success)' : 'var(--danger)'}; font-weight:700;">${qA > qB ? teamA : teamB}</td>
                </tr>`;
        }

        html += `
                <tr style="background: rgba(255,255,255,0.05)">
                    <td><strong>1st Half</strong></td>
                    <td><strong>${h1A.toFixed(1)}</strong></td>
                    <td><strong>${h1B.toFixed(1)}</strong></td>
                    <td><strong style="color: ${h1A > h1B ? 'var(--success)' : 'var(--danger)'}">${h1A > h1B ? teamA : teamB}</strong></td>
                </tr>
                <tr style="background: rgba(255,255,255,0.05)">
                    <td><strong>2nd Half</strong></td>
                    <td><strong>${h2A.toFixed(1)}</strong></td>
                    <td><strong>${h2B.toFixed(1)}</strong></td>
                    <td><strong style="color: ${h2A > h2B ? 'var(--success)' : 'var(--danger)'}">${h2A > h2B ? teamA : teamB}</strong></td>
                </tr>
            </tbody></table></div></div>`;

        // Form History Comparison
        html += `<div class="responsive-grid-stack" style="display: grid; grid-template-columns: 1fr 1fr; gap: 2rem; width: 100%; margin-top: 2rem;">
                    <div class="glass" style="padding: 1.5rem;">
                        <div style="margin-bottom: 1rem; font-weight: 700; color: var(--accent-primary); border-bottom: 1px solid var(--glass-border); padding-bottom: 0.5rem;">${teamA} LAST 10 FORM</div>
                        ${lastA.last10_form.map(g => `<div style="font-size: 0.8rem; margin-bottom: 0.3rem; display: flex; justify-content: space-between;">
                            <span>vs ${g.opponent}</span>
                            <span><span style="color: ${g.result === 'W' ? 'var(--success)' : 'var(--danger)'}; font-weight:700;">${g.result}</span> ${g.score}</span>
                        </div>`).join('')}
                    </div>
                    <div class="glass" style="padding: 1.5rem;">
                        <div style="margin-bottom: 1rem; font-weight: 700; color: var(--accent-secondary); border-bottom: 1px solid var(--glass-border); padding-bottom: 0.5rem;">${teamB} LAST 10 FORM</div>
                        ${lastB.last10_form.map(g => `<div style="font-size: 0.8rem; margin-bottom: 0.3rem; display: flex; justify-content: space-between;">
                            <span>vs ${g.opponent}</span>
                            <span><span style="color: ${g.result === 'W' ? 'var(--success)' : 'var(--danger)'}; font-weight:700;">${g.result}</span> ${g.score}</span>
                        </div>`).join('')}
                    </div>
                </div>`;

        resultDiv.innerHTML = html;
    } else if (currentTab === 'players') {
        const teamAPlayers = analyticsData.player_stats.filter(p => p.team === teamA);
        const teamBPlayers = analyticsData.player_stats.filter(p => p.team === teamB);

        const allPlayers = [...teamAPlayers, ...teamBPlayers].sort((a, b) => b.roll_pts - a.roll_pts);

        let html = '<div class="player-grid fade-in">';

        allPlayers.forEach(p => {
            // Adjust pts based on opponent defense (higher DRtg = more points)
            const oppDRtg = p.team === teamA ? lastB.adj_drtg_10 : lastA.adj_drtg_10;
            const mult = (oppDRtg / 100);
            const projPts = (p.roll_pts || 0) * mult;
            const momentumIcon = (p.pts_momentum || 1) > 1.15 ? '🔥' : ((p.pts_momentum || 1) < 0.85 ? '❄️' : '');
            const momentumClass = (p.pts_momentum || 1) > 1.15 ? 'heating-up' : ((p.pts_momentum || 1) < 0.85 ? 'cooling-down' : '');

            // Calculate Risk Level (Green, Yellow, Red)
            const cv = (p.std_pts || 0) / (p.roll_pts || 1);
            const m = p.pts_momentum || 1;
            let pRisk = 'Medium';
            let pRiskColor = '#facc15'; // Yellow

            if (cv < 0.22 && m > 0.92 && m < 1.12) {
                pRisk = 'Low';
                pRiskColor = 'var(--success)';
            } else if (cv > 0.38 || m < 0.8 || m > 1.25) {
                pRisk = 'High';
                pRiskColor = 'var(--danger)';
            }

            html += `
                <div class="player-card ${momentumClass}" style="border-top: 3px solid ${pRiskColor}">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.5rem;">
                         <span class="badge" style="background: ${pRiskColor}22; color: ${pRiskColor}; font-size: 0.6rem; padding: 2px 8px; border: 1px solid ${pRiskColor}44;">${pRisk} Risk</span>
                         <div style="font-size: 0.6rem; color: var(--text-secondary); text-transform: uppercase;">MOMENTUM</div>
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                        <div>
                            <div class="player-name">
                                ${p.player} ${momentumIcon}
                                ${p.status && p.status !== 'Active' ? `<span class="injury-badge ${p.status.toLowerCase().includes('out') ? 'out' : 'gtd'}">${p.status}</span>` : ''}
                            </div>
                            <div class="player-team" style="font-size: 0.7rem;">${p.team} | Recent Average: ${p.roll3_pts.toFixed(1)} Points</div>
                        </div>
                        <div style="text-align: right;">
                           <div style="font-weight: 700; color: ${p.pts_momentum > 1 ? 'var(--success)' : 'var(--danger)'}; font-size: 0.8rem;">${((p.pts_momentum - 1) * 100).toFixed(0)}%</div>
                        </div>
                    </div>
                    <div class="player-stats-row">
                        <div class="p-stat">
                            <span class="p-stat-val">${projPts.toFixed(1)} <span style="font-size: 0.7rem; color: var(--text-secondary); font-weight: 400;">±${(p.std_pts * mult).toFixed(1)}</span></span>
                            <span class="p-stat-lbl">PROJECTED POINTS</span>
                        </div>
                        <div class="p-stat">
                            <span class="p-stat-val">${p.roll_reb.toFixed(1)} <span style="font-size: 0.7rem; color: var(--text-secondary); font-weight: 400;">±${p.std_reb.toFixed(1)}</span></span>
                            <span class="p-stat-lbl">REBOUNDS</span>
                        </div>
                        <div class="p-stat">
                            <span class="p-stat-val">${p.roll_ast.toFixed(1)} <span style="font-size: 0.7rem; color: var(--text-secondary); font-weight: 400;">±${p.std_ast.toFixed(1)}</span></span>
                            <span class="p-stat-lbl">ASSISTS</span>
                        </div>
                    </div>
                    <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.5rem; margin-top: 1rem; border-top: 1px solid var(--glass-border); padding-top: 0.5rem;">
                        <div class="p-stat">
                            <span class="p-stat-val" style="font-size: 0.9rem;">${p.roll_stl.toFixed(1)}</span>
                            <span class="p-stat-lbl">STEALS</span>
                        </div>
                        <div class="p-stat">
                            <span class="p-stat-val" style="font-size: 0.9rem;">${p.roll_blk.toFixed(1)}</span>
                            <span class="p-stat-lbl">BLOCKS</span>
                        </div>
                        <div class="p-stat">
                            <span class="p-stat-val" style="font-size: 0.9rem;">${p.roll_tov.toFixed(1)}</span>
                            <span class="p-stat-lbl">TURNOVERS</span>
                        </div>
                    </div>
                    ${p.market_pts ? `
                    <div style="margin-top: 0.8rem; font-size: 0.75rem; background: rgba(255,255,255,0.05); padding: 0.5rem; border-radius: 6px; display: flex; justify-content: space-between;">
                        <span style="color: var(--text-secondary)">DraftKings Market Line:</span>
                        <span style="font-weight: 700; color: ${p.proj_pts > p.market_pts ? 'var(--success)' : 'var(--danger)'}">
                            Points ${p.market_pts} (${p.proj_pts > p.market_pts ? 'OVER' : 'UNDER'})
                        </span>
                    </div>` : ''}
                </div>`;
        });

        html += '</div>';
        resultDiv.innerHTML = html;
    }
}

function renderBestBet(teamA, teamB, winProbA, spread, mlPerc, total, ptsA, ptsB, recommendedBet = 0, blowoutRisk = 0) {
    let bestBet = "";
    let confidence = 0;
    let reasoning = "";

    const matchup = analyticsData.upcoming_matches.find(m => (m.homeTeam === teamA && m.awayTeam === teamB) || (m.homeTeam === teamB && m.awayTeam === teamA));
    const shap = matchup ? matchup.shap_explanation : null;

    // Determine the most influential stat from SHAP for the reasoning
    let topFactor = "";
    if (shap) {
        const top = Object.keys(shap).sort((a, b) => Math.abs(shap[b]) - Math.abs(shap[a]))[0];
        if (top) {
            const influence = (shap[top] > 0) ? teamA : teamB;
            topFactor = ` Key Factor: ${top.replace('PREV_', '').toUpperCase()} favoring ${influence}.`;
        }
    }

    const isAfavored = (ptsA || 0) > (ptsB || 0);
    const projectSpread = Math.abs((ptsA || 0) - (ptsB || 0)).toFixed(1);

    let riskLevel = 'Medium Risk';
    if (mlPerc > 65 || mlPerc < 35) riskLevel = 'Low Risk';
    if (mlPerc > 50 && mlPerc < 55 || mlPerc < 50 && mlPerc > 45) riskLevel = 'High Risk';

    if (mlPerc > 65) {
        bestBet = `${teamA} Moneyline`;
        confidence = mlPerc;
        reasoning = `Bayesian updating shows high probability for ${teamA}.${topFactor}`;
    } else if (mlPerc < 35) {
        bestBet = `${teamB} Moneyline`;
        confidence = 100 - mlPerc;
        reasoning = `Bayesian updating shows high probability for ${teamB}.${topFactor}`;
    } else {
        const betTeam = isAfavored ? teamA : teamB;
        bestBet = `${betTeam} Spread (-${projectSpread})`;
        confidence = Math.max(mlPerc, 100 - mlPerc);
        reasoning = `Monte Carlo simulation identifies value in the margin. Odds favor ${betTeam}.${topFactor}`;
    }

    const riskColor = riskLevel === 'Low Risk' ? 'var(--success)' : (riskLevel === 'Medium Risk' ? '#facc15' : '#f87171');
    const blowoutBadge = blowoutRisk > 0.15 ? `<span class="badge" style="background: #ef444422; color: #ef4444; border: 1px solid #ef444444;">High Blowout Risk</span>` : '';

    return `
        <div class="glass fade-in responsive-flex-stack" style="width: 100%; margin-top: 1rem; margin-bottom: 2rem; padding: 1.5rem; border-left: 4px solid ${riskColor}; display: flex; flex-direction: column; gap: 0.5rem; position: relative; overflow: hidden;">
            <div class="responsive-flex-stack" style="display: flex; justify-content: space-between; align-items: flex-start;">
                <div style="font-size: 0.85rem; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 1px; font-weight: 600;">Advanced AI Analysis & Betting Strategy</div>
                <div style="display: flex; gap: 0.5rem;">
                    ${blowoutBadge}
                    <span class="badge" style="background: ${riskColor}33; color: ${riskColor}; border: 1px solid ${riskColor}66; font-size: 0.7rem;">${riskLevel}</span>
                </div>
            </div>
            <div class="responsive-flex-stack" style="display: flex; justify-content: space-between; align-items: flex-end;">
                <div>
                    <div style="font-size: 1.5rem; font-weight: 700; color: ${riskColor};">${bestBet}</div>
                    <div style="display: flex; gap: 1rem; align-items: center; font-size: 0.9rem; flex-wrap: wrap; margin-top: 0.5rem;">
                        <span style="background: rgba(255, 255, 255, 0.1); color: var(--text-primary); padding: 0.2rem 0.6rem; border-radius: 4px; font-weight: 600;">AI Confidence: ${confidence.toFixed(1)}%</span>
                        <span style="color: var(--text-secondary); line-height: 1.4;">${reasoning.replace('Monte Carlo simulation', 'AI Simulation').replace('Bayesian updating', 'AI Historical Trends')}</span>
                    </div>
                </div>
                <div style="text-align: right; background: rgba(56, 189, 248, 0.1); padding: 0.8rem; border-radius: 12px; border: 1px solid rgba(56, 189, 248, 0.2);">
                    <div style="font-size: 0.6rem; color: var(--accent-primary); text-transform: uppercase; font-weight:700;">Suggested Stake</div>
                    <div style="font-size: 1.2rem; font-weight: 800; color: var(--text-primary);">$${recommendedBet.toFixed(2)}</div>
                    <div style="font-size: 0.6rem; color: var(--text-secondary);">per $1,000 bankroll</div>
                </div>
            </div>
            <div style="position: absolute; right: -20px; top: -20px; opacity: 0.05; font-size: 8rem; pointer-events: none;">📈</div>
        </div>
    `;
}

function renderShapExplanation(teamA, teamB) {
    const match = analyticsData.upcoming_matches.find(m => (m.homeTeam === teamA && m.awayTeam === teamB) || (m.homeTeam === teamB && m.awayTeam === teamA));
    if (!match || !match.shap_explanation) return '<div class="placeholder-text">SHAP data not available for this matchup.</div>';

    const shapVals = match.shap_explanation;
    // Sort features by absolute influence
    const sortedFeatures = Object.keys(shapVals)
        .map(k => ({ name: k.toUpperCase(), val: shapVals[k] }))
        .sort((a, b) => Math.abs(b.val) - Math.abs(a.val))
        .slice(0, 10); // Top 10 features

    if (sortedFeatures.length === 0) return '<div class="placeholder-text">No significant feature influence found.</div>';

    // Find max absolute value to scale bars relative to 100% width (up to center)
    const maxVal = Math.max(...sortedFeatures.map(f => Math.abs(f.val)));

    let html = '';
    sortedFeatures.forEach(f => {
        const isPositive = f.val > 0;
        const color = isPositive ? 'var(--accent-primary)' : 'var(--accent-secondary)';
        const label = isPositive ? `+${(f.val).toFixed(2)}` : `${(f.val).toFixed(2)}`;
        const percentage = Math.max(2, (Math.abs(f.val) / maxVal) * 50); // Scale up to 50% max width
        
        // Translate technical feature name to human label
        const cleanName = f.name.replace('PREV_', '');
        const humanLabel = FEATURE_LABELS[cleanName] || cleanName;

        html += `
            <div class="responsive-grid-stack" style="display: grid; grid-template-columns: 1fr 1fr 1fr; align-items: center; gap: 1rem; font-size: 0.8rem; margin-bottom: 0.3rem;">
                <div style="text-align: right; color: var(--text-secondary); font-weight: 600; line-height: 1;">${humanLabel}</div>
                
                <!-- Left side (Negative influence towards B) -->
                <div style="display: flex; justify-content: flex-end; align-items: center;">
                    ${!isPositive ? `<span style="margin-right: 0.5rem; color: ${color}; font-weight: 700;">${label}</span><div style="height: 6px; border-radius: 3px; background: ${color}; width: ${percentage}%;"></div>` : ''}
                </div>
                
                <!-- Right side (Positive influence towards A) -->
                <div style="display: flex; justify-content: flex-start; align-items: center;">
                    ${isPositive ? `<div style="height: 6px; border-radius: 3px; background: ${color}; width: ${percentage}%;"></div><span style="margin-left: 0.5rem; color: ${color}; font-weight: 700;">${label}</span>` : ''}
                </div>
            </div>
        `;
    });

    return html;
}

function renderMatchupRadar(teamA, teamB, lastA, lastB) {
    if (!lastA || !lastB) return;
    if (radarChart) radarChart.destroy();
    const radarElem = document.getElementById('matchupRadar');
    if (!radarElem) return;
    const ctx = radarElem.getContext('2d');

    // Normalize data for radar (0-100 scale)
    const normalize = (val, max) => Math.min(100, (val / max) * 100);

    const dataA = [
        normalize(lastA.adj_ortg_10, 125),
        normalize(100 - lastA.adj_drtg_10, 125), // Defense: 100 - DRtg
        normalize(lastA.adj_pace_10, 110),
        normalize(lastA.last10_form.filter(g => g.result === 'W').length, 10),
        normalize(lastA.adj_ortg_10 - lastA.adj_drtg_10 + 20, 40) // Net Rating
    ];

    const dataB = [
        normalize(lastB.adj_ortg_10, 125),
        normalize(100 - lastB.adj_drtg_10, 125),
        normalize(lastB.adj_pace_10, 110),
        normalize(lastB.last10_form.filter(g => g.result === 'W').length, 10),
        normalize(lastB.adj_ortg_10 - lastB.adj_drtg_10 + 20, 40)
    ];

    radarChart = new Chart(ctx, {
        type: 'radar',
        data: {
            labels: ['Offense', 'Defense', 'Pace', 'Recent Form', 'Net Efficiency'],
            datasets: [{
                label: teamA,
                data: dataA,
                borderColor: '#38bdf8',
                backgroundColor: 'rgba(56, 189, 248, 0.2)',
                pointBackgroundColor: '#38bdf8'
            }, {
                label: teamB,
                data: dataB,
                borderColor: '#818cf8',
                backgroundColor: 'rgba(129, 140, 248, 0.2)',
                pointBackgroundColor: '#818cf8'
            }]
        },
        options: {
            scales: {
                r: {
                    angleLines: { color: 'rgba(255,255,255,0.1)' },
                    grid: { color: 'rgba(255,255,255,0.1)' },
                    pointLabels: { color: '#94a3b8', font: { size: 10 } },
                    ticks: { display: false },
                    suggestedMin: 0, suggestedMax: 100
                }
            },
            plugins: { legend: { labels: { color: '#f8fafc', font: { size: 10 } } } }
        }
    });
}

function renderUpcomingMatches() {
    const container = document.getElementById('upcomingMatches');
    if (!container) return;

    if (!analyticsData.upcoming_matches || analyticsData.upcoming_matches.length === 0) {
        container.innerHTML = '<div class="placeholder-text" style="grid-column: 1 / -1; text-align: center;">No matches found in database.</div>';
        return;
    }

    const now = Math.floor(Date.now() / 1000);
    
    // Filter matches based on selected tab
    let filtered = [];
    if (matchFilter === 'live') {
        // Simple heuristic for live: started in last 3 hours but not finished (would need real-time status)
        filtered = analyticsData.upcoming_matches.filter(m => m.matchTime <= now && m.matchTime > now - 10800);
    } else if (matchFilter === 'finished') {
        filtered = analyticsData.upcoming_matches.filter(m => m.matchTime <= now - 10800);
    } else {
        filtered = analyticsData.upcoming_matches.filter(m => m.matchTime > now);
    }

    if (filtered.length === 0) {
        container.innerHTML = `<div class="placeholder-text" style="grid-column: 1 / -1; text-align: center;">No ${matchFilter} matches found right now.</div>`;
        return;
    }

    // Sort by time
    filtered.sort((a, b) => a.matchTime - b.matchTime);

    let html = '';
    let currentLeague = "";

    filtered.forEach(match => {
        // League grouping (NBA for now)
        const league = "NBA League"; 
        if (league !== currentLeague) {
            html += `<div class="league-group">${league}</div>`;
            currentLeague = league;
        }

        const teamA = match.homeTeam;
        const teamB = match.awayTeam;
        const nameA = match.homeName || teamA;
        const nameB = match.awayName || teamB;

        const date = new Date(match.matchTime * 1000);
        const timeStr = date.toLocaleString([], { weekday: 'short', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });

        // Build status badge
        let badgeHtml = '';
        if (matchFilter === 'live') {
            badgeHtml = '<span class="status-badge status-live">Live</span>';
        } else if (matchFilter === 'finished') {
            badgeHtml = '<span class="status-badge status-finished">Final</span>';
        } else {
            badgeHtml = '<span class="status-badge status-upcoming">Scheduled</span>';
        }

        const lastA = analyticsData.latest_metrics.find(m => m.team === teamA);
        const lastB = analyticsData.latest_metrics.find(m => m.team === teamB);
        let predHtml = '';

        if (lastA && lastB) {
            const pred = match.prediction || {};
            const main = pred.main || {};
            const ptsA = main.ptsA || 0;
            const ptsB = main.ptsB || 0;
            const spread = ptsB - ptsA;
            const spreadStr = spread > 0 ? `${nameB} -${spread.toFixed(1)}` : `${nameA} -${Math.abs(spread).toFixed(1)}`;

            predHtml = `
                <div class="upcoming-pred" style="flex-direction: column; gap: 0.5rem; padding: 0.4rem 0; border-top: 1px solid var(--glass-border);">
                    <div style="display: flex; justify-content: space-between; width: 100%; font-size: 0.75rem;">
                        <span><strong style="color:var(--accent-primary)">AI Pick:</strong> ${spreadStr}</span>
                        <span><strong style="color:var(--accent-secondary)">Total:</strong> O/U ${(ptsA + ptsB).toFixed(1)}</span>
                    </div>
                </div>
            `;
        }

        html += `
            <div class="upcoming-card glass fade-in" onclick="selectTeamsForPrediction('${teamA}', '${teamB}')">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.8rem;">
                    ${badgeHtml}
                    <span style="font-size: 0.7rem; color: var(--text-secondary); font-weight: 500;">${timeStr}</span>
                </div>
                <div class="upcoming-matchup" style="margin-bottom: 0.8rem; display: flex; align-items: center; gap: 1rem;">
                    <div style="display: flex; flex-direction: column; gap: 0.5rem; flex: 1;">
                        <span style="font-size: 0.95rem; font-weight: 700;">${nameB}</span>
                        <span style="font-size: 0.95rem; font-weight: 700;">${nameA}</span>
                    </div>
                    <div style="font-size: 0.7rem; color: var(--text-secondary); font-weight: 800; opacity: 0.5;">VS</div>
                </div>
                ${predHtml}
            </div>
        `;
    });

    container.innerHTML = html;
}

function selectTeamsForPrediction(teamA, teamB) {
    const selectA = document.getElementById('teamA');
    const selectB = document.getElementById('teamB');

    if (selectA && selectB) {
        if (Array.from(selectA.options).some(opt => opt.value === teamA)) selectA.value = teamA;
        if (Array.from(selectB.options).some(opt => opt.value === teamB)) selectB.value = teamB;

        updatePrediction();
        document.querySelector('.predictor-section').scrollIntoView({ behavior: 'smooth' });
    }
}

function populateTeamSelects() {
    const selectA = document.getElementById('teamA');
    const selectB = document.getElementById('teamB');
    if (!selectA || !selectB) return;

    // Create a mapping for full names
    const cityToName = {};
    for (const [fullName, abbr] of Object.entries(teamCityMap)) {
        cityToName[abbr] = fullName;
    }

    // Only populate teams that have metrics
    const teamsWithData = analyticsData.latest_metrics.map(m => m.team);

    analyticsData.teams.sort().forEach(team => {
        if (!teamsWithData.includes(team)) return;
        const fullName = cityToName[team] || team;
        const optA = document.createElement('option'); optA.value = team; optA.textContent = fullName;
        selectA.appendChild(optA);
        const optB = document.createElement('option'); optB.value = team; optB.textContent = fullName;
        selectB.appendChild(optB);
    });

    selectA.value = analyticsData.teams[0];
    selectB.value = analyticsData.teams[1];
}

function renderEloChart() {
    const canvas = document.getElementById('eloChart');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    // Select top 5 teams by ELO
    const topTeams = [...analyticsData.latest_metrics]
        .map(t => {
            const history = analyticsData.elo_history.filter(h => h.team === t.team);
            return { team: t.team, elo: history.length > 0 ? history.slice(-1)[0].elo : 1500 };
        })
        .sort((a, b) => b.elo - a.elo)
        .slice(0, 5)
        .map(t => t.team);

    const datasets = topTeams.map((team, index) => {
        const teamHistory = analyticsData.elo_history.filter(h => h.team === team);
        return {
            label: team,
            data: teamHistory.map(h => ({ x: h.date, y: h.elo })),
            borderColor: getTeamColor(index),
            backgroundColor: 'transparent',
            borderWidth: 3,
            tension: 0.4,
            pointRadius: 0,
            pointHoverRadius: 6,
            pointBackgroundColor: getTeamColor(index),
            pointBorderColor: '#fff',
            pointBorderWidth: 2
        };
    });

    eloChart = new Chart(ctx, {
        type: 'line', data: { datasets },
        options: {
            responsive: true, maintainAspectRatio: false,
            scales: {
                x: { ticks: { color: '#94a3b8', font: { size: 10 } }, grid: { color: 'rgba(255,255,255,0.05)' } },
                y: { ticks: { color: '#94a3b8', font: { size: 10 } }, grid: { color: 'rgba(255,255,255,0.05)' } }
            },
            plugins: { legend: { labels: { color: '#f8fafc', boxWidth: 10, font: { size: 10 } } } }
        }
    });
}

function renderEfficiencyChart() {
    const canvas = document.getElementById('efficiencyChart');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    efficiencyChart = new Chart(ctx, {
        type: 'scatter',
        data: {
            datasets: [{
                label: 'Teams',
                data: analyticsData.latest_metrics.map(m => ({ x: m.adj_ortg_10, y: m.adj_drtg_10, team: m.team })),
                backgroundColor: '#38bdf8'
            }]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            scales: {
                x: { title: { display: true, text: 'Offense (ORtg)', color: '#94a3b8' }, ticks: { color: '#94a3b8' }, grid: { color: 'rgba(255,255,255,0.05)' } },
                y: { reverse: true, title: { display: true, text: 'Defense (DRtg)', color: '#94a3b8' }, ticks: { color: '#94a3b8' }, grid: { color: 'rgba(255,255,255,0.05)' } }
            },
            plugins: {
                tooltip: {
                    backgroundColor: 'rgba(7, 11, 20, 0.9)',
                    titleColor: '#fff',
                    bodyColor: '#cbd5e1',
                    padding: 12,
                    displayColors: false,
                    callbacks: { label: (ctx) => `${ctx.raw.team}: ORtg ${ctx.raw.x.toFixed(1)}, DRtg ${ctx.raw.y.toFixed(1)} ` }
                },
                legend: { display: false }
            }
        }
    });
}

function getTeamColor(index) {
    const colors = ['#38bdf8', '#818cf8', '#fbbf24', '#f87171', '#4ade80'];
    return colors[index % colors.length];
}

function renderHelpGuide() {
    const modalBody = document.getElementById('modalBody');
    if (!modalBody) return;

    modalBody.innerHTML = `
        <div class="help-section fade-in">
            <p>This dashboard combines multiple predictive models to give you a deep lens on the game. Here is how to interpret the AI's "internal reasoning."</p>
            
            <h3>1. Core Markets</h3>
            <p><span class="help-highlight">Moneyline (Win Probability):</span> The AI's estimate of a team's chance to win outright. For example, "GSW 67.4%" means the AI sees a 67.4% chance of victory.</p>
            <p><span class="help-highlight">Spread:</span> A point handicap. A team with a negative spread (e.g., -3.6) is the favorite; positive is the underdog. If the AI predicts a team to win by more than the spread, they "cover."</p>
            <p><span class="help-highlight">Total (Over/Under):</span> The predicted combined final score. You can bet on whether the actual total will be over or under this line.</p>

            <div class="help-note">
                <strong>Pro Tip:</strong> If the model predicts a win but by a margin <em>smaller</em> than the spread, the underdog may be the better pick!
            </div>

            <h3>2. Scientific "Four Factors" Analysis</h3>
            <p>Dean Oliver's "Four Factors" determine roughly 95% of all game outcomes. Our model processes these in real-time:</p>
            <ul>
                <li><span class="help-highlight">eFG% (Effective Shooting):</span> Adjusts for the value of 3-pointers.</li>
                <li><span class="help-highlight">TOV% (Ball Security):</span> How often a team turns it over relative to total possessions.</li>
                <li><span class="help-highlight">ORB% (Rebounding):</span> The percentage of available offensive rebounds a team secures.</li>
                <li><span class="help-highlight">FT Rate (Free Throws):</span> How effectively a team gets to the line and makes shots.</li>
            </ul>

            <h3>3. Strength of Schedule (SOS) & Rest</h3>
            <p><span class="help-highlight">SOS:</span> Adjusts team ratings based on the quality of their recent opponents. A high SOS means a team has faced a difficult schedule.</p>
            <p><span class="help-highlight">Rest/B2B:</span> The model penalizes teams on a "Back-to-Back" (B2B) night, accounting for fatigue which statistically drops shooting percentages by 2-3%.</p>

            <div class="help-note" style="border-left-color: var(--accent-primary)">
                <strong>Decision Process:</strong> Look at the Win Probability, check the AI Top Pick for value, and verify the Four Factors align with what you know about the teams (injuries, rest, etc.).
            </div>
        </div>
    `;
}

initDashboard();

---
description: How to run the NBA Matchup Predictor pipeline
---

To run the entire NBA Matchup Predictor pipeline (generate data and run results):

1. **Ensure dependencies are installed**
   ```powershell
   pip install -r requirements.txt
   ```

2. **Generate fresh sample data**
// turbo
   ```powershell
   python generate_data.py
   ```

3. **Run the prediction engine**
// turbo
   ```powershell
   python predictor.py
   ```

Alternatively, you can run them together:
// turbo
```powershell
python generate_data.py; python predictor.py
```

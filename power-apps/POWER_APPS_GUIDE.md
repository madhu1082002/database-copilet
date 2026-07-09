# DataOps Copilot — Power Apps Build Guide

Build the Canvas App frontend described in your pSIDDHI proposal (S3-D-08), connected to your Flask backend via a **Custom Connector**.

> **Note:** Power Apps runs in Microsoft's cloud. You cannot build it as local code files — you build it at [make.powerapps.com](https://make.powerapps.com). This guide gives you every step.

---

## Prerequisites

| Requirement | Details |
|-------------|---------|
| **Power Apps Premium** | Required for custom connectors (~₹1,674/month) |
| **Flask backend running** | `py app.py` on port 5000 |
| **Public URL** | Power Apps cannot reach `localhost` — use **ngrok** (see Step 1) |
| **Microsoft account** | Same tenant as Power Apps |

---

## Step 1: Expose Flask to the Internet (ngrok)

Power Apps needs a public HTTPS URL to call your API.

1. Download [ngrok](https://ngrok.com/download)
2. Start Flask: `py app.py`
3. In a new terminal:

```powershell
ngrok http 5000
```

4. Copy the HTTPS URL (e.g. `https://abc123.ngrok-free.app`)
5. Replace `YOUR_NGROK_URL.ngrok-free.app` in `power-apps/openapi.json` with your ngrok host (no `https://`)

---

## Step 2: Create Custom Connector

1. Go to [make.powerapps.com](https://make.powerapps.com)
2. Left menu → **Data** → **Custom connectors** → **+ New custom connector** → **Import an OpenAPI file**
3. Name: `DataOpsCopilot`
4. Upload `power-apps/openapi.json`
5. **General** tab: set Host to your ngrok URL
6. **Security**: No authentication (or API key if you add auth later)
7. **Definition**: Review all 6 actions:
   - `HealthCheck`
   - `GetDashboard`
   - `GetPipelineStatus`
   - `GetFailureDiagnosis`
   - `GetOptimization`
   - `SendQuery`
   - `SendFeedback`
8. **Test** tab: Test `GetDashboard` — should return pipeline data
9. Click **Create connector**

---

## Step 3: Create Canvas App

1. **Home** → **+ Create** → **Blank app** → **Blank canvas app**
2. Name: `DataOps Copilot`
3. Format: **Tablet** (or Phone for mobile demo)
4. Add connector: **Data** → search `DataOpsCopilot` → Add

---

## Step 4: App Variables (App → OnStart)

```powerapps
Set(varMessages, Table());
Set(varCategory, "");
Set(varLoading, false);
Set(varDashboard, DataOpsCopilot.GetDashboard());
```

---

## Step 5: Screen Layout

### Screen 1: `HomeScreen`

| Control | Name | Purpose |
|---------|------|---------|
| Label | `lblTitle` | "DataOps Copilot" |
| Label | `lblSubtitle` | "GenAI-Powered Data Ops Assistant" |
| Gallery | `galStats` | Dashboard stats (4 cards) |
| Gallery | `galPipelines` | Pipeline list from dashboard |
| Dropdown | `ddCategory` | Category selector |
| Text input | `txtQuery` | Chat input box |
| Button | `btnSend` | Send query |
| Gallery | `galChat` | Conversation history |
| Button | `btnRefresh` | Refresh dashboard |

### Layout (top to bottom)

```
┌─────────────────────────────────────────┐
│  DataOps Copilot          [Refresh]     │
│  GenAI-Powered Data Ops Assistant       │
├─────────────────────────────────────────┤
│  [Total: 10] [Success: 4] [Failed: 5]   │
│  [Savings: ₹13K]                        │
├─────────────────────────────────────────┤
│  Pipeline List (Gallery)                │
│  customer_ingestion    FAILED           │
│  sales_etl             SUCCESS          │
├─────────────────────────────────────────┤
│  Category: [Auto-detect ▼]              │
│  Chat messages (scrollable gallery)     │
│  [Text input................] [Send]    │
└─────────────────────────────────────────┘
```

---

## Step 6: Key Formulas

### Dashboard stats gallery (`galStats`)

**Items:**
```powerapps
Table(
    {Label: "Total Pipelines", Value: varDashboard.total_pipelines},
    {Label: "Successful", Value: varDashboard.success_count},
    {Label: "Failed", Value: varDashboard.failed_count},
    {Label: "Potential Savings", Value: "₹" & Text(RoundDown(varDashboard.potential_monthly_savings_inr/1000, 0)) & "K"}
)
```

### Pipeline list gallery (`galPipelines`)

**Items:**
```powerapps
varDashboard.pipelines
```

**Title:** `ThisItem.pipeline_name`  
**Subtitle:** `ThisItem.run_time`  
**Status label:** `ThisItem.status`

### Category dropdown (`ddCategory`)

**Items:**
```powerapps
["", "pipeline_status", "failure_diagnosis", "optimization"]
```

### Send button (`btnSend` → OnSelect)

```powerapps
Set(varLoading, true);

Collect(varMessages, {
    Role: "user",
    Text: txtQuery.Text,
    Time: Now()
});

Set(
    varAIResponse,
    DataOpsCopilot.SendQuery({
        query: txtQuery.Text,
        category: If(ddCategory.Selected.Value = "", Blank(), ddCategory.Selected.Value)
    })
);

Collect(varMessages, {
    Role: "assistant",
    Text: varAIResponse.response,
    Intent: varAIResponse.intent,
    Time: Now()
});

Reset(txtQuery);
Set(varLoading, false)
```

### Chat gallery (`galChat`)

**Items:**
```powerapps
varMessages
```

**Template:**
- If `ThisItem.Role = "user"`: align right, blue background
- If `ThisItem.Role = "assistant"`: align left, gray background
- Show `ThisItem.Text` in a label
- If assistant, show `ThisItem.Intent` as a small tag

### Refresh button (`btnRefresh` → OnSelect)

```powerapps
Set(varDashboard, DataOpsCopilot.GetDashboard())
```

### Screen OnVisible

```powerapps
Set(varDashboard, DataOpsCopilot.GetDashboard())
```

---

## Step 7: Suggestion Chips (optional)

Add 3 buttons above the text input:

| Button text | OnSelect |
|-------------|----------|
| Did sales_etl run today? | `Set(txtQuery, "Did sales_etl run today?")` |
| Why did customer_ingestion fail? | `Set(txtQuery, "Why did customer_ingestion fail?")` |
| Can we reduce compute costs? | `Set(txtQuery, "Can we reduce compute costs?")` |

---

## Step 8: Feedback Buttons (optional)

In the chat gallery template for assistant messages, add:

**Thumbs Up OnSelect:**
```powerapps
Notify("Thanks for your feedback!", NotificationType.Success)
```

(Wire to `DataOpsCopilot.SendFeedback` when query_id is returned from backend.)

---

## Step 9: Test End-to-End

1. Flask running + ngrok running
2. Open Power Apps → **Play**
3. Try: "Did sales_etl run today?"
4. Verify AI response appears in chat
5. Verify dashboard shows pipeline cards

---

## Step 10: Publish & Demo

1. **File** → **Save** → **Publish**
2. **Share** with your evaluators
3. For Moodle demo: record screen showing Power Apps → Flask → Gemini flow

---

## Architecture (matches your proposal)

```
Power Apps Canvas App (chat UI)
        ↓ Custom Connector (HTTP)
Flask Backend (Python)
        ↓
Gemini 2.5 Flash + Mock Pipeline Data
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Connector test fails | Check ngrok is running and URL in connector matches |
| CORS error | Flask already has CORS enabled |
| Empty dashboard | Test `GetDashboard` in connector Test tab |
| AI not responding | Check `.env` API keys; quota may be exceeded |
| ngrok URL changed | Update custom connector host when ngrok restarts |

---

## Files in this folder

| File | Purpose |
|------|---------|
| `openapi.json` | Import into Power Apps custom connector |
| `POWER_APPS_GUIDE.md` | This guide |

Your web UI at `http://localhost:5000` remains a working fallback for demos if Power Apps connector has issues (Risk #3 in your proposal).

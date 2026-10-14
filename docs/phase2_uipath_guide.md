# Phase 2 Guide: NASA DONKI Data Collection in UiPath Studio

This guide provides step-by-step instructions for creating the **Data Collection** workflow in **UiPath Studio**.

---

## 1. Prerequisites

1. **UiPath Studio** (Community or Enterprise edition) running on Windows.
2. Inside your project, install the WebAPI package:
   - In UiPath Studio, click **Manage Packages** (top ribbon).
   - Under the **Official** tab, search for: `UiPath.WebAPI.Activities`.
   - Click **Install** and then **Save** / **Accept**.
3. Verify `UiPath.System.Activities` is also present (installed by default).

> ℹ️ **API Note:** As of the September 30, 2026 CCMC DONKI infrastructure migration, the base URL is `https://ccmc.gsfc.nasa.gov/DONKI-API/get`. **No API key is required.**

---

## 2. Setting Up the UiPath Project

1. Open **UiPath Studio**.
2. Click **New Project** → **Process**.
3. Fill in the project details:
   - **Name**: `SolarSentinel`
   - **Location**: `c:\Users\Devraj\SolarSentinel\uipath`
   - **Description**: `SolarSentinel space weather data collection and automation workflow`
   - **Language**: `VB` (Visual Basic) or `C#` (guide examples use standard VB syntax)
4. Click **Create**.
5. In the Project panel, double-click `Main.xaml` to open the workflow designer.

---

## 3. Creating Workflow Variables

In the **Variables** panel at the bottom of the designer, declare the following variables:

| Variable Name | Variable Type | Default Value | Scope |
|---|---|---|---|
| `startDate` | `String` | `""` | `Main` / Root Sequence |
| `endDate` | `String` | `""` | `Main` / Root Sequence |
| `apiUrl` | `String` | `""` | `Main` / Root Sequence |
| `rawResponseBody` | `String` | `""` | `Main` / Root Sequence |
| `outputFilePath` | `String` | `"..\data\raw\cme_response.json"` | `Main` / Root Sequence |

> 💡 **Path Tip**: Since UiPath project files reside in `uipath\`, relative paths refer to the project folder. `"..\data\raw\cme_response.json"` writes to the root `data\raw\` directory. Alternatively, use absolute path `"c:\Users\Devraj\SolarSentinel\data\raw\cme_response.json"`.

---

## 4. Building the Workflow

Construct the sequence by dragging and dropping activities in the following order:

### Root Activity: Sequence
- **Display Name**: `SolarSentinel - CME Data Collection`

### Step 1: Log Initial Message
- **Activity**: `Log Message`
- **Level**: `Info`
- **Message**: `"=== SolarSentinel Data Collection Started ==="`

### Step 2: Assign Date Range (Past 7 Days)
- **Activity**: `Assign`
  - **Save to**: `startDate`
  - **Value**: `DateTime.UtcNow.AddDays(-7).ToString("yyyy-MM-dd")`
- **Activity**: `Assign`
  - **Save to**: `endDate`
  - **Value**: `DateTime.UtcNow.ToString("yyyy-MM-dd")`

### Step 3: Construct the API URL
- **Activity**: `Assign`
  - **Save to**: `apiUrl`
  - **Value**: `"https://ccmc.gsfc.nasa.gov/DONKI-API/get/CME?startDate=" + startDate + "&endDate=" + endDate`

### Step 4: Log API Target
- **Activity**: `Log Message`
- **Level**: `Info`
- **Message**: `"Requesting NASA DONKI CME data from: " + apiUrl`

### Step 5: Network Call with Exception Handling
- **Activity**: `Try Catch`
  - **Display Name**: `Try Catch - Fetch DONKI Data`
  
  #### Inside `Try`:
  1. **Activity**: `HTTP Request` (`UiPath.WebAPI.Activities.HttpClient`)
     - **Properties Panel Configuration**:
       - **EndPoint**: `apiUrl`
       - **Method**: `GET`
       - **AcceptFormat**: `JSON` (or set Headers: `Accept` = `"application/json"`)
       - **TimeoutMS**: `30000` (30 seconds)
       - **Result** (Output string): `rawResponseBody`
  
  2. **Activity**: `If`
     - **Condition**: `String.IsNullOrWhiteSpace(rawResponseBody) OrElse rawResponseBody.Trim().Equals("[]")`
     - **Then**:
       - `Log Message` (Warn): `"Notice: No CME events recorded in the specified date range or empty response received."`
     - **Else**:
       - `Log Message` (Info): `"Successfully retrieved response payload (" + rawResponseBody.Length.ToString() + " characters)."`

  3. **Activity**: `Write Text File`
     - **FileName**: `outputFilePath`
     - **Text**: `rawResponseBody`
     - **Encoding**: `System.Text.Encoding.UTF8`

  4. **Activity**: `Log Message`
     - **Level**: `Info`
     - **Message**: `"SUCCESS: Raw response written to: " + outputFilePath`

  #### Inside `Catches`:
  - Add catch block for `System.Exception` (name the variable `exception`):
    - **Activity**: `Log Message`
      - **Level**: `Error`
      - **Message**: `"ERROR: Failed to retrieve or save NASA DONKI data: " + exception.Message`
    - **Activity**: `Rethrow` (optional, to bubble failure up)

### Step 6: Log Completion
- **Activity**: `Log Message`
- **Level**: `Info`
- **Message**: `"=== SolarSentinel Data Collection Finished ==="`

---

## 5. Verification & Testing

1. In UiPath Studio, click **Run** (or press `F5`).
2. Open the **Output** panel (bottom left) and verify the log output:
   - `=== SolarSentinel Data Collection Started ===`
   - `Requesting NASA DONKI CME data from: https://ccmc.gsfc.nasa.gov/DONKI-API/get/CME?...`
   - `SUCCESS: Raw response written to: ...\data\raw\cme_response.json`
   - `=== SolarSentinel Data Collection Finished ===`
3. Verify the file output:
   - Navigate to `data\raw\cme_response.json`.
   - Open it and verify that it contains a valid JSON array (`[{...}]`) with real solar observation entries.

---

## 6. Next Steps

Once verified, commit your changes in Git:
```bash
git add .
git commit -m "feat: Phase 2 - live NASA DONKI CME data collection workflow"
```

Report completion to Claude to proceed with **Phase 3 (Data Processing & Event Normalization)**.

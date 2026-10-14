# Phase 3 Guide: CME Event Normalization in UiPath Studio

This guide provides step-by-step instructions for creating the **CME Event Normalization** workflow (`NormalizeEvents.xaml`) in **UiPath Studio**.

---

## 1. Overview & Architectural Motivation

### Why Normalization is Essential
Raw NASA DONKI CME data is deeply nested, contains variable instrument lists, multiple concurrent CME analyses (some marked preliminary, some accurate), and complex 3D WSA-ENLIL MHD simulation arrays. 

Feeding raw API dumps directly into LLMs (like Google Gemini in Phase 4) has severe drawbacks:
1. **Token Inefficiency:** Raw dumps include dozens of internal IDs, unneeded submission timestamps, and redundant geometry parameters that bloat token consumption.
2. **Hallucination Risk:** Multiple analysis objects with conflicting speeds or directions cause AI models to extract inaccurate metrics.
3. **Fragile Downstream Logic:** Deterministic risk engines and Excel reporting require flat, strongly-typed fields with predictable defaults.

**The Solution:**
`NormalizeEvents.xaml` parses raw JSON, resolves ambiguities (e.g. selecting the most accurate analysis and highest shock speed), extracts Earth-directed collision trajectories, and produces a clean, standardized JSON array at `data/raw/cme_normalized.json`.

---

## 2. Namespace Configuration

To parse JSON objects and execute LINQ queries on tokens in UiPath, ensure `Newtonsoft.Json.Linq` is imported:

1. Open your **SolarSentinel** project in **UiPath Studio**.
2. Look at the bottom tabs of the designer and click **Imports** (or open **Project** panel → click the **Settings** gear icon → **Namespaces**).
3. In the search box, enter: `Newtonsoft.Json.Linq`.
4. Select `Newtonsoft.Json.Linq` and press **Enter** to add it to your imported namespaces.
5. Verify `System.Linq` is also imported (present by default in modern UiPath).

---

## 3. Creating `NormalizeEvents.xaml`

1. In the **Project** panel (left sidebar), right-click the root folder (or right-click `SolarSentinel`).
2. Select **Add** → **Sequence**.
3. Name the file: `NormalizeEvents.xaml`.
4. Click **Create**.

### Configure In Arguments
Open the **Arguments** tab at the bottom of the designer and create:

| Argument Name | Direction | Argument Type | Default Value | Description |
|---|---|---|---|---|
| `in_inputFilePath` | `In` | `String` | `"..\..\data\raw\cme_response.json"` | Path to raw DONKI response |
| `in_outputFilePath` | `In` | `String` | `"..\..\data\raw\cme_normalized.json"` | Target normalized JSON path |

> 💡 **Path Tip:** Since the UiPath project is nested inside `uipath\SolarSentinel\`, two levels up (`..\..\data\raw\...`) reaches the workspace `data\raw\` directory. You may also use absolute paths (e.g. `C:\Users\Devraj\SolarSentinel\data\raw\cme_response.json`) if preferred.

---

## 4. Declaring Workflow Variables

In the **Variables** panel at the bottom of the `NormalizeEvents` sequence, declare:

| Variable Name | Variable Type | Default Value | Scope |
|---|---|---|---|
| `rawJson` | `String` | `""` | `NormalizeEvents` (Root) |
| `cmeArray` | `Newtonsoft.Json.Linq.JArray` | — | `NormalizeEvents` (Root) |
| `normalizedEvents` | `List(Of String)` | `New List(Of String)()` | `NormalizeEvents` (Root) |
| `finalJson` | `String` | `""` | `NormalizeEvents` (Root) |
| `eventCount` | `Int32` | `0` | `NormalizeEvents` (Root) |
| `earthDirectedCount` | `Int32` | `0` | `NormalizeEvents` (Root) |

*(If `List(Of String)` is not visible in the dropdown, choose **Browse for Types...**, search `System.Collections.Generic.List<T>`, and choose `String` as the type argument).*

---

## 5. Step-by-Step Workflow Construction

Assemble the sequence inside `NormalizeEvents.xaml`:

### Step 5.1: Log Start Message
- **Activity**: `Log Message`
- **Level**: `Info`
- **Message**: `"=== Starting CME Event Normalization ==="`

### Step 5.2: Read Raw Response File
- **Activity**: `Read Text File`
- **FileName**: `in_inputFilePath` *(or in modern activities, File: `LocalResource.FromPath(in_inputFilePath)`)*
- **Content** (Output): `rawJson`
- **Encoding**: `System.Text.Encoding.UTF8`

### Step 5.3: Validate Content
- **Activity**: `If`
- **Condition**: `String.IsNullOrWhiteSpace(rawJson) OrElse rawJson.Trim().Equals("[]")`
- **Then**:
  - `Log Message` (Warn): `"Input JSON is empty. Writing empty normalized array."`
  - `Write Text File`:
    - **FileName**: `in_outputFilePath`
    - **Text**: `"[]"`
  - Add an empty `Return` activity or leave empty to exit gracefully.
- **Else**:
  - Leave empty (continue execution).

### Step 5.4: Parse JSON Array & Initialize Collector
- **Activity**: `Assign`
  - **Save to**: `cmeArray`
  - **Value**: `Newtonsoft.Json.Linq.JArray.Parse(rawJson)`
- **Activity**: `Assign`
  - **Save to**: `normalizedEvents`
  - **Value**: `New List(Of String)()`
- **Activity**: `Assign`
  - **Save to**: `eventCount`
  - **Value**: `0`
- **Activity**: `Assign`
  - **Save to**: `earthDirectedCount`
  - **Value**: `0`

---

### Step 5.5: Loop & Normalize Each CME Event

- **Activity**: `For Each`
- **Values**: `cmeArray`
- **TypeArgument**: `Newtonsoft.Json.Linq.JToken`
- **Item name**: `cmeToken`

#### Inside the Body of `For Each`:

Declare sequence-scoped variables inside the loop (or in the Variables panel with Scope = `Body`):
- `cmeObj` (`Newtonsoft.Json.Linq.JObject`)
- `bestAnalysis` (`Newtonsoft.Json.Linq.JToken`)
- `earthEnlil` (`Newtonsoft.Json.Linq.JToken`)
- `hasEarthEnlil` (`Boolean`)
- `normObj` (`Newtonsoft.Json.Linq.JObject`)

Add the following activities in order:

#### 1. Cast Token to JObject:
- **Activity**: `Assign`
  - **Save to**: `cmeObj`
  - **Value**: `CType(cmeToken, Newtonsoft.Json.Linq.JObject)`

#### 2. Resolve Best Analysis (Highest Speed among `isMostAccurate: true`):
NASA DONKI sometimes contains multiple analysis objects marked `isMostAccurate = true` (e.g., preliminary bulk vs. shock fit). We select the most accurate analysis with the highest measured speed:

- **Activity**: `Assign`
  - **Save to**: `bestAnalysis`
  - **Value**:
    ```vb
    If(cmeObj("cmeAnalyses") IsNot Nothing AndAlso cmeObj("cmeAnalyses").Any(Function(a) a("isMostAccurate") IsNot Nothing AndAlso CBool(a("isMostAccurate"))), cmeObj("cmeAnalyses").Where(Function(a) a("isMostAccurate") IsNot Nothing AndAlso CBool(a("isMostAccurate"))).OrderByDescending(Function(a) If(a("speed") IsNot Nothing AndAlso a("speed").Type <> Newtonsoft.Json.Linq.JTokenType.Null, CDbl(a("speed")), 0.0)).FirstOrDefault(), If(cmeObj("cmeAnalyses") IsNot Nothing AndAlso cmeObj("cmeAnalyses").Count > 0, cmeObj("cmeAnalyses").First(), Nothing))
    ```

#### 3. Detect Earth-Directed Trajectory & Shock Arrival:
Check whether any WSA-ENLIL simulation in the chosen analysis indicates an Earth Glancing Blow or direct impact (`isEarthGB = true`):

- **Activity**: `Assign`
  - **Save to**: `hasEarthEnlil`
  - **Value**:
    ```vb
    bestAnalysis IsNot Nothing AndAlso bestAnalysis("enlilList") IsNot Nothing AndAlso bestAnalysis("enlilList").Any(Function(e) e("isEarthGB") IsNot Nothing AndAlso CBool(e("isEarthGB")))
    ```

- **Activity**: `Assign`
  - **Save to**: `earthEnlil`
  - **Value**:
    ```vb
    If(hasEarthEnlil, bestAnalysis("enlilList").FirstOrDefault(Function(e) e("isEarthGB") IsNot Nothing AndAlso CBool(e("isEarthGB"))), Nothing)
    ```

#### 4. Build Normalized JObject:
Using `JObject` handles JSON formatting, quote escaping in notes, and null values safely:

- **Activity**: `Assign`
  - **Save to**: `normObj`
  - **Value**: `New Newtonsoft.Json.Linq.JObject()`

- **Activity**: `Assign`
  - **Save to**: `normObj("event_id")`
  - **Value**: `cmeObj("activityID").ToString()`

- **Activity**: `Assign`
  - **Save to**: `normObj("event_type")`
  - **Value**: `"CME"`

- **Activity**: `Assign`
  - **Save to**: `normObj("catalog")`
  - **Value**: `If(cmeObj("catalog") IsNot Nothing, cmeObj("catalog").ToString(), "M2M_CATALOG")`

- **Activity**: `Assign`
  - **Save to**: `normObj("start_time")`
  - **Value**: `If(cmeObj("startTime") IsNot Nothing, cmeObj("startTime").ToString(), "")`

- **Activity**: `Assign`
  - **Save to**: `normObj("source_location")`
  - **Value**: `If(cmeObj("sourceLocation") IsNot Nothing AndAlso Not String.IsNullOrWhiteSpace(cmeObj("sourceLocation").ToString()), cmeObj("sourceLocation").ToString(), "UNKNOWN")`

- **Activity**: `Assign`
  - **Save to**: `normObj("active_region")`
  - **Value**: `If(cmeObj("activeRegionNum") IsNot Nothing AndAlso cmeObj("activeRegionNum").Type <> Newtonsoft.Json.Linq.JTokenType.Null, CInt(cmeObj("activeRegionNum")), Nothing)`

- **Activity**: `Assign`
  - **Save to**: `normObj("instruments")`
  - **Value**: `If(cmeObj("instruments") IsNot Nothing, Newtonsoft.Json.Linq.JArray.FromObject(cmeObj("instruments").Select(Function(i) i("displayName").ToString())), New Newtonsoft.Json.Linq.JArray())`

- **Activity**: `Assign`
  - **Save to**: `normObj("speed_km_s")`
  - **Value**: `If(bestAnalysis IsNot Nothing AndAlso bestAnalysis("speed") IsNot Nothing AndAlso bestAnalysis("speed").Type <> Newtonsoft.Json.Linq.JTokenType.Null, CDbl(bestAnalysis("speed")), Nothing)`

- **Activity**: `Assign`
  - **Save to**: `normObj("half_angle_deg")`
  - **Value**: `If(bestAnalysis IsNot Nothing AndAlso bestAnalysis("halfAngle") IsNot Nothing AndAlso bestAnalysis("halfAngle").Type <> Newtonsoft.Json.Linq.JTokenType.Null, CDbl(bestAnalysis("halfAngle")), Nothing)`

- **Activity**: `Assign`
  - **Save to**: `normObj("cme_type")`
  - **Value**: `If(bestAnalysis IsNot Nothing AndAlso bestAnalysis("type") IsNot Nothing AndAlso bestAnalysis("type").Type <> Newtonsoft.Json.Linq.JTokenType.Null, bestAnalysis("type").ToString(), Nothing)`

- **Activity**: `Assign`
  - **Save to**: `normObj("feature_code")`
  - **Value**: `If(bestAnalysis IsNot Nothing AndAlso bestAnalysis("featureCode") IsNot Nothing AndAlso bestAnalysis("featureCode").Type <> Newtonsoft.Json.Linq.JTokenType.Null, bestAnalysis("featureCode").ToString(), Nothing)`

- **Activity**: `Assign`
  - **Save to**: `normObj("measurement_technique")`
  - **Value**: `If(bestAnalysis IsNot Nothing AndAlso bestAnalysis("measurementTechnique") IsNot Nothing AndAlso bestAnalysis("measurementTechnique").Type <> Newtonsoft.Json.Linq.JTokenType.Null, bestAnalysis("measurementTechnique").ToString(), Nothing)`

- **Activity**: `Assign`
  - **Save to**: `normObj("time_at_21_5_rs")`
  - **Value**: `If(bestAnalysis IsNot Nothing AndAlso bestAnalysis("time21_5") IsNot Nothing AndAlso bestAnalysis("time21_5").Type <> Newtonsoft.Json.Linq.JTokenType.Null, bestAnalysis("time21_5").ToString(), Nothing)`

- **Activity**: `Assign`
  - **Save to**: `normObj("is_earth_directed")`
  - **Value**: `hasEarthEnlil`

- **Activity**: `Assign`
  - **Save to**: `normObj("earth_arrival_time")`
  - **Value**: `If(hasEarthEnlil AndAlso earthEnlil("estimatedShockArrivalTime") IsNot Nothing AndAlso earthEnlil("estimatedShockArrivalTime").Type <> Newtonsoft.Json.Linq.JTokenType.Null, earthEnlil("estimatedShockArrivalTime").ToString(), Nothing)`

- **Activity**: `Assign`
  - **Save to**: `normObj("max_kp_predicted")`
  - **Value**:
    ```vb
    If(bestAnalysis IsNot Nothing AndAlso bestAnalysis("enlilList") IsNot Nothing AndAlso bestAnalysis("enlilList").Count > 0, If(bestAnalysis("enlilList")(0)("kp_180") IsNot Nothing AndAlso bestAnalysis("enlilList")(0)("kp_180").Type <> Newtonsoft.Json.Linq.JTokenType.Null, CInt(bestAnalysis("enlilList")(0)("kp_180")), If(bestAnalysis("enlilList")(0)("kp_135") IsNot Nothing AndAlso bestAnalysis("enlilList")(0)("kp_135").Type <> Newtonsoft.Json.Linq.JTokenType.Null, CInt(bestAnalysis("enlilList")(0)("kp_135")), If(bestAnalysis("enlilList")(0)("kp_90") IsNot Nothing AndAlso bestAnalysis("enlilList")(0)("kp_90").Type <> Newtonsoft.Json.Linq.JTokenType.Null, CInt(bestAnalysis("enlilList")(0)("kp_90")), Nothing))), Nothing)
    ```

- **Activity**: `Assign`
  - **Save to**: `normObj("estimated_duration_hrs")`
  - **Value**:
    ```vb
    If(bestAnalysis IsNot Nothing AndAlso bestAnalysis("enlilList") IsNot Nothing AndAlso bestAnalysis("enlilList").Count > 0 AndAlso bestAnalysis("enlilList")(0)("estimatedDuration") IsNot Nothing AndAlso bestAnalysis("enlilList")(0)("estimatedDuration").Type <> Newtonsoft.Json.Linq.JTokenType.Null, CDbl(bestAnalysis("enlilList")(0)("estimatedDuration")), Nothing)
    ```

- **Activity**: `Assign`
  - **Save to**: `normObj("linked_event_ids")`
  - **Value**: `If(cmeObj("linkedEvents") IsNot Nothing AndAlso cmeObj("linkedEvents").Type <> Newtonsoft.Json.Linq.JTokenType.Null, Newtonsoft.Json.Linq.JArray.FromObject(cmeObj("linkedEvents").Select(Function(le) le("activityID").ToString())), New Newtonsoft.Json.Linq.JArray())`

- **Activity**: `Assign`
  - **Save to**: `normObj("note")`
  - **Value**: `If(cmeObj("note") IsNot Nothing, cmeObj("note").ToString(), "")`

- **Activity**: `Assign`
  - **Save to**: `normObj("donki_url")`
  - **Value**: `If(cmeObj("link") IsNot Nothing, cmeObj("link").ToString(), "")`

#### 5. Add to Collection and Track Counters:
- **Activity**: `Invoke Method`
  - **TargetObject**: `normalizedEvents`
  - **MethodName**: `Add`
  - **Parameters**: `normObj.ToString(Newtonsoft.Json.Formatting.Indented)` *(In, String)*
  *(Alternatively: Use an `Assign` activity with `normalizedEvents = normalizedEvents.Concat(New String() { normObj.ToString(Newtonsoft.Json.Formatting.Indented) }).ToList()`)*

- **Activity**: `Assign`
  - **Save to**: `eventCount`
  - **Value**: `eventCount + 1`

- **Activity**: `If`
  - **Condition**: `hasEarthEnlil`
  - **Then**:
    - `Assign`: `earthDirectedCount = earthDirectedCount + 1`

---

### Step 5.6: Serialize and Save Normalized Output

Outside the `For Each` loop:

1. **Activity**: `Assign`
   - **Save to**: `finalJson`
   - **Value**: `"[" + Environment.NewLine + String.Join("," + Environment.NewLine, normalizedEvents) + Environment.NewLine + "]"`

2. **Activity**: `Write Text File`
   - **FileName**: `in_outputFilePath` *(or File: `LocalResource.FromPath(in_outputFilePath)`)*
   - **Text**: `finalJson`
   - **Encoding**: `System.Text.Encoding.UTF8`

3. **Activity**: `Log Message`
   - **Level**: `Info`
   - **Message**: `"=== CME Normalization Complete: " + eventCount.ToString() + " events normalized (" + earthDirectedCount.ToString() + " Earth-directed). Saved to: " + in_outputFilePath + " ==="`

---

## 6. Integrating into `Main.xaml`

Now chain the normalization workflow to run automatically after data collection:

1. In UiPath Studio, open `Main.xaml`.
2. Locate the existing data collection sequence (after `Write Text File` of `cme_response.json`).
3. Drag an **Invoke Workflow File** activity and place it right after the file write.
4. Set the workflow file to invoke: `"NormalizeEvents.xaml"`.
5. Click **Import Arguments** (or **Edit Arguments**) in the properties panel:
   - `in_inputFilePath` = `"..\..\data\raw\cme_response.json"` *(or `"C:\Users\Devraj\SolarSentinel\data\raw\cme_response.json"`)*
   - `in_outputFilePath` = `"..\..\data\raw\cme_normalized.json"` *(or `"C:\Users\Devraj\SolarSentinel\data\raw\cme_normalized.json"`)*
6. Save `Main.xaml`.

---

## 7. Verification & Testing Checklist

1. In UiPath Studio, click **Run** (or press `F5`).
2. Verify the **Output** panel:
   - `=== SolarSentinel Data Collection Started ===`
   - `SUCCESS: Raw response written to: ...\data\raw\cme_response.json`
   - `=== Starting CME Event Normalization ===`
   - `=== CME Normalization Complete: X events normalized (Y Earth-directed). Saved to: ...\data\raw\cme_normalized.json ===`
3. Inspect `data\raw\cme_normalized.json`:
   - Valid JSON array containing objects matching `data/sample/cme_normalized_sample.json`.
   - Event `2026-10-10T16:15:00-CME-001` should show:
     - `speed_km_s`: `1553.0`
     - `max_kp_predicted`: `9`
     - `feature_code`: `"SH"`
     - `is_earth_directed`: `false`
     - `active_region`: `14549`
   - Earth-directed events have `is_earth_directed: true` and a valid ISO timestamp in `earth_arrival_time`.

---

## 8. Next Steps & Git Commit

Once testing succeeds, commit your progress in Git:

```bash
git add data/sample/cme_normalized_sample.json docs/phase3_uipath_guide.md uipath/SolarSentinel/NormalizeEvents.xaml uipath/SolarSentinel/Main.xaml
git commit -m "feat: Phase 3 - CME event normalization workflow (NormalizeEvents.xaml)"
```

Notify Claude to proceed with **Phase 4: AI Analysis & Structured Threat Assessment**.

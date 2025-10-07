import java.net.http.*;
import java.net.URI;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.regex.*;
import java.io.IOException;
import java.util.stream.Collectors;

public class JiraACToTestsNoDeps {

    // --- env ---
    private static final String JIRA_BASE   = reqEnv("JIRA_BASE_URL");
    private static final String JIRA_EMAIL  = reqEnv("JIRA_EMAIL");
    private static final String JIRA_TOKEN  = reqEnv("JIRA_API_TOKEN");
    private static final String PROJECT_KEY = optEnv("JIRA_PROJECT_KEY", "SCRUM");
    private static final String STORY_KEY   = optEnv("STORY_KEY", "SCRUM-1");
    private static final String TEST_TYPE   = optEnv("TEST_ISSUE_TYPE", "Test");
    private static final String LINK_TYPE   = optEnv("ISSUE_LINK_TYPE", "Relates");
    private static final String AC_FIELD_ID = optEnv("AC_FIELD_ID", "customfield_10059");

    private static final HttpClient HTTP = HttpClient.newBuilder().build();

    public static void main(String[] args) throws Exception {
        // 1) Read the story (summary + AC field only)
        String fields = urlEncode("summary," + AC_FIELD_ID);
        String issueUrl = JIRA_BASE + "/rest/api/3/issue/" + STORY_KEY + "?fields=" + fields;

        String storyJson = doGet(issueUrl);
        String storySummary = extractSummary(storyJson);
        List<String> acLines = extractAC(storyJson, AC_FIELD_ID);

        if (acLines.isEmpty()) {
            acLines = List.of("No Acceptance Criteria provided.");
            System.out.println("⚠️  No AC found in " + AC_FIELD_ID + " for " + STORY_KEY + "; creating a placeholder test.");
        }

        // 2) Create one Test per AC line and link it back to the story
        List<String> created = new ArrayList<>();
        int idx = 0;
        for (String ac : acLines) {
            idx++;
            String summary = "[Auto-Test] " + STORY_KEY + " - AC " + idx;
            String description = buildPlainDescription(storySummary, ac, idx, acLines.size());

            String testKey = createIssue(PROJECT_KEY, TEST_TYPE, summary, description);
            linkIssues(testKey, STORY_KEY, LINK_TYPE);
            System.out.printf("✅ Created %s and linked to %s%n", testKey, STORY_KEY);
            created.add(testKey);
        }

        System.out.println("Done. Created tests: " + created);
    }

    // ---------- HTTP helpers ----------
    private static String doGet(String url) throws IOException, InterruptedException {
        HttpRequest req = HttpRequest.newBuilder()
                .uri(URI.create(url))
                .GET()
                .header("Authorization", basicAuth())
                .header("Accept", "application/json")
                .build();
        HttpResponse<String> resp = HTTP.send(req, HttpResponse.BodyHandlers.ofString());
        ensure2xx(resp, "GET " + url);
        return resp.body();
    }

    private static String doPost(String url, String jsonBody) throws IOException, InterruptedException {
        HttpRequest req = HttpRequest.newBuilder()
                .uri(URI.create(url))
                .POST(HttpRequest.BodyPublishers.ofString(jsonBody))
                .header("Authorization", basicAuth())
                .header("Accept", "application/json")
                .header("Content-Type", "application/json")
                .build();
        HttpResponse<String> resp = HTTP.send(req, HttpResponse.BodyHandlers.ofString());
        ensure2xx(resp, "POST " + url + " body=" + jsonBody);
        return resp.body();
    }

    private static void ensure2xx(HttpResponse<?> resp, String ctx) {
        int code = resp.statusCode();
        if (code < 200 || code >= 300) {
            throw new RuntimeException("HTTP " + code + " for " + ctx + " ; body=" + resp.body());
        }
    }

    private static String basicAuth() {
        String creds = JIRA_EMAIL + ":" + JIRA_TOKEN;
        return "Basic " + Base64.getEncoder().encodeToString(creds.getBytes(StandardCharsets.UTF_8));
    }

    private static String urlEncode(String s) {
        return URLEncoder.encode(s, StandardCharsets.UTF_8);
    }

    // ---------- JIRA operations ----------
    private static String createIssue(String projectKey, String issueType, String summary, String descriptionPlain)
            throws IOException, InterruptedException {

        // Using plain-text description (valid in Jira Cloud). If you prefer ADF, you can craft ADF JSON string similarly.
        String payload = "{\n" +
                "  \"fields\": {\n" +
                "    \"project\": {\"key\": " + jsonStr(projectKey) + "},\n" +
                "    \"summary\": " + jsonStr(summary) + ",\n" +
                "    \"issuetype\": {\"name\": " + jsonStr(issueType) + "},\n" +
                "    \"description\": " + jsonStr(descriptionPlain) + "\n" +
                "  }\n" +
                "}";

        String res = doPost(JIRA_BASE + "/rest/api/3/issue", payload);
        // Extract "key":"ABC-123" (simple regex—avoids external JSON libs)
        Matcher m = Pattern.compile("\\\"key\\\"\\s*:\\s*\\\"([A-Z]+-\\d+)\\\"").matcher(res);
        if (m.find()) return m.group(1);
        throw new RuntimeException("Could not parse created issue key from: " + res);
    }

    private static void linkIssues(String inwardKey, String outwardKey, String linkType) throws IOException, InterruptedException {
        String payload = "{\n" +
                "  \"type\": {\"name\": " + jsonStr(linkType) + "},\n" +
                "  \"inwardIssue\": {\"key\": " + jsonStr(inwardKey) + "},\n" +
                "  \"outwardIssue\": {\"key\": " + jsonStr(outwardKey) + "}\n" +
                "}";
        doPost(JIRA_BASE + "/rest/api/3/issueLink", payload);
    }

    // ---------- Minimal JSON extraction (summary + AC) ----------
    private static String extractSummary(String json) {
        // naive but effective for Jira's shape when fields=summary,<acField>
        Matcher m = Pattern.compile("\"summary\"\\s*:\\s*\"((?:\\\\.|[^\"\\\\])*)\"", Pattern.DOTALL).matcher(json);
        return m.find() ? unescape(m.group(1)) : "(no summary)";
    }

    private static List<String> extractAC(String json, String acFieldId) {
        // 1) Try array of strings
        Pattern arr = Pattern.compile("\"" + Pattern.quote(acFieldId) + "\"\\s*:\\s*\\[(.*?)\\]", Pattern.DOTALL);
        Matcher ma = arr.matcher(json);
        if (ma.find()) {
            String inside = ma.group(1);
            // capture every "string" inside the array
            Matcher item = Pattern.compile("\"((?:\\\\.|[^\"\\\\])*)\"").matcher(inside);
            List<String> items = new ArrayList<>();
            while (item.find()) items.add(unescape(item.group(1)));
            return normalizeToLines(items);
        }

        // 2) Try plain string
        Pattern str = Pattern.compile("\"" + Pattern.quote(acFieldId) + "\"\\s*:\\s*\"((?:\\\\.|[^\"\\\\])*)\"", Pattern.DOTALL);
        Matcher ms = str.matcher(json);
        if (ms.find()) {
            String s = unescape(ms.group(1));
            return normalizeToLines(List.of(s));
        }

        // 3) If it's an object (ADF/rich), just flatten by stripping quotes/braces best-effort
        Pattern obj = Pattern.compile("\"" + Pattern.quote(acFieldId) + "\"\\s*:\\s*\\{");
        if (obj.matcher(json).find()) {
            // grab a rough block from field start to next top-level comma under "fields"
            // fallback: one generic line (you can extend to true ADF parsing if needed)
            return List.of("Acceptance Criteria present (rich/ADF) — review in story.");
        }

        return Collections.emptyList();
    }

    private static List<String> normalizeToLines(List<String> blocks) {
        List<String> out = new ArrayList<>();
        for (String b : blocks) {
            if (b == null) continue;
            // split by newlines or bullet-like prefixes
            String[] parts = b.split("\\r?\\n|\\u2022\\s+|^\\s*[-*]\\s+");
            for (String p : parts) {
                String t = p.trim();
                if (!t.isBlank()) out.add(t);
            }
        }
        // dedupe, keep order
        return new ArrayList<>(new LinkedHashSet<>(out));
    }

    private static String buildPlainDescription(String storySummary, String ac, int idx, int total) {
        return "Generated from story: " + STORY_KEY + " — " + storySummary + "\n\n" +
               "Acceptance Criteria (" + idx + "/" + total + "):\n" + ac + "\n\n" +
               "Suggested Steps:\n" +
               "1) Review prerequisites\n" +
               "2) Execute steps per AC (Given/When/Then)\n" +
               "3) Capture actual result & evidence\n" +
               "4) Record pass/fail and link defects\n";
    }

    // ---------- tiny JSON helpers ----------
    private static String jsonStr(String s) {
        return "\"" + s
                .replace("\\", "\\\\")
                .replace("\"", "\\\"")
                .replace("\n", "\\n")
                .replace("\r", "\\r") + "\"";
    }

    private static String unescape(String s) {
        return s.replace("\\n", "\n").replace("\\r", "\r").replace("\\\"", "\"").replace("\\\\", "\\");
    }

    private static String reqEnv(String k) {
        String v = System.getenv(k);
        if (v == null || v.isBlank()) throw new IllegalArgumentException("Missing env var: " + k);
        return v.trim();
    }
    private static String optEnv(String k, String def) {
        String v = System.getenv(k);
        return (v == null || v.isBlank()) ? def : v.trim();
    }
}

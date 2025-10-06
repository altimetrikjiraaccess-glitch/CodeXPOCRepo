try:
    import requests  # noqa
except ImportError:
    import subprocess, sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])

import os, sys, json, argparse, hashlib, requests, pathlib, textwrap, re

JIRA_BASE  = os.getenv("JIRA_BASE")

JIRA_EMAIL = os.getenv("JIRA_EMAIL")

JIRA_TOKEN = os.getenv("JIRA_TOKEN")

AC_FIELD   = os.getenv("AC_FIELD", "customfield_10059")

TEST_ISSUETYPE_NAME = os.getenv("TEST_ISSUETYPE_NAME","Test")

LINK_TYPE_NAME       = os.getenv("LINK_TYPE_NAME","Tests")

CODEX_BASE = os.getenv("CODEX_BASE")


def jira_headers():

    return {

        "Accept": "application/json",

        "Content-Type": "application/json"

    }

def jira_get_issue(key, fields=None):

    params = {}

    if fields: params["fields"] = ",".join(fields)

    r = requests.get(f"{JIRA_BASE}/rest/api/3/issue/{key}",

                     headers=jira_headers(), params=params, auth=(JIRA_EMAIL, JIRA_TOKEN), timeout=30)

    r.raise_for_status(); return r.json()

def jira_create_test(project_key, summary, adf_description, labels=None, priority=None):

    payload = {

        "fields": {

            "project": {"key": project_key},

            "issuetype": {"name": TEST_ISSUETYPE_NAME},

            "summary": summary,

            "description": adf_description,

            "labels": (labels or ["autogen","codex"])

        }

    }

    if priority: payload["fields"]["priority"] = {"name": priority}

    r = requests.post(f"{JIRA_BASE}/rest/api/3/issue", headers=jira_headers(),

                      auth=(JIRA_EMAIL, JIRA_TOKEN), json=payload, timeout=30)

    r.raise_for_status(); return r.json()["key"]

def jira_link(story_key, test_key):

    payload = {"type":{"name":LINK_TYPE_NAME}, "inwardIssue":{"key":story_key}, "outwardIssue":{"key":test_key}}

    r = requests.post(f"{JIRA_BASE}/rest/api/3/issueLink", headers=jira_headers(),

                      auth=(JIRA_EMAIL, JIRA_TOKEN), json=payload, timeout=30)

    r.raise_for_status()

def jira_comment(issue_key, text):

    r = requests.post(f"{JIRA_BASE}/rest/api/3/issue/{issue_key}/comment", headers=jira_headers(),

                      auth=(JIRA_EMAIL, JIRA_TOKEN), json={"body": text}, timeout=30)

    r.raise_for_status()

def adf_paragraph(t): return {"type":"paragraph","content":[{"type":"text","text":t}]}

def adf_from_test(pre, steps, expected):

    return {"type":"doc","version":1,"content":[

        adf_paragraph(f"Preconditions: {pre}"),

        {"type":"heading","attrs":{"level":3},"content":[{"type":"text","text":"Steps"}]},

        {"type":"orderedList","content":[{"type":"listItem","content":[adf_paragraph(s)]} for s in steps]},

        {"type":"heading","attrs":{"level":3},"content":[{"type":"text","text":"Expected"}]},

        {"type":"bulletList","content":[{"type":"listItem","content":[adf_paragraph(e)]} for e in expected]}

    ]}

def adf_to_plain(adf):

    def walk(n):

        if isinstance(n, dict):

            t = n.get("text","")

            return " ".join([t] + [walk(c) for c in n.get("content",[]) if c])

        if isinstance(n, list): return " ".join(walk(x) for x in n)

        return ""

    try: return re.sub(r"\s+"," ", walk(adf)).strip()

    except: return ""

def call_codex(summary, description, ac_text):

    if not (CODEX_BASE and CODEX_API_KEY):

        return None

    prompt = f"""You are a QA architect. Generate concise functional test cases from this Jira story.

Summary: {summary}

Acceptance Criteria:

{ac_text}

If AC is missing, infer a baseline happy path.

Return JSON list where each item = {{

  "title": str,

  "preconditions": str,

  "steps": [str],

  "expected": [str]

}}."""

    try:

        r = requests.post(f"{CODEX_BASE}/v1/generate-tests",

                          headers={"Authorization": f"Bearer {CODEX_API_KEY}",

                                   "Content-Type": "application/json"},

                          json={"prompt": prompt, "format":"json"}, timeout=60)

        r.raise_for_status()

        data = r.json()

        # Accept either direct list or {tests: [...]}

        tests = data.get("tests", data if isinstance(data, list) else [])

        # sanity

        norm = []

        for t in tests:

            norm.append({

                "title": t.get("title")[:255],

                "preconditions": t.get("preconditions","As per story"),

                "steps": [str(s) for s in (t.get("steps") or [])] or ["Execute main flow"],

                "expected": [str(e) for e in (t.get("expected") or [])] or ["Meets acceptance criteria"]

            })

        return norm or None

    except Exception as e:

        print("CodeX call failed:", e, file=sys.stderr); return None

def fallback_generate(summary, ac_text):

    lines = [l.strip("-•* ").strip() for l in (ac_text or "").splitlines() if l.strip()]

    if not lines:

        return [{"title": f"{summary} – Happy path","preconditions":"As per story",

                 "steps":["Execute main flow"],"expected":["Meets acceptance criteria"]}]

    out=[]

    for i, l in enumerate(lines,1):

        out.append({"title": f"{summary} – AC{i}","preconditions":"As per story",

                    "steps":[l], "expected":["Acceptance criterion satisfied"]})

    return out

def write_repo_tests(issue_key, tests):

    base = pathlib.Path("tests/generated") / issue_key

    base.mkdir(parents=True, exist_ok=True)

    # Gherkin-style .feature + Markdown

    feat = []

    for i,t in enumerate(tests,1):

        feat.append(f"Scenario: {t['title']}\n  Given {t['preconditions']}\n" +

                    "".join([f"  When {t['steps'][0]}\n" if j==0 else f"  And {s}\n" for j,s in enumerate(t['steps'])]) +

                    "".join([f"  Then {e}\n" for e in t['expected']]) + "\n")

        md = f"""# {t['title']}

**Preconditions**  

{t['preconditions']}

## Steps

{os.linesep.join([f"{idx}. {s}" for idx,s in enumerate(t['steps'],1)])}

## Expected

{os.linesep.join([f"- {e}" for e in t['expected']])}

"""

        (base / f"TC_{i:02}.md").write_text(md, encoding="utf-8")

    (base / f"{issue_key}.feature").write_text("Feature: Auto tests\n\n" + "\n".join(feat), encoding="utf-8")

def main():

    ap = argparse.ArgumentParser()

    ap.add_argument("--jira-key", required=True)

    ap.add_argument("--mode", choices=["repo","jira","both"], default="repo")

    args = ap.parse_args()

    issue = jira_get_issue(args.jira_key, fields=[

        "summary","description","labels","priority","project","status",AC_FIELD

    ])

    f = issue["fields"]

    summary = f.get("summary", args.jira_key)

    project_key = f["project"]["key"]

    priority = (f.get("priority") or {}).get("name")

    labels = (f.get("labels") or []) + ["autogen","codex"]

    # Pull AC text (prefer custom field)

    ac_raw = f.get(AC_FIELD)

    if isinstance(ac_raw, dict) and "content" in (ac_raw or {}):

        ac_text = adf_to_plain(ac_raw)

    else:

        ac_text = (ac_raw or "").strip()

    if not ac_text:

        desc = f.get("description") or ""

        ac_text = adf_to_plain(desc) if isinstance(desc, dict) else str(desc)

    # Hash for idempotency

    h = hashlib.sha256((summary + ac_text + project_key).encode()).hexdigest()[:12]

    # Try CodeX; fallback local

    tests = call_codex(summary, f"{summary}\n\n{ac_text}", ac_text) or fallback_generate(summary, ac_text)

    # repo mode

    if args.mode in ("repo","both"):

        write_repo_tests(args.jira_key, tests)

    created = []

    if args.mode in ("jira","both"):

        for t in tests:

            adf = adf_from_test(t["preconditions"], t["steps"], t["expected"])

            tk = jira_create_test(project_key, t["title"], adf, labels=labels, priority=priority)

            jira_link(args.jira_key, tk)

            created.append(tk)

    try:

        note = f"CodeX: generated {len(tests)} test(s) (mode={args.mode}, hash={h})."

        if created: note += " Created Jira Tests: " + ", ".join(created)

        jira_comment(args.jira_key, note)

    except Exception as e:

        print("Comment failed:", e, file=sys.stderr)

if __name__ == "__main__":

    main()

 

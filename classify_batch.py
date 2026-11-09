
import csv
import json
import os
import time
from openai import OpenAI

# -----------------------------
# Configuration
# -----------------------------

INPUT_FILE = "physorg_test.csv"
OUTPUT_FILE = "classified_physorg_test_v2.csv"
MODEL = "gpt-4.1-mini"
MAX_NEW_ARTICLES = 10

client = OpenAI(max_retries=2)

# -----------------------------
# Save results safely
# -----------------------------

def save_results(results):
    if not results:
        return

    temporary_file = OUTPUT_FILE + ".tmp"

    with open(
        temporary_file,
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=list(results[0].keys())
        )
        writer.writeheader()
        writer.writerows(results)

    os.replace(temporary_file, OUTPUT_FILE)


# -----------------------------
# Load articles
# -----------------------------

with open(
    INPUT_FILE,
    encoding="utf-8-sig",
    newline=""
) as file:
    articles = list(csv.DictReader(file))

# Process newer science sources first
source_priority = {
    "Nature": 0,
    "Phys.org": 1,
    "ScienceDaily": 2,
    "Guardian": 3
}

articles.sort(
    key=lambda article: source_priority.get(
        article["source"], 99
    )
)

print(f"Loaded {len(articles)} articles to check.")

# -----------------------------
# Load existing classifications
# -----------------------------

results = []

if os.path.exists(OUTPUT_FILE):
    with open(
        OUTPUT_FILE,
        encoding="utf-8-sig",
        newline=""
    ) as file:
        results = list(csv.DictReader(file))

    print(f"Loaded {len(results)} previous classifications.")

# Revalidate existing recommendations without API calls
for result in results:
    impact = int(result["impact"])
    significance = int(result["significance"])
    evidence = int(result["evidence"])

    total = impact + significance + evidence

    
    eligible = (
        total >= 12
        and impact >= 3
        and evidence >= 4
        and (
            (
                result["story_type"] == "achieved progress"
                and significance >= 3
            )
            or (
                result["story_type"] == "credible breakthrough"
                and significance >= 4
            )
        )
    )


    result["total"] = total

    if result["recommendation"] == "INCLUDE" and not eligible:
        result["recommendation"] = "REVIEW"

completed_urls = {
    result["url"] for result in results
}

# Save any corrections to existing classifications
save_results(results)

# -----------------------------
# AI editorial instructions
# -----------------------------



INSTRUCTIONS = """
You are the assistant editor of The Other Headlines,
a publication covering meaningful positive progress
and exciting, significant discoveries.

Assess ONLY the supplied headline and description.
Do not invent evidence, outcomes or significance.

There are TWO editorial pathways.

PATHWAY 1: ACHIEVED PROGRESS

A meaningful positive development that has already
delivered demonstrable real-world benefits.

Examples include:
- Successful disease elimination
- Measurable reductions in poverty or mortality
- Major successful environmental restoration
- Proven improvements in technology or infrastructure

Assess:
- Demonstrated impact
- Significance
- Strength of evidence

PATHWAY 2: CREDIBLE BREAKTHROUGH

A genuinely important scientific, medical, historical
or technological discovery.

A breakthrough does NOT need immediate practical
applications or demonstrated real-world benefits.

It must, however:
- Represent a substantial advance in knowledge
- Have clear novelty or exceptional significance
- Be supported by robust evidence
- Go meaningfully beyond routine research

Examples include:
- A major discovery about the early universe
- A fundamentally new biological mechanism
- A major archaeological discovery
- A transformative advance in scientific understanding

Do not treat every published study as a breakthrough.

SCORING

Impact (0-5):
For achieved progress, assess demonstrated benefits.
For discoveries, assess the importance of the advance
to knowledge or scientific understanding.

5 = Transformative impact or fundamental discovery
4 = Major impact or substantial knowledge advance
3 = Meaningful impact or important discovery
2 = Limited or preliminary impact
1 = Minor or speculative
0 = No identifiable positive impact


Significance (0-5):

5 = Transformative or field-changing advance
that fundamentally alters understanding or capability.

4 = Major advance with clearly established importance
beyond a narrow research speciality, or a landmark
discovery of exceptional scientific importance.

3 = Meaningful advance with identifiable broader
implications, but not a major breakthrough.

2 = Incremental or narrowly significant contribution,
including most new measurements, observations and
improvements within an established research field.

1 = Routine finding with limited wider importance.

0 = No significant development.

IMPORTANT:
Novelty alone does not establish significance.

Do not award a significance score of 4 or 5 merely
because a discovery is described as a first, new,
unprecedented or important.

The supplied evidence must explain what substantial
understanding or capability has changed and why
that change matters.

When broader significance is merely asserted or
speculated about, score conservatively.


Evidence (0-5):
5 = Strong independently corroborated evidence
4 = Robust evidence clearly supported by supplied text
3 = Credible but with important uncertainties
2 = Preliminary or limited evidence
1 = Weak evidence
0 = No evidence provided

Do not automatically award high evidence scores
because a university or journal is mentioned.

DECISION RULES

INCLUDE achieved progress only when:
- Impact >= 3
- Significance >= 3
- Evidence >= 4
- Total score >= 12

INCLUDE credible breakthrough only when:
- Impact >= 3
- Significance >= 4
- Evidence >= 4
- Total score >= 12


REVIEW when:
- There is a specific, credible reason to believe the
  story could meet one of the INCLUDE pathways
- The supplied text suggests a substantial advance,
  but important evidence or context is missing
- Further verification could realistically change
  the recommendation to INCLUDE

Do NOT use REVIEW simply because a study is new,
interesting, credible or scientifically valid.

EXCLUDE when:
- Research is routine, incremental or narrowly
  significant within a specialist field
- A discovery is novel but its broader importance
  is not established
- The story primarily describes a problem, warning
  or negative trend without meaningful progress
- Claims are speculative or unsupported
- No meaningful progress or major discovery
  is demonstrated
- The story is primarily opinion or commentary

IMPORTANT EDITORIAL PRINCIPLE

The Other Headlines is a selective publication,
not a comprehensive science news aggregator.

A credible scientific discovery is not automatically
a significant breakthrough.

When the supplied evidence does not establish
substantial significance, prefer EXCLUDE over REVIEW
unless there is a concrete reason further investigation
could establish that significance.

Be selective and avoid inflated scores.

Return ONLY a valid JSON object containing:
impact, significance, evidence, story_type,
recommendation, explanation.

Scores must be integers from 0 to 5.

story_type must be one of:
- achieved progress
- credible breakthrough
- other

recommendation must be one of:
- INCLUDE
- REVIEW
- EXCLUDE

Explain briefly what was achieved or discovered,
why it matters and what remains uncertain.
"""


# -----------------------------
# Classify new articles
# -----------------------------

new_articles_processed = 0

for index, article in enumerate(articles, start=1):

    url = article["url"]

    # Skip articles already classified
    if url in completed_urls:
        print(
            f"Skipping {index}/{len(articles)}: "
            "already classified"
        )
        continue

    # Stop after 10 NEW classifications
    if new_articles_processed >= MAX_NEW_ARTICLES:
        print("Test limit reached. Stopping.")
        break

    print(
        f"Classifying {index}/{len(articles)}: "
        f"{article['title'][:65]}",
        flush=True
    )

    try:
        response = client.responses.create(
            model=MODEL,
            instructions=INSTRUCTIONS,
            input=(
                "Return your assessment as a valid JSON object.\n\n"
                f"Title: {article['title']}\n"
                f"Description: {article['description']}"
            ),
            text={
                "format": {
                    "type": "json_object"
                }
            },
            max_output_tokens=400
        )

        result = json.loads(response.output_text)

        impact = int(result["impact"])
        significance = int(result["significance"])
        evidence = int(result["evidence"])

        if not all(
            0 <= score <= 5
            for score in [impact, significance, evidence]
        ):
            raise ValueError("AI returned an invalid score.")

        total = impact + significance + evidence

        story_type = result["story_type"].strip().lower()
        recommendation = result["recommendation"].strip().upper()

        valid_types = [
            "achieved progress",
            "credible breakthrough",
            "other"
        ]

        if story_type not in valid_types:
            raise ValueError("AI returned an invalid story type.")

        if recommendation not in [
            "INCLUDE", "REVIEW", "EXCLUDE"
        ]:
            raise ValueError("AI returned an invalid recommendation.")

        
        eligible = (
            total >= 12
            and impact >= 3
            and evidence >= 4
            and (
                (
                    story_type == "achieved progress"
                    and significance >= 3
                )
                or (
                    story_type == "credible breakthrough"
                    and significance >= 4
                )
            )
        )


        if recommendation == "INCLUDE" and not eligible:
            recommendation = "REVIEW"

        results.append({
            **article,
            "impact": impact,
            "significance": significance,
            "evidence": evidence,
            "total": total,
            "story_type": story_type,
            "recommendation": recommendation,
            "explanation": result["explanation"]
        })

        completed_urls.add(url)
        new_articles_processed += 1

        # Save after every successful classification
        save_results(results)

    except Exception as error:
        print(f"ERROR on article {index}: {error}")
        print("Previous classifications have been preserved.")
        print("You can rerun the script to retry this article.")
        break

    time.sleep(0.2)

# -----------------------------
# Summary
# -----------------------------

print(f"\nSaved {len(results)} classifications to {OUTPUT_FILE}")

for decision in ["INCLUDE", "REVIEW", "EXCLUDE"]:
    count = sum(
        1 for result in results
        if result["recommendation"] == decision
    )
    print(f"{decision}: {count}")

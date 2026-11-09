
import csv
import os
import streamlit as st

ARTICLES_FILE = "classified_news.csv"
DECISIONS_FILE = "editorial_decisions.csv"

st.set_page_config(
    page_title="The Other Headlines | Editor",
    page_icon="📰",
    layout="wide"
)

st.title("The Other Headlines")
st.caption("Private editorial dashboard")

# Load articles
with open(ARTICLES_FILE, encoding="utf-8-sig", newline="") as file:
    articles = list(csv.DictReader(file))

# Load previously saved decisions
decisions = {}

if os.path.exists(DECISIONS_FILE):
    with open(DECISIONS_FILE, encoding="utf-8-sig", newline="") as file:
        for row in csv.DictReader(file):
            decisions[row["url"]] = row["decision"]


def save_decision(url, decision):
    decisions[url] = decision

    with open(
        DECISIONS_FILE, "w",
        encoding="utf-8-sig", newline=""
    ) as file:
        writer = csv.DictWriter(
            file, fieldnames=["url", "decision"]
        )
        writer.writeheader()

        for article_url, status in decisions.items():
            writer.writerow({
                "url": article_url,
                "decision": status
            })


# Editorial overview
pending = sum(
    1 for a in articles
    if decisions.get(a["url"], "Pending") == "Pending"
)
approved = sum(
    1 for a in articles
    if decisions.get(a["url"]) == "Approved"
)
rejected = sum(
    1 for a in articles
    if decisions.get(a["url"]) == "Rejected"
)
held = sum(
    1 for a in articles
    if decisions.get(a["url"]) == "Held"
)

c1, c2, c3, c4 = st.columns(4)

c1.metric("Pending", pending)
c2.metric("Approved", approved)
c3.metric("Rejected", rejected)
c4.metric("Held", held)

st.divider()


# Editorial inbox filters
st.subheader("Editorial inbox")

view = st.selectbox(
    "Show articles",
    [
        "AI shortlist",
        "All pending",
        "Approved",
        "Rejected",
        "Held",
        "All articles"
    ]
)

if view == "AI shortlist":
    filtered = [
        article for article in articles
        if article["recommendation"] in ["INCLUDE", "REVIEW"]
        and decisions.get(article["url"], "Pending") == "Pending"
    ]

elif view == "All pending":
    filtered = [
        article for article in articles
        if decisions.get(article["url"], "Pending") == "Pending"
    ]

elif view == "All articles":
    filtered = articles

else:
    filtered = [
        article for article in articles
        if decisions.get(article["url"], "Pending") == view
    ]
# Filter articles by publisher
publishers = sorted(set(
    article["source"] for article in articles
))

selected_publisher = st.selectbox(
    "Filter by publisher",
    ["All publishers"] + publishers
)

if selected_publisher != "All publishers":
    filtered = [
        article for article in filtered
        if article["source"] == selected_publisher
    ]
# Put the strongest AI candidates first
filtered = sorted(
    filtered,
    key=lambda article: int(article["total"]),
    reverse=True
)

st.write(f"Showing {len(filtered)} articles")


# Editorial review cards
for article in filtered:
    with st.container(border=True):
        st.subheader(article["title"])

        st.caption(
            f"{article['source']} | {article['category']}"
        )

        st.write(article["description"])

        st.markdown("#### AI editorial assessment")

        recommendation = article["recommendation"]

        if recommendation == "INCLUDE":
            st.success("AI recommendation: INCLUDE")
        elif recommendation == "REVIEW":
            st.warning("AI recommendation: REVIEW")
        else:
            st.info("AI recommendation: EXCLUDE")

        score1, score2, score3, score4 = st.columns(4)

        score1.metric("Positive impact", article["impact"] + "/5")
        score2.metric("Significance", article["significance"] + "/5")
        score3.metric("Evidence", article["evidence"] + "/5")
        score4.metric("Total", article["total"] + "/15")

        st.caption(f"Story type: {article['story_type']}")
        st.write(article["explanation"])


        st.link_button(
            "Read original article",
            article["url"]
        )

        current_status = decisions.get(
            article["url"], "Pending"
        )

        st.write(f"**Status:** {current_status}")

        col1, col2, col3 = st.columns(3)

        if col1.button(
            "Approve",
            key=f"approve_{article['url']}"
        ):
            save_decision(article["url"], "Approved")
            st.rerun()

        if col2.button(
            "Reject",
            key=f"reject_{article['url']}"
        ):
            save_decision(article["url"], "Rejected")
            st.rerun()

        if col3.button(
            "Hold",
            key=f"hold_{article['url']}"
        ):
            save_decision(article["url"], "Held")
            st.rerun()

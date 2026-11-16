"""Locust scenario: signed-in caregivers using the app (#224).

Each simulated caregiver is one of the users made by setup_users.py (token,
privacy notice agreed, one child). Between actions they pause 3-10 seconds,
like a person reading a screen. The weights follow everyday use: opening
Today's ideas most, then Explore and the tracker, sometimes asking for new
ideas, giving feedback and looking at the options it offers.

Set LOADTEST_USERS to the JSON file written by setup_users.py.
"""

import itertools
import json
import os
import random

from locust import HttpUser, between, task

USERS = json.loads(open(os.environ["LOADTEST_USERS"], encoding="utf-8").read())
NEXT = itertools.cycle(USERS)
SEARCHES = [
    "messy play with water",
    "songs and rhymes",
    "tummy time",
    "first words",
    "playing with balls",
    "calm bedtime",
    "colours and shapes",
    "sharing feelings in pregnancy",
]
FEEDBACK = [
    {"outcome": "went_well", "interest": "happy", "rating": 5},
    {"outcome": "partly", "issues": ["no_time"], "interest": "okay"},
    {"outcome": "didnt_work", "issues": ["too_hard"], "interest": "bored"},
]


def recommendation_ids(response):
    try:
        data = response.json()
    except ValueError:
        return []
    items = data.get("recommendations", data) if isinstance(data, dict) else data
    return [r["id"] for r in items if isinstance(r, dict) and "id" in r]


class Caregiver(HttpUser):
    wait_time = between(3, 10)

    def on_start(self):
        account = next(NEXT)
        self.client.headers["Authorization"] = f"Token {account['token']}"
        self.child = account["child"]
        self.ideas = []

    def _today(self):
        with self.client.get(
            f"/api/children/{self.child}/recommendations/",
            name="GET recommendations (Today)",
            catch_response=True,
        ) as r:
            self.ideas = recommendation_ids(r)
            r.success() if r.ok else r.failure(r.status_code)
        if not self.ideas:  # the app asks for a first batch when there's none
            self._generate()

    def _generate(self):
        with self.client.post(
            f"/api/children/{self.child}/recommendations/",
            name="POST recommendations (generate)",
            catch_response=True,
        ) as r:
            self.ideas = recommendation_ids(r) or self.ideas
            r.success() if r.ok else r.failure(r.status_code)

    @task(10)
    def today(self):
        self._today()

    @task(2)
    def new_ideas(self):
        self._generate()

    @task(3)
    def explore(self):
        self.client.get(
            f"/api/children/{self.child}/activities/",
            name="GET Explore (browse)",
        )

    @task(3)
    def explore_search(self):
        self.client.get(
            f"/api/children/{self.child}/activities/",
            params={"q": random.choice(SEARCHES)},
            name="GET Explore (search, SBERT)",
        )

    @task(3)
    def tracker(self):
        self.client.get(
            f"/api/children/{self.child}/tracker/", name="GET milestone tracker"
        )

    @task(2)
    def milestone_search(self):
        self.client.get(
            "/api/reference-milestones/",
            params={"search": random.choice(["walk", "words", "smile", "sit"])},
            name="GET milestone search",
        )

    @task(1)
    def feedback_and_options(self):
        if not self.ideas:
            self._today()
        if not self.ideas:
            return
        rec = random.choice(self.ideas)
        self.client.put(
            f"/api/recommendations/{rec}/feedback/",
            json=random.choice(FEEDBACK),
            name="PUT feedback",
        )
        self.client.get(
            f"/api/recommendations/{rec}/options/", name="GET options after feedback"
        )

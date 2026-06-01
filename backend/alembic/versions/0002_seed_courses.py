"""seed UATX course catalog

Revision ID: 0002_seed_courses
Revises: 0001_initial
Create Date: 2026-06-01

Seeds the courses table with the UATX 2025-2026 academic catalog:
Intellectual Foundations (INF), the three Centers (ALT, EPH, STM), Polaris (POL),
and the catalog's cross-disciplinary Special Topics (EDU). 167 rows total.

Idempotent via ON CONFLICT (code) DO NOTHING so re-running against a partially
seeded DB is safe. Downgrade only deletes rows whose code is in this catalog,
so a teammate's manually-added course would survive a downgrade.
"""
from __future__ import annotations

import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002_seed_courses"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Source: UATX 2025-2026 Academic Catalog → Course Descriptions section.
# Ordered by prefix then course number for stable diffs.
COURSES: tuple[tuple[str, str], ...] = (
    # Intellectual Foundations
    ("INF 1100", "Chaos and Civilization"),
    ("INF 1110", "Knowing, Doing, Making, Wisdom"),
    ("INF 1130", "Quantitative Reasoning I"),
    ("INF 1200", "The Beginning of Politics"),
    ("INF 1210", "Writing and the English Language"),
    ("INF 1220", "Quantitative Reasoning II"),
    ("INF 1300", "Christianity and Islam, Europe and the East"),
    ("INF 1320", "Intellectual Foundations of Economics"),
    ("INF 1330", "Foundations of Science I"),
    ("INF 2100", "The Uses and Abuses of Technology"),
    ("INF 2110", "Foundations of Science II"),
    ("INF 2120", "Modernity and the West"),
    ("INF 2200", "The American Experiment"),
    ("INF 2210", "Mortality and Meaning in Art and Music"),
    ("INF 2300", "Ideological Experiments of the 20th Century"),
    # Center for Arts and Letters
    ("ALT 1010", "The Rise and Fall of Ancient Rome"),
    ("ALT 1020", "Crown, Cathedral, and Crusade"),
    ("ALT 1030", "The Renaissance and the Reformation"),
    ("ALT 1040", "Reason and Revolution"),
    ("ALT 1050", "Romanticism and Realism"),
    ("ALT 1060", "Decadence, Modernism, and Postmodernism"),
    ("ALT 1100", "Faith, Reason, and Science I: Medieval, Contemporary, and Early Modern"),
    ("ALT 1120", "Faith, Reason, and Science II: Modern and Contemporary"),
    ("ALT 1140", "Work, Leisure, and the Good Life"),
    ("ALT 1160", "The Sublime and the Beautiful I: Classical, Medieval, and Early Modern"),
    ("ALT 1180", "The Sublime and the Beautiful II: Modern and Contemporary"),
    ("ALT 1200", "The Theory Wars"),
    ("ALT 1220", "Postmodernism and the End of History"),
    ("ALT 1240", "Colonialism, Decolonization, and Postcolonialism"),
    ("ALT 1260", "Critical Theory"),
    ("ALT 1300", "Tragedy"),
    ("ALT 1400", "Comedy"),
    ("ALT 1500", "Medieval Literature"),
    ("ALT 1600", "Early Modern Literature"),
    ("ALT 1800", "Romantic and Victorian Literature"),
    ("ALT 1900", "Modern and Contemporary Literature"),
    ("ALT 1950", "American Literature"),
    ("ALT 2000", "Classical Ethics I: Plato, Aristotle, and the Hellenistic Philosophers"),
    ("ALT 2020", "Classical Ethics II: Cicero, Seneca, and Plutarch"),
    ("ALT 2100", "Classical Political Philosophy"),
    ("ALT 2200", "Medieval and Early Modern Ethics"),
    ("ALT 2300", "Medieval and Early Modern Political Philosophy"),
    ("ALT 2400", "Modern and Contemporary Political Philosophy"),
    ("ALT 2500", "Self and Other: The Ethics and Politics of Recognition"),
    ("ALT 2600", "Methodological Approaches to Political Philosophy"),
    ("ALT 2700", "Introduction to the History and Culture of China"),
    ("ALT 3000", "Plato, Republic"),
    ("ALT 3160", "Chaucer, The Canterbury Tales"),
    ("ALT 3200", "Socrates and Montaigne"),
    ("ALT 3220", "Machiavelli, Discourses on Livy"),
    ("ALT 3300", "Shakespeare: Tragedies and Romances"),
    ("ALT 3310", "Dante, Inferno"),
    ("ALT 3315", "Dante, Purgatorio"),
    ("ALT 3320", "Dante, Paradiso"),
    ("ALT 3330", "Shakespeare: Comedies and Problem Plays"),
    ("ALT 3340", "Shakespeare: The Roman Plays"),
    ("ALT 3360", "Shakespeare: The History Plays"),
    ("ALT 3400", "Milton, Paradise Lost"),
    ("ALT 3500", "Austen"),
    ("ALT 3600", "Montesquieu, The Spirit of the Laws"),
    ("ALT 3620", "Tocqueville, Democracy in America"),
    ("ALT 3700", "Kant and Hegel"),
    ("ALT 3720", "Kierkegaard"),
    ("ALT 3740", "Melville, Moby Dick"),
    ("ALT 3760", "Dostoyevsky"),
    ("ALT 3780", "Nietzsche"),
    ("ALT 3800", "Arendt and Strauss"),
    ("ALT 3850", "MacIntyre"),
    ("ALT 3900", "Joyce"),
    ("ALT 4000", "Writing Studio"),
    ("ALT 4100", "Special Topics in Literature Pre 1800"),
    ("ALT 4110", "Special Topics in Literature Pre 1800"),
    ("ALT 4200", "Special Topics in Literature Post 1800"),
    ("ALT 4210", "Special Topics in Literature Post 1800"),
    ("ALT 4300", "Independent Study Pre 1800"),
    ("ALT 4310", "Independent Study Pre 1800"),
    ("ALT 4400", "Independent Study Post 1800"),
    ("ALT 4410", "Independent Study Post 1800"),
    ("ALT 4500", "Special Topics in Ethics and Politics"),
    ("ALT 4510", "Special Topics in Ethics and Politics"),
    ("ALT 4600", "Independent Study in Ethics and Politics"),
    ("ALT 4610", "Independent Study in Ethics and Politics"),
    ("ALT 4700", "Special Topics in Film"),
    ("ALT 4710", "Special Topics in Film"),
    # Cross-disciplinary Special Topics
    ("EDU 2900", "Special Topics"),
    ("EDU 2910", "Special Topics"),
    ("EDU 2920", "Special Topics"),
    ("EDU 4900", "Special Topics"),
    ("EDU 4910", "Special Topics"),
    ("EDU 4920", "Special Topics"),
    # Center for Economics, Politics, and History
    ("EPH 1100", "Analytical Tools for Economics and Political Science"),
    ("EPH 1200", "Introduction to American Politics"),
    ("EPH 1300", "Foundations of Microeconomics I"),
    ("EPH 1400", "Foundations of Macroeconomics I"),
    ("EPH 1500", "History, Historiography, and the Philosophy of History"),
    ("EPH 1600", "American Legal System"),
    ("EPH 2000", "Introduction to Applied Econometrics"),
    ("EPH 2010", "Data Science for Social Scientists"),
    ("EPH 2100", "Political Theories of Democracy"),
    ("EPH 2200", "Foundations of Political Science I"),
    ("EPH 2300", "Foundations of Political Science II"),
    ("EPH 2400", "Philosophers of Political Economy"),
    ("EPH 2600", "The Changing Structure of Civilization: Tribes, City States, Empires, & Nations"),
    ("EPH 2900", "Special Topics"),
    ("EPH 2910", "Special Topics"),
    ("EPH 2920", "Special Topics"),
    ("EPH 3010", "Foundations of Microeconomics II"),
    ("EPH 3020", "Foundations of Macroeconomics II"),
    ("EPH 3030", "Corporate Finance, Accounting, and Business Planning"),
    ("EPH 3040", "Introduction to World Economic and Political History"),
    ("EPH 3050", "Public Choice"),
    ("EPH 3060", "Advanced Topics in Panel Data Analysis"),
    ("EPH 3070", "Advanced Topics in Time Series Analysis"),
    ("EPH 3080", "Advanced Topics in Data Science for Social Sciences"),
    ("EPH 3090", "Advanced Microeconomics"),
    ("EPH 3100", "Advanced Macroeconomics, Public Finance and Growth Theory"),
    ("EPH 3110", "Advanced Topics in American Political History"),
    ("EPH 3120", "Voting, Political Parties and Electoral Politics"),
    ("EPH 3130", "Business Structures and Governance"),
    ("EPH 3140", "Capitalism, Its Critics, and the History of Growth, Poverty, and Inequality"),
    ("EPH 3150", "How Political Revolutions Happen"),
    ("EPH 3160", "Advanced Topics in American Economic History"),
    ("EPH 3170", "Advanced Topics in World Economic History"),
    ("EPH 3180", "Property Rights and Their Economic and Political Consequences"),
    ("EPH 3190", "International Trade"),
    ("EPH 3200", "Rationality and its Limits: From Becker to Thaler and Beyond"),
    ("EPH 3210", "International Finance"),
    ("EPH 3220", "Money, Banking, and the Financial System"),
    ("EPH 3230", "Finance and Economic Development"),
    ("EPH 3240", "International Relations"),
    ("EPH 3250", "Entrepreneurship and Entrepreneurial Finance"),
    ("EPH 3900", "Special Topics"),
    ("EPH 4000", "Independent Study"),
    ("EPH 4900", "Special Topics"),
    ("EPH 4910", "Special Topics"),
    ("EPH 4920", "Special Topics"),
    # Center for Science, Technology, Engineering, and Mathematics
    ("STM 1001", "Calculus I"),
    ("STM 1002", "Calculus II"),
    ("STM 1004", "Differential Equations"),
    ("STM 1005", "Discrete Mathematics"),
    ("STM 2101", "Probability"),
    ("STM 2102", "Statistics"),
    ("STM 2103", "Linear Algebra"),
    ("STM 2104", "Linear Optimization"),
    ("STM 2300", "Data Wrangling and Visualization"),
    ("STM 2301", "Programming I"),
    ("STM 2302", "Programming II"),
    ("STM 2501", "Physics I"),
    ("STM 2502", "Physics II"),
    ("STM 3301", "Data Structures and Scalability"),
    ("STM 3302", "Data Storage"),
    ("STM 3303", "Machine Learning"),
    ("STM 3304", "Computer Architecture and Organization"),
    ("STM 3900", "Special Topics"),
    ("STM 3910", "Special Topics"),
    ("STM 3915", "Special Topics"),
    ("STM 4101", "Nonparametric Statistics"),
    ("STM 4102", "Statistical Learning"),
    ("STM 4301", "Human Data Interaction"),
    ("STM 4302", "Big Data Computing"),
    ("STM 4303", "Computer Algorithms"),
    # Polaris Project
    ("POL 1110", "Polaris Ideas"),
    ("POL 2100", "Polaris Inspirations"),
    ("POL 2110", "Polaris Frame"),
    ("POL 3100", "Polaris Pitch"),
    ("POL 3110", "Polaris Build"),
    ("POL 4150", "Polaris Launch"),
)


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            "INSERT INTO courses (id, code, title) "
            "VALUES (:id, :code, :title) "
            "ON CONFLICT (code) DO NOTHING"
        ),
        [{"id": uuid.uuid4(), "code": code, "title": title} for code, title in COURSES],
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text("DELETE FROM courses WHERE code = :code"),
        [{"code": code} for code, _ in COURSES],
    )

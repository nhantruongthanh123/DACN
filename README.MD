# Student Academic Risk Prediction and Synthetic Data Generation

This repository contains two separate components: a notebook-based early-warning
workflow that predicts course failure risk from assessment and learning activity,
and a standalone synthetic grade generator in `synthetic_data/`. The synthetic
grade output is not currently wired into the model-training notebooks.

The intended system is designed to answer two practical questions:

1. **Who is at risk?** Use a predictive model to flag students early enough for
	an instructor or support team to intervene.
2. **Why is the student at risk, and what could help?** Use explainable AI to
	identify influential factors and counterfactual analysis to describe
	plausible changes that could move a prediction to the lower-risk class.

## Repository Structure

```text
.
├── README.MD
├── requirements.txt
├── models/
│   └── xgboost_risk_model.json
├── notebooks/
│   ├── 01_data_explore.ipynb         # Feature preparation and model training
│   ├── 02_test_model.ipynb           # Single-record prediction example
│   └── 03_xai_shap.ipynb             # SHAP explanations
└── synthetic_data/
	├── input/                        # Inputs for the synthetic grade generator
	├── generated/                    # Generated CSV outputs
	├── config.json
	└── generate_dataset.py
```

## Getting Started

Follow these steps to set up the project environment and run the data processing pipeline locally.

### 1. Set up the Python Environment
It is highly recommended to use a virtual environment. Create one and install the required libraries using the `requirements.txt` file:

```bash
# Create a virtual environment named .venv
python -m venv .venv

# Activate the virtual environment
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

# Install all required dependencies
pip install -r requirements.txt
```

### 2. Prepare model input data

The current checkout does not contain the source CSVs or a `data/` directory.
The first notebook reads `studentInfo.csv`, `studentAssessment.csv`,
`assessments.csv`, `studentVle.csv`, and `vle.csv`; their relative paths are
defined in its first cell. Provide compatible files and update those paths if
needed before running the notebook. Also create `data/processed/`, where the
prepared feature table is written. These notebook inputs are separate from the
CSVs in `synthetic_data/input/`.

### 3. Prepare features and train the model

Open `notebooks/01_data_explore.ipynb` and run its cells in order. The first cell
builds `data/processed/df_final_prepared.csv` using activity and assessment data
through day 60. It labels `Fail` and `Withdrawn` as risk, and `Pass` and
`Distinction` as not at risk. Features include prior attempts, studied credits,
early coursework scores and submissions, late days, total and forum clicks,
active days, and click momentum.

The second cell splits the data into stratified 80/20 train and test sets,
trains an `XGBClassifier`, prints a classification report and ROC-AUC, and saves
the model to `models/xgboost_risk_model.json`.

- `notebooks/02_test_model.ipynb` loads the saved model and demonstrates a
	prediction from a manually supplied ten-feature student record.
- `notebooks/03_xai_shap.ipynb` computes SHAP values, shows a summary plot, and
	creates a waterfall explanation for a selected row (default index: 99).

`shap` is not currently listed in `requirements.txt`; install it separately
before running the explainability notebook:

```bash
pip install shap
```

Run notebooks from the `notebooks/` directory so their relative data and model
paths resolve as written. The SHAP example requires at least 100 prepared rows
unless `student_index` is changed.


# Synthetic grade generation

The `synthetic_data/` directory contains a standalone Python generator for simulated
student course attempts. It combines the synthetic student, curriculum,
assessment, prerequisite, and class tables with configurable ability and score
distributions. Its generated grade records are not real student records and are
not used by the early-warning notebooks above.

## Run

Install dependencies and run the generator from the repository root:

```bash
pip install -r requirements.txt
python synthetic_data/generate_dataset.py --input synthetic_data/input --output synthetic_data/generated --config synthetic_data/config.json
```

Optional arguments:

- `--input`: directory containing the five source CSV files (default: `input`).
- `--output`: directory for generated CSV files (default: `generated`; created if
	it does not exist).
- `--config`: JSON simulation configuration (default: `config.json`).
- `--limit-students N`: process only the first `N` rows in `student.csv`, useful
	for a quick test run. `N` must be greater than zero.

The random generator uses `seed` from the config. With the same inputs,
configuration, and seed, the generated results are reproducible.

## Input files

The default input files are in `synthetic_data/input/` (or pass another
directory with `--input`):

| File | Required columns used by the generator | Purpose |
| --- | --- | --- |
| `student.csv` | `user_id` | One row per student. The first two characters of `user_id` are used as the cohort when building term codes. |
| `course.csv` | `course_code`, `course_name`, `credits`, `course_group` | Course metadata, credit load, and elective group. |
| `assessment.csv` | `course_id`, `quiz`, `lab`, `btl`, `giua_ky`, `cuoi_ky` | Assessment-component weights for each course. Weights are percentages and should total 100 for a conventional weighted score. |
| `course_prerequisite.csv` | `course_code`, `related_course_code` | Prerequisite edges: `related_course_code` must be passed before `course_code` can be scheduled. `relation_type` may be present but is not used by this generator. |
| `class.csv` | `id`, `course_id` | Available class sections. IDs are expected to begin with a term code such as `231`; the generator uses a matching section when available. |

The IDs must agree across files: `course.csv.course_code` is matched to
`assessment.csv.course_id`, `course_prerequisite.csv`, and
`class.csv.course_id`. Keep every course code and user ID as a string to avoid
losing leading zeros.

## Generation workflow

For each student, the script:

1. Samples an ability group using the configured `proportion`, then samples a
	 latent ability from that group's normal distribution. It also samples one
	 `personality_profile` for the student; the profile adds score offsets and
	 controls score variability across all of that student's courses.
2. Builds an individual curriculum from every `NON_ELECTIVE` course, plus 5
	 courses from `ELECTIVE_GROUP_C`, 1 from `ELECTIVE_GROUP_A`, 1 from
	 `ELECTIVE_GROUP_B`, and 1 from `ELECTIVE_MANAGEMENT`. Electives are sampled
	 without replacement. If a selected course has prerequisites, the full
	 prerequisite chain is added to the curriculum.
3. Schedules courses over up to `max_terms` terms, starting from the cohort in
	 `user_id` (for example, cohort `23` produces terms `231`, `232`, `233`, then
	 `241`). A course is eligible only after all its prerequisites have passed.
	 Each term's greedy scheduler prioritizes lower-credit courses and does not
	 exceed `max_credits_per_term`. If nothing is eligible, the student simply
	 has no attempt recorded for that term.
4. Selects the first matching class section for the course and term, sorted by
	 class ID. If no section exists for that term, it falls back to the first
	 available section for the course; if the course has no section at all,
	 `class_id` is empty.
5. Generates the assessment components and weighted final score, records a
	 `PASS` or `FAIL`, and keeps failed courses eligible for a later term until
	 they pass or reach `max_retakes` attempts. Each attempt is generated with a
	 new random draw. A course that reaches the attempt limit while still
	 failing is no longer scheduled, so dependent courses may remain blocked.

The selected curriculum and the courses actually attempted can therefore
differ: term limits, credit limits, prerequisite failures, and exhausted
retakes can prevent some selected courses from being taken.

## Score model

For each student-course attempt, the script first estimates course difficulty
from the course-group modifier, a small credit-based adjustment, and random
variation. For each assessment component with a positive weight, it samples a
score around the student's ability minus course difficulty, adjusted by the
student's personality and a shared course-level shock. Component-specific
noise is configured separately. Scores are clipped to the 0-10 range; a
component with a zero weight is assigned zero.

The final score is the weighted sum of the generated components using the
weights in `assessment.csv`. A score at or above `pass_score` passes unless a
separate random failure event triggers. That event uses the student's
configured `fail_rate` (reduced by 0.05, with a floor of zero); when it turns a
passing score into a failure, the score is lowered below the pass threshold so
the score and status remain consistent. Letter grades and 4.0-scale grade
points are then derived from the final score.

## Configuration

`synthetic_data/config.json` controls the simulation:

- `seed`: random seed for reproducibility.
- `max_terms`: maximum number of terms simulated per student.
- `max_credits_per_term`: upper credit limit used by the course scheduler.
- `pass_score`: minimum final score for passing before the random failure event.
- `max_retakes`: maximum total attempts for one course, including its first
	attempt. For example, `2` means one initial attempt and at most one retry.
- `ability_groups`: each group's population proportion, ability mean and
	standard deviation, optional ability bounds, and failure tendency.
- `personality_profiles`: population proportions, overall and component score
	offsets, and a multiplier for component noise.
- `course_group_difficulty`: difficulty adjustment by curriculum group.
- `component_noise`: score variability for `quiz`, `lab`, `btl`, `giua_ky`, and
	`cuoi_ky`.

Group and personality proportions are normalized by the script before sampling;
they do not need to sum to exactly 1. `min_credits_per_term` may appear in the
config but is not currently used by `generate_dataset.py`.

## Output files

The output directory contains:

- `student_course_attempts.csv`: one row per attempted course, including
	student/cohort, sampled ability group and personality, term, course metadata,
	class, attempt number, component scores and weights, final score, letter
	grade, 4.0-scale grade, and pass/fail status.
- `class_assessments.csv`: a copy of the attempt-level records, with the same
	columns as `student_course_attempts.csv`.
- `student_profile.csv`: one row per processed student. Includes ability and
	personality, number of passed courses, credit-weighted GPA over passed
	credit-bearing courses, retake/improvement credit totals, and derived
	academic classification. A student with no passed credit-bearing courses
	receives a GPA of 0.
- `score_distribution.csv`: counts and proportions of attempted final scores
	in the ranges `0-2`, `2-4`, `4-5`, `5-6`, `6-7`, `7-8`, `8-9`, and `9-10`.

The configured proportions, ability distributions, difficulty adjustments, and
failure rates are simulation assumptions, not measured HCMUT statistics.
`DROPOUT` is an ability-group label that affects score and failure behavior; the
generator does not assign final graduation or dropout outcomes.
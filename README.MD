# Explainable and Counterfactual AI for Student Academic Early Warning

This project explores an early-warning system for identifying students who may
be at risk of failing or withdrawing from a course. It uses the Open University
Learning Analytics Dataset (OULAD) and combines academic activity with virtual
learning environment (VLE) interaction data.

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
├── data/
│   ├── oulad/                         # OULAD source tables
│   │   ├── assessments.csv           # Assessment metadata
│   │   ├── courses.csv               # Module and presentation metadata
│   │   ├── studentAssessment.csv     # Student assessment results
│   │   ├── studentInfo.csv           # Student demographics and outcomes
│   │   ├── studentRegistration.csv   # Registration and withdrawal dates
│   │   ├── studentVle.csv            # Student VLE interactions
│   │   └── vle.csv                   # VLE activity metadata
│   └── processed/
│       └── df_final_prepared.csv     # Model-ready early-warning features
├── models/
│   └── xgboost_model.json            # XGBoost model artifact
└── notebooks/
│       └── 01_data_explore.ipynb         # Preparation and exploratory analysis
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

### 2. Download the OULAD Dataset
```bash
Download the data in oulad and place in data/oulad
```

### 3. Run the Processing Notebook
```bash
Open notebooks/01_data_explore.ipynb using Jupyter Notebook, JupyterLab, or VS Code.

Run first block code to extract data into data/processed/df_final_prepared.csv 

Run second block code to build model base on features: num_of_prev_attempts, studied_credits, is_Risk, Avg_Coursework_Score,  Total_late_days, Submitted_assignments,First_Assessment_Score, Total_clicks, Active_days, Forum_clicks, Click_Momentum 


```
## Dataset Reference

The project uses the Open University Learning Analytics Dataset (OULAD),
published by the Open University Learning Analytics Dataset project:

<https://analyse.kmi.open.ac.uk/open_dataset>

Check the dataset's terms and citation requirements before redistributing the
source files or publishing derived results.



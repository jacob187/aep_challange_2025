# AEP Dynamic Grid Challenge

This repository contains a Streamlit application for analyzing transmission line stress under varying atmospheric conditions using IEEE-738 thermal rating calculations. All data is from

## Getting Started

Follow these instructions to set up and run the application.

### Prerequisites

Ensure you have Python 3.8+ installed.

### Installation

1.  Clone the repository:

    ```bash
    git clone https://github.com/your_username/aep_challange_2025.git
    cd aep_challange_2025
    ```

2.  Create a virtual environment and activate it (recommended):

    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

3.  Install the required Python packages:

    ```bash
    pip install -r requirements.txt
    ```

### Running the Streamlit App

To start the application, navigate to the project root directory and run:

```bash
streamlit run app/app.py
```

This will open the application in your web browser.

## Features

- Interactive map visualization with color-coded line stress
- Real-time atmospheric parameter adjustment with sliders
- Quick scenario presets (Heat Wave, Cool & Windy, etc.)
- Data export functionality

## Acknowledgments

Data is provided by American Electric Power from the their [Hack OHI/O Project](https://github.com/cwebber314/osu_hackathon)

For more detailed information about the project and the challenge, refer to `docs/AEP_README.md`.

# ELIE

**Explain Like I'm an Expert**: a spin on "Explain Like I'm 5"—but for people who want expert-level nuance.

## What It Does

ELIE is an interactive [Dash Plotly app](https://dash.plotly.com/) that tailors explanations to your current knowledge.
Think of it as a "choose-your-own-expert" learning map.

## How It Works

1. **Pick a topic:** Type in something you want to learn—say, "quaternions".
2. **Get a baseline:** ELIE shows you an initial explanation and a web of related concepts (e.g. "complex numbers", "rotation", "linear algebra").
3. **Click what you know:** Select any familiar node—e.g. "linear algebra"—and ELIE refines the explanation.
4. **Iterate to expertise.**
   Keep choosing known concepts; the map updates and the explanation sharpens until it's perfectly pitched to your expertise.

## Quick Start

Clone the repository:
```bash
git clone https://github.com/niksirbi/ELIE.git
cd ELIE
```

Create and activate a conda environment:
```bash
conda create -n elie-env python=3.12
conda activate elie-env
```

Install the package:
```bash
pip install -e .
```

If you are a developer trying to contribute, include the "modal" extra:
```bash
pip install -e '.[modal]'
```

Launch the dash-plotly app:

```bash
python -m elie.app
```

Click on the link in the terminal, e.g. `http://127.0.0.1:8050/` to open the app in your browser.

## About

This is a hackathon project started at the [CompMotifs: Hack the Sciences](https://lu.ma/apsqlxlj?tk=jK3xrw) event in June 2025,
by Tomas Hrdlicka (@tomashrdlicka), Eva Sevenster (@eva-se), and Niko Sirmpilatze (@niksirbi).

> [!warning]
> This is a proof-of-concept project. Feel free to play around with it, but
> keep in mind that it is not production-ready.

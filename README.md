# Heuristic Optimization Project

## Gerekli Kütüphaneler

```bash
python -m pip install -r requirements.txt
```

## Veritabanı Kurulumu

1. MySQL Server ve MySQL Workbench kurulu olmalı.
2. `diet.sql` dosyasını MySQL Workbench üzerinden import edin.
3. `database/db_config.py` dosyasındaki şifreyi kendi MySQL şifreniz ile güncelleyin.

## Projeyi Çalıştırma

```bash
python main.py
```

## Not

Database bağlantıları ve veri çekme işlemleri `database/` klasörü altında bulunmaktadır.
# Multi-Objective Diet Optimization using NSGA-II and SPEA2

## Overview

This project was developed as part of the **Heuristic Optimization Algorithms** course. The objective is to solve a **Multi-Objective Diet Optimization Problem (MODP)** using evolutionary optimization techniques.

The system generates personalized daily meal plans while simultaneously:

* Maximizing user preference
* Minimizing meal cost
* Minimizing CO₂ emissions
* Satisfying nutritional constraints

Two state-of-the-art Multi-Objective Evolutionary Algorithms (MOEAs) were implemented and compared:

* **NSGA-II (Non-Dominated Sorting Genetic Algorithm II)**
* **SPEA2 (Strength Pareto Evolutionary Algorithm 2)**

The optimization process uses real food and nutritional data stored in a MySQL database.

---

## Problem Definition

The diet planning problem is formulated as a **Multi-Objective Multidimensional Knapsack Problem (MOMKP)**.

### Objectives

1. Maximize user preference score
2. Minimize total meal cost
3. Minimize total CO₂ emission

### Nutritional Constraints

The generated meal plans must satisfy Dietary Reference Intake (DRI) limits for:

* Energy
* Protein
* Carbohydrates
* Fiber
* Sodium

Constraint violations are handled through penalty-based fitness evaluation.

---

## Technologies Used

* Python 3
* MySQL
* Pandas
* NumPy
* Matplotlib
* Evolutionary Algorithms
* NSGA-II
* SPEA2

---

## Project Structure

```text
heuristic_Algo_project/
│
├── database/
│   ├── db_config.py
│   ├── db_connection.py
│   └── data_loader.py
│
├── algorithms/
│   ├── nsga2.py
│   ├── spea2.py
│   └── genetic_operators.py
│
├── experiment.py
├── visualization.py
├── main.py
│
├── results/
│   ├── plots/
│   ├── json/
│   └── sample_menus/
│
└── README.md
```

---

## Main Components

### Database Layer

Responsible for loading:

* Food information
* Nutrient values
* User preferences
* DRI constraints

### Chromosome Representation

Each chromosome consists of two independent permutations:

```text
[ Breakfast Foods | Lunch-Dinner Foods ]
```

This representation prevents duplicate food selections and supports permutation-based genetic operators.

### Genetic Operators

#### Initialization

Random permutation generation.

#### Order Crossover (OX)

Preserves ordering information while producing valid offspring solutions.

#### Swap Mutation

Introduces diversity by swapping food positions inside chromosomes.

---

## Implemented Algorithms

### NSGA-II

Features:

* Fast Non-Dominated Sorting
* Crowding Distance
* Tournament Selection
* Pareto Front Generation

### SPEA2

Features:

* Strength-Based Fitness Assignment
* External Archive
* Density Estimation
* Environmental Selection

---

## Experiments

Three experiments were conducted.

### Experiment 1 – User Comparison

Comparison of generated meal plans for different user profiles.

### Experiment 2 – Algorithm Comparison

Performance comparison between NSGA-II and SPEA2 using:

* Hypervolume
* Pareto Front Size
* Spacing Metric

### Experiment 3 – Diversity Impact

Comparison of optimization performance with:

* Diversity Disabled
* Diversity Enabled

---

## Generated Outputs

The system automatically exports:

### Pareto Front Results

CSV files containing objective values.

Example:

```text
algo_nsga2_run1.csv
algo_spea2_run1.csv
```

### Sample Menus

CSV files containing:

* Objective values
* Breakfast food IDs
* Lunch-Dinner food IDs

Example:

```text
algo_nsga2_menu_run1.csv
div_on_nsga2_menu_run1.csv
```

### Visualization Plots

Generated figures include:

* Pareto Front
* 3D Pareto Front
* Convergence Curves
* Algorithm Comparison
* User Comparison

---

## Running the Project

### 1. Configure Database

Update database connection settings in:

```python
database/db_config.py
```

Example:

```python
DB_CONFIG = {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "root",
    "password": "your_password",
    "database": "diet"
}
```

### 2. Install Dependencies

```bash
pip install pandas numpy matplotlib mysql-connector-python
```

### 3. Run the Optimization

```bash
python main.py
```

---

## Results

The experiments demonstrate that evolutionary multi-objective optimization can effectively generate personalized and nutritionally feasible meal plans.

Key observations:

* NSGA-II generally achieved higher hypervolume values.
* SPEA2 produced competitive Pareto fronts through archive-based elitism.
* Diversity preservation improved meal variety.
* Different user profiles generated significantly different optimal meal plans.

---

## Authors

Developed as a term project for the Heuristic Optimization Algorithms course.

Contributors:

 Esmanur Oruç
 Zeynep Sıla Erdoğan
 Yüsra Nur Atalay
 Elif İlhanoğulları
 Serpil Elinç



---

## License

This project was developed for academic and educational purposes.

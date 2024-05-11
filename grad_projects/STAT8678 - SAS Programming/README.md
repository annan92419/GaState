# Investigating Causes of Student Performance

---

### Introduction

As a pivotal stage in academic development, secondary education lays the foundation for future endeavors and significantly shapes students’ future plans. It not only equips students with essential knowledge and skills but also fosters critical thinking, problem-solving abilities, and social-emotional growth. As such, the quality of secondary education profoundly influences individuals’ academic trajectories, career opportunities, and over-all life outcomes. Understanding the intricacies of student achievement is essential for educators, policymakers, and stakeholders alike to implement targeted interventions and support mechanisms. Therefore, this project seeks to construct a simple yet robust model that not only identifies key predictors of academic achievement but also offers actionable recommendations for enhancing educational outcomes.

### Dataset

The dataset used in this project was sourced from [UC Irvine Machine Learning Repository](https://archive.ics.uci.edu/dataset/320/student+performance). Below is a list of all the features in the dataset, as well as the varaible type of each feature.

| Feature | Description |
|---------|-------------|
| school | student's school (binary: "GP" - Gabriel Pereira or "MS" - Mousinho da Silveira) |
| sex | student's sex (binary: "F" - female or "M" - male) |
| age | student's age (numeric: from 15 to 22) |
| address | student's home address type (binary: "U" - urban or "R" - rural) |
| famsize | family size (binary: "LE3" - less or equal to 3 or "GT3" - greater than 3) |
| Pstatus | parent's cohabitation status (binary: "T" - living together or "A" - apart) |
| Medu | mother's education (numeric: 0 - none, 1 - primary education, 2 – 5th to 9th grade, 3 – secondary education or 4 – higher education) |
| Fedu | father's education (numeric: 0 - none, 1 - primary education, 2 – 5th to 9th grade, 3 – secondary education or 4 – higher education) |
| Mjob | mother's job (nominal) |
| Fjob | father's job (nominal) |
| reason | reason to choose this school (nominal) |
| guardian | student's guardian (nominal) |
| traveltime | home to school travel time (numeric) |
| studytime | weekly study time (numeric) |
| failures | number of past class failures (numeric) |
| schoolsup | extra educational support (binary: yes or no) |
| famsup | family educational support (binary: yes or no) |
| paid | extra paid classes within the course subject (binary: yes or no) |
| activities | extra-curricular activities (binary: yes or no) |
| nursery | attended nursery school (binary: yes or no) |
| higher | wants to take higher education (binary: yes or no) |
| internet | Internet access at home (binary: yes or no) |
| romantic | with a romantic relationship (binary: yes or no) |
| famrel | quality of family relationships (numeric) |
| freetime | free time after school (numeric) |
| goout | going out with friends (numeric) |
| Dalc | workday alcohol consumption (numeric) |
| Walc | weekend alcohol consumption (numeric) |
| health | current health status (numeric) |
| absences | number of school absences (numeric) |
| G1 | first period grade (numeric) |
| G2 | second period grade (numeric) |
| G3 | final grade (numeric, output target) |




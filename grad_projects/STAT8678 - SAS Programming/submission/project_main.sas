*****************************
* IMPORTING BOTH DATA FILES *
*****************************;
proc import datafile='/home/u62534565/student_mat.csv'
	dbms='csv'
	out=mat
	replace;
	delimiter=';';
	getnames=yes;
	datarow=2;
run;

proc import datafile='/home/u62534565/student_por.csv'
	dbms='csv'
	out=por
	replace;
	delimiter=';';
	getnames=yes;
	datarow=2;
run;

data mat;
	set mat;
	subject="math";
	format subject $5.;
run;

data por;
	set por;
	subject="port";
	format subject $5.;
run;



**************************
* INSPECTING BOTH TABLES *
**************************;
title 'Student Performance on the Math Course';
proc print data=mat (obs=5);
run;
title;

title 'Student Performance on the Portuguese Language Course';
proc print data=por (obs=5);
run;
title;



************************************
* MERGING BOTH FILES INTO ONE DATA *
************************************;
proc sort data=mat;
	by _all_;
run;

proc sort data=por;
	by _all_; 
run;

data students;
	merge mat por;
	by _all_;
run;

title 'Combined Student Performance';
proc print data=students (obs=5);
run;
title;



***************************
* OVERVIEW OF THE DATASET *
***************************;
proc contents data=students position;
run;

*converting G1 and G2 to numeric values;
data students;
    set students;
    G1_num = input(G1, best12.);
    G2_num = input(G2, best12.);
    drop G1 G2;
    rename G1_num=G1 G2_num=G2;
run;

%let score=g2; * observe: g1, g2, or g3;
proc sgplot data=students;
	title "Distribution of Subject Scores";
	histogram &score / group=subject transparency=0.5 nbins=30;
	xaxis label="Exam Scores (G1/G2/G3)";
	yaxis label="Distribution (in %)";
	keylegend / title="Subject";
run;
title;

proc sgplot data=students;
    vbox g3 / category=school group=subject;
    xaxis label="Subject";
    yaxis label="Final Grade (G3)";
    keylegend / title="Subject";
run;
* It seems it is easier to pass the Portuguese language course;



*****************************
* EXPLORATORY DATA ANALYSIS *
*****************************;
/* Question:
Does presence of family support and educational support affect
student performance while accounting for variability in gender? */
proc freq data=students;
	tables sex;
run;

proc means data=students;
	class sex famsup schoolsup;
	var g3;
run;

proc sgplot data=students;
	title "Distribution of Final Grade Given Family Support";
	histogram g3 / group=famsup transparency=0.5 nbins=30;
	xaxis label="Final Grade (G3)";
	yaxis label="Distribution (in %)";
	keylegend / title="Family Support";
run;
title;
/* Comments:
1. Although there are more females than males, performance
between genders isn't significantly different with roughtly
the same distribution.
2. However, with family support and school support, females
tend to perform better than males, with the best score for
males being 15 on Q3, whereas for females it's 18.
3. At the same time, with no support from either family or
school, we observe that both genders achieve their best
performances on average. */

/* Question:
Does the presence of educational support (schoolsup) affect
student performance (G3) while accounting for variability
within schools? */
proc freq data=students;
	tables school*schoolsup;
run;

proc means data=students mean stddev min max maxdec=3;
	class school schoolsup;
	var g3;
run;

proc sgplot data=students;
	title "Final grade variability between schools";
	vbox g3 / category=school;
	xaxis label="School";
	yaxis label="Final Grade (G3)";
run;
title;
/* Comments:
From the frequency and mean procedure, we observe that
Gabriel Pereira (GP) students perform better compared
to Mousinho da Silveira's (MS) students. It can also
be seen that relatively, GP has a larger number of
supported students (107) compared to MS (12), which
may indicate a greater emphasis on support services or
resources at GP */

/* Question:
What are the potential causes of extreme absenses? */
proc univariate data=students;
	var absences;
run;

ods graphics on;
proc freq data=students order=freq;
	tables absences / nocum plots=freqplot(orient=horizontal);
run;

%let absence=25; *absence threshold;
%let group=famsup; *observe: pstatus and famsup;
data ext_absence;
	set students;
	where absences > &absence;
	keep pstatus guardian medu fedu mjob fjob famsup higher traveltime romantic absences health g1 g2 g3;
run;

proc sort data=ext_absence;
	by health absences;
run;

proc print data=ext_absence;
run;

proc print data=ext_absence;
	where pstatus="A" and famsup="no";
run;

proc sgplot data=ext_absence;
	title "Relationship Between Absence and Final Grade";
	scatter x=absences y=g3 / group=&group;
	xaxis label="Absence";
	yaxis label="Final Grade (G3)";
	keylegend / title="Family Support";
run;
title;
/* Comment:
1. Among the students with the most absences, only five
appear to have extreme health problems with health=1 or 2.
Surprisingly, two students performed better than the average
student.
2. Another factor that seems to affect absences and
subsequently performance is the parental status (pstatus),
which indicates whether the guardian is staying together (T)
with their child or apart (A), and family support. We can
observe that two students with guardians away and without
support performed worse than the average student, indicating
that parental support and presence are necessary for students'
success. */

/* Question:
Does the number of past class failures predict final grades
differently across schools */
proc sgplot data=students;
	title "Variabily of Final Scores Across Schools Categorized by Failures";
	vbox g3 / category=failures group=school;
	xaxis label="Failures";
	yaxis label="Final Scores (G3)";
	keylegend / title="School";
run;
title;
/* Comment:
We observe that students in Gabriel Pereira (GP) who failed
more than once performed poorly in the final exam compared
to students at Mousinho da Silveira (MS). */

/* Question:
Is there an interaction between weekend alcohol consumption
(walc) and weekday alcohol consumption (dalc) in predicting
academic performance, and does this interaction vary between
gender (sex) */
%let category=walc; *takes: dalc or walc;
proc sgplot data=students;
	title "Variabily of Final Scores Across Alcohol Consumption Categorized by Gender";
	vbox g3 / category=&category group=sex;
	yaxis label="Final Scores (G3)";
	keylegend / title="Gender";
run;
title;

proc means data=students maxdec=3;
	class &category sex;
	var g3;
run;
/* Comment:
Based on the variability of the boxplots and averages, we can
observe that alcohol consumption doesn't affect the performance
of female students, but greatly affects the performance of
male students. This is evident with female students having a
minimum of 11 and 10 for daily and weekly consumption
respectively, while the minimum for male students is 5 and 0
for daily and weekly consumption respectively. */

/* Question:
Does the type of guardian (pstatus) influences students'
academic performance (g3) and their aspiration for higher
education (higher)
*/
proc sgplot data=students;
	title "Relationship between Guardian Status, Higher Education Aspiration, and Final Scores";
    vbox g3 / category=pstatus group=higher groupdisplay=cluster;
    xaxis label="Guardian Status (pstatus)";
    yaxis label="Final Scores (G3)";
    keylegend / title="Higher Education?";
run;
title;
/* Comment:
It can be observed that regardless of guardian status (i.e.,
whether the guardian is living together or apart from the
student), students who perform above average aspire to continue
their education. */



******************************************************
* FIXED EFFECT FEATURE SELECTION AND MODEL SELECTION *
******************************************************;
proc glmselect data=students;
    class sex address famsize pstatus medu fedu mjob fjob reason guardian schoolsup famsup paid activities nursery higher internet romantic subject;
    model g3 = sex age address famsize pstatus medu fedu mjob fjob reason guardian traveltime studytime failures schoolsup famsup paid activities nursery higher internet romantic famrel freetime goout dalc walc health absences subject g1 g2 / selection=stepwise(stop=none);
run;

data selected_features;
	set students;
	keep school failures subject absences g1 g2 g3; * selected features from glmselect;
run;

data correlation;
	format subj best12.;
	format g1 best12.;
	format g2 best12.;
	set selected_features;
	if subject = "math" then subj = 1;
	else if subject = "port" then subj = 0;
	keep failures subj absences g1 g2 g3;
run;

proc corr data=correlation;
    var failures subj absences g1 g2 g3;
run;

proc mixed data=selected_features method=reml covtest plots=(residualPanel) alpha=0.1;
    class school absences subject failures;
    model g3 = failures subject absences subject*failures g1 g2;
    random intercept school;
run;



******************
* ABLATION STUDY *
******************;
* Removing all G3 scores=0;
data nozeros;
	set students;
	where g3 > 0;
	keep school failures subject paid absences g1 g2 g3;
run;

proc mixed data=nozeros method=reml covtest plots=(residualPanel) alpha=0.1;
    class school absences subject failures;
    model g3 = failures subject absences subject*failures g1 g2;
    random intercept school;
run;
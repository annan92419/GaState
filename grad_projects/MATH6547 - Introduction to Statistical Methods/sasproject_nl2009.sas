PROC IMPORT OUT= WORK.nl2009 
            DATAFILE= "C:\Users\jesse\OneDrive\Desktop\stat\MLB-NL2009.csv" 
            DBMS=CSV REPLACE;
     GETNAMES=YES;
     DATAROW=2; 
RUN;

TITLE "MLB NL2009";
PROC PRINT DATA=WORK.NL2009;
run;

* drawing histogram;
PROC CHART DATA=WORK.NL2009;
	VBAR AVG /SPACE=0;
RUN;

/* mean, standard deviation, quantiles
stem-and-leaf plot, and normal plot */
PROC UNIVARIATE DATA=WORK.NL2009 NORMAL PLOT;
	VAR AVG;
RUN;

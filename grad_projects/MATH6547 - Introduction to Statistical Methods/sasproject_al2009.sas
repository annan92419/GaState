PROC IMPORT OUT= WORK.al2009 
            DATAFILE= "C:\Users\jesse\OneDrive\Desktop\stat\MLB-AL2009.csv" 
            DBMS=CSV REPLACE;
     GETNAMES=YES;
     DATAROW=2; 
RUN;

TITLE "MLB AL2009";
PROC PRINT DATA=WORK.AL2009;
run;

* drawing histogram;
PROC CHART DATA=WORK.AL2009;
	VBAR AVG /SPACE=0;
RUN;

/* mean, standard deviation, quantiles
stem-and-leaf plot, and normal plot */
PROC UNIVARIATE DATA=WORK.AL2009 NORMAL PLOT;
	VAR AVG;
RUN;

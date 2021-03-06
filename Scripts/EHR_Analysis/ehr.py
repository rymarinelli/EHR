# -*- coding: utf-8 -*-
"""EHR

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/10z6Yw91poLoja5WO9cm8YcSJ4IiVR4rb
"""



import pandasql as ps
import pandas as pd
import plotly.express as px
import numpy as np
import logging
from collections import namedtuple
from sklearn.linear_model import LinearRegression
import plotly.graph_objects as go

from datetime import datetime

# Creating Log File and Formatting
logging.basicConfig(filename='EHR.log', level=logging.DEBUG)
logging.Formatter("%(asctime)s;%(levelname)s;%(message)s")

try:
    import statsmodels.api as sm
    import statsmodels.formula.api as smf
    from statsmodels.tsa.ar_model import AutoReg


#
except ImportError:
    import os
    raise('Please restart runtime. Statsmodels may need to be updated')


class FileNotAdded(Exception):
    """
    Exception to notify that a file has not been uploaded to Github for the load_data function
    """

    def __init__(self, message):
        super().__init__(message)


def load_data(file):
    """ Util function to read in data from curl request using pandas API

    Keyword arguments:
    file -- name of the name of the csv that was converted and is stored in github to be read

    Return:
    Pandas dataframe that may contain casting into types conductive to this analysis

    """
    try:
        if (file == "encounters"):
            df = pd.read_parquet(f"https://github.com/rymarinelli/EHR/blob/main/data/{file}.parquet?raw=true")
            df.CODE = df.CODE.astype('str')
            return df

        elif (file == "patients"):
            df = pd.read_parquet(f"https://github.com/rymarinelli/EHR/blob/main/data/{file}.parquet?raw=true")
            df.Id = df.Id.astype('str')
            return df

        elif (file == "observations"):
            df = pd.read_parquet(f"https://github.com/rymarinelli/EHR/blob/main/data/{file}.parquet?raw=true")
            conditions = pd.read_parquet(f"https://github.com/rymarinelli/EHR/blob/main/data/conditions.parquet?raw=true")

            conditions = conditions[ ( conditions['DESCRIPTION'] == "Alzheimer's disease (disorder)")].drop_duplicates()

            df['PATIENT_FILTER'] = df.PATIENT.isin(conditions['PATIENT'])
            df = df[df['PATIENT_FILTER'] == True]
            df = df.drop(['PATIENT_FILTER'], axis=1)

            df['DATE'] = pd.to_datetime(df['DATE'])
            df = df[df['DESCRIPTION'] == "Total score [MMSE]"].sort_values(by='DATE')
            df['YEAR'] = pd.DatetimeIndex(df['DATE']).year
            df.VALUE = df.VALUE.astype("float")
            return df 

        # Files that do not require additional pre-processing are the default case here
        else:
            return pd.read_parquet(f"https://github.com/rymarinelli/EHR/blob/main/data/{file}.parquet?raw=true")
    except:
        raise (FileNotAdded(
            "The file selectied has not been added to the database yet.\n Please keep select to the following: \n 1.conditions \n 2.encounters \n 3.medications \n 4.observations \n 5. patients"))


def convert_file(file):
    """ Util function to convert data to parquet format

    Keyword argument --
    Takes a csv file in working directory and convert to parquet
    """
    df = pd.read_csv(f"{file}.csv")

    # gzip parameter further compresses parquet file. Other option may speed up compression at less effect ration
    df.to_parquet(f"{file}.parquet", compression="gzip")


def clean_NA(df, col_name):
    """Util function to remove NA based on row values
       if a row value is NA based on a specific column
       the row is filtered out

   Keyword argument --
   df: Pandas dataframe
   col_name = column in the pandas dataframe that is used for inclusion critera
   """

    df['temp_col'] = pd.Series.isna(df[f"{col_name}"])
    df = df[df['temp_col'] == False]
    df = df.drop(['temp_col'], axis=1)
    return df


conditions = load_data("conditions")
encounters = load_data("encounters")
patients = load_data("patients")

"""#Question 1 

"""

alzheimer_df = conditions[(conditions['DESCRIPTION'] == "Familial Alzheimer's disease of early onset (disorder)") | (
            conditions['DESCRIPTION'] == "Alzheimer's disease (disorder)")][
    ['PATIENT', 'DESCRIPTION', "CODE"]].drop_duplicates().groupby(['DESCRIPTION', 'CODE']).count()

logging.info(f'Question 1: {alzheimer_df.iloc}')

"""#Question 2"""

# SELECTs encounter, code, description and gets a count of unique patients and divides the number of encounter by the unique patients
average_encounter_df = ps.sqldf(''' SELECT  ENCOUNTERCLASS, CODE, DESCRIPTION, Count(ENCOUNTERCLASS) AS Number_Of_Encounters, Count(DISTINCT PATIENT) AS Patient_Count,  CAST(Count(ENCOUNTERCLASS) as FLOAT)/Count(DISTINCT PATIENT) AS Mean_Count 
          FROM encounters
          GROUP BY ENCOUNTERCLASS, CODE ''')

logging.info(f"Question 2: {average_encounter_df}")

"""#Question 3"""

# Converts conditions column to time filters by Alzheimer's Disease in the Description field
# Sorts DataFrame by Start year
# Groups by ID associated with each year

conditions['START'] = pd.to_datetime(conditions['START'])
conditions = conditions[(conditions['DESCRIPTION'] == "Alzheimer's disease (disorder)")].sort_values(
    by='START').groupby("PATIENT").first()

# Finds the difference in number of days and converts to year
# The conditions table is already sorted to get the first diagnosis
age = ps.sqldf('''
          SELECT conditions.PATIENT, conditions.START, patients.Birthdate, CAST((julianday(start) - julianday(BIRTHDATE))/365.25 as Int) as Age 
          FROM  conditions
          JOIN patients
          ON conditions.PATIENT = patients.Id
          ''')

# Leftward most numbers are the labels for ages
# rightward most are the frequency of ages
age = pd.DataFrame(age['Age'].value_counts())

# Fixing Labels to the correct order
age = age.rename(columns={"Age": "Frequency"})
age['Age'] = age.index
logging.info(f"Question 3: {age}")

fig = px.bar(age, x='Age', y="Frequency", title="Age At First AD Diagnosis")
fig.show()
# Right skew mean is somewhere around 78

"""#Question 4"""

# Using namedTuple collection as it supports the object dot syntax to make accessing the data more clear
age_statistics = namedtuple("age_statistics", "mean std")
age_statistics = age_statistics(np.array(ps.sqldf('''
          SELECT conditions.PATIENT, conditions.START, patients.Birthdate, CAST((julianday(start) - julianday(BIRTHDATE))/365.25 as Int) as Age 
          FROM  conditions
          JOIN patients
          ON conditions.PATIENT = patients.Id
          ''')['Age']).mean(), np.array(ps.sqldf('''
          SELECT conditions.PATIENT, conditions.START, patients.Birthdate, CAST((julianday(start) - julianday(BIRTHDATE))/365.25 as Int) as Age 
          FROM  conditions
          JOIN patients
          ON conditions.PATIENT = patients.Id
          ''')['Age']).std())
logging.info(f'Question 4 {age_statistics.std}')
logging.info(f'Question 4 {age_statistics.mean}')

print(age_statistics.std)
print(age_statistics.mean)

"""#Question 5"""

medications = load_data("medications")
conditions = load_data("conditions")
conditions = conditions[(conditions['DESCRIPTION'] == "Alzheimer's disease (disorder)")].drop_duplicates()

# Finds the intersection of ids that are present in both the conditions tables and medications table
len(set(conditions["PATIENT"]) & set(medications['PATIENT']))

"""#Question 6

"""

observations = load_data("observations")

observation_plot = ps.sqldf(''' SELECT YEAR, CAST(AVG(VALUE) AS FLOAT )AS VALUE
         FROM observations
         GROUP BY YEAR
         ORDER BY YEAR 
         '''
                            )

logging.info(f"Question 6: {observation_plot}")

fig = px.line(data_frame=observation_plot, x="YEAR", y="VALUE", title = "Average MMSE Per Year of AD Patients")
fig.show()

type(observation_plot['VALUE'])

px.scatter(data_frame=observation_plot, x="YEAR", y="VALUE", trendline="lowess")

"""#Question 7"""

conditions = load_data("conditions")
conditions = conditions[(conditions['DESCRIPTION'] == "Alzheimer's disease (disorder)")].sort_values(
    by='START').groupby("PATIENT").first()
conditions['YEAR'] = pd.DatetimeIndex(conditions['START']).year

# Use CASE-WHEN to make a dummy vvariable to split by
age_comparison = ps.sqldf('''
          SELECT conditions.PATIENT, conditions.START, patients.Birthdate, CAST((julianday(start) - julianday(BIRTHDATE))/365.25 as Int) as Age, 
          CASE 
          WHEN CAST((julianday(start) - julianday(BIRTHDATE))/365.25 as Int) >= 75 THEN 1
          WHEN CAST((julianday(start) - julianday(BIRTHDATE))/365.25 as Int) < 75 THEN 0
          END as Age_Split
          FROM  conditions
          JOIN patients
          ON conditions.PATIENT = patients.Id
          ''')

# Taking the average to create visualizations, the indiviudal level is too noisy to make good insights
age_viz = ps.sqldf("""
            SELECT AVG(observations.VALUE) AS VALUE, observations.YEAR, CAST(age_comparison.Age_Split AS Integer) AS Age_Split, age_comparison.Age
            FROM observations
            JOIN age_comparison 
            ON age_comparison.PATIENT = observations.PATIENT
            GROUP BY YEAR
          """)

# When Age_Split = 0, they are under 75
# When Age_split = 1, they are 75 or over
fig = px.scatter(age_viz, x="YEAR", y="VALUE", facet_col="Age_Split", trendline="lowess",
                 color="Age_Split", title='Age of AD Diagnosis If Over or Under 75 ')
fig.show()

"""#Question 8"""

observations.groupby(['YEAR', 'VALUE'])

observations_AR = observations.groupby('YEAR').agg({'VALUE': 'mean'})

X = pd.DataFrame(observations_AR.index)
Y = observations_AR['VALUE']
reg = LinearRegression(n_jobs=-1).fit(X, Y)
print(reg.coef_)
logging.info(f"Question 8: {reg.coef_}")

results = AutoReg(observations['VALUE'], lags=[1, 5, 10]).fit()
results = pd.concat([pd.DataFrame(results.params), pd.DataFrame(results.pvalues)], axis=1)
results.columns = ['Beta_Coefficients', 'P_Value']



fig = go.Figure(data=[go.Table(
    header=dict(values=list(results.columns),
                fill_color='paleturquoise',
                align='left'),
    cells=dict(values=[results.Beta_Coefficients, results.P_Value],
               fill_color='lavender',
               align='left'))
])

fig.show()

patients['Gender_Indicator'] = pd.get_dummies(patients['GENDER'])['M']
age_comparison['Age'] = np.subtract(np.array(age_comparison['Age']), (np.array(age_comparison['Age']).mean()))

model_df = ps.sqldf('''
          SELECT patients.Id, patients.Gender_Indicator, 
          age_comparison.Age, age_comparison.Age_Split, 
          observations.VALUE, observations.YEAR
          FROM patients
          JOIN age_comparison
          ON patients.Id = age_comparison.PATIENT
          JOIN observations 
          ON observations.PATIENT = patients.Id
          '''
                    )

y = model_df['VALUE']
X = model_df[['Gender_Indicator', 'Age', 'Age_Split']]
X.set_index(model_df['Id'])

X = sm.add_constant(X)
mod = sm.OLS(y, X)
res = mod.fit()

print(res.summary())
logging.info(f"Question 8: {res.summary}")

mod = smf.ols(formula='VALUE ~ Age + Gender_Indicator + Age_Split + Age_Split*Gender_Indicator', data=model_df)
res = mod.fit()
logging.info(f"Question 8: {res.summary}")
print(res.summary())

"""#Question 9

For the initial fit of with year as the dependent variable, there is a slight negative association. For each year, there is a - 0.12 drop in the MMSE score. This is a logical progression of aging. Since a higher MMSE suggests healthier cognitive functions, the erosion of  mental acuity is expected with age.  In addition to simple regression, an ARIMA model is also applied to observe lag effects. The effects of aging from five years ago are still affecting the MMSE score. The effects of aging from ten years also have some effect on the present. The associated p-value is over .05 threshold, but it is likely still contributing to the overall negative trend. 

For the  multivariate regression model, a per unit change in age is associated with a .04 decrease in MMSE. The baseline for the model has a MMSE of 12.67; this is the intercept term. As for gender, men have a lower MMSE of women. Holding all other factors equal, gender is associated with a decrease of .04. Essentially, being a man has the same effect of being a woman but being a year older.

#Question 10

When looking to answer this hypothesis, a dummy variable is encoded based on when someone had their AD diagnosis. If they were 75 or older at their diagnosis, it is encoded as 1. If not, the variable is encoded as zero. Holding all other factors equal, a person that had their diagnosis at or after reaching 75, should have a half a point higher than a person that had their diagnosis earlier. This is likely detecting when patients started their cognitive declines. A person with an earlier onset has a longer time to degrade and get a lower MMSE. If you are older, you have less time to degrade and are likely to pass away from other ailments before your MMSE can be measured. Effectively, people with later onsets might just too soon before their MMSE can degrade.
"""

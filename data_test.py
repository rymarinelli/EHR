import pytest
from EHR_Analysis.ehr import load_data
import pandas as pd
import pandasql as ps
import numpy as np
from EHR_Analysis.ehr import alzheimer_df
from datetime import datetime
from EHR_Analysis.ehr import age_statistics
from EHR_Analysis.ehr import age_comparison

def test_data_load():
    test_df = load_data('conditions')
    conditions = load_data("conditions")
    test_df = pd.read_parquet(f"https://github.com/rymarinelli/EHR/blob/main/data/conditions.parquet?raw=true")
    assert conditions.shape == test_df.shape

@pytest.mark.Question_One
def test_Alzheimer():
    # Testing the filtering conditions
    conditions = load_data("conditions")
    conditions[(conditions['DESCRIPTION'] == "Familial Alzheimer's disease of early onset (disorder)") | (
                conditions['DESCRIPTION'] == "Alzheimer's disease (disorder)")][
        ['PATIENT', 'DESCRIPTION', "CODE"]].drop_duplicates()
    assert len(set(conditions[(conditions['DESCRIPTION'] == "Familial Alzheimer's disease of early onset (disorder)") | (
                conditions['DESCRIPTION'] == "Alzheimer's disease (disorder)")][
                ['PATIENT', 'DESCRIPTION', "CODE"]].drop_duplicates()['DESCRIPTION']) - set(
        ["Familial Alzheimer's disease of early onset (disorder)", "Alzheimer's disease (disorder)"])) == 0

@pytest.mark.Question_One
def test_Alzheimer_Count_First():
    #Confirming the logic done in pandas with SQL and getting concurrent results
    conditions = load_data("conditions")
    assert ps.sqldf("""
               SELECT DISTINCT Count(PATIENT) as PATIENT, DESCRIPTION, CODE
               FROM conditions 
               WHERE  DESCRIPTION IN ("Familial Alzheimer's disease of early onset (disorder)", "Alzheimer's disease (disorder)")
               GROUP BY DESCRIPTION, CODE
               """).iloc[0, 0] == alzheimer_df.iloc[0,0]


@pytest.mark.Question_Two()
def test_Mean_Calculation():
    #Testing the mean is being calculated in the table based on tabulated values
    encounters = load_data("encounters")
    test_df = ps.sqldf( ''' SELECT  ENCOUNTERCLASS, CODE, DESCRIPTION, Count(ENCOUNTERCLASS) AS Number_Of_Encounters, Count(DISTINCT PATIENT) AS Patient_Count,  CAST(Count(ENCOUNTERCLASS) as FLOAT)/Count(DISTINCT PATIENT) AS Mean_Count 
          FROM encounters
          GROUP BY ENCOUNTERCLASS, CODE ''')
    np.testing.assert_array_equal(np.divide(np.array(test_df['Number_Of_Encounters']), test_df['Patient_Count']),
                                  test_df['Mean_Count'])


@pytest.mark.Question_Three
def test_First_AD_Diagonsis():
    #Fresh Data load
    conditions = load_data("conditions")

    #Get the min time for each start date groping by patient and sorting it by the start date
    #The min start date in the sorted dates should be the first diagnosis with the WHERE clause filtering
    test_df = ps.sqldf(""" SELECT min(STRFTIME('%Y/%m/%d' , START)) as START, DESCRIPTION, PATIENT
                            FROM conditions
                            WHERE DESCRIPTION = "Alzheimer's disease (disorder)"
                            GROUP BY PATIENT
                            ORDER BY START
                        """)

    conditions['START'] = pd.to_datetime(conditions['START'])

    #Same Logic as SQL but to confirm start dates
    conditions = conditions[(conditions['DESCRIPTION'] == "Alzheimer's disease (disorder)")].sort_values(
        by='START').groupby("PATIENT").first()

    conditions['test_id'] = conditions.index.isin(test_df.PATIENT)
    conditions = conditions[conditions['test_id'] == True]
    conditions = conditions.drop("test_id", axis=1)
    conditions = conditions[conditions["DESCRIPTION"] == "Alzheimer's disease (disorder)"]

    #Converting pandas to a dictionary with patient IDS as columns
    #Testing the start dates based on a look up table
    # This is done to be robust to any errors in ordering

    test_dict = test_df.set_index(test_df["PATIENT"])
    test_dict = test_dict.transpose()
    test_dict = test_dict.to_dict()

    sentinel_val = True

    # For patient IDs, look up at the start time in the dictionary and compare the time to the pandas dataframe
    # If the ids have a start date that does not match, it suggests an error in the procedure

    for i in test_df['PATIENT']:
        for j in range(0, len(conditions[conditions.index == i]["START"].values)):
            row_test = datetime.strptime(test_dict.get(i)["START"], '%Y/%m/%d') == datetime.strptime(
                str(conditions[conditions.index == i]["START"].values[j])[0:10], "%Y-%m-%d")
            if row_test == False:
                sentenal_val = False
    assert sentinel_val == True

@pytest.mark.Question_Four
def test_Descriptive_Stat():
    #Test confirms mean calculation

    # Fresh Data load
    conditions = load_data("conditions")
    patients = load_data("patients")
    test_df = ps.sqldf('''
              SELECT conditions.PATIENT, conditions.START, patients.Birthdate, CAST((julianday(start) - julianday(BIRTHDATE))/365.25 as Int) as Age 
              FROM  conditions
              JOIN patients
              ON conditions.PATIENT = patients.Id
              ''')

    assert (test_df['Age'].sum() / len(test_df['Age']) -  age_statistics.mean) < .10

@pytest.mark.Question_Five
def test_Count():
    conditions = load_data("conditions")
    medications = load_data("medications")

    conditions = conditions[(conditions['DESCRIPTION'] == "Alzheimer's disease (disorder)")].drop_duplicates()
    medications = medications.drop_duplicates()

    conditions["test_col"] = conditions.PATIENT.isin(medications['PATIENT'])
    conditions = conditions[conditions['test_col'] == True]

    assert len(conditions['PATIENT'].unique()) == len(set(conditions["PATIENT"]) & set(medications['PATIENT']))

@pytest.mark.Question_Seven
def test_Row_Total():
    conditions = load_data("conditions")
    patients = load_data("patients")

    test_df = ps.sqldf('''
                      SELECT conditions.PATIENT, CAST((julianday(start) - julianday(BIRTHDATE))/365.25 as Int) as Age 
                      FROM  conditions
                      JOIN patients
                      ON conditions.PATIENT = patients.Id
                       ''')
    assert len(ps.sqldf("""
              SELECT age_comparison.PATIENT 
              FROM age_comparison
              WHERE age_comparison.PATIENT IN (SELECT test_df.PATIENT FROM test_df)
           """)) == len(age_comparison)

@pytest.mark.Question_Seven
def test_Row_Total_Exclusion():
    conditions = load_data("conditions")
    patients = load_data("patients")

    test_df = ps.sqldf('''
                          SELECT conditions.PATIENT, CAST((julianday(start) - julianday(BIRTHDATE))/365.25 as Int) as Age 
                          FROM  conditions
                          JOIN patients
                          ON conditions.PATIENT = patients.Id
                           ''')
    assert len(ps.sqldf("""
              SELECT age_comparison.PATIENT 
              FROM age_comparison
              WHERE age_comparison.PATIENT NOT IN (SELECT test_df.PATIENT FROM test_df)
           """)) == 0


@pytest.mark.Question_Seven
def test_Age_Split_Inclusion():
    conditions = load_data("conditions")
    conditions = load_data("conditions")
    conditions = conditions[(conditions['DESCRIPTION'] == "Alzheimer's disease (disorder)")].sort_values(
        by='START').groupby("PATIENT").first()
    conditions['YEAR'] = pd.DatetimeIndex(conditions['START']).year

    patients = load_data("patients")

    test_df = ps.sqldf('''
                              SELECT conditions.PATIENT, CAST((julianday(start) - julianday(BIRTHDATE))/365.25 as Int) as Age 
                              FROM  conditions
                              JOIN patients
                              ON conditions.PATIENT = patients.Id
                               ''')

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

    assert len(ps.sqldf("""
          SELECT test_df.PATIENT 
          FROM test_df
          WHERE test_df.PATIENT IN (SELECT age_comparison.PATIENT FROM age_comparison WHERE age_comparison.Age_Split == 1)
          """)) == len(ps.sqldf("""
          SELECT test_df.PATIENT
          FROM test_df
          WHERE test_df.AGE >= 75
          """))

@pytest.mark.Question_Seven
def test_Age_Split_Exclusion():
    conditions = load_data("conditions")
    patients = load_data("patients")

    conditions = load_data("conditions")
    conditions = conditions[(conditions['DESCRIPTION'] == "Alzheimer's disease (disorder)")].sort_values(
        by='START').groupby("PATIENT").first()
    conditions['YEAR'] = pd.DatetimeIndex(conditions['START']).year

    test_df = ps.sqldf('''
                               SELECT conditions.PATIENT, CAST((julianday(start) - julianday(BIRTHDATE))/365.25 as Int) as Age 
                               FROM  conditions
                               JOIN patients
                               ON conditions.PATIENT = patients.Id
                                ''')

    assert len(ps.sqldf("""
              SELECT test_df.PATIENT 
              FROM test_df
              WHERE test_df.PATIENT IN (SELECT age_comparison.PATIENT FROM age_comparison WHERE age_comparison.Age_Split == 0)
              """)) == len(ps.sqldf("""
              SELECT test_df.PATIENT
              FROM test_df
              WHERE test_df.AGE < 75
              """))


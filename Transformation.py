# -*- coding: utf-8 -*-
"""
@author: An Binh (Jason) Nguyen
@date: 12/03/2021
@introduction: Optimmisations around ED wait time and staffing are highly desireable in a world where detailed records of patience visits are kept by hospitals.
@purpose: This script transforms original dataset to:
                1. Clean data
                2. Calculate metrics of interest
"""

import pandas as pd

# read dataset
Dataset_ED = pd.read_excel("Generic ED 2009.xlsx", sheet_name="Generic ED Data")

# calculate hour value for each patient's arrival
Dataset_ED["Arrival Hour"] = [d.hour for d in Dataset_ED["Arrival Date"]]

# calculate total patients in ED at the point of new patient's arrival
TotalPatientsInEDAtArrival = [0 for i in range(len(Dataset_ED))]
for i in range(1, len(Dataset_ED)):
    currentArrivalDate = Dataset_ED.iloc[i]["Arrival Date"]
    TotalPatientsInEDAtArrival[i] = len(Dataset_ED.loc[(Dataset_ED["Depart Actual Date"] > currentArrivalDate) & (Dataset_ED["Arrival Date"] < currentArrivalDate)])
        
Dataset_ED["TotalPatientsInEDAtArrival"] = TotalPatientsInEDAtArrival

# calculate total wait time between arrival and first doctor inspection
Dataset_ED["TimeDiff Arrival-TreatDrNr (mins)"] = (Dataset_ED["Dr Seen Date"] - Dataset_ED["Arrival Date"]).dt.seconds/60.0

# test calculations of minutes for arrival - departure and arrival - doctor inspection
Dataset_ED["Calculated TimeDiff TreatDrNr-Act. Depart (mins)"] = (Dataset_ED["Depart Actual Date"] - Dataset_ED["Dr Seen Date"]).dt.seconds/60.0
Dataset_ED["Check TreatDrNr-Act. Depart"] = Dataset_ED["Calculated TimeDiff TreatDrNr-Act. Depart (mins)"] == Dataset_ED["TimeDiff TreatDrNr-Act. Depart (mins)"]

Dataset_ED["Calculated TimeDiff Arrival-Actual Depart (mins)"] = (Dataset_ED["Depart Actual Date"] - Dataset_ED["Arrival Date"]).dt.seconds/60.0
Dataset_ED["Check Arrival-Actual Depart"] = Dataset_ED["Calculated TimeDiff Arrival-Actual Depart (mins)"] == Dataset_ED["TimeDiff Arrival-Actual Depart (mins)"]

# proxy for wait time

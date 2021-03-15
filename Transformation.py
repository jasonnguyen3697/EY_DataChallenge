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
import datetime

# read dataset
Dataset_ED = pd.read_excel("Generic ED 2009.xlsx", sheet_name="Generic ED Data")

# calculate hour value for each patient's arrival
Dataset_ED["Arrival Hour"] = [d.hour for d in Dataset_ED["Arrival Date"]]

# calculate total patients in ED at the point of new patient's arrival
# generate table of patients currently presenting at each arrival time
# calculate ranking for dr seen to see where there is a discrepancy between the order in which a patient requires medical attention vs what actually happened
triageTimeLimit = [2, 10, 30, 60, 120]
TotalPatientsInEDAtArrival = [0 for i in range(len(Dataset_ED))]
CurrentPresentations = {"Datetime": [], "MRN": [], "Presentation Visit Number": [], "Arrival Date": [], "Triage Priority": [], "Expected Dr Seen":[], "Actual Dr Seen": []}
TriagePriorityCount = {"Triage 1 count": [0 for i in range(len(Dataset_ED))], "Triage 2 count": [0 for i in range(len(Dataset_ED))], "Triage 3 count": [0 for i in range(len(Dataset_ED))], "Triage 4 count": [0 for i in range(len(Dataset_ED))], "Triage 5 count": [0 for i in range(len(Dataset_ED))]}
for i in range(len(Dataset_ED)):
    currentArrivalDate = Dataset_ED.iloc[i]["Arrival Date"]
    current_presentations = Dataset_ED.loc[(Dataset_ED["Depart Actual Date"] > currentArrivalDate) & (Dataset_ED["Arrival Date"] <= currentArrivalDate)][["Arrival Date", "MRN", "Presentation Visit Number", "Triage Priority", "Dr Seen Date"]]
    CurrentPresentations["Datetime"] += [currentArrivalDate for i in range(len(current_presentations))]
    CurrentPresentations["Presentation Visit Number"] += [current_presentations.iloc[i]["Presentation Visit Number"] for i in range(len(current_presentations))]
    CurrentPresentations["MRN"] += [current_presentations.iloc[i]["MRN"] for i in range(len(current_presentations))]
    CurrentPresentations["Triage Priority"] += [current_presentations.iloc[i]["Triage Priority"] for i in range(len(current_presentations))]
    CurrentPresentations["Arrival Date"] += [current_presentations.iloc[i]["Arrival Date"] for i in range(len(current_presentations))]
    CurrentPresentations["Expected Dr Seen"] += [current_presentations.iloc[i]["Arrival Date"] + datetime.timedelta(minutes=triageTimeLimit[current_presentations.iloc[i]["Triage Priority"]-1]) for i in range(len(current_presentations))]
    CurrentPresentations["Actual Dr Seen"] += [current_presentations.iloc[i]["Dr Seen Date"] for i in range(len(current_presentations))]
    for j in range(1, 6):
        TriagePriorityCount["Triage {} count".format(j)][i] = len(current_presentations.loc[(current_presentations["Arrival Date"] < currentArrivalDate) & (current_presentations["Triage Priority"] == j)])
    TotalPatientsInEDAtArrival[i] = sum([TriagePriorityCount["Triage {} count".format(j)][i] for j in range(1, 6)])
        
Dataset_ED["TotalPatientsInEDAtArrival"] = TotalPatientsInEDAtArrival
for key in TriagePriorityCount.keys():
    Dataset_ED[key] = TriagePriorityCount[key]
CurrentPresentationsDf = pd.DataFrame(CurrentPresentations)

# calculate relative order of priority for each presentation instance
for date in list(CurrentPresentationsDf["Datetime"].unique()):
    currentPresentations = CurrentPresentationsDf.loc[CurrentPresentationsDf["Datetime"]==date]
    rankingActual = currentPresentations["Actual Dr Seen"].rank(method="first", ascending=True)
    CurrentPresentationsDf.loc[CurrentPresentationsDf["Datetime"]==date, "Actual Ranking"] = rankingActual
    rankingExpected = currentPresentations["Expected Dr Seen"].rank(method="first", ascending=True)
    CurrentPresentationsDf.loc[CurrentPresentationsDf["Datetime"]==date, "Expected Ranking"] = rankingExpected

# calculate population treated after their expected ordering
dateTimeTreatedLaterThanOrdering = list(CurrentPresentationsDf.loc[CurrentPresentationsDf["Actual Ranking"] > CurrentPresentationsDf["Expected Ranking"]]["Datetime"].unique())
treatedLaterThanOrdering = CurrentPresentationsDf.loc[CurrentPresentationsDf["Actual Ranking"] > CurrentPresentationsDf["Expected Ranking"]][["MRN", "Presentation Visit Number"]].drop_duplicates(subset=["MRN", "Presentation Visit Number"], keep="first")

# add flag to transformed dataset
Dataset_ED = Dataset_ED.merge(treatedLaterThanOrdering, how="left", on=["MRN", "Presentation Visit Number"], indicator=True)
mask = Dataset_ED["_merge"] == "both"
Dataset_ED.loc[mask, "TreatedLaterThanOrdering"] = 1
Dataset_ED.loc[~mask, "TreatedLaterThanOrdering"] = 0
Dataset_ED.drop(labels=["_merge"], axis="columns", inplace=True)

# calculate total wait time between arrival and first doctor inspection
Dataset_ED["TimeDiff Arrival-TreatDrNr (mins)"] = (Dataset_ED["Dr Seen Date"] - Dataset_ED["Arrival Date"]).dt.seconds/60.0

# test calculations of minutes for arrival - departure and arrival - doctor inspection
Dataset_ED["Calculated TimeDiff TreatDrNr-Act. Depart (mins)"] = (Dataset_ED["Depart Actual Date"] - Dataset_ED["Dr Seen Date"]).dt.seconds/60.0
Dataset_ED["Check TreatDrNr-Act. Depart"] = Dataset_ED["Calculated TimeDiff TreatDrNr-Act. Depart (mins)"] == Dataset_ED["TimeDiff TreatDrNr-Act. Depart (mins)"]

Dataset_ED["Calculated TimeDiff Arrival-Actual Depart (mins)"] = (Dataset_ED["Depart Actual Date"] - Dataset_ED["Arrival Date"]).dt.seconds/60.0
Dataset_ED["Check Arrival-Actual Depart"] = Dataset_ED["Calculated TimeDiff Arrival-Actual Depart (mins)"] == Dataset_ED["TimeDiff Arrival-Actual Depart (mins)"]

# test difference between triage priority time to be seen by a doctor recommendation vs dataset
for i in range(1, 6):
    mask = Dataset_ED["Triage Priority"]==i
    Dataset_ED.loc[mask, "LateSeenByDr"] = Dataset_ED["TimeDiff Arrival-TreatDrNr (mins)"] - triageTimeLimit[i-1]

# whether a person was late being seen by a doctor    
Dataset_ED.loc[Dataset_ED["LateSeenByDr"] > 0, "LateFlag"] = 1
Dataset_ED.loc[Dataset_ED["LateSeenByDr"] <= 0, "LateFlag"] = 0

LatePopulation = Dataset_ED.loc[Dataset_ED["LateFlag"]==1]
OnTimePopulation = Dataset_ED.loc[Dataset_ED["LateFlag"]==0]

with pd.ExcelWriter("output.xlsx") as xWriter:
    Dataset_ED.to_excel(xWriter, sheet_name="Dataset_ED_transformed", index=False)
    CurrentPresentationsDf.to_excel(xWriter, sheet_name="Presentation Timeline", index=False)
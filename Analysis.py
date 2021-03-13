# -*- coding: utf-8 -*-
"""
Spyder Editor

This is a temporary script file.
"""

import pandas as pd
import os
import matplotlib.pyplot as plt
import numpy as np

def createGroupedCharts(labels, ax, dataset, disaggregationColumn, countColumn="Count", width=0.2):
    ind = np.arange(len(labels))
    axesList = []
    
    uniqueDisaggValues = list(dataset[disaggregationColumn].unique())
    for i in range(len(uniqueDisaggValues)):
        label = disaggregationColumn + " {}".format(uniqueDisaggValues[i])
        count = list(dataset.loc[dataset[disaggregationColumn]==uniqueDisaggValues[i]][countColumn])
        axesList.append(ax.bar(ind - width*(len(uniqueDisaggValues) - (i*2 + 1))/2, count, width, label=label))
        
    return axesList

def calculateTotalPatientsInED(dataset):
    """Calculate number of patients currently presenting in ED. The start of a presentation is from Arrival Time until Departure time
    
    Input:
        dataset - Generic ED 2009 dataset
        
    Output:
        Cummulative count of number of patients currently presenting in ED at time of new patient arrival
    """
    dataset["TotalPatientsInEDAtArrival"] = [0 for i in range(len(dataset))]
    for i in range(1, len(dataset)):
        currentArrivalDate = dataset.iloc[i]["Arrival Date"]
        dataset.iloc[i]["TotalPatientsInEDAtArrival"] = len(dataset.loc[(dataset["Depart Actual Date"] > currentArrivalDate) & (dataset["Arrival Date"] < currentArrivalDate)])
        
    dataset.insert(len(dataset), "TotalPatientsInEDAtArrival", TotalPatientsInEDAtArrival, inplace=True)
    
    return

Dataset_ED = pd.read_excel("C:\\Users\\jnguyen11\\OneDrive - KPMG\\Desktop\\Stuff\\Generic ED 2009.xlsx", sheet_name="Generic ED Data")

Dataset_ED["Triage Priority"].value_counts().sort_index().plot(kind="bar", x = "Triage Priority", y="Presentation count", title="Graph to show distribution of triage priorities for a generic ED")

Dataset_ED["Arrival Hour"] = [d.hour for d in Dataset_ED["Arrival Date"]]

Hour_Triage = Dataset_ED.groupby(["Arrival Hour", "Triage Priority"]).size().reset_index().rename(columns={0:'Count'})

fig, ax = plt.subplots(figsize = (15, 10))

labels = list(Hour_Triage["Arrival Hour"].unique())

ind = np.arange(len(labels))

axesList = createGroupedCharts(labels, ax, Hour_Triage, "Triage Priority")

ax.set_xticks(ind)
ax.set_xticklabels(labels)
ax.legend()

#calculateTotalPatientsInED(Dataset_ED)

TotalPatientsInEDAtArrival = [0 for i in range(len(Dataset_ED))]
for i in range(1, len(Dataset_ED)):
    currentArrivalDate = Dataset_ED.iloc[i]["Arrival Date"]
    TotalPatientsInEDAtArrival[i] = len(Dataset_ED.loc[(Dataset_ED["Depart Actual Date"] > currentArrivalDate) & (Dataset_ED["Arrival Date"] < currentArrivalDate)])
        
Dataset_ED["TotalPatientsInEDAtArrival"] = TotalPatientsInEDAtArrival

Dataset_ED[["TotalPatientsInEDAtArrival", "Calculated Arrival-TreatDrNr (mins)"]].groupby(by="TotalPatientsInEDAtArrival").mean().reset_index()
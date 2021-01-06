
# Finish: Clean this up and import from "modulesImport.py"
# Finish: Add file resources\columns.py for genderDf and countryDf
# Finish: Rather than self.fileType, have subclasses of Examiner and Lawyer, inherit from GenederRaceAnalysis
import  pandas as pd
import numpy as np
from resources.superCultureMap import culture_dict
import time
from collections import defaultdict
import regex as re


class GenderRaceAnalysis:
    def __init__(self,fileType):
        assert fileType == "E" or fileType == "L", ' Must indicate Examiners or Lawyers by passing, either: "E" or "L" '
        self.femaleThreshold = self.maleThreshold = 95
        self.superCultureMap = culture_dict
        self.firstNameFreq_Threshold = .40
        self.lastNameFreq_Threshold = .90

        if fileType == "E":
            self.fileType = "Examiners"
            self.idColumnName = "Examiner_ID"
            self.filePathIbm = "data/ibmOuputs/ExaminerDirectory_New_Output3.csv"
            self.filePathPatent = "data/patentData/ExaminerPatentMap.csv"
            self.patentDict_FirstName = self.getPatentData()
        elif fileType == "L":
            self.fileType = "Lawyers"
            self.idColumnName = "Lawyer_ID"
            self.filePathIbm = "data/ibmOuputs/LawyerDirectory_New_Output3.csv"
            self.filePathPatent = "data/patentData/LawyerPatentMap.csv"
            self.patentDict_FirstName = self.getPatentData()

        self.genderDf,self.countryDf = self.readFile()
        self.IBM_GenderCutoff(self.genderDf,self.femaleThreshold,self.maleThreshold)
        self.IBM_SuperCulture()
        self.patentDict_FirstName = self.mergePatentIbm()
        self.idTopFirstName = self.selectTopName(self.patentDict_FirstName)
        # self.idTopLastName = self.selectTopName(self.patentDict_LastName)
        self.test(self.idTopFirstName, self.idColumnName)
        
        
        
    def readFile(self):
        """
        Reads and formats IBM output files
        Returns 2 pandas dataframe for Gender and Culture Analysis
        """
        clean_df_master = pd.read_csv(self.filePathIbm).fillna("")
        clean_df_master['ExaminerFirstName_Key'] = clean_df_master['ExaminerID'].astype(str) + "," + clean_df_master['FirstName']
        clean_df_master['ExaminerLastName_Key'] = clean_df_master['ExaminerID'].astype(str) + "," + clean_df_master['LastName']

        # Dataframe for Gender
        clean_df_master.insert(9, 'Female Classification', "TBD")
        clean_df_master.insert(10, 'Male Classification', "TBD")        
        genderDf = clean_df_master[['ExaminerID','FirstName', 'LastName', 'Classification Confidence', 'Given Name Confidence', 'Surname Confidence', 'Female %',  'Female Classification',  ' Male %',  'Male Classification','ExaminerFirstName_Key','ExaminerLastName_Key',]]

        # Dataframe for Country and Culture
        clean_df_country = clean_df_master[['ExaminerID', 'FirstName', 'LastName', 'ExaminerFirstName_Key','ExaminerLastName_Key','Country 1','Top Culture', 'Unnamed: 31','Unnamed: 32', 'Unnamed: 33', 'Unnamed: 34','Unnamed: 35', 'Unnamed: 36','Unnamed: 37','Unnamed: 38', 'Unnamed: 39']]
        countryDf = clean_df_country.rename(columns={ "Unnamed: 31": "Top Culture 2"  ,"Unnamed: 32": "Top Culture 3","Unnamed: 33": "Top Culture 4","Unnamed: 34": "Top Culture 5","Unnamed: 35": "Top Culture 6","Unnamed: 36": "Top Culture 7","Unnamed: 37": "Top Culture 8","Unnamed: 38": "Top Culture 9","Unnamed: 39": "Top Culture 10"})
        return genderDf, countryDf
       
    
    def IBM_GenderCutoff(self, genderDf,thresholdFemale,thresholdMale):
        """ 
        Assign Gender to Rows, based on defined threshold for IBM female/male % 
        """
        genderDf['Female %'] = pd.to_numeric(genderDf['Female %'], errors='coerce')
        genderDf['Male %'] = pd.to_numeric(genderDf[' Male %'], errors='coerce')
        genderDf['Female Classification'] = [ 1 if val >= thresholdFemale else 0 for val in genderDf['Female %']]
        genderDf['Male Classification'] = [ 1 if val >= thresholdMale else 0 for val in genderDf['Male %']]
        del genderDf[' Male %'] 
    
    def IBM_SuperCulture(self):
        """
        Compresses up to 10 cultures associated with a given name into 1 super culture value
        """
        superCulturesCol = []
        for index, row in self.countryDf.loc[:, "Top Culture":"Top Culture 10"].iterrows():
            cultures = set(filter(lambda x: False if x == "" else True,row)) # filter out instances with no culuture value (ex. "Top Culture 10" column)
            superCultures = [self.superCultureMap[culture] for culture in cultures] 
            if "Ambiguous" not in superCultures and len(superCultures) == 1:
                superCulturesCol.append(superCultures[0])
            elif "Ambiguous" in superCultures or len(superCultures) > 1:
                superCulturesCol.append("No certain culture")
            else:
                superCulturesCol.append("Ambiguous")
        
        dropThese = ["Top Culture", "Top Culture 2", "Top Culture 3", "Top Culture 4", "Top Culture 5", "Top Culture 6", "Top Culture 7", "Top Culture 8", "Top Culture 9", "Top Culture 10"]
        self.countryDf.drop(columns=dropThese, axis=1, inplace=True)
        self.countryDf['super_culture'] = superCulturesCol

    def getPatentData(self):
        """
        Creates counter dictionary for names in Patent data
        """
        if self.fileType == "Examiners":

            ### FirstName
            badIds = ["51225,SANG KIM","51224,ELMIRA MEHRMANESH"] # Extra IDs not found in Original  51225,SANG KIM (Maps to 8216) and 51224,ELMIRA MEHRMANESH (Maps to 28326) from nameCount dict 

            df = pd.read_csv(self.filePathPatent, dtype={"PrimaryID": 'str',"AssistantID": 'str',})
            df["Primary_FirstName_Key"] = df["PrimaryID"] + "," + df["Primary_Firstname"]
            df["AssistantFirstName_Key"] = df["AssistantID"]  + "," + df["Assistant_FirstName"]
            allExaminers = list(df["Primary_FirstName_Key"].dropna()) + list(df["AssistantFirstName_Key"].dropna())
            patentDict_FirstName = defaultdict(list)
            for key in allExaminers:
                if key in badIds: continue
                if key in patentDict_FirstName:
                    patentDict_FirstName[key][0] += 1
                else:
                    patentDict_FirstName[key].append(1)
                    idStr = key.split(",")[0]
                    patentDict_FirstName[key].append(idStr)
                    # idStr = re.search('([0-9]+),.+', key) # Compare runtime of: .split() vs Regex, remember key is a small str
                    # if idStr: 
                    #     patentDict_FirstName[key].append(idStr.group(1))
            
            ### LastName
            # Finish: Generalize for last Name 
            # Finish: Use inhertance for subclass of Lawyer 
            return patentDict_FirstName
    
    
    # Finish: optimize this function in general space like using dictionary comprehensiopn and numpy arrays
    # Finish: Generalize for last Name 
    # Finish: Use inhertance for subclass of Lawyer 
    def mergePatentIbm(self):
        """
        Merges: IBM/Directory data onto Patent data dictionary 
        """
        genderDfIbm, countryDfIbm = self.genderDf, self.countryDf
        patentDict = self.patentDict_FirstName
        mergedDict_Gender = defaultdict(list)
        mergedDict_Country = defaultdict(list)

        # Create dictionary for IBM Data
        classifications = {}
        gender_classifications_keys = list(genderDfIbm['ExaminerFirstName_Key'])
        female_classifications_keys = list(genderDfIbm['Female %'])
        male_classifications_keys = list(genderDfIbm['Male %'])
        for key in range(len(gender_classifications_keys)):
            if gender_classifications_keys[key] in classifications:
                continue
            else:
                classifications[gender_classifications_keys[key]] = [female_classifications_keys[key],male_classifications_keys[key]]
        
        # Merge IBM Data onto Patent Data
        for key in patentDict:
            if key in classifications:
                patentDict[key].append(classifications[key][0])
                patentDict[key].append(classifications[key][1])
        return patentDict

    # Changed from [2],[3] to [3],[4] || from x  > 0 to x >= 0 
    # Caught logical mistake: I was checking if the running count sum was ambigious (denoted by ***)  -> This should give me: +.03% classified and -.03%  unclassified 
    # Finish: Get the difference in  = set(result I sent mukund) - set(using this selection)
    def selectTopName(self, idName_Count):  
        """
        Chooses "top name" for any given ID, by prioritizing:
        Names that returned results from IBM GNR, then the most frequent name (relative to ID)

        ex. idsTopName[10007] = ['10007,RODNEY H', 4804, 4843, 0.0, 98.0]
        """
        idTopName = {}
        for first_id_key in idName_Count:    
            # Name does not have return value from GNR
            if len(idName_Count[first_id_key]) < 4: continue

            examiner_id = idName_Count[first_id_key][1]
            if examiner_id in idTopName:                                                                  
                if type(idName_Count[first_id_key][2]) == str: idName_Count[first_id_key][2] = 0
                if type(idName_Count[first_id_key][3]) == str: idName_Count[first_id_key][3] = 0

                # Accumulate running count of ID occurences in patent data   
                runningCount = idTopName[examiner_id][2] + idName_Count[first_id_key][0] 
                canidate = [first_id_key, idName_Count[first_id_key][0], runningCount,                 
                            idName_Count[first_id_key][2],idName_Count[first_id_key][3]]
                # If Existing ID's top name has valid male % and female %
                if idTopName[examiner_id][3] >= 0 or idTopName[examiner_id][4] >= 0: # ***             
                    if (canidate[1] > idTopName[examiner_id][2]): # If current has greater count
                        idTopName[examiner_id] = canidate
                    else:
                        idTopName[examiner_id][2] = runningCount
                else:
                    idTopName[examiner_id] = canidate                                               # Finish: see if you can cosolidate IFs by 1 layer,  with above where we assign canidate
            else: 
                if type(idName_Count[first_id_key][2]) == str: idName_Count[first_id_key][2] = 0
                if type(idName_Count[first_id_key][3]) == str: idName_Count[first_id_key][3] = 0
                runningCount = idName_Count[first_id_key][0]
                init = [first_id_key,idName_Count[first_id_key][0], runningCount,
                        idName_Count[first_id_key][2], idName_Count[first_id_key][3]]
                idTopName[examiner_id] = init
            
        # print(idTopName['10007'])
        # print(len(idTopName))
        return idTopName

    def test(self, idTopName, idColumnName):
        """
        Generates 2 Dataframes for classified and non-classified IDs
        Based on frequency threshold and IBM threshold 
        """
        # List of dictionaries, where: key,val pairs are rows in dataframe
        fullDataDf = pd.DataFrame([ {idColumnName: idStr, 
                                "Key_topSpelling": topName, 
                                "Freq": Freq, "Total": Total, 
                                "Freq%": round(Freq/Total,2),
                                "Female%":female , 
                                "Male%":male
                                } for idStr, (topName, Freq, Total, female, male) in idTopName.items() ]
                        )
        
        # Determine which IDs met our classification criteria 
        met_threshold = [ idTopName[key][0] for key,freq in zip(idTopName,fullDataDf['Freq%']) 
                                            if (idTopName[key][3]>= self.femaleThreshold or idTopName[key][4] >= self.maleThreshold) and (freq >= self.firstNameFreq_Threshold) ]
        # Partition fullData into 2 dataframes based on classification criteria         
        classifiedDf = fullDataDf[fullDataDf['Key_topSpelling'].isin(met_threshold)]
        notClassifiedDf = fullDataDf[~fullDataDf['Key_topSpelling'].isin(met_threshold)]
    
        print("classified: - ",len(classifiedDf), ":", round(len(classifiedDf)/len(idTopName)*100,2))
        print("not classified - ",len(notClassifiedDf), ":", round(len(notClassifiedDf)/len(idTopName)*100,2))


def main():
    t0 = time.time()
    examinerObj = GenderRaceAnalysis("E")
    # lawyerObj = GenderRaceAnalysis("L")



    t1 = time.time()
    print(f"time elapsed: {round(t1-t0,2)} sec")

    # print(f'gender df: {examinerObj.genderDf.head(1)}')
    print(f'country df: {examinerObj.countryDf.head()}')
    
main()
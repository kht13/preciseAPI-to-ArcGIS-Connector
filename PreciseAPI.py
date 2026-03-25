from arcgis.features import Feature
from arcgis.geometry import project
import requests

class preciseApi:
    def __init__(self, apiKey: str, userName: str, companyId: int, apiVer: str = 'v202007'):
        self.__headers = {'User-Name': userName, 'Api-Key': apiKey}
        self.__companyId = companyId
        if apiVer[0]!='v':
            apiVer = 'v'+apiVer
        self.__baseUrl = 'https://api-myfleet.precisemrm.com/api/'+apiVer+'/companies/' + str(self.__companyId)
        data = requests.get(self.__baseUrl+"/fleets", headers = self.__headers)
        if(data.status_code != 200):
            errorMessage = data.text[17:-21]
            raise Exception(errorMessage)
        
    def getFleetsAndAssets(self):
        url = self.__baseUrl + '/fleets'
        fleetListData = requests.get(url, headers=self.__headers)
        if(fleetListData.status_code != 200):
            if(fleetListData.status_code == 404):
                errorMessage = "404 - File or directory not found"
            else:
                errorMessage = fleetListData.text
            raise Exception(errorMessage)
        fleets = []
        for fleetData in fleetListData.json()['FleetList']:
            if(fleetData["Active"]):
                fleet = {"text": "Name: "+fleetData["FleetName"]+"\nID: "+str(fleetData["FleetId"]), "name": fleetData["FleetName"]}
                fleet["value"] = []
                assetListData = requests.get(url+"/"+str(fleetData["FleetId"])+"/assets", headers=self.__headers)
                if(assetListData.status_code != 200):
                    if(assetListData.status_code == 404):
                        errorMessage = "404 - File or directory not found"
                    else:
                        errorMessage = assetListData.text
                    raise Exception(errorMessage)
                for assetData in assetListData.json()['AssetList']:
                    if(assetData["Active"]):
                        fleet["value"].append({
                            "text":"Name: "+assetData["Name"]+"\nID: "+str(assetData["AssetId"]),
                            "name": assetData["Name"],
                            "value": assetData["AssetId"]
                        })
                fleets.append(fleet)
        return fleets
    
    def convertRawGeoData(self, rawData, assetIdMap: None | dict[int, int]=None) -> dict[str, list[Feature]]:
        adds = []
        updates = []
        keySet = set(assetIdMap.values() if assetIdMap is not None else [])
        #project takes a long time each time it is used, so it is faster to build geometries and project all
        points = project(
                    geometries=
                        [{"x":assetReport['Positions'][0]['Location']['Longitude'], 
                          "y":assetReport['Positions'][0]['Location']['Latitude']}
                         for assetReport in rawData], 
                    in_sr = 4326, 
                    out_sr = 3857)
        for i in range(len(rawData)):
            assetReport = rawData[i]
            attributes = {
                'AssetId': assetReport['AssetId'],
                'AssetName': assetReport['AssetName'],
                'HeadingDegrees': assetReport['Positions'][0]['HeadingDegrees'],
                'IgnitionStatus': 1 if assetReport['Positions'][0]['IgnitionStatusOn'] else 0,
                'ReportTime': assetReport['Positions'][0]['ReportTime'],
                'SpeedMilesPerHour': assetReport['Positions'][0]['SpeedMetersPerSecond']*3600/1609.344,
                'IdleSeconds': assetReport['Positions'][0]['VehicleMeters']['IdleSeconds'],
                'OdometerMiles': assetReport['Positions'][0]['VehicleMeters']['OdometerMeters']/1609.344,
            }
            if(assetReport['Positions'][0]['FORCEMessages'] is not None):
                attributes['ErrorStatus'] = assetReport['Positions'][0]['FORCEMessages']['ErrorStatus']
                attributes['VehicleId'] = assetReport['Positions'][0]['FORCEMessages']['VehicleId']
            if(assetIdMap is not None and assetReport['AssetId'] in assetIdMap):
                attributes["OBJECTID"] = assetIdMap[assetReport['AssetId']]
                feature = Feature(geometry=points[i], attributes=attributes)
                updates.append(feature)
                keySet.remove(assetIdMap[assetReport['AssetId']])
            else:
                feature = Feature(geometry=points[i], attributes=attributes)
                adds.append(feature)
        
        features = {}
        if(len(adds)>0):
            features['adds'] = adds
        if(len(updates)>0):
            features['updates'] = updates
        if(len(keySet)>0):
            features['deletes'] = list(keySet)
            
        return features
    
    def getLatestAssetLocations(self, assetIds: list[int], assetIdMap: None | dict[int, int]=None) -> dict[str, list[Feature]]:
        url = self.__baseUrl + '/reports/LastReport'
        rawData = requests.post(url, data={"AssetIds":assetIds}, headers=self.__headers)
        if(rawData.status_code != 200):
            if(rawData.status_code == 404):
                errorMessage = "404 - File or directory not found"
            else:
                errorMessage = rawData.text
            raise Exception(errorMessage)
        data = rawData.json()
        return self.convertRawGeoData(data['FleetRawData'][0]['AssetRawData'], assetIdMap)
        

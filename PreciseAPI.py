from arcgis.features import Feature
from arcgis.geometry import project
import requests

class preciseApi:
    def __init__(self, apiKey: str, userName: str, companyId: int, apiVer: str | None = None):
        self.__headers = {'User-Name': userName, 'Api-Key': apiKey}
        self.__companyId = companyId
        self.__apiVer = 'v202007' if apiVer is None or apiVer[0]!='v' else apiVer
        self.__baseUrl = 'https://api-myfleet.precisemrm.com/api/'+self.__apiVer+'/companies/' + str(self.__companyId)
        data = requests.get(self.__baseUrl+"/fleets", headers = self.__headers)
        if(data.status_code != 200):
            errorMessage = data.text[17:-21]
            raise Exception(errorMessage)
        
    def getFleetsAndAssets(self):
        url = self.__baseUrl + '/fleets'
        fleetListData = requests.get(url, headers=self.__headers).json()
        fleets = []
        for fleetData in fleetListData['FleetList']:
            if(fleetData["Active"]):
                fleet = {"FleetId": fleetData["FleetId"], "FleetName": fleetData["FleetName"]}
                fleet["Assets"] = []
                assetListData = requests.get(url+"/"+str(fleetData["FleetId"])+"/assets", headers=self.__headers).json()
                for assetData in assetListData['AssetList']:
                    if(assetData["Active"]):
                        fleet["Assets"].append({
                            "AssetId": assetData["AssetId"],
                            "AssetName": assetData["Name"]
                        })
                fleets.append(fleet)
        return fleets
    
    def convertRawGeoData(self, rawData, assetIdMap: None | dict[int, int]=None) -> dict[str, list[Feature]]:
        adds = []
        updates = []
        keySet = set(assetIdMap.values() if assetIdMap is not None else [])
        for assetReport in rawData:
            point = project(
                geometries=[{"x":assetReport['Positions'][0]['Location']['Longitude'], 
                        "y":assetReport['Positions'][0]['Location']['Latitude']}],
                in_sr = 4326,
                out_sr = 3857
            )[0]
            attributes = {
                'AssetId': assetReport['AssetId'],
                'AssetName': assetReport['AssetName'],
                'HeadingDegrees': assetReport['Positions'][0]['HeadingDegrees'],
                'IgnitionStatus': 1 if assetReport['Positions'][0]['IgnitionStatusOn'] else 0,
                'ReportTime': assetReport['Positions'][0]['ReportTime'],
                'SpeedMetersPerSecond': assetReport['Positions'][0]['SpeedMetersPerSecond'],
                'EngineSeconds': assetReport['Positions'][0]['VehicleMeters']['EngineSeconds'],
                'IdleSeconds': assetReport['Positions'][0]['VehicleMeters']['IdleSeconds'],
                'OdometerMeters': assetReport['Positions'][0]['VehicleMeters']['OdometerMeters'],
            }
            if(assetReport['Positions'][0]['FORCEMessages'] is not None):
                attributes['ErrorStatus'] = assetReport['Positions'][0]['FORCEMessages']['ErrorStatus']
                attributes['VehicleId'] = assetReport['Positions'][0]['FORCEMessages']['VehicleId']
            if(assetIdMap is not None and assetReport['AssetId'] in assetIdMap):
                attributes["OBJECTID"] = assetIdMap[assetReport['AssetId']]
                feature = Feature(geometry=point, attributes=attributes)
                updates.append(feature)
                keySet.remove(assetIdMap[assetReport['AssetId']])
            else:
                feature = Feature(geometry=point, attributes=attributes)
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
        data = requests.post(url, data={"AssetIds":assetIds}, headers=self.__headers).json()
        return self.convertRawGeoData(data['FleetRawData'][0]['AssetRawData'], assetIdMap)
        

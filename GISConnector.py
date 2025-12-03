from arcgis.gis import GIS
from arcgis.features import FeatureLayerCollection, FeatureLayer
from PreciseAPI import preciseApi
import json

class gisHelper:
    __layer: FeatureLayer | None = None
    __assetIdMap: dict[int, int] | None = None
    def __init__(self, apiKey: str| None = None, username: str | None = None, password: str | None = None):
        if(apiKey is not None):
            self.__gis = GIS(api_key=apiKey)
        else:
            self.__gis = GIS(username=username, password=password)
        try:
            self.__gis.content.is_service_name_available("A", "featureService")
        except(KeyError):
            raise Exception("Bad Api Key.")
        
    
    def setLayer(self, layerName: str):
        flc = None
        if not self.__gis.content.is_service_name_available(layerName, "featureService"):
            item = self.__gis.content.search(query="title:"+layerName, item_type="Feature Layer Collection")[0]
            flc = FeatureLayerCollection.fromitem(item)
        else:
            emptyService = self.__gis.content.create_service(name = layerName, service_type = 'featureService')
            flc = FeatureLayerCollection.fromitem(emptyService)
        for layer in flc.layers:
            if(layer.properties.name==layerName):
                self.__layer = layer
                self.__assetIdMap = {}
                for feature in self.__layer.query().features:
                    self.__assetIdMap[feature.attributes['AssetId']] = feature.attributes['OBJECTID'] 
                return
        fl_definition = None
        with open("Layer Definition.json") as f:
            fl_definition = json.load(f)
        fl_definition['name'] = layerName
        flc.manager.add_to_definition({"layers": [fl_definition]})
        for layer in flc.layers:
            if(layer.properties.name==layerName):
                self.__layer = layer
    
    def updateLayer(self, precise: preciseApi, assetIds: list):
        features = precise.getLatestAssetLocations(assetIds, assetIdMap=self.__assetIdMap)
        if(self.__layer is None):
            raise Exception("No layer has been set. Try setting a layer with setLayer first.")
        res = self.__layer.edit_features(**features)
        if('adds' in features or 'deletes' in features):
            newIdMap = {}
            for feature in self.__layer.query().features:
                newIdMap[feature.attributes['AssetId']] = feature.attributes['OBJECTID']
            self.__assetIdMap = newIdMap
        return res
# CustomTianDiTuLayerV100.0-ObjC

##概览

这个示例是为了解决如何基于ArcGIS Runtime SDK for iOS 100.0，通过客户化图层访问天地图WMTS服务。这是一个完整独立的工程，基于Xcode8.2版本开发，支持iOS9以上的系统部署。

##说明：

工程中包含的TianDiTuLayer，是用于访问天地图服务的自定义图层。TianDiTuLayerInfo封装了天地图wmts服务的缓存schema信息。

这个Demo实现了对以下天地图服务的访问：

1. 天地图矢量服务，（地图，中文标注，英文标注）
2. 天地图影像服务，（地图，中文标注，英文标注）
3. 天地图地形服务，（地图，中文标注）

支持Web Mercator和GCS2000两种坐标系的服务访问。

##系统需求：

1. ArcGIS Runtime SDK for iOS 100.0
2. Xcode 8(或更高)
3. iOS 10 SDK（或更高）

##工程下载地址：
[ArcGISRuntimeForIOSV100.0Demos](https://github.com/serverteamCN/IOS.git)





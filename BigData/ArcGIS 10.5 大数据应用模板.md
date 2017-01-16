# ArcGIS 10.5 大数据应用模板 #
author: 刘峥，勾戈雪黎
date: 2017-1-16

![](http://i.imgur.com/a4qUJKL.jpg)

# GeoAnalytics矢量大数据应用模板 #
## 案例一：结合GeoEvent实时数据源与Python API生成追踪线 ##
 
*关键词：实时；GeoEvent；流服务；Python API；*
    
实时数据是大数据分析中最重要的数据来源之一，而Python API又提供了
简单方便的Web端调用大数据分析工具的接口，本案例将示范如何通过    GeoEvent接入实时流服务，并将结果要素服务输入大数据分析工具Reconstruct Tracts，通过在浏览器中调用Python API来生成追踪线。本案例中使用的数据源为在线的流服务，实时记录了美国西雅图市公交车的运行情况：https://geoeventsample3.esri.com:6443/arcgis/rest/services/SeattleBus/StreamServer
 

1.	在GeoEvent Manager中通过订阅WebSocket端口建立Input输入：
wss://geoeventsample3.esri.com:8443/arcgis/ws/services/SeattleBus/StreamServer/subscribe

2.	在GeoEvent Manager中建立Output输入，选择输出到Spatiotemporal Big Data Store中，并创建结果要素服务： 
![](http://i.imgur.com/jiAc0r1.png)
![](http://i.imgur.com/VLnlKY3.png)
 
3.	在GeoEvent Manager中建立GeoEvent服务：
![](http://i.imgur.com/X2iKrTw.png)
![](http://i.imgur.com/t7h3Skl.png)
  
4.	在Portal中查看对应的结果及地图服务是否已生成：
![](http://i.imgur.com/rB6HrVJ.jpg)
 
5.	启动Jupyter Notebook，通过Python API调用GeoAnalytics矢量大数据分析工具Reconstruct Tracts：
![](http://i.imgur.com/Fiz69FG.png)
 
6.	在Portal中查看生成的结果：

![](http://i.imgur.com/hCFk0VM.png)
 
图1. 所有巴士运行情况

![](http://i.imgur.com/SaAIxBv.png)
 
图2. 不同线路的巴士运行情况

## 案例二：时空立方体及新兴时空热点分析 ##
 
*关键词：时空立方体；新兴时空热点；ArcGIS Pro；*

时空立方体将时空事件点聚合到时空条柱上，可直观的可视化同时具有时间和空间属性的大数据，新兴时空热点分析工具可识别出其中的趋势，发现时空热点及冷点。本案例将示范如何在ArcGIS Pro中进行新兴时空热点分析。本案例中使用的数据源为美国纽约市出租车记录，并通过在GeoAnalytics Server中注册为Big Data File Shares的方式调用：http://www.nyc.gov/html/tlc/html/about/trip_record_data.shtml
 
1.	在Pro中调用GeoAnalytics大数据工具Create Space Time Cube，生成NetCDF文件（该大数据工具目前只能通过Pro调用，不能通过Portal Map Viewer中的分析工具栏调用）：
![](http://i.imgur.com/SkltvQw.png)

2.	将生成的NetCDF文件输入Emerging Hot Spot Analysis工具，进行新兴时空热点分析，并通过Visualize Space Time Cube in 3D进行三维可视化：
![](http://i.imgur.com/QUPzeF8.png) 

3.	调用GeoAnalytics大数据工具Aggregate Points，利用数据中的“Trip distance”行驶距离属性，生成1km聚合格网：
![](http://i.imgur.com/TNyr3s0.jpg)
 
4.	将新兴时空立方体结果与行驶距离聚合结果共同展示对比：
![](http://i.imgur.com/DgFwasv.png)

 
图3. 出租车的时空热（冷）点与行驶距离对比

## 案例三：利用ModelBuilder生成地铁客流示意图 ##
 
*关键词：ModelBuilder；ArcGIS Pro；示意线；*

利用ModelBuilder建模是地理设计中重要的实现手段，本案例将示范如何在Pro中用ModelBuilder建立模型，自动化的调用GeoAnalytics大数据分析工具来生成地铁客流的示意图。本案例中使用的数据源为英国伦敦市地铁进出站刷卡记录：
https://figshare.com/articles/Spatio-Temporal_Public_Transport_Networks/1452948/1
 
OpenStreetMap提供的伦敦市建筑物底图：
https://mapzen.com/data/metro-extracts/
Tweeter网站公布的带有GeoTag的tweeter数据：
https://dev.twitter.com/streaming/public

1.	先利用GeoAnalytics大数据工具Summarize Attributes将地铁客流数据按照进出站位置汇总，统计出从X站进站—Y站出站的记录共有多少条；再利用XY To Line工具将汇总后的记录生成连线；

2.	利用GeoAnalytics大数据工具Join Features将发布twitter的数据根据地理位置关联到建筑物底图上，模拟表示人口密度；


3.	将两个流程在Pro的ModelBuilder中建立模型：
![](http://i.imgur.com/1Uhiu8M.png) 

4.	叠加显示地铁客流示意图及模拟人口密度图：
![](http://i.imgur.com/RkYRh4B.png)
 
图4. 地铁客流示意图（线段粗细代表客流量）
![](http://i.imgur.com/ThR62Tx.jpg)
 
图5. 中心地区人口密度（红色代表密度较高）与地铁客流量对比

# RasterAnalytics栅格大数据应用模板 #
## 案例一：对连续数据源分析管理和历史展示（2D和3D） ##
 
*关键词：镶嵌数据集；时间模块；*

工具：ArcGIS Pro,  Portal for ArcGIS,  ArcGIS for Server
需求分析：原始数据具有时效性，可用于影像分析工具输入，不同时间的原始数据产出的最后的结果需要统一管理，并需要展示历史变化。
结果展示： 用户可以在Web端看见展示历史变化的服务。见附件“栅格时空展示2”。

1.	原始数据可以是实际采集的某个时间点的矢量数据，如下图:
![](http://i.imgur.com/SWTj1Eu.png)

 
2.	需求是针对这些点做出预测，例如针对点生成插值栅格，可以使用影像大数据提供的栅格工具，如下图所示：
![](http://i.imgur.com/jC51DSM.png)
 

3.	运行工具生成结果如下图所示：
![](http://i.imgur.com/LuWk1TC.png)
 
4.	如果原始数据是持续采集的，那么后续生成的栅格需要统一管理，并且可以开启时间属性，展示历史数据。该功能需要借助镶嵌数据集管理栅格，将步骤一至步骤三生成的结果添加进同一个镶嵌数据集，然后对镶嵌数据集中footprint添加时间字段，记录每份原始数据记录的时间，然后对图层开启时间属性，最后展示结果见附件“栅格时空展示1”。


5.	将开始时间属性的镶嵌数据集发布成为服务，如果后续有新采集数据，直接将该数据分析完成后的结果加入到镶嵌数据集中，前端服务即可随之跟新，所以用户只要维护一个服务，即可一直添加数据，展示历史变化。


## 案例二：将无人机数据接入平台 ##
 
*关键词：无人机*

影像数据的获取方式越来越多，无人机的普及让影像处理也越来越私人化，对于无人机生产的小型范围数据可以直接利用Esri的Drone2Map来处理。
以下利用Drone2Map处理生成的正射影像和DSM栅格数据。
![](http://i.imgur.com/nuhmrs9.jpg)
![](http://i.imgur.com/i92OHKb.jpg)
 
处理后的数据可以直接与平台对接，作为影像大数据处理输入。利用栅格分析Extractbands方法，将一二波段抽出融合，结果更加清晰的对比了土地和植被。结果以服务的形式直接托管在ArcGIS for Server上。
![](http://i.imgur.com/gFRXemC.png)
 
 
## 案例三：学校选址 ##
 
*关键词：分析任务链；*

传统的桌面分析可以转移到Pro或者Portal中,可以利用影像大数据分析工具编辑器,建立整个工作链。
以学校选址为例，其中输入为三个栅格图层：高程图，到其他学校距离图以及到娱乐场所距离图。
利用栅格大数据工具中的Remap，将以上三个图层重分类，并进行加权叠加获取最后的结果图，其中粉红色区域为事宜的学校选址。
![](http://i.imgur.com/EuZFcNG.png)
 

----------

 
*## 附录： python API 调用工具代码##*
    <!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/1999/REC-html401-19991224/strict.dtd">
<html>
<body>
<div style="float: left; white-space: pre; line-height: 1; background: #FFFFFF; "><span class="sc0">
</span><span class="sc1"># coding: utf-8</span><span class="sc0">

</span><span class="sc1"># In[3]:</span><span class="sc0">

</span><span class="sc5">from</span><span class="sc0"> </span><span class="sc11">arcgis</span><span class="sc10">.</span><span class="sc11">gis</span><span class="sc0"> </span><span class="sc5">import</span><span class="sc0"> </span><span class="sc11">GIS</span><span class="sc0">

</span><span class="sc1">#</span><span class="sc0">
</span><span class="sc1">#连接到Portal并获取实时传入的GeoEvent结果要素图层作为工具输入</span><span class="sc0">
</span><span class="sc1">#</span><span class="sc0">
</span><span class="sc11">my_portal</span><span class="sc0"> </span><span class="sc10">=</span><span class="sc0"> </span><span class="sc11">GIS</span><span class="sc10">(</span><span class="sc3">"https://server111.esrichina.com/arcgis"</span><span class="sc10">,</span><span class="sc0"> </span><span class="sc3">"portaladmin"</span><span class="sc10">,</span><span class="sc0"> </span><span class="sc3">"password"</span><span class="sc10">,</span><span class="sc0"> </span><span class="sc11">verify_cert</span><span class="sc10">=</span><span class="sc5">False</span><span class="sc10">)</span><span class="sc0">
</span><span class="sc11">bus_pts</span><span class="sc0"> </span><span class="sc10">=</span><span class="sc0"> </span><span class="sc11">my_portal</span><span class="sc10">.</span><span class="sc11">content</span><span class="sc10">.</span><span class="sc11">search</span><span class="sc10">(</span><span class="sc3">"seattle"</span><span class="sc10">,</span><span class="sc0"> </span><span class="sc3">"Feature Layer"</span><span class="sc10">)[</span><span class="sc2">0</span><span class="sc10">]</span><span class="sc0">
</span><span class="sc11">bus_pts</span><span class="sc0">


</span><span class="sc1"># In[23]:</span><span class="sc0">

</span><span class="sc1">#</span><span class="sc0">
</span><span class="sc1"># 查看图层属性表中的字段</span><span class="sc0">
</span><span class="sc1">#</span><span class="sc0">
</span><span class="sc11">bus_layer</span><span class="sc0"> </span><span class="sc10">=</span><span class="sc0"> </span><span class="sc11">bus_pts</span><span class="sc10">.</span><span class="sc11">layers</span><span class="sc10">[</span><span class="sc2">0</span><span class="sc10">]</span><span class="sc0">
</span><span class="sc11">attri</span><span class="sc0"> </span><span class="sc10">=</span><span class="sc0"> </span><span class="sc11">bus_layer</span><span class="sc10">.</span><span class="sc11">query</span><span class="sc10">().</span><span class="sc11">df</span><span class="sc10">.</span><span class="sc11">head</span><span class="sc10">()</span><span class="sc0">
</span><span class="sc11">attri</span><span class="sc0">


</span><span class="sc1"># In[24]:</span><span class="sc0">

</span><span class="sc1">#</span><span class="sc0">
</span><span class="sc1">#执行reconstruct_tracks工具</span><span class="sc0">
</span><span class="sc1">#</span><span class="sc0">
</span><span class="sc5">from</span><span class="sc0"> </span><span class="sc11">arcgis</span><span class="sc10">.</span><span class="sc11">geoanalytics</span><span class="sc10">.</span><span class="sc11">summarize_data</span><span class="sc0"> </span><span class="sc5">import</span><span class="sc0"> </span><span class="sc11">reconstruct_tracks</span><span class="sc0">
</span><span class="sc11">agg_result</span><span class="sc0"> </span><span class="sc10">=</span><span class="sc0"> </span><span class="sc11">reconstruct_tracks</span><span class="sc10">(</span><span class="sc11">bus_layer</span><span class="sc10">.</span><span class="sc11">url</span><span class="sc10">,</span><span class="sc0"> 
                                </span><span class="sc11">track_fields</span><span class="sc10">=</span><span class="sc4">'BusNo'</span><span class="sc10">,</span><span class="sc0">
                                </span><span class="sc11">method</span><span class="sc10">=</span><span class="sc4">'GEODESIC'</span><span class="sc10">,</span><span class="sc0">
                               </span><span class="sc11">output_name</span><span class="sc10">=</span><span class="sc4">'Seattle Bus Tracks by PythonAPI'</span><span class="sc10">)</span><span class="sc0">


</span><span class="sc1"># In[25]:</span><span class="sc0">

</span><span class="sc1">#</span><span class="sc0">
</span><span class="sc1"># 查看生成的结果要素服务</span><span class="sc0">
</span><span class="sc1">#</span><span class="sc0">
</span><span class="sc11">agg_result</span><span class="sc0">

</span></div></body>
</html>
